from http import HTTPStatus

from fastapi import APIRouter, HTTPException

from restaurante_api.api.dependencies import UserServiceDep
from restaurante_api.core.dependencies import Current_user
from restaurante_api.schemas.user import UserCreate, UserPublic, UserUpdate

router = APIRouter(prefix='/users', tags=['users'])


@router.post(
    '/create', status_code=HTTPStatus.CREATED, response_model=UserPublic
)
async def create_user(user: UserCreate, user_service: UserServiceDep):
    try:
        db_user = await user_service.register_user(user)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e))

    return db_user


@router.put('/update/{public_id}', response_model=UserPublic)
async def update_user(
    public_id: str,
    user: UserUpdate,
    user_service: UserServiceDep,
    current_user: Current_user,
):
    if current_user.public_id != public_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions.'
        )

    try:
        updated_user = await user_service.updated_user(
            public_id=public_id, data=user
        )

        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=str(e),
        )


@router.delete('/delete/{public_id}')
async def delete_user(
    public_id: str, user_service: UserServiceDep, current_user: Current_user
):
    if current_user.public_id != public_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions.'
        )

    await user_service.desactive_user(public_id=public_id)

    return {'message': 'User as been deleted.'}
