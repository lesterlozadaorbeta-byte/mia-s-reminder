"""AI Chat endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import enforce_ai_limit, increment_ai_usage
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.chat import (
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    AIAction,
)
from app.ai.engine import AIEngine
from app.ai.action_executor import ActionExecutor

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    data: MessageCreate,
    current_user: User = Depends(enforce_ai_limit),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the AI assistant."""
    conversation = None

    if data.conversation_id:
        # Get existing conversation
        result = await db.execute(
            select(Conversation)
            .where(
                Conversation.id == data.conversation_id,
                Conversation.user_id == current_user.id,
            )
            .options(selectinload(Conversation.messages))
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
    else:
        # Create new conversation
        conversation = Conversation(
            user_id=current_user.id,
            title=data.content[:50] + "..." if len(data.content) > 50 else data.content,
        )
        db.add(conversation)
        await db.flush()

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.content,
    )
    db.add(user_message)
    await db.flush()

    # Get conversation history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in messages]

    # Process with AI engine
    ai_engine = AIEngine(db, current_user)
    context = conversation.context_data or {}

    response_text, actions, follow_ups = await ai_engine.process_message(
        user_message=data.content,
        conversation_history=history,
        context=context,
    )

    # Execute detected actions
    action_executor = ActionExecutor(db, current_user.id)
    executed_actions = []
    action_responses = []

    for action in actions:
        result = await action_executor.execute(action)
        executed_actions.append(result)
        action_responses.append(
            AIAction(
                action_type=action["action_type"],
                parameters=action["parameters"],
                confirmation_needed=False,
                message=f"Created {action['action_type'].replace('_', ' ')}",
            )
        )

    # Save assistant message
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        model_used="gpt-4o",
        intent_detected=actions[0]["action_type"] if actions else None,
        actions_taken=executed_actions,
    )
    db.add(assistant_message)

    # Update conversation context
    conversation.context_data = context
    conversation.updated_at = user_message.created_at

    return ChatResponse(
        message=MessageResponse(
            id=assistant_message.id,
            conversation_id=conversation.id,
            role="assistant",
            content=response_text,
            intent_detected=assistant_message.intent_detected,
            actions_taken=executed_actions,
            created_at=assistant_message.created_at,
        ),
        actions=action_responses,
        follow_up_questions=follow_ups,
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user conversations."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()
    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .options(selectinload(Conversation.messages))
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    await db.delete(conversation)
