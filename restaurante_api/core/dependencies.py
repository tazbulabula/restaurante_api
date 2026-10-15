from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from restaurante_api.core.database import get_session
from restaurante_api.core.security import get_current_user
from restaurante_api.models.user import User
from restaurante_api.schemas.produto import ProduceCreate

Current_user = Annotated[User, Depends(get_current_user)]
Session = Annotated[AsyncSession, Depends(get_session)]
Oauth2Form = Annotated[OAuth2PasswordRequestForm, Depends()]
ProduceCreateForm = Annotated[ProduceCreate, Depends(ProduceCreate.as_form)]
