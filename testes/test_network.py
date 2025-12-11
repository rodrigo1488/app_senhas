#!/usr/bin/env python3
"""
Script para testar conectividade de rede e mostrar informações úteis
"""

import socket
import requests
import subprocess
import platform

def obter_ip_rede_local():
    """Obtém o IP da rede local"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        return ip_local
    except Exception as e:
        print(f"❌ Erro ao obter IP local: {e}")
        return None

def testar_conectividade():
    """Testa conectividade básica"""
    print("🌐 Testando conectividade de rede...")
    
    # Obter IP local
    ip_local = obter_ip_rede_local()
    if ip_local:
        print(f"✅ IP da rede local: {ip_local}")
    else:
        print("❌ Não foi possível obter o IP local")
        return False
    
    # Testar conectividade com internet
    try:
        response = requests.get("https://www.google.com", timeout=5)
        print("✅ Conectividade com internet: OK")
    except Exception as e:
        print(f"⚠️  Conectividade com internet: {e}")
    
    # Testar porta 5000 local
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()
        if result == 0:
            print("✅ Porta 5000 local: Em uso (aplicação rodando)")
        else:
            print("ℹ️  Porta 5000 local: Livre")
    except Exception as e:
        print(f"❌ Erro ao testar porta 5000: {e}")
    
    return True

def mostrar_comandos_uteis(ip_local):
    """Mostra comandos úteis para testar conectividade"""
    print("\n🔧 Comandos úteis para testar:")
    print("=" * 50)
    
    print(f"\n📱 Para dispositivos móveis na mesma rede:")
    print(f"   HTTP:  http://{ip_local}:5000")
    print(f"   HTTPS: https://{ip_local}:5000")
    
    print(f"\n💻 Para testar no próprio computador:")
    print(f"   HTTP:  http://localhost:5000")
    print(f"   HTTPS: https://localhost:5000")
    
    print(f"\n🔍 Para testar conectividade:")
    if platform.system() == "Windows":
        print(f"   ping {ip_local}")
        print(f"   telnet {ip_local} 5000")
    else:
        print(f"   ping {ip_local}")
        print(f"   nc -zv {ip_local} 5000")
    
    print(f"\n📋 Para verificar firewall:")
    if platform.system() == "Windows":
        print(f"   netsh advfirewall firewall show rule name=all | findstr 5000")
    else:
        print(f"   sudo ufw status")
        print(f"   sudo iptables -L")

def verificar_certificados_ssl():
    """Verifica se os certificados SSL existem"""
    import os
    
    print("\n🔒 Verificando certificados SSL...")
    
    cert_exists = os.path.exists('cert.pem')
    key_exists = os.path.exists('key.pem')
    
    if cert_exists and key_exists:
        print("✅ Certificados SSL encontrados")
        print("   - cert.pem: OK")
        print("   - key.pem: OK")
        return True
    else:
        print("❌ Certificados SSL não encontrados")
        if not cert_exists:
            print("   - cert.pem: Ausente")
        if not key_exists:
            print("   - key.pem: Ausente")
        print("\n💡 Para gerar certificados SSL:")
        print("   python setup_notifications.py")
        return False

def main():
    """Função principal"""
    print("🚀 Teste de Conectividade de Rede")
    print("=" * 40)
    
    # Testar conectividade
    if not testar_conectividade():
        return
    
    # Obter IP local
    ip_local = obter_ip_rede_local()
    
    # Verificar certificados SSL
    ssl_ok = verificar_certificados_ssl()
    
    # Mostrar comandos úteis
    mostrar_comandos_uteis(ip_local)
    
    print(f"\n🎯 Resumo:")
    print(f"   IP Local: {ip_local}")
    print(f"   SSL: {'✅ Ativo' if ssl_ok else '❌ Inativo'}")
    print(f"   Protocolo: {'HTTPS' if ssl_ok else 'HTTP'}")
    
    if ssl_ok:
        print(f"\n✅ Sistema pronto para notificações push!")
        print(f"   Acesse: https://{ip_local}:5000")
    else:
        print(f"\n⚠️  Para ativar notificações push:")
        print(f"   1. Execute: python setup_notifications.py")
        print(f"   2. Reinicie o aplicativo")
        print(f"   3. Acesse: https://{ip_local}:5000")

if __name__ == '__main__':
    main() 