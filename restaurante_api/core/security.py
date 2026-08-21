from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, decode, encode
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from restaurante_api.core.database import get_session
from restaurante_api.core.settings import Settings
from restaurante_api.models.user import User

settings = Settings()

SECRET_KEY = 'your-secret-key'  # Isso é provisório, vamos ajustar!
pwd_context = PasswordHash.recommended()
oauth2_schema = OAuth2PasswordBearer(
    tokenUrl='token/login', refreshUrl='token/refresh_token'
)
Session = Annotated[AsyncSession, Depends(get_session)]


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(tz=ZoneInfo('UTC')) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({'exp': expire.timestamp()})

    encoded_jwt = encode(to_encode, SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def hash_password(password: str):
    """
    Recebe password em texto plano faz o has.
    :param password:
    :return:
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


async def get_current_user(
    session: Session,
    token: str = Depends(oauth2_schema),
):
    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    try:
        payload = decode(token, SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject_public_id = payload.get('sub')

        if not subject_public_id:
            raise credentials_exception
    except DecodeError:
        raise credentials_exception
    except ExpiredSignatureError:
        raise credentials_exception

    user = await session.scalar(
        select(User).where(User.public_id == subject_public_id)
    )

    if not user:
        raise credentials_exception

    return user
