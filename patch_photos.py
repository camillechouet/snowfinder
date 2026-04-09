#!/usr/bin/env python3
"""
SnowFinder — Patch photos vignettes recherche.html
===================================================
Pour chaque station qui a un fichier /img/[slug]-montagne.jpg local,
met à jour le champ "photo" dans le DATA de recherche.html.

USAGE : python patch_photos.py
À lancer depuis la racine du repo SnowFinder.
"""
import re, json, unicodedata, os, sys

def slugify(name):
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = script_dir  # à lancer depuis la racine du repo
recherche_path = os.path.join(root_dir, 'recherche.html')

with open(recherche_path, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'(const DATA = )(\[.*?\])(;)', content, re.DOTALL)
if not m:
    print("ERREUR: const DATA non trouvé dans recherche.html")
    sys.exit(1)

DATA = json.loads(m.group(2))
print(f"✓ {len(DATA)} stations chargées")

updated = 0
for s in DATA:
    slug = slugify(s['name'])
    local_path = os.path.join(root_dir, 'img', f'{slug}-montagne.jpg')
    if os.path.exists(local_path):
        new_photo = f'/img/{slug}-montagne.jpg'
        if s.get('photo') != new_photo:
            s['photo'] = new_photo
            updated += 1
            print(f"  ✅ {s['name']} → {new_photo}")

if updated == 0:
    print("Aucune photo locale trouvée. Vérifie que tu lances le script depuis la racine du repo.")
    sys.exit(0)

new_data_str = json.dumps(DATA, ensure_ascii=False, separators=(',', ':'))
new_content = content[:m.start()] + m.group(1) + new_data_str + m.group(3) + content[m.end():]

with open(recherche_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"\n✓ {updated} photos mises à jour dans recherche.html")
