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

    FRONTEND_URL: str = 'http://localhost:3000'

    # Email de suporte (opcional)
    MAIL_SUPPORT: str = 'suporte@restaurante_aurora.com'
