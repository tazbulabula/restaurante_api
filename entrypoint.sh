#!/bin/bash

echo "Aguardando banco de dados..."
sleep 2

echo "Rodando migrações..."
alembic upgrade head || echo "Migrações já aplicadas ou falha"

echo "Rodando seed (dados iniciais)..."
python scripts/seed.py || echo "Seed já executado ou falha"

echo "Iniciando servidor..."
uvicorn restaurante_api.app:app --host 0.0.0.0 --port 8000