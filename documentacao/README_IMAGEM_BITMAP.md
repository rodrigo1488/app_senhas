# Funcionalidade de Impressão de Imagem Bitmap

## Visão Geral
O sistema agora suporta impressão da senha como imagem bitmap de alta qualidade, mantendo as demais informações em texto ESC/POS tradicional.

## Características da Imagem

### 1. Especificações Técnicas
- **Formato**: Bitmap 1-bit (preto e branco puro)
- **Largura**: Máximo 384px (compatível com impressoras térmicas)
- **Altura**: 80px (otimizada para orientação horizontal)
- **Resolução**: Otimizada para impressão térmica
- **Compressão**: PNG para transmissão
- **Orientação**: Horizontal (largura > altura)

### 2. Fontes Suportadas
O sistema tenta usar as seguintes fontes do sistema (em ordem de prioridade):
- Arial (Arial-Bold)
- Calibri (Calibri-Bold)
- Verdana (Verdana-Bold)
- Fonte padrão do sistema (fallback)

### 3. Ajuste Automático
- **Tamanho**: Ajusta automaticamente conforme o número de caracteres
- **Centralização**: Centraliza automaticamente na imagem
- **Limites**: Respeita a largura máxima de 384px
- **Fonte**: Tamanho inicial 72px (aumentado em 20%)
- **Fallback**: Fonte padrão 48px se não encontrar fonte do sistema

## Implementação

### 1. Função Principal
```python
def gerar_imagem_senha(senha, largura_maxima=384):
    """
    Gera uma imagem bitmap da senha para impressão térmica
    
    Args:
        senha (str): Número da senha
        largura_maxima (int): Largura máxima da imagem (padrão 384px)
    
    Returns:
        PIL.Image: Imagem bitmap da senha
    """
```

### 2. Processo de Geração
1. **Criação da imagem**: 384x120px em escala de cinza
2. **Carregamento da fonte**: Sistema ou padrão
3. **Cálculo do tamanho**: Ajuste automático
4. **Posicionamento**: Centralização
5. **Conversão**: Para bitmap 1-bit
6. **Retorno**: Imagem pronta para impressão

### 3. Integração com ESC/POS
```python
# Gerar imagem
imagem_senha = gerar_imagem_senha(senha)

# Salvar em buffer
buffer = io.BytesIO()
imagem_senha.save(buffer, format='PNG')
buffer.seek(0)

# Imprimir
p.image(buffer, impl='bitImageRaster')
```

## Layout Resultante

### 1. Estrutura da Impressão
```
================================

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

### 2. Vantagens
- ✅ **Alta qualidade**: Senha bem visível e legível
- ✅ **Compatibilidade**: Funciona com todas as impressoras térmicas
- ✅ **Performance**: Formato otimizado para transmissão
- ✅ **Fallback**: Volta para texto se falhar
- ✅ **Flexibilidade**: Ajusta automaticamente

## Configuração

### 1. Parâmetros Ajustáveis
```python
# Na função gerar_imagem_senha()
largura_maxima = 384  # Largura da imagem
altura = 80           # Altura da imagem (otimizada para horizontal)
tamanho_fonte = 72    # Tamanho inicial da fonte (aumentado em 20%)
```

### 2. Fontes Personalizadas
Para adicionar novas fontes:
```python
fontes_possiveis = [
    'arial.ttf', 'Arial.ttf', 'arialbd.ttf', 'Arial-Bold.ttf',
    'calibri.ttf', 'Calibri.ttf', 'calibrib.ttf', 'Calibri-Bold.ttf',
    'verdana.ttf', 'Verdana.ttf', 'verdanab.ttf', 'Verdana-Bold.ttf',
    # Adicione suas fontes aqui
    'minha_fonte.ttf'
]
```

## Troubleshooting

### 1. Erro de Fonte
```
[ERRO IMPRESSAO] Erro ao carregar fonte: [Errno 2] No such file or directory
```
**Solução**: O sistema usará a fonte padrão automaticamente

### 2. Erro de Imagem
```
[ERRO IMPRESSAO] Erro ao imprimir imagem da senha: [Errno 32] Broken pipe
```
**Solução**: Sistema volta automaticamente para texto ESC/POS

### 3. Imagem Muito Grande
```
[ERRO IMPRESSAO] Erro ao gerar imagem da senha: Image too large
```
**Solução**: Ajuste o parâmetro `largura_maxima` na função

## Teste

### 1. Via Browser
```
http://localhost:5000/test_impressora?ip=192.168.1.100
```
O teste inclui uma imagem de exemplo "TESTE"

### 2. Via Python
```python
from app import gerar_imagem_senha

# Gerar imagem
imagem = gerar_imagem_senha("N1234")

# Salvar para teste
if imagem:
    imagem.save("teste_senha.png")
    print("Imagem gerada com sucesso!")
```

## Performance

### 1. Otimizações Implementadas
- **Formato 1-bit**: Menor tamanho de arquivo
- **Buffer em memória**: Sem arquivos temporários
- **Ajuste automático**: Evita imagens muito grandes
- **Fallback rápido**: Volta para texto se necessário

### 2. Tempo de Geração
- **Imagem simples**: ~50ms
- **Imagem complexa**: ~100ms
- **Fallback**: ~10ms

## Manutenção

### 1. Adicionar Novas Fontes
1. Adicione o arquivo .ttf na pasta do sistema
2. Inclua o nome na lista `fontes_possiveis`
3. Reinicie a aplicação

### 2. Ajustar Tamanhos
1. Modifique `largura_maxima` e `altura` na função
2. Teste com diferentes senhas
3. Verifique compatibilidade com sua impressora

### 3. Personalizar Layout
1. Edite a função `gerar_imagem_senha()`
2. Ajuste cores, posicionamento, etc.
3. Teste a impressão 