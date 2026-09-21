"""
Máquina de estados do Agente Vendedor
Gerencia a conversa de cada número de WhatsApp de forma independente
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

import asaas_api
import evolution_api
import legacy_api
import config

log = logging.getLogger(__name__)

# Arquivo onde os estados das conversas ficam salvos (simples e persistente)
ESTADOS_FILE = os.path.join(os.path.dirname(__file__), "estados.json")

# ─────────────────────────────────────────────
# Persistência de estados
# ─────────────────────────────────────────────

def _carregar_estados() -> dict:
    try:
        with open(ESTADOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _salvar_estados(estados: dict) -> None:
    with open(ESTADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(estados, f, ensure_ascii=False, indent=2)


def _get_estado(numero: str) -> dict:
    estados = _carregar_estados()
    return estados.get(numero, {"etapa": "inicio", "dados": {}})


def _set_estado(numero: str, etapa: str, dados: dict = None) -> None:
    estados = _carregar_estados()
    estados[numero] = {
        "etapa":     etapa,
        "dados":     dados or {},
        "atualizado": datetime.now().isoformat(),
    }
    _salvar_estados(estados)


def _limpar_estado(numero: str) -> None:
    estados = _carregar_estados()
    estados.pop(numero, None)
    _salvar_estados(estados)


# ─────────────────────────────────────────────
# Envio de resposta (abstração)
# ─────────────────────────────────────────────

def _enviar(numero: str, texto: str) -> None:
    try:
        evolution_api.enviar_texto(numero, texto)
    except Exception as e:
        log.error("Falha ao enviar mensagem para %s: %s", numero, e)


# ─────────────────────────────────────────────
# Máquina de estados principal
# ─────────────────────────────────────────────

def processar_mensagem(numero: str, nome: str, texto: str, message_id: str = "") -> None:
    """
    Ponto de entrada: processa uma mensagem recebida e responde ao cliente.
    """
    evolution_api.marcar_como_lida(numero, message_id)

    texto_lower = texto.lower().strip()
    estado = _get_estado(numero)
    etapa  = estado["etapa"]
    dados  = estado["dados"]

    log.info("[%s] etapa=%s texto='%s'", numero, etapa, texto[:60])

    # ── Atalhos globais ──────────────────────────────────────
    if texto_lower in ("menu", "inicio", "cancelar", "0", "voltar", "oi", "olá", "ola"):
        _limpar_estado(numero)
        etapa = "inicio"

    if texto_lower in ("ajuda", "help", "#"):
        _enviar(numero, AJUDA_MSG)
        return

    # ── Roteador de etapas ───────────────────────────────────
    if etapa == "inicio":
        _etapa_inicio(numero, nome)

    elif etapa == "aguardando_escolha_plano":
        _etapa_escolha_plano(numero, nome, texto, dados)

    elif etapa == "aguardando_nome":
        _etapa_nome(numero, texto, dados)

    elif etapa == "aguardando_cpf":
        _etapa_cpf(numero, texto, dados)

    elif etapa == "aguardando_confirmacao":
        _etapa_confirmacao(numero, texto, dados)

    elif etapa == "aguardando_pagamento":
        _etapa_aguardando_pagamento(numero, texto, dados)

    else:
        _limpar_estado(numero)
        _etapa_inicio(numero, nome)


# ─────────────────────────────────────────────
# Etapas individuais
# ─────────────────────────────────────────────

def _etapa_inicio(numero: str, nome: str) -> None:
    """Saudação + lista de planos."""
    primeiro_nome = nome.split()[0] if nome else "cliente"
    saudacao = _saudacao()

    try:
        planos = legacy_api.listar_planos()
    except Exception as e:
        log.error("Erro ao buscar planos: %s", e)
        _enviar(numero,
            f"{saudacao} {primeiro_nome}! 👋\n\n"
            "Estamos com instabilidade técnica. Por favor, tente novamente em alguns minutos.\n"
            "Ou fale diretamente com nosso atendente: " + config.WHATSAPP_NUMBER
        )
        return

    if not planos:
        _enviar(numero, "Nenhum plano disponível no momento. Tente mais tarde.")
        return

    msg = (
        f"{saudacao} *{primeiro_nome}*! 👋\n"
        f"Bem-vindo à *{config.NOME_EMPRESA}*! 📺\n\n"
        + legacy_api.formatar_planos_whatsapp(planos)
    )
    _enviar(numero, msg)
    _set_estado(numero, "aguardando_escolha_plano", {"planos": planos, "nome_cliente": nome})


def _etapa_escolha_plano(numero: str, nome: str, texto: str, dados: dict) -> None:
    """Cliente digitou o número do plano."""
    planos = dados.get("planos", [])

    if texto.strip() == "0":
        _enviar(numero,
            f"Tudo bem! Você será atendido por um de nossos especialistas.\n"
            f"📞 Fale conosco: {config.WHATSAPP_NUMBER}\n\n"
            "Digite *menu* a qualquer momento para recomeçar."
        )
        _limpar_estado(numero)
        return

    try:
        idx = int(texto.strip()) - 1
        plano = planos[idx]
    except (ValueError, IndexError):
        _enviar(numero,
            f"Opção inválida. Digite o número do plano (1 a {len(planos)}) "
            "ou *0* para falar com um atendente."
        )
        return

    dados["plano_escolhido"] = plano
    preco_fmt = f"R$ {plano['preco']:.2f}".replace(".", ",")
    _enviar(numero,
        f"Ótima escolha! ✅\n\n"
        f"📺 *{plano['nome']}*\n"
        f"💰 {preco_fmt}/mês | {plano['conexoes']} tela(s)\n\n"
        "Para continuar, preciso de algumas informações.\n\n"
        "Qual é o seu *nome completo*?"
    )
    _set_estado(numero, "aguardando_nome", dados)


def _etapa_nome(numero: str, texto: str, dados: dict) -> None:
    """Coleta nome do cliente."""
    if len(texto.strip()) < 3:
        _enviar(numero, "Por favor, informe seu nome completo.")
        return

    dados["nome_completo"] = texto.strip().title()
    _enviar(numero,
        f"Olá, *{dados['nome_completo']}*! 👋\n\n"
        "Para emitir o Pix, preciso do seu *CPF* (apenas números):"
    )
    _set_estado(numero, "aguardando_cpf", dados)


def _etapa_cpf(numero: str, texto: str, dados: dict) -> None:
    """Coleta e valida o CPF."""
    cpf = "".join(filter(str.isdigit, texto))
    if not _cpf_valido(cpf):
        _enviar(numero, "CPF inválido. Por favor, informe apenas os 11 dígitos do CPF.")
        return

    dados["cpf"] = cpf
    plano = dados["plano_escolhido"]
    preco_fmt = f"R$ {plano['preco']:.2f}".replace(".", ",")
    cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    _enviar(numero,
        f"📋 *Confirme seu pedido:*\n\n"
        f"👤 Nome: {dados['nome_completo']}\n"
        f"🪪 CPF: {cpf_fmt}\n"
        f"📺 Plano: {plano['nome']}\n"
        f"💰 Valor: {preco_fmt}\n\n"
        "Digite *1* para confirmar ou *2* para cancelar."
    )
    _set_estado(numero, "aguardando_confirmacao", dados)


def _etapa_confirmacao(numero: str, texto: str, dados: dict) -> None:
    """Confirma o pedido e gera Pix."""
    if texto.strip() == "2":
        _enviar(numero, "Pedido cancelado. 😊 Digite *menu* para ver os planos novamente.")
        _limpar_estado(numero)
        return

    if texto.strip() != "1":
        _enviar(numero, "Por favor, responda *1* para confirmar ou *2* para cancelar.")
        return

    _enviar(numero, "⏳ Gerando seu Pix, aguarde um instante...")

    plano = dados["plano_escolhido"]

    try:
        # 1. Cria/encontra cliente no Asaas
        customer_id = asaas_api.obter_ou_criar_cliente(
            nome=dados["nome_completo"],
            cpf_cnpj=dados["cpf"],
            whatsapp=numero,
        )

        # 2. Cria cobrança Pix
        cobranca = asaas_api.criar_cobranca_pix(
            customer_id=customer_id,
            valor=plano["preco"],
            descricao=f"{config.NOME_EMPRESA} - {plano['nome']}",
            dias_vencimento=1,
        )

        dados["payment_id"] = cobranca["id"]
        dados["cobranca"] = cobranca

        # 3. Envia mensagem com Pix
        msg_pix = asaas_api.formatar_pix_whatsapp(cobranca, plano["nome"])
        _enviar(numero, msg_pix)
        _enviar(numero,
            "⏰ *Importante:* Após o pagamento, enviarei seu usuário e senha automaticamente.\n\n"
            "Digite *#* para verificar o status do seu pagamento."
        )
        _set_estado(numero, "aguardando_pagamento", dados)

    except Exception as e:
        log.error("Erro ao gerar Pix para %s: %s", numero, e)
        _enviar(numero,
            "❌ Ops! Tive um problema técnico ao gerar o Pix.\n"
            f"Por favor, fale diretamente com o atendente: {config.WHATSAPP_NUMBER}"
        )
        _limpar_estado(numero)


def _etapa_aguardando_pagamento(numero: str, texto: str, dados: dict) -> None:
    """Aguarda confirmação de pagamento e entrega o acesso."""
    payment_id = dados.get("payment_id")
    plano = dados.get("plano_escolhido", {})

    if not payment_id:
        _limpar_estado(numero)
        _etapa_inicio(numero, dados.get("nome_completo", ""))
        return

    # Verifica o status do pagamento
    try:
        status = asaas_api.verificar_pagamento(payment_id)
    except Exception as e:
        log.error("Erro ao verificar pagamento: %s", e)
        _enviar(numero, "Não consegui verificar o pagamento agora. Tente em alguns minutos.")
        return

    if status in ("RECEIVED", "CONFIRMED"):
        _entregar_acesso(numero, dados, plano)
    elif status == "OVERDUE":
        _enviar(numero,
            "⚠️ Seu Pix expirou. Digite *menu* para gerar um novo pedido."
        )
        _limpar_estado(numero)
    else:
        _enviar(numero,
            "⏳ Pagamento ainda não confirmado. \n"
            "Assim que o banco processar, enviarei seus dados de acesso automaticamente!\n\n"
            "Dúvidas? Fale com nosso atendente: " + config.WHATSAPP_NUMBER
        )


def _entregar_acesso(numero: str, dados: dict, plano: dict) -> None:
    """Cria o cliente no Legacy e envia as credenciais."""
    try:
        _enviar(numero, "✅ Pagamento confirmado! Criando seu acesso...")

        cliente = legacy_api.criar_cliente(
            server_id=plano["server_id"],
            package_id=plano["id"],
        )

        _enviar(numero,
            f"🎉 *Acesso criado com sucesso!*\n\n"
            f"📺 Plano: *{plano['nome']}*\n"
            f"👤 Usuário: `{cliente['username']}`\n"
            f"🔑 Senha: `{cliente['password']}`\n"
            f"📅 Válido até: {cliente['vencimento']}\n\n"
            f"*Como configurar:*\n"
            f"• No aplicativo, use o usuário e senha acima\n"
            f"• Dúvidas? Digite *ajuda* ou fale com o suporte: {config.WHATSAPP_NUMBER}\n\n"
            f"Aproveite! 🚀📺"
        )
        _limpar_estado(numero)

    except Exception as e:
        log.error("Erro ao criar cliente no Legacy para %s: %s", numero, e)
        _enviar(numero,
            "✅ Pagamento confirmado, mas tive um problema técnico ao criar seu acesso.\n"
            f"Nosso atendente já foi notificado e entrará em contato em breve.\n"
            f"Suporte: {config.WHATSAPP_NUMBER}"
        )


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _saudacao() -> str:
    hora = datetime.now().hour
    if hora < 12:
        return "Bom dia"
    elif hora < 18:
        return "Boa tarde"
    return "Boa noite"


def _cpf_valido(cpf: str) -> bool:
    """Validação básica de CPF (11 dígitos, não todos iguais)."""
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    # Valida dígitos verificadores
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        d = (soma * 10 % 11) % 10
        if d != int(cpf[i]):
            return False
    return True


AJUDA_MSG = (
    "🆘 *Como funciona:*\n\n"
    "1️⃣ Digite *menu* para ver os planos\n"
    "2️⃣ Escolha o plano digitando o número\n"
    "3️⃣ Informe seus dados\n"
    "4️⃣ Pague o Pix gerado automaticamente\n"
    "5️⃣ Receba seu acesso na hora!\n\n"
    f"📞 *Atendimento humano:* {config.WHATSAPP_NUMBER}\n"
    "🔄 *Reiniciar:* digite *menu*"
)
