#!/usr/bin/env python3
"""
Script para testar com uma senha que não está finalizada
"""

import sqlite3
import os

def test_senha_nao_finalizada():
    """Testa com uma senha que não está finalizada"""
    print("🧪 Testando com senha não finalizada...")
    
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados {db_path} não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Criar uma senha de teste que não está finalizada
        print("🔄 Criando senha de teste não finalizada...")
        
        cursor.execute("""
            INSERT INTO senhas (senha, status, token_unico, setor_id, pedido, tem_pedido, pedido_confirmado)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('N8888', 'A', 'test-token-nao-finalizada', 1, 'Pedido de teste não finalizado', 1, 0))
        
        conn.commit()
        
        # Buscar a senha criada
        cursor.execute("""
            SELECT id, senha, status, pedido, tem_pedido, pedido_confirmado, token_unico
            FROM senhas 
            WHERE senha = 'N8888'
            ORDER BY id DESC LIMIT 1
        """)
        
        senha = cursor.fetchone()
        
        if not senha:
            print("❌ Senha N8888 não encontrada!")
            return
        
        print(f"✅ Senha criada:")
        print(f"   - ID: {senha[0]}")
        print(f"   - Senha: {senha[1]}")
        print(f"   - Status: {senha[2]}")
        print(f"   - Pedido: '{senha[3]}'")
        print(f"   - Tem pedido: {senha[4]}")
        print(f"   - Pedido confirmado: {senha[5]}")
        print(f"   - Token: {senha[6]}")
        
        conn.close()
        
        print(f"\n🎯 Para testar a tela de carregamento com senha não finalizada:")
        print(f"   1. Abra: http://localhost:5000/notificacao/{senha[6]}")
        print(f"   2. A tela de carregamento deve aparecer primeiro")
        print(f"   3. Verifique as mensagens de status:")
        print(f"      - 'Conectando ao servidor...'")
        print(f"      - 'Registrando no servidor...'")
        print(f"      - 'Verificando status da senha...'")
        print(f"      - 'Configurando monitoramento...'")
        print(f"      - 'Monitoramento ativo!'")
        print(f"   4. Como o status é 'A', deve ir para interface principal")
        print(f"   5. A tela de carregamento só some quando a interface principal aparece")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    test_senha_nao_finalizada() 