from http import HTTPStatus


def test_read_root(client):
    response = client.get('/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Welcome to the Restaurante API!'}
