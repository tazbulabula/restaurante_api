# restaurante_api/routes/reservas.py

from datetime import datetime, timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError

from restaurante_api.core.dependencies import Current_user, Session
from restaurante_api.models.mesa import Mesa, StatusMesa
from restaurante_api.models.reserva_mesa import ReservaMesa
from restaurante_api.models.user import User
from restaurante_api.schemas.reserva_mesa import (
    ReservaFiltros,
    ReservaMesaCancelarResponse,
    ReservaMesaCreate,
    ReservaMesaDetalhadaResponse,
    ReservaMesaResponse,
    ReservaMesaUpdate,
)
from restaurante_api.schemas.user import UserType
from restaurante_api.services.permission_service import PermissionService

router = APIRouter(prefix='/reservas', tags=['reservas'])


# ============================================================
# 1. LISTAR RESERVAS (ADMIN ou PRÓPRIAS)
# ============================================================
@router.get(
    '/',
    response_model=List[ReservaMesaResponse],
    status_code=status.HTTP_200_OK,
    summary='Listar reservas',
    description='Lista das reservas',
)
async def listar_reservas(
    session: Session,
    current_user: Current_user,
    filtros: Annotated[ReservaFiltros, Depends()],
):
    """Lista reservas com filtros"""
    query = select(ReservaMesa)

    # Admin vê todas, usuário comum vê apenas as próprias
    if current_user.user_type != UserType.ADMIN:
        query = query.where(ReservaMesa.usuario_id == current_user.id)
        # Se não tiver usuário_id, é convidado - só admin pode ver

    if filtros.status_reserva:
        query = query.where(ReservaMesa.status == filtros.status_reserva)

    if filtros.data_inicio:
        query = query.where(ReservaMesa.data_hora >= filtros.data_inicio)

    if filtros.data_fim:
        query = query.where(ReservaMesa.data_hora <= filtros.data_fim)

    query = query.order_by(ReservaMesa.data_hora)
    query = query.limit(filtros.limit).offset(filtros.offset)

    result = await session.execute(query)

    return result.scalars().all()


# ============================================================
# 2. BUSCAR RESERVA POR PUBLIC_ID
# ============================================================
@router.get(
    '/{public_id}',
    response_model=ReservaMesaDetalhadaResponse,
    status_code=status.HTTP_200_OK,
    summary='Buscar reserva por Public ID',
    description='Retorna os detalhes de uma reserva específica',
)
async def buscar_reserva_por_public_id(
    public_id: str,
    session: Session,
    current_user: Current_user,
):
    """Busca uma reserva pelo public_id"""
    query = select(ReservaMesa).where(ReservaMesa.public_id == public_id)
    result = await session.execute(query)
    reserva = result.scalar_one_or_none()

    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Reserva com Public ID {public_id} não encontrada',
        )

    # Verifica permissão: admin ou dono da reserva
    PermissionService.require_owner_or_admin(current_user, reserva.usuario_id)

    # Busca dados da mesa e do usuário para enriquecer a resposta
    mesa_query = select(Mesa).where(Mesa.id == reserva.mesa_id)
    mesa_result = await session.execute(mesa_query)
    mesa = mesa_result.scalar_one_or_none()

    usuario_nome = None
    if reserva.usuario_id:
        user_query = select(User).where(User.id == reserva.usuario_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        usuario_nome = user.username if user else None

    return ReservaMesaDetalhadaResponse(
        **reserva.__dict__,
        mesa_numero=mesa.numero if mesa else None,
        mesa_capacidade=mesa.capacidade if mesa else None,
        usuario_nome=usuario_nome,
    )


# ============================================================
# 3. CRIAR RESERVA
# ============================================================
@router.post(
    '/',
    response_model=ReservaMesaResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Criar reserva',
    description='Cria uma nova reserva de mesa',
)
async def criar_reserva(
    reserva_data: ReservaMesaCreate,
    session: Session,
    current_user: Current_user,
):
    """Cria uma nova reserva de mesa"""

    # Verifica se a mesa existe
    mesa = await session.get(Mesa, reserva_data.mesa_id)
    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Mesa não encontrada',
        )

    # Verifica se a mesa está disponível
    if mesa.status != StatusMesa.DISPONIVEL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Mesa {mesa.numero} não está disponível',
        )

    # Verifica capacidade
    m = f'Mesa {mesa.numero} tem capacidade para {mesa.capacidade} pessoas'
    if mesa.capacidade < reserva_data.numero_pessoas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=m,
        )

    # Verifica conflito de horário
    duracao_minutos = 60  # Duração padrão da reserva
    fim_reserva = reserva_data.data_hora + timedelta(minutes=duracao_minutos)

    query = select(ReservaMesa).where(
        and_(
            ReservaMesa.mesa_id == reserva_data.mesa_id,
            ReservaMesa.status.in_([StatusMesa.RESERVADA, StatusMesa.OCUPADA]),
            or_(
                # Reserva que começa dentro do período
                and_(
                    ReservaMesa.data_hora >= reserva_data.data_hora,
                    ReservaMesa.data_hora < fim_reserva,
                ),
                # Reserva que termina dentro do período
                and_(
                    ReservaMesa.data_hora <= reserva_data.data_hora,
                    ReservaMesa.expira_em > reserva_data.data_hora,
                ),
            ),
        )
    )
    result = await session.execute(query)
    reserva_existente = result.scalar_one_or_none()

    if reserva_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Já existe uma reserva para esta mesa neste horário',
        )

    # Cria a reserva com timeout de 15 minutos
    expira_em = datetime.now() + timedelta(minutes=15)
    c = current_user.user_type != UserType.CLIENT
    reserva = ReservaMesa(
        mesa_id=reserva_data.mesa_id,
        usuario_id=current_user.id if c else None,
        cliente_nome=reserva_data.cliente_nome,
        cliente_telefone=reserva_data.cliente_telefone,
        data_hora=reserva_data.data_hora,
        numero_pessoas=reserva_data.numero_pessoas,
        observacoes=reserva_data.observacoes,
        expira_em=expira_em,
        status=StatusMesa.RESERVADA,
    )
    session.add(reserva)

    # Atualiza o status da mesa
    mesa.status = StatusMesa.RESERVADA

    try:
        await session.commit()
        await session.refresh(reserva)
        await session.refresh(mesa)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao criar reserva. Verifique os dados.',
        )

    return reserva


# ============================================================
# 4. ATUALIZAR RESERVA
# ============================================================
@router.put(
    '/{public_id}',
    response_model=ReservaMesaResponse,
    status_code=status.HTTP_200_OK,
    summary='Atualizar reserva',
    description='Atualiza uma reserva existente (apenas o dono ou admin)',
)
async def atualizar_reserva(
    public_id: str,
    reserva_data: ReservaMesaUpdate,
    session: Session,
    current_user: Current_user,
):
    """Atualiza uma reserva existente"""
    query = select(ReservaMesa).where(ReservaMesa.public_id == public_id)
    result = await session.execute(query)
    reserva = result.scalar_one_or_none()

    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Reserva com Public ID {public_id} não encontrada',
        )

    # Verifica permissão: admin ou dono da reserva
    PermissionService.require_owner_or_admin(current_user, reserva.usuario_id)

    # Não permite alterar se a reserva já foi confirmada ou expirou
    m = 'É impossível alterar uma reserva que já foi confirmada ou finalizada'
    if reserva.status in {StatusMesa.OCUPADA, StatusMesa.INDISPONIVEL}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=m,
        )

    update_data = reserva_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(reserva, field, value)

    try:
        await session.commit()
        await session.refresh(reserva)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao atualizar reserva. Verifique os dados.',
        )

    return reserva


# ============================================================
# 5. CANCELAR RESERVA
# ============================================================
@router.patch(
    '/{public_id}/cancelar',
    response_model=ReservaMesaCancelarResponse,
    status_code=status.HTTP_200_OK,
    summary='Cancelar reserva',
    description='Cancela uma reserva existente (apenas o dono ou admin)',
)
async def cancelar_reserva(
    public_id: str,
    session: Session,
    current_user: Current_user,
):
    """Cancela uma reserva e libera a mesa"""
    query = select(ReservaMesa).where(ReservaMesa.public_id == public_id)
    result = await session.execute(query)
    reserva = result.scalar_one_or_none()

    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Reserva com Public ID {public_id} não encontrada',
        )

    # Verifica permissão: admin ou dono da reserva
    PermissionService.require_owner_or_admin(current_user, reserva.usuario_id)

    # Não permite cancelar se já foi confirmada ou finalizada
    m = 'Não é possível cancelar uma reserva já confirmada ou finalizada'
    if reserva.status in {StatusMesa.OCUPADA, StatusMesa.INDISPONIVEL}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=m,
        )

    # Atualiza status da reserva e da mesa
    reserva.status = StatusMesa.DISPONIVEL
    await session.commit()
    await session.refresh(reserva)

    # Libera a mesa
    mesa = await session.get(Mesa, reserva.mesa_id)
    if mesa:
        mesa.status = StatusMesa.DISPONIVEL
        await session.commit()
        await session.refresh(mesa)

    return ReservaMesaCancelarResponse(
        message='Reserva cancelada com sucesso',
        reserva_id=reserva.id,
        status=reserva.status,
    )


# ============================================================
# 6. MINHAS RESERVAS (USUÁRIO COMUM)
# ============================================================
@router.get(
    '/minhas',
    response_model=List[ReservaMesaResponse],
    status_code=status.HTTP_200_OK,
    summary='Minhas reservas',
    description='Lista as reservas do usuário autenticado',
)
async def minhas_reservas(
    session: Session,
    current_user: Current_user,
    status_reserva: Annotated[
        Optional[StatusMesa], Query(description='Filtrar por status')
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Lista as reservas do usuário atual"""
    query = select(ReservaMesa).where(
        ReservaMesa.usuario_id == current_user.id
    )

    if status_reserva:
        query = query.where(ReservaMesa.status == status_reserva)

    query = query.order_by(ReservaMesa.data_hora).limit(limit).offset(offset)

    result = await session.execute(query)
    return result.scalars().all()


# ============================================================
# 7. VERIFICAR RESERVAS POR MESA
# ============================================================
@router.get(
    '/mesa/{mesa_id}',
    response_model=List[ReservaMesaResponse],
    status_code=status.HTTP_200_OK,
    summary='Reservas de uma mesa',
    description='Lista todas as reservas de uma mesa específica',
)
async def reservas_por_mesa(
    mesa_id: int,
    session: Session,
    current_user: Current_user,
    data_inicio: Annotated[
        Optional[datetime], Query(description='Data inicial')
    ] = None,
    data_fim: Annotated[
        Optional[datetime], Query(description='Data final')
    ] = None,
):
    """Lista reservas de uma mesa específica (apenas admin)"""
    PermissionService.require_admin(current_user)

    # Verifica se a mesa existe
    mesa = await session.get(Mesa, mesa_id)
    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Mesa não encontrada',
        )

    query = select(ReservaMesa).where(ReservaMesa.mesa_id == mesa_id)

    if data_inicio:
        query = query.where(ReservaMesa.data_hora >= data_inicio)

    if data_fim:
        query = query.where(ReservaMesa.data_hora <= data_fim)

    query = query.order_by(ReservaMesa.data_hora)

    result = await session.execute(query)
    return result.scalars().all()
