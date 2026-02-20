from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.schemas.auth import Token
from app.core.security import create_access_token, create_refresh_token
from app.schemas.user import UserLogin


class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_service = UserService(db)
    
    async def login(self, credentials: UserLogin) -> Token:
        user = await self.user_service.authenticate_user(credentials.email, credentials.password)
        
        if not user:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_refresh_token(data={"sub": user.id})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    async def register(self, user_data):
        user = await self.user_service.create_user(user_data)
        
        access_token = create_access_token(data={"sub": user.id})
        refresh_token = create_refresh_token(data={"sub": user.id})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        ), user
