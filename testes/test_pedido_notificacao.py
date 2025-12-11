#!/usr/bin/env python3
"""
Script para testar o fluxo completo de notificação de pedido
"""

import sqlite3
import os
import requests
import time

def test_pedido_notificacao():
    """Testa o fluxo completo de notificação de pedido"""
    print("🧪 Testando fluxo completo de notificação de pedido...")
    
    # 1. Verificar se a senha de teste existe
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados {db_path} não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar senha N8888
        cursor.execute("""
            SELECT id, senha, pedido, tem_pedido, status, token_unico
            FROM senhas 
            WHERE senha = 'N8888'
            ORDER BY id DESC LIMIT 1
        """)
        
        senha = cursor.fetchone()
        conn.close()
        
        if not senha:
            print("❌ Senha N8888 não encontrada! Execute create_test_senha_atual.py primeiro.")
            return
        
        print(f"✅ Senha encontrada:")
        print(f"   - ID: {senha[0]}")
        print(f"   - Senha: {senha[1]}")
        print(f"   - Pedido: '{senha[2]}'")
        print(f"   - Tem pedido: {senha[3]}")
        print(f"   - Status: {senha[4]}")
        print(f"   - Token: {senha[5]}")
        
        # 2. Testar API de verificação de senha
        print(f"\n🔍 Testando API de verificação de senha...")
        try:
            response = requests.get(f"http://localhost:5000/api/verificar_senha/{senha[5]}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API funcionando:")
                print(f"   - Senha: {data.get('senha')}")
                print(f"   - Setor: {data.get('setor')}")
                print(f"   - Chamada: {data.get('chamada')}")
                print(f"   - Pedido: {data.get('pedido')}")
            else:
                print(f"❌ Erro na API: {response.status_code}")
        except Exception as e:
            print(f"❌ Erro ao testar API: {e}")
        
        # 3. Testar API de salvar pedido
        print(f"\n💾 Testando API de salvar pedido...")
        try:
            pedido_teste = "Pedido de teste para notificação"
            response = requests.post(
                f"http://localhost:5000/api/salvar_pedido/{senha[5]}",
                json={"pedido": pedido_teste}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Pedido salvo com sucesso:")
                print(f"   - Mensagem: {data.get('message')}")
                print(f"   - Pedido: {pedido_teste}")
            else:
                print(f"❌ Erro ao salvar pedido: {response.status_code}")
        except Exception as e:
            print(f"❌ Erro ao testar API de pedido: {e}")
        
        # 4. Verificar dados atualizados
        print(f"\n📊 Verificando dados atualizados...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, senha, pedido, tem_pedido, status
            FROM senhas 
            WHERE senha = 'N8888'
            ORDER BY id DESC LIMIT 1
        """)
        
        senha_atualizada = cursor.fetchone()
        conn.close()
        
        if senha_atualizada:
            print(f"✅ Dados atualizados:")
            print(f"   - ID: {senha_atualizada[0]}")
            print(f"   - Senha: {senha_atualizada[1]}")
            print(f"   - Pedido: '{senha_atualizada[2]}'")
            print(f"   - Tem pedido: {senha_atualizada[3]}")
            print(f"   - Status: {senha_atualizada[4]}")
        
        print(f"\n🎯 Fluxo de teste concluído!")
        print(f"📝 Para testar a notificação completa:")
        print(f"   1. Abra a página de notificação com o token: {senha[5]}")
        print(f"   2. Abra a página de senhas pendentes")
        print(f"   3. Clique no botão 'Ver Pedido'")
        print(f"   4. Clique em 'Confirmar Recebimento'")
        print(f"   5. Verifique se a notificação aparece na página do cliente")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

if __name__ == "__main__":
    test_pedido_notificacao() 