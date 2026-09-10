import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response, session, g, request as flask_request, send_from_directory, flash
from flask_socketio import SocketIO, emit
import supabase
import sqlite3
import random
from escpos.printer import Network
import socket  # Corrigido: Importação do módulo socket
import os
import sys
from dotenv import load_dotenv
import threading
from datetime import timedelta
import time
import datetime
import uuid
import qrcode
import json
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import io
from flask_socketio import join_room
from collections import defaultdict


load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env

# Detectar se está rodando como executável PyInstaller
def resource_path(relative_path):
    """Obtém o caminho absoluto para recursos, funciona para dev e PyInstaller"""
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Configuração do Flask e SocketIO
# Ajustar caminho dos templates e static para funcionar com PyInstaller
if getattr(sys, 'frozen', False):
    # Se está rodando como executável compilado
    template_folder = resource_path('templates')
    static_folder = resource_path('static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    # Se está rodando como script Python normal
    app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)

# Configurações de sessão para persistência
app.config['SESSION_COOKIE_SECURE'] = False  # Para desenvolvimento local
app.config['SESSION_COOKIE_HTTPONLY'] = False  # Permite acesso via JavaScript
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Política de segurança
app.config['SESSION_COOKIE_MAX_AGE'] = 60 * 60 * 24 * 365  # 1 ano

# Configurações para upload de imagens
# Ajustar caminho para funcionar com PyInstaller
if getattr(sys, 'frozen', False):
    # Executável PyInstaller - usar diretório do executável
    base_dir = os.path.dirname(sys.executable) if hasattr(sys, 'executable') else os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(base_dir, 'static', 'uploads')
else:
    # Script Python normal
    UPLOAD_FOLDER = 'static/uploads'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Criar pasta de uploads se não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
socketio = SocketIO(app)


IMPRESSORA_PORTA = 9100
# Recupera os valores
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supa_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

# Caminho do banco de dados local padrão
# Ajustar para funcionar com PyInstaller
if getattr(sys, 'frozen', False):
    # Executável PyInstaller - usar diretório do executável
    base_dir = os.path.dirname(sys.executable) if hasattr(sys, 'executable') else os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(base_dir, "appsenhas.sqlite")
else:
    # Script Python normal
    DB_PATH = "appsenhas.sqlite"

# Variável global para armazenar a senha atual
senha_atual = None
setor_locks = defaultdict(threading.Lock)  # Lock por setor para serializar chamadas

# Configuração de proporção e alerta
PROPORCAO_NORMAIS = 2  # Quantas normais para cada preferencial
LIMITE_PREFERENCIAIS_ALERTA = 3  # Se houver mais que isso, prioriza preferencial e alerta

# Configuração da empresa
NOME_EMPRESA_PADRAO = "TESTE" # Personalize com o nome da sua empresa

# Configuração de cookies
app.config['SESSION_COOKIE_SECURE'] = False  # Para desenvolvimento local
app.config['SESSION_COOKIE_HTTPONLY'] = False  # Permite acesso via JavaScript

# Configurações VAPID para Web Push Notifications
VAPID_PRIVATE_KEY = "OBrReW-zVxCF6JWKKRyQNNNkPbY-8plD2cFdajsJ-dk"
VAPID_PUBLIC_KEY = "m8SlKTywMoMWfmtEYVdH7SMWFOQjGeMMvP7Q-d8FSwY"
VAPID_EMAIL = "seu-email@exemplo.com"

def obter_nome_empresa():
    """Retorna o nome da empresa, priorizando configurações personalizadas"""
    # Primeiro tenta buscar de um cookie (se disponível)
    try:
        if hasattr(request, 'cookies'):
            nome_cookie = request.cookies.get('nome_empresa')
            print(f"[EMPRESA] Cookie encontrado: {nome_cookie}")
            if nome_cookie:
                print(f"[EMPRESA] Usando nome do cookie: {nome_cookie}")
                return nome_cookie
    except Exception as e:
        print(f"[EMPRESA] Erro ao buscar cookie: {e}")
        pass
    
    # Se não encontrar no cookie, usa o valor padrão
    print(f"[EMPRESA] Usando nome padrão: {NOME_EMPRESA_PADRAO}")
    return NOME_EMPRESA_PADRAO

def gerar_token_unico():
    """Gera um token único para notificações"""
    return str(uuid.uuid4())

def obter_ip_rede_local():
    """Obtém o IP da rede local para uso no QR Code"""
    try:
        import socket
        # Conectar a um endereço externo para descobrir o IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        return ip_local
    except Exception as e:
        print(f"[ERRO] Erro ao obter IP local: {e}")
        return "localhost"

def get_ngrok_url():
    """Obtém a URL do ngrok das configurações"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'ngrok_url'")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else ''
    except Exception as e:
        print(f"Erro ao obter URL do ngrok: {e}")
        return ''

def get_notification_url(token):
    """Gera a URL para notificações, usando ngrok se configurado"""
    ngrok_url = get_ngrok_url()
    
    if ngrok_url:
        # Usar URL do ngrok se configurada
        base_url = ngrok_url.rstrip('/')
        return f"{base_url}/notificacao/{token}"
    else:
        # Usar IP local
        ip_local = obter_ip_rede_local()
        return f"http://{ip_local}:5000/notificacao/{token}"

def gerar_qr_code_notificacao(token_unico):
    """Gera um QR Code com o link de notificação"""
    try:
        # Usar a função que já suporta ngrok
        url_notificacao = get_notification_url(token_unico)
        
        print(f"[QR CODE] Gerando QR Code para: {url_notificacao}")
        
        # Criar QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr.add_data(url_notificacao)
        qr.make(fit=True)
        
        # Criar imagem do QR Code
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para bytes
        buffer = io.BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer
    except Exception as e:
        print(f"[ERRO] Erro ao gerar QR Code: {e}")
        return None

def validar_operador_avaliacao(operador):
    """Valida se o operador tem avaliação válida (não None)"""
    if operador and operador[1] is not None:
        return operador
    return None

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file):
    """Processa e salva a imagem com UUID único"""
    try:
        # Gerar UUID único para o nome do arquivo
        file_uuid = str(uuid.uuid4())
        
        # Ler a imagem
        image = Image.open(file)
        
        # Converter para RGB se necessário (para compatibilidade com JPEG)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Redimensionar se a imagem for muito grande (máximo 500x500)
        max_size = (500, 500)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Salvar como JPEG com qualidade otimizada
        filename = f"{file_uuid}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        image.save(filepath, 'JPEG', quality=85, optimize=True)
        
        return filename
    except Exception as e:
        print(f"Erro ao processar imagem: {e}")
        return None

def gerar_imagem_senha(senha, largura_maxima=384):
    """
    Gera uma imagem bitmap da senha para impressão térmica
    
    Args:
        senha (str): Número da senha
        largura_maxima (int): Largura máxima da imagem (padrão 384px)
    
    Returns:
        PIL.Image: Imagem bitmap da senha
    """
    try:
        # Configurações da imagem
        # Para impressão térmica, usar proporção adequada
        # Largura: 384px (padrão impressoras térmicas)
        # Altura: proporcional para garantir orientação horizontal
        altura = 80  # Altura reduzida para melhor proporção
        cor_fundo = 255  # Branco
        cor_texto = 0    # Preto
        
        # Criar imagem em escala de cinza (1-bit) - LARGURA x ALTURA
        # Proporção 384x80 garante orientação horizontal
        imagem = Image.new('L', (largura_maxima, altura), cor_fundo)
        draw = ImageDraw.Draw(imagem)
        
        # Tentar usar uma fonte do sistema, fallback para fonte padrão
        try:
            # Tentar fontes comuns do sistema
            fontes_possiveis = [
                'arial.ttf', 'Arial.ttf', 'arialbd.ttf', 'Arial-Bold.ttf',
                'calibri.ttf', 'Calibri.ttf', 'calibrib.ttf', 'Calibri-Bold.ttf',
                'verdana.ttf', 'Verdana.ttf', 'verdanab.ttf', 'Verdana-Bold.ttf'
            ]
            
            fonte = None
            tamanho_fonte = 72  # Tamanho inicial aumentado em 20% (60 * 1.2 = 72)
            
            for fonte_nome in fontes_possiveis:
                try:
                    fonte = ImageFont.truetype(fonte_nome, tamanho_fonte)
                    break
                except:
                    continue
            
            # Se não encontrou fonte do sistema, usar padrão
            if fonte is None:
                fonte = ImageFont.load_default()
                tamanho_fonte = 48  # Tamanho aumentado em 20% (40 * 1.2 = 48)
                
        except Exception as e:
            print(f"[IMPRESSAO] Erro ao carregar fonte: {e}")
            fonte = ImageFont.load_default()
            tamanho_fonte = 60
        
        # Calcular posição central do texto
        bbox = draw.textbbox((0, 0), senha, font=fonte)
        largura_texto = bbox[2] - bbox[0]
        altura_texto = bbox[3] - bbox[1]
        
        # Se o texto for muito largo, reduzir o tamanho da fonte
        while largura_texto > largura_maxima - 20 and tamanho_fonte > 18:  # Aumentado em 20% (15 * 1.2 = 18)
            tamanho_fonte -= 5
            try:
                fonte = ImageFont.truetype(fonte_nome, tamanho_fonte) if fonte_nome else ImageFont.load_default()
            except:
                fonte = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), senha, font=fonte)
            largura_texto = bbox[2] - bbox[0]
            altura_texto = bbox[3] - bbox[1]
        
        # Calcular posição central
        x = (largura_maxima - largura_texto) // 2
        y = (altura - altura_texto) // 2
        
        # Desenhar o texto
        draw.text((x, y), senha, fill=cor_texto, font=fonte)
        
        # Converter para bitmap 1-bit (preto e branco puro)
        imagem_bw = imagem.convert('1')
        
        print(f"[IMPRESSAO] Imagem da senha '{senha}' gerada com sucesso ({largura_maxima}x{altura})")
        return imagem_bw
        
    except Exception as e:
        print(f"[ERRO IMPRESSAO] Erro ao gerar imagem da senha 'resa{senha}': {e}")
        return None

def delete_old_image(filename):
    """Deleta uma imagem antiga se existir"""
    if filename:
        try:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Erro ao deletar imagem: {e}")

def init_local_db():
    """Inicializa o banco de dados local padrão se não existir."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS senhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            setor_id INTEGER,
            status TEXT DEFAULT 'A',
            token_unico TEXT UNIQUE,
            notificado INTEGER DEFAULT 0,
            push_subscription TEXT,
            pedido TEXT,
            tem_pedido BOOLEAN DEFAULT 0,
            FOREIGN KEY (setor_id) REFERENCES setores (id)
        )
    ''')
    
    # Verificar se a coluna pedido existe, se não, adicionar
    cursor.execute("PRAGMA table_info(senhas)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'pedido' not in columns:
        cursor.execute("ALTER TABLE senhas ADD COLUMN pedido TEXT")
        print("✅ Coluna 'pedido' adicionada à tabela senhas")
    
    if 'tem_pedido' not in columns:
        cursor.execute("ALTER TABLE senhas ADD COLUMN tem_pedido BOOLEAN DEFAULT 0")
        print("✅ Coluna 'tem_pedido' adicionada à tabela senhas")
    
    conn.commit()
    conn.close()

def ensure_table_exists(db_path):
    """Garante que todas as tabelas necessárias existam no banco de dados"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar se a coluna pedido existe na tabela senhas
    try:
        cursor.execute("PRAGMA table_info(senhas)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'pedido' not in columns:
            cursor.execute("ALTER TABLE senhas ADD COLUMN pedido TEXT")
            print("✅ Coluna 'pedido' adicionada à tabela senhas")
        
        if 'tem_pedido' not in columns:
            cursor.execute("ALTER TABLE senhas ADD COLUMN tem_pedido BOOLEAN DEFAULT 0")
            print("✅ Coluna 'tem_pedido' adicionada à tabela senhas")
            
    except sqlite3.OperationalError:
        print("❌ Tabela 'senhas' não existe ainda")
    
    conn.commit()
    conn.close()

end_banco_local = "appsenhas.sqlite"  # Caminho do banco de dados local


@app.route('/check_helth', methods=['GET'])
def check_helth():
    return jsonify({'status': 'ok'})

@app.route('/test_cookie', methods=['GET'])
def test_cookie():
    """Rota para testar se os cookies estão funcionando"""
    auth_result = require_login()
    if auth_result:
        return auth_result
    
    # Mostrar todos os cookies
    cookies_info = {}
    for key, value in request.cookies.items():
        cookies_info[key] = value
    
    # Testar definição de cookie
    resp = make_response(f"""
    <h1>Teste de Cookies</h1>
    <h2>Cookies Atuais:</h2>
    <pre>{cookies_info}</pre>
    
    <h2>Nome da Empresa Atual:</h2>
    <p>Cookie: {request.cookies.get('nome_empresa', 'Não definido')}</p>
    <p>Função obter_nome_empresa(): {obter_nome_empresa()}</p>
    <p>Valor padrão: {NOME_EMPRESA_PADRAO}</p>
    
    <h2>Teste de Definição:</h2>
    <form method="POST" action="/test_cookie_set">
        <input type="text" name="nome_empresa" value="EMPRESA TESTE" placeholder="Nome da empresa">
        <button type="submit">Definir Cookie</button>
    </form>
    
    <p><a href="/admin">Voltar ao Painel</a></p>
    """)
    
    return resp

@app.route('/test_cookie_set', methods=['POST'])
def test_cookie_set():
    """Rota para testar definição de cookie"""
    auth_result = require_login()
    if auth_result:
        return auth_result
    
    nome_empresa = request.form.get('nome_empresa', 'EMPRESA TESTE')
    resp = make_response(redirect(url_for('test_cookie')))
    resp.set_cookie('nome_empresa', nome_empresa, 
                   max_age=60*60*24*365,  # 1 ano
                   path='/',              # Disponível em todo o site
                   httponly=False,        # Acessível via JavaScript
                   secure=False,          # Para desenvolvimento local
                   samesite='Lax')        # Política de segurança
    print(f"[TESTE] Cookie definido: nome_empresa={nome_empresa}")
    return resp

@app.route('/test_impressora', methods=['GET'])
def test_impressora():
    """Testa a conectividade com a impressora térmica"""
    p = None
    try:
        impressora_ip = request.args.get('ip') or request.cookies.get('end_impressora_local')
        if not impressora_ip:
            return jsonify({'error': 'IP da impressora não fornecido'}), 400
        
        print(f"[TESTE] Testando conectividade com impressora {impressora_ip}")
        
        # Tenta conectar à impressora
        p = Network(impressora_ip, IMPRESSORA_PORTA)
        
        # Envia um teste simples com melhor espaçamento
        p.set(align='center')
        p.text("\n")  # Espaço inicial
        p.text("=" * 20 + "\n")  # Linha separadora
        
        # Nome da empresa no teste
        p.text('\x1B\x21\x10')  # Fonte um pouco maior
        p.text(f"{obter_nome_empresa()}\n")
        p.text('\x1B\x21\x00')  # Volta para fonte normal
        p.text("TESTE DE CONECTIVIDADE\n")
        p.text("=" * 20 + "\n")  # Linha separadora
        
        # Teste de imagem da senha
        p.text("TESTE IMAGEM SENHA:\n")
        imagem_teste = gerar_imagem_senha("TESTE", 384)
        if imagem_teste:
            try:
                buffer = io.BytesIO()
                imagem_teste.save(buffer, format='PNG')
                buffer.seek(0)
                p.image(buffer, impl='bitImageRaster')
                p.text("Imagem enviada com sucesso!\n")
            except Exception as e:
                p.text(f"Erro na imagem: {str(e)[:20]}...\n")
        else:
            p.text("Falha ao gerar imagem\n")
        
        # Informações com fonte menor
        p.text('\x1B\x21\x00')  # Define fonte menor
        p.text(f"IP: {impressora_ip}\n")
        p.text(f"Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        p.text("=" * 20 + "\n")  # Linha separadora inferior
        p.cut()
        
        return jsonify({'success': True, 'message': f'Teste enviado com sucesso para {impressora_ip}'})
        
    except Exception as e:
        print(f"[ERRO TESTE] Erro ao testar impressora: {e}")
        return jsonify({'error': f'Erro ao conectar com impressora: {str(e)}'}), 500
    finally:
        # Fecha a conexão com a impressora
        if p:
            try:
                p.close()
                print(f"[TESTE] Conexão com impressora {impressora_ip} fechada")
            except Exception as e:
                print(f"[ERRO TESTE] Erro ao fechar conexão com impressora: {e}")

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Rota para servir as imagens de perfil"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Se já estiver logado e tiver setor_id, redireciona para a home
    if 'user_id' in session and flask_request.cookies.get('setor_id'):
        return redirect(url_for('render_senhas'))
    if flask_request.method == 'POST':
        email = flask_request.form['email']
        senha = flask_request.form['senha']
        
        # Consulta na tabela `users` do Supabase
        response = supa_client.from_('users').select('*').eq('email', email).single().execute()
        
        if response.data:
            user = response.data
            if user['senha'] == senha:  # Verificação simples de senha
                

                ensure_table_exists(end_banco_local)  # Garante que a tabela `senhas` existe
                session['user_id'] = user['id']
                session.permanent = True  # Tornar a sessão permanente
                resp = make_response(redirect(url_for('selecionar_setor')))
                print(response)
                # Armazena o caminho do banco local
    
                # Armazena o endereço IP da impressora
                resp.set_cookie('user_id', str(user['id']), max_age=60*60*24*365)  # 1 ano
                resp.set_cookie('nome_empresa', str(user['nome_empresa']), max_age=60*60*24*365)  # 1 ano
                return resp
            else:
                return "Senha incorreta."
        else:
            return "Usuário não encontrado."
    
    return render_template('login.html')

def require_login():
    """Verifica se o usuário está logado usando sessão ou cookies"""
    # Primeiro verifica a sessão
    if 'user_id' in session:
        # Tornar a sessão permanente
        session.permanent = True
        return None  # Usuário logado via sessão
    
    # Se não há sessão, verifica cookies
    user_id_cookie = request.cookies.get('user_id')
    if user_id_cookie:
        # Restaura a sessão a partir do cookie
        try:
            session['user_id'] = user_id_cookie
            session.permanent = True  # Tornar a sessão permanente
            print(f"[AUTH] Sessão restaurada do cookie: {user_id_cookie}")
            return None  # Usuário logado via cookie
        except Exception as e:
            print(f"[AUTH] Erro ao restaurar sessão: {e}")
    
    # Se não há nem sessão nem cookie válido, redireciona para login
    return redirect(url_for('login'))

def get_ip_impressora():
    conn = sqlite3.connect(end_banco_local)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO senhas (senha, tipo) VALUES (?, ?)", (codigo_senha, tipo))
    conn.commit()
    conn.close()

def atualizar_senhas_periodicamente():
    while True:
        socketio.sleep(1)  # Atualiza a cada 5 segundos (ajuste conforme necessário)
        end_banco_local = "local_db.sqlite"  # Modifique para a variável correta se necessário
        
        if not os.path.exists(end_banco_local):
            continue

        conn = sqlite3.connect(end_banco_local)
        cursor = conn.cursor()
        cursor.execute("SELECT id, senha, tipo FROM senhas ORDER BY tipo DESC, id ASC")
        senhas_pendentes = cursor.fetchall()
        conn.close()

        # Emite o evento para todos os clientes conectados
        socketio.emit('atualizar_lista', {'senhas': senhas_pendentes})


# Inicia a atualização contínua em uma thread separada
threading.Thread(target=atualizar_senhas_periodicamente, daemon=True).start()


@app.route('/')
def home():
    auth_result = require_login()
    if auth_result:
        return auth_result
    # Redireciona para a seleção de setores
    return redirect(url_for('selecionar_setor'))

@app.route('/senhas', methods=['GET', 'POST'])
def render_senhas():
    auth_result = require_login()
    if auth_result:
        return auth_result
    return render_template('senhas.html')

@app.route('/setores', methods=['GET', 'POST'])
def selecionar_setor():
    auth_result = require_login()
    if auth_result:
        return auth_result
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, descricao FROM setores')
    setores = cursor.fetchall()
    conn.close()

    if request.method == 'POST':
        setor_id = request.form['setor_id']
        # Buscar impressora do setor
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT ip FROM impressoras WHERE setor_id = ?', (setor_id,))
        impressora = cursor.fetchone()
        conn.close()
        resp = make_response(redirect(url_for('setor_opcoes', setor_id=setor_id)))
        resp.set_cookie('setor_id', str(setor_id))
        resp.set_cookie('end_banco_local', 'appsenhas.sqlite')  # Valor fixo
        if impressora:
            resp.set_cookie('end_impressora_local', impressora[0])
        return resp
    return render_template('selecionar_setor.html', setores=setores)

@app.route('/setor/<int:setor_id>/opcoes')
def setor_opcoes(setor_id):
    auth_result = require_login()
    if auth_result:
        return auth_result
    return render_template('setor_opcoes.html', setor_id=setor_id)

def imprimir_senha(senha):
    """Envia a senha para a impressora térmica usando ESC/POS"""
    try:
        # Recupera o IP da impressora do cookie
        impressora_ip = request.cookies.get('end_impressora_local')
        if not impressora_ip:
            # Caso não haja o cookie, utilize um valor padrão (opcional)
            return jsonify({'error': 'Endereço IP da impressora não encontrado.'}), 400
        
        # Usa a função melhorada de impressão
        return imprimir_senha_com_ip(senha, impressora_ip)
        
    except Exception as e:
        print(f"Erro ao imprimir: {e}")
        return False

@app.route('/retirar_senha/<tipo>')
def retirar_senha(tipo):
    auth_result = require_login()
    if auth_result:
        return auth_result
    end_banco_local = request.cookies.get('end_banco_local') or 'appsenhas.sqlite'
    setor_id = request.cookies.get('setor_id')
    impressora_ip = request.cookies.get('end_impressora_local')

    # Buscar IP da impressora do setor no banco se não estiver no cookie
    if not impressora_ip and setor_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT ip FROM impressoras WHERE setor_id = ?', (setor_id,))
        impressora = cursor.fetchone()
        conn.close()
        if impressora:
            impressora_ip = impressora[0]

    if not end_banco_local:
        end_banco_local = 'appsenhas.sqlite'
    if not impressora_ip:
        return "Impressora do setor não encontrada."
    if not setor_id:
        return "Setor não selecionado."

    codigo_senha = f"{tipo[:1].upper()}{random.randint(1000, 9999)}"
    token_unico = gerar_token_unico()

    # Conectar ao banco e armazenar a senha, incluindo setor_id e token
    conn = sqlite3.connect(end_banco_local)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO senhas (senha, tipo, setor_id, token_unico) VALUES (?, ?, ?, ?)", 
                   (codigo_senha, tipo, setor_id, token_unico))
    conn.commit()
    conn.close()

    # Buscar dados do setor para impressão
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT nome, descricao FROM setores WHERE id = ?', (setor_id,))
    setor_info = cursor.fetchone()
    conn.close()
    
    # Enviar para impressão
    resp = make_response(redirect(url_for('render_senhas')))
    resp.set_cookie('end_impressora_local', impressora_ip)
    resp.set_cookie('end_banco_local', 'appsenhas.sqlite')  # Valor fixo
    resp.set_cookie('setor_id', str(setor_id))
    
    # Passar informações do setor para impressão
    nome_setor = setor_info[0] if setor_info else "Setor"
    descricao_setor = setor_info[1] if setor_info else ""
    
    imprimir_senha_com_ip(codigo_senha, impressora_ip, nome_setor, descricao_setor, token_unico)
    # Emitir evento para atualizar lista de senhas pendentes
    socketio.emit('atualizar_lista_senhas', {'setor_id': setor_id})
    return resp

def imprimir_senha_com_ip(senha, impressora_ip, nome_setor="Setor", descricao_setor="", token_unico=None):
    """Envia a senha para a impressora térmica usando ESC/POS com imagem bitmap da senha"""
    p = None
    try:
        print(f"[IMPRESSAO] Tentando imprimir senha '{senha}' na impressora {impressora_ip}")
        
        # Conecta à impressora térmica
        p = Network(impressora_ip, IMPRESSORA_PORTA)
        
        # Configurações da impressão
        p.set(align='center')  # Alinha no centro
        
        # Cabeçalho com fonte normal
        p.text('\x1B\x21\x00')  # Define fonte normal
        p.text("\n")  # Espaço inicial
        p.text("=" * 32 + "\n")  # Linha separadora superior
        p.text("\n")  # Espaço após separadora
        
        # Nome da empresa
        p.text('\x1B\x21\x10')  # Fonte um pouco maior
        p.text(f"{obter_nome_empresa()}\n")
        p.text('\x1B\x21\x00')  # Volta para fonte normal
        p.text("\n")  # Espaço após empresa
        
        
        # Gerar e imprimir imagem da senha
        imagem_senha = gerar_imagem_senha(senha)
        if imagem_senha:
            try:
                # Salvar imagem temporariamente em buffer
                buffer = io.BytesIO()
                imagem_senha.save(buffer, format='PNG')
                buffer.seek(0)
                
                # Imprimir a imagem da senha
                # Usar bitImageRaster para melhor compatibilidade
                p.image(buffer, impl='bitImageRaster', center=True)
                print(f"[IMPRESSAO] Imagem da senha '{senha}' enviada com sucesso")
                
            except Exception as e:
                print(f"[ERRO IMPRESSAO] Erro ao imprimir imagem da senha: {e}")
                # Fallback: imprimir senha como texto
                p.text('\x1B\x21\x30')  # Fonte grande
                p.text(f"{senha}\n")
                p.text('\x1B\x21\x00')  # Volta para fonte normal
        else:
            # Fallback: imprimir senha como texto se falhar ao gerar imagem
            p.text('\x1B\x21\x30')  # Fonte grande
            p.text(f"{senha}\n")
            p.text('\x1B\x21\x00')  # Volta para fonte normal
        
        p.text("\n")  # Espaço após a senha
        p.text("=" * 32 + "\n")  # Linha separadora
        
        # Data e hora com fonte menor
        p.text(f"Data: {datetime.datetime.now().strftime('%d/%m/%Y')}\n")
        p.text(f"Hora: {datetime.datetime.now().strftime('%H:%M')}\n")
        
        # Nome do setor
        p.text(f"{nome_setor}\n")
        if descricao_setor:
            p.text(f"{descricao_setor}\n")
        p.text("=" * 32 + "\n")  # Linha separadora
        
        # QR Code para notificação (se token disponível)
        if token_unico:
            p.text("\n")  # Espaço antes do QR Code
            p.text("Escaneie para receber\n")
            p.text("notificação quando\n")
            p.text("for sua vez\n")
            p.text("\n")  # Espaço após texto
            
            # Gerar e imprimir QR Code
            qr_buffer = gerar_qr_code_notificacao(token_unico)
            if qr_buffer:
                try:
                    p.image(qr_buffer, impl='bitImageRaster', center=True)
                    print(f"[IMPRESSAO] QR Code da notificação enviado para senha '{senha}'")
                except Exception as e:
                    print(f"[ERRO IMPRESSAO] Erro ao imprimir QR Code: {e}")
            
            p.text("\n")  # Espaço após QR Code
        
        # Mensagem inferior com fonte menor
        p.text("Aguarde ser chamada\n")
        p.text("na tela de atendimento\n")
        p.text("=" * 32 + "\n")  # Linha separadora inferior
        
        # Corta o papel
        p.cut()
        
        print(f"[IMPRESSAO] Senha '{senha}' enviada com sucesso para {impressora_ip}")
        return True
        
    except Exception as e:
        print(f"[ERRO IMPRESSAO] Erro ao imprimir senha '{senha}': {e}")
        return False
    finally:
        # Fecha a conexão com a impressora
        if p:
            try:
                p.close()
                print(f"[IMPRESSAO] Conexão com impressora {impressora_ip} fechada")
            except Exception as e:
                print(f"[ERRO IMPRESSAO] Erro ao fechar conexão com impressora: {e}")

@app.route('/senhas_pendentes')
def senhas_pendentes():
    """Renderiza a página de senhas pendentes."""
    auth_result = require_login()
    if auth_result:
        return auth_result
    setor_id = request.cookies.get('setor_id')
    operador_id = request.cookies.get('operador_id')
    print(f'[SENHAS_PENDENTES] operador_id={operador_id}, setor_id={setor_id}')
    if not setor_id:
        return "Setor não selecionado."
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, senha, tipo FROM senhas WHERE setor_id = ? AND status = 'A' ORDER BY tipo DESC, id ASC", (setor_id,))
    senhas = cursor.fetchall()
    cursor.execute("SELECT id, nome, foto_perfil FROM operadores WHERE setor_id = ?", (setor_id,))
    operadores = cursor.fetchall()
    # Buscar apenas o último atendimento de cada operador
    cursor.execute('''
        SELECT a.operador_id, o.nome, s.senha, s.tipo, o.foto_perfil
        FROM atendimento_atual a
        JOIN operadores o ON a.operador_id = o.id
        JOIN senhas s ON a.senha_id = s.id
        WHERE a.setor_id = ?
        AND a.id = (
            SELECT MAX(id) FROM atendimento_atual a2 WHERE a2.operador_id = a.operador_id AND a2.setor_id = a.setor_id
        )
        ORDER BY o.nome ASC
    ''', (setor_id,))
    atendimentos = cursor.fetchall()
    conn.close()
    return render_template('senhas_pendentes.html', senhas=senhas, operadores=operadores, atendimentos=atendimentos)

@socketio.on('chamar_proxima')
def handle_chamar_proxima():
    """Chama a próxima senha e atualiza todos os clientes."""
    global senha_atual
    end_banco_local = request.cookies.get('end_banco_local')
    if not end_banco_local or not os.path.exists(end_banco_local):
        emit('erro', {'mensagem': 'Banco de dados local não encontrado.'})
        return

    ensure_table_exists(end_banco_local)

    conn = sqlite3.connect(end_banco_local)
    cursor = conn.cursor()
    
    # Buscar a próxima senha com pedido
    cursor.execute("SELECT id, senha, pedido FROM senhas ORDER BY tipo DESC, id ASC LIMIT 1")
    proxima_senha = cursor.fetchone()

    if proxima_senha:
        senha_id, senha_atual, pedido = proxima_senha
        
        # Atualizar status para 'C' (Chamada)
        cursor.execute("UPDATE senhas SET status = 'C' WHERE id = ?", (senha_id,))
        conn.commit()

        # Buscar todas as senhas pendentes
        cursor.execute("SELECT id, senha, tipo FROM senhas ORDER BY tipo DESC, id ASC")
        senhas_pendentes = cursor.fetchall()
        conn.close()

        # Emitir evento para atualizar lista
        emit('atualizar_lista', {'senha_atual': senha_atual, 'senhas': senhas_pendentes}, broadcast=True)
        
        # Se há pedido, emitir evento específico
        if pedido:
            socketio.emit('senha_chamada_com_pedido', {
                'senha_id': senha_id,
                'senha': senha_atual,
                'pedido': pedido,
                'setor': 'Geral'  # Para compatibilidade
            })
            print(f'[SOCKET] Senha {senha_atual} chamada com pedido: {pedido}')
    else:
        senha_atual = None
        emit('erro', {'mensagem': 'Nenhuma senha disponível.'})
        conn.close()

@app.route('/senha_atual')
def senha_atual_view():
    """Renderiza a página para exibir a senha atual."""
    auth_result = require_login()
    if auth_result:
        return auth_result
    
    # Verificar se tem setor_id no cookie
    setor_id = request.cookies.get('setor_id')
    if not setor_id:
        # Se não tem setor_id, redirecionar para seleção de setor
        return redirect(url_for('selecionar_setor'))
    
    return render_template('senha_atual.html')

@app.route('/get_senha_atual')
def get_senha_atual():
    """Endpoint para retornar a senha atual em formato JSON."""
    global senha_atual
    return jsonify({'senha_atual': senha_atual if senha_atual else 'Aguardando próxima senha...'})

@app.route('/get_senha_atual_setor')
def get_senha_atual_setor():
    setor_id = flask_request.cookies.get('setor_id')
    print(f"[GET_SENHA_ATUAL] setor_id do cookie: {setor_id}")
    
    if not setor_id:
        return jsonify({'senha_atual': 'Setor não selecionado.', 'operador': '', 'foto_operador': None, 'tem_pedido': False, 'pedido': None})
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Busca a senha atual (status C = Chamada) e o operador que está atendendo
        cursor.execute("""
            SELECT s.senha, o.nome, o.foto_perfil, s.pedido, s.tem_pedido, s.pedido_confirmado
            FROM senhas s
            JOIN atendimento_atual a ON a.senha_id = s.id
            JOIN operadores o ON a.operador_id = o.id
            WHERE s.setor_id = ? AND s.status = 'C'
            ORDER BY s.id DESC LIMIT 1
        """, (setor_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"[GET_SENHA_ATUAL] Senha encontrada: {row[0]}, Operador: {row[1]}")
            return jsonify({
                'senha_atual': row[0], 
                'operador': row[1], 
                'foto_operador': row[2],
                'tem_pedido': bool(row[4]) if row[4] is not None else False,
                'pedido': row[3] if row[3] else None,
                'pedido_confirmado': bool(row[5]) if row[5] is not None else False
            })
        else:
            print(f"[GET_SENHA_ATUAL] Nenhuma senha em atendimento para setor {setor_id}")
            return jsonify({
                'senha_atual': 'Aguardando próxima senha...', 
                'operador': '', 
                'foto_operador': None,
                'tem_pedido': False,
                'pedido': None,
                'pedido_confirmado': False
            })
            
    except Exception as e:
        print(f"[GET_SENHA_ATUAL] Erro: {e}")
        return jsonify({
            'senha_atual': 'Erro ao buscar senha', 
            'operador': '', 
            'foto_operador': None,
            'tem_pedido': False,
            'pedido': None,
            'pedido_confirmado': False
        })

@app.route('/check_webview_update')
def check_webview_update():
    """Rota específica para WebView verificar atualizações"""
    auth_result = require_login()
    if auth_result:
        return jsonify({'error': 'Usuário não autenticado'})
    
    setor_id = request.cookies.get('setor_id')
    if not setor_id:
        return jsonify({'error': 'Setor não selecionado'})
    
    end_banco_local = request.cookies.get('end_banco_local') or 'appsenhas.sqlite'
    
    try:
        conn = sqlite3.connect(end_banco_local)
        cursor = conn.cursor()
        
        # Verificar senha atual
        cursor.execute("SELECT senha FROM senhas WHERE setor_id = ? ORDER BY id DESC LIMIT 1", (setor_id,))
        senha_result = cursor.fetchone()
        senha_atual = senha_result[0] if senha_result else None
        
        # Verificar se há avaliação pendente
        cursor.execute("SELECT COUNT(*) FROM senhas WHERE setor_id = ? AND avaliada = 0", (setor_id,))
        avaliacoes_pendentes = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'senha_atual': senha_atual,
            'avaliacoes_pendentes': avaliacoes_pendentes,
            'timestamp': datetime.datetime.now().isoformat(),
            'force_reload': avaliacoes_pendentes > 0
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get_atendimentos')
def get_atendimentos():
    setor_id = flask_request.cookies.get('setor_id')
    if not setor_id:
        return jsonify([])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Buscar apenas o último atendimento de cada operador
    cursor.execute('''
        SELECT a.operador_id, o.nome, s.senha, s.tipo, o.foto_perfil
        FROM atendimento_atual a
        JOIN operadores o ON a.operador_id = o.id
        JOIN senhas s ON a.senha_id = s.id
        WHERE a.setor_id = ?
        AND a.id = (
            SELECT MAX(id) FROM atendimento_atual a2 WHERE a2.operador_id = a.operador_id AND a2.setor_id = a.setor_id
        )
        ORDER BY o.nome ASC
    ''', (setor_id,))
    atendimentos = cursor.fetchall()
    conn.close()
    return jsonify([
        {'operador_id': a[0], 'nome': a[1], 'senha': a[2], 'tipo': a[3], 'foto_perfil': a[4]} for a in atendimentos
    ])

@app.route('/get_senhas_pendentes')
def get_senhas_pendentes():
    """Retorna as senhas pendentes em formato JSON"""
    auth_result = require_login()
    if auth_result:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    setor_id = request.cookies.get('setor_id')
    if not setor_id:
        return jsonify({'error': 'Setor não selecionado'}), 400
    
    print(f'[GET_SENHAS_PENDENTES] Buscando senhas para setor_id: {setor_id}')
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, senha, tipo, pedido, tem_pedido 
            FROM senhas 
            WHERE setor_id = ? AND status = 'A' 
            ORDER BY id ASC
        """, (setor_id,))
        
        senhas = cursor.fetchall()
        conn.close()
        
        print(f'[GET_SENHAS_PENDENTES] Encontradas {len(senhas)} senhas pendentes')
        
        # Converter para formato JSON
        senhas_json = []
        for senha in senhas:
            senha_data = {
                'id': senha[0],
                'senha': senha[1],
                'tipo': senha[2],
                'pedido': senha[3],
                'tem_pedido': bool(senha[4])
            }
            senhas_json.append(senha_data)
            
            # Log detalhado de cada senha
            print(f'[GET_SENHAS_PENDENTES] Senha: {senha[1]}, Pedido: "{senha[3]}", Tem pedido: {bool(senha[4])}')
        
        print(f'[GET_SENHAS_PENDENTES] Retornando {len(senhas_json)} senhas em JSON')
        return jsonify(senhas_json)
        
    except Exception as e:
        print(f"[GET_SENHAS_PENDENTES] Erro ao buscar senhas pendentes: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/chamar_proxima', methods=['GET', 'POST'])
def chamar_proxima():
    auth_result = require_login()
    if auth_result:
        return auth_result
    global senha_atual
    end_banco_local = request.cookies.get('end_banco_local') or 'appsenhas.sqlite'
    if not end_banco_local or not os.path.exists(end_banco_local):
        return "Banco de dados local não encontrado."

    if flask_request.method == 'POST':
        operador_id = flask_request.form['operador_id']
        ensure_table_exists(end_banco_local)
        conn = sqlite3.connect(end_banco_local)
        conn.isolation_level = None  # Controle manual de transação
        cursor = conn.cursor()
        cursor.execute('SELECT setor_id FROM operadores WHERE id=?', (operador_id,))
        setor_row = cursor.fetchone()
        if not setor_row:
            conn.close()
            return make_response(jsonify({'success': False, 'error': 'Operador não encontrado'}), 400)
        setor_id = setor_row[0]

        lock = setor_locks[setor_id]
        with lock:
            try:
                cursor.execute('BEGIN IMMEDIATE')
                cursor.execute('SELECT id, senha_id FROM atendimento_atual WHERE setor_id=? AND operador_id=? ORDER BY id DESC LIMIT 1', (setor_id, operador_id))
                last_att = cursor.fetchone()
                if last_att:
                    last_att_id, last_senha_id = last_att
                    cursor.execute('INSERT INTO finalizados (senha_id, operador_id, setor_id, avaliacao) VALUES (?, ?, ?, ?)', (last_senha_id, operador_id, setor_id, ''))
                    cursor.execute('DELETE FROM atendimento_atual WHERE id=?', (last_att_id,))
                    cursor.execute("UPDATE senhas SET status = 'F' WHERE id = ?", (last_senha_id,))

                cursor.execute("SELECT id, senha, tipo, pedido, tem_pedido FROM senhas WHERE setor_id = ? AND status = 'A' ORDER BY id ASC", (setor_id,))
                todas = cursor.fetchall()
                normais = [s for s in todas if s[2] == 'normal']
                preferenciais = [s for s in todas if s[2] == 'preferencial']
                try:
                    proporcao_normais = int(request.cookies.get('proporcao_normais', PROPORCAO_NORMAIS))
                except Exception:
                    proporcao_normais = PROPORCAO_NORMAIS
                try:
                    limite_preferenciais_alerta = int(request.cookies.get('limite_preferenciais_alerta', LIMITE_PREFERENCIAIS_ALERTA))
                except Exception:
                    limite_preferenciais_alerta = LIMITE_PREFERENCIAIS_ALERTA
                normais_chamadas = int(request.cookies.get('normais_chamadas', '0'))
                alerta_preferenciais = False

                if len(preferenciais) > limite_preferenciais_alerta:
                    proxima = preferenciais[0] if preferenciais else (normais[0] if normais else None)
                    tipo_a_chamar = 'preferencial' if preferenciais else 'normal'
                    alerta_preferenciais = True
                    normais_chamadas = 0
                elif preferenciais and normais:
                    if normais_chamadas < proporcao_normais:
                        proxima = normais[0]
                        tipo_a_chamar = 'normal'
                        normais_chamadas += 1
                    else:
                        proxima = preferenciais[0]
                        tipo_a_chamar = 'preferencial'
                        normais_chamadas = 0
                elif preferenciais:
                    proxima = preferenciais[0]
                    tipo_a_chamar = 'preferencial'
                    normais_chamadas = 0
                elif normais:
                    proxima = normais[0]
                    tipo_a_chamar = 'normal'
                    normais_chamadas += 1
                else:
                    cursor.execute('COMMIT')
                    conn.close()
                    return make_response(jsonify({'success': False, 'error': 'Sem senhas pendentes'}), 200)

                senha_atual_local = proxima[1]
                senha_id = proxima[0]
                pedido = proxima[3]
                tem_pedido = proxima[4]

                cursor.execute("UPDATE senhas SET status = 'C' WHERE id = ?", (senha_id,))
                cursor.execute("INSERT INTO atendimento_atual (senha_id, setor_id, operador_id) VALUES (?, ?, ?)", (senha_id, setor_id, operador_id))
                cursor.execute('COMMIT')
            except Exception as e:
                cursor.execute('ROLLBACK')
                conn.close()
                return make_response(jsonify({'success': False, 'error': str(e)}), 500)
        conn.close()

        socketio.emit('nova_senha_para_avaliacao', {'setor_id': setor_id, 'senha_id': senha_id, 'operador_id': operador_id})
        socketio.emit('atualizar_atendimentos', {'setor_id': setor_id})
        socketio.emit('atualizar_lista_senhas', {'setor_id': setor_id})
        broadcast_posicao_fila(setor_id)
        broadcast_senha_chamada(senha_id)

        if tem_pedido and pedido:
            socketio.emit('senha_chamada_com_pedido', {
                'senha_id': senha_id,
                'senha': senha_atual_local,
                'pedido': pedido,
                'setor_id': setor_id
            })
            socketio.emit('senha_chamada_com_pedido', {
                'senha_id': senha_id,
                'senha': senha_atual_local,
                'pedido': pedido,
                'setor_id': setor_id
            }, room=f'setor_{setor_id}')

        resp = make_response(jsonify({'success': True, 'senha': senha_atual_local, 'tipo': tipo_a_chamar, 'alerta_preferenciais': alerta_preferenciais}))
        resp.set_cookie('operador_id', str(operador_id))
        resp.set_cookie('setor_id', str(setor_id))
        resp.set_cookie('last_tipo_chamado', tipo_a_chamar)
        resp.set_cookie('normais_chamadas', str(normais_chamadas))
        return resp
    return render_template('identificar_operador.html')

@app.route('/avaliacao_pendente')
def avaliacao_pendente():
    auth_result = require_login()
    if auth_result:
        return auth_result
    setor_id = request.cookies.get('setor_id')
    operador_id = request.cookies.get('operador_id')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT senha_id FROM atendimento_atual WHERE setor_id=? AND operador_id=? ORDER BY id DESC LIMIT 1', (setor_id, operador_id))
    row = cursor.fetchone()
    conn.close()
    if row:
        senha_id = row[0]
        return redirect(url_for('avaliacao', senha_id=senha_id, setor_id=setor_id, operador_id=operador_id, auto_finalize='1'))
    else:
        return redirect(url_for('setor_opcoes', setor_id=setor_id))

@app.route('/avaliacao', methods=['GET', 'POST'])
def avaliacao():
    auth_result = require_login()
    if auth_result:
        return auth_result
    setor_id = flask_request.args.get('setor_id') or flask_request.cookies.get('setor_id')
    operador_id = flask_request.args.get('operador_id') or flask_request.cookies.get('operador_id')
    print(f'[AVALIACAO] setor_id={setor_id}, operador_id={operador_id}')
    auto_finalize = flask_request.args.get('auto_finalize')
    avaliou = False
    senha_id = None
    senha_texto = None
    # Buscar a última senha finalizada, mas ainda não avaliada, para o operador
    operador_nome = None
    operador_foto = None
    if setor_id and operador_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar informações do operador
        cursor.execute('SELECT nome, foto_perfil FROM operadores WHERE id = ?', (operador_id,))
        operador_info = cursor.fetchone()
        if operador_info:
            operador_nome = operador_info[0]
            operador_foto = operador_info[1]
        
        cursor.execute('''
            SELECT f.senha_id, s.senha
            FROM finalizados f
            JOIN senhas s ON f.senha_id = s.id
            WHERE f.setor_id=? AND f.operador_id=? AND (f.avaliacao IS NULL OR f.avaliacao = '')
            ORDER BY f.id DESC LIMIT 1
        ''', (setor_id, operador_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            senha_id = row[0]
            senha_texto = row[1]
    if flask_request.method == 'POST':
        nota = flask_request.form['nota']
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Atualiza a avaliação na tabela finalizados
        cursor.execute('UPDATE finalizados SET avaliacao=? WHERE senha_id=? AND setor_id=? AND operador_id=? AND (avaliacao IS NULL OR avaliacao = \'\')', (nota, senha_id, setor_id, operador_id))
        cursor.execute('UPDATE senhas SET status = \'F\' WHERE id = ?', (senha_id,))
        conn.commit()
        conn.close()
        avaliou = True
        return render_template('avaliacao.html', saudacao=True)
    if auto_finalize == '1':
        return render_template('avaliacao.html', senha_id=senha_id, setor_id=setor_id, operador_id=operador_id, auto_finalize=True, senha_texto=senha_texto, operador_nome=operador_nome, operador_foto=operador_foto)
    # Sempre renderiza avaliacao.html, mesmo se não houver avaliação pendente
    return render_template('avaliacao.html', senha_id=senha_id, setor_id=setor_id, operador_id=operador_id, auto_finalize=False, senha_texto=senha_texto, operador_nome=operador_nome, operador_foto=operador_foto)

@app.route('/admin')
def admin():
    """Página administrativa principal"""
    auth_result = require_login()
    if auth_result:
        return auth_result
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar operadores com seus setores
        cursor.execute("""
            SELECT o.id, o.nome, s.nome as setor_nome, o.foto_perfil
            FROM operadores o
            LEFT JOIN setores s ON o.setor_id = s.id
            ORDER BY o.nome
        """)
        operadores = cursor.fetchall()
        
        # Buscar impressoras com seus setores
        cursor.execute("""
            SELECT i.id, i.nome, i.ip, i.porta, s.nome as setor_nome
            FROM impressoras i
            LEFT JOIN setores s ON i.setor_id = s.id
            ORDER BY i.nome
        """)
        impressoras = cursor.fetchall()
        
        # Buscar setores
        cursor.execute("SELECT * FROM setores ORDER BY nome")
        setores = cursor.fetchall()
        
        # Buscar configuração do ngrok
        ngrok_url = get_ngrok_url()
        
        # Buscar estatísticas para o dashboard
        cursor.execute("""
            SELECT s.nome, COUNT(*) as total
            FROM senhas sen
            JOIN setores s ON sen.setor_id = s.id
            WHERE sen.status = 'F' 
            AND DATE(sen.data_hora) = DATE('now')
            GROUP BY s.id, s.nome
        """)
        atendimentos_dia = cursor.fetchall()
        
        cursor.execute("""
            SELECT s.nome, COUNT(*) as total
            FROM senhas sen
            JOIN setores s ON sen.setor_id = s.id
            WHERE sen.status = 'F' 
            AND strftime('%Y-%m', sen.data_hora) = strftime('%Y-%m', 'now')
            GROUP BY s.id, s.nome
        """)
        atendimentos_mes = cursor.fetchall()
        
        # Buscar médias de avaliação por operador
        cursor.execute("""
            SELECT o.nome, AVG(f.avaliacao) as media, s.nome as setor
            FROM finalizados f
            JOIN operadores o ON f.operador_id = o.id
            LEFT JOIN setores s ON o.setor_id = s.id
            GROUP BY o.id, o.nome, s.nome
            ORDER BY media DESC
        """)
        medias_operadores = cursor.fetchall()
        
        # Melhor e pior operador
        melhor_operador = medias_operadores[0] if medias_operadores else None
        pior_operador = medias_operadores[-1] if medias_operadores else None
        
        # Médias por setor
        medias_por_setor = {}
        for setor in setores:
            cursor.execute("""
                SELECT o.nome, AVG(f.avaliacao) as media
                FROM finalizados f
                JOIN operadores o ON f.operador_id = o.id
                WHERE o.setor_id = ?
                GROUP BY o.id, o.nome
                ORDER BY media DESC
            """, (setor[0],))
            medias_por_setor[setor[0]] = cursor.fetchall()
        
        # Atendimentos do mês por operador por setor
        cursor.execute("""
            SELECT s.id, o.nome, COUNT(*) as total
            FROM senhas sen
            JOIN setores s ON sen.setor_id = s.id
            JOIN atendimento_atual aa ON sen.id = aa.senha_id
            JOIN operadores o ON aa.operador_id = o.id
            WHERE sen.status = 'F' 
            AND strftime('%Y-%m', sen.data_hora) = strftime('%Y-%m', 'now')
            GROUP BY s.id, o.id, o.nome
            ORDER BY s.id, total DESC
        """)
        atendimentos_mes_operador_por_setor = {}
        for row in cursor.fetchall():
            setor_id = row[0]
            if setor_id not in atendimentos_mes_operador_por_setor:
                atendimentos_mes_operador_por_setor[setor_id] = []
            atendimentos_mes_operador_por_setor[setor_id].append((row[1], row[2]))
        
        conn.close()
        
        return render_template('admin.html', 
                             operadores=operadores, 
                             impressoras=impressoras, 
                             setores=setores,
                             ngrok_url=ngrok_url,
                             atendimentos_dia=atendimentos_dia,
                             atendimentos_mes=atendimentos_mes,
                             medias_operadores=medias_operadores,
                             melhor_operador=melhor_operador,
                             pior_operador=pior_operador,
                             medias_por_setor=medias_por_setor,
                             atendimentos_mes_operador_por_setor=atendimentos_mes_operador_por_setor)
        
    except Exception as e:
        print(f"Erro no admin: {e}")
        return "Erro interno do servidor", 500

@app.route('/admin/operador/add', methods=['GET', 'POST'])
def add_operador():
    auth_result = require_login()
    if auth_result:
        return auth_result
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        setor_id = request.form['setor_id']
        
        # Processar upload de imagem
        foto_perfil = None
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file and file.filename != '' and allowed_file(file.filename):
                # Verificar tamanho do arquivo
                file.seek(0, 2)  # Ir para o final do arquivo
                file_size = file.tell()
                file.seek(0)  # Voltar para o início
                
                if file_size <= MAX_FILE_SIZE:
                    foto_perfil = process_image(file)
                else:
                    return "Arquivo muito grande. Tamanho máximo: 5MB", 400
            elif file and file.filename != '':
                return "Tipo de arquivo não permitido. Use: PNG, JPG, JPEG, GIF, WEBP", 400
        
        cursor.execute('INSERT INTO operadores (nome, setor_id, foto_perfil) VALUES (?, ?, ?)', 
                      (nome, setor_id, foto_perfil))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    cursor.execute('SELECT id, nome FROM setores')
    setores = cursor.fetchall()
    conn.close()
    return render_template('add_operador.html', setores=setores)

@app.route('/admin/operador/edit/<int:operador_id>', methods=['GET', 'POST'])
def edit_operador(operador_id):
    auth_result = require_login()
    if auth_result:
        return auth_result
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        nome = request.form['nome']
        setor_id = request.form['setor_id']
        
        # Buscar foto atual do operador
        cursor.execute('SELECT foto_perfil FROM operadores WHERE id=?', (operador_id,))
        result = cursor.fetchone()
        foto_atual = result[0] if result else None
        
        # Processar upload de nova imagem
        nova_foto = foto_atual
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file and file.filename != '' and allowed_file(file.filename):
                # Verificar tamanho do arquivo
                file.seek(0, 2)  # Ir para o final do arquivo
                file_size = file.tell()
                file.seek(0)  # Voltar para o início
                
                if file_size <= MAX_FILE_SIZE:
                    nova_foto = process_image(file)
                    # Deletar foto antiga se existir
                    if foto_atual:
                        delete_old_image(foto_atual)
                else:
                    return "Arquivo muito grande. Tamanho máximo: 5MB", 400
            elif file and file.filename != '':
                return "Tipo de arquivo não permitido. Use: PNG, JPG, JPEG, GIF, WEBP", 400
        
        # Verificar se o usuário quer remover a foto
        if 'remover_foto' in request.form and request.form['remover_foto'] == '1':
            if foto_atual:
                delete_old_image(foto_atual)
            nova_foto = None
        
        cursor.execute('UPDATE operadores SET nome=?, setor_id=?, foto_perfil=? WHERE id=?', 
                      (nome, setor_id, nova_foto, operador_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    
    # Buscar dados do operador
    cursor.execute('SELECT id, nome, setor_id, foto_perfil FROM operadores WHERE id=?', (operador_id,))
    operador = cursor.fetchone()
    if not operador:
        conn.close()
        return "Operador não encontrado.", 404
    
    # Buscar setores para o select
    cursor.execute('SELECT id, nome FROM setores')
    setores = cursor.fetchall()
    conn.close()
    
    return render_template('edit_operador.html', operador=operador, setores=setores)

@app.route('/admin/operador/delete/<int:operador_id>')
def delete_operador(operador_id):
    auth_result = require_login()
    if auth_result:
        return auth_result
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Buscar a foto do operador antes de deletar
    cursor.execute('SELECT foto_perfil FROM operadores WHERE id=?', (operador_id,))
    result = cursor.fetchone()
    if result and result[0]:
        delete_old_image(result[0])
    
    cursor.execute('DELETE FROM operadores WHERE id=?', (operador_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/impressora/add', methods=['GET', 'POST'])
def add_impressora():
    auth_result = require_login()
    if auth_result:
        return auth_result
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        ip = request.form['ip']
        porta = request.form['porta']
        setor_id = request.form['setor_id']
        
        cursor.execute('INSERT INTO impressoras (nome, ip, porta, setor_id) VALUES (?, ?, ?, ?)', (nome, ip, porta, setor_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    
    cursor.execute('SELECT id, nome FROM setores')
    setores = cursor.fetchall()
    conn.close()
    return render_template('add_impressora.html', setores=setores)

@app.route('/admin/impressora/delete/<int:impressora_id>')
def delete_impressora(impressora_id):
    auth_result = require_login()
    if auth_result:
        return auth_result
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM impressoras WHERE id=?', (impressora_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/setor/add', methods=['GET', 'POST'])
def add_setor():
    auth_result = require_login()
    if auth_result:
        return auth_result
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        senha_setor = request.form.get('senha_setor', '')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO setores (nome, descricao, senha_setor) VALUES (?, ?, ?)', (nome, descricao, senha_setor))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    return render_template('add_setor.html')

@app.route('/admin/setor/edit/<int:setor_id>', methods=['GET', 'POST'])
def edit_setor(setor_id):
    auth_result = require_login()
    if auth_result:
        return auth_result
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        senha_setor = request.form.get('senha_setor', '')
        
        cursor.execute('UPDATE setores SET nome=?, descricao=?, senha_setor=? WHERE id=?', (nome, descricao, senha_setor, setor_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    
    cursor.execute('SELECT id, nome, descricao, senha_setor FROM setores WHERE id=?', (setor_id,))
    setor = cursor.fetchone()
    conn.close()
    return render_template('edit_setor.html', setor=setor)

@app.route('/admin/setor/delete/<int:setor_id>')
def delete_setor(setor_id):
    auth_result = require_login()
    if auth_result:
        return auth_result
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM setores WHERE id=?', (setor_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/configuracao', methods=['GET', 'POST'])
def configuracao_empresa():
    auth_result = require_login()
    if auth_result:
        return auth_result
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        resp = make_response(redirect(url_for('admin')))
        resp.set_cookie('nome_empresa', nome_empresa, max_age=365*24*60*60)  # 1 ano
        return resp
    return render_template('configuracao_empresa.html')

@app.route('/notificacao/<token>')
def notificacao_page(token):
    """Página para registro de notificação push"""
    return render_template('notificacao.html', token=token, vapid_public_key=VAPID_PUBLIC_KEY)

@app.route('/api/registrar_token/<token>', methods=['POST'])
def registrar_token(token):
    """Registra token para notificações"""
    try:
        data = request.get_json()
        timestamp = data.get('timestamp')
        
        # Atualizar banco de dados
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE senhas 
            SET notificado = 1 
            WHERE token_unico = ?
        ''', (token,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Token não encontrado'}), 404
        
        conn.commit()
        conn.close()
        
        print(f"[NOTIFICACAO] Token registrado: {token}")
        return jsonify({'success': True, 'message': 'Token registrado'})
        
    except Exception as e:
        print(f"[ERRO] Erro ao registrar token: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/verificar_senha/<token>', methods=['GET'])
def verificar_senha(token):
    """Verifica o status da senha pelo token"""
    try:
        # Buscar a senha pelo token
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.senha, s.status, s.pedido, s.tem_pedido, s.pedido_confirmado, st.nome as setor_nome
            FROM senhas s
            LEFT JOIN setores st ON s.setor_id = st.id
            WHERE s.token_unico = ?
        """, (token,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            senha, status, pedido, tem_pedido, pedido_confirmado, setor_nome = row
            return jsonify({
                'senha': senha,
                'status': status,
                'chamada': status == 'C',
                'finalizado': status == 'F',
                'pedido': pedido,
                'tem_pedido': bool(tem_pedido) if tem_pedido is not None else False,
                'pedido_confirmado': bool(pedido_confirmado) if pedido_confirmado is not None else False,
                'setor': setor_nome or 'N/A'
            })
        else:
            return jsonify({'error': 'Token não encontrado'}), 404
            
    except Exception as e:
        print(f"Erro ao verificar senha: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/salvar_pedido/<token>', methods=['POST'])
def salvar_pedido(token):
    """Salva o pedido do cliente"""
    try:
        data = request.get_json()
        pedido = data.get('pedido', '').strip()
        if not pedido:
            return jsonify({'error': 'Pedido não pode estar vazio'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE senhas
            SET pedido = ?, tem_pedido = 1
            WHERE token_unico = ?
        ''', (pedido, token))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Token não encontrado'}), 404
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Pedido salvo com sucesso!'})
    except Exception as e:
        print(f"Erro ao salvar pedido: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/chamar_senha_novamente', methods=['POST'])
def chamar_senha_novamente():
    """Chama uma senha novamente"""
    try:
        data = request.get_json()
        senha = data.get('senha')
        operador_id = data.get('operador_id')
        
        if not senha or not operador_id:
            return jsonify({'error': 'Senha e operador_id são obrigatórios'}), 400
        
        # Buscar informações da senha
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.setor_id, s.token_unico
            FROM senhas s
            WHERE s.senha = ? AND s.status = 'C'
        ''', (senha,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'error': 'Senha não encontrada ou não está sendo atendida'}), 404
        
        senha_id, setor_id, token_unico = result
        
        # Imprimir a senha novamente
        try:
            imprimir_senha_com_ip(senha, setor_id)
            print(f"[IMPRESSAO] Senha '{senha}' impressa novamente")
        except Exception as e:
            print(f"[ERRO IMPRESSAO] Erro ao imprimir senha '{senha}' novamente: {e}")
        
        # Emitir eventos Socket.IO
        socketio.emit('senha_chamada_novamente', {
            'senha': senha,
            'operador_id': operador_id,
            'token': token_unico
        })
        
        conn.close()
        
        return jsonify({'success': True, 'message': f'Senha {senha} chamada novamente'})
        
    except Exception as e:
        print(f"[ERRO] Erro ao chamar senha novamente: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/registrar_push/<token>', methods=['POST'])
def registrar_push(token):
    """Registra a subscription de push notification"""
    try:
        data = request.get_json()
        subscription = data.get('subscription')
        
        if not subscription:
            return jsonify({'error': 'Subscription não fornecida'}), 400
        
        # Atualizar o banco com a subscription
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE senhas SET push_subscription = ? WHERE token_unico = ?", 
                      (str(subscription), token))
        conn.commit()
        conn.close()
        
        print(f"[NOTIFICACAO] Push subscription registrada para token: {token}")
        return jsonify({'success': True, 'message': 'Subscription registrada com sucesso'})
        
    except Exception as e:
        print(f"[ERRO] Erro ao registrar push subscription: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notificar/<int:senha_id>', methods=['POST'])
def notificar_senha(senha_id):
    """Envia notificação push para uma senha específica"""
    try:
        # Buscar a senha e subscription
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT senha, push_subscription FROM senhas WHERE id = ?", (senha_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'Senha não encontrada'}), 404
        
        senha, subscription = result
        
        if not subscription:
            return jsonify({'error': 'Nenhuma subscription encontrada para esta senha'}), 404
        
        # Enviar notificação push usando pywebpush
        try:
            from pywebpush import webpush
            
            # Preparar dados da notificação
            notification_data = {
                "title": f"Sua senha {senha} foi chamada!",
                "body": "Dirija-se ao atendimento.",
                "icon": "/static/icon-192x192.png",
                "tag": "senha-chamada",
                "requireInteraction": True
            }
            
            # Enviar notificação
            result = webpush(
                subscription_info=subscription,
                data=json.dumps(notification_data),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": VAPID_EMAIL,
                    "aud": "https://fcm.googleapis.com"
                }
            )
            
            print(f"[NOTIFICACAO] Notificação enviada com sucesso para senha {senha} (ID: {senha_id})")
            print(f"[NOTIFICACAO] Status: {result.status_code}")
            
        except ImportError:
            print(f"[ERRO] pywebpush não instalado. Instale com: pip install pywebpush")
        except Exception as e:
            print(f"[ERRO] Erro ao enviar notificação push: {e}")
        
        return jsonify({'success': True, 'message': f'Notificação enviada para senha {senha}'})
        
    except Exception as e:
        print(f"[ERRO] Erro ao enviar notificação: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@socketio.on('connect')
def handle_connect():
    print(f'[SOCKET] Cliente conectado: {request.sid}')

@socketio.on('join_setor')
def handle_join_setor(data):
    """Permite que operadores entrem na sala específica do setor"""
    setor_id = data.get('setor_id')
    if setor_id:
        room = f'setor_{setor_id}'
        join_room(room)
        print(f'[SOCKET] Operador entrou na sala do setor {setor_id}: {request.sid}')
        emit('joined_setor', {'setor_id': setor_id, 'room': room})

@socketio.on('solicitar_posicao')
def handle_solicitar_posicao(data):
    """Envia a posição na fila para um token específico"""
    try:
        token = data.get('token')
        if not token:
            return
        
        # Buscar posição na fila
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar a senha pelo token
        cursor.execute('''
            SELECT s.id, s.senha, s.status, s.setor_id, st.nome as setor_nome
            FROM senhas s
            LEFT JOIN setores st ON s.setor_id = st.id
            WHERE s.token_unico = ?
        ''', (token,))
        
        senha_result = cursor.fetchone()
        if not senha_result:
            conn.close()
            return
        
        senha_id, senha_numero, status, setor_id, setor_nome = senha_result
        
        # Se a senha já foi chamada, posição = 0
        if status == 'C':
            socketio.emit('posicao_fila', {'posicao': 0, 'token': token}, room=request.sid)
            conn.close()
            return
        
        # Contar quantas senhas estão na frente (status = 'A' e id menor)
        cursor.execute('''
            SELECT COUNT(*) 
            FROM senhas 
            WHERE setor_id = ? AND status = 'A' AND id < ?
        ''', (setor_id, senha_id))
        
        posicao = cursor.fetchone()[0]
        conn.close()
        
        print(f'[FILA] Token {token}: posição {posicao}')
        
        # Enviar posição para o cliente
        socketio.emit('posicao_fila', {
            'posicao': posicao,
            'token': token,
            'senha': senha_numero,
            'setor': setor_nome or 'Geral'
        }, room=request.sid)
        
        # Se estiver próximo (1-3 pessoas na frente), enviar alerta
        if 1 <= posicao <= 3:
            socketio.emit('senha_proxima', {
                'posicao': posicao,
                'token': token
            }, room=f'token_{token}')
            
    except Exception as e:
        print(f'[ERRO] Erro ao calcular posição: {e}')

def broadcast_posicao_fila(setor_id):
    """Atualiza a posição na fila para todos os clientes do setor"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar todas as senhas ativas do setor
        cursor.execute('''
            SELECT s.token_unico, s.id, s.senha, s.status
            FROM senhas s
            WHERE s.setor_id = ? AND s.status = 'A' AND s.token_unico IS NOT NULL
            ORDER BY s.id ASC
        ''', (setor_id,))
        
        senhas = cursor.fetchall()
        
        # Calcular posição para cada senha (quantas estão na frente)
        for token, senha_id, senha_numero, status in senhas:
            # Contar quantas senhas estão na frente desta (id menor)
            cursor.execute('''
                SELECT COUNT(*) 
                FROM senhas 
                WHERE setor_id = ? AND status = 'A' AND id < ?
            ''', (setor_id, senha_id))
            
            posicao = cursor.fetchone()[0]
            
            # Enviar posição para todos os clientes
            socketio.emit('posicao_fila', {
                'posicao': posicao,
                'token': token,
                'senha': senha_numero
            })
            
            # Se estiver próximo, enviar alerta APENAS para o cliente específico
            if 1 <= posicao <= 3:
                socketio.emit('senha_proxima', {
                    'posicao': posicao,
                    'token': token
                }, room=f'token_{token}')
        
        conn.close()
                
    except Exception as e:
        print(f'[ERRO] Erro ao broadcast posição: {e}')

def broadcast_senha_chamada(senha_id):
    """Notifica quando uma senha é chamada"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.token_unico, s.senha, st.nome as setor_nome, s.status, s.pedido, s.setor_id
            FROM senhas s
            LEFT JOIN setores st ON s.setor_id = st.id
            WHERE s.id = ?
        ''', (senha_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            token, senha_numero, setor_nome, status, pedido, setor_id = result
            
            # Só enviar notificação se a senha foi realmente chamada (status = 'C')
            if status == 'C':
                # Enviar notificação para todos os clientes
                socketio.emit('senha_chamada', {
                    'token': token,
                    'senha': senha_numero,
                    'setor': setor_nome or 'Geral'
                })
                
                # Se houver pedido, enviar evento específico com pedido para TODOS os clientes
                if pedido:
                    socketio.emit('senha_chamada_com_pedido', {
                        'token': token,
                        'senha': senha_numero,
                        'setor': setor_nome or 'Geral',
                        'pedido': pedido
                    })
                    
                    # Também enviar para a sala específica do setor (operadores)
                    if setor_id:
                        socketio.emit('senha_chamada_com_pedido', {
                            'token': token,
                            'senha': senha_numero,
                            'setor': setor_nome or 'Geral',
                            'pedido': pedido
                        }, room=f'setor_{setor_id}')
                
                print(f'[CHAMADA] Senha {senha_numero} chamada - token: {token}')
                if pedido:
                    print(f'[CHAMADA] Pedido: {pedido}')
            
    except Exception as e:
        print(f'[ERRO] Erro ao broadcast senha chamada: {e}')

@socketio.on('pedido_confirmado')
def handle_pedido_confirmado(data):
    """Handler para quando o operador confirma o pedido"""
    print(f'[SOCKET] pedido_confirmado recebido: {data}')
    
    senha = data.get('senha')
    pedido = data.get('pedido')
    mensagem = data.get('mensagem', 'Pedido sendo preparado')
    
    print(f'[SOCKET] Enviando notificação para senha {senha}')
    
    try:
        # Buscar o token da senha para enviar a notificação
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT token_unico FROM senhas 
            WHERE senha = ? AND status = 'C'
            ORDER BY id DESC LIMIT 1
        """, (senha,))
        
        row = cursor.fetchone()
        
        if row:
            token = row[0]
            print(f'[SOCKET] Token encontrado: {token}')
            
            # Atualizar o status pedido_confirmado para TRUE
            cursor.execute("""
                UPDATE senhas 
                SET pedido_confirmado = 1 
                WHERE senha = ? AND status = 'C'
            """, (senha,))
            conn.commit()
            print(f'[SOCKET] Status pedido_confirmado atualizado para TRUE')
            
            # Enviar notificação para o cliente específico
            socketio.emit('pedido_preparando', {
                'senha': senha,
                'pedido': pedido,
                'mensagem': mensagem,
                'timestamp': datetime.now().isoformat()
            }, room=token)
            
            print(f'[SOCKET] Notificação enviada para token {token}')
        else:
            print(f'[SOCKET] Token não encontrado para senha {senha}')
            
        conn.close()
    except Exception as e:
        print(f'[SOCKET] Erro ao enviar notificação: {e}')
        if conn:
            conn.close()

@socketio.on('join_token_room')
def handle_join_token_room(data):
    """Permite que o cliente entre na sala específica do seu token"""
    token = data.get('token')
    if token:
        room_name = f'token_{token}'
        join_room(room_name)
        print(f'[SOCKET] Cliente entrou na sala do token: {room_name}')
        emit('joined_token_room', {'token': token})
    else:
        print(f'[SOCKET] Token não fornecido para join_token_room')

def set_ngrok_url(url):
    """Define a URL do ngrok nas configurações"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE configuracoes 
            SET valor = ?, data_atualizacao = CURRENT_TIMESTAMP 
            WHERE chave = 'ngrok_url'
        """, (url,))
        conn.commit()
        conn.close()
        print(f"URL do ngrok atualizada: {url}")
        return True
    except Exception as e:
        print(f"Erro ao atualizar URL do ngrok: {e}")
        return False

def get_configuracao(chave):
    """Obtém uma configuração específica"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Erro ao obter configuração {chave}: {e}")
        return None

def set_configuracao(chave, valor, descricao=None):
    """Define uma configuração específica"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se a configuração já existe
        cursor.execute("SELECT id FROM configuracoes WHERE chave = ?", (chave,))
        if cursor.fetchone():
            # Atualizar configuração existente
            cursor.execute("""
                UPDATE configuracoes 
                SET valor = ?, data_atualizacao = CURRENT_TIMESTAMP 
                WHERE chave = ?
            """, (valor, chave))
        else:
            # Inserir nova configuração
            cursor.execute("""
                INSERT INTO configuracoes (chave, valor, descricao)
                VALUES (?, ?, ?)
            """, (chave, valor, descricao))
        
        conn.commit()
        conn.close()
        print(f"Configuração {chave} atualizada: {valor}")
        return True
    except Exception as e:
        print(f"Erro ao atualizar configuração {chave}: {e}")
        return False

@app.route('/admin/configuracao/ngrok', methods=['GET', 'POST'])
def configuracao_ngrok():
    """Página para configurar a URL do ngrok"""
    if request.method == 'POST':
        ngrok_url = request.form.get('ngrok_url', '').strip()
        if set_ngrok_url(ngrok_url):
            flash('URL do ngrok atualizada com sucesso!', 'success')
        else:
            flash('Erro ao atualizar URL do ngrok!', 'error')
        return redirect(url_for('configuracao_ngrok'))
    
    ngrok_url = get_ngrok_url()
    return render_template('configuracao_ngrok.html', ngrok_url=ngrok_url)

@app.route('/api/configuracao/ngrok', methods=['GET', 'POST'])
def api_configuracao_ngrok():
    """API para gerenciar configurações do ngrok"""
    if request.method == 'GET':
        ngrok_url = get_ngrok_url()
        return jsonify({'ngrok_url': ngrok_url})
    
    elif request.method == 'POST':
        data = request.get_json()
        ngrok_url = data.get('ngrok_url', '').strip()
        
        if set_ngrok_url(ngrok_url):
            return jsonify({'success': True, 'message': 'URL do ngrok atualizada com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Erro ao atualizar URL do ngrok!'}), 500

def generate_qr_code_with_ngrok(token):
    """Gera QR code com URL do ngrok se configurada"""
    notification_url = get_notification_url(token)
    
    # Gerar QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=2,
    )
    qr.add_data(notification_url)
    qr.make(fit=True)
    
    # Criar imagem
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converter para bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr.getvalue()

@app.route('/qr/<token>')
def qr_code(token):
    """Gera QR code para a senha"""
    try:
        # Verificar se a senha existe
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT senha FROM senhas WHERE token_unico = ?", (token,))
        senha = cursor.fetchone()
        conn.close()
        
        if not senha:
            return "Token não encontrado", 404
        
        # Gerar QR code com URL do ngrok se configurada
        qr_data = generate_qr_code_with_ngrok(token)
        
        response = make_response(qr_data)
        response.headers.set('Content-Type', 'image/png')
        return response
        
    except Exception as e:
        print(f"Erro ao gerar QR code: {e}")
        return "Erro interno", 500

if __name__ == '__main__':
    init_local_db()  # Inicializa o banco de dados local padrão
    
    print("[HTTP] Iniciando aplicativo...")
    print("[HTTP] Para usar SSL e notificações push:")
    print("[HTTP] 1. Execute: python setup_notifications.py")
    print("[HTTP] 2. Execute: python run_with_ssl.py")
    print("[HTTP] Acesse: http://<seu-ip-local>:5000")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
