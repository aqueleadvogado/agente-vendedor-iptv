"""
Wrapper para a API do Asaas — geração de cobranças Pix
"""

import requests
import logging
from datetime import datetime, timedelta
import config

log = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "access_token": config.ASAAS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, path: str, **kwargs):
    url = f"{config.ASAAS_BASE_URL}/{path.lstrip('/')}"
    resp = requests.request(method, url, headers=_headers(), timeout=20, **kwargs)
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────
# Clientes no Asaas
# ─────────────────────────────────────────────

def obter_ou_criar_cliente(nome: str, cpf_cnpj: str, whatsapp: str) -> str:
    """
    Retorna o ID do cliente Asaas. Cria se não existir.
    """
    # Tenta buscar pelo CPF/CNPJ
    cpf_limpo = "".join(filter(str.isdigit, cpf_cnpj))
    data = _request("GET", f"/customers?cpfCnpj={cpf_limpo}")
    clientes = data.get("data", [])
    if clientes:
        return clientes[0]["id"]

    # Cria novo cliente
    payload = {
        "name":     nome,
        "cpfCnpj":  cpf_limpo,
        "mobilePhone": whatsapp,
    }
    novo = _request("POST", "/customers", json=payload)
    return novo["id"]


# ─────────────────────────────────────────────
# Cobranças Pix
# ─────────────────────────────────────────────

def criar_cobranca_pix(
    customer_id: str,
    valor: float,
    descricao: str,
    dias_vencimento: int = 1,
) -> dict:
    """
    Cria uma cobrança Pix e retorna o código copia-e-cola e o link de pagamento.
    """
    vencimento = (datetime.now() + timedelta(days=dias_vencimento)).strftime("%Y-%m-%d")

    payload = {
        "customer":    customer_id,
        "billingType": "PIX",
        "value":       round(valor, 2),
        "dueDate":     vencimento,
        "description": descricao,
        "externalReference": f"legacy_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }

    cobranca = _request("POST", "/payments", json=payload)
    payment_id = cobranca["id"]

    # Busca o QR Code Pix
    pix = _request("GET", f"/payments/{payment_id}/pixQrCode")

    return {
        "id":           payment_id,
        "valor":        valor,
        "vencimento":   vencimento,
        "pix_copia_cola": pix.get("payload", ""),
        "link_pagamento": cobranca.get("invoiceUrl", ""),
        "qr_code_url":  pix.get("encodedImage", ""),
    }


def formatar_pix_whatsapp(cobranca: dict, plano_nome: str) -> str:
    """Formata mensagem de Pix para enviar no WhatsApp."""
    valor_fmt = f"R$ {cobranca['valor']:.2f}".replace(".", ",")
    msg = (
        f"✅ *Pedido recebido!*\n\n"
        f"📺 Plano: *{plano_nome}*\n"
        f"💰 Valor: *{valor_fmt}*\n"
        f"📅 Vence: {cobranca['vencimento']}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔑 *PIX Copia e Cola:*\n"
        f"`{cobranca['pix_copia_cola']}`\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"👆 Copie o código acima e cole no seu banco.\n"
        f"Após o pagamento confirmado, enviarei seus dados de acesso em instantes! 🚀"
    )
    return msg


def verificar_pagamento(payment_id: str) -> str:
    """Retorna o status do pagamento: PENDING, RECEIVED, CONFIRMED, OVERDUE, etc."""
    data = _request("GET", f"/payments/{payment_id}")
    return data.get("status", "PENDING")
