#!/usr/bin/env python3
"""
SnowFinder — Générateur de sitemap.xml
=======================================
Lit les stations depuis recherche.html et génère sitemap.xml à la racine.
Appelé automatiquement par GitHub Actions après generate_stations.py.
Ou manuellement : python3 _scripts/generate_sitemap.py
"""
import re, json, unicodedata, os, sys
from datetime import date

def slugify(name):
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
recherche_path = os.path.join(root_dir, 'recherche.html')

with open(recherche_path, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'const DATA = (\[.*?\]);', content, re.DOTALL)
if not m:
    print("ERREUR: const DATA non trouvé dans recherche.html")
    sys.exit(1)

DATA = json.loads(m.group(1))
print(f"✓ {len(DATA)} stations chargées")

today = date.today().isoformat()

MAIN_PAGES = [
    ('https://snowfinder.fr/',                          '1.0', 'daily'),
    ('https://snowfinder.fr/recherche.html',            '0.9', 'weekly'),
    ('https://snowfinder.fr/hebergement.html',          '0.8', 'weekly'),
    ('https://snowfinder.fr/enneigement.html',          '0.8', 'daily'),
    ('https://snowfinder.fr/comparateur.html',          '0.7', 'weekly'),
    ('https://snowfinder.fr/tinder.html',               '0.6', 'monthly'),
    ('https://snowfinder.fr/favoris.html',              '0.5', 'monthly'),
    ('https://snowfinder.fr/station-du-moment.html',    '0.6', 'weekly'),
    ('https://snowfinder.fr/mentions-legales.html',     '0.2', 'yearly'),
]

xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n\n'

for loc, pri, freq in MAIN_PAGES:
    xml += f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>\n\n'

for s in DATA:
    slug = slugify(s['name'])
    loc = f'https://snowfinder.fr/stations/{slug}.html'
    xml += f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n\n'

xml += '</urlset>'

sitemap_path = os.path.join(root_dir, 'sitemap.xml')
with open(sitemap_path, 'w', encoding='utf-8') as f:
    f.write(xml)

total = len(MAIN_PAGES) + len(DATA)
print(f"✓ sitemap.xml généré : {total} URLs ({len(MAIN_PAGES)} pages + {len(DATA)} stations)")
