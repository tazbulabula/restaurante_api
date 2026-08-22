from typing import Annotated

from fastapi import Depends

from restaurante_api.core.dependencies import Session
from restaurante_api.repositories.token import TokenRepository
from restaurante_api.repositories.user import UserRepository
from restaurante_api.services.auth_service import AuthService
from restaurante_api.services.email_service import EmailService
from restaurante_api.services.user_services import UserService


async def get_user_service(session: Session) -> UserService:
    user_repo = UserRepository(session)
    return UserService(user_repo)


async def get_email_service() -> EmailService:
    return EmailService()


# Dependencies
UserServiceDep = Annotated[UserService, Depends(get_user_service)]

EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]


async def get_auth_service(
    session: Session, email_service: EmailServiceDep
) -> AuthService:
    user_repo = UserRepository(session)
    token_repo = TokenRepository(session)
    return AuthService(user_repo, email_service, token_repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
