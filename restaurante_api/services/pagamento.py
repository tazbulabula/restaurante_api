# restaurante_api/services/pagamento.py

import logging
from datetime import datetime
from typing import Any, Dict

import httpx

from restaurante_api.core import settings

logger = logging.getLogger(__name__)


class EMISService:
    """Serviço de integração com a vPOS da EMIS (Multicaixa Express)"""

    def __init__(self):
        self.base_url = settings.EMIS_API_URL
        self.pos_id = settings.EMIS_POS_ID
        self.token = settings.EMIS_MERCHANT_TOKEN
        self.supervisor_card = settings.EMIS_SUPERVISOR_CARD
        self.callback_url = settings.EMIS_CALLBACK_URL
        self.timeout = settings.PAGAMENTO_TIMEOUT_SEGUNDOS

    async def iniciar_pagamento(
        self,
        pedido_id: int,
        pedido_public_id: str,
        valor: float,
        telefone: str,
        descricao: str = "Pedido Restaurante"
    ) -> Dict[str, Any]:
        """
        Inicia uma transação de pagamento via Multicaixa Express

        Args:
            pedido_id: ID do pedido
            pedido_public_id: Public ID do pedido
            valor: Valor a ser pago (em Kz)
            telefone: Número do cliente (Multicaixa Express)
            descricao: Descrição da transação

        Returns:
            Dict com dados da transação (transacao_id, status, etc.)

        Raises:
            Exception: Se ocorrer erro na comunicação com EMIS
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "posId": self.pos_id,
                "merchantToken": self.token,
                "telefone": telefone,
                "valor": valor,
                "referencia": f"PED-{pedido_public_id[:8]}",
                "descricao": descricao,
                "callbackUrl": self.callback_url,
            }

            p = pedido_public_id
            logger.info(
                f"Iniciando pagamento para pedido {p} - Valor: {valor} Kz"
            )

            try:
                response = await client.post(
                    f"{self.base_url}/vpos/pagamento/iniciar",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

                d = data.get('transacao_id')
                logger.info(
                    f"Pagamento iniciado com sucesso. Transação: {d}"
                )
                return {
                    "transacao_id": data.get("transacao_id"),
                    "status": data.get("status", "PENDENTE"),
                    "mensagem": data.get(
                        "mensagem", "Pagamento iniciado com sucesso"
                    ),
                    "data_hora": data.get("data_hora"),
                }

            except httpx.HTTPStatusError as e:
                s = e.response.status_code
                logger.error(
                    f"Erro HTTP na EMIS: {s} - {e.response.text}"
                )
                raise Exception(
                    f"Erro na comunicação com EMIS: {e.response.status_code}"
                )

            except httpx.TimeoutException:
                logger.error("Timeout na comunicação com EMIS")
                raise Exception("Tempo limite excedido ao comunicar com EMIS")

            except Exception as e:
                logger.error(f"Erro inesperado na EMIS: {str(e)}")
                raise Exception(f"Erro ao iniciar pagamento: {str(e)}")

    async def consultar_transacao(self, transacao_id: str) -> Dict[str, Any]:
        """
        Consulta o status de uma transação

        Args:
            transacao_id: ID da transação na EMIS

        Returns:
            Dict com dados da transação
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/vpos/transacao/{transacao_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                response.raise_for_status()
                return response.json()

            except Exception as e:
                logger.error(
                    f"Erro ao consultar transação {transacao_id}: {str(e)}"
                )
                raise Exception(f"Erro ao consultar transação: {str(e)}")

    async def processar_callback(
            self, dados: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Processa o callback recebido da EMIS

        Args:
            dados: Dados do callback

        Returns:
            Dict com status do processamento
        """
        transacao_id = dados.get("transacao_id")
        status = dados.get("status")
        t = transacao_id
        s = status
        logger.info(
            f"Processando callback para transação {t} - Status: {s}"
        )

        # Validação básica
        if not transacao_id:
            raise Exception("Callback sem transacao_id")

        if status not in {"APROVADO", "REJEITADO", "CANCELADO"}:
            logger.warning(f"Status desconhecido no callback: {status}")
            status = "DESCONHECIDO"

        return {
            "transacao_id": transacao_id,
            "status": status,
            "valor": dados.get("valor", 0.0),
            "codigo_autorizacao": dados.get("codigo_autorizacao"),
            "mensagem": dados.get("mensagem"),
            "data_hora": dados.get("data_hora", datetime.now().isoformat()),
        }
