from datetime import datetime
from http import HTTPStatus


def test_create_user(client):
    response = client.post(
        '/users/create',
        json={
            'username': 'Taz',
            'email': 'taz@gmail.com',
            'password': '1234',
            'phone': '9xxxxxxxxxx',
        },
    )
    data = response.json()
    assert response.status_code == HTTPStatus.CREATED
    assert len(data) == int(5)

    assert data == {
        'username': data['username'],
        'email': data['email'],
        'phone': data['phone'],
        'user_type': data['user_type'],
        'public_id': data['public_id'],
    }


def test_create_user_with_email_existent(client, user):
    response = client.post(
        '/users/create',
        json={
            'username': 'Taz',
            'email': user.email,
            'password': '1234',
            'phone': '9xxxxxxxxxx',
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'detail': 'Email already in use by another user'
    }


def test_update_user(client, user, token):
    response = client.put(
        f'/users/update/{user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'Taz',
            'email': 'taz@gmail.com',
            'password': '1234',
            'phone': '9xxxxxxxxxx',
        },
    )
    data = response.json()
    # Converte last_login de string para datetime
    if 'last_login' in data and isinstance(data['last_login'], str):
        data['last_login'] = datetime.fromisoformat(
            data['last_login'].replace('Z', '+00:00')
        )
    assert response.status_code == HTTPStatus.OK
    assert data == {
        'public_id': user.public_id,
        'username': 'Taz',
        'email': 'taz@gmail.com',
        'phone': '9xxxxxxxxxx',
        'user_type': 'client',
    }


def test_update_user_with_integrity_error(client, user, token):
    client.post(
        '/users/create',
        json={
            'username': 'Taz',
            'email': 'outroEmail@gmail.com',
            'password': '1234',
            'phone': '9xxxxxxxxxx',
        },
    )

    response = client.put(
        f'/users/update/{user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'Taz',
            'email': 'outroEmail@gmail.com',
            'password': '1234',
            'phone': '9xxxxxxxxxx',
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'detail': 'Email already in use by another user'
    }


def test_update_user_with_other_public_id(client, user, other_user, token):
    response = client.put(
        f'/users/update/{other_user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': 'Taz',
            'email': 'taz@gmail.com',
            'password': '1234',
            'phone': '9xxxxxxxxxx',
        },
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {'detail': 'Not enough permissions.'}


def test_delete_user(client, user, token):
    response = client.delete(
        f'/users/delete/{user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'User as been deleted.'}


def test_delete_other_user(client, user, token, other_user):
    response = client.delete(
        f'/users/delete/{other_user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {'detail': 'Not enough permissions.'}


# ============================================================
# TESTES PARA LISTAR USUÁRIOS (ADMIN)
# ============================================================


def test_list_users_as_admin(client, admin_token, admin_user, user):
    """Testa que admin pode listar todos os usuários"""
    response = client.get(
        '/users/',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert 'users' in data
    assert 'total' in data
    assert 'page' in data
    assert 'per_page' in data

    # Deve ter pelo menos 2 usuários (admin + user)
    assert data['total'] >= int(2)
    assert len(data['users']) >= int(2)

    # Verifica que o admin está na lista
    admin_in_list = any(u['email'] == admin_user.email for u in data['users'])
    assert admin_in_list is True


def test_list_users_as_common_user(client, token):
    """Testa que usuário comum NÃO pode listar usuários"""
    response = client.get(
        '/users/',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'apenas administradores' in response.json()['detail'].lower()


def test_list_users_without_token(client):
    """Testa que usuário não autenticado NÃO pode listar usuários"""
    response = client.get('/users/')

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_list_users_with_search_filter(client, admin_token, user):
    """Testa busca por usuários com filtro de busca"""
    response = client.get(
        f'/users/?search={user.username}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert data['total'] >= int(1)
    assert any(u['username'] == user.username for u in data['users'])


def test_list_users_with_user_type_filter(client, admin_token):
    """Testa filtro por tipo de usuário (client)"""
    response = client.get(
        '/users/?user_type=client',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Todos os usuários retornados devem ser do tipo 'client'
    for u in data['users']:
        assert u['user_type'] == 'client'


def test_list_users_with_admin_type_filter(client, admin_token, admin_user):
    """Testa filtro por tipo de usuário (admin)"""
    response = client.get(
        '/users/?user_type=admin',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Todos os usuários retornados devem ser do tipo 'admin'
    for u in data['users']:
        assert u['user_type'] == 'admin'

    # Deve conter o admin que fez a requisição
    assert any(u['email'] == admin_user.email for u in data['users'])


def test_list_users_with_pagination(client, admin_token):
    """Testa paginação na listagem de usuários"""
    # Cria alguns usuários extras
    for i in range(3):
        client.post(
            '/users/create',
            json={
                'username': f'pag_test_{i}',
                'email': f'pag_test_{i}@email.com',
                'password': '123456',
                'phone': '9xxxxxxxxxx',
            },
        )

    # Primeira página (limit=2)
    response = client.get(
        '/users/?limit=2&offset=0',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['per_page'] == int(2)
    assert len(data['users']) <= int(2)
    assert data['page'] == int(1)

    # Segunda página (limit=2, offset=2)
    response2 = client.get(
        '/users/?limit=2&offset=2',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response2.status_code == HTTPStatus.OK
    data2 = response2.json()
    assert data2['per_page'] == int(2)
    assert data2['page'] == int(2)

    # Os usuários da primeira página devem ser diferentes da segunda
    if len(data['users']) > 0 and len(data2['users']) > 0:
        assert data['users'][0]['public_id'] != data2['users'][0]['public_id']


def test_list_users_with_active_only_filter(client, admin_token):
    """Testa filtro para apenas usuários ativos"""
    response = client.get(
        '/users/?active_only=true',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Todos os usuários devem estar ativos (deleted_at is None)
    for u in data['users']:
        assert u['deleted_at'] is None


# ============================================================
# TESTES PARA SOFT DELETE
# ============================================================


def test_soft_delete_user_as_admin(client, admin_token, user):
    """Testa que admin pode desativar (soft delete) um usuário"""
    response = client.delete(
        f'/users/delete/{user.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['message'] == 'Usuário desativado com sucesso'

    # Verifica que o usuário não aparece na lista de ativos
    response = client.get(
        '/users/',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    data = response.json()
    assert not any(u['public_id'] == user.public_id for u in data['users'])


def test_soft_delete_user_as_common_user(client, token, user):
    """Testa que usuário comum pode desativar a si mesmo"""
    response = client.delete(
        f'/users/delete/{user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['message'] == 'Usuário desativado com sucesso'


def test_soft_delete_other_user_as_common_user(client, token, other_user):
    """Testa que usuário comum NÃO pode desativar outro usuário"""
    response = client.delete(
        f'/users/delete/{other_user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'permissão' in response.json()['detail'].lower()


def test_list_deleted_users_as_admin(client, admin_token, user):
    """Testa que admin pode listar usuários deletados"""
    # Desativa um usuário
    client.delete(
        f'/users/delete/{user.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    response = client.get(
        '/users/deleted',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) >= 1
    assert any(u['public_id'] == user.public_id for u in data)


def test_list_deleted_users_as_common_user(client, token):
    """Testa que usuário comum NÃO pode listar usuários deletados"""
    response = client.get(
        '/users/deleted',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'apenas administradores' in response.json()['detail'].lower()


def test_restore_user_as_admin(client, admin_token, user):
    """Testa que admin pode restaurar um usuário deletado"""
    # Desativa o usuário
    client.delete(
        f'/users/delete/{user.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    # Restaura o usuário
    response = client.patch(
        f'/users/{user.public_id}/restore',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['public_id'] == user.public_id
    assert data['deleted_at'] is None

    # Verifica que o usuário voltou à lista de ativos
    response = client.get(
        '/users/',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    data = response.json()
    assert any(u['public_id'] == user.public_id for u in data['users'])


def test_restore_user_as_common_user(client, token, user):
    """Testa que usuário comum NÃO pode restaurar usuários"""
    response = client.patch(
        f'/users/{user.public_id}/restore',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'apenas administradores' in response.json()['detail'].lower()


def test_hard_delete_user_as_admin(client, admin_token, user):
    """Testa que admin pode deletar permanentemente um usuário"""
    # Desativa o usuário primeiro
    client.delete(
        f'/users/delete/{user.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    # Deleta permanentemente
    response = client.delete(
        f'/users/{user.public_id}/permanent',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['message'] == 'Usuário removido permanentemente'

    # Verifica que o usuário foi completamente removido
    response = client.get(
        '/users/deleted',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    data = response.json()
    assert not any(u['public_id'] == user.public_id for u in data)


def test_hard_delete_user_as_common_user(client, token, user):
    """Testa que usuário comum NÃO pode deletar permanentemente"""
    response = client.delete(
        f'/users/{user.public_id}/permanent',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'apenas administradores' in response.json()['detail'].lower()


def test_hard_delete_self_as_admin(client, admin_token, admin_user):
    """Testa que admin NÃO pode deletar permanentemente a si mesmo"""
    response = client.delete(
        f'/users/{admin_user.public_id}/permanent',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    m = 'Não é possível deletar permanentemente sua própria conta'
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert m in response.json()['detail']


def test_include_deleted_filter(client, admin_token, user):
    """Testa o filtro include_deleted para listar usuários"""
    # Desativa um usuário
    client.delete(
        f'/users/delete/{user.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    # Lista sem incluir deletados (padrão)
    response = client.get(
        '/users/',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    data = response.json()
    assert not any(u['public_id'] == user.public_id for u in data['users'])

    # Lista incluindo deletados
    response = client.get(
        '/users/?include_deleted=true',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    data = response.json()
    assert any(u['public_id'] == user.public_id for u in data['users'])


def test_change_user_type_as_admin(client, admin_token, user):
    """Testa que admin pode alterar o tipo de um usuário"""
    response = client.patch(
        f'/users/{user.public_id}/tipo',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'user_type': 'admin'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['public_id'] == user.public_id
    assert data['user_type'] == 'admin'


def test_change_user_type_to_client(client, admin_token, user):
    """Testa que admin pode alterar usuário admin para client"""
    # Primeiro altera para admin
    client.patch(
        f'/users/{user.public_id}/tipo',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'user_type': 'admin'},
    )

    # Depois altera para client
    response = client.patch(
        f'/users/{user.public_id}/tipo',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'user_type': 'client'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['public_id'] == user.public_id
    assert data['user_type'] == 'client'


def test_change_user_type_as_common_user(client, token, other_user):
    """Testa que usuário comum NÃO pode alterar tipo de outro usuário"""
    response = client.patch(
        f'/users/{other_user.public_id}/tipo',
        headers={'Authorization': f'Bearer {token}'},
        json={'user_type': 'admin'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert 'apenas administradores' in response.json()['detail'].lower()


def test_change_own_user_type_as_admin(client, admin_token, admin_user):
    """Testa que admin NÃO pode alterar seu próprio tipo"""
    response = client.patch(
        f'/users/{admin_user.public_id}/tipo',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'user_type': 'client'},
    )
    message = 'Não é possível alterar seu próprio tipo'
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert message in response.json()['detail']


def test_change_user_type_with_invalid_type(client, admin_token, user):
    """Testa que admin NÃO pode usar tipo inválido"""
    response = client.patch(
        f'/users/{user.public_id}/tipo',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'user_type': 'super_admin'},
    )

    message = "Tipo inválido. Use 'admin' ou 'client'"
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert message in response.json()['detail']


def test_change_user_type_user_not_found(client, admin_token):
    """Testa que admin recebe 404 ao tentar alterar usuário inexistente"""
    response = client.patch(
        '/users/99999999-9999-9999-9999-999999999999/tipo',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'user_type': 'admin'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'Usuário não encontrado' in response.json()['detail']


def test_change_user_type_without_token(client, user):
    """Testa que usuário sem token NÃO pode alterar tipo"""
    response = client.patch(
        f'/users/{user.public_id}/tipo',
        json={'user_type': 'admin'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_change_user_type_deleted_user(client, admin_token, user):
    """Testa que admin NÃO pode alterar tipo de usuário deletado"""
    # Desativa o usuário
    client.delete(
        f'/users/delete/{user.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    # Tenta alterar o tipo do usuário deletado
    response = client.patch(
        f'/users/{user.public_id}/tipo',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'user_type': 'admin'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert 'Usuário não encontrado' in response.json()['detail']


def test_change_user_type_with_empty_body(client, admin_token, user):
    """Testa que admin recebe 422 ao enviar body vazio"""
    response = client.patch(
        f'/users/{user.public_id}/tipo',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_change_user_type_restored_user(client, admin_token, user):
    """Testa que admin pode alterar tipo de usuário restaurado"""
    # 1. Desativa o usuário
    client.delete(
        f'/users/delete/{user.public_id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    # 2. Restaura o usuário
    client.patch(
        f'/users/{user.public_id}/restore',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    # 3. Altera o tipo
    response = client.patch(
        f'/users/{user.public_id}/tipo',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'user_type': 'admin'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['public_id'] == user.public_id
    assert data['user_type'] == 'admin'
