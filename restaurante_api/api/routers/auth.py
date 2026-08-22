from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from restaurante_api.api.dependencies import AuthServiceDep
from restaurante_api.core.dependencies import (
    Current_user,
    Oauth2Form,
)
from restaurante_api.core.security import (
    create_access_token,
)
from restaurante_api.schemas.auth import (
    AuthSchema,
    PasswordChangeSchema,
    PasswordResetRequest,
)
from restaurante_api.schemas.Root import RootPublic

router = APIRouter(prefix='/token', tags=['token'])


@router.post('/login', response_model=AuthSchema, status_code=HTTPStatus.OK)
async def auth_login(form_data: Oauth2Form, auth_repo: AuthServiceDep):

    try:
        token = await auth_repo.login(data=form_data)

    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=str(e))

    return token


@router.post('/refresh_token', response_model=AuthSchema)
async def refresh_access_token(user: Current_user):
    new_access_token = create_access_token(
        data={'sub': user.public_id, 'user_type': user.user_type}
    )
    return {'access_token': new_access_token, 'token_type': 'bearer'}


@router.patch('/change_password/{public_id}', response_model=RootPublic)
async def change_new_password(
    public_id: str,
    data_password: PasswordChangeSchema,
    current_user: Current_user,
    auth_service: AuthServiceDep,
):
    try:
        data_password.validate_passwords()

    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))

    try:
        return await auth_service.change_new_password(
            public_id=public_id,
            current_password=current_user.password,
            data_password=data_password,
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))


@router.post('/reset-password')
async def request_reset(
    request: PasswordResetRequest, auth_service: AuthServiceDep
):

    try:
        await auth_service.request_password_reset(request.email)
        await auth_service.token_repo.commit()
        return {'message': 'Email sent'}
    except ValueError as e:
        await auth_service.token_repo.rollback()
        raise HTTPException(400, detail=str(e))
