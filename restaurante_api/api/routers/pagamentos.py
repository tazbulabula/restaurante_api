# restaurante_api/routes/pagamento.py

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
# 1. INICIAR PAGAMENTO
# ============================================================
@router.post(
    '/iniciar',
    response_model=IniciarPagamentoResponse,
    status_code=status.HTTP_200_OK,
    summary='Iniciar pagamento',
    description=(
            'Inicia uma transação de pagamento via Multicaixa Express (EMIS/vPOS)'
    ),
)
async def iniciar_pagamento(
    request: IniciarPagamentoRequest,
    session: Session,
    current_user: Current_user,
    background_tasks: BackgroundTasks,
):
    """
    Inicia o pagamento de um pedido via Multicaixa Express

    O fluxo é:
    1. Verifica se o pedido existe e pertence ao usuário
    2. Verifica se o pedido está aguardando pagamento
    3. Chama a EMIS para iniciar a transação
    4. Retorna o ID da transação para o cliente
    5. O cliente aguarda a notificação no Multicaixa Express
    """
    # Busca o pedido
    query = select(Pedido).where(
        Pedido.public_id == request.pedido_public_id
    )
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Pedido não encontrado',
        )

    # Verifica permissão: admin ou dono do pedido
    PermissionService.require_owner_or_admin(current_user, pedido.usuario_id)

    # Verifica se o pedido está aguardando pagamento
    if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'O pedido já está com status {pedido.status.value}. Não é possível iniciar pagamento.',
        )

    # Verifica se o total é válido
    if pedido.total <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Valor do pedido inválido',
        )

    try:
        # Chama o serviço EMIS
        emis = EMISService()
        resultado = await emis.iniciar_pagamento(
            pedido_id=pedido.id,
            pedido_public_id=pedido.public_id,
            valor=pedido.total,
            telefone=request.telefone,
            descricao=f"Pedido #{pedido.public_id[:8]} - Restaurante",
        )

        # Salva o transacao_id no pedido
        pedido.transacao_id = resultado.get('transacao_id')

        # Atualiza dados do pagamento
        pedido.cliente_telefone = request.telefone

        await session.commit()
        await session.refresh(pedido)

        return IniciarPagamentoResponse(
            transacao_id=resultado.get('transacao_id'),
            pedido_id=pedido.id,
            pedido_public_id=pedido.public_id,
            valor=pedido.total,
            status=resultado.get('status', 'PENDENTE'),
            mensagem=resultado.get(
                'mensagem', 'Pagamento iniciado com sucesso'
            ),
            instrucoes='Aguardando confirmação no Multicaixa Express',
        )

    except Exception as e:
        logger.error(f"Erro ao iniciar pagamento: {str(e)}")
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
    include_in_schema=False,  # Opcional: esconder da documentação
)
async def callback_emis(
    callback_data: CallbackPagamento,
    session: Session,
    background_tasks: BackgroundTasks,
):
    """
    Recebe o callback da EMIS/vPOS e processa o resultado do pagamento

    Este endpoint é chamado automaticamente pela EMIS após a confirmação
    ou rejeição do pagamento no Multicaixa Express.

    O processamento é feito em background para não bloquear a resposta.
    """
    logger.info(
        f"Callback recebido da EMIS: {callback_data.model_dump()}"
    )

    # Busca o pedido pelo transacao_id
    query = select(Pedido).where(
        Pedido.transacao_id == callback_data.transacao_id
    )
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        logger.error(
            f"Pedido não encontrado para transação {callback_data.transacao_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Pedido não encontrado para esta transação',
        )

    # Processa o callback em background
    background_tasks.add_task(
        processar_callback_pagamento,
        pedido_id=pedido.id,
        callback_data=callback_data,
    )

    return CallbackResponse(
        status="OK",
        transacao_id=callback_data.transacao_id,
        message="Callback recebido e processando em background",
    )


# ============================================================
# FUNÇÃO DE PROCESSAMENTO EM BACKGROUND
# ============================================================

async def processar_callback_pagamento(
    pedido_id: int,
    callback_data: CallbackPagamento,
    session: Session = None,
):
    """
    Processa o callback do pagamento em background

    Esta função atualiza o status do pedido e da reserva com base no
    resultado do pagamento.
    """

    from restaurante_api.core.database import get_session

    # Cria uma sessão separada para o processamento em background
    async for session in get_session():
        try:
            async with session as sess:
                # Busca o pedido novamente
                pedido = await sess.get(Pedido, pedido_id)

                if not pedido:
                    logger.error(
                        f"Pedido {pedido_id} não encontrado para processamento"
                    )
                    return

                # Verifica se o pedido ainda está aguardando pagamento
                if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
                    p = pedido_id
                    logger.warning(
                        f"Pedido {p} já processado. Status atual: {pedido.status}"
                    )
                    return

                # Processa o resultado
                if callback_data.status == "APROVADO":
                    # Pagamento aprovado
                    pedido.status = StatusPedido.PAGO
                    pedido.pagamento_confirmado_em = callback_data.data_hora or datetime.now()
                    pedido.codigo_autorizacao = callback_data.codigo_autorizacao
                    pedido.pagamento_dados = callback_data.model_dump()

                    # Atualiza a reserva se existir
                    if pedido.reserva_mesa_id:
                        reserva = await sess.get(
                            ReservaMesa, pedido.reserva_mesa_id
                        )
                        if reserva:
                            reserva.status = StatusMesa.CONFIRMADA

                    logger.info(
                        f"Pagamento aprovado para pedido {pedido_id}"
                    )

                elif callback_data.status == "REJEITADO":
                    # Pagamento rejeitado
                    pedido.status = StatusPedido.AGUARDANDO_PAGAMENTO
                    pedido.pagamento_dados = callback_data.model_dump()
                    logger.warning(f"Pagamento rejeitado para pedido {pedido_id}")

                elif callback_data.status == "CANCELADO":
                    # Pagamento cancelado
                    pedido.status = StatusPedido.AGUARDANDO_PAGAMENTO
                    pedido.pagamento_dados = callback_data.model_dump()
                    logger.warning(
                        f"Pagamento cancelado para pedido {pedido_id}"
                    )

                else:
                    c = callback_data.status
                    logger.error(
                        f"Status desconhecido no callback: {c}"
                    )
                    return

                await sess.commit()
                await sess.refresh(pedido)

                p = pedido_id
                p_s = pedido.status
                logger.info(
                    f"Pagamento processado para pedido {p}. Novo status: {p_s}"
                )

        except Exception as e:
            logger.error(
                f"Erro ao processar callback do pedido {pedido_id}: {str(e)}"
            )
            if session:
                await session.rollback()
            raise


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
    """
    Consulta o status do pagamento de um pedido

    Retorna o status atual do pedido e informações do pagamento.
    """
    query = select(Pedido).where(Pedido.public_id == pedido_public_id)
    result = await session.execute(query)
    pedido = result.scalar_one_or_none()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Pedido não encontrado',
        )

    # Verifica permissão: admin ou dono do pedido
    PermissionService.require_owner_or_admin(current_user, pedido.usuario_id)

    # Mensagem baseada no status
    a = "Aguardando confirmação do pagamento no Multicaixa Express"
    mensagens = {
        StatusPedido.AGUARDANDO_PAGAMENTO: a,
        StatusPedido.PAGO: "Pagamento confirmado com sucesso!",
        StatusPedido.PREPARANDO: "Pagamento confirmado. Pedido em preparação.",
        StatusPedido.PRONTO: "Pagamento confirmado. Pedido pronto.",
        StatusPedido.ENTREGUE: "Pedido entregue. Obrigado!",
        StatusPedido.CANCELADO: "Pedido cancelado.",
    }

    return ConsultarStatusPagamentoResponse(
        pedido_id=pedido.id,
        pedido_public_id=pedido.public_id,
        status_pedido=pedido.status,
        transacao_id=pedido.transacao_id,
        valor=pedido.total,
        pagamento_confirmado_em=pedido.pagamento_confirmado_em,
        codigo_autorizacao=pedido.codigo_autorizacao,
        mensagem=mensagens.get(pedido.status, "Status desconhecido"),
    )
