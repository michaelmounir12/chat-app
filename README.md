# Production-Grade Real-Time Chat Backend

A production-ready FastAPI backend for real-time chat applications with WebSocket support, JWT authentication, PostgreSQL, and Redis.

## Features

- **FastAPI** with async/await support
- **PostgreSQL** database with SQLAlchemy 2.0 (async)
- **Redis** for caching and pub/sub
- **WebSocket** support for real-time messaging
- **JWT** authentication with access and refresh tokens
- **Clean Architecture** with separation of concerns
- **Repository Pattern** for data access
- **Service Layer** for business logic
- **Docker** support with docker-compose

## Architecture

```
app/
├── core/           # Core configuration and utilities
├── db/             # Database models and session management
├── schemas/        # Pydantic schemas for request/response validation
├── repositories/   # Data access layer (Repository pattern)
├── services/       # Business logic layer
├── api/            # API routes and endpoints
└── main.py         # Application entry point
```

## Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker and Docker Compose (optional)

## Setup

### Using Docker Compose (Recommended)

1. Copy `.env.example` to `.env` and update the values:
   ```bash
   cp .env.example .env
   ```

2. Update the `SECRET_KEY` in `.env` with a secure random string (minimum 32 characters)

3. Start all services:
   ```bash
   docker-compose up -d
   ```

4. The API will be available at `http://localhost:8000`

### Manual Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up PostgreSQL and Redis (or use Docker for these services)

4. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

5. Update the `DATABASE_URL` and `REDIS_URL` in `.env` to match your setup

6. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `DATABASE_URL`: PostgreSQL connection string (asyncpg format)
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key (change in production!)
- `DEBUG`: Enable/disable debug mode
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT access token expiration time
- `REFRESH_TOKEN_EXPIRE_DAYS`: JWT refresh token expiration time

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login and get tokens

### Users
- `GET /api/v1/users/me` - Get current user info
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/me` - Update current user
- `DELETE /api/v1/users/me` - Delete current user

### Chat Rooms
- `POST /api/v1/chat/rooms` - Create a chat room
- `GET /api/v1/chat/rooms` - Get user's rooms
- `GET /api/v1/chat/rooms/{room_id}` - Get room details
- `PUT /api/v1/chat/rooms/{room_id}` - Update room
- `POST /api/v1/chat/rooms/{room_id}/members/{member_id}` - Add member
- `DELETE /api/v1/chat/rooms/{room_id}/members/{member_id}` - Remove member

### Messages
- `POST /api/v1/chat/messages` - Send a message
- `GET /api/v1/chat/rooms/{room_id}/messages` - Get room messages

### WebSocket
- `WS /api/v1/ws/chat/{room_id}?token={jwt_token}` - Connect to room WebSocket

## WebSocket Usage

Connect to a chat room WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/chat/1?token=YOUR_JWT_TOKEN');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

ws.send(JSON.stringify({
  content: 'Hello, world!',
  timestamp: new Date().toISOString()
}));
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black app/
isort app/
```

### Database Migrations

For production, use Alembic for migrations:

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Production Considerations

1. **Change SECRET_KEY**: Use a strong, random secret key
2. **Set DEBUG=False**: Disable debug mode in production
3. **Use Environment Variables**: Never commit `.env` files
4. **Database Migrations**: Use Alembic for schema changes
5. **HTTPS**: Use HTTPS in production
6. **Rate Limiting**: Consider adding rate limiting middleware
7. **Monitoring**: Add logging and monitoring (e.g., Sentry)
8. **Database Connection Pooling**: Tune pool settings for your load

## License

MIT
