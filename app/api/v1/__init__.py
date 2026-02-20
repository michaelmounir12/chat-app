from fastapi import APIRouter
from app.api.v1 import auth, users, chat, websocket

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
