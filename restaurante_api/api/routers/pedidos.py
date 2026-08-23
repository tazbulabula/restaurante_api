# restaurante_api/routes/pedidos.py

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from restaurante_api.core.dependencies import Current_user, Session
from restaurante_api.models import ItemPedido
from restaurante_api.models.mesa import StatusMesa
from restaurante_api.models.pedido import Pedido, StatusPedido
from restaurante_api.models.produto import Produto
from restaurante_api.models.reserva_mesa import ReservaMesa
from restaurante_api.models.user import User
from restaurante_api.schemas.item_pedido import ItemPedidoDetalhadoResponse
from restaurante_api.schemas.pedido import (
    PedidoCreate,
    PedidoDetalhadoResponse,
    PedidoFiltros,
    PedidoResponse,
    PedidoStatusUpdate,
    PedidoUpdate,
)
from restaurante_api.schemas.user import UserType
from restaurante_api.services.permission_service import PermissionService

router = APIRouter(prefix='/pedidos', tags=['pedidos'])


# ============================================================
# 1. LISTAR PEDIDOS
# ============================================================
@router.get(
    '/',
    response_model=List[PedidoResponse],
    status_code=status.HTTP_200_OK,
    summary='Listar pedidos',
    description='Lista pedidos com filtros',
)
async def listar_pedidos(
    session: Session,
    current_user: Current_user,
    filtros: Annotated[PedidoFiltros, Depends()],
):
    """Lista pedidos com filtros"""
    query = select(Pedido)

    # Admin vê todos, usuário comum vê apenas os próprios
    if current_user.user_type != UserType.ADMIN:
        query = query.where(Pedido.usuario_id == current_user.id)

    if filtros.status:
        query = query.where(Pedido.status == filtros.status)

    if filtros.origem:
        query = query.where(Pedido.origem == filtros.origem)

    if filtros.data_inicio:
        query = query.where(Pedido.created_at >= filtros.data_inicio)

    if filtros.data_fim:
        query = query.where(Pedido.created_at <= filtros.data_fim)

    query = query.order_by(Pedido.created_at.desc())
    query = query.limit(filtros.limit).offset(filtros.offset)

    result = await session.execute(query)
    return result.scalars().all()


# ============================================================
# 2. BUSCAR PEDIDO POR PUBLIC_ID
# ============================================================
@router.get(
    '/{public_id}',
    response_model=PedidoDetalhadoResponse,
    status_code=status.HTTP_200_OK,
    summary='Buscar pedido por Public ID',
    description='Retorna os detalhes de um pedido específico',
)
async def buscar_pedido_por_public_id(
    public_id: str,
    session: Session,
    current_user: Current_user,
):
    """Busca um pedido pelo public_id"""
    query = select(Pedido).where(Pedido.public_id == public_id)
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Pedido com Public ID {public_id} não encontrado',
        )

    # Verifica permissão: admin ou dono do pedido
    PermissionService.require_owner_or_admin(current_user, pedido.usuario_id)

    # Busca nome do usuário
    usuario_nome = None
    if pedido.usuario_id:
        user_query = select(User).where(User.id == pedido.usuario_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        usuario_nome = user.username if user else None

    # Busca detalhes dos itens
    itens_detalhados = []
    for item in pedido.itens:
        produto = await session.get(Produto, item.produto_id)
        itens_detalhados.append(
            ItemPedidoDetalhadoResponse(
                **item.__dict__,
                produto_nome=produto.name if produto else None,
                produto_categoria=produto.category.value if produto else None,
            )
        )

    return PedidoDetalhadoResponse(
        **pedido.__dict__,
        usuario_nome=usuario_nome,
        itens_detalhados=itens_detalhados,
    )


# ============================================================
# 3. CRIAR PEDIDO
# ============================================================
@router.post(
    '/',
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Criar pedido',
    description='Cria um novo pedido com seus itens',
)
async def criar_pedido(
    pedido_data: PedidoCreate,
    session: Session,
    current_user: Current_user,
):
    """Cria um novo pedido com itens"""
    total = 0.0
    itens_pedido = []

    # Valida e processa os itens
    for item_data in pedido_data.itens:
        produto = await session.get(Produto, item_data.produto_id)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Produto com ID {item_data.produto_id} não encontrado',
            )

        if not produto.is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'Produto "{produto.name}" não está disponível',
            )

        subtotal = produto.price * item_data.quantidade
        total += subtotal

        itens_pedido.append({
            'produto_id': item_data.produto_id,
            'quantidade': item_data.quantidade,
            'preco_unitario': produto.price,
            'subtotal': subtotal,
            'observacoes': item_data.observacoes,
        })

    # Verifica se a reserva existe (se fornecida)
    if pedido_data.reserva_mesa_id:
        reserva = await session.get(ReservaMesa, pedido_data.reserva_mesa_id)
        if not reserva:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Reserva não encontrada',
            )
        if reserva.status != StatusMesa.RESERVADA:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Reserva não está mais disponível',
            )

    # Cria o pedido
    v = current_user.user_type != 'CONVIDADO'
    pedido = Pedido(
        mesa_numero=pedido_data.mesa_numero,
        cliente_nome=pedido_data.cliente_nome,
        cliente_telefone=pedido_data.cliente_telefone,
        cliente_tipo=pedido_data.cliente_tipo,
        observacoes=pedido_data.observacoes,
        origem=pedido_data.origem,
        usuario_id=current_user.id if v else pedido_data.usuario_id,
        reserva_mesa_id=pedido_data.reserva_mesa_id,
        total=total,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    )
    session.add(pedido)
    await session.flush()  # Para obter o ID do pedido

    # Cria os itens do pedido
    for item_data in itens_pedido:
        item = ItemPedido(pedido_id=pedido.id, **item_data)
        session.add(item)

    # Atualiza o status da reserva se existir
    if pedido_data.reserva_mesa_id:
        reserva = await session.get(ReservaMesa, pedido_data.reserva_mesa_id)
        if reserva:
            reserva.status = StatusMesa.CONFIRMADA
            reserva.pedido_id = pedido.id

    try:
        await session.commit()
        await session.refresh(pedido)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao criar pedido. Verifique os dados.',
        )

    return pedido


# ============================================================
# 4. ATUALIZAR PEDIDO
# ============================================================
@router.put(
    '/{public_id}',
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    summary='Atualizar pedido',
    description='Atualiza um pedido existente (apenas admin ou dono)',
)
async def atualizar_pedido(
    public_id: str,
    pedido_data: PedidoUpdate,
    session: Session,
    current_user: Current_user,
):
    """Atualiza um pedido existente"""
    query = select(Pedido).where(Pedido.public_id == public_id)
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Pedido com Public ID {public_id} não encontrado',
        )

    # Verifica permissão: admin ou dono do pedido
    PermissionService.require_owner_or_admin(current_user, pedido.usuario_id)

    update_data = pedido_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(pedido, field, value)

    try:
        await session.commit()
        await session.refresh(pedido)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao atualizar pedido. Verifique os dados.',
        )

    return pedido


# ============================================================
# 5. ATUALIZAR STATUS DO PEDIDO
# ============================================================
@router.patch(
    '/{public_id}/status',
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    summary='Atualizar status do pedido',
    description='Atualiza o status de um pedido (apenas admin)',
)
async def atualizar_status_pedido(
    public_id: str,
    status_data: PedidoStatusUpdate,
    session: Session,
    current_user: Current_user,
):
    """Atualiza o status de um pedido"""
    PermissionService.require_admin(current_user)

    query = select(Pedido).where(Pedido.public_id == public_id)
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Pedido com Public ID {public_id} não encontrado',
        )

    pedido.status = status_data.status

    # Se o pedido for cancelado, libera a reserva se existir
    if status_data.status == StatusPedido.CANCELADO and pedido.reserva_mesa_id:
        reserva = await session.get(ReservaMesa, pedido.reserva_mesa_id)
        if reserva:
            reserva.status = StatusMesa.DISPONIVEL

    try:
        await session.commit()
        await session.refresh(pedido)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao atualizar status do pedido.',
        )

    return pedido


# ============================================================
# 6. MEUS PEDIDOS (USUÁRIO COMUM)
# ============================================================
@router.get(
    '/listar/meus',
    response_model=List[PedidoResponse],
    status_code=status.HTTP_200_OK,
    summary='Meus pedidos',
    description='Lista os pedidos do usuário autenticado',
)
async def meus_pedidos(
    session: Session,
    current_user: Current_user,
    status_pedido: Annotated[
        Optional[StatusPedido], Query(description='Filtrar por status')
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Lista os pedidos do usuário atual"""
    query = select(Pedido).where(Pedido.usuario_id == current_user.id)

    if status_pedido:
        query = query.where(Pedido.status == status_pedido)

    query = query.order_by(Pedido.created_at.desc())
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)

    return result.scalars().all()


# ============================================================
# 7. CANCELAR PEDIDO
# ============================================================
@router.patch(
    '/{public_id}/cancelar',
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    summary='Cancelar pedido',
    description='Cancela um pedido (apenas admin ou dono)',
)
async def cancelar_pedido(
    public_id: str,
    session: Session,
    current_user: Current_user,
):
    """Cancela um pedido"""
    query = select(Pedido).where(Pedido.public_id == public_id)
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Pedido com Public ID {public_id} não encontrado',
        )

    # Verifica permissão: admin ou dono do pedido
    PermissionService.require_owner_or_admin(current_user, pedido.usuario_id)

    # Não permite cancelar se já foi entregue
    if pedido.status in {StatusPedido.ENTREGUE}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Não é possível cancelar um pedido já entregue',
        )

    pedido.status = StatusPedido.CANCELADO

    # Libera a reserva se existir
    if pedido.reserva_mesa_id:
        reserva = await session.get(ReservaMesa, pedido.reserva_mesa_id)
        if reserva:
            reserva.status = StatusMesa.DISPONIVEL

    try:
        await session.commit()
        await session.refresh(pedido)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao cancelar pedido.',
        )

    return pedido
