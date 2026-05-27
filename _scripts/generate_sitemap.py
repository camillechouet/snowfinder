#!/usr/bin/env python3
"""
generate_sitemap.py — SnowFinder
─────────────────────────────────
Régénère sitemap.xml à partir de la source de vérité unique : la liste
IA_STATIONS dans recherche.html.

Utilisation depuis la racine du repo :
    python3 _scripts/generate_sitemap.py

Le script :
  1. Lit les 226 stations depuis recherche.html
  2. Génère le slug de chaque station avec la fonction canonique
  3. Vérifie que le fichier /stations/{slug}.html existe vraiment
  4. Écrit sitemap.xml avec les pages principales + toutes les stations existantes
  5. Affiche un rapport (stations OK / stations manquantes côté fichiers)
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://snowfinder.fr"
REPO_ROOT = Path(__file__).resolve().parent.parent  # _scripts/ → racine
RECHERCHE_HTML = REPO_ROOT / "recherche.html"
STATIONS_DIR = REPO_ROOT / "stations"
SITEMAP_OUT = REPO_ROOT / "sitemap.xml"

# Pages principales avec leurs métadonnées SEO
MAIN_PAGES = [
    ("/",                       "daily",   "1.0"),
    ("/recherche.html",         "weekly",  "0.9"),
    ("/hebergement.html",       "weekly",  "0.8"),
    ("/enneigement.html",       "daily",   "0.8"),
    ("/comparateur.html",       "weekly",  "0.7"),
    ("/tinder.html",            "weekly",  "0.7"),
    ("/favoris.html",           "weekly",  "0.5"),
    ("/station-du-moment.html", "weekly",  "0.6"),
    ("/mentions-legales.html",  "yearly",  "0.2"),
]

# ── Fonction slug canonique (UNE SEULE source de vérité) ─────────────────────

def slugify(name: str) -> str:
    """
    Convertit un nom de station en slug.

    Règles (alignées sur les fichiers déjà déployés) :
      - minuscules
      - accents supprimés (é → e, à → a, etc.)
      - apostrophes et espaces → tiret
      - tout caractère non alphanumérique restant supprimé
      - tirets multiples fusionnés, tirets en début/fin supprimés

    Exemples :
      "Val d'Isère"        → "val-d-isere"
      "Sixt-Fer-à-Cheval"  → "sixt-fer-a-cheval"
      "L'Audibergue"       → "l-audibergue"
    """
    s = name.lower()
    # Suppression des accents (NFD = décomposition canonique)
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    # Apostrophes (droite et courbe) et espaces → tiret
    s = re.sub(r"['\u2019\s]+", "-", s)
    # Reste : on garde seulement alphanumérique + tiret
    s = re.sub(r"[^a-z0-9-]", "", s)
    # Fusion des tirets multiples + nettoyage
    s = re.sub(r"-+", "-", s).strip("-")
    return s


# ── Extraction des stations depuis recherche.html ────────────────────────────

def load_stations() -> list[dict]:
    """Lit l'array IA_STATIONS dans recherche.html et le parse en JSON."""
    if not RECHERCHE_HTML.exists():
        sys.exit(f"❌ Fichier introuvable : {RECHERCHE_HTML}")

    content = RECHERCHE_HTML.read_text(encoding="utf-8")
    m = re.search(r"const\s+IA_STATIONS\s*=\s*(\[.*?\]);", content, re.DOTALL)
    if not m:
        sys.exit("❌ Impossible de trouver IA_STATIONS dans recherche.html")

    try:
        stations = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        sys.exit(f"❌ JSON invalide dans IA_STATIONS : {e}")

    if not isinstance(stations, list) or not stations:
        sys.exit("❌ IA_STATIONS vide ou mal formé")

    return stations


# ── Construction du sitemap ──────────────────────────────────────────────────

def url_entry(path: str, lastmod: str, changefreq: str, priority: str) -> str:
    return (
        "  <url>\n"
        f"    <loc>{BASE_URL}{path}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>\n"
    )


def build_sitemap(stations: list[dict]) -> tuple[str, list[str], list[str]]:
    """
    Construit le contenu du sitemap.

    Retourne : (xml, slugs_ok, slugs_manquants)
      - slugs_ok : stations dont le fichier HTML existe et sont incluses
      - slugs_manquants : stations dont le fichier HTML est introuvable
    """
    today = date.today().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
        "",
    ]

    # Pages principales
    for path, changefreq, priority in MAIN_PAGES:
        lines.append(url_entry(path, today, changefreq, priority))

    # Pages stations (par ordre alphabétique du slug pour la stabilité du diff)
    slugs_ok: list[str] = []
    slugs_manquants: list[str] = []

    entries = []
    for s in stations:
        slug = slugify(s["name"])
        html_path = STATIONS_DIR / f"{slug}.html"
        if not html_path.exists():
            slugs_manquants.append(f"{s['name']} (slug attendu : {slug})")
            continue
        slugs_ok.append(slug)
        entries.append((slug, s.get("score", 0)))

    # Tri : score décroissant puis slug alpha (les meilleures stations en haut
    # ne change rien pour Google mais aide à la lisibilité du fichier)
    entries.sort(key=lambda e: (-e[1], e[0]))

    for slug, _score in entries:
        lines.append(url_entry(f"/stations/{slug}.html", today, "weekly", "0.8"))

    lines.append("</urlset>")
    lines.append("")  # newline final

    return "\n".join(lines), slugs_ok, slugs_manquants


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"📍 Racine du repo  : {REPO_ROOT}")
    print(f"📄 Lecture         : {RECHERCHE_HTML.relative_to(REPO_ROOT)}")
    print(f"📁 Dossier stations: {STATIONS_DIR.relative_to(REPO_ROOT)}")
    print(f"📝 Sortie          : {SITEMAP_OUT.relative_to(REPO_ROOT)}")
    print()

    stations = load_stations()
    print(f"✓ {len(stations)} stations trouvées dans IA_STATIONS")

    if not STATIONS_DIR.exists():
        sys.exit(f"❌ Dossier introuvable : {STATIONS_DIR}")

    xml, slugs_ok, slugs_manquants = build_sitemap(stations)
    SITEMAP_OUT.write_text(xml, encoding="utf-8")

    print(f"✓ {len(slugs_ok)} pages stations ajoutées au sitemap")
    print(f"✓ {len(MAIN_PAGES)} pages principales ajoutées")
    print(f"✓ Total : {len(slugs_ok) + len(MAIN_PAGES)} URLs dans {SITEMAP_OUT.name}")

    if slugs_manquants:
        print()
        print(f"⚠️  {len(slugs_manquants)} stations sans fichier HTML "
              f"(elles ne sont PAS dans le sitemap) :")
        for s in slugs_manquants:
            print(f"   - {s}")
        print()
        print("   → Génère leur page station puis relance le script.")
    else:
        print()
        print("🎉 Toutes les stations ont leur fichier HTML. Sitemap complet.")


if __name__ == "__main__":
    main()
