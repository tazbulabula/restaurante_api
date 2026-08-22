# tests/unit/services/test_auth_service.py
from unittest.mock import AsyncMock, Mock, patch

import pytest

from restaurante_api.core.security import hash_password
from restaurante_api.services.auth_service import AuthService

# ========== Fixtures (sem self, usando @staticmethod) ==========


@pytest.fixture
@staticmethod
def mock_user_repo():
    """Mock do UserRepository."""
    repo = AsyncMock()
    repo.get_by_email = AsyncMock()
    repo.commit = AsyncMock()
    repo.update_password = AsyncMock()
    repo.get_by_public_id = AsyncMock()
    repo.get = AsyncMock()
    return repo


@pytest.fixture
@staticmethod
def mock_email_service():
    """Mock do EmailService."""
    service = AsyncMock()
    service.send_reset_password_email = AsyncMock()
    return service


@pytest.fixture
@staticmethod
def mock_token_repo():
    """Mock do TokenRepository."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.refresh = AsyncMock()
    repo.get_valid_token = AsyncMock()
    repo.mark_as_used = AsyncMock()
    return repo


@pytest.fixture
@staticmethod
def auth_service(mock_user_repo, mock_email_service, mock_token_repo):
    """Instância do AuthService com mocks."""
    return AuthService(
        user_repo=mock_user_repo,
        email_service=mock_email_service,
        token_repo=mock_token_repo,
    )


@pytest.fixture
@staticmethod
def mock_user(user):
    """Mock de usuário."""
    return user


# ========== Testes para login ==========


@pytest.mark.asyncio
async def test_login_success(auth_service, mock_user_repo, mock_user):
    """Testa login bem-sucedido."""
    # Arrange
    login_data = Mock()
    login_data.username = mock_user.email
    login_data.password = '123'

    mock_user_repo.get_by_email.return_value = mock_user

    # Act
    result = await auth_service.login(login_data)

    # Assert
    assert 'access_token' in result
    assert result['token_type'] == 'bearer'

    mock_user_repo.commit.assert_called_once()


@pytest.mark.asyncio
async def test_login_invalid_email(auth_service, mock_user_repo):
    """Testa login com email inválido."""
    # Arrange
    login_data = Mock()
    login_data.username = 'naoexiste@example.com'
    login_data.password = '123'

    mock_user_repo.get_by_email.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match='Incorrect Email'):
        await auth_service.login(login_data)

    mock_user_repo.update_last_login.assert_not_called()


@pytest.mark.asyncio
async def test_login_invalid_password(auth_service, mock_user_repo, mock_user):
    """Testa login com senha incorreta."""
    # Arrange
    login_data = Mock()
    login_data.username = mock_user.email
    login_data.password = 'wrongpassword'

    mock_user_repo.get_by_email.return_value = mock_user

    # Act & Assert
    with pytest.raises(ValueError, match='Incorrect Password'):
        await auth_service.login(login_data)

    mock_user_repo.update_last_login.assert_not_called()


# ========== Testes para change_new_password ==========


@pytest.mark.asyncio
async def test_change_password_success(
    auth_service, mock_user_repo, mock_user
):
    """Testa mudança de senha bem-sucedida."""
    # Arrange
    current_password = hash_password('oldpass123')

    class PasswordData:
        current_password = '123'
        new_password = 'newpass456'

    # Act
    with patch(
        'restaurante_api.services.auth_service.verify_password',
        return_value=True,
    ):
        result = await auth_service.change_new_password(
            current_password=current_password,
            data_password=PasswordData(),
            public_id='test-public-id',
        )

    # Assert
    assert result['message'] == 'Password is been changed'
    mock_user_repo.update_password.assert_called_once()


@pytest.mark.asyncio
async def test_change_password_wrong_current(auth_service, mock_user_repo):
    """Testa mudança de senha com senha atual incorreta."""
    # Arrange
    current_password = hash_password('oldpass123')

    class PasswordData:
        current_password = 'wrongpass'
        new_password = 'newpass456'

    # Act & Assert
    with patch(
        'restaurante_api.services.auth_service.verify_password',
        return_value=False,
    ):
        with pytest.raises(ValueError, match='Current password is incorrect'):
            await auth_service.change_new_password(
                current_password=current_password,
                data_password=PasswordData(),
                public_id='test-public-id',
            )


# ========== Testes para request_password_reset ==========


@pytest.mark.asyncio
async def test_request_password_reset_success(
    auth_service,
    mock_user_repo,
    mock_token_repo,
    mock_email_service,
    mock_user,
):
    """Testa solicitação de reset de senha bem-sucedida."""
    # Arrange
    email = mock_user.email
    mock_user_repo.get_by_email.return_value = mock_user

    mock_token = Mock()
    mock_token.token = '123456'
    mock_token_repo.create.return_value = mock_token

    # Act
    await auth_service.request_password_reset(email)

    # Assert
    mock_user_repo.get_by_email.assert_called_once_with(email=email)
    mock_token_repo.create.assert_called_once_with(user_id=mock_user.id)
    mock_email_service.send_reset_password_email.assert_called_once_with(
        to_email=email, token=mock_token.token, name=mock_user.username
    )


@pytest.mark.asyncio
async def test_request_password_reset_user_not_found(
    auth_service, mock_user_repo, mock_token_repo, mock_email_service
):
    """Testa solicitação de reset com email não encontrado."""
    # Arrange
    email = 'naoexiste@example.com'
    mock_user_repo.get_by_email.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match='Email is incorrect'):
        await auth_service.request_password_reset(email)

    mock_token_repo.create.assert_not_called()
    mock_email_service.send_reset_password_email.assert_not_called()


# ========== Testes para reset_password ==========


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_reset_password_success(
    auth_service, mock_token_repo, mock_user_repo, mock_user
):
    """Testa reset de senha bem-sucedido."""
    # Arrange
    token = '123456'
    new_password = mock_user.email

    mock_token = Mock()
    mock_token.user_id = mock_user.id
    mock_token_repo.get_valid_token.return_value = mock_token

    mock_user_repo.get.return_value = mock_user

    # Act
    with patch(
        'restaurante_api.services.auth_service.hash_password',
        return_value='hashed_new_pass',
    ):
        result = await auth_service.reset_password(token, new_password)

    # Assert
    assert result is None
    # ✅ Ajustar: chamado com APENAS token
    mock_token_repo.get_valid_token.assert_called_once_with(token)
    mock_user_repo.update_password.assert_called_once()
    mock_token_repo.mark_as_used.assert_called_once_with(mock_token)
    mock_user_repo.commit.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_invalid_token(
    auth_service, mock_token_repo, mock_user_repo
):
    """Testa reset com token inválido."""
    # Arrange
    token = 'invalid'
    new_password = 'newpass123'

    mock_token_repo.get_valid_token.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match='Invalid or expired token'):
        await auth_service.reset_password(token, new_password)

    mock_user_repo.update_password.assert_not_called()


@pytest.mark.asyncio
async def test_reset_password_token_user_mismatch(
    auth_service, mock_token_repo, mock_user_repo
):
    """Testa reset onde token pertence a outro usuário."""
    # Arrange
    token = '123456'
    new_password = 'newpass123'

    mock_token = Mock()
    mock_token.user_id = 999
    mock_token_repo.get_valid_token.return_value = mock_token

    mock_user_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match='User not found'):
        await auth_service.reset_password(token, new_password)
