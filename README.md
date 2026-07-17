# Mia's Reminder

A production-ready, AI-powered personal assistant application built with Flutter (Web/Android/iOS) and FastAPI backend. Features natural language conversation, intelligent scheduling, persistent reminders, calendar management, and Telegram integration.

## Architecture Overview

```
ai-assistant/          (Mia's Reminder)
├── backend/                  # FastAPI Python backend
│   ├── app/
│   │   ├── ai/              # OpenAI integration & action execution
│   │   ├── api/endpoints/   # REST API routes
│   │   ├── core/            # Config, DB, security, Redis
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── notifications/   # FCM, Telegram, email services
│   │   ├── scheduler/       # APScheduler for reminders/alarms
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic services
│   │   └── telegram/        # Telegram bot handlers
│   ├── alembic/             # Database migrations
│   ├── tests/               # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # Flutter cross-platform app
│   ├── lib/
│   │   ├── config/          # API config, routing
│   │   ├── models/          # Data models
│   │   ├── providers/       # Riverpod state management
│   │   ├── screens/         # UI screens (auth, chat, calendar, etc.)
│   │   ├── services/        # API service, notification service
│   │   ├── theme/           # Material Design 3 theming
│   │   ├── utils/           # Helper utilities
│   │   └── widgets/         # Reusable widgets
│   └── pubspec.yaml
├── docker-compose.yml        # Local development stack
└── README.md
```

## Tech Stack

| Layer          | Technology                        |
|----------------|-----------------------------------|
| Frontend       | Flutter 3.x (Web, Android, iOS)   |
| Backend        | Python 3.11 + FastAPI             |
| Database       | PostgreSQL 16                     |
| Cache          | Redis 7                           |
| AI             | OpenAI GPT-4o                     |
| Auth           | Firebase Authentication           |
| Push Notifs    | Firebase Cloud Messaging (FCM)    |
| Bot            | Telegram Bot API (python-telegram-bot) |
| Scheduling     | APScheduler                       |
| Deployment     | Docker / Railway / Vercel         |

## Features

### AI Chat (ChatGPT-like)
- Natural language understanding
- Context memory per conversation
- Automatic action detection (reminders, events, todos, alarms)
- Follow-up questions for missing info
- Task breakdown and duration estimation
- Schedule conflict detection

### Calendar
- Daily/Weekly/Monthly views
- Recurring events (RRULE)
- Color-coded multiple calendars
- Drag-and-drop scheduling
- Conflict detection

### To-Do Lists
- Priorities (P1-P4)
- Subtasks with progress tracking
- Categories and tags
- Smart sorting
- AI-generated task breakdowns

### Reminders (Persistent Mode)
- One-time and recurring
- **Persistent mode**: keeps reminding every N minutes until "Done" is pressed
- Configurable interval and max duration
- Snooze (5/10/30 min)
- Multi-channel: Push + Telegram + Email

### Alarms
- Multiple types: wake-up, medication, study
- Recurring by weekday
- Custom sounds and vibration
- Snooze with max count

### Telegram Bot
- `/today` - Today's schedule
- `/tomorrow` - Tomorrow's schedule
- `/reminders` - Active reminders
- `/todos` - Pending tasks
- `/ask <question>` - AI conversation
- Inline buttons for Done/Snooze on reminders

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for Flutter web)
- Flutter SDK 3.x
- Docker & Docker Compose
- PostgreSQL 16 (or use Docker)

### Backend Setup

```bash
cd backend
cp .env.example .env
# Edit .env with your keys (OpenAI, Firebase, Telegram)

# With Docker (recommended)
cd ..
docker-compose up -d

# Without Docker
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
python main.py
```

### Frontend Setup

```bash
cd frontend
flutter pub get
flutter run -d chrome     # Web
flutter run -d android    # Android
flutter run -d ios        # iOS
```

### Environment Variables

See `backend/.env.example` for all required configuration.

Key variables:
- `OPENAI_API_KEY` - OpenAI API key for GPT-4o
- `TELEGRAM_BOT_TOKEN` - Telegram bot token from @BotFather
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing secret (generate a strong random string)

## API Documentation

When running in development mode, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Email/password login |
| POST | `/api/v1/auth/oauth` | OAuth via Firebase |
| POST | `/api/v1/chat/message` | Send message to AI |
| GET  | `/api/v1/calendar/events` | List events by date range |
| POST | `/api/v1/calendar/events` | Create event |
| GET  | `/api/v1/todos` | List todos |
| POST | `/api/v1/todos` | Create todo |
| GET  | `/api/v1/reminders` | List reminders |
| POST | `/api/v1/reminders` | Create reminder |
| POST | `/api/v1/reminders/{id}/done` | Mark done |
| POST | `/api/v1/reminders/{id}/snooze` | Snooze |
| GET  | `/api/v1/alarms` | List alarms |
| GET  | `/api/v1/dashboard` | Dashboard data |

## Database Schema

### Core Tables
- `users` - User accounts with settings
- `conversations` - AI chat threads
- `messages` - Individual messages with AI metadata
- `calendars` - Calendar containers
- `calendar_events` - Events with recurrence
- `todos` - Tasks with subtask hierarchy
- `todo_categories` - Task categories
- `reminders` - Reminders with persistence config
- `alarms` - Alarms with recurrence

## Testing

```bash
cd backend
pytest -v
pytest --cov=app tests/
```

## Deployment

### Backend (Railway/Render)
1. Push to GitHub
2. Connect to Railway/Render
3. Set environment variables
4. Deploy with Dockerfile

### Frontend (Vercel)
```bash
cd frontend
flutter build web
# Deploy build/web to Vercel
```

### Production Checklist
- [ ] Set `DEBUG=false`
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure CORS for your domain
- [ ] Set up PostgreSQL with SSL
- [ ] Configure Firebase project
- [ ] Set Telegram webhook URL
- [ ] Enable rate limiting
- [ ] Set up monitoring/logging

## Security

- JWT-based authentication with refresh tokens
- Firebase token verification for OAuth
- Bcrypt password hashing
- Rate limiting (60 req/min default)
- Input validation via Pydantic
- CORS configuration
- SQL injection prevention (SQLAlchemy ORM)
- Non-root Docker containers

## License

MIT
