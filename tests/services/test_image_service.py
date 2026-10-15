# tests/services/test_image_service.py

import io

import pytest
from fastapi import HTTPException, UploadFile

from restaurante_api.core.settings import settings
from restaurante_api.services.image_service import ImageService


def _upload(
    filename: str, content: bytes = b'\xff\xd8\xff\xe0' + b'\x00' * 100
):
    return UploadFile(filename=filename, file=io.BytesIO(content))


@pytest.mark.asyncio
async def test_salvar_imagem_sucesso(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'UPLOAD_DIR', str(tmp_path))

    up = _upload('foto.jpg')
    url = await ImageService.salvar_imagem_produto(up, 'abc-123')

    assert url.startswith('/static/produtos/')
    assert url.endswith('.jpg')

    nome = url.split('/')[-1]
    caminho = settings.products_upload_path / nome
    assert caminho.is_file()
    assert caminho.read_bytes() == b'\xff\xd8\xff\xe0' + b'\x00' * 100


@pytest.mark.asyncio
async def test_salvar_imagem_extensao_invalida():
    up = _upload('malware.exe')
    with pytest.raises(HTTPException) as exc:
        await ImageService.salvar_imagem_produto(up, 'abc')
    assert exc.value.status_code == int(400)
    assert 'não permitida' in exc.value.detail


@pytest.mark.asyncio
async def test_salvar_imagem_sem_extensao():
    up = _upload('semextensao')
    with pytest.raises(HTTPException) as exc:
        await ImageService.salvar_imagem_produto(up, 'abc')
    assert exc.value.status_code == int(400)


@pytest.mark.asyncio
async def test_salvar_imagem_vazia():
    up = _upload('vazia.jpg', content=b'')
    with pytest.raises(HTTPException) as exc:
        await ImageService.salvar_imagem_produto(up, 'abc')
    assert exc.value.status_code == int(400)
    assert 'vazio' in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_salvar_imagem_demasiado_grande(monkeypatch):
    monkeypatch.setattr(settings, 'MAX_UPLOAD_SIZE_MB', 1)
    grande = b'\xff\xd8\xff\xe0' + b'\x00' * (2 * 1024 * 1024)
    up = _upload('grande.jpg', content=grande)

    with pytest.raises(HTTPException) as exc:
        await ImageService.salvar_imagem_produto(up, 'abc')
    assert exc.value.status_code == int(413)


def test_remover_imagem(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'UPLOAD_DIR', str(tmp_path))

    # cria ficheiro manualmente
    nome = 'abc_123.jpg'
    caminho = settings.products_upload_path / nome
    caminho.write_bytes(b'x')
    assert caminho.is_file()

    ImageService.remover_imagem(f'/static/produtos/{nome}')
    assert not caminho.is_file()


def test_remover_imagem_url_externa():
    # não deve rebentar com URL externa
    ImageService.remover_imagem('https://cdn.exemplo.com/x.jpg')
