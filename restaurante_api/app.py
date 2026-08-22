from fastapi import FastAPI

from restaurante_api.api.routers import auth, produtos, users

app = FastAPI(
    title='Restaurante API',
    version='1.0.0',
    description='API for Restaurante Management',
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(produtos.router)


@app.get('/')
def read_root():
    return {'message': 'Welcome to the Restaurante API!'}
