#!/usr/bin/env python3
"""
Script para testar se o cálculo da posição na fila está correto
"""

import sqlite3
import sys
import os

# Adicionar o diretório atual ao path para importar o app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import DB_PATH

def test_posicao_fila():
    """Testa se o cálculo da posição na fila está correto"""
    print("🧪 Testando cálculo da posição na fila...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Verificar senhas ativas por setor
        cursor.execute('''
            SELECT s.setor_id, st.nome as setor_nome, COUNT(*) as total_senhas
            FROM senhas s
            LEFT JOIN setores st ON s.setor_id = st.id
            WHERE s.status = 'A' AND s.token_unico IS NOT NULL
            GROUP BY s.setor_id, st.nome
            ORDER BY s.setor_id
        ''')
        
        setores = cursor.fetchall()
        print(f"\n1. Setores com senhas ativas:")
        
        for setor_id, setor_nome, total in setores:
            print(f"   Setor {setor_id} ({setor_nome}): {total} senhas")
            
            # 2. Calcular posição para cada senha do setor
            cursor.execute('''
                SELECT s.id, s.senha, s.token_unico, s.status
                FROM senhas s
                WHERE s.setor_id = ? AND s.status = 'A' AND s.token_unico IS NOT NULL
                ORDER BY s.id ASC
            ''', (setor_id,))
            
            senhas_setor = cursor.fetchall()
            
            print(f"\n   Posições no setor {setor_nome}:")
            for senha_id, senha_numero, token, status in senhas_setor:
                # Calcular posição (quantas senhas estão na frente)
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM senhas 
                    WHERE setor_id = ? AND status = 'A' AND id < ?
                ''', (setor_id, senha_id))
                
                posicao = cursor.fetchone()[0]
                
                # Verificar se deveria receber alerta
                alerta = "✅ ALERTA" if 1 <= posicao <= 3 else "⏳ Aguardando"
                
                print(f"      Senha {senha_numero} (ID: {senha_id}): Posição {posicao} - {alerta}")
        
        # 3. Verificar se há senhas sem token
        cursor.execute('''
            SELECT COUNT(*) 
            FROM senhas 
            WHERE status = 'A' AND token_unico IS NULL
        ''')
        
        senhas_sem_token = cursor.fetchone()[0]
        if senhas_sem_token > 0:
            print(f"\n⚠️  ATENÇÃO: {senhas_sem_token} senhas ativas sem token único!")
        
        # 4. Verificar se há senhas duplicadas
        cursor.execute('''
            SELECT token_unico, COUNT(*) as total
            FROM senhas 
            WHERE status = 'A' AND token_unico IS NOT NULL
            GROUP BY token_unico
            HAVING COUNT(*) > 1
        ''')
        
        tokens_duplicados = cursor.fetchall()
        if tokens_duplicados:
            print(f"\n⚠️  ATENÇÃO: Tokens duplicados encontrados!")
            for token, total in tokens_duplicados:
                print(f"   Token {token[:8]}...: {total} ocorrências")
        
        conn.close()
        
        print(f"\n🎯 Resumo:")
        print(f"   - Setores com senhas ativas: {len(setores)}")
        print(f"   - Senhas sem token: {senhas_sem_token}")
        print(f"   - Tokens duplicados: {len(tokens_duplicados)}")
        
        print(f"\n💡 Como funciona:")
        print(f"   - Posição 0: Próximo a ser chamado")
        print(f"   - Posição 1-3: Deve receber alerta de proximidade")
        print(f"   - Posição 4+: Aguardando na fila")
        
    except Exception as e:
        print(f"❌ Erro ao testar posição na fila: {e}")

if __name__ == "__main__":
    test_posicao_fila() 