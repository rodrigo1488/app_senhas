"""Gera ícone, gráfico de recurso e capturas no tamanho exigido pela Play Store."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "graficos"
OUT.mkdir(parents=True, exist_ok=True)

ORANGE = (245, 73, 0, 255)
ORANGE_LIGHT = (255, 137, 4, 255)
NAVY = (18, 11, 30, 255)
WHITE = (255, 255, 255, 255)
CREAM = (255, 247, 237, 255)
DARK = (24, 24, 27, 255)
MUTED = (113, 113, 122, 255)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def icon_512() -> Image.Image:
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((16, 16, 496, 496), radius=110, fill=ORANGE)
    d.rounded_rectangle((118, 150, 394, 390), radius=36, fill=WHITE)
    d.ellipse((96, 236, 148, 288), fill=ORANGE)
    d.ellipse((364, 236, 416, 288), fill=ORANGE)
    d.text((256, 270), "A12", font=font(92), fill=ORANGE, anchor="mm")
    return img


def feature_graphic() -> Image.Image:
    img = Image.new("RGB", (1024, 500), (255, 247, 237))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 1024, 500), fill=ORANGE)
    d.polygon([(620, 0), (1024, 0), (1024, 500), (480, 500)], fill=ORANGE_LIGHT)
    d.text((64, 150), "CompuFlow", font=font(72), fill=WHITE, anchor="ls")
    d.text((64, 240), "Senhas", font=font(72), fill=WHITE, anchor="ls")
    d.text((64, 340), "Fila, TV e atendimento no tablet", font=font(28, bold=False), fill=CREAM, anchor="ls")
    d.rounded_rectangle((740, 110, 970, 390), radius=28, fill=NAVY)
    d.text((855, 200), "PREF", font=font(22), fill=WHITE, anchor="mm")
    d.text((855, 280), "A01", font=font(56), fill=WHITE, anchor="mm")
    return img


def phone_login() -> Image.Image:
    img = Image.new("RGB", (1080, 1920), ORANGE)
    d = ImageDraw.Draw(img)
    rounded_rect(d, (80, 360, 1000, 1560), 48, WHITE)
    d.ellipse((440, 430, 640, 630), fill=ORANGE)
    d.text((540, 720), "CompuFlow", font=font(56), fill=ORANGE, anchor="mm")
    d.text((540, 790), "Entre com o código do seu setor", font=font(28, bold=False), fill=MUTED, anchor="mm")
    rounded_rect(d, (140, 880, 940, 1000), 24, (250, 250, 250, 255))
    d.text((170, 940), "http://senhas.computicket.space", font=font(26, bold=False), fill=DARK, anchor="lm")
    rounded_rect(d, (140, 1040, 520, 1160), 24, CREAM)
    d.text((330, 1100), "Escanear", font=font(28), fill=ORANGE, anchor="mm")
    rounded_rect(d, (560, 1040, 940, 1160), 24, ORANGE)
    d.text((750, 1100), "Conectar", font=font(28), fill=WHITE, anchor="mm")
    rounded_rect(d, (140, 1220, 940, 1340), 24, (250, 250, 250, 255))
    d.text((170, 1280), "Código do setor", font=font(26, bold=False), fill=MUTED, anchor="lm")
    rounded_rect(d, (140, 1400, 940, 1520), 24, ORANGE)
    d.text((540, 1460), "Entrar", font=font(32), fill=WHITE, anchor="mm")
    return img


def phone_tv() -> Image.Image:
    img = Image.new("RGB", (1080, 1920), DARK)
    d = ImageDraw.Draw(img)
    rounded_rect(d, (0, 0, 1080, 420), 0, NAVY)
    d.text((270, 120), "PREFERENCIAL", font=font(28), fill=WHITE, anchor="mm")
    d.text((270, 260), "A01", font=font(88), fill=WHITE, anchor="mm")
    rounded_rect(d, (540, 0, 1080, 420), 0, ORANGE)
    d.text((810, 120), "NORMAL", font=font(28), fill=WHITE, anchor="mm")
    d.text((810, 260), "N24", font=font(88), fill=WHITE, anchor="mm")
    d.rectangle((0, 420, 1080, 1920), fill=(40, 40, 44))
    d.text((540, 1100), "Painel da TV", font=font(48), fill=WHITE, anchor="mm")
    d.text((540, 1180), "Senhas em cima da mídia", font=font(28, bold=False), fill=CREAM, anchor="mm")
    return img


def main() -> None:
    icon_512().save(OUT / "icon-512.png")
    feature_graphic().save(OUT / "feature-1024x500.png")
    phone_login().save(OUT / "phone-1.png")
    phone_tv().save(OUT / "phone-2.png")
    print(f"Gráficos em {OUT}")


if __name__ == "__main__":
    main()
