"""
Flask Webhook — recebe mensagens da Evolution API e aciona o bot
Deploy no PythonAnywhere como aplicação WSGI
"""

import logging
import hmac
import hashlib
from flask import Flask, request, jsonify

import bot
import evolution_api
import config

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)


# ─────────────────────────────────────────────
# Webhook principal (Evolution API → Bot)
# ─────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(silent=True) or {}

    # Ignora eventos que não são mensagens
    evento = payload.get("event", "")
    if evento not in ("messages.upsert", "MESSAGES_UPSERT"):
        return jsonify({"status": "ignored", "event": evento}), 200

    msg = evolution_api.parsear_mensagem(payload)
    if not msg or not msg.get("texto"):
        return jsonify({"status": "no_text"}), 200

    log.info("Mensagem recebida de %s: %s", msg["numero"], msg["texto"][:80])

    try:
        bot.processar_mensagem(
            numero=msg["numero"],
            nome=msg["nome"],
            texto=msg["texto"],
            message_id=msg["message_id"],
        )
    except Exception as e:
        log.exception("Erro ao processar mensagem de %s: %s", msg["numero"], e)
        # Não retorna erro 500 para não travar o webhook da Evolution
        return jsonify({"status": "error", "detail": str(e)}), 200

    return jsonify({"status": "ok"}), 200


# ─────────────────────────────────────────────
# Webhook do Asaas (confirmação de pagamento)
# ─────────────────────────────────────────────

@app.route("/webhook/asaas", methods=["POST"])
def webhook_asaas():
    """
    O Asaas envia um POST quando o status de pagamento muda.
    Quando confirmado, entregamos o acesso automaticamente.
    """
    payload = request.get_json(silent=True) or {}
    evento  = payload.get("event", "")
    payment = payload.get("payment", {})

    log.info("Webhook Asaas: evento=%s payment_id=%s status=%s",
             evento, payment.get("id"), payment.get("status"))

    if evento in ("PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"):
        payment_id = payment.get("id")
        if not payment_id:
            return jsonify({"status": "no_id"}), 200

        # Busca o estado que tem esse payment_id para saber o número do cliente
        import json, os
        try:
            with open(bot.ESTADOS_FILE, "r", encoding="utf-8") as f:
                estados = json.load(f)
        except Exception:
            estados = {}

        for numero, estado in estados.items():
            if estado.get("dados", {}).get("payment_id") == payment_id:
                dados = estado["dados"]
                plano = dados.get("plano_escolhido", {})
                log.info("Entregando acesso para %s (payment %s)", numero, payment_id)
                bot._entregar_acesso(numero, dados, plano)
                break

    return jsonify({"status": "ok"}), 200


# ─────────────────────────────────────────────
# Endpoints auxiliares
# ─────────────────────────────────────────────

@app.route("/setup", methods=["GET"])
def setup():
    """Configura o webhook na Evolution API. Acesse uma vez após deploy."""
    webhook_url = request.args.get("url") or request.host_url + "webhook"
    try:
        resultado = evolution_api.configurar_webhook(webhook_url)
        return jsonify({"status": "ok", "webhook_url": webhook_url, "result": resultado})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


@app.route("/status", methods=["GET"])
def status():
    """Health check — verifica conexão com Evolution API."""
    estado = evolution_api.status_instancia()
    return jsonify({
        "bot":      "online",
        "whatsapp": estado,
        "instance": config.EVOLUTION_INSTANCE,
    })


@app.route("/", methods=["GET"])
def index():
    return jsonify({"app": "Agente Vendedor IPTV", "version": "1.0"})


# ─────────────────────────────────────────────
# Entry point local (para testes)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
