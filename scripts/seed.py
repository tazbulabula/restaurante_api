# scripts/seed.py

import asyncio

from sqlalchemy import select

from restaurante_api.core.database import AsyncSessionLocal
from restaurante_api.core.security import hash_password
from restaurante_api.models.mesa import Mesa, TipoMesa
from restaurante_api.models.produto import CategoriaProduto, Produto
from restaurante_api.models.user import User, UserType


async def seed():
    """Popula o banco de dados com dados iniciais"""
    async with AsyncSessionLocal() as session:
        print('🌱 Iniciando seed do banco de dados...')

        # ============================================================
        # 1. CRIAR USUÁRIO ADMIN
        # ============================================================
        print('👤 Criando usuário admin...')

        query_admin = select(User).where(User.email == 'admin@restaurante.com')
        result = await session.execute(query_admin)
        admin_existente = result.scalar_one_or_none()

        if not admin_existente:
            admin = User(
                username='admin',
                email='admin@restaurante.com',
                password=hash_password('admin123'),
                phone='+244 999 999 999',
                user_type=UserType.ADMIN,
            )
            session.add(admin)
            print('✅ Admin criado: admin@restaurante.com / admin123')
        else:
            print('ℹ️ Admin já existe')

        # ============================================================
        # 2. CRIAR USUÁRIO COMUM (opcional)
        # ============================================================
        print('👤 Criando usuário comum...')

        query_user = select(User).where(User.email == 'client@restaurante.com')
        result = await session.execute(query_user)
        user_existente = result.scalar_one_or_none()

        if not user_existente:
            user = User(
                username='cliente',
                email='cliente@restaurante.com',
                password=hash_password('cliente123'),
                phone='+244 999 999 998',
                user_type=UserType.CLIENT,
            )
            session.add(user)
            print('✅ Cliente criado: cliente@restaurante.com / cliente123')
        else:
            print('ℹ️ Cliente já existe')

        # ============================================================
        # 3. CRIAR PRODUTOS
        # ============================================================
        print('🍽️ Criando produtos...')

        produtos = [
            # Principais
            Produto(
                name='Picanha Grelhada',
                price=3500.00,
                category=CategoriaProduto.PRINCIPAL,
                description='Acompanha arroz, farofa e vinagrete',
                is_available=True,
            ),
            Produto(
                name='Frango à Cafreal',
                price=2800.00,
                category=CategoriaProduto.PRINCIPAL,
                description='Frango grelhado com molho especial',
                is_available=True,
            ),
            Produto(
                name='Lasanha à Bolonhesa',
                price=3200.00,
                category=CategoriaProduto.PRINCIPAL,
                description='Lasanha com molho à bolonhesa e queijo gratinado',
                is_available=True,
            ),
            Produto(
                name='Pizza Margherita',
                price=2500.00,
                category=CategoriaProduto.PRINCIPAL,
                description='Mussarela, tomate e manjericão',
                is_available=True,
            ),
            # Entradas
            Produto(
                name='Salada Caesar',
                price=1500.00,
                category=CategoriaProduto.ENTRADA,
                description='Alface, frango, croutons e molho caesar',
                is_available=True,
            ),
            Produto(
                name='Pastel de Carne (3 un)',
                price=850.00,
                category=CategoriaProduto.PETISCO,
                description='Pastéis crocantes recheados com carne',
                is_available=True,
            ),
            # Bebidas
            Produto(
                name='Coca-Cola',
                price=350.00,
                category=CategoriaProduto.REFRIGERANTE,
                description='Lata 350ml',
                is_available=True,
            ),
            Produto(
                name='Suco de Laranja',
                price=450.00,
                category=CategoriaProduto.SUCOS,
                description='Suco natural',
                is_available=True,
            ),
            Produto(
                name='Cerveja Cuca',
                price=380.00,
                category=CategoriaProduto.CERVEJA,
                description='Garrafa 330ml',
                is_available=True,
            ),
            Produto(
                name='Café Expresso',
                price=250.00,
                category=CategoriaProduto.CAFE,
                description='Café encorpado',
                is_available=True,
            ),
            # Sobremesas
            Produto(
                name='Mousse de Chocolate',
                price=650.00,
                category=CategoriaProduto.SOBREMESA,
                description='Chocolate belga com raspas',
                is_available=True,
            ),
        ]

        for produto in produtos:
            query = select(Produto).where(Produto.name == produto.name)
            result = await session.execute(query)
            existente = result.scalar_one_or_none()
            if not existente:
                session.add(produto)
        print(f'✅ {len(produtos)} produtos adicionados')

        # ============================================================
        # 4. CRIAR MESAS
        # ============================================================
        print('🪑 Criando mesas...')

        mesas = [
            Mesa(
                numero=1,
                capacidade=2,
                tipo=TipoMesa.PADRAO,
                localizacao='Salão Principal',
            ),
            Mesa(
                numero=2,
                capacidade=4,
                tipo=TipoMesa.PADRAO,
                localizacao='Salão Principal',
            ),
            Mesa(
                numero=3,
                capacidade=4,
                tipo=TipoMesa.PADRAO,
                localizacao='Salão Principal',
            ),
            Mesa(
                numero=4,
                capacidade=6,
                tipo=TipoMesa.PADRAO,
                localizacao='Salão Principal',
            ),
            Mesa(
                numero=5,
                capacidade=2,
                tipo=TipoMesa.JANTAR,
                localizacao='Área VIP',
            ),
            Mesa(
                numero=6,
                capacidade=4,
                tipo=TipoMesa.VIP,
                localizacao='Área VIP',
            ),
            Mesa(
                numero=7,
                capacidade=8,
                tipo=TipoMesa.VIP,
                localizacao='Área VIP',
            ),
            Mesa(
                numero=8,
                capacidade=4,
                tipo=TipoMesa.EXTERNA,
                localizacao='Terraço',
            ),
            Mesa(
                numero=9,
                capacidade=6,
                tipo=TipoMesa.EXTERNA,
                localizacao='Terraço',
            ),
            Mesa(
                numero=10,
                capacidade=2,
                tipo=TipoMesa.BAR,
                localizacao='Balcão',
            ),
        ]

        for mesa in mesas:
            query = select(Mesa).where(Mesa.numero == mesa.numero)
            result = await session.execute(query)
            existente = result.scalar_one_or_none()
            if not existente:
                session.add(mesa)
        print(f'✅ {len(mesas)} mesas adicionadas')

        # ============================================================
        # COMMIT FINAL
        # ============================================================
        await session.commit()
        print('\n🎉 Seed concluído com sucesso!')


async def main():
    try:
        await seed()
    except Exception as e:
        print(f'❌ Erro durante o seed: {str(e)}')
        raise


if __name__ == '__main__':
    asyncio.run(main())
