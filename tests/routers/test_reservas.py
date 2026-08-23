# tests/routes/test_reservas.py

from datetime import datetime, timedelta
from http import HTTPStatus

import pytest

from restaurante_api.models.mesa import Mesa, StatusMesa
from restaurante_api.models.reserva_mesa import ReservaMesa
from restaurante_api.schemas.user import UserType

# ============================================================
# TESTES DE LISTAGEM
# ============================================================


@pytest.mark.asyncio
async def test_listar_reservas_admin(client, session, admin_token, admin_user):
    """Testa listagem de reservas como admin (vê todas)"""
    # Cria mesas
    mesa1 = Mesa(numero=1, capacidade=4)
    mesa2 = Mesa(numero=2, capacidade=6)
    session.add_all([mesa1, mesa2])
    await session.commit()
    await session.refresh(mesa1)
    await session.refresh(mesa2)

    # Cria reservas
    reserva1 = ReservaMesa(
        mesa_id=mesa1.id,
        usuario_id=admin_user.id,
        cliente_nome='Admin Reserva',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    reserva2 = ReservaMesa(
        mesa_id=mesa2.id,
        usuario_id=None,
        cliente_nome=UserType.CLIENT,
        cliente_telefone='+244 999 999 998',
        data_hora=datetime.now() + timedelta(days=2),
        numero_pessoas=3,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add_all([reserva1, reserva2])
    await session.commit()

    response = client.get(
        '/reservas/', headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(2)


@pytest.mark.asyncio
async def test_listar_reservas_usuario_comum(client, session, token, user):
    """Testa listagem de reservas como usuário comum (vê apenas as próprias)"""
    # Cria mesa
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    # Cria reservas: uma do usuário, outra de convidado
    reserva1 = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=user.id,
        cliente_nome='Usuário Comum',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    reserva2 = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=None,
        cliente_nome='Convidado',
        cliente_telefone='+244 999 999 998',
        data_hora=datetime.now() + timedelta(days=2),
        numero_pessoas=3,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add_all([reserva1, reserva2])
    await session.commit()

    response = client.get(
        '/reservas/', headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(1)
    assert data[0]['cliente_nome'] == 'Usuário Comum'


@pytest.mark.asyncio
async def test_listar_reservas_sem_autenticacao(client):
    """Testa listagem de reservas sem token (deve falhar)"""
    response = client.get('/reservas/')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# ============================================================
# TESTES DE BUSCA
# ============================================================


@pytest.mark.asyncio
async def test_buscar_reserva_por_public_id(
    client, session, admin_token, admin_user
):
    """Testa busca de reserva por public_id"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=admin_user.id,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    response = client.get(
        f'/reservas/{reserva.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['public_id'] == reserva.public_id
    assert data['cliente_nome'] == 'Cliente Teste'


@pytest.mark.asyncio
async def test_buscar_reserva_public_id_nao_encontrado(client, admin_token):
    """Testa busca de reserva com public_id inexistente"""
    response = client.get(
        '/reservas/00000000-0000-0000-0000-000000000000',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'não encontrada' in response.json()['detail']


@pytest.mark.asyncio
async def test_buscar_reserva_usuario_sem_permissao(
    client, session, token, user, admin_user
):
    """Testa busca de reserva de outro usuário (deve falhar)"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    # Reserva criada pelo admin
    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=admin_user.id,
        cliente_nome='Admin Reserva',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    # Usuário comum tenta ver a reserva do admin
    response = client.get(
        f'/reservas/{reserva.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'permissão' in response.json()['detail'].lower()


# ============================================================
# TESTES DE CRIAÇÃO
# ============================================================


@pytest.mark.asyncio
async def test_criar_reserva(client, session, token):
    """Testa criação de reserva"""
    mesa = Mesa(numero=1, capacidade=4, status=StatusMesa.DISPONIVEL)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    data_hora = datetime.now() + timedelta(days=1)
    reserva_data = {
        'mesa_id': mesa.id,
        'data_hora': data_hora.isoformat(),
        'numero_pessoas': 2,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
        'observacoes': 'Aniversário',
    }

    response = client.post(
        '/reservas/',
        headers={'Authorization': f'Bearer {token}'},
        json=reserva_data,
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['mesa_id'] == mesa.id
    assert data['cliente_nome'] == 'Cliente Teste'
    assert data['status'] == 'reservada'
    assert data['expira_em'] is not None


@pytest.mark.asyncio
async def test_criar_reserva_sem_autenticacao(client):
    """Testa criação de reserva sem token (deve falhar)"""
    reserva_data = {
        'mesa_id': 1,
        'data_hora': (datetime.now() + timedelta(days=1)).isoformat(),
        'numero_pessoas': 2,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
    }

    response = client.post('/reservas/', json=reserva_data)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_criar_reserva_mesa_indisponivel(client, session, token):
    """Testa criação de reserva para mesa indisponível"""
    mesa = Mesa(numero=1, capacidade=4, status=StatusMesa.OCUPADA)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva_data = {
        'mesa_id': mesa.id,
        'data_hora': (datetime.now() + timedelta(days=1)).isoformat(),
        'numero_pessoas': 2,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
    }

    response = client.post(
        '/reservas/',
        headers={'Authorization': f'Bearer {token}'},
        json=reserva_data,
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert 'não está disponível' in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_reserva_capacidade_excedida(client, session, token):
    """Testa criação de reserva com capacidade excedida"""
    mesa = Mesa(numero=1, capacidade=2, status=StatusMesa.DISPONIVEL)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva_data = {
        'mesa_id': mesa.id,
        'data_hora': (datetime.now() + timedelta(days=1)).isoformat(),
        'numero_pessoas': 4,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
    }

    response = client.post(
        '/reservas/',
        headers={'Authorization': f'Bearer {token}'},
        json=reserva_data,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'capacidade' in response.json()['detail']


@pytest.mark.asyncio
async def test_criar_reserva_conflito_horario(client, session, token, user):
    """Testa criação de reserva com conflito de horário"""
    mesa = Mesa(numero=1, capacidade=4, status=StatusMesa.DISPONIVEL)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    data_hora = datetime.now() + timedelta(days=1)

    # Primeira reserva
    reserva1 = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=user.id,
        cliente_nome='Cliente 1',
        cliente_telefone='+244 999 999 999',
        data_hora=data_hora,
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add(reserva1)
    await session.commit()

    # Atualiza status da mesa
    mesa.status = StatusMesa.RESERVADA
    await session.commit()

    # Tenta criar outra reserva no mesmo horário
    reserva_data = {
        'mesa_id': mesa.id,
        'data_hora': data_hora.isoformat(),
        'numero_pessoas': 2,
        'cliente_nome': 'Cliente 2',
        'cliente_telefone': '+244 999 999 998',
    }

    response = client.post(
        '/reservas/',
        headers={'Authorization': f'Bearer {token}'},
        json=reserva_data,
    )
    data = response.json()['detail']
    assert response.status_code == HTTPStatus.CONFLICT
    assert f'Mesa {mesa.numero} não está disponível' in data


@pytest.mark.asyncio
async def test_criar_reserva_mesa_inexistente(client, token):
    """Testa criação de reserva para mesa inexistente"""
    reserva_data = {
        'mesa_id': 999,
        'data_hora': (datetime.now() + timedelta(days=1)).isoformat(),
        'numero_pessoas': 2,
        'cliente_nome': 'Cliente Teste',
        'cliente_telefone': '+244 999 999 999',
    }

    response = client.post(
        '/reservas/',
        headers={'Authorization': f'Bearer {token}'},
        json=reserva_data,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'Mesa não encontrada' in response.json()['detail']


# ============================================================
# TESTES DE ATUALIZAÇÃO
# ============================================================


@pytest.mark.asyncio
async def test_atualizar_reserva(client, session, token, user):
    """Testa atualização de reserva"""
    mesa = Mesa(numero=1, capacidade=4, status=StatusMesa.RESERVADA)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=user.id,
        cliente_nome='Cliente Original',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    update_data = {'numero_pessoas': 3, 'observacoes': 'Atualizado'}

    response = client.put(
        f'/reservas/{reserva.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json=update_data,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['numero_pessoas'] == int(3)
    assert data['observacoes'] == 'Atualizado'


@pytest.mark.asyncio
async def test_atualizar_reserva_sem_permissao(
    client, session, token, user, admin_user
):
    """Testa atualização de reserva de outro usuário (deve falhar)"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    # Reserva criada pelo admin
    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=admin_user.id,
        cliente_nome='Admin Reserva',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    response = client.put(
        f'/reservas/{reserva.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'numero_pessoas': 4},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'permissão' in response.json()['detail'].lower()


# ============================================================
# TESTES DE CANCELAMENTO
# ============================================================


@pytest.mark.asyncio
async def test_cancelar_reserva(client, session, token, user):
    """Testa cancelamento de reserva"""
    mesa = Mesa(numero=1, capacidade=4, status=StatusMesa.RESERVADA)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=user.id,
        cliente_nome='Cliente Teste',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    response = client.patch(
        f'/reservas/{reserva.public_id}/cancelar',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['message'] == 'Reserva cancelada com sucesso'
    assert data['status'] == 'disponivel'

    # Verifica que a mesa foi liberada
    await session.refresh(mesa)
    assert mesa.status == StatusMesa.DISPONIVEL


@pytest.mark.asyncio
async def test_cancelar_reserva_sem_permissao(
    client, session, token, admin_user
):
    """Testa cancelamento de reserva de outro usuário (deve falhar)"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=admin_user.id,
        cliente_nome='Admin Reserva',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    response = client.patch(
        f'/reservas/{reserva.public_id}/cancelar',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'permissão' in response.json()['detail'].lower()


@pytest.mark.asyncio
async def test_cancelar_reserva_ja_finalizada(
    client, session, admin_token, admin_user
):
    """Testa cancelamento de reserva já finalizada (deve falhar)"""
    mesa = Mesa(numero=1, capacidade=4, status=StatusMesa.OCUPADA)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=admin_user.id,
        cliente_nome='Cliente Finalizado',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() - timedelta(hours=1),
        numero_pessoas=2,
        status=StatusMesa.OCUPADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add(reserva)
    await session.commit()
    await session.refresh(reserva)

    response = client.patch(
        f'/reservas/{reserva.public_id}/cancelar',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert 'não é possível cancelar' in response.json()['detail'].lower()


# ============================================================
# TESTES DE MINHAS RESERVAS
# ============================================================


'''@pytest.mark.asyncio
async def test_minhas_reservas(client, session, token, user):
    """Testa listagem de minhas reservas"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva1 = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=user.id,
        cliente_nome='Minha Reserva 1',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    reserva2 = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=None,
        cliente_nome='Reserva Convidado',
        cliente_telefone='+244 999 999 998',
        data_hora=datetime.now() + timedelta(days=2),
        numero_pessoas=3,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add_all([reserva1, reserva2])
    await session.commit()

    response = client.get(
        '/reservas/minhas', headers={'Authorization': f'Bearer {token}'}
    )
    breakpoint()
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert len(data) == int(1)
    assert data[0]['cliente_nome'] == 'Minha Reserva 1'''


# ============================================================
# TESTES DE RESERVAS POR MESA (ADMIN)
# ============================================================


@pytest.mark.asyncio
async def test_reservas_por_mesa_admin(
    client, session, admin_token, admin_user
):
    """Testa listagem de reservas por mesa (admin)"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    reserva1 = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=admin_user.id,
        cliente_nome='Reserva 1',
        cliente_telefone='+244 999 999 999',
        data_hora=datetime.now() + timedelta(days=1),
        numero_pessoas=2,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    reserva2 = ReservaMesa(
        mesa_id=mesa.id,
        usuario_id=None,
        cliente_nome='Reserva 2',
        cliente_telefone='+244 999 999 998',
        data_hora=datetime.now() + timedelta(days=2),
        numero_pessoas=3,
        status=StatusMesa.RESERVADA,
        expira_em=datetime.now() + timedelta(minutes=15),
    )
    session.add_all([reserva1, reserva2])
    await session.commit()

    response = client.get(
        f'/reservas/mesa/{mesa.id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == int(2)


@pytest.mark.asyncio
async def test_reservas_por_mesa_usuario_comum(client, session, token):
    """Testa listagem de reservas por mesa com usuário comum (deve falhar)"""
    mesa = Mesa(numero=1, capacidade=4)
    session.add(mesa)
    await session.commit()
    await session.refresh(mesa)

    response = client.get(
        f'/reservas/mesa/{mesa.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'administradores' in response.json()['detail'].lower()
