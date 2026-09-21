# Agente Vendedor IPTV — Guia de Configuração

## Visão Geral

```
WhatsApp → Evolution API (Railway) → Webhook → PythonAnywhere (bot) → Legacy API
                                                                     → Asaas API (Pix)
```

---

## PASSO 1 — Configurar o Asaas (gratuito)

1. Acesse https://asaas.com e crie uma conta gratuita
2. No painel, vá em **Integrações → API**
3. Copie a **Chave de API** (começa com `$aact_...`)
4. Em **Integrações → Notificações (Webhooks)**, adicione:
   - URL: `https://SEU_USUARIO.pythonanywhere.com/webhook/asaas`
   - Eventos: `PAYMENT_RECEIVED`, `PAYMENT_CONFIRMED`

---

## PASSO 2 — Subir Evolution API no Railway (gratuito)

1. Acesse https://railway.app e crie conta com o GitHub
2. Clique em **New Project → Deploy from GitHub repo**
3. Use o repo: `EvolutionAPI/evolution-api`
4. Nas variáveis de ambiente do Railway, adicione:
   ```
   AUTHENTICATION_API_KEY=escolha_uma_chave_forte
   AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=true
   ```
5. Após deploy, copie a URL pública (ex: `https://evolution.up.railway.app`)
6. Crie a instância pelo navegador:
   ```
   POST https://evolution.up.railway.app/instance/create
   Header: apikey: SUA_CHAVE
   Body: {"instanceName": "agente_vendedor", "qrcode": true}
   ```
7. Conecte o WhatsApp escaneando o QR Code em:
   ```
   GET https://evolution.up.railway.app/instance/connect/agente_vendedor
   ```

---

## PASSO 3 — Subir o bot no PythonAnywhere

1. Faça login em https://pythonanywhere.com
2. Abra um **Bash console** e execute:
   ```bash
   git clone https://github.com/SEU_REPO/agente_vendedor ~/agente_vendedor
   # OU faça upload manual dos arquivos via Files
   
   pip install -r ~/agente_vendedor/requirements.txt --user
   ```

3. Vá em **Web → Add a new web app**
   - Python version: 3.11
   - Manual configuration
   - WSGI file: `/home/SEU_USUARIO/agente_vendedor/wsgi.py`
   - Working directory: `/home/SEU_USUARIO/agente_vendedor`

4. Em **Web → Environment variables** (ou edite o WSGI e adicione `os.environ`):
   ```
   LEGACY_BASE_URL=https://painellegacy.space/api
   LEGACY_USERNAME=seu_usuario_legacy
   LEGACY_PASSWORD=sua_senha_legacy
   EVOLUTION_BASE_URL=https://evolution.up.railway.app
   EVOLUTION_API_KEY=sua_chave_evolution
   EVOLUTION_INSTANCE=agente_vendedor
   ASAAS_API_KEY=$aact_sua_chave_asaas
   WHATSAPP_NUMBER=5511900000000
   NOME_EMPRESA=Legacy IPTV
   DIAS_AVISO_VENCIMENTO=3
   ```

5. Clique em **Reload** para aplicar.

---

## PASSO 4 — Configurar o Webhook (uma única vez)

Abra no navegador:
```
https://SEU_USUARIO.pythonanywhere.com/setup
```

Isso registra automaticamente a URL de webhook na sua Evolution API.

Verifique se está tudo certo:
```
https://SEU_USUARIO.pythonanywhere.com/status
```

---

## PASSO 5 — Agendar avisos de vencimento

No PythonAnywhere, vá em **Tasks → Add a new scheduled task**:
- Command: `python /home/SEU_USUARIO/agente_vendedor/scheduler.py`
- Hour: `9`   Minute: `0`   (executa todo dia às 09:00)

---

## Fluxo da conversa

```
Cliente envia "oi" / "menu"
    ↓
Bot mostra lista de planos
    ↓
Cliente escolhe o número do plano
    ↓
Bot pede nome completo
    ↓
Bot pede CPF
    ↓
Bot mostra resumo e pede confirmação
    ↓
Bot gera Pix via Asaas e envia copia-e-cola
    ↓
[Pagamento confirmado automaticamente pelo webhook Asaas]
    ↓
Bot cria cliente no Legacy e envia usuário + senha
```

---

## Comandos do cliente

| Digite    | Ação                           |
|-----------|--------------------------------|
| `menu`    | Reinicia a conversa            |
| `oi`      | Reinicia a conversa            |
| `0`       | Falar com atendente humano     |
| `#`       | Verificar pagamento pendente   |
| `ajuda`   | Mostra guia rápido             |

---

## Solução de problemas

**Bot não responde:** verifique `/status` e confirme que o WhatsApp está conectado.

**Pix não é gerado:** confira a chave do Asaas em `config.py` e se o CPF do cliente é válido.

**Cliente criado mas não chega no WhatsApp:** verifique se o número de WhatsApp do cliente está cadastrado no Legacy.

**Railway apagou a instância:** o free tier tem 500h/mês. Se acabar, recrie a instância e re-escaneie o QR Code.

---

## Segurança

- Nunca commite o `config.py` com senhas reais no GitHub
- Use variáveis de ambiente do PythonAnywhere
- Ative 2FA na sua conta do Legacy, Railway e Asaas
