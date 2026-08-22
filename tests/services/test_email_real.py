# scripts/test_email_isolated.py
import asyncio

import pytest
from dotenv import load_dotenv

from restaurante_api.services.email_service import EmailService

# Carregar variáveis de ambiente
load_dotenv()


@pytest.mark.asyncio
async def test_email():
    email_service = EmailService()

    try:
        await email_service.send_reset_password_email(
            to_email='tazcmanongobulabula@gmail.com',
            token='123456',
            name='Teste',
        )
        print('✅ Email enviado com sucesso!')
    except Exception as e:
        print(f'❌ Erro ao enviar: {e}')


if __name__ == '__main__':
    asyncio.run(test_email())
