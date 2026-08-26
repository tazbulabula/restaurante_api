# backend/Dockerfile

FROM python:3.11-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Instala Poetry
RUN pip install poetry

# Copia os arquivos de dependências
COPY pyproject.toml poetry.lock ./

# Instala as dependências (sem criar virtualenv)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copia o código fonte
COPY . .

# Expõe a porta
EXPOSE 8000

# Comando para rodar o servidor
CMD ["uvicorn", "restaurante_api.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]