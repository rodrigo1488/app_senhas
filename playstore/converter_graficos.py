import os
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS = Path(os.environ["PLAYSTORE_ASSETS"]) if os.environ.get("PLAYSTORE_ASSETS") else SCRIPT_DIR / "assets"
OUT = SCRIPT_DIR / "graficos"
OUT.mkdir(parents=True, exist_ok=True)

if not ASSETS.is_dir():
    raise SystemExit(
        f"Pasta de origem não encontrada: {ASSETS}\n"
        "Coloque as imagens em playstore/assets ou defina PLAYSTORE_ASSETS."
    )


def fit(src: Path, size: tuple[int, int], dest: Path, rgb: bool = False) -> None:
    im = Image.open(src).convert("RGBA")
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    nw, nh = int(im.width * scale), int(im.height * scale)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    im = im.crop((left, top, left + tw, top + th))
    if rgb:
        im = im.convert("RGB")
    im.save(dest, "PNG")
    print(dest.name, im.size)


fit(ASSETS / "play-icon-compuflow.jpg", (512, 512), OUT / "icon-512.png")
fit(ASSETS / "play-feature-compuflow.jpg", (1024, 500), OUT / "feature-1024x500.png")
fit(ASSETS / "play-phone-login.jpg", (1080, 1920), OUT / "phone-1.png", rgb=True)
fit(ASSETS / "play-phone-tv.jpg", (1080, 1920), OUT / "phone-2.png", rgb=True)
