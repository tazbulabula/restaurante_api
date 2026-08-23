# restaurante_api/routes/mesas.py

from datetime import timedelta
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError

from restaurante_api.core.dependencies import Current_user, Session
from restaurante_api.models.mesa import Mesa, StatusMesa
from restaurante_api.models.reserva_mesa import ReservaMesa
from restaurante_api.schemas.mesa import (
    MesaCreate,
    MesaDisponivelResponse,
    MesaFiltros,
    MesaResponse,
    MesaUpdate,
    VerificarDisponibilidadeRequest,
    VerificarDisponibilidadeResponse,
)
from restaurante_api.services.permission_service import PermissionService

router = APIRouter(prefix='/mesas', tags=['mesas'])


# ============================================================
# 1. LISTAR MESAS (PÚBLICO)
# ============================================================
@router.get(
    '/',
    response_model=List[MesaResponse],
    status_code=status.HTTP_200_OK,
    summary='Listar mesas',
    description='Retorna todas as mesas com filtros opcionais',
)
async def listar_mesas(
    session: Session, filtros: Annotated[MesaFiltros, Depends()]
):
    """Lista mesas com filtros opcionais"""
    query = select(Mesa)

    if filtros.status_mesa:
        query = query.where(Mesa.status == filtros.status_mesa)

    if filtros.tipo:
        query = query.where(Mesa.tipo == filtros.tipo)

    if filtros.disponivel is not None:
        query = query.where(Mesa.is_active == filtros.disponivel)

    query = query.order_by(Mesa.numero)
    query = query.limit(filtros.limit).offset(filtros.offset)
    result = await session.execute(query)
    return result.scalars().all()


# ============================================================
# 2. BUSCAR MESA POR ID (PÚBLICO)
# ============================================================
@router.get(
    '/{mesa_id}',
    response_model=MesaResponse,
    status_code=status.HTTP_200_OK,
    summary='Buscar mesa por ID',
    description='Retorna uma mesa específica pelo ID numérico',
)
async def buscar_mesa_por_id(
    mesa_id: int,
    session: Session,
):
    mesa = await session.get(Mesa, mesa_id)

    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Mesa com ID {mesa_id} não encontrada',
        )

    return mesa


# ============================================================
# 3. BUSCAR MESA POR PUBLIC ID (PÚBLICO)
# ============================================================
@router.get(
    '/public/{public_id}',
    response_model=MesaResponse,
    status_code=status.HTTP_200_OK,
    summary='Buscar mesa por Public ID',
    description='Retorna uma mesa específica pelo UUID público',
)
async def buscar_mesa_por_public_id(
    public_id: str,
    session: Session,
):
    query = select(Mesa).where(Mesa.public_id == public_id)
    result = await session.execute(query)
    mesa = result.scalar_one_or_none()

    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Mesa com Public ID {public_id} não encontrada',
        )

    return mesa


# ============================================================
# 4. BUSCAR POR NÚMERO (PÚBLICO)
# ============================================================
@router.get(
    '/numero/{numero}',
    response_model=MesaResponse,
    status_code=status.HTTP_200_OK,
    summary='Buscar mesa por número',
    description='Retorna uma mesa específica pelo número da mesa',
)
async def buscar_mesa_por_numero(
    numero: int,
    session: Session,
):
    query = select(Mesa).where(Mesa.numero == numero)
    result = await session.execute(query)
    mesa = result.scalar_one_or_none()

    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Mesa número {numero} não encontrada',
        )

    return mesa


# ============================================================
# 5. VERIFICAR DISPONIBILIDADE (PÚBLICO)
# ============================================================
@router.post(
    '/disponibilidade',
    response_model=VerificarDisponibilidadeResponse,
    status_code=status.HTTP_200_OK,
    summary='Verificar disponibilidade de mesas',
    description='Verifica quais mesas estão disponíveis',
)
async def verificar_disponibilidade(
    request: VerificarDisponibilidadeRequest,
    session: Session,
):
    """Verifica mesas disponíveis para um horário específico"""

    # Calcula o fim da reserva (início + duração)
    fim_reserva = request.data_hora + timedelta(
        minutes=request.duracao_minutos
    )

    # Busca reservas que conflitam com o horário solicitado
    query_reservas = select(ReservaMesa).where(
        and_(
            ReservaMesa.status.in_([StatusMesa.RESERVADA, StatusMesa.OCUPADA]),
            or_(
                # Reserva começa dentro do período solicitado
                and_(
                    ReservaMesa.data_hora >= request.data_hora,
                    ReservaMesa.data_hora < fim_reserva,
                ),
                # Reserva termina dentro do período solicitado
                and_(
                    ReservaMesa.data_hora <= request.data_hora,
                    ReservaMesa.expira_em > request.data_hora,
                ),
            ),
        )
    )
    result = await session.execute(query_reservas)
    reservas_conflitantes = result.scalars().all()

    mesas_ocupadas = {r.mesa_id for r in reservas_conflitantes}

    # Busca todas as mesas ativas
    query_mesas = (
        select(Mesa)
        .where(
            and_(
                Mesa.is_active,
                Mesa.status != StatusMesa.INDISPONIVEL,
                Mesa.capacidade >= request.numero_pessoas,
            )
        )
        .order_by(Mesa.capacidade)
    )

    result = await session.execute(query_mesas)
    todas_mesas = result.scalars().all()

    # Filtra mesas disponíveis
    mesas_disponiveis = [
        mesa for mesa in todas_mesas if mesa.id not in mesas_ocupadas
    ]

    # Converte para response
    mesas_response = [
        MesaDisponivelResponse(
            id=m.id,
            public_id=m.public_id,
            numero=m.numero,
            capacidade=m.capacidade,
            tipo=m.tipo,
            localizacao=m.localizacao,
            status=m.status,
        )
        for m in mesas_disponiveis
    ]

    return VerificarDisponibilidadeResponse(
        disponivel=len(mesas_disponiveis) > 0,
        mesas_disponiveis=mesas_response,
    )


# ============================================================
# 6. CRIAR MESA (ADMIN)
# ============================================================
@router.post(
    '/',
    response_model=MesaResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Criar mesa',
    description='Cria uma nova mesa (apenas administradores)',
)
async def criar_mesa(
    mesa_data: MesaCreate,
    session: Session,
    current_user: Current_user,
):
    PermissionService.require_admin(current_user)

    # Verifica se já existe mesa com mesmo número
    query = select(Mesa).where(Mesa.numero == mesa_data.numero)
    result = await session.execute(query)
    existente = result.scalar_one_or_none()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Já existe uma mesa com o número {mesa_data.numero}',
        )

    mesa = Mesa(**mesa_data.model_dump())
    session.add(mesa)

    try:
        await session.commit()
        await session.refresh(mesa)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao criar mesa. Verifique os dados.',
        )

    return mesa


# ============================================================
# 7. ATUALIZAR MESA (ADMIN)
# ============================================================
@router.put(
    '/{public_id}',
    response_model=MesaResponse,
    status_code=status.HTTP_200_OK,
    summary='Atualizar mesa',
    description='Atualiza uma mesa existente (apenas administradores)',
)
async def atualizar_mesa(
    public_id: str,
    mesa_data: MesaUpdate,
    session: Session,
    current_user: Current_user,
):
    PermissionService.require_admin(current_user)

    query = select(Mesa).where(Mesa.public_id == public_id)
    result = await session.execute(query)
    mesa = result.scalar_one_or_none()

    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Mesa com Public ID {public_id} não encontrada',
        )

    update_data = mesa_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(mesa, field, value)

    try:
        await session.commit()
        await session.refresh(mesa)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Erro ao atualizar mesa. Verifique os dados.',
        )

    return mesa


# ============================================================
# 8. DELETAR MESA (ADMIN)
# ============================================================
@router.delete(
    '/{public_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Deletar mesa',
    description='Remove uma mesa do sistema (apenas administradores)',
)
async def deletar_mesa(
    public_id: str,
    session: Session,
    current_user: Current_user,
):
    PermissionService.require_admin(current_user)

    query = select(Mesa).where(Mesa.public_id == public_id)
    result = await session.execute(query)
    mesa = result.scalar_one_or_none()

    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Mesa com Public ID {public_id} não encontrada',
        )

    # Verifica se a mesa tem reservas ativas
    query_reservas = select(ReservaMesa).where(
        and_(
            ReservaMesa.mesa_id == mesa.id,
            ReservaMesa.status.in_([StatusMesa.RESERVADA, StatusMesa.OCUPADA]),
        )
    )
    result = await session.execute(query_reservas)
    reservas_ativas = result.scalars().all()

    if reservas_ativas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Não é possível deletar uma mesa com reservas ativas',
        )

    await session.delete(mesa)
    await session.commit()


# ============================================================
# 9. ALTERAR STATUS (ADMIN)
# ============================================================
@router.patch(
    '/{public_id}/status',
    response_model=MesaResponse,
    status_code=status.HTTP_200_OK,
    summary='Alterar status da mesa',
    description='Altera o status de uma mesa (apenas administradores)',
)
async def alterar_status_mesa(
    public_id: str,
    novo_status: Annotated[
        StatusMesa, Query(description='Novo status da mesa')
    ],
    session: Session,
    current_user: Current_user,
):
    PermissionService.require_admin(current_user)

    query = select(Mesa).where(Mesa.public_id == public_id)
    result = await session.execute(query)
    mesa = result.scalar_one_or_none()

    if not mesa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Mesa com Public ID {public_id} não encontrada',
        )

    mesa.status = novo_status
    await session.commit()
    await session.refresh(mesa)

    return mesa
