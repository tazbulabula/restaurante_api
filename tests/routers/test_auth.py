from http import HTTPStatus

from freezegun import freeze_time


def test_auth_login(client, user):
    response = client.post(
        'token/login',
        data={'username': user.email, 'password': user.clean_password},
    )

    token = response.json()

    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in token
    assert 'token_type' in token


def test_auth_login_with_email_incorrect(user, client):
    response = client.post(
        'token/login',
        data={
            'username': 'email_incorrect@gmail.com',
            'password': user.clean_password,
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {'detail': 'Incorrect Email.'}


def test_auth_login_with_password_incorrect(user, client):
    response = client.post(
        'token/login',
        data={
            'username': user.email,
            'password': 'password-incorrect',
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {'detail': 'Incorrect Password.'}


def test_token_expired_after_time(client, user):
    with freeze_time('2026-03-14 12:00:00'):
        response = client.post(
            '/token/login',
            data={'username': user.email, 'password': user.clean_password},
        )
        assert response.status_code == HTTPStatus.OK
        token = response.json()['access_token']

    with freeze_time('2026-03-14 12:31:00'):
        response = client.put(
            f'/users/update/{user.public_id}',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'username': 'wrongwrong',
                'email': 'wrong@wrong.com',
                'password': 'wrong',
            },
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json() == {'detail': 'Could not validate credentials'}


def test_refresh_token(client, user, token):
    response = client.post(
        '/token/refresh_token', headers={'Authorization': f'Bearer {token}'}
    )
    data = response.json()
    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in data
    assert 'token_type' in data
    assert data['token_type'] == 'bearer'


def test_token_expired_dont_refresh(client, user):
    with freeze_time('2026-03-14 12:00:00'):
        response = client.post(
            '/token/login',
            data={'username': user.email, 'password': user.clean_password},
        )
        assert response.status_code == HTTPStatus.OK
        token = response.json()['access_token']

    with freeze_time('2026-03-14 12:31:00'):
        response = client.post(
            '/token/refresh_token',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json() == {'detail': 'Could not validate credentials'}


def test_change_password(client, user, token):
    response = client.patch(
        f'/token/change_password/{user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'current_password': '123',
            'new_password': '1234',
            'confirm_password': '1234',
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Password is been changed'}


def test_change_password_with_current_password_invalid(client, user, token):
    response = client.patch(
        f'/token/change_password/{user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'current_password': '1235',
            'new_password': '1234',
            'confirm_password': '1234',
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Current password is incorrect'}


def test_change_password_with_new_and_confirm_password_diff(
    client, user, token
):
    response = client.patch(
        f'/token/change_password/{user.public_id}',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'current_password': '123',
            'new_password': '12345',
            'confirm_password': '1234',
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Passwords not match'}


def test_send_token_reset(client, other_user):
    response = client.post(
        '/token/reset-password',
        json={'email': other_user.email},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Email sent'}
