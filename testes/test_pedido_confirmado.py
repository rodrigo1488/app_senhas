#!/usr/bin/env python3
"""
Script para testar a funcionalidade de pedido confirmado
"""

import sqlite3
import os

def test_pedido_confirmado():
    """Testa a funcionalidade de pedido confirmado"""
    print("🧪 Testando funcionalidade de pedido confirmado...")
    
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados {db_path} não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a coluna pedido_confirmado existe
        cursor.execute("PRAGMA table_info(senhas)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'pedido_confirmado' in columns:
            print("✅ Coluna 'pedido_confirmado' existe na tabela senhas")
        else:
            print("❌ Coluna 'pedido_confirmado' não encontrada!")
            return
        
        # Verificar senha N9999
        cursor.execute("""
            SELECT id, senha, pedido, tem_pedido, pedido_confirmado, status, token_unico
            FROM senhas 
            WHERE senha = 'N9999'
            ORDER BY id DESC LIMIT 1
        """)
        
        senha = cursor.fetchone()
        
        if not senha:
            print("❌ Senha N9999 não encontrada!")
            return
        
        print(f"✅ Senha encontrada:")
        print(f"   - ID: {senha[0]}")
        print(f"   - Senha: {senha[1]}")
        print(f"   - Pedido: '{senha[2]}'")
        print(f"   - Tem pedido: {senha[3]}")
        print(f"   - Pedido confirmado: {senha[4]}")
        print(f"   - Status: {senha[5]}")
        print(f"   - Token: {senha[6]}")
        
        # Testar atualização do status pedido_confirmado
        print(f"\n🔄 Testando atualização do status pedido_confirmado...")
        cursor.execute("""
            UPDATE senhas 
            SET pedido_confirmado = 1 
            WHERE senha = 'N9999'
        """)
        conn.commit()
        
        # Verificar se foi atualizado
        cursor.execute("""
            SELECT pedido_confirmado
            FROM senhas 
            WHERE senha = 'N9999'
        """)
        
        resultado = cursor.fetchone()
        if resultado and resultado[0] == 1:
            print("✅ Status pedido_confirmado atualizado para TRUE")
        else:
            print("❌ Erro ao atualizar status pedido_confirmado")
        
        conn.close()
        
        print(f"\n🎯 Para testar a funcionalidade completa:")
        print(f"   1. Abra: http://localhost:5000/notificacao/{senha[6]}")
        print(f"   2. Abra: http://localhost:5000/senhas_pendentes")
        print(f"   3. Clique no botão 'Ver Pedido'")
        print(f"   4. Clique em 'Confirmar Recebimento'")
        print(f"   5. Verifique se a faixa 'PEDIDO EM PRODUÇÃO' aparece no cliente")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    test_pedido_confirmado() 