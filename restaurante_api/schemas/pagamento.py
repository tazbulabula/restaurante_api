# restaurante_api/schemas/pagamento.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from restaurante_api.models.pedido import StatusPedido

# ============ INICIAR PAGAMENTO ============


class IniciarPagamentoRequest(BaseModel):
    """Request para iniciar pagamento via EMIS/vPOS"""
    pedido_public_id: str = Field(..., description="Public ID do pedido")
    telefone: str = Field(
        ...,
        min_length=9,
        max_length=20,
        description="Número de telefone do cliente (Multicaixa Express)"
    )


class IniciarPagamentoResponse(BaseModel):
    """Resposta ao iniciar pagamento"""
    transacao_id: str = Field(..., description="ID da transação na EMIS")
    pedido_id: int
    pedido_public_id: str
    valor: float
    status: str = Field(..., description="Status da transação")
    mensagem: str
    instrucoes: str = Field(
        default="Aguardando confirmação no Multicaixa Express"
    )


# ============ CALLBACK EMIS ============

class CallbackPagamento(BaseModel):
    """Callback recebido da EMIS/vPOS"""
    transacao_id: str = Field(..., description="ID da transação")
    status: str = Field(..., description="APROVADO, REJEITADO, CANCELADO")
    valor: float = Field(..., description="Valor da transação")
    codigo_autorizacao: Optional[str] = Field(
        None, description="Código de autorização (se aprovado)"
    )
    mensagem: Optional[str] = Field(None, description="Mensagem da operadora")
    data_hora: Optional[datetime] = Field(
        None, description="Data e hora da confirmação"
    )

    @field_validator('status')
    def validate_status(cls, v: str) -> str:
        valid_status = ['APROVADO', 'REJEITADO', 'CANCELADO']
        if v not in valid_status:
            raise ValueError(
                f'Status inválido: {v}. Valores permitidos: {valid_status}'
            )
        return v


class CallbackResponse(BaseModel):
    """Resposta do callback para a EMIS"""
    status: str = Field(
        default="OK", description="Status do processamento do callback"
    )
    transacao_id: str
    message: str = Field(default="Callback processado com sucesso")


# ============ CONSULTAR STATUS ============

class ConsultarStatusPagamentoResponse(BaseModel):
    """Resposta para consulta de status de pagamento"""
    pedido_id: int
    pedido_public_id: str
    status_pedido: StatusPedido
    transacao_id: Optional[str] = None
    valor: float
    pagamento_confirmado_em: Optional[datetime] = None
    codigo_autorizacao: Optional[str] = None
    mensagem: str
