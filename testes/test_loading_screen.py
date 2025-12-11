#!/usr/bin/env python3
"""
Script para testar a tela de carregamento
"""

import sqlite3
import os

def test_loading_screen():
    """Testa a funcionalidade da tela de carregamento"""
    print("🧪 Testando tela de carregamento...")
    
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
        
        conn.close()
        
        print(f"\n🎯 Para testar a tela de carregamento:")
        print(f"   1. Abra: http://localhost:5000/notificacao/{senha[6]}")
        print(f"   2. A tela de carregamento deve aparecer primeiro")
        print(f"   3. Verifique as mensagens de status:")
        print(f"      - 'Conectando ao servidor...'")
        print(f"      - 'Registrando no servidor...'")
        print(f"      - 'Verificando status da senha...'")
        print(f"      - 'Configurando monitoramento...'")
        print(f"      - 'Monitoramento ativo!'")
        print(f"   4. Como o status é 'F', deve ir direto para tela de finalizado")
        print(f"   5. A tela de carregamento só some quando a tela definitiva aparece")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    test_loading_screen() 