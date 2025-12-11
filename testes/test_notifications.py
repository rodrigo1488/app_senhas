#!/usr/bin/env python3
"""
Script para testar notificações push
"""

import requests
import json
import sys

def test_notification_endpoint():
    """Testa o endpoint de notificação"""
    try:
        # URL do endpoint
        url = "https://192.168.2.33:5000/api/notificar/1"
        
        print(f"Testando endpoint: {url}")
        
        # Fazer requisição POST
        response = requests.post(url, verify=False, timeout=10)
        
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text}")
        
        if response.status_code == 200:
            print("✅ Endpoint funcionando!")
        else:
            print("❌ Endpoint com problema")
            
    except requests.exceptions.SSLError as e:
        print(f"⚠️ Erro SSL: {e}")
        print("Isso é normal com certificados autoassinados")
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_notification_page():
    """Testa a página de notificação"""
    try:
        # URL da página
        url = "https://192.168.2.33:5000/notificacao/teste-123"
        
        print(f"\nTestando página: {url}")
        
        # Fazer requisição GET
        response = requests.get(url, verify=False, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Página funcionando!")
            if "Service Worker" in response.text:
                print("✅ Service Worker detectado na página")
            else:
                print("⚠️ Service Worker não encontrado na página")
        else:
            print("❌ Página com problema")
            
    except requests.exceptions.SSLError as e:
        print(f"⚠️ Erro SSL: {e}")
        print("Isso é normal com certificados autoassinados")
    except Exception as e:
        print(f"❌ Erro: {e}")

def main():
    """Função principal"""
    print("🧪 Testando sistema de notificações...")
    print("=" * 40)
    
    # Testar página de notificação
    test_notification_page()
    
    # Testar endpoint de notificação
    test_notification_endpoint()
    
    print("\n📋 Resumo:")
    print("- Se a página retornou 200: ✅ HTTPS funcionando")
    print("- Se há erro SSL: ⚠️ Normal com certificados autoassinados")
    print("- Para usar no celular: Aceite o certificado quando solicitado")

if __name__ == '__main__':
    main() 