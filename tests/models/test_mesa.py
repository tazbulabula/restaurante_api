# tests/models/test_mesa.py

import pytest
from sqlalchemy.exc import IntegrityError

from restaurante_api.models.mesa import Mesa, StatusMesa, TipoMesa


@pytest.mark.asyncio
async def test_create_mesa(session, mock_db_time):
    """Testa criação de uma mesa"""
    with mock_db_time(model=Mesa) as time:
        mesa = Mesa(
            numero=1,
            capacidade=4,
            tipo=TipoMesa.PADRAO,
            descricao='Mesa perto da janela',
            localizacao='Salão principal',
        )
        session.add(mesa)
        await session.commit()
        await session.refresh(mesa)

    assert mesa.id == int(1)
    assert mesa.public_id == '00000000-0000-0000-0000-000000000000'
    assert mesa.numero == int(1)
    assert mesa.capacidade == int(4)
    assert mesa.status == StatusMesa.DISPONIVEL
    assert mesa.tipo == TipoMesa.PADRAO
    assert mesa.descricao == 'Mesa perto da janela'
    assert mesa.localizacao == 'Salão principal'
    assert mesa.is_active is True
    assert mesa.created_at == time
    assert mesa.updated_at == time


@pytest.mark.asyncio
async def test_create_mesa_numero_unico(session):
    """Testa que número da mesa é único"""
    mesa1 = Mesa(numero=1, capacidade=4)
    session.add(mesa1)
    await session.commit()

    mesa2 = Mesa(numero=1, capacidade=2)
    session.add(mesa2)

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_update_mesa_status(session):
    """Testa atualização do status da mesa"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()

    mesa.status = StatusMesa.RESERVADA
    await session.commit()
    await session.refresh(mesa)

    assert mesa.status == StatusMesa.RESERVADA


'''@pytest.mark.asyncio
async def test_mesa_status_enum(session):
    """Testa que status aceita apenas valores do Enum"""
    mesa = Mesa(
        numero=1,
        capacidade=4,
        status='status_invalido',  # Não é um StatusMesa válido
    )
    session.add(mesa)

    with pytest.raises(IntegrityError):
        await session.commit()'''
