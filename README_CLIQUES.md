# Funcionalidade de 5 Cliques Consecutivos

## Visão Geral
O sistema implementa uma funcionalidade de navegação rápida que permite redirecionar para a página de setores através de 5 cliques consecutivos em qualquer lugar da tela.

## Como Funciona

### 1. Detecção de Cliques
- **Localização**: Qualquer lugar da tela (exceto elementos interativos)
- **Tempo**: 2 segundos entre cliques para serem considerados consecutivos
- **Quantidade**: 5 cliques consecutivos para ativar o redirecionamento

### 2. Elementos Ignorados
O sistema não conta cliques nos seguintes elementos:
- Links (`<a>`)
- Botões (`<button>`)
- Campos de entrada (`<input>`)
- Seletores (`<select>`)
- Áreas de texto (`<textarea>`)
- Formulários (`<form>`)

### 3. Redirecionamento
- **Destino**: `/setores`
- **Método**: `window.location.href`
- **Log**: Mensagem no console para debug

## Implementação

### 1. Arquivo Centralizado
- **Localização**: `static/consecutive-clicks.js`
- **Função**: Centraliza toda a lógica de detecção
- **Reutilização**: Incluído em todas as páginas principais

### 2. Páginas com Funcionalidade
- ✅ `templates/senhas.html` - Tela principal de senhas
- ✅ `templates/login.html` - Tela de login
- ✅ `templates/selecionar_setor.html` - Seleção de setores

### 3. Inclusão nos Templates
```html
<!-- Script para sistema de 5 cliques consecutivos -->
<script src="{{ url_for('static', filename='consecutive-clicks.js') }}"></script>
```

## Configuração

### 1. Parâmetros Ajustáveis
```javascript
const CLICK_TIMEOUT = 2000; // 2 segundos
const REQUIRED_CLICKS = 5; // 5 cliques
```

### 2. Personalização
Para alterar o comportamento:
1. Edite `static/consecutive-clicks.js`
2. Modifique as constantes conforme necessário
3. Reinicie a aplicação

## Debug e Monitoramento

### 1. Logs no Console
- **Inicialização**: "Sistema de 5 cliques ativado..."
- **Detecção**: "5 cliques consecutivos detectados! Redirecionando..."
- **Reset**: "Timer expirado. Contador de cliques resetado."

### 2. Como Verificar
1. Abra o console do navegador (F12)
2. Clique 5 vezes consecutivas em qualquer lugar da tela
3. Observe as mensagens de log

## Casos de Uso

### 1. Navegação Rápida
- Acesso rápido à seleção de setores
- Útil para administradores e operadores
- Navegação alternativa sem menus visíveis

### 2. Recuperação de Sessão
- Redirecionamento para setores quando perdido
- Acesso rápido ao painel administrativo
- Navegação de emergência

## Segurança

### 1. Proteções Implementadas
- ✅ Ignora cliques em elementos interativos
- ✅ Timer de expiração para evitar ativação acidental
- ✅ Logs para auditoria
- ✅ Redirecionamento apenas para `/setores`

### 2. Considerações
- Funcionalidade visível apenas no console
- Não interfere com operação normal
- Fácil de desabilitar se necessário

## Manutenção

### 1. Adicionar a Novas Páginas
Para incluir a funcionalidade em uma nova página:
```html
<!-- Adicione antes do fechamento do </body> -->
<script src="{{ url_for('static', filename='consecutive-clicks.js') }}"></script>
```

### 2. Modificar Comportamento
- Edite `static/consecutive-clicks.js`
- Ajuste constantes conforme necessário
- Teste em todas as páginas

### 3. Desabilitar Temporariamente
- Comente a linha de inclusão do script
- Ou modifique a condição de redirecionamento

## Troubleshooting

### 1. Não Funciona
- Verifique se o arquivo `consecutive-clicks.js` existe
- Confirme se o script está sendo carregado (console)
- Teste cliques em áreas vazias da tela

### 2. Ativação Acidental
- Aumente `REQUIRED_CLICKS` para mais cliques
- Diminua `CLICK_TIMEOUT` para menos tempo
- Adicione mais elementos à lista de exclusão

### 3. Performance
- O script é leve e não impacta performance
- Event listeners são otimizados
- Timer é limpo adequadamente 