#!/usr/bin/env python3
"""
add_offres.py — SnowFinder : branche l'encart « Offres & bons plans » sur toutes les pages concernées.

Ajoute (une seule fois, sans doublon) la ligne <script src="/offres.js" defer></script> juste avant </body> sur :
  stations/*.html, articles/*.html, comparatifs/*.html  (+ leurs copies anglaises dans en/)
sauf les pages de liste (toutes-les-actus, tous-les-comparatifs).
Lancé automatiquement par le workflow « Traduction anglaise » (chaque nuit, à chaque nouvelle page) :
une page générée plus tard reçoit donc l'encart toute seule.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = '<script src="/offres.js" defer></script>'
FOLDERS = ["stations", "articles", "comparatifs"]
SKIP = {"toutes-les-actus.html", "tous-les-comparatifs.html"}


def patch(p: Path) -> bool:
    try:
        s = p.read_text(encoding="utf-8")
    except Exception:
        return False
    if "/offres.js" in s or "</body>" not in s:
        return False
    i = s.rfind("</body>")
    p.write_text(s[:i] + TAG + "\n" + s[i:], encoding="utf-8")
    return True


def main() -> None:
    n = 0
    for base in (ROOT, ROOT / "en"):
        for f in FOLDERS:
            d = base / f
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.html")):
                if p.name in SKIP:
                    continue
                if patch(p):
                    n += 1
    print(f"✅ Encart offres : {n} page(s) mise(s) à jour")


if __name__ == "__main__":
    main()
