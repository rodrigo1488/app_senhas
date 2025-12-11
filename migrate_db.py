import sqlite3
import os

def migrate_database():
    """Migra o banco de dados para adicionar o campo tem_pedido"""
    db_path = "appsenhas.sqlite"
    if not os.path.exists(db_path):
        print(f"Banco de dados {db_path} não encontrado!")
        return
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a tabela senhas existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='senhas'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(senhas)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'tem_pedido' not in columns:
                print("Adicionando coluna 'tem_pedido' à tabela senhas...")
                cursor.execute("ALTER TABLE senhas ADD COLUMN tem_pedido BOOLEAN DEFAULT 0")
                conn.commit()
                print("✅ Coluna 'tem_pedido' adicionada com sucesso!")
            else:
                print("✅ Coluna 'tem_pedido' já existe na tabela senhas.")
            
            if 'pedido_confirmado' not in columns:
                print("Adicionando coluna 'pedido_confirmado' à tabela senhas...")
                cursor.execute("ALTER TABLE senhas ADD COLUMN pedido_confirmado BOOLEAN DEFAULT 0")
                conn.commit()
                print("✅ Coluna 'pedido_confirmado' adicionada com sucesso!")
            else:
                print("✅ Coluna 'pedido_confirmado' já existe na tabela senhas.")
            
            # Atualizar registros existentes que têm pedido
            print("Atualizando registros existentes com pedidos...")
            cursor.execute("""
                UPDATE senhas 
                SET tem_pedido = 1 
                WHERE pedido IS NOT NULL AND pedido != '' AND tem_pedido = 0
            """)
            updated_count = cursor.rowcount
            conn.commit()
            print(f"✅ {updated_count} registros atualizados com tem_pedido = 1")
            
            if 'pedido' not in columns:
                print("Adicionando coluna 'pedido' à tabela senhas...")
                cursor.execute("ALTER TABLE senhas ADD COLUMN pedido TEXT")
                conn.commit()
                print("✅ Coluna 'pedido' adicionada com sucesso!")
            else:
                print("✅ Coluna 'pedido' já existe na tabela senhas.")
            
            # Verificar outras colunas necessárias
            if 'token_unico' not in columns:
                print("Adicionando coluna 'token_unico' à tabela senhas...")
                cursor.execute("ALTER TABLE senhas ADD COLUMN token_unico TEXT")
                conn.commit()
                print("✅ Coluna 'token_unico' adicionada com sucesso!")
            else:
                print("✅ Coluna 'token_unico' já existe na tabela senhas.")
            
            if 'notificado' not in columns:
                print("Adicionando coluna 'notificado' à tabela senhas...")
                cursor.execute("ALTER TABLE senhas ADD COLUMN notificado INTEGER DEFAULT 0")
                conn.commit()
                print("✅ Coluna 'notificado' adicionada com sucesso!")
            else:
                print("✅ Coluna 'notificado' já existe na tabela senhas.")
            
            if 'push_subscription' not in columns:
                print("Adicionando coluna 'push_subscription' à tabela senhas...")
                cursor.execute("ALTER TABLE senhas ADD COLUMN push_subscription TEXT")
                conn.commit()
                print("✅ Coluna 'push_subscription' adicionada com sucesso!")
            else:
                print("✅ Coluna 'push_subscription' já existe na tabela senhas.")
            
            # Adicionar coluna data_hora se não existir
            if 'data_hora' not in columns:
                print("Adicionando coluna 'data_hora' à tabela senhas...")
                cursor.execute("ALTER TABLE senhas ADD COLUMN data_hora TIMESTAMP")
                conn.commit()
                print("✅ Coluna 'data_hora' adicionada com sucesso!")
            else:
                print("✅ Coluna 'data_hora' já existe na tabela senhas.")
        else:
            print("❌ Tabela 'senhas' não existe!")
        
        # Verificar se a tabela setores existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='setores'")
        if not cursor.fetchone():
            print("Criando tabela 'setores'...")
            cursor.execute("""
                CREATE TABLE setores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    descricao TEXT,
                    senha_setor TEXT
                )
            """)
            conn.commit()
            print("✅ Tabela 'setores' criada com sucesso!")
        else:
            print("✅ Tabela 'setores' já existe.")
            # Verificar se a coluna senha_setor existe
            cursor.execute("PRAGMA table_info(setores)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'senha_setor' not in columns:
                print("Adicionando coluna 'senha_setor' à tabela setores...")
                cursor.execute("ALTER TABLE setores ADD COLUMN senha_setor TEXT")
                conn.commit()
                print("✅ Coluna 'senha_setor' adicionada com sucesso!")
            else:
                print("✅ Coluna 'senha_setor' já existe na tabela setores.")
        
        # Verificar se a tabela operadores existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='operadores'")
        if not cursor.fetchone():
            print("Criando tabela 'operadores'...")
            cursor.execute("""
                CREATE TABLE operadores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    foto_perfil TEXT,
                    setor_id INTEGER,
                    FOREIGN KEY (setor_id) REFERENCES setores (id)
                )
            """)
            conn.commit()
            print("✅ Tabela 'operadores' criada com sucesso!")
        else:
            print("✅ Tabela 'operadores' já existe.")
        
        # Verificar se a tabela atendimento_atual existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='atendimento_atual'")
        if not cursor.fetchone():
            print("Criando tabela 'atendimento_atual'...")
            cursor.execute("""
                CREATE TABLE atendimento_atual (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    senha_id INTEGER NOT NULL,
                    setor_id INTEGER NOT NULL,
                    operador_id INTEGER NOT NULL,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (senha_id) REFERENCES senhas (id),
                    FOREIGN KEY (setor_id) REFERENCES setores (id),
                    FOREIGN KEY (operador_id) REFERENCES operadores (id)
                )
            """)
            conn.commit()
            print("✅ Tabela 'atendimento_atual' criada com sucesso!")
        else:
            print("✅ Tabela 'atendimento_atual' já existe.")
        
        # Verificar se a tabela finalizados existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='finalizados'")
        if not cursor.fetchone():
            print("Criando tabela 'finalizados'...")
            cursor.execute("""
                CREATE TABLE finalizados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    senha_id INTEGER NOT NULL,
                    operador_id INTEGER NOT NULL,
                    setor_id INTEGER NOT NULL,
                    avaliacao TEXT,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (senha_id) REFERENCES senhas (id),
                    FOREIGN KEY (operador_id) REFERENCES operadores (id),
                    FOREIGN KEY (setor_id) REFERENCES setores (id)
                )
            """)
            conn.commit()
            print("✅ Tabela 'finalizados' criada com sucesso!")
        else:
            print("✅ Tabela 'finalizados' já existe.")
        
        # Verificar se a tabela impressoras existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='impressoras'")
        if not cursor.fetchone():
            print("Criando tabela 'impressoras'...")
            cursor.execute("""
                CREATE TABLE impressoras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    porta INTEGER DEFAULT 9100,
                    setor_id INTEGER,
                    FOREIGN KEY (setor_id) REFERENCES setores (id)
                )
            """)
            conn.commit()
            print("✅ Tabela 'impressoras' criada com sucesso!")
        else:
            print("✅ Tabela 'impressoras' já existe.")
        
        # Verificar se a tabela configuracoes existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracoes'")
        if not cursor.fetchone():
            print("Criando tabela 'configuracoes'...")
            cursor.execute("""
                CREATE TABLE configuracoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chave TEXT UNIQUE NOT NULL,
                    valor TEXT,
                    descricao TEXT,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("✅ Tabela 'configuracoes' criada com sucesso!")
        else:
            print("✅ Tabela 'configuracoes' já existe.")
        
        # Inserir configuração padrão do ngrok se não existir
        cursor.execute("SELECT id FROM configuracoes WHERE chave = 'ngrok_url'")
        if not cursor.fetchone():
            print("Inserindo configuração padrão do ngrok...")
            cursor.execute("""
                INSERT INTO configuracoes (chave, valor, descricao)
                VALUES (?, ?, ?)
            """, ('ngrok_url', '', 'URL do ngrok para notificações externas'))
            conn.commit()
            print("✅ Configuração padrão do ngrok inserida!")
        else:
            print("✅ Configuração do ngrok já existe.")
        
        conn.close()
        print("\n🎉 Migração concluída com sucesso!")
        print("O banco de dados está pronto para usar a funcionalidade de pedidos com campo booleano e confirmação.")
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🔄 Iniciando migração do banco de dados...")
    migrate_database() 