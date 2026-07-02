"""Erstellt logo.ico aus dem Logo-Design fuer den Desktop-Shortcut."""
import sys
from PIL import Image, ImageDraw


def make_icon(out_path):
    sizes = [256, 64, 48, 32, 16]
    base = Image.new('RGBA', (256, 256), (15, 110, 86, 255))
    d = ImageDraw.Draw(base)

    grid = [(col, row) for row in range(3) for col in range(3)]
    for col, row in grid:
        px = 256 * (0.30 + col * 0.20)
        py = 256 * (0.30 + row * 0.20)
        r = 256 * (0.07 if (row == 1 and col == 1) else 0.045)
        r = max(1.0, r)
        d.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, 255))

    imgs = [base.resize((s, s), Image.LANCZOS) for s in sizes]
    imgs[0].save(out_path, format='ICO',
                 sizes=[(s, s) for s in sizes],
                 append_images=imgs[1:])


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'logo.ico'
    try:
        make_icon(out)
        print(f'Icon erstellt: {out}')
    except Exception as e:
        print(f'Icon-Erstellung fehlgeschlagen (wird uebersprungen): {e}')
