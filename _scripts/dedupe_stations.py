#!/usr/bin/env python3
"""
dedupe_stations.py — SnowFinder
================================
Aligne tous les blocs JS de données stations sur la source de vérité
qui est `const DATA = [...]` dans recherche.html (226 stations propres,
déjà dédoublonnées).

PROBLÈME DÉTECTÉ
----------------
Le site contient 4 blocs JS de données stations qui ont divergé :

  Fichier         Bloc            Avant    Après
  --------------- --------------- -------- -------
  recherche.html  DATA              226     226   ← source de vérité
  recherche.html  IA_STATIONS       254     226
  recherche.html  FAV_STATIONS      254     226
  index.html      DATA              254     226

Les 28 doublons identifiés sont :
  - 10 doublons exacts (même nom, ex: Châtel ID 21 et 200)
  - 18 doublons cachés sous variantes orthographiques :
    Vars / Vars-Les Claux, Barèges / La Mongie-Barèges,
    Le Lioran / Le Lioran-Super Lioran, Chamonix / Chamonix-Argentière,
    Guzet / Guzet-Neige, Ceillac-en-Queyras / Ceillac, etc.

PRINCIPE DE LA FUSION
---------------------
On garde les IDs originaux (stables pour les favoris localStorage).
On supprime les IDs qui sont absents du DATA principal.
On ne touche pas au schéma de chaque bloc (IA/FAV ne récupèrent pas
les champs lourds desc_long/photo/snow qu'ils n'utilisent pas).

Usage :
    python3 dedupe_stations.py                # patche les 2 fichiers
    python3 dedupe_stations.py --dry-run      # rapport sans écriture
    python3 dedupe_stations.py --root .       # chemin du site
"""

import argparse
import json
import re
import sys
from pathlib import Path


TARGETS = [
    ("recherche.html", "IA_STATIONS"),
    ("recherche.html", "FAV_STATIONS"),
    ("index.html",     "DATA"),
]

SOURCE_FILE = "recherche.html"
SOURCE_CONST = "DATA"

COUNTER_REPLACEMENTS = [
    (r"\+250</span>", "+226</span>"),
]


def find_js_array(content, const_name):
    m = re.search(rf"const\s+{re.escape(const_name)}\s*=\s*\[", content)
    if not m:
        return None
    arr_start = m.end() - 1
    depth = 0; in_str = False; esc = False; i = arr_start
    while i < len(content):
        c = content[i]
        if in_str:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == '"': in_str = False
        else:
            if c == '"': in_str = True
            elif c == '[': depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    return arr_start, i + 1, content[arr_start:i + 1]
        i += 1
    return None


def load_source_of_truth(root):
    src = (root / SOURCE_FILE).read_text(encoding='utf-8')
    res = find_js_array(src, SOURCE_CONST)
    if res is None:
        raise RuntimeError(f"const {SOURCE_CONST} introuvable dans {SOURCE_FILE}")
    _, _, raw = res
    return json.loads(raw)


def align_block(raw_json, valid_ids):
    stations = json.loads(raw_json)
    before = len(stations)
    removed_items = [s for s in stations if s.get("id") not in valid_ids]
    kept = [s for s in stations if s.get("id") in valid_ids]
    new_json = json.dumps(kept, ensure_ascii=False, separators=(',', ':'))
    return new_json, before - len(kept), len(kept), removed_items


def patch_file(filepath, const_names, valid_ids, dry_run=False):
    content = filepath.read_text(encoding='utf-8')
    original_size = len(content)
    report = {"file": filepath.name, "blocks": [], "counters_replaced": 0,
              "removed_stations": []}

    block_positions = []
    for const_name in const_names:
        res = find_js_array(content, const_name)
        if res is None:
            report["blocks"].append({"const": const_name, "status": "NOT_FOUND"})
            continue
        start, end, raw = res
        block_positions.append((start, end, raw, const_name))

    block_positions.sort(key=lambda x: -x[0])

    for start, end, raw, const_name in block_positions:
        is_source = (filepath.name == SOURCE_FILE and const_name == SOURCE_CONST)
        if is_source:
            report["blocks"].append({"const": const_name, "status": "SOURCE (intact)",
                                     "removed": 0, "remaining": len(json.loads(raw))})
            continue

        new_json, removed, kept, removed_items = align_block(raw, valid_ids)
        content = content[:start] + new_json + content[end:]
        report["blocks"].append({
            "const": const_name, "status": "OK",
            "removed": removed, "remaining": kept,
        })
        if not report["removed_stations"] and removed_items:
            report["removed_stations"] = [
                {"id": s.get("id"), "name": s.get("name"), "region": s.get("region")}
                for s in sorted(removed_items, key=lambda x: x.get("id", 0))
            ]

    for pattern, replacement in COUNTER_REPLACEMENTS:
        content, n = re.subn(pattern, replacement, content)
        report["counters_replaced"] += n

    report["size_before"] = original_size
    report["size_after"] = len(content)
    report["delta"] = len(content) - original_size

    if not dry_run:
        filepath.write_text(content, encoding='utf-8')
        report["written"] = True
    else:
        report["written"] = False

    return report


def print_report(reports):
    print("\n" + "=" * 70)
    print("RAPPORT")
    print("=" * 70)
    all_removed = None
    for r in reports:
        print(f"\n📄 {r['file']}")
        for b in r["blocks"]:
            if b["status"] == "NOT_FOUND":
                print(f"   ⚠️  const {b['const']:<14} : INTROUVABLE")
            elif b["status"].startswith("SOURCE"):
                print(f"   ★ const {b['const']:<14} : SOURCE DE VÉRITÉ — {b['remaining']} stations (non modifié)")
            else:
                print(f"   ✓ const {b['const']:<14} : -{b['removed']} stations (reste {b['remaining']})")
        if r["counters_replaced"]:
            print(f"   ✓ Compteurs textuels remplacés : {r['counters_replaced']}")
        sign = "+" if r["delta"] >= 0 else ""
        print(f"   Taille : {r['size_before']:,} → {r['size_after']:,} octets ({sign}{r['delta']:,})")
        if not r["written"]:
            print(f"   ⚠️  DRY-RUN : aucun fichier écrit")
        if r["removed_stations"] and all_removed is None:
            all_removed = r["removed_stations"]

    if all_removed:
        print(f"\n{'=' * 70}")
        print(f"DOUBLONS SUPPRIMÉS ({len(all_removed)})")
        print('=' * 70)
        for st in all_removed:
            print(f"   ID {st['id']:3d} | {st['name']:<35} | {st['region']}")


def main():
    parser = argparse.ArgumentParser(
        description="Aligne tous les blocs JS de données sur DATA de recherche.html"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="N'écrit aucun fichier, affiche le rapport")
    parser.add_argument("--root", default=".",
                        help="Racine du site (défaut: répertoire courant)")
    args = parser.parse_args()

    root = Path(args.root)
    src_path = root / SOURCE_FILE
    if not src_path.exists():
        print(f"❌ Source introuvable : {src_path}")
        sys.exit(1)

    print(f"Chargement de la source de vérité : {SOURCE_FILE} → const {SOURCE_CONST}")
    truth = load_source_of_truth(root)
    valid_ids = set(s["id"] for s in truth)
    print(f"  → {len(truth)} stations valides (IDs min/max : {min(valid_ids)} / {max(valid_ids)})")

    by_file = {}
    for fname, const_name in TARGETS:
        by_file.setdefault(fname, []).append(const_name)
    by_file.setdefault(SOURCE_FILE, []).insert(0, SOURCE_CONST)

    reports = []
    for fname, consts in by_file.items():
        fpath = root / fname
        if not fpath.exists():
            print(f"⚠️  Fichier introuvable : {fpath}")
            continue
        report = patch_file(fpath, consts, valid_ids, dry_run=args.dry_run)
        reports.append(report)

    print_report(reports)
    print()


if __name__ == "__main__":
    main()
