# Notificações do cliente (QR) — AppSenhas

## Visão geral

Após retirar a senha, o QR Code abre a tela pública no **Next.js**:

`{ADMIN_WEB_URL}/acompanhar/{token}`

Exemplo local: `http://localhost:3000/acompanhar/<token_unico>`.

A rota legada Flask `GET /notificacao/<token>` redireciona para essa URL.

## O que a tela faz

1. Conecta via Socket.IO com `auth: { ticket_token }`
2. Mostra posição / chamada / pedido / finalização
3. Registra **Web Push** (Service Worker em `web/public/sw.js`)
4. Após finalização, pede **avaliação 1–5** no navegador

## Push por etapa

O backend envia Web Push (se houver subscription) em:

| Etapa | Tag |
|-------|-----|
| Posição ≤ 3 | `senha-perto` |
| Chamada | `senha-chamada` |
| Pedido preparando | `pedido-status` |
| Finalizado | `senha-finalizada` |

Implementação: `api/backend/services/push_service.py` + emitters.

## APIs públicas

| Método | Rota | Uso |
|--------|------|-----|
| GET | `/api/vapid-public-key` | Chave pública VAPID |
| POST | `/api/registrar_push/<token>` | Salva subscription |
| POST | `/api/salvar_pedido/<token>` | Pedido opcional |
| POST | `/api/avaliar/<token>` | `{ "nota": 1..5 }` |
| GET | `/api/verificar_senha/<token>` | Fallback/legado |

No Next, essas rotas (e `/socket.io`) são reescritas para a API Flask.

## Configuração VAPID

No `.env` (ver `.env.example`):

```bash
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_EMAIL=seu-email@exemplo.com
ADMIN_WEB_URL=http://localhost:3000
```

Push no navegador exige **HTTPS** (ou `localhost`). Em rede local sem TLS, o Socket.IO continua funcionando; o push pode falhar até haver HTTPS/ngrok.

## QR Code

`get_notification_url(token)` em `api/backend/utils.py` gera:

`{ADMIN_WEB_URL}/acompanhar/{token}`

(ou IP local `:3000` se `ADMIN_WEB_URL` não estiver definido).

## Avaliação

- **Celular (QR):** `POST /api/avaliar/<token>` na tela Next
- **Kiosk tablet:** fluxo `/avaliacao` permanece para o operador

## Arquivos principais

- UI: `web/src/app/acompanhar/[token]/page.tsx`, `web/src/components/cliente/`
- SW: `web/public/sw.js`
- Backend: `api/backend/blueprints/notificacao_bp.py`, `api/backend/services/push_service.py`
