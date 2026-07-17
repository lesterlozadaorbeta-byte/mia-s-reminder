"""AI Engine - Core intelligence for natural language processing and action generation."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ai.prompts import SYSTEM_PROMPT, SCHEDULER_PROMPT, TASK_BREAKDOWN_PROMPT

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key)


class AIEngine:
    """Core AI engine for processing user messages and generating actions."""

    def __init__(self, db: AsyncSession, user):
        self.db = db
        self.user = user
        self.actions: List[Dict[str, Any]] = []
        self.follow_up_questions: List[str] = []

    def _build_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """Build the system prompt with user context."""
        return SYSTEM_PROMPT.format(
            timezone=self.user.timezone or "UTC",
            current_time=datetime.now(timezone.utc).isoformat(),
            user_name=self.user.full_name,
            user_habits=context.get("habits", "No habits learned yet.") if context else "No habits learned yet.",
            recent_context=context.get("recent", "No recent context.") if context else "No recent context.",
        )

    async def process_message(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[Dict[str, Any]], List[str]]:
        """
        Process a user message and return AI response with actions.

        Returns:
            Tuple of (response_text, actions, follow_up_questions)
        """
        system_prompt = self._build_system_prompt(context)

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 20 messages for context)
        for msg in conversation_history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current message
        messages.append({"role": "user", "content": user_message})

        # Add function calling for structured action extraction
        tools = self._get_tools()

        try:
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=settings.openai_max_tokens,
                temperature=0.7,
            )

            # Process response
            assistant_message = response.choices[0].message
            response_text = assistant_message.content or ""

            # Process tool calls (actions)
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    action = {
                        "action_type": tool_call.function.name,
                        "parameters": json.loads(tool_call.function.arguments),
                    }
                    self.actions.append(action)

            # Extract follow-up questions from response
            self._extract_follow_ups(response_text)

            return response_text, self.actions, self.follow_up_questions

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return (
                "I'm sorry, I encountered an issue processing your request. Please try again.",
                [],
                [],
            )

    def _get_tools(self) -> List[Dict[str, Any]]:
        """Define available tools/functions for the AI."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_reminder",
                    "description": "Create a new reminder for the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Reminder title"},
                            "description": {"type": "string", "description": "Additional details"},
                            "remind_at": {"type": "string", "description": "ISO datetime when to remind"},
                            "is_recurring": {"type": "boolean", "description": "Whether it repeats"},
                            "recurrence_type": {
                                "type": "string",
                                "enum": ["daily", "weekly", "monthly", "yearly"],
                                "description": "How often it repeats",
                            },
                            "priority": {"type": "integer", "minimum": 1, "maximum": 4},
                            "is_persistent": {"type": "boolean", "description": "Keep reminding until done"},
                        },
                        "required": ["title", "remind_at"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_event",
                    "description": "Create a calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "start_time": {"type": "string", "description": "ISO datetime"},
                            "end_time": {"type": "string", "description": "ISO datetime"},
                            "location": {"type": "string"},
                            "is_recurring": {"type": "boolean"},
                            "recurrence_rule": {"type": "string", "description": "RRULE format"},
                        },
                        "required": ["title", "start_time", "end_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_todo",
                    "description": "Create a to-do task or task list",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 4},
                            "due_date": {"type": "string", "description": "ISO datetime"},
                            "estimated_duration_minutes": {"type": "integer"},
                            "subtasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "estimated_duration_minutes": {"type": "integer"},
                                    },
                                },
                            },
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_alarm",
                    "description": "Create an alarm",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "alarm_time": {"type": "string", "description": "ISO datetime"},
                            "alarm_type": {
                                "type": "string",
                                "enum": ["wake_up", "medication", "study", "general"],
                            },
                            "is_recurring": {"type": "boolean"},
                            "repeat_days": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "0=Mon, 6=Sun",
                            },
                        },
                        "required": ["title", "alarm_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_schedule",
                    "description": "Generate an optimized schedule for the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "schedule_type": {
                                "type": "string",
                                "enum": ["daily", "weekly", "study", "work", "fitness"],
                            },
                            "date_range_start": {"type": "string"},
                            "date_range_end": {"type": "string"},
                            "tasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "duration_minutes": {"type": "integer"},
                                        "priority": {"type": "integer"},
                                    },
                                },
                            },
                        },
                        "required": ["schedule_type"],
                    },
                },
            },
        ]

    def _extract_follow_ups(self, response_text: str):
        """Extract follow-up questions from the AI response."""
        # Simple heuristic: lines ending with '?' in the response
        lines = response_text.split("\n")
        for line in lines:
            line = line.strip()
            if line.endswith("?") and len(line) > 10:
                self.follow_up_questions.append(line)

    async def generate_schedule(
        self,
        tasks: List[Dict[str, Any]],
        existing_events: List[Dict[str, Any]],
        preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate an optimized schedule using AI."""
        prompt = f"""Create an optimized schedule given:

Tasks to schedule:
{json.dumps(tasks, indent=2)}

Existing events (cannot overlap):
{json.dumps(existing_events, indent=2)}

User preferences:
{json.dumps(preferences, indent=2)}

Return a JSON schedule with time slots for each task.
"""
        try:
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SCHEDULER_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=2048,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Schedule generation error: {e}")
            return {"error": "Failed to generate schedule"}

    async def break_down_task(self, task: str, context: str = "") -> List[Dict[str, Any]]:
        """Break a large task into smaller subtasks."""
        prompt = TASK_BREAKDOWN_PROMPT.format(task=task, context=context)

        try:
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a task breakdown assistant. Return JSON."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=1024,
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("subtasks", [])
        except Exception as e:
            logger.error(f"Task breakdown error: {e}")
            return []
