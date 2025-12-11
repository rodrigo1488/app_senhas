# Funcionalidade de Impressão Térmica

## Visão Geral
O sistema de senhas agora suporta impressão térmica usando a biblioteca `python-escpos` para enviar comandos ESC/POS para impressoras térmicas via rede.

## Configuração

### 1. Requisitos
- Biblioteca `python-escpos==3.1` (já incluída no requirements.txt)
- Impressora térmica com interface de rede
- Porta padrão: 9100 (configurável via `IMPRESSORA_PORTA`)

### 2. Configuração da Impressora
- **IP da Impressora**: Configurado via painel administrativo
- **Porta**: 9100 (padrão para impressoras térmicas)
- **Protocolo**: ESC/POS via rede

### 3. Configuração da Empresa
- **Nome da Empresa**: Configurado via interface web ou variável `NOME_EMPRESA_PADRAO`
- **Interface Web**: Painel administrativo → Configurações → Configurar Empresa
- **Cookie**: Prioridade sobre valor padrão (duração: 1 ano)
- **Setor**: Buscado automaticamente do banco de dados
- **Descrição**: Incluída se disponível no cadastro do setor

## Funcionalidades

### 1. Impressão de Senhas
- **Rota**: `/retirar_senha/<tipo>`
- **Função**: `imprimir_senha_com_ip(senha, impressora_ip, nome_setor, descricao_setor)`
- **Layout**: Nome da empresa + setor + senha como imagem bitmap + texto ESC/POS
- **Imagem**: Gerada dinamicamente com PIL

### 2. Layout da Impressão (Com Imagem Bitmap)
```
================================

        EMPRESA EXEMPLO

        Setor: Atendimento
        Descrição do Setor

            SENHA

       [IMAGEM BITMAP DA SENHA]

================================
Data: 25/07/2025
Hora: 14:30
================================
Aguarde ser chamada
na tela de atendimento
================================
```

**Características da Imagem da Senha:**
- **Formato**: Bitmap 1-bit (preto e branco puro)
- **Largura**: Máximo 384px (compatível com impressoras térmicas)
- **Altura**: 80px (otimizada para orientação horizontal)
- **Fonte**: Sistema (Arial, Calibri, Verdana) ou padrão
- **Tamanho**: Automático (ajusta conforme necessário)
- **Centralização**: Automática
- **Orientação**: Horizontal garantida

### 3. Teste de Conectividade
- **Rota**: `/test_impressora?ip=192.168.1.100`
- **Função**: Testa se a impressora está acessível
- **Retorno**: JSON com status de sucesso/erro
- **Inclui**: Teste de imagem bitmap da senha

### 4. Geração de Imagem Bitmap
- **Função**: `gerar_imagem_senha(senha, largura_maxima=384)`
- **Biblioteca**: PIL (Pillow)
- **Formato**: 1-bit (preto e branco puro)
- **Fallback**: Texto ESC/POS se falhar

## Gerenciamento de Conexões

### 1. Fechamento Automático de Conexões
**IMPORTANTE**: O sistema agora gerencia adequadamente as conexões com a impressora:

- **Problema Anterior**: Conexões não eram fechadas após cada impressão
- **Solução Implementada**: Uso de blocos `try/finally` para garantir fechamento
- **Benefício**: Evita vazamentos de recursos e impressoras travando

### 2. Implementação da Correção
```python
def imprimir_senha_com_ip(senha, impressora_ip):
    p = None
    try:
        p = Network(impressora_ip, IMPRESSORA_PORTA)
        # ... código de impressão ...
        return True
    except Exception as e:
        print(f"[ERRO IMPRESSAO] {e}")
        return False
    finally:
        # Fecha a conexão com a impressora
        if p:
            try:
                p.close()
                print(f"[IMPRESSAO] Conexão com impressora {impressora_ip} fechada")
            except Exception as e:
                print(f"[ERRO IMPRESSAO] Erro ao fechar conexão: {e}")
```

### 3. Logs de Conexão
O sistema agora registra:
- Abertura de conexão
- Fechamento de conexão
- Erros durante o fechamento

## Configuração no Painel Administrativo

### 1. Adicionar Impressora
1. Acesse o painel administrativo
2. Vá em "Impressoras" → "Adicionar Impressora"
3. Preencha:
   - **Nome**: Nome da impressora
   - **IP**: Endereço IP da impressora
   - **Porta**: 9100 (padrão)
   - **Setor**: Setor associado

### 2. Configuração por Setor
- Cada setor pode ter sua própria impressora
- O sistema busca automaticamente a impressora do setor
- Fallback para cookie `end_impressora_local`

## Troubleshooting

### 1. Erro de Conexão
```
[ERRO IMPRESSAO] Erro ao imprimir senha 'N1234': [Errno 10061] 
No connection could be made because the target machine actively refused it
```
**Solução**: Verificar se a impressora está ligada e acessível na rede

### 2. IP Incorreto
```
[ERRO IMPRESSAO] Erro ao imprimir senha 'N1234': [Errno 11001] 
getaddrinfo failed
```
**Solução**: Verificar se o IP da impressora está correto

### 3. Porta Bloqueada
```
[ERRO IMPRESSAO] Erro ao imprimir senha 'N1234': [Errno 10060] 
A connection attempt failed because the connected party did not properly respond
```
**Solução**: Verificar firewall e configurações de rede

### 4. Impressora Para Após Algumas Impressões
**Problema**: Impressora trava após algumas impressões
**Causa**: Conexões não fechadas adequadamente
**Solução**: ✅ **CORRIGIDO** - Implementado fechamento automático de conexões

## Teste Manual

### 1. Via Browser
```
http://localhost:5000/test_impressora?ip=192.168.1.100
```

### 2. Via Python
```python
from escpos.printer import Network
p = Network('192.168.1.100', 9100)
p.text("Teste\n")
p.cut()
p.close()  # IMPORTANTE: Sempre fechar a conexão
```

## Logs do Sistema

### 1. Logs de Sucesso
```
[IMPRESSAO] Tentando imprimir senha 'N1234' na impressora 192.168.1.100
[IMPRESSAO] Senha 'N1234' enviada com sucesso para 192.168.1.100
[IMPRESSAO] Conexão com impressora 192.168.1.100 fechada
```

### 2. Logs de Erro
```
[ERRO IMPRESSAO] Erro ao imprimir senha 'N1234': [Errno 10061] 
No connection could be made because the target machine actively refused it
[ERRO IMPRESSAO] Erro ao fechar conexão com impressora: [Errno 10054]
```

## Configurações Avançadas

### 1. Personalização do Layout
Edite a função `imprimir_senha_com_ip()` para personalizar:
- Tamanho da fonte
- Alinhamento
- Conteúdo adicional
- Formatação da data/hora
- Espaçamentos entre elementos

#### Personalização da Empresa:
```python
# No arquivo app.py, linha ~50
NOME_EMPRESA_PADRAO = "SUA EMPRESA AQUI"  # Personalize com o nome da sua empresa
```

**Via Interface Web:**
- Acesse o painel administrativo
- Clique na aba "Configurações"
- Clique em "Configurar Empresa"
- Digite o nome da empresa
- Clique em "Salvar Configuração"

**Via Cookie:**
- O nome da empresa pode ser configurado via cookie `nome_empresa`
- Duração: 1 ano
- Prioridade sobre o valor padrão

#### Comandos de Fonte ESC/POS Utilizados:
- `\x1B\x21\x30` - Fonte grande (para título e número da senha)
- `\x1B\x21\x00` - Fonte normal (para data/hora e instruções)

#### Melhorias de Layout Implementadas:
- ✅ Espaçamento adequado entre "SENHA" e o número da senha
- ✅ Fonte menor para data/hora (mais compacto)
- ✅ Fonte menor para mensagem inferior (mais compacto)
- ✅ Eliminação de espaços em branco desnecessários
- ✅ Layout mais compacto e eficiente
- ✅ Redução do espaço em branco na parte inferior

### 2. Múltiplas Impressoras
- Configure diferentes impressoras por setor
- Use cookies para armazenar preferências
- Implemente fallback automático

### 3. Monitoramento
- Logs detalhados de todas as impressões
- Status de conectividade em tempo real
- Alertas para impressoras offline
- **Novo**: Monitoramento de fechamento de conexões

## Melhorias Implementadas

### 1. Gerenciamento de Recursos
- ✅ Fechamento automático de conexões
- ✅ Tratamento de exceções durante fechamento
- ✅ Logs detalhados de operações

### 2. Estabilidade
- ✅ Prevenção de vazamentos de recursos
- ✅ Melhor estabilidade da impressora
- ✅ Redução de travamentos

### 3. Monitoramento
- ✅ Logs de abertura e fechamento de conexões
- ✅ Rastreamento de erros de conexão
- ✅ Diagnóstico melhorado de problemas

### 4. Layout e Formatação
- ✅ Espaçamento adequado entre elementos
- ✅ Melhor legibilidade do número da senha
- ✅ Layout mais limpo e profissional
- ✅ Fonte menor para informações secundárias (data/hora, instruções)
- ✅ Layout mais compacto e eficiente
- ✅ Eliminação de espaços em branco desnecessários
- ✅ Formatação consistente entre impressão e teste

### 5. Impressão de Imagem Bitmap
- ✅ Senha impressa como imagem bitmap de alta qualidade
- ✅ Formato 1-bit otimizado para impressoras térmicas
- ✅ Largura máxima de 384px (compatível)
- ✅ Fonte automática do sistema (Arial, Calibri, Verdana)
- ✅ Centralização automática do texto
- ✅ Fallback para texto ESC/POS se falhar
- ✅ Ajuste automático de tamanho da fonte
- ✅ Tamanho de fonte aumentado em 20% para melhor legibilidade

### 6. Informações da Empresa e Setor
- ✅ Nome da empresa configurável via variável
- ✅ Nome do setor buscado automaticamente do banco
- ✅ Descrição do setor incluída se disponível
- ✅ Layout profissional com hierarquia visual
- ✅ Fonte diferenciada para nome da empresa 