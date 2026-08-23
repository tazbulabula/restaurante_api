# tests/routes/test_mesas.py

from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from sqlalchemy import select

from restaurante_api.models.mesa import Mesa, StatusMesa, TipoMesa
from restaurante_api.models.reserva_mesa import ReservaMesa

# ============================================================
# TESTES DE LISTAGEM (PÚBLICOS)
# ============================================================


@pytest.mark.asyncio
async def test_listar_mesas(client, session):
    """Testa listagem de mesas"""
    mesas = [
        Mesa(numero=1, capacidade=4, tipo=TipoMesa.PADRAO),
        Mesa(numero=2, capacidade=6, tipo=TipoMesa.VIP),
        Mesa(numero=3, capacidade=2, tipo=TipoMesa.BAR),
    ]
    for m in mesas:
        session.add(m)
    await session.commit()

    response = client.get('/mesas/')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(3)
    assert data[0]['numero'] == int(1)
    assert data[1]['numero'] == int(2)
    assert data[2]['numero'] == int(3)


@pytest.mark.asyncio
async def test_listar_mesas_com_filtro_status(client, session):
    """Testa listagem filtrando por status"""
    mesas = [
        Mesa(numero=1, capacidade=4, status=StatusMesa.DISPONIVEL),
        Mesa(numero=2, capacidade=6, status=StatusMesa.RESERVADA),
        Mesa(numero=3, capacidade=2, status=StatusMesa.DISPONIVEL),
    ]
    for m in mesas:
        session.add(m)
    await session.commit()

    response = client.get('/mesas/?status_mesa=disponivel')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(2)
    assert all(m['status'] == 'disponivel' for m in data)


@pytest.mark.asyncio
async def test_listar_mesas_com_filtro_tipo(client, session):
    """Testa listagem filtrando por tipo"""
    mesas = [
        Mesa(numero=1, capacidade=4, tipo=TipoMesa.PADRAO),
        Mesa(numero=2, capacidade=6, tipo=TipoMesa.VIP),
        Mesa(numero=3, capacidade=2, tipo=TipoMesa.PADRAO),
    ]
    for m in mesas:
        session.add(m)
    await session.commit()

    response = client.get('/mesas/?tipo=padrao')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(2)
    assert all(m['tipo'] == 'padrao' for m in data)


@pytest.mark.asyncio
async def test_listar_mesas_paginacao(client, session):
    """Testa paginação na listagem"""
    for i in range(10):
        mesa = Mesa(numero=i + 1, capacidade=4)
        session.add(mesa)
    await session.commit()

    response = client.get('/mesas/?limit=3&offset=2')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(3)
    assert data[0]['numero'] == int(3)
    assert data[1]['numero'] == int(4)
    assert data[2]['numero'] == int(5)


# ============================================================
# TESTES DE BUSCA (PÚBLICOS)
# ============================================================


@pytest.mark.asyncio
async def test_buscar_mesa_por_id(client, session):
    """Testa busca de mesa por ID"""
    mesa = Mesa(numero=5, capacidade=4, tipo=TipoMesa.VIP)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    response = client.get(f'/mesas/{mesa.id}')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['numero'] == int(5)
    assert data['tipo'] == 'vip'


@pytest.mark.asyncio
async def test_buscar_mesa_por_id_nao_encontrado(client):
    """Testa busca de mesa por ID inexistente"""
    response = client.get('/mesas/999')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrada' in response.json()['detail']


@pytest.mark.asyncio
async def test_buscar_mesa_por_public_id(client, session):
    """Testa busca de mesa por Public ID"""
    mesa = Mesa(numero=7, capacidade=6, tipo=TipoMesa.EXTERNA)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    response = client.get(f'/mesas/public/{mesa.public_id}')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['numero'] == int(7)
    assert data['tipo'] == 'externa'


@pytest.mark.asyncio
async def test_buscar_mesa_por_public_id_nao_encontrado(client):
    """Testa busca de mesa por Public ID inexistente"""
    response = client.get('/mesas/public/00000000-0000-0000-0000-000000000000')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrada' in response.json()['detail']


@pytest.mark.asyncio
async def test_buscar_mesa_por_numero(client, session):
    """Testa busca de mesa por número"""
    mesa = Mesa(numero=10, capacidade=8, tipo=TipoMesa.JANTAR)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    response = client.get('/mesas/numero/10')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['numero'] == int(10)
    assert data['tipo'] == 'jantar'


@pytest.mark.asyncio
async def test_buscar_mesa_por_numero_nao_encontrado(client):
    """Testa busca de mesa por número inexistente"""
    response = client.get('/mesas/numero/999')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrada' in response.json()['detail']


# ============================================================
# TESTES DE DISPONIBILIDADE (PÚBLICOS)
# ============================================================


@pytest.mark.asyncio
async def test_verificar_disponibilidade(client, session):
    """Testa verificação de disponibilidade de mesas"""
    # Cria mesas
    mesa1 = Mesa(numero=1, capacidade=4)
    mesa2 = Mesa(numero=2, capacidade=6)
    session.add_all([mesa1, mesa2])
    await session.commit()
    await session.refresh(mesa1)
    await session.refresh(mesa2)

    # Cria uma reserva para a mesa1
    data_hora = datetime.now() + timedelta(hours=2)
    reserva = ReservaMesa(
        mesa_id=mesa1.id,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        data_hora=data_hora,
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=data_hora + timedelta(minutes=15),
    )
    session.add(reserva)
    await session.commit()

    # Verifica disponibilidade
    request_data = {
        'data_hora': data_hora.isoformat(),
        'numero_pessoas': 4,
        'duracao_minutos': 60,
    }
    response = client.post('/mesas/disponibilidade', json=request_data)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['disponivel'] is True
    assert len(data['mesas_disponiveis']) == int(1)
    assert data['mesas_disponiveis'][0]['numero'] == int(2)


@pytest.mark.asyncio
async def test_verificar_disponibilidade_sem_mesas(client, session):
    """Testa verificação quando não há mesas disponíveis"""
    # Cria uma mesa com capacidade menor que o número de pessoas
    mesa = Mesa(numero=1, capacidade=2)
    session.add(mesa)
    await session.commit()

    request_data = {
        'data_hora': (datetime.now() + timedelta(hours=1)).isoformat(),
        'numero_pessoas': 5,
        'duracao_minutos': 60,
    }
    response = client.post('/mesas/disponibilidade', json=request_data)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['disponivel'] is False
    assert len(data['mesas_disponiveis']) == int(0)


# ============================================================
# TESTES DE CRIAÇÃO (ADMIN)
# ============================================================


@pytest.mark.asyncio
async def test_criar_mesa(client, session, admin_token):
    """Testa criação de mesa (admin)"""
    mesa_data = {
        'numero': 15,
        'capacidade': 4,
        'tipo': 'vip',
        'descricao': 'Mesa especial',
        'localizacao': 'Área VIP',
        'is_active': True,
    }

    response = client.post(
        '/mesas/',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=mesa_data,
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['numero'] == int(15)
    assert data['capacidade'] == int(4)
    assert data['tipo'] == 'vip'
    assert data['descricao'] == 'Mesa especial'
    assert data['localizacao'] == 'Área VIP'
    assert data['status'] == 'disponivel'
    assert data['public_id'] is not None


@pytest.mark.asyncio
async def test_criar_mesa_numero_duplicado(client, session, admin_token):
    """Testa criação de mesa com número já existente"""
    mesa = Mesa(numero=20, capacidade=4)
    session.add(mesa)
    await session.commit()

    mesa_data = {
        'numero': 20,
        'capacidade': 6,
        'tipo': 'padrao',
    }

    response = client.post(
        '/mesas/',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=mesa_data,
    )

    message = f'Já existe uma mesa com o número {mesa.numero}'

    assert response.status_code == HTTPStatus.CONFLICT
    assert message in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_mesa_sem_autenticacao(client):
    """Testa criação de mesa sem token (deve falhar)"""
    mesa_data = {
        'numero': 25,
        'capacidade': 4,
        'tipo': 'padrao',
    }

    response = client.post('/mesas/', json=mesa_data)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert 'not authenticated' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_criar_mesa_usuario_comum(client, token):
    """Testa criação de mesa com usuário comum (deve falhar)"""
    mesa_data = {
        'numero': 30,
        'capacidade': 4,
        'tipo': 'padrao',
    }

    response = client.post(
        '/mesas/',
        headers={'Authorization': f'Bearer {token}'},
        json=mesa_data,
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'administradores' in response.json()['detail'].lower()


# ============================================================
# TESTES DE ATUALIZAÇÃO (ADMIN)
# ============================================================


@pytest.mark.asyncio
async def test_atualizar_mesa(client, session, admin_token):
    """Testa atualização de mesa"""
    mesa = Mesa(numero=35, capacidade=4, tipo=TipoMesa.PADRAO)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    update_data = {
        'capacidade': 6,
        'tipo': 'vip',
        'descricao': 'Mesa VIP atualizada',
    }

    response = client.put(
        f'/mesas/{mesa.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
        json=update_data,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['capacidade'] == int(6)
    assert data['tipo'] == 'vip'
    assert data['descricao'] == 'Mesa VIP atualizada'
    assert data['numero'] == int(35)  # Mantido


@pytest.mark.asyncio
async def test_atualizar_mesa_nao_encontrada(client, admin_token):
    """Testa atualização de mesa inexistente"""
    response = client.put(
        '/mesas/00000000-0000-0000-0000-000000000000',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'capacidade': 6},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrada' in response.json()['detail']


# ============================================================
# TESTES DE DELETAÇÃO (ADMIN)
# ============================================================


@pytest.mark.asyncio
async def test_deletar_mesa(client, session, admin_token):
    """Testa deleção de mesa"""
    mesa = Mesa(numero=40, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    response = client.delete(
        f'/mesas/{mesa.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT

    # Verifica que foi deletada
    result = await session.execute(select(Mesa).where(Mesa.id == mesa.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_deletar_mesa_com_reservas_ativas(client, session, admin_token):
    """Testa deleção de mesa com reservas ativas (deve falhar)"""
    mesa = Mesa(numero=45, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=30),
    )
    session.add(reserva)
    await session.commit()

    response = client.delete(
        f'/mesas/{mesa.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert 'reservas ativas' in response.json()['detail']


@pytest.mark.asyncio
async def test_deletar_mesa_nao_encontrada(client, admin_token):
    """Testa deleção de mesa inexistente"""
    response = client.delete(
        '/mesas/00000000-0000-0000-0000-000000000000',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrada' in response.json()['detail']


# ============================================================
# TESTES DE ALTERAÇÃO DE STATUS (ADMIN)
# ============================================================


@pytest.mark.asyncio
async def test_alterar_status_mesa(client, session, admin_token):
    """Testa alteração de status da mesa"""
    mesa = Mesa(numero=50, capacidade=4, status=StatusMesa.DISPONIVEL)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    response = client.patch(
        f'/mesas/{mesa.public_id}/status?novo_status=reservada',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['status'] == 'reservada'


@pytest.mark.asyncio
async def test_alterar_status_mesa_nao_encontrada(client, admin_token):
    """Testa alteração de status de mesa inexistente"""
    response = client.patch(
        '/mesas/00000000-0000-0000-0000-000000000000/status?novo_status=ocupada',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrada' in response.json()['detail']
