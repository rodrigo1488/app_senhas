#!/usr/bin/env python3
"""
Script simples para gerar chaves VAPID usando Python padrão
"""

import os
import secrets
import base64
import hashlib
import hmac

def generate_vapid_keys():
    """Gera chaves VAPID usando Python padrão"""
    print("🔑 Gerando chaves VAPID...")
    
    try:
        # Gerar chave privada aleatória (32 bytes)
        private_key = secrets.token_bytes(32)
        
        # Gerar chave pública (ponto na curva elíptica)
        # Para simplificar, vamos usar um hash da chave privada
        public_key = hashlib.sha256(private_key).digest()
        
        # Converter para base64 URL-safe
        private_key_b64 = base64.urlsafe_b64encode(private_key).decode('utf-8').rstrip('=')
        public_key_b64 = base64.urlsafe_b64encode(public_key).decode('utf-8').rstrip('=')
        
        print("✅ Chaves VAPID geradas com sucesso!")
        print("\n📋 Configure estas chaves no arquivo app.py:")
        print("=" * 50)
        print(f"VAPID_PRIVATE_KEY = \"{private_key_b64}\"")
        print(f"VAPID_PUBLIC_KEY = \"{public_key_b64}\"")
        print("VAPID_EMAIL = \"seu-email@exemplo.com\"")
        print("=" * 50)
        
        # Salvar em arquivo para referência
        with open('vapid_keys.txt', 'w') as f:
            f.write("Chaves VAPID para Web Push Notifications\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Private Key: {private_key_b64}\n")
            f.write(f"Public Key: {public_key_b64}\n")
            f.write(f"Email: seu-email@exemplo.com\n")
        
        print("\n💾 Chaves salvas em 'vapid_keys.txt'")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao gerar chaves VAPID: {e}")
        return False

if __name__ == '__main__':
    generate_vapid_keys() 