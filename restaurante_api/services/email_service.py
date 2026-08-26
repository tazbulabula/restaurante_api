# services/email_service.py

import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from restaurante_api.core.settings import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.settings = settings
        self.template_dir = (
            Path(__file__).parent.parent / 'templates' / 'email'
        )
        self.jinja_env = None

        if self.template_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=True,
            )
        else:
            logger.warning(
                'Diretório de templates não encontrado: %s', self.template_dir
            )

    def _get_template(self, template_name: str):
        """Retorna o template Jinja2"""
        if not self.jinja_env:
            raise FileNotFoundError(f'Template {template_name} não encontrado')
        return self.jinja_env.get_template(template_name)

    @staticmethod
    def _get_fallback_email(template_type: str, **kwargs) -> str:
        """Cria um email simples em HTML como fallback"""
        if template_type == 'reset_password':
            name = kwargs.get('name', '')
            reset_link = kwargs.get('reset_link', '')
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Redefinição de Senha</title>
            </head>
            <body style="font-family: Arial, sans-serif;
            max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #d4a82e;">🍽️ Restaurante Aurora</h1>
                <h2>Redefinição de Senha</h2>
                <p>Olá <strong>{name}</strong>,</p>
                <p>Clique no link abaixo para redefinir sua senha:</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p>Este link é válido por <strong>1 hora</strong>.</p>
                <hr>
                <p style="color: #999; font-size: 12px;">
                    © 2026 Restaurante Aurora
                </p>
            </body>
            </html>
            """

        if template_type == 'welcome':
            name = kwargs.get('name', '')
            frontend_url = kwargs.get('frontend_url', '')
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Bem-vindo!</title>
            </head>
            <body style="font-family: Arial, sans-serif;
            max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #d4a82e;">🍽️ Restaurante Aurora</h1>
                <h2>🎉 Bem-vindo ao Restaurante Aurora!</h2>
                <p>Olá <strong>{name}</strong>,</p>
                <p>
                    Estamos muito felizes em tê-lo como parte da nossa família!
                </p>
                <p>Com sua conta, você pode:</p>
                <ul>
                    <li>🍽️ Fazer pedidos online</li>
                    <li>📅 Reservar mesas</li>
                    <li>📋 Acompanhar seus pedidos</li>
                </ul>
                <p>
                    Acesse nosso site:
                    <a href="{frontend_url}">{frontend_url}</a>
                </p>
                <hr>
                <p style="color: #999; font-size: 12px;">
                    © 2026 Restaurante Aurora
                </p>
            </body>
            </html>
            """

        return ''

    @staticmethod
    def _build_email_message(
        to_email: str,
        subject: str,
        html_body: str,
    ) -> MIMEMultipart:
        """Constrói a mensagem de email"""
        msg = MIMEMultipart('alternative')
        msg['From'] = f'{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>'
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        return msg

    @staticmethod
    async def _send_email(msg: MIMEMultipart) -> None:
        """Envia o email usando aiosmtplib"""
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_USE_TLS,
                start_tls=False,
                timeout=30,
            )
        except aiosmtplib.SMTPAuthenticationError as e:
            logger.error('❌ Erro de autenticação SMTP: %s', e)
            raise
        except aiosmtplib.SMTPException as e:
            logger.error('❌ Erro SMTP: %s', e)
            raise
        except Exception as e:
            logger.error('❌ Erro ao enviar email: %s', e)
            raise

    def _render_template(
        self,
        template_name: str,
        context: dict,
        fallback_type: str,
        fallback_context: dict,
    ) -> str:
        """Renderiza um template Jinja2 ou usa fallback"""
        try:
            template = self._get_template(template_name)
            return template.render(**context)
        except TemplateNotFound, FileNotFoundError:
            return self._get_fallback_email(fallback_type, **fallback_context)

    # ============================================================
    # EMAIL DE RESET DE SENHA
    # ============================================================

    async def send_reset_password_email(
        self,
        to_email: str,
        token: str,
        name: Optional[str] = None,
    ) -> bool:
        """Envia email com token para reset de senha."""
        if not name:
            name = to_email.split('@', maxsplit=1)[0]

        reset_link = f'{settings.FRONTEND_URL}/redefinir-senha?token={token}'

        return await self._send_templated_email({
            'to_email': to_email,
            'subject': '🔐 Redefinição de Senha - Restaurante Aurora',
            'template_name': 'reset_password.html',
            'context': {
                'name': name,
                'token': token,
                'reset_link': reset_link,
                'frontend_url': settings.FRONTEND_URL,
                'year': datetime.now().year,
            },
            'fallback_type': 'reset_password',
            'fallback_context': {'name': name, 'reset_link': reset_link},
        })

    # ============================================================
    # EMAIL DE BOAS-VINDAS
    # ============================================================

    async def send_welcome_email(self, to_email: str, name: str) -> bool:
        """Envia email de boas-vindas após o registro."""
        return await self._send_templated_email({
            'to_email': to_email,
            'subject': '🎉 Bem-vindo ao Restaurante Aurora!',
            'template_name': 'welcome.html',
            'context': {
                'name': name,
                'frontend_url': settings.FRONTEND_URL,
                'year': datetime.now().year,
            },
            'fallback_type': 'welcome',
            'fallback_context': {
                'name': name,
                'frontend_url': settings.FRONTEND_URL,
            },
        })

    # ============================================================
    # MÉTODO PRINCIPAL DE ENVIO (com 1 argumento)
    # ============================================================

    async def _send_templated_email(
        self,
        email_data: dict,
    ) -> bool:
        """
        Envia um email usando template.

        Args:
            email_data: Dict com os dados do email
                - to_email: str
                - subject: str
                - template_name: str
                - context: dict
                - fallback_type: str
                - fallback_context: dict
        """
        to_email = email_data['to_email']
        subject = email_data['subject']
        template_name = email_data['template_name']
        context = email_data['context']
        fallback_type = email_data['fallback_type']
        fallback_context = email_data['fallback_context']

        logger.info('📨 Preparando email para: %s', to_email)

        try:
            html_body = self._render_template(
                template_name,
                context,
                fallback_type,
                fallback_context,
            )

            msg = self._build_email_message(to_email, subject, html_body)
            await self._send_email(msg)

            logger.info('✅ Email enviado para: %s', to_email)
            return True

        except Exception as e:
            logger.error('❌ Erro ao enviar email para %s: %s', to_email, e)
            return False
