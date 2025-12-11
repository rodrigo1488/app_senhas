#!/usr/bin/env python3
"""
Script para criar uma senha de teste que será chamada (status C) com pedido
"""

import sqlite3
import os

def create_test_senha_atual():
    """Cria uma senha de teste que será chamada com pedido"""
    db_path = "appsenhas.sqlite"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados {db_path} não encontrado!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Primeiro, vamos finalizar qualquer atendimento atual
        print("🔄 Finalizando atendimentos atuais...")
        cursor.execute("DELETE FROM atendimento_atual WHERE setor_id = 1")
        
        # Criar uma nova senha com pedido
        senha_teste = "N8888"
        pedido_teste = "Pedido de teste para o botão Ver Pedido"
        
        print(f"📝 Criando senha de teste: {senha_teste}")
        print(f"📝 Pedido: {pedido_teste}")
        
        # Inserir a senha
        cursor.execute("""
            INSERT INTO senhas (senha, tipo, setor_id, status, pedido, tem_pedido)
            VALUES (?, 'normal', 1, 'A', ?, 1)
        """, (senha_teste, pedido_teste))
        
        senha_id = cursor.lastrowid
        print(f"✅ Senha criada com ID: {senha_id}")
        
        # Chamar a senha (mudar status para C)
        print("🔄 Chamando a senha...")
        cursor.execute("UPDATE senhas SET status = 'C' WHERE id = ?", (senha_id,))
        
        # Inserir na tabela de atendimento_atual
        cursor.execute("""
            INSERT INTO atendimento_atual (senha_id, setor_id, operador_id)
            VALUES (?, 1, 1)
        """, (senha_id,))
        
        conn.commit()
        
        print(f"✅ Senha chamada com sucesso!")
        print(f"   - ID: {senha_id}")
        print(f"   - Senha: {senha_teste}")
        print(f"   - Status: C (Chamada)")
        print(f"   - Pedido: {pedido_teste}")
        print(f"   - Tem pedido: 1")
        print(f"   - Operador: 1 (RODRIGO)")
        
        # Verificar se foi criada corretamente
        cursor.execute("""
            SELECT s.id, s.senha, s.pedido, s.tem_pedido, s.status, o.nome
            FROM senhas s
            LEFT JOIN atendimento_atual a ON a.senha_id = s.id
            LEFT JOIN operadores o ON a.operador_id = o.id
            WHERE s.id = ?
        """, (senha_id,))
        
        senha = cursor.fetchone()
        if senha:
            print(f"\n✅ Verificação - Senha encontrada:")
            print(f"   - ID: {senha[0]}, Senha: {senha[1]}")
            print(f"   - Pedido: '{senha[2]}'")
            print(f"   - Tem pedido: {senha[3]} (tipo: {type(senha[3])})")
            print(f"   - Status: {senha[4]}")
            print(f"   - Operador: {senha[5]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao criar senha de teste: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🧪 Criando senha de teste chamada com pedido...")
    create_test_senha_atual() 