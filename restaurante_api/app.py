from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from restaurante_api.api.routers import (
    auth,
    dashboard,
    mesas,
    pagamentos,
    pedidos,
    produtos,
    reservas,
    users,
)
from restaurante_api.core.settings import settings

app = FastAPI(
    title='Restaurante API',
    version='1.0.0',
    description='API for Restaurante Management',
    swagger_ui_parameters={'syntaxHighlight': False},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(produtos.router)
app.include_router(mesas.router)
app.include_router(reservas.router)
app.include_router(pedidos.router)
app.include_router(pagamentos.router)
app.include_router(dashboard.router)

app.mount(
    settings.STATIC_URL,
    StaticFiles(directory=settings.upload_path),
    name='static',
)


@app.get('/')
def read_root():
    return {'message': 'Welcome to the Restaurante API!'}
