#!/usr/bin/env python3
"""
Script para testar notificações HTTP
"""

import requests
import json
import sys

def test_notification_page():
    """Testa a página de notificação em HTTP"""
    try:
        # URL da página
        url = "http://192.168.2.33:5000/notificacao/teste-123"
        
        print(f"Testando página: {url}")
        
        # Fazer requisição GET
        response = requests.get(url, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Página funcionando!")
            if "Service Worker" in response.text:
                print("✅ Service Worker detectado na página")
            else:
                print("⚠️ Service Worker não encontrado na página")
        else:
            print("❌ Página com problema")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_notification_endpoint():
    """Testa o endpoint de notificação"""
    try:
        # URL do endpoint
        url = "http://192.168.2.33:5000/api/notificar/1"
        
        print(f"\nTestando endpoint: {url}")
        
        # Fazer requisição POST
        response = requests.post(url, timeout=10)
        
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text}")
        
        if response.status_code == 200:
            print("✅ Endpoint funcionando!")
        else:
            print("❌ Endpoint com problema")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def main():
    """Função principal"""
    print("🧪 Testando sistema de notificações HTTP...")
    print("=" * 40)
    
    # Testar página de notificação
    test_notification_page()
    
    # Testar endpoint de notificação
    test_notification_endpoint()
    
    print("\n📋 Resumo:")
    print("- Se a página retornou 200: ✅ HTTP funcionando")
    print("- Agora deve funcionar no celular sem problemas de SSL")

if __name__ == '__main__':
    main() 