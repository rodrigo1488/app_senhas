#!/usr/bin/env python3
"""
Script para testar se os alertas de fila estão funcionando corretamente
"""

import sqlite3
import sys
import os

# Adicionar o diretório atual ao path para importar o app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import DB_PATH

def test_alerta_fila():
    """Testa se os alertas de fila estão funcionando corretamente"""
    print("🧪 Testando alertas de fila...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Verificar senhas ativas
        cursor.execute('''
            SELECT s.id, s.senha, s.token_unico, s.status, st.nome as setor_nome
            FROM senhas s
            LEFT JOIN setores st ON s.setor_id = st.id
            WHERE s.status = 'A' AND s.token_unico IS NOT NULL
            ORDER BY s.id ASC
        ''')
        
        senhas = cursor.fetchall()
        print(f"\n1. Senhas ativas encontradas: {len(senhas)}")
        
        if not senhas:
            print("   ⚠️  Nenhuma senha ativa encontrada")
            return
        
        # 2. Mostrar posições na fila
        print(f"\n2. Posições na fila:")
        for i, (senha_id, senha_numero, token, status, setor) in enumerate(senhas):
            posicao = i
            print(f"   Posição {posicao}: Senha {senha_numero} (Token: {token[:8]}...) - Setor: {setor}")
            
            # Verificar se deveria receber alerta
            if 1 <= posicao <= 3:
                print(f"      ✅ Deveria receber alerta de proximidade")
            else:
                print(f"      ⏳ Aguardando na fila")
        
        # 3. Verificar se há inconsistências
        print(f"\n3. Verificando inconsistências:")
        
        # Verificar se há senhas com posição 0 mas status 'A'
        cursor.execute('''
            SELECT COUNT(*) 
            FROM senhas 
            WHERE status = 'A' AND token_unico IS NOT NULL
        ''')
        
        total_ativas = cursor.fetchone()[0]
        print(f"   Total de senhas ativas: {total_ativas}")
        print(f"   Posições calculadas: {len(senhas)}")
        
        if total_ativas != len(senhas):
            print(f"   ⚠️  Inconsistência detectada!")
        else:
            print(f"   ✅ Dados consistentes")
        
        # 4. Verificar tokens únicos
        print(f"\n4. Verificando tokens únicos:")
        tokens = [senha[2] for senha in senhas]
        tokens_unicos = set(tokens)
        
        if len(tokens) == len(tokens_unicos):
            print(f"   ✅ Todos os tokens são únicos")
        else:
            print(f"   ⚠️  Tokens duplicados detectados!")
            print(f"   Total: {len(tokens)}, Únicos: {len(tokens_unicos)}")
        
        # 5. Verificar setores
        print(f"\n5. Verificando setores:")
        setores = set([senha[4] for senha in senhas if senha[4]])
        print(f"   Setores com senhas ativas: {', '.join(setores) if setores else 'Nenhum'}")
        
        conn.close()
        
        print(f"\n🎯 Resumo:")
        print(f"   - Senhas ativas: {len(senhas)}")
        print(f"   - Senhas que deveriam receber alerta: {len([s for i, s in enumerate(senhas) if 1 <= i <= 3])}")
        print(f"   - Setores: {len(setores)}")
        
        print(f"\n💡 Para testar os alertas:")
        print(f"   1. Acesse a URL de notificação de uma senha")
        print(f"   2. Observe se o alerta aparece apenas quando a posição diminui")
        print(f"   3. Verifique se o número no alerta corresponde à posição real")
        
    except Exception as e:
        print(f"❌ Erro ao testar alertas: {e}")

if __name__ == "__main__":
    test_alerta_fila() 