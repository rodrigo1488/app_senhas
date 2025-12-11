#!/usr/bin/env python3
"""
Script para criar uma senha de teste com pedido
"""

import sqlite3
import os

def create_test_senha():
    """Cria uma senha de teste com pedido"""
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados {db_path} não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Criar uma nova senha com pedido
        senha_teste = "N9999"
        pedido_teste = "Teste de pedido para popup"
        
        print(f"📝 Criando senha de teste: {senha_teste}")
        print(f"📝 Pedido: {pedido_teste}")
        
        cursor.execute("""
            INSERT INTO senhas (senha, tipo, setor_id, status, pedido, tem_pedido)
            VALUES (?, 'normal', 1, 'A', ?, 1)
        """, (senha_teste, pedido_teste))
        
        conn.commit()
        senha_id = cursor.lastrowid
        
        print(f"✅ Senha criada com sucesso!")
        print(f"   - ID: {senha_id}")
        print(f"   - Senha: {senha_teste}")
        print(f"   - Status: A (Pendente)")
        print(f"   - Pedido: {pedido_teste}")
        print(f"   - Tem pedido: 1")
        
        # Verificar se foi criada corretamente
        cursor.execute("""
            SELECT id, senha, tipo, pedido, tem_pedido, status, setor_id
            FROM senhas 
            WHERE id = ?
        """, (senha_id,))
        
        senha = cursor.fetchone()
        if senha:
            print(f"\n✅ Verificação - Senha encontrada:")
            print(f"   - ID: {senha[0]}, Senha: {senha[1]}, Tipo: {senha[2]}")
            print(f"   - Pedido: '{senha[3]}'")
            print(f"   - Tem pedido: {senha[4]} (tipo: {type(senha[4])})")
            print(f"   - Status: {senha[5]}, Setor: {senha[6]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao criar senha de teste: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🧪 Criando senha de teste com pedido...")
    create_test_senha() 