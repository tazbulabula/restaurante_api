# tests/factories/produto_factory.py

import factory
from faker import Faker as FakeGenerator

from restaurante_api.models.produto import CategoriaProduto
from restaurante_api.schemas.produto import ProduceCreate

fake = FakeGenerator()


class ProduceFactory(factory.Factory):
    """Factory para criar produtos em testes."""

    class Meta:
        model = ProduceCreate

    name = factory.Sequence(lambda n: f'Produto {n}')
    description = factory.LazyAttribute(lambda _: fake.sentence(nb_words=10))
    price = factory.LazyAttribute(
        lambda _: round(fake.random_number(digits=4, fix_len=False), 2)
    )
    category = factory.LazyAttribute(
        lambda _: fake.random_element(elements=list(CategoriaProduto))
    )
    subcategory = factory.LazyAttribute(
        lambda _: fake.word() if fake.boolean() else None
    )
    is_available = True
    image_url = factory.LazyAttribute(
        lambda _: fake.image_url() if fake.boolean() else None
    )
