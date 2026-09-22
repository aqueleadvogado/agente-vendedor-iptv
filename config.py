"""
Configurações do Agente Vendedor IPTV
Edite este arquivo com suas credenciais antes de subir no PythonAnywhere
"""

import os

# ─────────────────────────────────────────────
# LEGACY PANEL
# ─────────────────────────────────────────────
LEGACY_BASE_URL = os.getenv("LEGACY_BASE_URL", "https://painellegacy.space/api").rstrip("/")
LEGACY_USERNAME = os.getenv("LEGACY_USERNAME", "seu_usuario_aqui").rstrip("/")
LEGACY_PASSWORD = os.getenv("LEGACY_PASSWORD", "sua_senha_aqui")

# ─────────────────────────────────────────────
# EVOLUTION API (hospede no Railway - gratuito)
# ─────────────────────────────────────────────
EVOLUTION_BASE_URL = os.getenv("EVOLUTION_BASE_URL", "https://seu-evolution.up.railway.app")
EVOLUTION_API_KEY  = os.getenv("EVOLUTION_API_KEY", "sua_chave_evolution")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "agente_vendedor")

# ─────────────────────────────────────────────
# ASAAS (Pix)
# ─────────────────────────────────────────────
ASAAS_BASE_URL = os.getenv("ASAAS_BASE_URL", "https://api.asaas.com/v3")
ASAAS_API_KEY  = os.getenv("ASAAS_API_KEY", "$aact_SUA_CHAVE_ASAAS_AQUI")
# Modo sandbox para testes: "https://sandbox.asaas.com/api/v3"

# ─────────────────────────────────────────────
# BOT
# ─────────────────────────────────────────────
# Número do WhatsApp do seu chip (apenas dígitos com DDI: ex: 5511999998888)
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "5511900000000")

# Webhook secret (qualquer string aleatória para validar requisições)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "mude_esta_chave_secreta")

# Quantos dias antes do vencimento avisar o cliente
DIAS_AVISO_VENCIMENTO = int(os.getenv("DIAS_AVISO_VENCIMENTO", "3"))

# Planos exibidos ao cliente (serão buscados automaticamente da API)
# Deixe em branco para usar todos os planos do painel
PLANOS_ATIVOS = []   # ex: ["LEGACY TITAN", "LEGACY ROYAL"]

# Mensagem de saudação
NOME_EMPRESA = "Legacy IPTV"

# ─────────────────────────────────────────────
# FLASK
# ─────────────────────────────────────────────
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
PORT  = int(os.getenv("PORT", "5000"))
