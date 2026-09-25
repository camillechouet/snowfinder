#!/usr/bin/env python3
"""
SnowFinder — Générateur de sitemap.xml
======================================
Découvre AUTOMATIQUEMENT toutes les pages HTML du site en scannant le disque,
plutôt que de les lister en dur. Un nouveau dossier (ex: domaines/) est donc
inclus sans modifier ce script.

lastmod : basé sur l'historique Git de chaque fichier (date du dernier commit
qui l'a réellement modifié), et non plus sur la date de checkout — sinon
toutes les pages se retrouvent avec la même date à chaque exécution du
générateur, qu'elles aient changé ou non. Une page tout juste créée/modifiée
dans le même run (donc pas encore commit au moment où ce script s'exécute)
reçoit la date du jour en repli.

Déclenchement via GitHub Actions, ou manuellement :
    python3 _scripts/generate_sitemap.py

⚠️ Pour que la date Git soit disponible, le job GitHub Actions qui exécute ce
script doit checkouter l'historique complet du dépôt (fetch-depth: 0), sinon
ce script retombe sur la date du jour pour toutes les pages (comme avant).
"""
import os
import re
import subprocess
from datetime import datetime, timezone

BASE_URL = "https://snowfinder.fr"

# ── Pages à NE PAS indexer ──────────────────────────────────────────
EXCLUDED_FILES = {
    "404.html",           # page d'erreur
    "sidebar.html",       # fragment injecté par sidebar.js
    "mentions-legales.html",  # utile mais sans valeur de référencement
    "grille-tarifaire.html",  # page prospection stations — non-listée volontairement, partagée par lien direct uniquement
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


def load_git_lastmod(root_dir):
    """Lit l'historique Git une seule fois et retourne {chemin_relatif: 'YYYY-MM-DD'},
    la date du commit le plus récent ayant modifié chaque fichier. Retourne un
    dict vide si Git n'est pas disponible ou si l'historique est absente
    (checkout superficiel) — les pages retombent alors sur la date du jour."""
    try:
        out = subprocess.run(
            ["git", "log", "--name-only", "--pretty=format:@@%cd", "--date=short"],
            cwd=root_dir, capture_output=True, text=True, check=True, timeout=120
        ).stdout
    except Exception as e:
        print(f"⚠ Historique Git indisponible ({e}) — repli sur la date du jour pour toutes les pages")
        return {}
    lastmod = {}
    current_date = None
    for line in out.splitlines():
        if line.startswith("@@"):
            current_date = line[2:]
        else:
            path = line.strip()
            if path and current_date and path not in lastmod:
                lastmod[path] = current_date  # première occurrence = commit le plus récent (git log est du plus récent au plus ancien)
    return lastmod


def collect_pages(root_dir):
    """Scanne le disque et retourne la liste des pages à indexer."""
    git_lastmod = load_git_lastmod(root_dir)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n_from_git, n_fallback = 0, 0

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
            if rel in git_lastmod:
                lastmod = git_lastmod[rel]
                n_from_git += 1
            else:
                # Fichier pas (encore) dans l'historique Git : nouveau ou modifié
                # dans ce run, pas encore commit — on met la date du jour.
                lastmod = today
                n_fallback += 1
            prio, freq = classify(rel)
            pages.append({"loc": f"{BASE_URL}/{rel}", "lastmod": lastmod,
                          "priority": prio, "changefreq": freq, "rel": rel})
    print(f"✓ lastmod : {n_from_git} pages depuis l'historique Git, {n_fallback} en repli sur la date du jour (nouvelles/modifiées)")
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
