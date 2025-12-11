#!/usr/bin/env python3
"""
Script para testar a geração do QR Code
"""

import sys
import os

# Adicionar o diretório atual ao path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_qr_code_generation():
    """Testa a geração do QR Code"""
    try:
        from app import obter_ip_rede_local, gerar_qr_code_notificacao
        
        print("🧪 Testando geração do QR Code...")
        print("=" * 40)
        
        # Testar obtenção do IP
        print("1. Testando obtenção do IP local...")
        ip_local = obter_ip_rede_local()
        print(f"   IP detectado: {ip_local}")
        
        if ip_local == "localhost":
            print("   ⚠️  Ainda retornando localhost!")
        else:
            print("   ✅ IP da rede detectado corretamente")
        
        # Testar geração do QR Code
        print("\n2. Testando geração do QR Code...")
        token_teste = "teste-12345"
        qr_buffer = gerar_qr_code_notificacao(token_teste)
        
        if qr_buffer:
            print("   ✅ QR Code gerado com sucesso")
            print(f"   📱 URL esperada: https://{ip_local}:5000/notificacao/{token_teste}")
        else:
            print("   ❌ Erro ao gerar QR Code")
        
        # Verificar se a URL está correta
        url_esperada = f"https://{ip_local}:5000/notificacao/{token_teste}"
        if "localhost" in url_esperada:
            print("   ⚠️  URL ainda contém localhost!")
        else:
            print("   ✅ URL está usando IP da rede")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False

if __name__ == '__main__':
    test_qr_code_generation() 