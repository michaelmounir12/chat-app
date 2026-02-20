# Chat API

A production-ready real-time chat backend built with **FastAPI**, **PostgreSQL**, and **Redis**. Supports 1-to-1 and group conversations, WebSocket messaging, read receipts, typing indicators, rate limiting, and message caching.

---

## Features

| Category | Features |
|----------|----------|
| **Auth** | JWT access + refresh tokens, bcrypt password hashing, UUID user IDs |
| **Chat** | 1-to-1 and group conversations, real-time WebSocket messaging |
| **Messages** | Persistence in PostgreSQL, read receipts, read status (sent/delivered/read) |
| **Real-time** | Typing indicators, online user tracking, offline message delivery on connect |
| **Performance** | Redis cache for last 50 messages per conversation, cursor-based pagination |
| **Reliability** | Rate limiting (Redis), centralized error handling, structured logging |
| **Database** | Async SQLAlchemy 2.0, composite indexes for common queries |

---

## Tech Stack

- **Python 3.11**
- **FastAPI** — async API framework
- **PostgreSQL** — primary data store (async via **asyncpg**)
- **Redis** — sessions, rate limiting, message cache, online users, typing state
- **SQLAlchemy 2.0** — async ORM
- **Pydantic v2** — validation and settings
- **Docker** — containerized run

---

## Project Structure

```
app/
├── core/                 # Config, security, middleware, errors
│   ├── config.py         # Settings (env-based)
│   ├── security.py       # JWT, password hashing
│   ├── dependencies.py   # get_db, get_current_user
│   ├── exceptions.py     # Custom exceptions + handlers
│   ├── rate_limit.py     # Redis rate limiting
│   ├── logging_middleware.py
│   └── auth_middleware.py
├── db/                   # Data layer
│   ├── session.py        # Async SQLAlchemy engine & session
│   ├── redis_client.py   # Redis connection
│   └── models.py         # User, Conversation, Message, MessageReadReceipt, ChatRoom, etc.
├── schemas/              # Pydantic request/response models
├── repositories/         # Data access (Repository pattern)
├── services/             # Business logic (no DB in routes)
├── websocket/            # WebSocket connection manager, Redis store, typing
├── api/v1/               # REST + WebSocket routes
│   ├── auth.py
│   ├── users.py
│   ├── chat.py           # Legacy chat rooms
│   ├── conversations.py  # 1-to-1 & group conversations, messages, typing, read receipts
│   └── websocket.py      # WS /conversations/{id}
└── main.py               # App entry, middleware, exception handlers
```

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 16+**
- **Redis 7+**
- **Docker & Docker Compose** (optional, recommended)

---

## Quick Start

### 1. Clone and configure

```bash
cd "d:\chat app python"
cp .env.example .env
```

Edit `.env`: set a strong **SECRET_KEY** (min 32 chars) and adjust `DATABASE_URL` / `REDIS_URL` if needed.

### 2. Run with Docker Compose (recommended)

```bash
docker-compose up -d
```

- API: **http://localhost:8000**
- Docs: **http://localhost:8000/docs**
- Health: **http://localhost:8000/health**

### 3. Run locally (no Docker)

```bash
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

Ensure PostgreSQL and Redis are running, then:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | `Chat API` |
| `DEBUG` | Debug mode | `false` |
| `API_V1_PREFIX` | API path prefix | `/api/v1` |
| **Database** | | |
| `DATABASE_URL` | PostgreSQL URL (asyncpg) | **required** |
| `DB_ECHO` | Log SQL | `false` |
| `DB_POOL_SIZE` | Connection pool size | `5` |
| `DB_MAX_OVERFLOW` | Pool overflow | `10` |
| **Redis** | | |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `REDIS_PASSWORD` | Redis password | — |
| **JWT** | | |
| `SECRET_KEY` | JWT signing key | **required** |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |
| **CORS** | | |
| `CORS_ORIGINS` | Allowed origins | `["http://localhost:3000","http://localhost:8000"]` |
| **Rate limiting** | | |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Per client/minute | `60` |
| `RATE_LIMIT_REQUESTS_PER_HOUR` | Per client/hour | `1000` |
| `RATE_LIMIT_MESSAGE_PER_MINUTE` | Per user messages/min (WS) | `30` |
| **Logging** | | |
| `LOG_LEVEL` | Log level | `INFO` |

---

## API Overview

Base URL: **`/api/v1`**

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register; returns tokens |
| `POST` | `/auth/login` | Login; returns tokens |
| `POST` | `/auth/refresh` | Body: `{ "refresh_token": "..." }`; returns new tokens |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users/me` | Current user (Bearer token) |
| `GET` | `/users/{user_id}` | User by ID |
| `PUT` | `/users/me` | Update current user |
| `DELETE` | `/users/me` | Delete current user |

### Conversations (1-to-1 & group)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/conversations/` | List current user's conversations |
| `GET` | `/conversations/online` | List online user IDs (Redis) |
| `GET` | `/conversations/direct?other_user_id=` | Get or create 1-to-1 |
| `POST` | `/conversations/direct` | Body: `{ "other_user_id": "uuid" }` |
| `POST` | `/conversations/group` | Body: `{ "type": "group", "name": "...", "participant_ids": [...] }` |
| `GET` | `/conversations/{id}` | Get conversation (participant only) |
| `GET` | `/conversations/{id}/messages` | Paginated messages (`cursor`, `limit`, `use_cache`) |
| `POST` | `/conversations/{id}/messages` | Send message (body: `content`, `conversation_id`) |
| `POST` | `/conversations/{id}/read` | Mark conversation as read |
| `POST` | `/conversations/{id}/typing` | Body: `{ "is_typing": true/false }` |
| `GET` | `/conversations/{id}/typing` | Current typing users |
| `POST` | `/conversations/messages/{message_id}/read` | Mark message read (creates receipt) |
| `GET` | `/conversations/messages/{message_id}/read-receipts` | List read receipts |

### Chat rooms (legacy)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/rooms` | Create room |
| `GET` | `/chat/rooms` | My rooms |
| `GET` | `/chat/rooms/{id}` | Room details |
| `PUT` | `/chat/rooms/{id}` | Update room |
| `POST` | `/chat/rooms/{id}/members/{user_id}` | Add member |
| `DELETE` | `/chat/rooms/{id}/members/{user_id}` | Remove member |
| `GET` | `/chat/rooms/{id}/messages` | Room messages |
| `POST` | `/chat/messages` | Send message to room |

### WebSocket

| Endpoint | Query | Description |
|----------|--------|-------------|
| `WS /api/v1/ws/conversations/{conversation_id}` | `token=<JWT>` | Join conversation; receive/send messages and typing |

**Events (client → server):**

- **Send message:** `{ "type": "message", "content": "Hello" }`
- **Typing:** `{ "type": "typing", "is_typing": true }` or `false`

**Events (server → client):**

- `type: "message"` — new message (id, sender_id, content, timestamp, read_status, sender)
- `type: "offline_message"` — unread messages delivered on connect
- `type: "typing_indicator"` — `typing_users` list
- `type: "error"` — e.g. rate limit (`retry_after` seconds)

**Example (browser):**

```javascript
const token = "YOUR_ACCESS_TOKEN";
const convId = "CONVERSATION_UUID";
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/conversations/${convId}?token=${token}`);

ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === "message") console.log("Message:", data.content);
  if (data.type === "typing_indicator") console.log("Typing:", data.typing_users);
};

// Send message
ws.send(JSON.stringify({ type: "message", content: "Hi" }));

// Typing
ws.send(JSON.stringify({ type: "typing", is_typing: true }));
```

---

## Pagination

- **Messages:** `GET /conversations/{id}/messages?limit=50&cursor=<message_uuid>&use_cache=true`
- Response: `{ "messages": [...], "next_cursor": "uuid", "has_more": true }`
- First page can be served from Redis cache (last 50 messages) when `use_cache=true`.

---

## Production Checklist

- [ ] Set **SECRET_KEY** to a long random value (e.g. 32+ chars).
- [ ] Set **DEBUG=false**.
- [ ] Use **HTTPS** and secure **CORS_ORIGINS**.
- [ ] Run DB migrations (e.g. Alembic) instead of `create_all` in production.
- [ ] Tune **DB_POOL_SIZE** / **DB_MAX_OVERFLOW** and **RATE_LIMIT_*** for load.
- [ ] Send logs to a central logging/monitoring service (e.g. Sentry, CloudWatch).

---

## Development

```bash
# Format
black app/
isort app/

# Migrations (Alembic)
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

---

## License

MIT
