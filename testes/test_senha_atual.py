#!/usr/bin/env python3
"""
Script para testar se o card da senha atual está funcionando
"""

import requests
import json
import sys

def test_senha_atual_endpoint():
    """Testa o endpoint get_senha_atual_setor"""
    try:
        # URL do endpoint
        url = "http://192.168.2.33:5000/get_senha_atual_setor"
        
        print(f"Testando endpoint: {url}")
        
        # Fazer requisição GET
        response = requests.get(url, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Resposta: {json.dumps(data, indent=2)}")
            
            # Verificar se há dados
            if data.get('senha_atual'):
                print(f"✅ Senha atual: {data['senha_atual']}")
            else:
                print("⚠️ Nenhuma senha atual")
                
            if data.get('operador'):
                print(f"✅ Operador: {data['operador']}")
            else:
                print("⚠️ Nenhum operador ativo")
                
            if data.get('foto_operador'):
                print(f"✅ Foto do operador: {data['foto_operador']}")
            else:
                print("⚠️ Sem foto do operador")
                
            return True
        else:
            print(f"❌ Erro: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_senhas_pendentes_page():
    """Testa a página de senhas pendentes"""
    try:
        # URL da página
        url = "http://192.168.2.33:5000/senhas_pendentes"
        
        print(f"\nTestando página: {url}")
        
        # Fazer requisição GET
        response = requests.get(url, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Página funcionando!")
            
            # Verificar se o card da senha atual está no HTML
            if 'senha-atual-card' in response.text:
                print("✅ Card da senha atual encontrado no HTML")
            else:
                print("❌ Card da senha atual NÃO encontrado no HTML")
                
            if 'function atualizarSenha' in response.text:
                print("✅ Função atualizarSenha encontrada no HTML")
            else:
                print("❌ Função atualizarSenha NÃO encontrada no HTML")
                
            if 'atualizandoSenha' in response.text:
                print("✅ Controle de atualização encontrado no HTML")
            else:
                print("❌ Controle de atualização NÃO encontrado no HTML")
                
            return True
        else:
            print("❌ Página com problema")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_senha_atual_page():
    """Testa a página de senha atual"""
    try:
        # URL da página
        url = "http://192.168.2.33:5000/senha_atual"
        
        print(f"\nTestando página: {url}")
        
        # Fazer requisição GET
        response = requests.get(url, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Página funcionando!")
            
            # Verificar se os elementos estão no HTML
            if 'id="senha_atual"' in response.text:
                print("✅ Elemento senha_atual encontrado no HTML")
            else:
                print("❌ Elemento senha_atual NÃO encontrado no HTML")
                
            if 'function atualizarSenhaAtual' in response.text:
                print("✅ Função atualizarSenhaAtual encontrada no HTML")
            else:
                print("❌ Função atualizarSenhaAtual NÃO encontrada no HTML")
                
            if 'atualizandoSenhaAtual' in response.text:
                print("✅ Controle de atualização encontrado no HTML")
            else:
                print("❌ Controle de atualização NÃO encontrado no HTML")
                
            return True
        else:
            print("❌ Página com problema")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    """Função principal"""
    print("🧪 Testando sistema de senha atual...")
    print("=" * 50)
    
    # Testar endpoint
    endpoint_ok = test_senha_atual_endpoint()
    
    # Testar página de senhas pendentes
    pendentes_ok = test_senhas_pendentes_page()
    
    # Testar página de senha atual
    atual_ok = test_senha_atual_page()
    
    print("\n📋 Resumo:")
    print(f"- Endpoint: {'✅ OK' if endpoint_ok else '❌ ERRO'}")
    print(f"- Página senhas pendentes: {'✅ OK' if pendentes_ok else '❌ ERRO'}")
    print(f"- Página senha atual: {'✅ OK' if atual_ok else '❌ ERRO'}")
    
    if endpoint_ok and pendentes_ok and atual_ok:
        print("\n🎉 Todos os testes passaram!")
    else:
        print("\n⚠️ Alguns testes falharam!")

if __name__ == '__main__':
    main() 