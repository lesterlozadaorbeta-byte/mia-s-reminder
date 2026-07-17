"""Mia's Reminder API - Production Configuration."""

import os
import uuid
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text, Integer, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from starlette.middleware.base import BaseHTTPMiddleware
import uuid as uuid_mod

# ═══════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("mia")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
APP_ENV = os.environ.get("APP_ENV", "production")
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

# ═══════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════

def get_database_url():
    url = os.environ.get("DATABASE_URL", "") or os.environ.get("DATABASE_PRIVATE_URL", "")
    if not url:
        return "sqlite+aiosqlite:///./mias_reminder.db"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

DB_URL = get_database_url()

try:
    engine = create_async_engine(DB_URL, echo=False, pool_size=10, pool_pre_ping=True, pool_recycle=300)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    logger.info(f"Database connected ({DB_URL.split('://')[0]})")
except Exception as e:
    engine = create_async_engine("sqlite+aiosqlite:///./mias_reminder.db", echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    logger.warning(f"Database fallback to SQLite: {e}")

# ═══════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid_mod.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    auth_provider = Column(String(50), default="email")
    timezone_str = Column("timezone", String(100), default="UTC")
    language = Column(String(10), default="en")
    theme = Column(String(20), default="system")
    telegram_chat_id = Column(String(100), nullable=True)
    notification_prefs = Column("notification_preferences", JSON, default=dict)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime(timezone=True), nullable=True)

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurrence_type = Column(String(20), nullable=True)
    is_persistent = Column(Boolean, default=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Todo(Base):
    __tablename__ = "todos"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=3)
    is_completed = Column(Boolean, default=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# ═══════════════════════════════════════════════
# SECURITY
# ═══════════════════════════════════════════════

def hash_password(password: str) -> str:
    salt = uuid.uuid4().hex[:16]
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(plain: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split("$", 1)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == hashed
    except Exception:
        return False

def create_token(user_id: str, token_type: str = "access", minutes: int = 60) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": user_id, "type": token_type, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def sanitize_input(text: str, max_length: int = 500) -> str:
    """Sanitize user input - prevent XSS."""
    if not text:
        return ""
    text = text[:max_length]
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text.strip()

# ═══════════════════════════════════════════════
# RATE LIMITING
# ═══════════════════════════════════════════════

rate_limit_store = defaultdict(list)

def check_rate_limit(ip: str, limit: int = 30, window: int = 60) -> bool:
    """Simple in-memory rate limiter."""
    now = time.time()
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < window]
    if len(rate_limit_store[ip]) >= limit:
        return False
    rate_limit_store[ip].append(now)
    return True

# ═══════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════

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

class PasswordResetReq(BaseModel):
    email: str

class PasswordChangeReq(BaseModel):
    current_password: str
    new_password: str

# ═══════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════

app = FastAPI(
    title="Mia's Reminder",
    version="1.0.0",
    docs_url="/docs" if APP_ENV != "production" else None,
    redoc_url=None,
)

# Security headers middleware
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ═══════════════════════════════════════════════
# DEPENDENCIES
# ═══════════════════════════════════════════════

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
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    try:
        result = await db.execute(select(User).where(User.id == uuid_mod.UUID(user_id)))
        user = result.scalar_one_or_none()
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session.")
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled.")
    return user

# ═══════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")
    except Exception as e:
        logger.error(f"Startup error: {e}")

# ═══════════════════════════════════════════════
# HEALTH & INFO
# ═══════════════════════════════════════════════

@app.get("/")
async def root():
    return {"name": "Mia's Reminder", "version": "1.0.0", "status": "running", "env": APP_ENV}

@app.get("/health")
async def health():
    try:
        async with SessionLocal() as db:
            await db.execute(select(User).limit(1))
        return {"status": "healthy", "database": "connected", "ai": "configured" if OPENAI_API_KEY else "not configured"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})

# ═══════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════

@app.post("/api/v1/auth/register")
async def register(data: RegisterReq, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"register:{client_ip}", limit=5, window=300):
        raise HTTPException(status_code=429, detail="Too many attempts. Please wait 5 minutes.")
    
    try:
        # Validate & sanitize
        email = data.email.strip().lower()
        full_name = sanitize_input(data.full_name, 255)
        
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            raise HTTPException(status_code=400, detail="Please enter a valid email address.")
        if len(data.password) < 4:
            raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")
        if not full_name or len(full_name) < 2:
            raise HTTPException(status_code=400, detail="Please enter your name.")

        # Check existing
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="This email is already registered. Try logging in.")
        
        # Create user
        user = User(email=email, full_name=full_name, hashed_password=hash_password(data.password))
        db.add(user)
        await db.flush()
        await db.refresh(user)
        
        access_token = create_token(str(user.id), "access", 60)
        refresh_token = create_token(str(user.id), "refresh", 10080)
        
        logger.info(f"New user: {email}")
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": 3600}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

@app.post("/api/v1/auth/login")
async def login(data: LoginReq, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"login:{client_ip}", limit=10, window=300):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait 5 minutes.")
    
    try:
        email = data.email.strip().lower()
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user or not user.hashed_password:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account disabled. Contact support.")
        
        user.last_login_at = datetime.now(timezone.utc)
        access_token = create_token(str(user.id), "access", 60)
        refresh_token = create_token(str(user.id), "refresh", 10080)
        
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": 3600}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed. Please try again.")

@app.post("/api/v1/auth/refresh")
async def refresh_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated.")
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    new_access = create_token(user_id, "access", 60)
    return {"access_token": new_access, "token_type": "bearer", "expires_in": 3600}

@app.get("/api/v1/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "timezone": user.timezone_str,
        "language": user.language,
        "theme": user.theme,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

@app.post("/api/v1/auth/change-password")
async def change_password(data: PasswordChangeReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    if len(data.new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters.")
    user.hashed_password = hash_password(data.new_password)
    return {"message": "Password changed successfully."}

@app.post("/api/v1/auth/logout")
async def logout():
    return {"message": "Logged out successfully."}

# ═══════════════════════════════════════════════
# AI CHAT
# ═══════════════════════════════════════════════

@app.post("/api/v1/chat/message")
async def chat_message(data: ChatReq, user: User = Depends(get_current_user)):
    content = sanitize_input(data.content, 5000)
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    # Try OpenAI/Gemini if configured, otherwise use built-in Mia
    reply = await get_mia_response(content, user.full_name)
    return _chat_response(reply)


async def get_mia_response(message: str, user_name: str) -> str:
    """Get response from Gemini AI or built-in responses."""
    msg = message.lower().strip()
    
    # Try Google Gemini (FREE)
    if GEMINI_API_KEY:
        try:
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": f"You are Mia, a friendly AI personal assistant. Help {user_name} organize their life with reminders, schedules, to-do lists, and alarms. Be helpful, concise, and warm. Current time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. User says: {message}"}]}],
                "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7}
            }
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    logger.warning(f"Gemini API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"Gemini failed: {e}")
    
    # Try OpenAI if configured
    if OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": f"You are Mia, a friendly AI assistant helping {user_name} organize their life."},
                    {"role": "user", "content": message},
                ],
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI failed: {e}")
    
    # Built-in Mia responses (works without any API key)
    if any(w in msg for w in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return f"Hey {user_name}! I'm Mia, your personal assistant. How can I help you today? I can help with reminders, to-do lists, scheduling, and more!"
    
    if any(w in msg for w in ["remind", "reminder", "don't forget", "remember"]):
        return f"I'd love to set a reminder for you! Tell me:\n\n1. What should I remind you about?\n2. When? (e.g., 'tomorrow at 8 AM')\n\nOr use the Reminders tab to create one directly!"
    
    if any(w in msg for w in ["todo", "to-do", "task", "to do", "list"]):
        return f"Let's organize your tasks! You can:\n\n• Tell me what tasks you need to do\n• I'll help you prioritize them\n• Or go to the Tasks tab to add them directly\n\nWhat do you need to get done?"
    
    if any(w in msg for w in ["schedule", "plan", "calendar", "event", "meeting"]):
        return f"I can help you plan! Tell me about your events or meetings and I'll help organize your day. What's coming up?"
    
    if any(w in msg for w in ["alarm", "wake", "wake up"]):
        return f"I can help with alarms! Tell me what time you'd like to be woken up or reminded, and whether it should repeat daily."
    
    if any(w in msg for w in ["thank", "thanks", "appreciate"]):
        return f"You're welcome, {user_name}! I'm always here to help. Anything else I can do for you?"
    
    if any(w in msg for w in ["how are you", "how do you feel", "what's up"]):
        return f"I'm doing great, thanks for asking! I'm ready to help you stay organized. What can I help you with today?"
    
    if any(w in msg for w in ["help", "what can you do", "features"]):
        return f"Here's what I can help you with:\n\n⏰ **Reminders** - Never forget anything\n✅ **To-Do Lists** - Track your tasks\n📅 **Scheduling** - Plan your days\n🔔 **Alarms** - Wake up on time\n\nJust tell me what you need in plain English!"
    
    if any(w in msg for w in ["study", "exam", "homework", "assignment"]):
        return f"Study time! I can help you:\n\n• Create a study schedule\n• Set reminders for deadlines\n• Break assignments into smaller tasks\n\nWhat subject or assignment do you need help organizing?"
    
    if any(w in msg for w in ["work", "project", "deadline"]):
        return f"Let's manage your work! Tell me about your project or deadline and I'll help you break it down into manageable steps."
    
    if any(w in msg for w in ["tired", "stressed", "overwhelmed"]):
        return f"I hear you, {user_name}. Let me help lighten your load. Tell me what's on your plate and I'll help you prioritize. One step at a time!"
    
    if any(w in msg for w in ["good night", "bye", "goodbye", "see you"]):
        return f"Good night, {user_name}! Sleep well. I'll be here whenever you need me. Don't forget to check your reminders for tomorrow!"
    
    # Default response
    return f"Thanks for your message, {user_name}! I'm here to help you stay organized. You can ask me to:\n\n• Set reminders\n• Create to-do lists\n• Plan your schedule\n• Set alarms\n\nWhat would you like help with?"

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

# ═══════════════════════════════════════════════
# REMINDERS
# ═══════════════════════════════════════════════

@app.get("/api/v1/reminders")
async def list_reminders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reminder).where(Reminder.user_id == str(user.id)).order_by(Reminder.remind_at))
    reminders = result.scalars().all()
    return [{"id": r.id, "title": r.title, "description": r.description, "remind_at": r.remind_at.isoformat() if r.remind_at else None, "status": r.status, "is_persistent": r.is_persistent, "created_at": r.created_at.isoformat() if r.created_at else None} for r in reminders]

@app.post("/api/v1/reminders")
async def create_reminder(data: ReminderReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    title = sanitize_input(data.title, 500)
    if not title:
        raise HTTPException(status_code=400, detail="Title is required.")
    reminder = Reminder(user_id=str(user.id), title=title, description=sanitize_input(data.description or "", 2000), remind_at=datetime.fromisoformat(data.remind_at), is_persistent=data.is_persistent)
    db.add(reminder)
    await db.flush()
    return {"id": reminder.id, "title": reminder.title, "status": "created", "message": "Reminder created!"}

@app.post("/api/v1/reminders/{reminder_id}/done")
async def complete_reminder(reminder_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == str(user.id)))
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    reminder.status = "completed"
    return {"id": reminder.id, "status": "completed"}

@app.delete("/api/v1/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == str(user.id)))
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    await db.delete(reminder)
    return {"message": "Reminder deleted."}

# ═══════════════════════════════════════════════
# TODOS
# ═══════════════════════════════════════════════

@app.get("/api/v1/todos")
async def list_todos(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo).where(Todo.user_id == str(user.id)).order_by(Todo.priority))
    todos = result.scalars().all()
    return {"todos": [{"id": t.id, "title": t.title, "description": t.description, "priority": t.priority, "is_completed": t.is_completed, "due_date": t.due_date.isoformat() if t.due_date else None, "created_at": t.created_at.isoformat() if t.created_at else None} for t in todos], "total": len(todos), "completed": sum(1 for t in todos if t.is_completed), "pending": sum(1 for t in todos if not t.is_completed)}

@app.post("/api/v1/todos")
async def create_todo(data: TodoReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    title = sanitize_input(data.title, 500)
    if not title:
        raise HTTPException(status_code=400, detail="Title is required.")
    todo = Todo(user_id=str(user.id), title=title, description=sanitize_input(data.description or "", 2000), priority=max(1, min(4, data.priority)), due_date=datetime.fromisoformat(data.due_date) if data.due_date else None)
    db.add(todo)
    await db.flush()
    return {"id": todo.id, "title": todo.title, "status": "created", "message": "Task created!"}

@app.post("/api/v1/todos/{todo_id}/complete")
async def complete_todo(todo_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo).where(Todo.id == todo_id, Todo.user_id == str(user.id)))
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="Task not found.")
    todo.is_completed = True
    return {"id": todo.id, "status": "completed"}

@app.delete("/api/v1/todos/{todo_id}")
async def delete_todo(todo_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo).where(Todo.id == todo_id, Todo.user_id == str(user.id)))
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="Task not found.")
    await db.delete(todo)
    return {"message": "Task deleted."}

# ═══════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════

@app.get("/api/v1/dashboard")
async def dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    uid = str(user.id)
    todos_result = await db.execute(select(Todo).where(Todo.user_id == uid))
    todos = todos_result.scalars().all()
    reminders_result = await db.execute(select(Reminder).where(Reminder.user_id == uid, Reminder.status == "active"))
    reminders = reminders_result.scalars().all()
    
    total = len(todos)
    completed = sum(1 for t in todos if t.is_completed)
    
    return {
        "today_events": [],
        "upcoming_reminders": [{"id": r.id, "title": r.title, "remind_at": r.remind_at.isoformat() if r.remind_at else None, "is_persistent": r.is_persistent} for r in reminders[:5]],
        "active_alarms": [],
        "pending_todos": [{"id": t.id, "title": t.title, "priority": t.priority, "due_date": t.due_date.isoformat() if t.due_date else None} for t in todos if not t.is_completed][:10],
        "stats": {
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
            "weekly_completed": completed,
            "active_reminders": len(reminders),
            "today_event_count": 0,
        },
    }

# ═══════════════════════════════════════════════
# ERROR HANDLING
# ═══════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled: {request.method} {request.url.path} - {exc}")
    if APP_ENV == "production":
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})
    return JSONResponse(status_code=500, content={"detail": str(exc)})
