import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
from flask_socketio import SocketIO, emit
import supabase
import sqlite3
import random
from escpos.printer import Network
import socket  # Corrigido: Importação do módulo socket
import os
import threading
from datetime import timedelta

# Configuração do Flask e SocketIO
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
socketio = SocketIO(app)


IMPRESSORA_PORTA = 9100

# Configuração do Supabase
SUPABASE_URL = "https://kgpsbltrllknuwtrfzee.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtncHNibHRybGxrbnV3dHJmemVlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzg4ODc2MzcsImV4cCI6MjA1NDQ2MzYzN30.qsL24AlQVVKHN9SG6dq78tppyHtvHqipw9kPm9ecTPg"
supa_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

# Caminho do banco de dados local padrão
DB_PATH = "local_db.sqlite"

# Variável global para armazenar a senha atual
senha_atual = None

def init_local_db():
    """Inicializa o banco de dados local padrão se não existir."""
    conn = sqlite3.connect(DB_PATH)
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login para autenticação."""
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        # Consulta na tabela `users` do Supabase
        response = supa_client.from_('users').select('*').eq('email', email).single().execute()
        
        if response.data:
            user = response.data
            if user['senha'] == senha:  # Verificação simples de senha
                end_banco_local = user['end_banco_local']
                end_impressora_local = user['end_impressora_local']  # Novo: IP da impressora vindo do banco
                ensure_table_exists(end_banco_local)  # Garante que a tabela `senhas` existe
                resp = make_response(redirect(url_for('home')))
                # Armazena o caminho do banco local
                resp.set_cookie('end_banco_local', end_banco_local, max_age=60*60*24)  # Cookie válido por 1 dia
                # Armazena o endereço IP da impressora
                resp.set_cookie('end_impressora_local', end_impressora_local, max_age=60*60*24)
                return resp
            else:
                return "Senha incorreta."
        else:
            return "Usuário não encontrado."
    
    return render_template('login.html')

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
    """Tela inicial com dois botões para escolher a senha."""
    return render_template('home.html')

def imprimir_senha(senha):
    """Envia a senha para a impressora térmica usando ESC/POS"""
    try:
        # Recupera o IP da impressora do cookie
        impressora_ip = request.cookies.get('end_impressora_local')
        if not impressora_ip:
            # Caso não haja o cookie, utilize um valor padrão (opcional)
            impressora_ip = "192.168.2.69"
        
        # A porta permanece padrão (9100)
        p = Network(impressora_ip, IMPRESSORA_PORTA)
        p.set(align='center')  # Alinha no centro
        p.text('\x1B\x21\x30')  # Define o tamanho máximo de fonte (o maior possível para sua impressora)
        p.text(f"Senha: {senha}\n")  # Escreve o texto
        p.cut()  # Corta o papel
        print(f"Senha '{senha}' enviada para a impressora em {impressora_ip}")
    except Exception as e:
        print(f"Erro ao imprimir: {e}")

@app.route('/retirar_senha/<tipo>')
def retirar_senha(tipo):
    """Gera uma senha, armazena no banco local e imprime automaticamente."""
    end_banco_local = request.cookies.get('end_banco_local')

    if not end_banco_local:
        return redirect(url_for('login'))
    
    codigo_senha = f"{tipo[:1].upper()}{random.randint(1000, 9999)}"

    # Conectar ao banco e armazenar a senha
    conn = sqlite3.connect(end_banco_local)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO senhas (senha, tipo) VALUES (?, ?)", (codigo_senha, tipo))
    conn.commit()
    conn.close()
    
    # Enviar para impressão
    imprimir_senha(codigo_senha)
    
    return redirect(url_for('home'))

@app.route('/senhas_pendentes')
def senhas_pendentes():
    """Renderiza a página de senhas pendentes."""
    return render_template('senhas_pendentes.html')

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
        cursor.execute("DELETE FROM senhas WHERE id = ?", (proxima_senha[0],))
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
    return render_template('senha_atual.html')

@app.route('/get_senha_atual')
def get_senha_atual():
    """Endpoint para retornar a senha atual em formato JSON."""
    global senha_atual
    return jsonify({'senha_atual': senha_atual if senha_atual else 'Aguardando próxima senha...'})

@app.route('/chamar_proxima')
def chamar_proxima():
    """Chama a próxima senha da fila."""
    global senha_atual
    end_banco_local = request.cookies.get('end_banco_local')
    if not end_banco_local or not os.path.exists(end_banco_local):
        return "Banco de dados local não encontrado."

    ensure_table_exists(end_banco_local)

    conn = sqlite3.connect(end_banco_local)
    cursor = conn.cursor()
    cursor.execute("SELECT id, senha FROM senhas ORDER BY tipo DESC, id ASC LIMIT 1")
    proxima_senha = cursor.fetchone()
    
    if proxima_senha:
        senha_atual = proxima_senha[1]
        cursor.execute("DELETE FROM senhas WHERE id = ?", (proxima_senha[0],))
        conn.commit()
        conn.close()

        socketio.emit('nova_senha', {'senha_atual': senha_atual})
        return "Senha chamada com sucesso."
    else:
        conn.close()
        return "Nenhuma senha disponível."

if __name__ == '__main__':
    init_local_db()  # Inicializa o banco de dados local padrão
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
