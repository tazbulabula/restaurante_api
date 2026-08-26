# restaurante_api/api/routers/users.py

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from restaurante_api.api.dependencies import UserServiceDep
from restaurante_api.core.dependencies import Current_user
from restaurante_api.schemas.user import (
    UserCreate,
    UserFilterSchema,
    UserList,
    UserPublic,
    UserTypeUpdate,
    UserUpdate,
)
from restaurante_api.services.permission_service import PermissionService

router = APIRouter(prefix='/users', tags=['users'])


# ============================================================
# 1. LISTAR USUÁRIOS (APENAS ADMIN)
# ============================================================
@router.get('/', response_model=UserList)
async def list_users(
    user_service: UserServiceDep,
    current_user: Current_user,
    filters: Annotated[UserFilterSchema, Depends()],
):
    """Lista todos os usuários com filtros (apenas administradores)."""
    PermissionService.require_admin(current_user)
    return await user_service.list_users(filters)


# ============================================================
# 2. LISTAR USUÁRIOS DELETADOS (APENAS ADMIN)
# ============================================================
@router.get('/deleted', response_model=List[UserPublic])
async def list_deleted_users(
    user_service: UserServiceDep,
    current_user: Current_user,
):
    """Lista apenas usuários deletados (soft delete)."""
    PermissionService.require_admin(current_user)
    return await user_service.get_deleted_users()


# ============================================================
# 3. RESTAURAR USUÁRIO (APENAS ADMIN) ✅ NOVA ROTA
# ============================================================
@router.patch('/{public_id}/restore', response_model=UserPublic)
async def restore_user(
    public_id: str,
    user_service: UserServiceDep,
    current_user: Current_user,
):
    """Restaura um usuário deletado (apenas administradores)."""
    PermissionService.require_admin(current_user)

    user = await user_service.restore_user(public_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado ou não está deletado',
        )
    return user


# ============================================================
# 4. DELETAR PERMANENTEMENTE (APENAS ADMIN)
# ============================================================
@router.delete('/{public_id}/permanent')
async def hard_delete_user(
    public_id: str,
    user_service: UserServiceDep,
    current_user: Current_user,
):
    """Remove permanentemente um usuário do banco (apenas administradores)."""
    PermissionService.require_admin(current_user)

    if current_user.public_id == public_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Não é possível deletar permanentemente sua própria conta',
        )

    deleted = await user_service.hard_delete_user(public_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )

    return {'message': 'Usuário removido permanentemente'}


# ============================================================
# 5. BUSCAR USUÁRIO POR PUBLIC_ID (APENAS ADMIN)
# ============================================================
@router.get('/buscar/{public_id}', response_model=UserPublic)
async def get_user_by_public_id(
    public_id: str,
    user_service: UserServiceDep,
    current_user: Current_user,
    include_deleted: Annotated[
        bool, Query(description='Incluir usuários deletados')
    ] = False,
):
    """Busca um usuário pelo public_id (apenas administradores)."""
    PermissionService.require_admin(current_user)

    user = await user_service.get_user_by_public_id(
        public_id,
        include_deleted=include_deleted,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )
    return user


# ============================================================
# 6. ALTERAR TIPO DE USUÁRIO (APENAS ADMIN)
# ============================================================


@router.patch('/{public_id}/tipo', response_model=UserPublic)
async def change_user_type(
    public_id: str,
    data: UserTypeUpdate,
    user_service: UserServiceDep,
    current_user: Current_user,
):
    """Altera o tipo de usuário (admin/client) - apenas administradores."""
    PermissionService.require_admin(current_user)

    if current_user.public_id == public_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Não é possível alterar seu próprio tipo',
        )

    if data.user_type not in {'admin', 'client'}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo inválido. Use 'admin' ou 'client'",
        )

    user = await user_service.change_user_type(public_id, data.user_type)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )
    return user


# ============================================================
# 7. CRIAR USUÁRIO (PÚBLICO)
# ============================================================
@router.post(
    '/create', status_code=status.HTTP_201_CREATED, response_model=UserPublic
)
async def create_user(user: UserCreate, user_service: UserServiceDep):
    try:
        db_user = await user_service.register_user(user)
        return db_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )


# ============================================================
# 8. ATUALIZAR USUÁRIO (ADMIN OU DONO)
# ============================================================
@router.put('/update/{public_id}', response_model=UserPublic)
async def update_user(
    public_id: str,
    user: UserUpdate,
    user_service: UserServiceDep,
    current_user: Current_user,
):
    if current_user.public_id != public_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not enough permissions.',
        )

    try:
        updated_user = await user_service.updated_user(
            public_id=public_id, data=user
        )
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


# ============================================================
# 9. SOFT DELETE (ADMIN OU DONO)
# ============================================================
@router.delete('/delete/{public_id}')
async def delete_user(
    public_id: str,
    user_service: UserServiceDep,
    current_user: Current_user,
):
    """Soft delete: marca o usuário como deletado."""

    PermissionService.require_owner_or_admin(current_user, public_id)

    user = await user_service.soft_delete_user(public_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )

    return {'message': 'Usuário desativado com sucesso'}


# ============================================================
# 10. USUÁRIO ATUAL (AUTENTICADO)
# ============================================================
@router.get('/me', response_model=UserPublic)
async def get_current_user_info(
    current_user: Current_user,
):
    """Retorna o usuário atual autenticado"""
    return current_user
