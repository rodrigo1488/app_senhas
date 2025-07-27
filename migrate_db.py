import sqlite3
import os

def migrate_database():
    """Migra o banco de dados para incluir o campo foto_perfil"""
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print("Banco de dados não encontrado. Criando novo banco...")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar se o campo foto_perfil já existe
        cursor.execute("PRAGMA table_info(operadores)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'foto_perfil' not in columns:
            print("Adicionando campo foto_perfil à tabela operadores...")
            cursor.execute("ALTER TABLE operadores ADD COLUMN foto_perfil TEXT")
            conn.commit()
            print("Campo foto_perfil adicionado com sucesso!")
        else:
            print("Campo foto_perfil já existe na tabela operadores.")
            
    except Exception as e:
        print(f"Erro durante a migração: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database() 