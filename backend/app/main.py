"""Mia's Reminder API - Production-ready, self-contained."""

import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text, Integer, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# --- Config ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

# --- Database URL ---
def get_database_url():
    """Get async database URL from environment."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        # Fallback: try individual components Railway might provide
        url = os.environ.get("DATABASE_PRIVATE_URL", "")
    if not url:
        logger.warning("No DATABASE_URL found, using SQLite fallback")
        return "sqlite+aiosqlite:///./mias_reminder.db"
    # Convert to asyncpg format
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not url.startswith("postgresql+asyncpg://"):
        url = "postgresql+asyncpg://" + url
    logger.info(f"Database URL scheme: {url.split('://')[0]}")
    return url

DB_URL = get_database_url()
logger.info(f"Connecting to database...")

try:
    if "sqlite" in DB_URL:
        engine = create_async_engine(DB_URL, echo=False)
    else:
        engine = create_async_engine(DB_URL, echo=False, pool_size=5, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Database engine creation failed: {e}")
    # Fallback to SQLite
    engine = create_async_engine("sqlite+aiosqlite:///./mias_reminder.db", echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Fell back to SQLite")

# --- Models ---
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    auth_provider = Column(String(50), default="email")
    timezone_str = Column("timezone", String(100), default="UTC")
    language = Column(String(10), default="en")
    theme = Column(String(20), default="system")
    telegram_chat_id = Column(String(100), nullable=True)
    notification_prefs = Column("notification_preferences", Text, default="{}")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), default="New Chat")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Message(Base):
    __tablename__ = "messages"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    remind_at = Column(DateTime, nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurrence_type = Column(String(20), nullable=True)
    is_persistent = Column(Boolean, default=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Todo(Base):
    __tablename__ = "todos"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=3)
    is_completed = Column(Boolean, default=False)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# --- Security ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(user_id: str, minutes: int = 60) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

# --- Schemas ---
class RegisterReq(BaseModel):
    email: str
    password: str
    full_name: str

class LoginReq(BaseModel):
    email: str
    password: str

class ChatReq(BaseModel):
    content: str
    conversation_id: Optional[str] = None

class ReminderReq(BaseModel):
    title: str
    description: Optional[str] = None
    remind_at: str
    is_persistent: bool = True

class TodoReq(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 3
    due_date: Optional[str] = None

# --- App ---
app = FastAPI(title="Mia's Reminder", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- DB Dependency ---
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_current_user(authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# --- Startup ---
@app.on_event("startup")
async def startup():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")
    except Exception as e:
        logger.error(f"Database startup error: {e}")

# --- Health ---
@app.get("/")
async def root():
    return {"name": "Mia's Reminder", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health():
    try:
        async with SessionLocal() as db:
            await db.execute(select(User).limit(1))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})

# --- Auth ---
@app.post("/api/v1/auth/register")
async def register(data: RegisterReq, db: AsyncSession = Depends(get_db)):
    try:
        # Validate
        if not data.email or "@" not in data.email:
            raise HTTPException(status_code=400, detail="Invalid email")
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        if not data.full_name:
            raise HTTPException(status_code=400, detail="Name is required")

        # Check existing
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")
        
        # Create user
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        
        access_token = create_token(user.id)
        refresh_token = create_token(user.id, minutes=10080)
        
        logger.info(f"User registered: {data.email}")
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": 3600}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/auth/login")
async def login(data: LoginReq, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        
        if not user or not user.hashed_password:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        user.last_login_at = datetime.now(timezone.utc)
        access_token = create_token(user.id)
        refresh_token = create_token(user.id, minutes=10080)
        
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": 3600}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "timezone": user.timezone_str}

# --- AI Chat ---
@app.post("/api/v1/chat/message")
async def chat_message(data: ChatReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        if not OPENAI_API_KEY:
            return _chat_response("Hi! I'm Mia. The AI service isn't configured yet, but the app is working! Your account is set up and ready.")
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": f"You are Mia, a friendly AI personal assistant. Help {user.full_name} organize their life with reminders, schedules, to-do lists, and alarms. Be helpful, concise, and warm. Current time: {datetime.now(timezone.utc).isoformat()}"},
                {"role": "user", "content": data.content},
            ],
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
        return _chat_response(reply)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return _chat_response(f"Sorry, I had trouble processing that. Error: {str(e)[:100]}")

def _chat_response(content: str):
    return {
        "message": {
            "id": str(uuid.uuid4()),
            "conversation_id": str(uuid.uuid4()),
            "role": "assistant",
            "content": content,
            "intent_detected": None,
            "actions_taken": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "actions": [],
        "follow_up_questions": [],
    }

# --- Reminders ---
@app.get("/api/v1/reminders")
async def list_reminders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reminder).where(Reminder.user_id == user.id).order_by(Reminder.remind_at))
    reminders = result.scalars().all()
    return [{"id": r.id, "title": r.title, "description": r.description, "remind_at": r.remind_at.isoformat() if r.remind_at else None, "status": r.status, "is_persistent": r.is_persistent} for r in reminders]

@app.post("/api/v1/reminders")
async def create_reminder(data: ReminderReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    reminder = Reminder(user_id=user.id, title=data.title, description=data.description, remind_at=datetime.fromisoformat(data.remind_at), is_persistent=data.is_persistent)
    db.add(reminder)
    await db.flush()
    return {"id": reminder.id, "title": reminder.title, "status": "created"}

# --- Todos ---
@app.get("/api/v1/todos")
async def list_todos(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo).where(Todo.user_id == user.id).order_by(Todo.priority))
    todos = result.scalars().all()
    return {"todos": [{"id": t.id, "title": t.title, "priority": t.priority, "is_completed": t.is_completed, "due_date": t.due_date.isoformat() if t.due_date else None} for t in todos], "total": len(todos), "completed": sum(1 for t in todos if t.is_completed), "pending": sum(1 for t in todos if not t.is_completed)}

@app.post("/api/v1/todos")
async def create_todo(data: TodoReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    todo = Todo(user_id=user.id, title=data.title, description=data.description, priority=data.priority, due_date=datetime.fromisoformat(data.due_date) if data.due_date else None)
    db.add(todo)
    await db.flush()
    return {"id": todo.id, "title": todo.title, "status": "created"}

@app.post("/api/v1/todos/{todo_id}/complete")
async def complete_todo(todo_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo).where(Todo.id == todo_id, Todo.user_id == user.id))
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo.is_completed = True
    return {"id": todo.id, "status": "completed"}

# --- Dashboard ---
@app.get("/api/v1/dashboard")
async def dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    todos_result = await db.execute(select(Todo).where(Todo.user_id == user.id))
    todos = todos_result.scalars().all()
    reminders_result = await db.execute(select(Reminder).where(Reminder.user_id == user.id, Reminder.status == "active"))
    reminders = reminders_result.scalars().all()
    
    total = len(todos)
    completed = sum(1 for t in todos if t.is_completed)
    
    return {
        "today_events": [],
        "upcoming_reminders": [{"id": r.id, "title": r.title, "remind_at": r.remind_at.isoformat() if r.remind_at else None} for r in reminders[:5]],
        "active_alarms": [],
        "pending_todos": [{"id": t.id, "title": t.title, "priority": t.priority} for t in todos if not t.is_completed][:5],
        "stats": {
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
            "weekly_completed": completed,
            "active_reminders": len(reminders),
            "today_event_count": 0,
        },
    }

# --- Error handler ---
@app.exception_handler(Exception)
async def global_handler(request, exc):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})
