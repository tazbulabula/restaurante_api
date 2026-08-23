from fastapi import FastAPI

from restaurante_api.api.routers import (
    auth,
    mesas,
    pagamentos,
    pedidos,
    produtos,
    reservas,
    users,
)

app = FastAPI(
    title='Restaurante API',
    version='1.0.0',
    description='API for Restaurante Management',
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(produtos.router)
app.include_router(mesas.router)
app.include_router(reservas.router)
app.include_router(pedidos.router)
app.include_router(pagamentos.router)


@app.get('/')
def read_root():
    return {'message': 'Welcome to the Restaurante API!'}
