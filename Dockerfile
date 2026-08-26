# backend/Dockerfile

FROM python:3.14-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho como /app (padrão)
WORKDIR /app

# Instala Poetry
RUN pip install poetry

# Copia os arquivos de dependências
COPY pyproject.toml poetry.lock ./

# Instala as dependências sem instalar o projeto
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copia o código fonte
COPY . .

# Define PYTHONPATH para encontrar o módulo
ENV PYTHONPATH="/app"

# Executa migrações e seed durante o build
RUN alembic upgrade head || true
RUN python scripts/seed.py || true

# Expõe a porta
EXPOSE 8000

# Comando para rodar o servidor (com PYTHONPATH)
CMD ["python", "-m", "uvicorn", "restaurante_api.app:app", "--host", "0.0.0.0", "--port", "8000"]