"""
Wrapper para a API do painel Legacy (Sigma)
"""

import requests
import logging
from datetime import datetime, timedelta
from functools import lru_cache
import config

log = logging.getLogger(__name__)

_session_token: str | None = None


def _get_token() -> str:
    """Faz login e retorna o bearer token. Reauthenticate se expirado."""
    global _session_token
    if _session_token:
        return _session_token

    resp = requests.post(
        f"{config.LEGACY_BASE_URL}/auth/login",
        json={"username": config.LEGACY_USERNAME, "password": config.LEGACY_PASSWORD},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    # O token pode vir em 'token' ou 'access_token'
    _session_token = data.get("token") or data.get("access_token") or data["data"]["token"]
    return _session_token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, path: str, **kwargs):
    """Executa uma requisição; em caso de 401 renova o token e tenta novamente."""
    global _session_token
    url = f"{config.LEGACY_BASE_URL}/{path.lstrip('/')}"
    resp = requests.request(method, url, headers=_headers(), timeout=15, **kwargs)
    if resp.status_code == 401:
        _session_token = None          # força renovação
        resp = requests.request(method, url, headers=_headers(), timeout=15, **kwargs)
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────
# Servidores e Planos
# ─────────────────────────────────────────────

def listar_servidores() -> list[dict]:
    """Retorna lista de servidores disponíveis."""
    data = _request("GET", "/servers")
    return data if isinstance(data, list) else data.get("data", [])


def listar_planos(server_id: int | None = None) -> list[dict]:
    """Retorna todos os planos, opcionalmente filtrados por servidor."""
    servidores = listar_servidores()
    planos = []
    for srv in servidores:
        if server_id and srv["id"] != server_id:
            continue
        for pkg in srv.get("packages", []) or []:
            if config.PLANOS_ATIVOS and pkg["name"] not in config.PLANOS_ATIVOS:
                continue
            planos.append({
                "id": pkg["id"],
                "nome": pkg["name"],
                "preco": pkg.get("price", 0),
                "conexoes": pkg.get("connections", 1),
                "duracao_dias": pkg.get("duration", 30),
                "server_id": srv["id"],
                "server_nome": srv["name"],
            })
    return planos


def formatar_planos_whatsapp(planos: list[dict]) -> str:
    """Formata lista de planos para enviar no WhatsApp."""
    if not planos:
        return "Nenhum plano disponível no momento."

    linhas = ["📺 *Planos disponíveis:*\n"]
    for i, p in enumerate(planos, 1):
        preco = f"R$ {p['preco']:.2f}".replace(".", ",")
        linhas.append(
            f"*{i}.* {p['nome']}\n"
            f"   💰 {preco}/mês\n"
            f"   📱 {p['conexoes']} tela(s)\n"
            f"   📅 {p['duracao_dias']} dias\n"
        )
    linhas.append("Digite o *número* do plano desejado ou *0* para falar com um atendente.")
    return "\n".join(linhas)


# ─────────────────────────────────────────────
# Clientes
# ─────────────────────────────────────────────

def criar_cliente(server_id: int, package_id: int) -> dict:
    """
    Cria um novo cliente no painel.
    Retorna dict com username, password e vencimento.
    """
    payload = {
        "serverId": server_id,
        "packageId": package_id,
    }
    data = _request("POST", "/customers", json=payload)
    cliente = data if "username" in data else data.get("data", data)
    return {
        "username":   cliente.get("username", ""),
        "password":   cliente.get("password", ""),
        "vencimento": cliente.get("expiryDate", ""),
        "id":         cliente.get("id", ""),
    }


def clientes_vencendo(dias: int = None) -> list[dict]:
    """Retorna clientes que vencem nos próximos `dias` dias."""
    if dias is None:
        dias = config.DIAS_AVISO_VENCIMENTO

    data = _request("GET", "/customers/expiring")
    todos = data if isinstance(data, list) else data.get("data", [])

    limite = datetime.now() + timedelta(days=dias)
    resultado = []
    for c in todos:
        expiry_raw = c.get("expiryDate") or c.get("expiry_date", "")
        try:
            expiry = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00"))
            if expiry.replace(tzinfo=None) <= limite:
                resultado.append({
                    "id":         c.get("id"),
                    "username":   c.get("username"),
                    "whatsapp":   c.get("whatsapp") or c.get("phone") or "",
                    "vencimento": expiry.strftime("%d/%m/%Y %H:%M"),
                    "plano":      c.get("package", {}).get("name", ""),
                    "preco":      c.get("package", {}).get("price", 0),
                })
        except Exception:
            pass
    return resultado


def buscar_cliente_por_whatsapp(numero: str) -> dict | None:
    """Busca cliente pelo número de WhatsApp cadastrado."""
    # Remove caracteres não numéricos e código do país se necessário
    numero_limpo = "".join(filter(str.isdigit, numero))
    data = _request("GET", f"/customers?phone={numero_limpo}&perPage=5")
    clientes = data if isinstance(data, list) else data.get("data", [])
    return clientes[0] if clientes else None
