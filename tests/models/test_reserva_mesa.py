from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from restaurante_api.models.mesa import Mesa, StatusMesa
from restaurante_api.models.reserva_mesa import ReservaMesa


@pytest.mark.asyncio
async def test_create_reserva_mesa(session, mock_db_time, user):
    """Testa criação de uma reserva de mesa"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    data_hora = datetime.now() + timedelta(days=1)

    with mock_db_time(model=ReservaMesa) as time:
        reserva = ReservaMesa(
            mesa_id=mesa.id,
            usuario_id=user.id,
            cliente_nome='Cliente Teste',
            cliente_telefone='+244 999 999 999',
            data_hora=data_hora,
            numero_pessoas=3,
            observacoes='Aniversário',
        )
        session.add(reserva)
        await session.commit()
        await session.refresh(reserva)

    assert reserva.id == int(1)
    assert reserva.mesa_id == mesa.id
    assert reserva.usuario_id == user.id
    assert reserva.cliente_nome == 'Cliente Teste'
    assert reserva.cliente_telefone == '+244 999 999 999'
    assert reserva.data_hora == data_hora
    assert reserva.numero_pessoas == int(3)
    assert reserva.status == StatusMesa.RESERVADA
    assert reserva.observacoes == 'Aniversário'
    assert reserva.created_at == time


@pytest.mark.asyncio
async def test_reserva_sem_usuario(session):
    """Testa criação de reserva sem usuário (convidado)"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=None,
        cliente_nome='Convidado',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)
    assert reserva.usuario_id is None
    assert reserva.cliente_nome == 'Convidado'


@pytest.mark.asyncio
async def test_reserva_com_expiracao(session):
    """Testa reserva com data de expiração"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    expira_em = datetime.now() + timedelta(minutes=15)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        expira_em=expira_em,
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    assert reserva.expira_em is not None
    assert reserva.expira_em <= datetime.now() + timedelta(minutes=16)


@pytest.mark.asyncio
async def test_relacionamento_mesa_reservas(session, user):
    """Testa o relacionamento entre Mesa e Reservas"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva1 = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=user.id,
        cliente_nome='Cliente 1',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
    )
    reserva2 = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=user.id,
        cliente_nome='Cliente 2',
        cliente_telefone='+244 999 999 998',
        data_hora=datetime.now() + timedelta(days=2),
        numero_pessoas=3,
    )
    session.add_all([reserva1, reserva2])
    await session.commit()

    # Busca a mesa com as reservas
    result = await session.execute(select(Mesa).where(Mesa.id == mesa.id))
    mesa_buscada = result.scalar_one()
    await session.refresh(mesa)
    assert len(mesa_buscada.reservas) == int(2)
    assert mesa_buscada.reservas[0].cliente_nome == 'Cliente 1'
    assert mesa_buscada.reservas[1].cliente_nome == 'Cliente 2'
