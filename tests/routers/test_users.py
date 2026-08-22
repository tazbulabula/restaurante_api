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
