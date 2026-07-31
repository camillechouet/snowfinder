#!/usr/bin/env python3
"""
SnowFinder — Générateur de sitemap.xml
======================================
Découvre AUTOMATIQUEMENT toutes les pages HTML du site en scannant le disque,
plutôt que de les lister en dur. Un nouveau dossier (ex: domaines/) est donc
inclus sans modifier ce script.

Déclenchement via GitHub Actions, ou manuellement :
    python3 _scripts/generate_sitemap.py
"""
import os
import re
from datetime import datetime, timezone

BASE_URL = "https://snowfinder.fr"

# ── Pages à NE PAS indexer ──────────────────────────────────────────
EXCLUDED_FILES = {
    "404.html",           # page d'erreur
    "sidebar.html",       # fragment injecté par sidebar.js
    "mentions-legales.html",  # utile mais sans valeur de référencement
}
EXCLUDED_DIRS = {
    ".git", ".github", "_scripts", "node_modules",
    "img", "images", "assets", "css", "js", ".well-known",
}
# Fragments / partiels : tout fichier commençant par "_" ou "partial"
EXCLUDED_PATTERNS = (
    re.compile(r"^_"),
    re.compile(r"^partial", re.I),
    re.compile(r"\.test\.html$", re.I),
)

# ── Priorités et fréquences par type de page ────────────────────────
# (motif de chemin, priorité, changefreq)
RULES = [
    ("index.html",            "1.0", "daily"),
    ("recherche.html",        "0.9", "daily"),
    ("enneigement.html",      "0.9", "daily"),
    ("domaines.html",         "0.9", "weekly"),
    ("station-du-moment.html","0.8", "weekly"),
    ("comparateur.html",      "0.8", "weekly"),
    ("hebergement.html",      "0.8", "weekly"),
    ("tinder.html",           "0.7", "monthly"),
    ("favoris.html",          "0.5", "monthly"),
]
DIR_RULES = [
    ("domaines/",    "0.8", "weekly"),
    ("stations/",    "0.7", "weekly"),
    ("comparatifs/", "0.6", "monthly"),
]
DEFAULT_PRIORITY, DEFAULT_FREQ = "0.5", "monthly"


def is_excluded(name):
    if name in EXCLUDED_FILES:
        return True
    return any(p.search(name) for p in EXCLUDED_PATTERNS)


def classify(rel_path):
    """Retourne (priority, changefreq) pour un chemin relatif."""
    for pattern, prio, freq in RULES:
        if rel_path == pattern:
            return prio, freq
    for prefix, prio, freq in DIR_RULES:
        if rel_path.startswith(prefix):
            return prio, freq
    return DEFAULT_PRIORITY, DEFAULT_FREQ


def escape_xml(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))


def collect_pages(root_dir):
    """Scanne le disque et retourne la liste des pages à indexer."""
    pages = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Élaguer les dossiers exclus et les dossiers cachés
        dirnames[:] = [d for d in dirnames
                       if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for fname in filenames:
            if not fname.endswith(".html") or is_excluded(fname):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root_dir).replace(os.sep, "/")
            try:
                mtime = os.path.getmtime(full)
                lastmod = datetime.fromtimestamp(mtime, timezone.utc).strftime("%Y-%m-%d")
            except OSError:
                lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            prio, freq = classify(rel)
            pages.append({"loc": f"{BASE_URL}/{rel}", "lastmod": lastmod,
                          "priority": prio, "changefreq": freq, "rel": rel})
    # Tri : priorité décroissante, puis alphabétique
    pages.sort(key=lambda p: (-float(p["priority"]), p["rel"]))
    return pages


def build_xml(pages):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        lines += ["  <url>",
                  f"    <loc>{escape_xml(p['loc'])}</loc>",
                  f"    <lastmod>{p['lastmod']}</lastmod>",
                  f"    <changefreq>{p['changefreq']}</changefreq>",
                  f"    <priority>{p['priority']}</priority>",
                  "  </url>"]
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    pages = collect_pages(root_dir)
    if not pages:
        print("⚠️  Aucune page trouvée — sitemap NON écrit (sécurité).")
        return 1

    xml = build_xml(pages)
    out = os.path.join(root_dir, "sitemap.xml")
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)

    # Récapitulatif par dossier
    counts = {}
    for p in pages:
        folder = p["rel"].split("/")[0] if "/" in p["rel"] else "(racine)"
        counts[folder] = counts.get(folder, 0) + 1

    print(f"✓ sitemap.xml généré — {len(pages)} URLs")
    for folder, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    {folder:<16} {n:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
