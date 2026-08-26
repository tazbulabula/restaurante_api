# restaurante_api/routes/pagamentos.py

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select

from restaurante_api.core.dependencies import Current_user, Session
from restaurante_api.models.mesa import StatusMesa
from restaurante_api.models.pedido import Pedido, StatusPedido
from restaurante_api.models.reserva_mesa import ReservaMesa
from restaurante_api.schemas.pagamento import (
    CallbackPagamento,
    CallbackResponse,
    ConsultarStatusPagamentoResponse,
    IniciarPagamentoRequest,
    IniciarPagamentoResponse,
)
from restaurante_api.services.pagamento import EMISService
from restaurante_api.services.permission_service import PermissionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/pagamento', tags=['pagamento'])


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================


async def _processar_pagamento_aprovado(pedido, callback_data):
    """Processa pagamento aprovado"""
    pedido.status = StatusPedido.PAGO
    pedido.pagamento_confirmado_em = callback_data.data_hora or datetime.now()
    pedido.codigo_autorizacao = callback_data.codigo_autorizacao
    pedido.pagamento_dados = callback_data.model_dump(mode='json')


async def _processar_pagamento_rejeitado(pedido, callback_data):
    """Processa pagamento rejeitado"""
    pedido.status = StatusPedido.AGUARDANDO_PAGAMENTO
    pedido.pagamento_dados = callback_data.model_dump(mode='json')


async def _processar_pagamento_cancelado(pedido, callback_data):
    """Processa pagamento cancelado"""
    pedido.status = StatusPedido.AGUARDANDO_PAGAMENTO
    pedido.pagamento_dados = callback_data.model_dump(mode='json')


async def _atualizar_reserva_se_existir(sess, pedido):
    """Atualiza a reserva se existir"""

    if pedido.reserva_mesa_id:
        reserva = await sess.get(ReservaMesa, pedido.reserva_mesa_id)
        if reserva:
            reserva.status = StatusMesa.CONFIRMADA


async def _executar_inicio_pagamento(session, pedido, request):
    """Executa o pagamento chamando a EMIS"""

    emis = EMISService()

    resultado = await emis.iniciar_pagamento(
        pedido_id=pedido.id,
        pedido_public_id=pedido.public_id,
        valor=pedido.total,
        telefone=request.telefone,
        descricao=f'Pedido #{pedido.public_id[:8]} - Restaurante',
    )

    pedido.transacao_id = resultado.get('transacao_id')
    pedido.cliente_telefone = request.telefone

    await session.commit()
    await session.refresh(pedido)

    return IniciarPagamentoResponse(
        transacao_id=resultado.get('transacao_id'),
        pedido_id=pedido.id,
        pedido_public_id=pedido.public_id,
        valor=pedido.total,
        status=resultado.get('status', 'PENDENTE'),
        mensagem=resultado.get('mensagem', 'Pagamento iniciado com sucesso'),
        instrucoes='Aguardando confirmação no Multicaixa Express',
    )


# ============================================================
# 1. INICIAR PAGAMENTO
# ============================================================


@router.post(
    '/iniciar',
    response_model=IniciarPagamentoResponse,
    status_code=status.HTTP_200_OK,
    summary='Iniciar pagamento',
    description='Inicia pagamento via Multicaixa Express (EMIS/vPOS)',
)
async def iniciar_pagamento(
    request: IniciarPagamentoRequest,
    session: Session,
    current_user: Current_user,
    background_tasks: BackgroundTasks,
):
    """Inicia o pagamento de um pedido via Multicaixa Express"""
    # Busca o pedido
    query = select(Pedido).where(Pedido.public_id == request.pedido_public_id)
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Pedido não encontrado',
        )

    PermissionService.require_owner_or_admin(current_user, pedido.usuario_id)

    if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
        msg = f'Pedido já está com status {pedido.status.value}'
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
        )

    if pedido.total <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Valor do pedido inválido',
        )

    try:
        return await _executar_inicio_pagamento(session, pedido, request)
    except Exception as e:
        logger.error(f'Erro ao iniciar pagamento: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro ao iniciar pagamento: {str(e)}',
        )


# ============================================================
# 2. CALLBACK DA EMIS
# ============================================================


@router.post(
    '/callback',
    response_model=CallbackResponse,
    status_code=status.HTTP_200_OK,
    summary='Callback EMIS',
    description='Endpoint para receber callbacks da EMIS/vPOS',
    include_in_schema=False,
)
async def callback_emis(
    callback_data: CallbackPagamento,
    session: Session,
    background_tasks: BackgroundTasks,
):
    """Recebe o callback da EMIS/vPOS e processa o resultado"""
    logger.info(f'Callback recebido da EMIS: {callback_data.model_dump()}')

    query = select(Pedido).where(
        Pedido.transacao_id == callback_data.transacao_id
    )
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        d = callback_data.transacao_id
        logger.error(f'Pedido não encontrado para transação {d}')
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Pedido não encontrado para esta transação',
        )

    background_tasks.add_task(
        processar_callback_pagamento,
        pedido_id=pedido.id,
        callback_data=callback_data,
        session=session,
    )

    return CallbackResponse(
        status='OK',
        transacao_id=callback_data.transacao_id,
        message='Callback recebido e processando em background',
    )


# ============================================================
# FUNÇÃO DE PROCESSAMENTO EM BACKGROUND
# ============================================================


async def processar_callback_pagamento(
    pedido_id: int,
    callback_data: CallbackPagamento,
    session: Session = None,
):
    """Processa o callback do pagamento em background"""

    try:
        async with session as sess:
            await _processar_callback_interno(pedido_id, callback_data, sess)
    except Exception as e:
        logger.error(
            f'Erro ao processar callback do pedido {pedido_id}: {str(e)}'
        )
        if session:
            await session.rollback()
        raise


async def _processar_callback_interno(pedido_id: int, callback_data, sess):
    """Processamento interno do callback"""
    pedido = await sess.get(Pedido, pedido_id)

    if not pedido:
        logger.error(f'Pedido {pedido_id} não encontrado')
        return

    if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
        logger.warning(
            f'Pedido {pedido_id} já processado. Status: {pedido.status}'
        )
        return

    if callback_data.status == 'APROVADO':
        await _processar_pagamento_aprovado(pedido, callback_data)
        await _atualizar_reserva_se_existir(sess, pedido)
        logger.info(f'Pagamento aprovado para pedido {pedido_id}')

    elif callback_data.status == 'REJEITADO':
        await _processar_pagamento_rejeitado(pedido, callback_data)
        logger.warning(f'Pagamento rejeitado para pedido {pedido_id}')

    elif callback_data.status == 'CANCELADO':
        await _processar_pagamento_cancelado(pedido, callback_data)
        logger.warning(f'Pagamento cancelado para pedido {pedido_id}')

    else:
        logger.error(f'Status desconhecido: {callback_data.status}')
        return

    await sess.commit()
    await sess.refresh(pedido)

    logger.info(f'Pedido {pedido_id} processado. Novo status: {pedido.status}')


# ============================================================
# 3. CONSULTAR STATUS DO PAGAMENTO
# ============================================================


@router.get(
    '/status/{pedido_public_id}',
    response_model=ConsultarStatusPagamentoResponse,
    status_code=status.HTTP_200_OK,
    summary='Consultar status do pagamento',
    description='Consulta o status do pagamento de um pedido',
)
async def consultar_status_pagamento(
    pedido_public_id: str,
    session: Session,
    current_user: Current_user,
):
    """Consulta o status do pagamento de um pedido"""
    query = select(Pedido).where(Pedido.public_id == pedido_public_id)
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Pedido não encontrado',
        )

    PermissionService.require_owner_or_admin(current_user, pedido.usuario_id)

    mensagens = {
        StatusPedido.AGUARDANDO_PAGAMENTO: (
            'Aguardando confirmação no Multicaixa Express'
        ),
        StatusPedido.PAGO: 'Pagamento confirmado com sucesso!',
        StatusPedido.PREPARANDO: 'Pagamento confirmado. Em preparação.',
        StatusPedido.PRONTO: 'Pagamento confirmado. Pedido pronto.',
        StatusPedido.ENTREGUE: 'Pedido entregue. Obrigado!',
        StatusPedido.CANCELADO: 'Pedido cancelado.',
    }

    return ConsultarStatusPagamentoResponse(
        pedido_id=pedido.id,
        pedido_public_id=pedido.public_id,
        status_pedido=pedido.status,
        transacao_id=pedido.transacao_id,
        valor=pedido.total,
        pagamento_confirmado_em=pedido.pagamento_confirmado_em,
        codigo_autorizacao=pedido.codigo_autorizacao,
        mensagem=mensagens.get(pedido.status, 'Status desconhecido'),
    )
