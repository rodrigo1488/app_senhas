# Sistema de Fotos de Perfil dos Operadores

## Funcionalidades Implementadas

### 1. Upload de Imagens
- **Formatos suportados**: PNG, JPG, JPEG, GIF, WEBP
- **Tamanho máximo**: 5MB
- **Processamento automático**: 
  - Redimensionamento para máximo 500x500 pixels
  - Conversão para JPEG com qualidade otimizada
  - Geração de UUID único para nome do arquivo

### 2. Armazenamento
- **Localização**: `static/uploads/`
- **Nome do arquivo**: UUID único + extensão .jpg
- **Banco de dados**: Campo `foto_perfil` na tabela `operadores`

### 3. Interface
- **Formulário de cadastro**: Campo de upload com preview
- **Validação client-side**: Verificação de tipo e tamanho
- **Preview em tempo real**: Visualização da imagem selecionada
- **Tabela administrativa**: Exibição das fotos dos operadores

## Como Usar

### 1. Cadastrar Operador com Foto
1. Acesse o painel administrativo (`/admin`)
2. Clique em "Operadores" → "+ Novo Operador"
3. Preencha o nome e selecione o setor
4. Clique em "📷 Clique para selecionar uma imagem"
5. Selecione uma imagem (PNG, JPG, JPEG, GIF, WEBP)
6. Visualize o preview da imagem
7. Clique em "Adicionar"

### 2. Visualizar Fotos
- **Painel administrativo**: A tabela de operadores mostra:
  - Foto de perfil (circular, 50x50px)
  - Avatar padrão (👤) para operadores sem foto
- **Página de senhas pendentes**: 
  - Botões dos operadores com fotos (30x30px)
  - Cards de atendimento com fotos (40x40px)
  - Avatar padrão para operadores sem foto

### 3. Card da Senha Atual
- **Design moderno**: Card com gradiente roxo/azul
- **Foto do operador**: Circular (80x80px) com borda branca
- **Informações exibidas**:
  - Nome do operador
  - Status "Atendendo agora"
  - Senha atual em destaque
- **Responsivo**: Adapta-se a diferentes tamanhos de tela
- **Atualização automática**: Via WebSocket em tempo real

### 4. Tela de Senha Atual (`senha_atual.html`)
- **Design futurista**: Background com gradientes e efeitos de luz
- **Foto do operador**: Circular (80x80px) com borda verde e brilho
- **Layout moderno**: Card com backdrop blur e bordas translúcidas
- **Animações**: Efeitos de entrada suaves
- **Responsivo**: Adapta-se a diferentes tamanhos de tela
- **Atualização em tempo real**: Via WebSocket

### 5. Tela de Avaliação (`avaliacao.html`)
- **Card do operador**: Layout horizontal com foto e informações
- **Foto do operador**: Circular (70x70px) com borda azul
- **Informações exibidas**: Nome do operador e status
- **Design consistente**: Cores azuis para manter padrão visual
- **Responsivo**: Adapta-se a diferentes tamanhos de tela
- **Avatar padrão**: Para operadores sem foto

### 6. Editar Operador
- Acesse o painel administrativo e clique em "Editar" na linha do operador
- Modifique nome, setor e/ou foto de perfil
- Visualize a foto atual e opção de removê-la
- Preview da nova imagem antes de salvar

### 7. Excluir Operador
- Ao excluir um operador, a foto é automaticamente removida do servidor

## Estrutura de Arquivos

```
compuflow/
├── static/
│   └── uploads/          # Pasta para armazenar as imagens
├── templates/
│   ├── add_operador.html # Formulário com upload
│   └── admin.html        # Tabela com fotos
├── app.py               # Lógica principal
├── migrate_db.py        # Script de migração
└── requirements.txt     # Dependências
```

## Configurações

### Variáveis de Configuração (app.py)
```python
UPLOAD_FOLDER = 'static/uploads'           # Pasta de uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}  # Extensões permitidas
MAX_FILE_SIZE = 5 * 1024 * 1024           # 5MB máximo
```

### Processamento de Imagem
- **Redimensionamento**: Máximo 500x500 pixels
- **Formato final**: JPEG com qualidade 85%
- **Otimização**: Ativada para reduzir tamanho

## Segurança

### Validações Implementadas
1. **Tipo de arquivo**: Apenas imagens permitidas
2. **Tamanho**: Máximo 5MB
3. **Nome único**: UUID evita conflitos
4. **Sanitização**: Nome do arquivo seguro

### Limpeza Automática
- Imagens antigas são removidas quando o operador é excluído
- Tratamento de erros para operações de arquivo

## Migração

Para bancos de dados existentes, execute:
```bash
python migrate_db.py
```

Este script adiciona o campo `foto_perfil` à tabela `operadores` se ele não existir.

## Dependências

As seguintes bibliotecas são necessárias:
- `Pillow` (PIL) - Processamento de imagens
- `uuid` - Geração de IDs únicos (módulo padrão)
- `werkzeug` - Utilitários Flask (já incluído)

## Rotas Adicionadas

- `POST /admin/operador/add` - Cadastro com upload de imagem
- `GET /admin/operador/edit/<id>` - Edição de operador
- `POST /admin/operador/edit/<id>` - Salvar alterações do operador
- `GET /uploads/<filename>` - Servir imagens de perfil 