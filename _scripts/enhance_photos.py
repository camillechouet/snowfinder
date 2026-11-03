#!/usr/bin/env python3
"""
SnowFinder — Amélioration automatique des photos de stations (img/<station>1.jpg, 2, 3)
======================================================================================
Applique à chaque photo le même traitement doux que celui des épingles Pinterest :
contraste et lumière corrigés selon la photo, couleurs un peu plus vives, netteté, léger relief.

SÉCURITÉS
  · Chaque photo n'est traitée QU'UNE FOIS : son nom est noté dans img/enhanced.json
    (un second passage les aurait trop poussées). Le script d'épingles ne les retraite pas non plus.
  · Par défaut, seules les photos AJOUTÉES au dépôt depuis --since (défaut 2026-10-29, début des photos
    libres Wikimedia) sont traitées : tes photos plus anciennes (perso, offices de tourisme) restent intactes.
  · --names a.jpg,b.jpg : traite ces fichiers précis (même s'ils sont antérieurs à --since).
  · --dry-run : liste ce qui serait fait sans rien écrire.
Les originaux restent dans l'historique GitHub (on peut toujours revenir en arrière).

Usage : python3 _scripts/enhance_photos.py [--since 2026-10-29] [--names x.jpg,y.jpg] [--dry-run]
"""
import os, re, sys, json, argparse, subprocess

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

ROOT = os.environ.get("SF_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "img")
DONE = os.path.join(IMG, "enhanced.json")
NAME_RE = re.compile(r"^[a-z0-9]+[123]\.(jpe?g)$", re.I)     # nomstation1.jpg / 2 / 3


def enhance(img):
    """Même traitement que generate_pinterest_feed.enhance, avec des rayons proportionnels à la taille."""
    k = max(img.width, 1) / 1000.0
    try:
        img = ImageOps.autocontrast(img, cutoff=(0.5, 0.3))
    except Exception:  # noqa: BLE001
        pass
    lum = ImageStat.Stat(img.convert("L")).mean[0]
    if lum < 120:
        g = min(1.0 + (120 - lum) / 220.0, 1.35)
        img = img.point([min(255, int(255 * ((i / 255.0) ** (1.0 / g)))) for i in range(256)] * 3)
    elif lum > 190:
        g = min(1.0 + (lum - 190) / 160.0, 1.25)
        img = img.point([min(255, int(255 * ((i / 255.0) ** g))) for i in range(256)] * 3)
    img = ImageEnhance.Color(img).enhance(1.18)
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = img.filter(ImageFilter.UnsharpMask(radius=45 * k, percent=22, threshold=0))
    img = img.filter(ImageFilter.UnsharpMask(radius=min(1.4 * k, 2.2), percent=70, threshold=2))
    return img


def load_done():
    try:
        with open(DONE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:  # noqa: BLE001
        return set()


def added_since(since):
    """Fichiers de img/ AJOUTÉS au dépôt depuis la date donnée (historique git complet nécessaire)."""
    out = subprocess.run(["git", "log", f"--since={since}", "--diff-filter=A", "--name-only", "--pretty=format:", "--", "img/"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return {os.path.basename(l.strip()) for l in out.splitlines() if l.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-10-29")
    ap.add_argument("--names", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    done = load_done()
    if a.names.strip():
        wanted = {n.strip() for n in a.names.split(",") if n.strip()}
    else:
        wanted = added_since(a.since)
    files = sorted(f for f in os.listdir(IMG) if NAME_RE.match(f) and f in wanted and f not in done)
    print(f"ℹ {len(files)} photo(s) à améliorer ({len(done)} déjà faites).")
    n = 0
    for f in files:
        p = os.path.join(IMG, f)
        if a.dry_run:
            print("   (essai)", f)
            continue
        try:
            im = Image.open(p).convert("RGB")
            before = os.path.getsize(p)
            im = enhance(im)
            im.save(p, "JPEG", quality=80, optimize=True, progressive=True)
            done.add(f)
            n += 1
            print(f"   ✓ {f} ({before // 1024} Ko -> {os.path.getsize(p) // 1024} Ko)")
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠ {f} : {e!r}")
    if n:
        with open(DONE, "w", encoding="utf-8") as fh:
            json.dump(sorted(done), fh, indent=1)
    print(f"✓ {n} photo(s) améliorée(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
