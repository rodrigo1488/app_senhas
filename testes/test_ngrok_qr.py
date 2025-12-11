#!/usr/bin/env python3
"""
Script para testar se os QR codes estão usando a URL do ngrok
"""

import sqlite3
import sys
import os

# Adicionar o diretório atual ao path para importar o app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_ngrok_url, get_notification_url, gerar_qr_code_notificacao

def test_ngrok_qr():
    """Testa se os QR codes estão usando a URL do ngrok"""
    print("🧪 Testando QR codes com ngrok...")
    
    # 1. Verificar se a URL do ngrok está configurada
    ngrok_url = get_ngrok_url()
    print(f"\n1. URL do ngrok configurada: {ngrok_url}")
    
    if ngrok_url:
        print("   ✅ URL do ngrok encontrada!")
    else:
        print("   ⚠️  URL do ngrok não configurada")
    
    # 2. Testar geração de URL de notificação
    token_teste = "teste-123"
    notification_url = get_notification_url(token_teste)
    print(f"\n2. URL de notificação gerada: {notification_url}")
    
    if ngrok_url and ngrok_url in notification_url:
        print("   ✅ URL está usando ngrok!")
    elif "localhost" in notification_url or "192.168" in notification_url:
        print("   ⚠️  URL está usando IP local")
    else:
        print("   ❓ URL não identificada")
    
    # 3. Testar geração do QR code
    print(f"\n3. Testando geração do QR code...")
    qr_buffer = gerar_qr_code_notificacao(token_teste)
    
    if qr_buffer:
        print("   ✅ QR code gerado com sucesso")
        print(f"   📊 Tamanho do QR code: {len(qr_buffer.getvalue())} bytes")
    else:
        print("   ❌ Erro ao gerar QR code")
    
    # 4. Verificar se o QR code contém a URL correta
    if qr_buffer and ngrok_url:
        print(f"\n4. QR code deve conter: {ngrok_url}")
        print("   📱 Escaneie o QR code para verificar se aponta para o ngrok")
    
    print(f"\n🎯 Resumo:")
    if ngrok_url:
        print(f"   - Ngrok configurado: {ngrok_url}")
        print(f"   - QR codes usarão: {ngrok_url}")
    else:
        print(f"   - Ngrok não configurado")
        print(f"   - QR codes usarão: IP local")
    
    print(f"\n💡 Para configurar o ngrok:")
    print(f"   1. Acesse: http://localhost:5000/admin")
    print(f"   2. Vá em 'Configuração' → 'Ngrok'")
    print(f"   3. Insira sua URL do ngrok")
    print(f"   4. Teste novamente este script")

if __name__ == "__main__":
    test_ngrok_qr() 