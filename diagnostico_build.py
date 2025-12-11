#!/usr/bin/env python3
"""
Script de diagnóstico completo para problemas no build
"""

import sys
import os
import subprocess

print("=" * 70)
print("DIAGNÓSTICO COMPLETO - Build PyInstaller")
print("=" * 70)
print()

# 1. Verificar Python
print("1. Verificando Python...")
python_version = sys.version_info
print(f"   Versão: {python_version.major}.{python_version.minor}.{python_version.micro}")
if python_version < (3, 8):
    print("   ⚠️  Python 3.8+ recomendado")
else:
    print("   ✅ Versão OK")
print()

# 2. Verificar PyInstaller
print("2. Verificando PyInstaller...")
try:
    import PyInstaller
    print(f"   ✅ PyInstaller instalado: {PyInstaller.__version__}")
except ImportError:
    print("   ❌ PyInstaller NÃO instalado!")
    print("   Execute: pip install pyinstaller")
    sys.exit(1)
print()

# 3. Verificar arquivos necessários
print("3. Verificando arquivos do projeto...")
arquivos_necessarios = [
    'app.py',
    'requirements.txt',
    'build_executable.spec',
    'templates',
    'static'
]

for arquivo in arquivos_necessarios:
    if os.path.exists(arquivo):
        print(f"   ✅ {arquivo}")
    else:
        print(f"   ❌ {arquivo} NÃO encontrado!")
print()

# 4. Verificar imports
print("4. Testando imports críticos...")
imports_criticos = [
    'eventlet',
    'flask',
    'flask_socketio',
    'supabase',
    'dns',
    'greenlet',
]

falhas = []
for mod in imports_criticos:
    try:
        __import__(mod)
        print(f"   ✅ {mod}")
    except ImportError as e:
        print(f"   ❌ {mod} - {e}")
        falhas.append(mod)
print()

# 5. Verificar estrutura de pastas
print("5. Verificando estrutura de pastas...")
if os.path.exists('templates'):
    templates_count = len([f for f in os.listdir('templates') if f.endswith('.html')])
    print(f"   ✅ templates/ ({templates_count} arquivos HTML)")
else:
    print("   ❌ templates/ não encontrado")

if os.path.exists('static'):
    static_items = len(os.listdir('static'))
    print(f"   ✅ static/ ({static_items} itens)")
else:
    print("   ❌ static/ não encontrado")
print()

# 6. Verificar dependências do requirements.txt
print("6. Verificando requirements.txt...")
if os.path.exists('requirements.txt'):
    with open('requirements.txt', 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    print(f"   ✅ {len(requirements)} dependências listadas")
    print("   Dependências principais:")
    for req in requirements[:10]:  # Mostrar primeiras 10
        print(f"      - {req}")
else:
    print("   ❌ requirements.txt não encontrado")
print()

# 7. Verificar se há builds anteriores
print("7. Verificando builds anteriores...")
if os.path.exists('build'):
    print("   ⚠️  Pasta 'build' existe (recomendado limpar)")
if os.path.exists('dist'):
    print("   ⚠️  Pasta 'dist' existe (recomendado limpar)")
if not os.path.exists('build') and not os.path.exists('dist'):
    print("   ✅ Nenhum build anterior encontrado")
print()

# Resumo
print("=" * 70)
if falhas:
    print("❌ PROBLEMAS ENCONTRADOS:")
    print(f"   Módulos faltando: {', '.join(falhas)}")
    print()
    print("💡 SOLUÇÃO:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
else:
    print("✅ DIAGNÓSTICO COMPLETO - Tudo OK!")
    print()
    print("🚀 Pronto para fazer o build!")
    print("   Execute: pyinstaller build_executable_v2.spec")
    sys.exit(0)

