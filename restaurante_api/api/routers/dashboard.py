# restaurante_api/routes/dashboard.py

from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import Integer, cast, func, select

from restaurante_api.core.dependencies import Current_user, Session
from restaurante_api.models import (
    ItemPedido,
    Mesa,
    Pedido,
    Produto,
    ReservaMesa,
    StatusMesa,
    StatusPedido,
    User,
)
from restaurante_api.schemas.user import UserType
from restaurante_api.services.permission_service import PermissionService

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


# ============================================================
# HELPERS
# ============================================================
def _inicio_do_dia(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time())


def _fim_do_dia(d: date) -> datetime:
    return _inicio_do_dia(d) + timedelta(days=1)


# ============================================================
# 1. ESTATÍSTICAS GERAIS
# ============================================================
@router.get(
    '/estatisticas',
    status_code=status.HTTP_200_OK,
    summary='Estatísticas gerais do restaurante',
)
async def estatisticas(
    session: Session,
    current_user: Current_user,
):
    PermissionService.require_admin(current_user)

    hoje = date.today()
    inicio_hoje = _inicio_do_dia(hoje)
    fim_hoje = _fim_do_dia(hoje)

    # ---------- Produtos ----------
    total_produtos = (
        await session.scalar(select(func.count()).select_from(Produto))
    ) or 0
    produtos_disponiveis = (
        await session.scalar(
            select(func.count())
            .select_from(Produto)
            .where(Produto.is_available.is_(True))
        )
    ) or 0

    # ---------- Mesas ----------
    total_mesas = (
        await session.scalar(select(func.count()).select_from(Mesa))
    ) or 0
    mesas_ocupadas = (
        await session.scalar(
            select(func.count())
            .select_from(Mesa)
            .where(Mesa.status == StatusMesa.OCUPADA)
        )
    ) or 0

    # ---------- Pedidos ----------
    # Só conta pedidos "válidos" (exclui cancelados)
    status_validos = [
        StatusPedido.PAGO,
        StatusPedido.PREPARANDO,
        StatusPedido.PRONTO,
        StatusPedido.ENTREGUE,
    ]

    total_pedidos = (
        await session.scalar(
            select(func.count())
            .select_from(Pedido)
            .where(Pedido.status != StatusPedido.CANCELADO)
        )
    ) or 0

    pedidos_hoje = (
        await session.scalar(
            select(func.count())
            .select_from(Pedido)
            .where(
                Pedido.created_at >= inicio_hoje,
                Pedido.created_at < fim_hoje,
                Pedido.status != StatusPedido.CANCELADO,
            )
        )
    ) or 0

    # ---------- Receita ----------
    receita_total = (
        await session.scalar(
            select(func.coalesce(func.sum(Pedido.total), 0.0)).where(
                Pedido.status.in_(status_validos)
            )
        )
    ) or 0.0

    receita_hoje = (
        await session.scalar(
            select(func.coalesce(func.sum(Pedido.total), 0.0)).where(
                Pedido.created_at >= inicio_hoje,
                Pedido.created_at < fim_hoje,
                Pedido.status.in_(status_validos),
            )
        )
    ) or 0.0

    # ---------- Reservas ----------
    total_reservas = (
        await session.scalar(select(func.count()).select_from(ReservaMesa))
    ) or 0

    reservas_hoje = (
        await session.scalar(
            select(func.count())
            .select_from(ReservaMesa)
            .where(
                ReservaMesa.data_hora >= inicio_hoje,
                ReservaMesa.data_hora < fim_hoje,
                ReservaMesa.status.notin_([
                    StatusMesa.CANCELADA,
                    StatusMesa.INDISPONIVEL,
                ]),
            )
        )
    ) or 0

    # ---------- Clientes ----------
    total_clientes = (
        await session.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.user_type == UserType.CLIENT,
                User.is_active.is_(True),
            )
        )
    ) or 0

    return {
        'total_produtos': int(total_produtos),
        'produtos_disponiveis': int(produtos_disponiveis),
        'total_mesas': int(total_mesas),
        'mesas_ocupadas': int(mesas_ocupadas),
        'total_pedidos': int(total_pedidos),
        'pedidos_hoje': int(pedidos_hoje),
        'receita_total': float(receita_total),
        'receita_hoje': float(receita_hoje),
        'total_reservas': int(total_reservas),
        'reservas_hoje': int(reservas_hoje),
        'total_clientes': int(total_clientes),
    }


# ============================================================
# 2. PRODUTOS POR CATEGORIA
# ============================================================
@router.get(
    '/produtos-por-categoria',
    status_code=status.HTTP_200_OK,
    summary='Distribuição de produtos por categoria',
)
async def produtos_por_categoria(
    session: Session,
    current_user: Current_user,
):
    PermissionService.require_admin(current_user)

    rows = await session.execute(
        select(
            Produto.category,
            func.count(Produto.id).label('total'),
            func.sum(cast(Produto.is_available, Integer)).label('disponiveis'),
        ).group_by(Produto.category)
    )

    resultado = []
    for row in rows:
        # Enum → string ('principal', 'bebida', etc.)
        categoria = (
            row.category.value
            if hasattr(row.category, 'value')
            else str(row.category)
        )
        resultado.append({
            'categoria': categoria,
            'total': int(row.total or 0),
            'disponiveis': int(row.disponiveis or 0),
        })

    # Ordena por total desc (útil para o gráfico)
    resultado.sort(key=lambda x: x['total'], reverse=True)
    return resultado


# ============================================================
# 3. PEDIDOS POR DIA
# ============================================================
@router.get(
    '/pedidos-por-dia',
    status_code=status.HTTP_200_OK,
    summary='Contagem de pedidos por dia',
)
async def pedidos_por_dia(
    session: Session,
    current_user: Current_user,
    dias: Annotated[int, Query(ge=1, le=90)] = 7,
):
    PermissionService.require_admin(current_user)

    # Início do período (ex: hoje - 6 dias = 7 dias no total)
    inicio = _inicio_do_dia(date.today() - timedelta(days=dias - 1))

    rows = await session.execute(
        select(
            func.date(Pedido.created_at).label('dia'),
            func.count(Pedido.id).label('total'),
        )
        .where(
            Pedido.created_at >= inicio,
            Pedido.status != StatusPedido.CANCELADO,
        )
        .group_by(func.date(Pedido.created_at))
        .order_by(func.date(Pedido.created_at))
    )

    # Mapa para preencher dias sem pedidos com 0
    mapa = {str(row.dia): int(row.total or 0) for row in rows}

    resultado = []
    for i in range(dias):
        d = date.today() - timedelta(days=dias - 1 - i)
        chave = d.isoformat()  # 'YYYY-MM-DD'
        resultado.append({
            'data': chave,
            'total': mapa.get(chave, 0),
        })

    return resultado


# ============================================================
# 4. RECEITA POR DIA
# ============================================================
@router.get(
    '/receita-por-dia',
    status_code=status.HTTP_200_OK,
    summary='Receita por dia',
)
async def receita_por_dia(
    session: Session,
    current_user: Current_user,
    dias: Annotated[int, Query(ge=1, le=90)] = 7,
):
    PermissionService.require_admin(current_user)

    inicio = _inicio_do_dia(date.today() - timedelta(days=dias - 1))

    status_validos = [
        StatusPedido.PAGO,
        StatusPedido.PREPARANDO,
        StatusPedido.PRONTO,
        StatusPedido.ENTREGUE,
    ]

    rows = await session.execute(
        select(
            func.date(Pedido.created_at).label('dia'),
            func.coalesce(func.sum(Pedido.total), 0.0).label('total'),
        )
        .where(
            Pedido.created_at >= inicio,
            Pedido.status.in_(status_validos),
        )
        .group_by(func.date(Pedido.created_at))
        .order_by(func.date(Pedido.created_at))
    )

    mapa = {str(row.dia): float(row.total or 0.0) for row in rows}

    resultado = []
    for i in range(dias):
        d = date.today() - timedelta(days=dias - 1 - i)
        chave = d.isoformat()
        resultado.append({
            'data': chave,
            'total': mapa.get(chave, 0.0),
        })

    return resultado


# ============================================================
# 5. TOP PRODUTOS MAIS VENDIDOS
# ============================================================
@router.get(
    '/top-produtos',
    status_code=status.HTTP_200_OK,
    summary='Top produtos mais vendidos',
)
async def top_produtos(
    session: Session,
    current_user: Current_user,
    limite: Annotated[int, Query(ge=1, le=20)] = 5,
    dias: Annotated[int, Query(ge=1, le=90)] = 30,
):
    PermissionService.require_admin(current_user)

    inicio = _inicio_do_dia(date.today() - timedelta(days=dias - 1))

    status_validos = [
        StatusPedido.PAGO,
        StatusPedido.PREPARANDO,
        StatusPedido.PRONTO,
        StatusPedido.ENTREGUE,
    ]

    rows = await session.execute(
        select(
            Produto.name.label('nome'),
            func.sum(ItemPedido.quantidade).label('total'),
        )
        .join(ItemPedido, ItemPedido.produto_id == Produto.id)
        .join(Pedido, Pedido.id == ItemPedido.pedido_id)
        .where(
            Pedido.created_at >= inicio,
            Pedido.status.in_(status_validos),
        )
        .group_by(Produto.id, Produto.name)
        .order_by(func.sum(ItemPedido.quantidade).desc())
        .limit(limite)
    )

    return [{'nome': row.nome, 'total': int(row.total or 0)} for row in rows]
