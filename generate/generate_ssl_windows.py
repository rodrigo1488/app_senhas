#!/usr/bin/env python3
"""
Script para gerar certificados SSL no Windows usando Python
"""

import os
import subprocess
import sys
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta

def generate_ssl_certificate():
    """Gera certificado SSL autoassinado usando Python"""
    print("Gerando certificado SSL autoassinado...")
    
    try:
        # Gerar chave privada
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Criar certificado
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "SP"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Sao Paulo"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "App Senhas"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Salvar chave privada
        with open("key.pem", "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Salvar certificado
        with open("cert.pem", "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        print("Certificados SSL gerados com sucesso!")
        print("- cert.pem: Certificado")
        print("- key.pem: Chave privada")
        
        return True
        
    except Exception as e:
        print(f"Erro ao gerar certificados SSL: {e}")
        return False

def generate_vapid_keys():
    """Gera chaves VAPID usando Python"""
    print("Gerando chaves VAPID...")
    
    try:
        import secrets
        import base64
        
        # Gerar chave privada aleatória (32 bytes)
        private_key = secrets.token_bytes(32)
        
        # Gerar chave pública (hash da privada)
        import hashlib
        public_key = hashlib.sha256(private_key).digest()
        
        # Converter para base64 URL-safe
        private_key_b64 = base64.urlsafe_b64encode(private_key).decode('utf-8').rstrip('=')
        public_key_b64 = base64.urlsafe_b64encode(public_key).decode('utf-8').rstrip('=')
        
        print("Chaves VAPID geradas com sucesso!")
        print("\nConfigure estas chaves no arquivo app.py:")
        print("=" * 50)
        print(f"VAPID_PRIVATE_KEY = \"{private_key_b64}\"")
        print(f"VAPID_PUBLIC_KEY = \"{public_key_b64}\"")
        print("VAPID_EMAIL = \"seu-email@exemplo.com\"")
        print("=" * 50)
        
        # Salvar em arquivo
        with open('vapid_keys.txt', 'w', encoding='utf-8') as f:
            f.write("Chaves VAPID para Web Push Notifications\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Private Key: {private_key_b64}\n")
            f.write(f"Public Key: {public_key_b64}\n")
            f.write(f"Email: seu-email@exemplo.com\n")
        
        print("Chaves salvas em 'vapid_keys.txt'")
        
        return True
        
    except Exception as e:
        print(f"Erro ao gerar chaves VAPID: {e}")
        return False

def main():
    """Funcao principal"""
    print("Configurando sistema de notificacoes...")
    print("=" * 40)
    
    # Gerar certificados SSL
    if generate_ssl_certificate():
        print("Certificados SSL: OK")
    else:
        print("Certificados SSL: FALHOU")
        return False
    
    # Gerar chaves VAPID
    if generate_vapid_keys():
        print("Chaves VAPID: OK")
    else:
        print("Chaves VAPID: FALHOU")
        return False
    
    print("\nConfiguracao concluida!")
    print("Execute: python run_with_ssl.py")
    
    return True

if __name__ == '__main__':
    main() 