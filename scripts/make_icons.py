"""Generate all app icons from assets/icon-source.png.

Usage:
    python scripts/make_icons.py [source.png]

- Prefers a transparent-background source; transparent pixels are composited
  onto Lyco crimson (#B62833) before export.
- Android: overwrites mipmap-*/ic_launcher.png (square) and
  ic_launcher_round.png (circular mask) at standard densities.
- iOS: reads mobile/app/ios/.../AppIcon.appiconset/Contents.json and renders
  every listed size, preserving Apple's expected filenames.
- Also writes assets/icon-512.png (Play Store) and assets/icon-1024.png.
"""
import json
import os
import sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    ROOT, "assets", "icon-source.png")
APP = os.path.join(ROOT, "mobile", "app")
CRIMSON = (0xB6, 0x28, 0x33, 255)

DENSITIES = [
    ("mipmap-mdpi", 48),
    ("mipmap-hdpi", 72),
    ("mipmap-xhdpi", 96),
    ("mipmap-xxhdpi", 144),
    ("mipmap-xxxhdpi", 192),
]


def load_base(path):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    side = min(w, h)
    im = im.crop(((w - side) // 2, (h - side) // 2,
                  (w + side) // 2, (h + side) // 2))
    bg = Image.new("RGBA", im.size, CRIMSON)
    return Image.alpha_composite(bg, im).convert("RGB")


def circle(im):
    size = im.size[0]
    mask = Image.new("L", (size, size), 0)
    px = mask.load()
    cx = cy = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            if (x - cx) ** 2 + (y - cy) ** 2 <= cx * cx:
                px[x, y] = 255
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def find_appiconset():
    for root, dirs, _ in os.walk(os.path.join(APP, "ios")):
        if root.endswith(".appiconset"):
            contents = os.path.join(root, "Contents.json")
            if os.path.exists(contents):
                return root, contents
    raise FileNotFoundError("AppIcon.appiconset not found")


def main():
    base = load_base(SRC)
    # --- Android ---
    res = os.path.join(APP, "android", "app", "src", "main", "res")
    for d, px in DENSITIES:
        sq = base.resize((px, px), Image.LANCZOS)
        sq.save(os.path.join(res, d, "ic_launcher.png"))
        circle(base.resize((px, px), Image.LANCZOS)).save(
            os.path.join(res, d, "ic_launcher_round.png"))
        print(f"android {d}: {px}px ok")
    # --- iOS (sizes driven by existing Contents.json) ---
    aset, contents_path = find_appiconset()
    with open(contents_path, encoding="utf-8") as f:
        contents = json.load(f)
    for entry in contents.get("images", []):
        size = entry.get("size", "0x0").split("x")
        scale = int(entry.get("scale", "1x").rstrip("x"))
        try:
            px = int(float(size[0]) * scale)
        except ValueError:
            continue
        if px <= 0:
            continue
        fn = entry.get("filename")
        if not fn:
            fn = (f"Icon-{size[0]}x{size[0]}@{entry.get('scale', '1x')}.png")
            entry["filename"] = fn
        base.resize((px, px), Image.LANCZOS).save(os.path.join(aset, fn))
        print(f"ios {fn}: {px}px ok")
    with open(contents_path, "w", encoding="utf-8") as f:
        json.dump(contents, f, indent=2)
        f.write("\n")
    # --- store listings ---
    assets = os.path.join(ROOT, "assets")
    base.resize((512, 512), Image.LANCZOS).save(
        os.path.join(assets, "icon-512.png"))
    base.resize((1024, 1024), Image.LANCZOS).save(
        os.path.join(assets, "icon-1024.png"))
    print("store icons ok")


if __name__ == "__main__":
    main()
