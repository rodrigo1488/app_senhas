import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response, session, g, request as flask_request
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


load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env

# Configuração do Flask e SocketIO
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
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
def ADMIN():
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
    resp = make_response(redirect(url_for('ADMIN')))
    resp.set_cookie('end_impressora_local', impressora_ip)
    resp.set_cookie('end_banco_local', 'appsenhas.sqlite')  # Valor fixo
    resp.set_cookie('setor_id', str(setor_id))
    imprimir_senha_com_ip(codigo_senha, impressora_ip)
    return resp

def imprimir_senha_com_ip(senha, impressora_ip):
    print(f"[TESTE] Endereço da impressora usado: {impressora_ip}")
    return True

@app.route('/senhas_pendentes')
def senhas_pendentes():
    """Renderiza a página de senhas pendentes."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    setor_id = request.cookies.get('setor_id')
    if not setor_id:
        return "Setor não selecionado."
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, senha, tipo FROM senhas WHERE setor_id = ? AND status = 'A' ORDER BY tipo DESC, id ASC", (setor_id,))
    senhas = cursor.fetchall()
    cursor.execute("SELECT id, nome FROM operadores WHERE setor_id = ?", (setor_id,))
    operadores = cursor.fetchall()
    conn.close()
    return render_template('senhas_pendentes.html', senhas=senhas, operadores=operadores)

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
        return jsonify({'senha_atual': 'Setor não selecionado.'})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT senha FROM senhas WHERE setor_id = ? AND status = 'B' ORDER BY id DESC LIMIT 1", (setor_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({'senha_atual': row[0]})
    else:
        return jsonify({'senha_atual': 'Aguardando próxima senha...'})

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
        if last_att:
            last_att_id, last_senha_id = last_att
            cursor.execute("UPDATE senhas SET status = 'F' WHERE id = ?", (last_senha_id,))
            conn.commit()
        # Chamar próxima senha do setor do operador
        cursor.execute("SELECT id, senha FROM senhas WHERE setor_id = ? AND status = 'A' ORDER BY tipo DESC, id ASC LIMIT 1", (setor_id,))
        proxima_senha = cursor.fetchone()
        if proxima_senha:
            senha_atual = proxima_senha[1]
            cursor.execute("UPDATE senhas SET status = 'B' WHERE id = ?", (proxima_senha[0],))
            cursor.execute("INSERT INTO atendimento_atual (senha_id, setor_id, operador_id) VALUES (?, ?, ?)", (proxima_senha[0], setor_id, operador_id))
            conn.commit()
            conn.close()
            # Emitir evento para avaliação do cliente
            socketio.emit('nova_senha_para_avaliacao', {'setor_id': setor_id, 'senha_id': proxima_senha[0], 'operador_id': operador_id})
            resp = make_response(redirect(url_for('senhas_pendentes')))
            resp.set_cookie('operador_id', str(operador_id))
            resp.set_cookie('setor_id', str(setor_id))
            return resp
        else:
            conn.close()
            # Apenas retorna para a tela de senhas pendentes, sem mensagem
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
    senha_id = flask_request.args.get('senha_id')
    setor_id = flask_request.args.get('setor_id') or flask_request.cookies.get('setor_id')
    operador_id = flask_request.args.get('operador_id') or flask_request.cookies.get('operador_id')
    auto_finalize = flask_request.args.get('auto_finalize')
    avaliou = False
    # Buscar senha em atendimento se não vier por GET
    if not senha_id and setor_id and operador_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT senha_id FROM atendimento_atual WHERE setor_id=? AND operador_id=? ORDER BY id DESC LIMIT 1', (setor_id, operador_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            senha_id = row[0]
    if flask_request.method == 'POST':
        nota = flask_request.form['nota']
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM atendimento_atual WHERE senha_id=? AND setor_id=? AND operador_id=?', (senha_id, setor_id, operador_id))
        atendimento = cursor.fetchone()
        if atendimento:
            cursor.execute('INSERT INTO finalizados (senha_id, operador_id, setor_id, avaliacao) VALUES (?, ?, ?, ?)', (senha_id, operador_id, setor_id, nota))
            cursor.execute('DELETE FROM atendimento_atual WHERE id=?', (atendimento[0],))
            cursor.execute("UPDATE senhas SET status = 'F' WHERE id = ?", (senha_id,))
            conn.commit()
        conn.close()
        avaliou = True
        return render_template('avaliacao.html', saudacao=True)
    if auto_finalize == '1':
        return render_template('avaliacao.html', senha_id=senha_id, setor_id=setor_id, operador_id=operador_id, auto_finalize=True)
    return render_template('avaliacao.html', senha_id=senha_id, setor_id=setor_id, operador_id=operador_id, auto_finalize=False)

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT o.id, o.nome, s.nome FROM operadores o JOIN SETORES s ON o.setor_id = s.id')
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
    melhor_operador = cursor.fetchone()
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
    pior_operador = cursor.fetchone()
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
        cursor.execute('INSERT INTO operadores (nome, setor_id) VALUES (?, ?)', (nome, setor_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_panel'))
    cursor.execute('SELECT id, nome FROM SETORES')
    setores = cursor.fetchall()
    conn.close()
    return render_template('add_operador.html', setores=setores)

@app.route('/admin/operador/delete/<int:operador_id>')
def delete_operador(operador_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
