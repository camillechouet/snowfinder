#!/usr/bin/env python3
"""
SnowFinder — Générateur de sitemap.xml
Met à jour sitemap.xml avec toutes les URLs (pages principales + 226 stations)
"""
import re, json, unicodedata, os
from datetime import date

def slugify(name):
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)

with open(os.path.join(root_dir, 'recherche.html'), 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'const DATA = (\[.*?\]);', content, re.DOTALL)
DATA = json.loads(m.group(1))

today = date.today().strftime("%Y-%m-%d")
domain = "https://snowfinder.fr"

pages_main = [
    {"url": "/",                       "priority": "1.0", "changefreq": "daily"},
    {"url": "/recherche.html",         "priority": "0.9", "changefreq": "weekly"},
    {"url": "/hebergement.html",       "priority": "0.8", "changefreq": "weekly"},
    {"url": "/enneigement.html",       "priority": "0.8", "changefreq": "daily"},
    {"url": "/comparateur.html",       "priority": "0.7", "changefreq": "weekly"},
    {"url": "/tinder.html",            "priority": "0.6", "changefreq": "monthly"},
    {"url": "/favoris.html",           "priority": "0.5", "changefreq": "monthly"},
    {"url": "/station-du-moment.html", "priority": "0.6", "changefreq": "weekly"},
    {"url": "/mentions-legales.html",  "priority": "0.2", "changefreq": "yearly"},
]

sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n\n'

for p in pages_main:
    sitemap += f'  <url>\n    <loc>{domain}{p["url"]}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>{p["changefreq"]}</changefreq>\n    <priority>{p["priority"]}</priority>\n  </url>\n\n'

for s in DATA:
    slug = slugify(s['name'])
    sitemap += f'  <url>\n    <loc>{domain}/stations/{slug}.html</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>\n\n'

sitemap += '</urlset>'

with open(os.path.join(root_dir, 'sitemap.xml'), 'w', encoding='utf-8') as f:
    f.write(sitemap)

total = len(pages_main) + len(DATA)
print(f"✓ sitemap.xml mis à jour — {total} URLs")
