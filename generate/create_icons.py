#!/usr/bin/env python3
"""
Script para criar ícones básicos para notificações push
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename, text="🔔"):
    """Cria um ícone básico para notificações"""
    try:
        # Criar imagem com fundo branco
        img = Image.new('RGB', (size, size), 'white')
        draw = ImageDraw.Draw(img)
        
        # Adicionar borda
        draw.rectangle([0, 0, size-1, size-1], outline='purple', width=3)
        
        # Adicionar texto centralizado
        try:
            # Tentar usar uma fonte do sistema
            font_size = size // 3
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fallback para fonte padrão
            font = ImageFont.load_default()
        
        # Calcular posição central
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        # Desenhar texto
        draw.text((x, y), text, fill='purple', font=font)
        
        # Salvar imagem
        img.save(filename, 'PNG')
        print(f"Ícone criado: {filename}")
        
    except Exception as e:
        print(f"Erro ao criar ícone {filename}: {e}")

def main():
    """Cria os ícones necessários"""
    print("Criando ícones para notificações push...")
    
    # Criar pasta static se não existir
    if not os.path.exists('static'):
        os.makedirs('static')
        print("Pasta 'static' criada")
    
    # Criar ícones
    create_icon(192, 'static/icon-192x192.png', "🔔")
    create_icon(72, 'static/badge-72x72.png', "📱")
    
    print("Ícones criados com sucesso!")
    print("Agora as notificações push devem funcionar corretamente.")

if __name__ == '__main__':
    main() 