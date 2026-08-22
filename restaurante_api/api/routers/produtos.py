# restaurante_api/routes/produtos.py

from typing import Annotated, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from restaurante_api.core.dependencies import Current_user, Session
from restaurante_api.models.produto import CategoriaProduto, Produto
from restaurante_api.schemas.produto import (
    ProduceCreate,
    ProduceResponse,
    ProduceUpdate,
)
from restaurante_api.services.permission_service import PermissionService

router = APIRouter(prefix='/produtos', tags=['produtos'])


@router.get(
    '/listar',
    response_model=List[ProduceResponse],
    status_code=status.HTTP_200_OK,
    summary='Listar produtos',
    description="""Retorna todos os produtos""",
)
async def listar_produtos(
    session: Session,
    limit: Annotated[
        int, Query(ge=1, le=100, description='Limite de resultados')
    ] = 50,
    offset: Annotated[int, Query(ge=0, description='Pular N resultados')] = 0,
    disponivel: Annotated[
        Optional[bool],
        Query(description='Filtrar por disponibilidade'),
    ] = None,
    categoria: Annotated[
        Optional[CategoriaProduto],
        Query(description='Filtrar por categoria'),
    ] = None,
):
    """Lista produtos com filtros opcionais"""

    query = select(Produto)

    # Aplica filtros
    if categoria:
        query = query.where(Produto.category == categoria)

    if disponivel is not None:
        query = query.where(Produto.is_available == disponivel)

    # Ordenação e paginação
    query = query.order_by(Produto.name).limit(limit).offset(offset)

    result = await session.execute(query)
    produtos = result.scalars().all()

    return produtos


@router.get(
    '/public/{public_id}',
    response_model=ProduceResponse,
    status_code=status.HTTP_200_OK,
    summary='Buscar produto por Public ID',
    description='Retorna um produto específico pelo seu UUID público',
)
async def buscar_produto_por_public_id(
    public_id: str,
    session: Session,
):
    """Busca um produto pelo public_id (UUID)"""

    query = select(Produto).where(Produto.public_id == public_id)
    result = await session.execute(query)
    produto = result.scalar_one_or_none()

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Produto com Public ID {public_id} não encontrado',
        )

    return produto


@router.post(
    '/create',
    response_model=ProduceResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Criar produto',
    description='Cria um novo produto no cardápio',
)
async def create_product(
    produto_data: ProduceCreate,
    session: Session,
    current_user: Current_user,
):
    """Verifica se o usuário é um admin ou cliente"""
    PermissionService.require_admin(current_user)
    """Cria um novo produto"""

    # Verifica se já existe produto com mesmo nome
    query = select(Produto).where(Produto.name == produto_data.name)
    result = await session.execute(query)
    existente = result.scalar_one_or_none()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Produto com nome '{produto_data.name}' já existe",
        )

    # Cria o produto
    produto = Produto(**produto_data.model_dump())
    session.add(produto)

    try:
        await session.commit()
        await session.refresh(produto)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao criar produto. Verifique os dados.',
        )

    return produto


@router.put(
    '/update/{public_id}',
    response_model=ProduceResponse,
    status_code=status.HTTP_200_OK,
    summary='Atualizar produto',
    description='Atualiza um produto existente pelo ID',
)
async def update_product(
    public_id: str,
    produto_data: ProduceUpdate,
    session: Session,
    current_user: Current_user,
):
    PermissionService.require_admin(current_user)

    """Atualiza um produto existente"""

    query = await session.execute(
        select(Produto).where(Produto.public_id == public_id)
    )
    produto = query.scalar_one_or_none()

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Produto com ID {public_id} não encontrado',
        )

    # Atualiza apenas os campos fornecidos
    update_data = produto_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(produto, field, value)

    try:
        await session.commit()
        await session.refresh(produto)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao atualizar produto. Verifique os dados.',
        )

    return produto


@router.delete(
    '/delete/{public_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Deletar produto',
    description='Remove um produto do cardápio pelo ID',
)
async def deletar_produto(
    public_id: str,
    session: Session,
    current_user: Current_user,
):
    PermissionService.require_admin(current_user)
    """Deleta um produto"""

    query = await session.execute(
        select(Produto).where(Produto.public_id == public_id)
    )
    produto = query.scalar_one_or_none()

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Produto com ID {public_id} não encontrado',
        )

    await session.delete(produto)
    await session.commit()


@router.patch(
    '/{public_id}/disponibilidade',
    response_model=ProduceResponse,
    status_code=status.HTTP_200_OK,
    summary='Alterar disponibilidade',
    description='Ativa ou desativa um produto',
)
async def alternar_disponibilidade(
    public_id: str,
    session: Session,
    current_user: Current_user,
    disponivel: Annotated[
        bool,
        Query(
            ..., description='True para disponível, False para indisponível'
        ),
    ] = None,
):
    PermissionService.require_admin(current_user)

    """Alterna a disponibilidade de um produto"""

    query = await session.execute(
        select(Produto).where(Produto.public_id == public_id)
    )
    produto = query.scalar_one_or_none()

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Produto com ID {public_id} não encontrado',
        )

    produto.is_available = disponivel
    await session.commit()
    await session.refresh(produto)

    return produto
