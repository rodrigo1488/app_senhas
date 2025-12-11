#!/usr/bin/env python3
"""
Script para testar a configuração do ngrok
"""

import sqlite3
import os

def test_ngrok_config():
    """Testa a configuração do ngrok"""
    print("🧪 Testando configuração do ngrok...")
    
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados {db_path} não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se a tabela configuracoes existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracoes'")
        if not cursor.fetchone():
            print("❌ Tabela 'configuracoes' não encontrada!")
            return
        
        print("✅ Tabela 'configuracoes' encontrada")
        
        # Verificar configuração do ngrok
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'ngrok_url'")
        result = cursor.fetchone()
        
        if result:
            ngrok_url = result[0]
            print(f"✅ Configuração do ngrok encontrada:")
            print(f"   - URL: '{ngrok_url}'")
            
            if ngrok_url:
                print(f"   - Status: Configurado")
                print(f"   - QR codes usarão: {ngrok_url}")
            else:
                print(f"   - Status: Não configurado")
                print(f"   - QR codes usarão: http://localhost:5000")
        else:
            print("❌ Configuração do ngrok não encontrada!")
        
        # Testar inserção de URL do ngrok
        print(f"\n🔄 Testando inserção de URL do ngrok...")
        test_url = "https://teste123.ngrok.io"
        
        cursor.execute("""
            UPDATE configuracoes 
            SET valor = ?, data_atualizacao = CURRENT_TIMESTAMP 
            WHERE chave = 'ngrok_url'
        """, (test_url,))
        conn.commit()
        
        # Verificar se foi atualizado
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'ngrok_url'")
        result = cursor.fetchone()
        
        if result and result[0] == test_url:
            print("✅ URL do ngrok atualizada com sucesso!")
        else:
            print("❌ Erro ao atualizar URL do ngrok")
        
        # Limpar URL de teste
        cursor.execute("""
            UPDATE configuracoes 
            SET valor = '', data_atualizacao = CURRENT_TIMESTAMP 
            WHERE chave = 'ngrok_url'
        """)
        conn.commit()
        print("✅ URL de teste removida")
        
        conn.close()
        
        print(f"\n🎯 Para testar a funcionalidade completa:")
        print(f"   1. Acesse: http://localhost:5000/admin")
        print(f"   2. Vá para a aba 'Configurações'")
        print(f"   3. Configure uma URL do ngrok (ex: https://abc123.ngrok.io)")
        print(f"   4. Salve a configuração")
        print(f"   5. Teste gerando um QR code para ver se usa a URL do ngrok")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    test_ngrok_config() 