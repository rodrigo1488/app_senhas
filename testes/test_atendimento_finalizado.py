#!/usr/bin/env python3
"""
Script para testar a funcionalidade de atendimento finalizado
"""

import sqlite3
import os

def test_atendimento_finalizado():
    """Testa a funcionalidade de atendimento finalizado"""
    print("🧪 Testando funcionalidade de atendimento finalizado...")
    
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados {db_path} não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar senha N9999
        cursor.execute("""
            SELECT id, senha, status, pedido, tem_pedido, pedido_confirmado, token_unico
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
        print(f"   - Status: {senha[2]}")
        print(f"   - Pedido: '{senha[3]}'")
        print(f"   - Tem pedido: {senha[4]}")
        print(f"   - Pedido confirmado: {senha[5]}")
        print(f"   - Token: {senha[6]}")
        
        # Testar mudança de status para finalizado
        print(f"\n🔄 Testando mudança de status para finalizado...")
        cursor.execute("""
            UPDATE senhas 
            SET status = 'F' 
            WHERE senha = 'N9999'
        """)
        conn.commit()
        
        # Verificar se foi atualizado
        cursor.execute("""
            SELECT status
            FROM senhas 
            WHERE senha = 'N9999'
        """)
        
        resultado = cursor.fetchone()
        if resultado and resultado[0] == 'F':
            print("✅ Status atualizado para 'F' (Finalizado)")
        else:
            print("❌ Erro ao atualizar status para finalizado")
        
        conn.close()
        
        print(f"\n🎯 Para testar a funcionalidade completa:")
        print(f"   1. Abra: http://localhost:5000/notificacao/{senha[6]}")
        print(f"   2. A tela de 'Atendimento Finalizado' deve aparecer automaticamente")
        print(f"   3. Verifique se todas as informações estão corretas")
        print(f"   4. A tela deve ser apenas informativa, sem botões de navegação")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    test_atendimento_finalizado() 