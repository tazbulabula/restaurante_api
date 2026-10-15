# restaurante_api/services/image_service.py

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from restaurante_api.core.settings import settings


class ImageService:
    """Serviço responsável por validar e guardar imagens de produtos."""

    @staticmethod
    def _validar_extensao(filename: str) -> str:
        if not filename or '.' not in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Ficheiro sem extensão válida.',
            )

        ext = filename.rsplit('.', 1)[-1].lower()
        if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Extensão '.{ext}' não permitida. "
                    f'Use: {", ".join(settings.ALLOWED_IMAGE_EXTENSIONS)}'
                ),
            )
        return ext

    @staticmethod
    async def _validar_tamanho(file: UploadFile) -> bytes:
        conteudo = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        if len(conteudo) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f'Imagem demasiado grande. '
                    f'Máximo: {settings.MAX_UPLOAD_SIZE_MB} MB.'
                ),
            )

        if len(conteudo) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Ficheiro vazio.',
            )

        return conteudo

    @classmethod
    async def salvar_imagem_produto(
        cls,
        file: UploadFile,
        public_id: str,
    ) -> str:
        """
        Guarda a imagem do produto e devolve a URL pública relativa.

        Ex.: /static/produtos/<public_id>.webp
        """
        ext = cls._validar_extensao(file.filename or '')
        conteudo = await cls._validar_tamanho(file)

        # Garante nome único (mesmo se o public_id já existir)
        nome_ficheiro = f'{public_id}_{uuid.uuid4().hex[:8]}.{ext}'
        destino: Path = settings.products_upload_path / nome_ficheiro

        with destino.open('wb') as f:
            f.write(conteudo)

        # URL pública relativa
        return f'{settings.STATIC_URL}/produtos/{nome_ficheiro}'

    @staticmethod
    def remover_imagem(image_url: str | None) -> None:
        """Remove o ficheiro físico associado à URL, se existir."""
        if not image_url:
            return

        prefixo = f'{settings.STATIC_URL}/produtos/'
        if not image_url.startswith(prefixo):
            return

        nome = image_url.replace(prefixo, '')
        caminho = settings.products_upload_path / nome

        if caminho.is_file():
            caminho.unlink(missing_ok=True)
