#!/usr/bin/env python3
"""
Script para testar e verificar senhas com pedido no banco de dados
"""

import sqlite3
import os

def test_pedidos():
    """Testa e verifica senhas com pedido no banco de dados"""
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados {db_path} não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Verificando estrutura da tabela senhas...")
        cursor.execute("PRAGMA table_info(senhas)")
        columns = cursor.fetchall()
        
        print("📋 Colunas da tabela senhas:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        print("\n🔍 Verificando senhas com pedido...")
        cursor.execute("""
            SELECT id, senha, tipo, pedido, tem_pedido, status, setor_id
            FROM senhas 
            WHERE pedido IS NOT NULL AND pedido != ''
            ORDER BY id DESC
        """)
        
        senhas_com_pedido = cursor.fetchall()
        
        if senhas_com_pedido:
            print(f"✅ Encontradas {len(senhas_com_pedido)} senhas com pedido:")
            for senha in senhas_com_pedido:
                print(f"  - ID: {senha[0]}, Senha: {senha[1]}, Tipo: {senha[2]}")
                print(f"    Pedido: '{senha[3]}'")
                print(f"    Tem pedido: {senha[4]} (tipo: {type(senha[4])})")
                print(f"    Status: {senha[5]}, Setor: {senha[6]}")
                print()
        else:
            print("❌ Nenhuma senha com pedido encontrada!")
        
        print("🔍 Verificando senhas pendentes (status = 'A')...")
        cursor.execute("""
            SELECT id, senha, tipo, pedido, tem_pedido, setor_id
            FROM senhas 
            WHERE status = 'A'
            ORDER BY id ASC
        """)
        
        senhas_pendentes = cursor.fetchall()
        
        if senhas_pendentes:
            print(f"✅ Encontradas {len(senhas_pendentes)} senhas pendentes:")
            for senha in senhas_pendentes:
                print(f"  - ID: {senha[0]}, Senha: {senha[1]}, Tipo: {senha[2]}")
                print(f"    Pedido: '{senha[3]}'")
                print(f"    Tem pedido: {senha[4]} (tipo: {type(senha[4])})")
                print(f"    Setor: {senha[5]}")
                print()
        else:
            print("❌ Nenhuma senha pendente encontrada!")
        
        print("🔍 Verificando senhas chamadas (status = 'C')...")
        cursor.execute("""
            SELECT id, senha, tipo, pedido, tem_pedido, setor_id
            FROM senhas 
            WHERE status = 'C'
            ORDER BY id DESC
        """)
        
        senhas_chamadas = cursor.fetchall()
        
        if senhas_chamadas:
            print(f"✅ Encontradas {len(senhas_chamadas)} senhas chamadas:")
            for senha in senhas_chamadas:
                print(f"  - ID: {senha[0]}, Senha: {senha[1]}, Tipo: {senha[2]}")
                print(f"    Pedido: '{senha[3]}'")
                print(f"    Tem pedido: {senha[4]} (tipo: {type(senha[4])})")
                print(f"    Setor: {senha[5]}")
                print()
        else:
            print("❌ Nenhuma senha chamada encontrada!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao testar pedidos: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🧪 Testando sistema de pedidos...")
    test_pedidos() 