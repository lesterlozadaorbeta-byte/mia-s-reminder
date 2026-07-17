"""Mia's Reminder API - simplified for reliable deployment."""

import os
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import Column, String, Boolean, DateTime, JSON, text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Setup ---
def get_db_url():
    url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/mias_reminder")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url

engine = create_async_engine(get_db_url(), echo=False, pool_size=10, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# --- User Model (inline) ---
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    auth_provider = Column(String(50), default="email")
    timezone = Column(String(100), default="UTC")
    language = Column(String(10), default="en")
    theme = Column(String(20), default="system")
    telegram_chat_id = Column(String(100), nullable=True)
    notification_preferences = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime(timezone=True), nullable=True)

# --- Security ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(user_id: str, minutes: int = 30) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

# --- Schemas ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800

class ChatRequest(BaseModel):
    content: str

# --- App ---
app = FastAPI(title="Mia's Reminder", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

# --- Routes ---
@app.get("/")
async def root():
    return {"name": "Mia's Reminder", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()
    
    token = create_token(str(user.id))
    refresh = create_token(str(user.id), minutes=10080)
    
    return TokenResponse(access_token=token, refresh_token=refresh)

@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user.last_login_at = datetime.now(timezone.utc)
    token = create_token(str(user.id))
    refresh = create_token(str(user.id), minutes=10080)
    
    return TokenResponse(access_token=token, refresh_token=refresh)

@app.post("/api/v1/chat/message")
async def chat_message(data: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI Chat endpoint - uses OpenAI."""
    from openai import AsyncOpenAI
    
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        return {"message": {"id": str(uuid.uuid4()), "conversation_id": str(uuid.uuid4()), "role": "assistant", "content": "AI is not configured yet. Please add your OpenAI API key.", "intent_detected": None, "actions_taken": [], "created_at": datetime.now(timezone.utc).isoformat()}, "actions": [], "follow_up_questions": []}
    
    client = AsyncOpenAI(api_key=openai_key)
    
    try:
        response = await client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": "You are Mia, a friendly AI personal assistant. You help users organize their life with reminders, schedules, to-do lists, and alarms. Be helpful, concise, and warm."},
                {"role": "user", "content": data.content},
            ],
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Sorry, I encountered an error: {str(e)}"
    
    return {
        "message": {
            "id": str(uuid.uuid4()),
            "conversation_id": str(uuid.uuid4()),
            "role": "assistant",
            "content": reply,
            "intent_detected": None,
            "actions_taken": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "actions": [],
        "follow_up_questions": [],
    }

@app.get("/api/v1/auth/me")
async def get_me():
    return {"message": "Auth required"}
