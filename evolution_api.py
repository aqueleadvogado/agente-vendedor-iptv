"""
Wrapper para a Evolution API — envio e recepção de mensagens WhatsApp
"""

import requests
import logging
import re
import config

log = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "apikey":       config.EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }


def _url(path: str) -> str:
    return f"{config.EVOLUTION_BASE_URL}/{path.lstrip('/')}"


def _numero_limpo(numero: str) -> str:
    """Remove tudo que não for dígito e garante o código do país."""
    n = re.sub(r"\D", "", numero)
    if not n.startswith("55"):
        n = "55" + n
    return n


# ─────────────────────────────────────────────
# Envio de Mensagens
# ─────────────────────────────────────────────

def enviar_texto(numero: str, texto: str) -> dict:
    """Envia mensagem de texto simples."""
    payload = {
        "number": _numero_limpo(numero),
        "text":   texto,
        "delay":  500,
    }
    resp = requests.post(
        _url(f"/message/sendText/{config.EVOLUTION_INSTANCE}"),
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def enviar_imagem(numero: str, url_imagem: str, legenda: str = "") -> dict:
    """Envia imagem (ex: QR Code Pix)."""
    payload = {
        "number": _numero_limpo(numero),
        "mediatype": "image",
        "mimetype": "image/png",
        "media": url_imagem,
        "caption": legenda,
    }
    resp = requests.post(
        _url(f"/message/sendMedia/{config.EVOLUTION_INSTANCE}"),
        headers=_headers(),
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def marcar_como_lida(numero: str, message_id: str) -> None:
    """Marca mensagem como lida (✓✓ azul)."""
    payload = {
        "readMessages": [{"id": message_id, "fromMe": False, "remote": _numero_limpo(numero)}]
    }
    try:
        requests.post(
            _url(f"/chat/markMessageAsRead/{config.EVOLUTION_INSTANCE}"),
            headers=_headers(),
            json=payload,
            timeout=10,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────
# Configuração de Webhook
# ─────────────────────────────────────────────

def configurar_webhook(webhook_url: str) -> dict:
    """
    Registra a URL de webhook na instância Evolution para receber mensagens.
    Chame uma vez durante o setup.
    Compatível com Evolution API v2 (usa POST em vez de PUT).
    """
    payload = {
        "webhook": {
            "enabled": True,
            "url":     webhook_url,
            "events":  ["MESSAGES_UPSERT"],
            "webhookByEvents": False,
            "webhookBase64":   False,
        }
    }
    resp = requests.post(
        _url(f"/webhook/set/{config.EVOLUTION_INSTANCE}"),
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def status_instancia() -> str:
    """Retorna o estado da conexão: open, close, connecting."""
    try:
        resp = requests.get(
            _url(f"/instance/connectionState/{config.EVOLUTION_INSTANCE}"),
            headers=_headers(),
            timeout=10,
        )
        data = resp.json()
        return data.get("instance", {}).get("state", "unknown")
    except Exception as e:
        log.warning("Erro ao consultar instância: %s", e)
    return "unknown"


# ─────────────────────────────────────────────
# Parsear Webhook
# ─────────────────────────────────────────────

def parsear_mensagem(payload: dict) -> dict | None:
    """
    Extrai informações úteis de um webhook da Evolution API.
    Retorna None se não for uma mensagem de entrada válida.
    """
    try:
        data = payload.get("data", {})
        key  = data.get("key", {})

        # Ignorar mensagens próprias e de grupos
        if key.get("fromMe"):
            return None
        jid = key.get("remoteJid", "")
        if "@g.us" in jid:
            return None

        numero = re.sub(r"\D", "", jid.replace("@s.whatsapp.net", ""))

        # Extrair texto da mensagem
        msg = data.get("message", {})
        texto = (
            msg.get("conversation")
            or msg.get("extendedTextMessage", {}).get("text")
            or ""
        ).strip()

        return {
            "numero":     numero,
            "nome":       data.get("pushName", "Cliente"),
            "texto":      texto,
            "message_id": key.get("id", ""),
            "timestamp":  data.get("messageTimestamp", 0),
        }
    except Exception as e:
        log.warning("Erro ao parsear mensagem: %s", e)
        return None
