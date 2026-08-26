from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra='ignore'
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    SMTP_HOST: str = 'smtp.gmail.com'
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    MAIL_FROM: str
    MAIL_FROM_NAME: str

    FRONTEND_URL: str = 'http://localhost:5173'

    ENVIRONMENT: str = 'development'

    # Email de suporte (opcional)
    MAIL_SUPPORT: str = 'suporte@restaurante_aurora.com'

    # ============================================================
    # EMIS/vPOS - Configurações para Angola
    # ============================================================
    EMIS_API_URL: str = 'https://apis.emis.co.ao'
    EMIS_POS_ID: str = ''  # ID do ponto de venda
    EMIS_MERCHANT_TOKEN: str = ''  # Token do comerciante
    EMIS_SUPERVISOR_CARD: str = ''  # Cartão do supervisor
    EMIS_CALLBACK_URL: str = 'http://localhost:8000/api/pagamento/callback'

    # ============================================================
    # Timeouts e Configurações
    # ============================================================
    PAGAMENTO_TIMEOUT_SEGUNDOS: int = 30
    PAGAMENTO_TENTATIVAS_MAX: int = 3

    # CORS
    CORS_ORIGINS: List[str] = [
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
        'https://seu-frontend.vercel.app'
    ]


settings = Settings()
