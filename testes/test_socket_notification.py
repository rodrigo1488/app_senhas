#!/usr/bin/env python3
"""
Script para testar a notificação via Socket.IO
"""

import sqlite3
import os
import requests
import json

def test_socket_notification():
    """Testa a notificação via Socket.IO"""
    print("🧪 Testando notificação via Socket.IO...")
    
    # 1. Verificar senha N9999
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados {db_path} não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar senha N9999
        cursor.execute("""
            SELECT id, senha, pedido, tem_pedido, status, token_unico
            FROM senhas 
            WHERE senha = 'N9999'
            ORDER BY id DESC LIMIT 1
        """)
        
        senha = cursor.fetchone()
        conn.close()
        
        if not senha:
            print("❌ Senha N9999 não encontrada!")
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
                print(f"   Resposta: {response.text}")
        except Exception as e:
            print(f"❌ Erro ao testar API: {e}")
        
        # 3. Testar se o servidor está rodando
        print(f"\n🌐 Testando se o servidor está rodando...")
        try:
            response = requests.get("http://localhost:5000/")
            if response.status_code == 200:
                print(f"✅ Servidor está rodando")
            else:
                print(f"⚠️ Servidor respondeu com status: {response.status_code}")
        except Exception as e:
            print(f"❌ Servidor não está rodando: {e}")
            print(f"   Execute: python app.py")
        
        print(f"\n🎯 Para testar a notificação completa:")
        print(f"   1. Certifique-se de que o servidor está rodando: python app.py")
        print(f"   2. Abra a página do cliente: http://localhost:5000/notificacao/{senha[5]}")
        print(f"   3. Abra a página do operador: http://localhost:5000/senhas_pendentes")
        print(f"   4. Clique no botão 'Ver Pedido'")
        print(f"   5. Clique em 'Confirmar Recebimento'")
        print(f"   6. Verifique os logs do servidor e do console do navegador")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")

if __name__ == "__main__":
    test_socket_notification() 