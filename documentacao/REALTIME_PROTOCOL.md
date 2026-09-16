# Protocolo de Tempo Real (Socket.IO) — CompuFlow

Este documento é a **fonte única da verdade** do protocolo de tempo real usado pelo
backend Flask, pelas telas web restantes (`templates/`) e pelo app Android
(`CompuFlow/`). Qualquer alteração de evento/payload precisa ser refletida aqui
**antes** de mudar o código, dos dois lados (servidor e clientes).

Não existe mais polling: nenhum cliente deve chamar `setInterval` para buscar
estado via REST. Todo estado que muda em tempo real chega via evento de socket,
com o payload completo — o cliente nunca precisa fazer um `fetch` de
confirmação depois de receber um evento.

## 1. Transporte e autenticação

- Biblioteca: Flask-SocketIO no servidor (protocolo Engine.IO v4 / Socket.IO v4).
- Namespace único: `/` (default). Não usamos múltiplos namespaces — a
  separação de "papel" (cliente/operador/avaliação/tv/admin) é feita por
  **rooms**, não por namespace, para simplificar o cliente Android.
- Autenticação no handshake: todo client (web ou Android) deve conectar
  enviando `auth` no `connect`, em um de dois formatos:

```json
{ "session_token": "<JWT obtido em /api/v1/setor/login ou nas rotas web de setor>" }
```
```json
{ "ticket_token": "<token_unico da senha, para acompanhamento anônimo via QR Code>" }
```

- O servidor valida a autenticação (ver `backend/auth.py` e
  `backend/sockets/handlers.py`) **no `connect`** e já coloca o socket nas rooms
  adequadas:
  - `session_token` → entra em `setor:<setor_id>` (e em
    `avaliacao:<setor_id>` se o papel for "avaliacao"; e também
    `avaliacao:<setor_id>:<operador_id>` quando o token traz operador).
  - `ticket_token` → entra em `ticket:<ticket_token>` e recebe imediatamente
    um `senha:posicao` com o estado atual daquela senha. É o mecanismo usado
    pela página pública `notificacao.html` (acessada via QR Code impresso na
    senha), que não tem login de setor.

  Isso substitui os eventos manuais antigos `join_setor` / `join_token_room`,
  que criavam uma janela de corrida entre "conectar" e "entrar na room" onde
  eventos podiam se perder.
- Se a autenticação for inválida/expirada, o servidor emite `auth:erro` e
  desconecta o socket.

## 2. Rooms

| Room | Quem entra | Uso |
|---|---|---|
| `setor:<setor_id>` | Operador, TV, Cliente (enquanto aguarda), Admin | Estado da fila do setor: lista de pendentes, atendimentos em curso, chamadas |
| `ticket:<ticket_token>` | O cliente daquela senha específica (app ou navegador via QR) | Posição na fila, chamada, status do pedido, avaliação daquele ticket |
| `avaliacao:<setor_id>` | Tablet de Avaliação do setor (idle com mídia) | Qualquer atendimento finalizado pede nota |
| `avaliacao:<setor_id>:<operador_id>` | Tela de Avaliação ligada a um operador (legado) | Avisa quando uma nova avaliação está pendente para aquele operador |

Um mesmo socket pode estar em mais de uma room (ex.: operador está em
`setor:<id>` e a TV também).

## 3. Eventos servidor → cliente

Todos os eventos abaixo trazem o payload **completo** necessário para
renderizar a tela — nenhum cliente deve reagir a um evento fazendo uma
chamada REST subsequente.

### `fila:atualizada` (room `setor:<setor_id>`)
Emitido sempre que uma senha é criada, chamada ou finalizada.
```json
{
  "setor_id": 1,
  "pendentes": [
    {"id": 10, "senha": "N0001", "tipo": "normal", "tem_pedido": false, "pedido": null}
  ],
  "atendimentos": [
    {"operador_id": 3, "operador_nome": "Ana", "operador_foto": "uuid.jpg", "senha": "P0002", "tipo": "preferencial"}
  ]
}
```

### `senha:chamada` (rooms `setor:<setor_id>` e `ticket:<ticket_token>`)
```json
{
  "setor_id": 1,
  "ticket_token": "uuid",
  "senha": "N0001",
  "tipo": "normal",
  "operador_nome": "Ana",
  "operador_foto": "uuid.jpg",
  "tem_pedido": false,
  "pedido": null
}
```

### `senha:posicao` (room `ticket:<ticket_token>`)
```json
{"ticket_token": "uuid", "posicao": 2, "senha": "N0001", "setor_nome": "Recepção"}
```

### `pedido:status` (room `ticket:<ticket_token>`)
```json
{"ticket_token": "uuid", "pedido": "2x café", "status": "preparando", "mensagem": "Pedido sendo preparado"}
```

### `avaliacao:solicitada` (rooms `avaliacao:<setor_id>` e `avaliacao:<setor_id>:<operador_id>`)
```json
{"setor_id": 1, "operador_id": 3, "operador_nome": "Ana", "operador_foto": "uuid.jpg", "senha_id": 10, "senha": "N0001"}
```

### `auth:erro` (direto ao socket, antes de desconectar)
```json
{"mensagem": "Sessão inválida ou expirada"}
```

### `tv:config_atualizada` (room `setor:<setor_id>`)
Emitido quando a fila de mídia da TV muda (upload, vínculo, ativar/desativar,
ordem, exclusão ou flags do setor). O payload é o mesmo de
`GET /api/v1/setor/tv_config`.
```json
{
  "propagandas_ativas": true,
  "layout_tv_web": "propaganda",
  "setor_nome": "Balcão",
  "imagens": [
    {"id": 1, "arquivo": "uuid.jpg", "ordem": 1, "tipo": "image"},
    {"id": 2, "arquivo": "uuid.mp4", "ordem": 2, "tipo": "video"}
  ],
  "intervalo_ms": 15000
}
```

## 4. Eventos cliente → servidor

### `operador:chamar_proxima`
```json
{"operador_id": 3}
```
Resposta: o servidor emite `fila:atualizada` e `senha:chamada` para a room do
setor (não há callback de ack; o próprio broadcast já atualiza a tela de
quem chamou).

### `operador:chamar_novamente`
```json
{"senha_id": 10}
```

### `cliente:criar_senha`
```json
{"tipo": "normal"}
```
Servidor responde com `fila:atualizada` (room do setor) e, apenas ao socket
que fez a chamada, um `senha:criada` com o `ticket_token` gerado — a partir
daí o cliente entra automaticamente na room `ticket:<ticket_token>` (o
servidor já faz isso antes de responder).

### `cliente:salvar_pedido`
```json
{"ticket_token": "uuid", "pedido": "2x café"}
```

### `operador:confirmar_pedido`
```json
{"senha": "N0001", "mensagem": "Pedido sendo preparado"}
```
Dispara `pedido:status` (status `"preparando"`) para a room `ticket:<ticket_token>` daquela senha.

### `avaliacao:enviar`
```json
{"senha_id": 10, "nota": 5}
```

### `ticket:seguir`
```json
{"ticket_token": "uuid"}
```
Usado quando o cliente já tem um `ticket_token` salvo (ex.: app reaberto, ou
o navegador do QR Code) e quer voltar a acompanhar aquela senha específica —
o servidor valida o token, entra o socket na room `ticket:<ticket_token>` e
responde imediatamente com `senha:posicao`.

> Nota de implementação: as ações principais (`operador:chamar_proxima`,
> `operador:chamar_novamente`, `cliente:salvar_pedido`, `avaliacao:enviar`)
> também estão disponíveis como endpoints REST equivalentes em
> `backend/blueprints/api_bp.py`, usados pelo app Android via Retrofit. Os dois
> caminhos chamam exatamente os mesmos `services` e emitem os mesmos eventos
> — a escolha entre socket e REST para *disparar* uma ação é só uma questão
> de conveniência do cliente; o que nunca é opcional é receber as
> atualizações **apenas** via socket, nunca via polling.

## 5. Mapeamento evento antigo → novo

| Antigo | Novo | Observação |
|---|---|---|
| thread `atualizar_senhas_periodicamente` (poll de 1s) | removido | estado só muda via evento pontual |
| `join_setor` / `join_token_room` (manual) | feito no `connect` via `auth` | elimina corrida de eventos perdidos |
| `atualizar_lista`, `atualizar_atendimentos`, `atualizar_lista_senhas` (3 eventos parecidos + fetch subsequente) | `fila:atualizada` (payload completo) | um único evento, sem fetch depois |
| `senha_chamada`, `senha_chamada_com_pedido`, `senha_chamada_novamente` | `senha:chamada` | um único evento cobre os três casos (`pedido` já vem no payload) |
| `pedido_confirmado` → `pedido_preparando` (bug: room `token` ≠ `token_<token>`) | `pedido:status` na room `ticket:<ticket_token>` | corrige o nome da room |
| `posicao_fila`, `senha_proxima` | `senha:posicao` | um único evento com a posição |
| `nova_senha_para_avaliacao` | `avaliacao:solicitada` | agora direcionado à room do operador, não broadcast geral |

## 6. Fluxo de login + REST no app Android

1. `POST /api/v1/setor/login {codigo_setor}` → `{session_token, setor}` (papel
   ainda genérico).
2. Usuário escolhe o modo na tela seguinte (Cliente/Operador/Avaliação/TV) →
   `POST /api/v1/sessao/papel {role, operador_id?}` com o token do passo 1 →
   novo `session_token` já com o papel definido. É esse token que vai no
   `auth.session_token` do socket a partir daqui.
3. Conecta o socket uma única vez com `{ auth: { session_token } }` — o
   servidor já entra na room `setor:<id>` (e `avaliacao:<id>:<operador_id>`
   se for o papel "avaliacao").
4. Ações (chamar próxima, criar senha, etc.) via REST (`/api/v1/...`); o
   resultado chega pelos eventos de socket, nunca pela resposta do REST em
   si (a resposta do REST é só um ack local).
5. Caso específico do papel "cliente": depois de `POST /api/v1/senha` (que
   retorna o `token_unico` da nova senha), o app emite `ticket:seguir
   {ticket_token}` no socket já conectado para passar a receber também os
   eventos daquela senha (`senha:chamada`, `senha:posicao`, `pedido:status`)
   — sem precisar reconectar.

## 7. Convenção para o app Android

O app Android usa o cliente `io.socket:socket.io-client` e implementa esse
mesmo contrato em `SocketManager.kt` (ver `CompuFlow/app/src/main/java/.../realtime/`).
Nomes de evento, nomes de campo e formato de room são **idênticos** aos
descritos aqui — não existem apelidos por plataforma.
