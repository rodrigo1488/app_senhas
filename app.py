import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response, session, g, request as flask_request, send_from_directory
from flask_socketio import SocketIO, emit
import supabase
import sqlite3
import random
from escpos.printer import Network
import socket  # Corrigido: Importação do módulo socket
import os
from dotenv import load_dotenv
import threading
from datetime import timedelta
import time
import datetime
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
import io


load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env

# Configuração do Flask e SocketIO
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)

# Configurações para upload de imagens
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Criar pasta de uploads se não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
socketio = SocketIO(app)


IMPRESSORA_PORTA = 9100
# Recupera os valores
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supa_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

# Caminho do banco de dados local padrão
DB_PATH = "appsenhas.sqlite"

# Variável global para armazenar a senha atual
senha_atual = None

# Configuração de proporção e alerta
PROPORCAO_NORMAIS = 2  # Quantas normais para cada preferencial
LIMITE_PREFERENCIAIS_ALERTA = 3  # Se houver mais que isso, prioriza preferencial e alerta

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
            FOREIGN KEY (setor_id) REFERENCES SETORES (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS SETORES (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            senha_setor TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operadores(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            setor_id INTEGER NOT NULL,
            foto_perfil TEXT,
            FOREIGN KEY (setor_id) REFERENCES SETORES (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finalizados(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            senha_id INTEGER,
            operador_id INTEGER,
            setor_id INTEGER,
            avaliacao TEXT,
            data_finalizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (senha_id) REFERENCES senhas (id),
            FOREIGN KEY (operador_id) REFERENCES operadores (id),
            FOREIGN KEY (setor_id) REFERENCES SETORES (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS impressoras(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            ip TEXT NOT NULL,
            porta INTEGER NOT NULL,
            setor_id INTEGER,
            FOREIGN KEY (setor_id) REFERENCES SETORES (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atendimento_atual(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            senha_id INTEGER,
            setor_id INTEGER,
            operador_id INTEGER,
            status TEXT DEFAULT 'A',
            FOREIGN KEY (senha_id) REFERENCES senhas (id),
            FOREIGN KEY (setor_id) REFERENCES SETORES (id),
            FOREIGN KEY (operador_id) REFERENCES operadores (id)
        )
    ''')
    conn.commit()
    conn.close()

def ensure_table_exists(db_path):
    """Garante que a tabela `senhas` exista no banco de dados especificado."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS senhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

end_banco_local = "appsenhas.sqlite"  # Caminho do banco de dados local


@app.route('/check_helth', methods=['GET'])
def check_helth():
    return jsonify({'status': 'ok'})

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
        p.text("TESTE DE CONECTIVIDADE\n")
        p.text("=" * 20 + "\n")  # Linha separadora
        
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
        return redirect(url_for('senhas'))
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
                resp = make_response(redirect(url_for('selecionar_setor')))
                # Armazena o caminho do banco local
    
                # Armazena o endereço IP da impressora
                resp.set_cookie('user_id', str(user['id']),max_age=60*60*24*30)
                return resp
            else:
                return "Senha incorreta."
        else:
            return "Usuário não encontrado."
    
    return render_template('login.html')

def require_login():
    if 'user_id' not in session:
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Redireciona para a seleção de setores
    return redirect(url_for('selecionar_setor'))

@app.route('/senhas', methods=['GET', 'POST'])
def render_senhas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('senhas.html')

@app.route('/setores', methods=['GET', 'POST'])
def selecionar_setor():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, descricao FROM SETORES')
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
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

    # Conectar ao banco e armazenar a senha, incluindo setor_id
    conn = sqlite3.connect(end_banco_local)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO senhas (senha, tipo, setor_id) VALUES (?, ?, ?)", (codigo_senha, tipo, setor_id))
    conn.commit()
    conn.close()

    # Enviar para impressão
    resp = make_response(redirect(url_for('render_senhas')))
    resp.set_cookie('end_impressora_local', impressora_ip)
    resp.set_cookie('end_banco_local', 'appsenhas.sqlite')  # Valor fixo
    resp.set_cookie('setor_id', str(setor_id))
    imprimir_senha_com_ip(codigo_senha, impressora_ip)
    # Emitir evento para atualizar lista de senhas pendentes
    socketio.emit('atualizar_lista_senhas', {'setor_id': setor_id})
    return resp

def imprimir_senha_com_ip(senha, impressora_ip):
    """Envia a senha para a impressora térmica usando ESC/POS"""
    p = None
    try:
        print(f"[IMPRESSAO] Tentando imprimir senha '{senha}' na impressora {impressora_ip}")
        
        # Conecta à impressora térmica
        p = Network(impressora_ip, IMPRESSORA_PORTA)
        
        # Configurações da impressão
        p.set(align='center')  # Alinha no centro
        p.text('\x1B\x21\x30')  # Define o tamanho máximo de fonte
        
        # Conteúdo da senha com melhor espaçamento
        p.text("\n")  # Espaço inicial
        p.text("=" * 32 + "\n")  # Linha separadora superior
        p.text("\n")  # Espaço após separadora
        p.text("SENHA\n")
        p.text("\n")  # Espaço entre "SENHA" e o número
        p.text(f"{senha}\n")
        p.text("\n")  # Espaço após o número
        p.text("=" * 32 + "\n")  # Linha separadora
        
        # Data e hora com fonte menor
        p.text('\x1B\x21\x00')  # Define fonte menor para data/hora
        p.text(f"Data: {datetime.datetime.now().strftime('%d/%m/%Y')}\n")
        p.text(f"Hora: {datetime.datetime.now().strftime('%H:%M')}\n")
        p.text("=" * 32 + "\n")  # Linha separadora
        
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
    cursor.execute("SELECT id, senha FROM senhas ORDER BY tipo DESC, id ASC LIMIT 1")
    proxima_senha = cursor.fetchone()

    if proxima_senha:
        senha_atual = proxima_senha[1]  # Atualiza a variável global
        cursor.execute("UPDATE senhas SET status = 'B' WHERE id = ?", (proxima_senha[0],)) # Alterar status para 'B'
        conn.commit()

        cursor.execute("SELECT id, senha, tipo FROM senhas ORDER BY tipo DESC, id ASC")
        senhas_pendentes = cursor.fetchall()
        conn.close()

        emit('atualizar_lista', {'senha_atual': senha_atual, 'senhas': senhas_pendentes}, broadcast=True)
    else:
        senha_atual = None
        emit('erro', {'mensagem': 'Nenhuma senha disponível.'})
        conn.close()

@app.route('/senha_atual')
def senha_atual_view():
    """Renderiza a página para exibir a senha atual."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('senha_atual.html')

@app.route('/get_senha_atual')
def get_senha_atual():
    """Endpoint para retornar a senha atual em formato JSON."""
    global senha_atual
    return jsonify({'senha_atual': senha_atual if senha_atual else 'Aguardando próxima senha...'})

@app.route('/get_senha_atual_setor')
def get_senha_atual_setor():
    setor_id = flask_request.cookies.get('setor_id')
    if not setor_id:
        return jsonify({'senha_atual': 'Setor não selecionado.', 'operador': ''})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Busca a senha atual (status B) e o operador que está atendendo
    cursor.execute("""
        SELECT s.senha, o.nome, o.foto_perfil
        FROM senhas s
        JOIN atendimento_atual a ON a.senha_id = s.id
        JOIN operadores o ON a.operador_id = o.id
        WHERE s.setor_id = ? AND s.status = 'B'
        ORDER BY s.id DESC LIMIT 1
    """, (setor_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({'senha_atual': row[0], 'operador': row[1], 'foto_operador': row[2]})
    else:
        return jsonify({'senha_atual': 'Aguardando próxima senha...', 'operador': '', 'foto_operador': None})

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
    setor_id = flask_request.cookies.get('setor_id')
    if not setor_id:
        return jsonify([])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, senha, tipo FROM senhas WHERE setor_id = ? AND status = 'A' ORDER BY tipo DESC, id ASC", (setor_id,))
    senhas = cursor.fetchall()
    conn.close()
    return jsonify([
        {'id': s[0], 'senha': s[1], 'tipo': s[2]} for s in senhas
    ])

@app.route('/chamar_proxima', methods=['GET', 'POST'])
def chamar_proxima():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    global senha_atual
    end_banco_local = request.cookies.get('end_banco_local') or 'appsenhas.sqlite'
    if not end_banco_local or not os.path.exists(end_banco_local):
        return "Banco de dados local não encontrado."

    if flask_request.method == 'POST':
        operador_id = flask_request.form['operador_id']
        ensure_table_exists(end_banco_local)
        conn = sqlite3.connect(end_banco_local)
        cursor = conn.cursor()
        # Buscar setor do operador
        cursor.execute('SELECT setor_id FROM operadores WHERE id=?', (operador_id,))
        setor_row = cursor.fetchone()
        if not setor_row:
            conn.close()
            return "Operador não encontrado."
        setor_id = setor_row[0]
        # Finalizar última senha em atendimento deste operador/setor (apenas status)
        cursor.execute('SELECT id, senha_id FROM atendimento_atual WHERE setor_id=? AND operador_id=? ORDER BY id DESC LIMIT 1', (setor_id, operador_id))
        last_att = cursor.fetchone()
        senha_id_para_avaliar = None
        if last_att:
            last_att_id, last_senha_id = last_att
            # Finaliza o atendimento: move para finalizados com avaliacao pendente
            cursor.execute('INSERT INTO finalizados (senha_id, operador_id, setor_id, avaliacao) VALUES (?, ?, ?, ?)', (last_senha_id, operador_id, setor_id, ''))
            cursor.execute('DELETE FROM atendimento_atual WHERE id=?', (last_att_id,))
            cursor.execute("UPDATE senhas SET status = 'F' WHERE id = ?", (last_senha_id,))
            conn.commit()
            senha_id_para_avaliar = last_senha_id
        # Buscar todas as senhas pendentes ordenadas por data (mais antiga primeiro)
        cursor.execute("SELECT id, senha, tipo FROM senhas WHERE setor_id = ? AND status = 'A' ORDER BY id ASC", (setor_id,))
        todas = cursor.fetchall()
        # Separar por tipo
        normais = [s for s in todas if s[2] == 'normal']
        preferenciais = [s for s in todas if s[2] == 'preferencial']
        # Ler proporção e limite dos cookies se existirem
        try:
            proporcao_normais = int(request.cookies.get('proporcao_normais', PROPORCAO_NORMAIS))
        except Exception:
            proporcao_normais = PROPORCAO_NORMAIS
        try:
            limite_preferenciais_alerta = int(request.cookies.get('limite_preferenciais_alerta', LIMITE_PREFERENCIAIS_ALERTA))
        except Exception:
            limite_preferenciais_alerta = LIMITE_PREFERENCIAIS_ALERTA
        # Contador de normais desde a última preferencial (cookie)
        normais_chamadas = int(request.cookies.get('normais_chamadas', '0'))
        alerta_preferenciais = False
        # Alerta: se houver muitas preferenciais acumuladas, prioriza preferencial
        if len(preferenciais) > limite_preferenciais_alerta:
            proxima = preferenciais[0] if preferenciais else (normais[0] if normais else None)
            tipo_a_chamar = 'preferencial' if preferenciais else 'normal'
            alerta_preferenciais = True
            normais_chamadas = 0  # Reinicia o contador
        elif preferenciais and normais:
            # Alternância por proporção
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
            conn.close()
            return redirect(url_for('senhas_pendentes'))
        if proxima:
            senha_atual = proxima[1]
            cursor.execute("UPDATE senhas SET status = 'B' WHERE id = ?", (proxima[0],))
            cursor.execute("INSERT INTO atendimento_atual (senha_id, setor_id, operador_id) VALUES (?, ?, ?)", (proxima[0], setor_id, operador_id))
            conn.commit()
            conn.close()
            # Emitir evento para avaliação do cliente
            socketio.emit('nova_senha_para_avaliacao', {'setor_id': setor_id, 'senha_id': proxima[0], 'operador_id': operador_id})
            # Emitir evento para atualizar cards de atendimento
            socketio.emit('atualizar_atendimentos', {'setor_id': setor_id})
            # Emitir evento para atualizar lista de senhas pendentes
            socketio.emit('atualizar_lista_senhas', {'setor_id': setor_id})
            # Emitir alerta se necessário
            if alerta_preferenciais:
                socketio.emit('alerta_preferenciais', {'setor_id': setor_id, 'qtd': len(preferenciais)})
            resp = make_response(redirect(url_for('senhas_pendentes')))
            resp.set_cookie('operador_id', str(operador_id))
            resp.set_cookie('setor_id', str(setor_id))
            resp.set_cookie('last_tipo_chamado', tipo_a_chamar)
            resp.set_cookie('normais_chamadas', str(normais_chamadas))
            return resp
        else:
            conn.close()
            return redirect(url_for('senhas_pendentes'))
    return render_template('identificar_operador.html')

@app.route('/avaliacao_pendente')
def avaliacao_pendente():
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
def admin_panel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT o.id, o.nome, s.nome, o.foto_perfil FROM operadores o JOIN SETORES s ON o.setor_id = s.id')
    operadores = cursor.fetchall()
    cursor.execute('SELECT i.id, i.nome, i.ip, i.porta, s.nome FROM impressoras i LEFT JOIN SETORES s ON i.setor_id = s.id')
    impressoras = cursor.fetchall()
    cursor.execute('SELECT id, nome FROM SETORES')
    setores = cursor.fetchall()
    # Dashboard: total de atendimentos finalizados do dia por setor
    hoje = datetime.date.today().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT s.nome, COUNT(f.id) FROM finalizados f
        JOIN SETORES s ON f.setor_id = s.id
        WHERE DATE(f.data_finalizacao) = ?
        GROUP BY s.id
    ''', (hoje,))
    atendimentos_dia = cursor.fetchall()
    # Dashboard: total de atendimentos do mês por setor
    mes_atual = datetime.date.today().strftime('%Y-%m')
    cursor.execute('''
        SELECT s.nome, COUNT(f.id) FROM finalizados f
        JOIN SETORES s ON f.setor_id = s.id
        WHERE strftime('%Y-%m', f.data_finalizacao) = ?
        GROUP BY s.id
    ''', (mes_atual,))
    atendimentos_mes = cursor.fetchall()
    # Dashboard: operador com maior média de avaliação
    cursor.execute('''
        SELECT o.nome, AVG(CASE WHEN f.avaliacao IS NULL OR f.avaliacao = '' THEN NULL ELSE CAST(f.avaliacao AS FLOAT) END) as media
        FROM operadores o
        LEFT JOIN finalizados f ON f.operador_id = o.id
        GROUP BY o.id
        HAVING COUNT(f.id) > 0
        ORDER BY media DESC
        LIMIT 1
    ''')
    melhor_operador = validar_operador_avaliacao(cursor.fetchone())
    # Dashboard: operador com menor média de avaliação
    cursor.execute('''
        SELECT o.nome, AVG(CASE WHEN f.avaliacao IS NULL OR f.avaliacao = '' THEN NULL ELSE CAST(f.avaliacao AS FLOAT) END) as media, s.nome
        FROM operadores o
        JOIN SETORES s ON o.setor_id = s.id
        LEFT JOIN finalizados f ON f.operador_id = o.id
        GROUP BY o.id
        HAVING COUNT(f.id) > 0
        ORDER BY media ASC
        LIMIT 1
    ''')
    pior_operador = validar_operador_avaliacao(cursor.fetchone())
    # Dicionário: setor_id -> lista de (nome_operador, media)
    medias_por_setor = {}
    for setor in setores:
        setor_id = setor[0]
        cursor.execute('''
            SELECT o.nome, AVG(CASE WHEN f.avaliacao IS NULL OR f.avaliacao = '' THEN NULL ELSE CAST(f.avaliacao AS FLOAT) END) as media
            FROM operadores o
            LEFT JOIN finalizados f ON f.operador_id = o.id AND f.setor_id = ?
            WHERE o.setor_id = ?
            GROUP BY o.id
        ''', (setor_id, setor_id))
        medias = cursor.fetchall()
        medias_por_setor[setor_id] = medias
    # Dashboard: atendimentos do mês por operador em cada setor
    atendimentos_mes_operador_por_setor = {}
    for setor in setores:
        setor_id = setor[0]
        cursor.execute('''
            SELECT o.nome, COUNT(f.id) as total
            FROM operadores o
            LEFT JOIN finalizados f ON f.operador_id = o.id AND f.setor_id = ? AND strftime('%Y-%m', f.data_finalizacao) = ?
            WHERE o.setor_id = ?
            GROUP BY o.id
        ''', (setor_id, mes_atual, setor_id))
        atendimentos = cursor.fetchall()
        atendimentos_mes_operador_por_setor[setor_id] = atendimentos
    conn.close()
    return render_template('admin.html', operadores=operadores, impressoras=impressoras, medias_por_setor=medias_por_setor, setores=setores, atendimentos_dia=atendimentos_dia, atendimentos_mes=atendimentos_mes, melhor_operador=melhor_operador, pior_operador=pior_operador, atendimentos_mes_operador_por_setor=atendimentos_mes_operador_por_setor)

@app.route('/admin/operador/add', methods=['GET', 'POST'])
def add_operador():
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
        return redirect(url_for('admin_panel'))
    cursor.execute('SELECT id, nome FROM SETORES')
    setores = cursor.fetchall()
    conn.close()
    return render_template('add_operador.html', setores=setores)

@app.route('/admin/operador/edit/<int:operador_id>', methods=['GET', 'POST'])
def edit_operador(operador_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
        return redirect(url_for('admin_panel'))
    
    # Buscar dados do operador
    cursor.execute('SELECT id, nome, setor_id, foto_perfil FROM operadores WHERE id=?', (operador_id,))
    operador = cursor.fetchone()
    if not operador:
        conn.close()
        return "Operador não encontrado.", 404
    
    # Buscar setores para o select
    cursor.execute('SELECT id, nome FROM SETORES')
    setores = cursor.fetchall()
    conn.close()
    
    return render_template('edit_operador.html', operador=operador, setores=setores)

@app.route('/admin/operador/delete/<int:operador_id>')
def delete_operador(operador_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
    return redirect(url_for('admin_panel'))

@app.route('/admin/impressora/add', methods=['GET', 'POST'])
def add_impressora():
    if 'user_id' not in session:
        return redirect(url_for('login'))
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
        return redirect(url_for('admin_panel'))
    cursor.execute('SELECT id, nome FROM SETORES')
    setores = cursor.fetchall()
    conn.close()
    return render_template('add_impressora.html', setores=setores)

@app.route('/admin/impressora/delete/<int:impressora_id>')
def delete_impressora(impressora_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM impressoras WHERE id=?', (impressora_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/setor/add', methods=['GET', 'POST'])
def add_setor():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        senha_setor = request.form['senha_setor']
        cursor.execute('INSERT INTO SETORES (nome, descricao, senha_setor) VALUES (?, ?, ?)', (nome, descricao, senha_setor))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_panel'))
    conn.close()
    return render_template('add_setor.html')

@app.route('/admin/setor/edit/<int:setor_id>', methods=['GET', 'POST'])
def edit_setor(setor_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        senha_setor = request.form['senha_setor']
        cursor.execute('UPDATE SETORES SET nome=?, descricao=?, senha_setor=? WHERE id=?', (nome, descricao, senha_setor, setor_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_panel'))
    cursor.execute('SELECT id, nome, descricao, senha_setor FROM SETORES WHERE id=?', (setor_id,))
    setor = cursor.fetchone()
    conn.close()
    return render_template('edit_setor.html', setor=setor)

@app.route('/admin/setor/delete/<int:setor_id>')
def delete_setor(setor_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM SETORES WHERE id=?', (setor_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@socketio.on('connect')
def handle_connect():
    print(f'[SOCKETIO] Cliente conectado: {flask_request.sid}')

if __name__ == '__main__':
    init_local_db()  # Inicializa o banco de dados local padrão
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
