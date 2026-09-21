"""
Scheduler de avisos de vencimento
Execute como tarefa agendada no PythonAnywhere (diariamente às 09:00)
"""

import logging
import sys
import os

# Garante que o módulo encontra os outros arquivos do projeto
sys.path.insert(0, os.path.dirname(__file__))

import legacy_api
import evolution_api
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


MENSAGEM_VENCIMENTO = (
    "⚠️ *Aviso de Vencimento — {empresa}*\n\n"
    "Olá! Seu plano *{plano}* vence em *{dias} dia(s)*, no dia *{vencimento}*.\n\n"
    "Para renovar e não perder o acesso, responda esta mensagem ou "
    "acesse o link de pagamento:\n\n"
    "💬 Responda *menu* para renovar agora!\n\n"
    "Dúvidas? Fale com o suporte: {suporte}"
)

MENSAGEM_VENCIDO = (
    "❌ *Plano Expirado — {empresa}*\n\n"
    "Olá! Seu plano *{plano}* expirou.\n\n"
    "Para reativar seu acesso, responda *menu* e siga as instruções.\n\n"
    "📞 Suporte: {suporte}"
)


def _dias_restantes(vencimento_str: str) -> int:
    """Calcula quantos dias faltam para o vencimento."""
    from datetime import datetime
    try:
        venc = datetime.strptime(vencimento_str, "%d/%m/%Y %H:%M")
        delta = venc - datetime.now()
        return delta.days
    except Exception:
        return 999


def enviar_avisos() -> None:
    """
    Busca clientes que vencem em breve e envia aviso no WhatsApp.
    Executa diariamente via tarefa agendada do PythonAnywhere.
    """
    log.info("Iniciando envio de avisos de vencimento...")

    try:
        clientes = legacy_api.clientes_vencendo(dias=config.DIAS_AVISO_VENCIMENTO)
    except Exception as e:
        log.error("Erro ao buscar clientes vencendo: %s", e)
        return

    log.info("%d cliente(s) próximos do vencimento", len(clientes))
    enviados = 0
    sem_whatsapp = 0

    for cliente in clientes:
        whatsapp = cliente.get("whatsapp", "").strip()
        if not whatsapp:
            log.warning("Cliente %s sem WhatsApp cadastrado", cliente.get("username"))
            sem_whatsapp += 1
            continue

        dias = _dias_restantes(cliente["vencimento"])

        if dias < 0:
            mensagem = MENSAGEM_VENCIDO.format(
                empresa=config.NOME_EMPRESA,
                plano=cliente["plano"],
                suporte=config.WHATSAPP_NUMBER,
            )
        else:
            mensagem = MENSAGEM_VENCIMENTO.format(
                empresa=config.NOME_EMPRESA,
                plano=cliente["plano"],
                dias=max(dias, 0),
                vencimento=cliente["vencimento"],
                suporte=config.WHATSAPP_NUMBER,
            )

        try:
            evolution_api.enviar_texto(whatsapp, mensagem)
            log.info("Aviso enviado para %s (vence: %s)", whatsapp, cliente["vencimento"])
            enviados += 1
        except Exception as e:
            log.error("Erro ao enviar aviso para %s: %s", whatsapp, e)

    log.info(
        "Avisos concluídos. Enviados: %d | Sem WhatsApp: %d | Total: %d",
        enviados, sem_whatsapp, len(clientes)
    )


if __name__ == "__main__":
    enviar_avisos()
