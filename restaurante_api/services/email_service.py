# services/email_service.py
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from restaurante_api.core.settings import Settings

settings = Settings()


class EmailService:
    def __init__(self):
        # Configurar templates Jinja2
        template_dir = Path(__file__).parent.parent / 'templates' / 'email'
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir), autoescape=True
        )

    async def send_reset_password_email(
        self, to_email: str, token: str, name: str = None
    ):
        """Envia email com token para reset de senha."""

        # Renderizar template HTML
        template = self.jinja_env.get_template('reset_password.html')
        html_body = template.render(
            name=name or to_email.split('@', maxsplit=1)[0],
            token=token,
            reset_link=f'{settings.FRONTEND_URL}/reset-password?token={token}',
        )

        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = f'{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>'
        msg['To'] = to_email
        msg['Subject'] = 'Redefinição de Senha - Marketplace Aurora'
        msg.attach(MIMEText(html_body, 'html'))

        # Enviar email
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=False,
                start_tls=True,
            )
        except Exception as e:
            # Log do erro (não repassa para não expor detalhes)
            print(f'Erro ao enviar email: {e}')
            # Opcional: salvar em banco para tentar novamente depois

    async def send_welcome_email(self, to_email: str, name: str):
        """Envia email de boas-vindas."""
        # Implementação similar...
        pass
