#!/usr/bin/env python3
"""
Script para testar se todos os imports necessários estão disponíveis
Execute antes de fazer o build para verificar dependências
"""

import sys

print("=" * 60)
print("TESTE DE IMPORTS - App Senhas")
print("=" * 60)
print()

# Lista de módulos para testar
modules_to_test = [
    # Core
    'eventlet',
    'flask',
    'flask_socketio',
    'flask_cors',
    'werkzeug',
    'supabase',
    'sqlite3',
    'socket',
    'threading',
    'uuid',
    'json',
    'io',
    'datetime',
    'random',
    'os',
    'sys',
    'time',
    # Eventlet específicos
    'eventlet.wsgi',
    'eventlet.green',
    'eventlet.greenio',
    'eventlet.hubs',
    'eventlet.hubs.epolls',
    'eventlet.hubs.kqueue',
    'eventlet.hubs.selects',
    'eventlet.hubs.poll',
    'eventlet.patcher',
    'eventlet.support.greendns',
    # DNS
    'dns',
    'dns.resolver',
    # Flask/SocketIO
    'engineio',
    'socketio',
    # Supabase
    'gotrue',
    'postgrest',
    'realtime',
    'storage3',
    'pydantic',
    'httpx',
    'urllib3',
    # Outros
    'greenlet',
    'escpos',
    'escpos.printer',
    'qrcode',
    'PIL',
    'PIL.Image',
    'dotenv',
    'pywebpush',
    'cryptography',
]

failed_imports = []
successful_imports = []

print("Testando imports...")
print()

for module_name in modules_to_test:
    try:
        __import__(module_name)
        successful_imports.append(module_name)
        print(f"✅ {module_name}")
    except ImportError as e:
        failed_imports.append((module_name, str(e)))
        print(f"❌ {module_name} - {e}")
    except Exception as e:
        # Alguns módulos podem ter erros de inicialização mas estar disponíveis
        successful_imports.append(module_name)
        print(f"⚠️  {module_name} - {type(e).__name__}: {e}")

print()
print("=" * 60)
print(f"RESUMO: {len(successful_imports)} sucessos, {len(failed_imports)} falhas")
print("=" * 60)

if failed_imports:
    print()
    print("❌ MÓDULOS FALTANDO:")
    for module, error in failed_imports:
        print(f"   - {module}: {error}")
    print()
    print("💡 Ação: Instale os módulos faltantes com:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
else:
    print()
    print("✅ Todos os módulos estão disponíveis!")
    print("✅ Pronto para fazer o build!")
    sys.exit(0)

