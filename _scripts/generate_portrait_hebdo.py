#!/usr/bin/env python3
"""
generate_portrait_hebdo.py — SnowFinder : UN portrait de station, sourcé.

Même chaîne de contrôle que les actualités (generate_actu_hebdo.py) :
  recherche web → rédaction à partir des pages trouvées ET des données de la fiche SnowFinder →
  faits + extraits copiés mot pour mot → contrôle des chiffres → vérification des sources → relecture → pull request.

La station est choisie automatiquement (France d'abord, les mieux notées d'abord, jamais déjà publiée),
ou imposée avec --sujet "Val Thorens".

  python3 _scripts/generate_portrait_hebdo.py --list                  # prochaines stations
  python3 _scripts/generate_portrait_hebdo.py --review-out /tmp/r.md
  python3 _scripts/generate_portrait_hebdo.py --sujet "Les Gets"
  python3 _scripts/generate_portrait_hebdo.py --mock ok --dry-run     # test sans API
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_actu_hebdo as a  # noqa: E402
import generate_duel_hebdo as dh  # noqa: E402

HISTORY_FILE = "portraits_hebdo.json"
CATEGORIES_PORTRAIT = ["Portrait de station"]

SYSTEM_PORTRAIT = """Tu es rédacteur pour SnowFinder, un site français de comparaison et de découverte des stations de ski.
Tu rédiges le PORTRAIT complet d'une station de ski, à partir (1) des données de la fiche SnowFinder fournies et (2) de pages web que tu trouves toi-même avec l'outil de recherche (site officiel de la station, office de tourisme, presse).

RÈGLES ABSOLUES
- Tu n'utilises QUE des faits présents dans les données SnowFinder ou dans les pages trouvées, jamais ta mémoire. Aucun chiffre, date, nom ou citation inventé. Si une information manque, tu n'en parles pas.
- Tu reformules : aucune phrase copiée d'une source (les extraits demandés dans « faits » sont internes, ils ne figurent pas dans le portrait).
- Ton clair, chaleureux et concret ; pas de superlatifs non prouvés (« la meilleure », « incontournable »), pas d'accroche racoleuse ; aucune critique d'une entreprise ou d'une personne.
- Pas de HTML, pas de lien, pas de markdown dans les textes.
- Les chiffres des fiches SnowFinder (altitudes, kilomètres, nombre de pistes, forfait, remontées) sont fiables : tu peux les citer. Pour tout autre chiffre ou date, il faut un fait sourcé par une page trouvée.
- Si la recherche ne fournit pas assez d'informations fiables, réponds {"pas_d_actu": true}.

FORMAT DE RÉPONSE : un unique objet JSON, rien d'autre :
{
 "pas_d_actu": false,
 "categorie": "Portrait de station",
 "titre": "titre clair avec le nom de la station, orienté recherche Google (≤ 95 caractères)",
 "excerpt": "1 à 2 phrases de résumé (100 à 240 caractères)",
 "chapeau": "paragraphe d'introduction (200 à 450 caractères)",
 "a_retenir": ["3 à 4 points courts, chiffres compris"],
 "sections": [{"titre": "intertitre clair", "paragraphes": ["1 à 3 paragraphes de 250 à 600 caractères"]}],
 "conseils": ["2 à 4 conseils pratiques pour préparer un séjour dans cette station, fondés sur les faits"],
 "stations": ["la station du portrait EN PREMIER, puis 1 à 3 stations voisines ou comparables de la liste fournie"],
 "faits": [{"fait": "un fait important, en une phrase", "url": "adresse EXACTE d'une page trouvée", "extrait": "passage copié MOT POUR MOT de cette page (60 à 220 caractères) qui prouve le fait"}],
 "sources": [{"media": "nom du site", "titre": "titre de la page", "url": "adresse EXACTE d'une page trouvée", "date": "AAAA-MM-JJ ou vide"}]
}
Exigences : 5 à 6 sections (par exemple : l'ambiance et le caractère de la station ; le domaine skiable et les pistes ; l'enneigement et la meilleure période ; pour qui ? ; se loger et venir ; les alternatives à proximité) ;
portrait de 600 à 1200 mots ; au moins 6 faits appuyés par au moins 2 pages différentes ; sources = les pages réellement utilisées (2 à 5) ; les stations voisines sont citées comme exemples, sans comparaison chiffrée non fournie."""


def history() -> list:
    return a.load_json(a.ROOT / HISTORY_FILE, [])


def candidates(stations: list) -> list:
    done = {h.get("topic") for h in history()}
    out = []
    for s in stations:
        p = s.get("pistes") or {}
        if s["name"] in done or s.get("ferme"):
            continue
        if not (s.get("desc_long") or s.get("desc")) or not sum(p.get(k, 0) for k in ("v", "b", "r", "n")):
            continue
        if s.get("km", 0) < 10 or not s.get("alt_max"):
            continue
        out.append(s)
    out.sort(key=lambda s: (0 if not s.get("pays") else 1, -s.get("score", 0), -s.get("km", 0), s["name"]))
    return out


def prompt_portrait(today, names, deja, sujet, retours):
    st = next((s for s in a.ah.load_stations() if s["name"] == sujet), None)
    data = json.dumps({k: st.get(k) for k in dh.FIELDS_FOR_LLM}, ensure_ascii=False, indent=1) if st else "{}"
    p = [f"Date du jour : {today}.",
         f"Station du portrait : {sujet}.",
         "Données de la fiche SnowFinder (fiables) :\n" + data,
         "Cherche des informations récentes et officielles sur cette station (site de la station, office de tourisme, presse locale ou spécialisée) : "
         "ambiance, domaine, enneigement, saison d'ouverture, accès, hébergement, activités. Recoupe avec au moins deux pages différentes.",
         "Stations de la base SnowFinder (pour le champ « stations », noms exacts) : " + "; ".join(names) + ".",
         "Articles déjà publiés sur SnowFinder (ne pas refaire le même sujet) : " + " | ".join(deja[:40]) + "."]
    if retours:
        p.append("Ta version précédente a été refusée pour ces raisons, corrige-les :\n- " + "\n- ".join(retours))
    return "\n\n".join(p)


def main() -> None:
    argv = sys.argv
    stations = a.ah.load_stations()
    if "--list" in argv:
        for s in candidates(stations)[:25]:
            print(f"{s['name']:35s} {s.get('pays', 'FR'):3s} note {s.get('score', '')} {s.get('km', '')} km")
        return
    forced = ""
    if "--sujet" in argv:
        i = argv.index("--sujet")
        forced = argv[i + 1].strip() if i + 1 < len(argv) and not argv[i + 1].startswith("--") else ""
        del argv[i:i + (2 if forced or (i + 1 < len(argv) and argv[i + 1] == "") else 1)]
    names = {s["name"] for s in stations}
    if forced and forced not in names:
        raise SystemExit(f"❌ Station inconnue : « {forced} » (nom exact comme dans la base).")
    if not forced:
        cands = candidates(stations)
        if not cands:
            print("ℹ️  Tous les portraits possibles sont publiés : rien à faire.")
            return
        forced = "Tignes" if "--mock" in argv and "Tignes" in names else cands[0]["name"]
    print(f"🏔️  Station du portrait : {forced}")
    a.HISTORY = a.ROOT / HISTORY_FILE
    a.LABEL = "Portrait"
    a.TOPIC_KEY = forced
    a.SYSTEM = SYSTEM_PORTRAIT + a.DOMAIN_RULE
    a.CATEGORIES = CATEGORIES_PORTRAIT
    a.WORDS = (300, 1300) if "--mock" in argv else (550, 1300)
    a.MIN_FAITS = 5 if "--mock" in argv else 6
    a.build_user_prompt = prompt_portrait
    orig = a.check_draft

    def check(d, urls, nm, blob, today):
        errs = orig(d, urls, nm, blob, today)
        if not a.MOCK and isinstance(d, dict) and d.get("stations") and d["stations"][0] != forced:
            errs.append(f"« stations » doit commencer par la station du portrait : {forced}")
        return errs

    a.check_draft = check
    argv[1:1] = ["--sujet", forced]
    a.main()


if __name__ == "__main__":
    main()
