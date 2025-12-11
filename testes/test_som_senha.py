#!/usr/bin/env python3
"""
Script para testar se o som está sendo reproduzido apenas quando uma nova senha é chamada
"""

import requests
import json
import time

def test_som_senha():
    """Testa se o som está sendo reproduzido corretamente"""
    
    print("🧪 Testando sistema de som para nova senha...")
    print("=" * 60)
    
    # URL do endpoint
    url = "http://192.168.2.33:5000/get_senha_atual_setor"
    
    print(f"Testando endpoint: {url}")
    print()
    
    # Primeira requisição - deve retornar a senha atual
    print("1️⃣ Primeira requisição (deve mostrar senha atual):")
    response1 = requests.get(url, timeout=10)
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"   Status: {response1.status_code}")
        print(f"   Senha: {data1.get('senha_atual', 'N/A')}")
        print(f"   Operador: {data1.get('operador', 'N/A')}")
        print(f"   Som: {'🔊 Tocado' if 'audio.mp3' in response1.text else '🔇 Não tocado'}")
    else:
        print(f"   ❌ Erro: {response1.status_code}")
    
    print()
    
    # Segunda requisição - mesma senha, não deve tocar som
    print("2️⃣ Segunda requisição (mesma senha, não deve tocar som):")
    response2 = requests.get(url, timeout=10)
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"   Status: {response2.status_code}")
        print(f"   Senha: {data2.get('senha_atual', 'N/A')}")
        print(f"   Operador: {data2.get('operador', 'N/A')}")
        print(f"   Som: {'🔊 Tocado' if 'audio.mp3' in response2.text else '🔇 Não tocado'}")
        
        # Verificar se é a mesma senha
        if data1.get('senha_atual') == data2.get('senha_atual'):
            print("   ✅ Mesma senha detectada")
        else:
            print("   ⚠️ Senha diferente detectada")
    else:
        print(f"   ❌ Erro: {response2.status_code}")
    
    print()
    
    # Terceira requisição - mesma senha, não deve tocar som
    print("3️⃣ Terceira requisição (mesma senha, não deve tocar som):")
    response3 = requests.get(url, timeout=10)
    if response3.status_code == 200:
        data3 = response3.json()
        print(f"   Status: {response3.status_code}")
        print(f"   Senha: {data3.get('senha_atual', 'N/A')}")
        print(f"   Operador: {data3.get('operador', 'N/A')}")
        print(f"   Som: {'🔊 Tocado' if 'audio.mp3' in response3.text else '🔇 Não tocado'}")
    else:
        print(f"   ❌ Erro: {response3.status_code}")
    
    print()
    print("📋 Resumo:")
    print("- O som deve ser reproduzido APENAS quando uma nova senha for chamada")
    print("- Requisições consecutivas com a mesma senha não devem tocar som")
    print("- Verifique o console do navegador para ver os logs detalhados")
    print()
    print("🎯 Para testar uma nova senha:")
    print("1. Vá para /senhas_pendentes")
    print("2. Clique em 'Chamar Próxima Senha'")
    print("3. Selecione um operador")
    print("4. Verifique se o som tocou apenas uma vez")

if __name__ == '__main__':
    test_som_senha() 