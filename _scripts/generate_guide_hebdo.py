#!/usr/bin/env python3
"""
generate_guide_hebdo.py — SnowFinder : UN guide pratique / saisonnier, sourcé.

Même chaîne de contrôle que les actualités (generate_actu_hebdo.py) :
  recherche web → rédaction à partir des pages trouvées → faits + extraits copiés mot pour mot →
  contrôle des chiffres → vérification des extraits dans les pages sources → relecture → pull request.

Différence : le sujet vient d'un calendrier de guides (« Ski à Noël », « Première fois au ski »…),
choisi selon le mois en cours et jamais déjà publié. Le guide est plus long et reste utile toute la saison.

Utilisation :
  python3 _scripts/generate_guide_hebdo.py --list                       # sujets du calendrier
  python3 _scripts/generate_guide_hebdo.py --review-out /tmp/r.md       # sujet du mois
  python3 _scripts/generate_guide_hebdo.py --sujet "Ski à Pâques 2027"  # thème libre
  python3 _scripts/generate_guide_hebdo.py --mock ok --dry-run          # test sans API
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_actu_hebdo as a  # noqa: E402

# (clé, mois où le sujet est pertinent, sujet détaillé donné à Claude)
SUJETS = [
    ("noel-nouvel-an", (10, 11, 12),
     "Ski à Noël et au Nouvel An : dates des vacances scolaires, stations les plus sûres côté neige, prix des forfaits et hébergements en période de fêtes, quand réserver"),
    ("premiere-fois", (10, 11, 12, 1),
     "Première fois au ski : bien préparer son premier séjour (cours, matériel, forfait débutant, stations aux pistes douces, erreurs à éviter)"),
    ("choisir-forfait", (10, 11, 12),
     "Quel forfait de ski choisir : forfait journée, plusieurs jours, saison, forfaits débutants, grands domaines reliés, où et quand l'acheter moins cher"),
    ("location-materiel", (10, 11, 12),
     "Louer ou acheter son matériel de ski : budget, formules de location, réflexes pour payer moins, quoi vérifier"),
    ("petit-budget", (10, 11, 12, 1),
     "Skier avec un petit budget : bonnes périodes, stations abordables, forfaits, hébergement, transport, astuces concrètes"),
    ("enfants-age", (11, 12, 1),
     "Initier ses enfants au ski : à partir de quel âge, cours collectifs ou particuliers, garderies et jardins des neiges, stations adaptées aux familles"),
    ("janvier-calme", (11, 12),
     "Ski en janvier : moins de monde, forfaits et hébergements moins chers, conditions de neige, stations à privilégier"),
    ("voyage-etranger", (11, 12, 1, 2),
     "Skier en Autriche, en Suisse ou en Italie depuis la France : avantages, prix, accès, ce qui change par rapport aux stations françaises"),
    ("mauvais-temps", (12, 1, 2),
     "Que faire en station quand il y a du mauvais temps ou peu de neige : activités, spas, visites, idées pour toute la famille"),
    ("nordique-raquettes", (12, 1, 2),
     "Ski de fond, raquettes, ski de randonnée : d'autres façons de profiter de la neige, pour débuter, avec les stations adaptées"),
    ("securite-pistes", (12, 1, 2),
     "Sécurité sur les pistes : règles de bonne conduite, casque, assurance, secours, hors-piste et risque d'avalanche"),
    ("mars-soleil", (1, 2, 3),
     "Ski en mars : soleil, neige de printemps, stations à altitude élevée, prix et organisation du séjour"),
    ("paques", (2, 3),
     "Ski à Pâques : dates, stations encore bien enneigées, prix, ce qu'il faut savoir avant de réserver"),
    ("ete-glacier", (5, 6, 7),
     "Skier en été : les glaciers ouverts, dates, prix, comment préparer sa journée"),
]

CATEGORIES_GUIDE = ["Guide pratique", "Conseils budget", "Famille", "Saison d'hiver", "Forfaits & budget"]

SYSTEM_GUIDE = """Tu es rédacteur pour SnowFinder, un site français de comparaison et de découverte des stations de ski.
Tu rédiges UN guide pratique fiable et utile aux skieurs, à partir de pages web que tu trouves toi-même avec l'outil de recherche.

RÈGLES ABSOLUES
- Tu n'utilises QUE des faits présents dans les pages trouvées par la recherche (dates officielles, tarifs publics, règles, durées, âges minimums…), jamais ta mémoire. Aucun chiffre, date, nom ou citation inventé.
- Tu reformules : aucune phrase copiée d'une source (les extraits demandés dans « faits » sont internes, ils ne figurent pas dans le guide).
- Les conseils généraux sont permis s'ils s'appuient sur un fait sourcé ; sinon reste factuel. Évite « toujours », « jamais », « le meilleur ».
- Ton clair, chaleureux et concret ; pas d'accroche racoleuse ; pas d'accusation contre une personne ou une entreprise.
- Pas de HTML, pas de lien, pas de markdown dans les textes.
- Si la recherche ne fournit pas assez d'informations fiables et à jour pour ce sujet, réponds {"pas_d_actu": true}.
- RÈGLE CHIFFRES : tout nombre de 10 ou plus, ou suivi d'une unité (km, m, €, %, pistes, remontées, jours…), écrit dans le texte doit figurer tel quel dans un « fait » (avec son extrait) ou dans les données SnowFinder fournies. Sinon, écris la phrase sans ce chiffre. N'additionne, ne convertis et n'arrondis aucun chiffre.
- Dans les textes, n'utilise aucun guillemet droit (") : emploie « » ou l'apostrophe. Aucun retour à la ligne dans une chaîne JSON.

FORMAT DE RÉPONSE : un unique objet JSON, rien d'autre :
{
 "pas_d_actu": false,
 "categorie": "une valeur parmi : %CATS%",
 "titre": "titre clair, orienté recherche Google (≤ 95 caractères)",
 "excerpt": "1 à 2 phrases de résumé (100 à 240 caractères)",
 "chapeau": "paragraphe d'introduction (200 à 450 caractères)",
 "a_retenir": ["3 à 4 points courts, chiffres et dates compris"],
 "sections": [{"titre": "intertitre sous forme de question ou de thème", "paragraphes": ["1 à 3 paragraphes de 250 à 600 caractères"]}],
 "conseils": ["2 à 4 conseils pratiques, fondés sur les faits"],
 "stations": ["1 à 4 noms de stations de la liste fournie, citées comme exemples pertinents"],
 "faits": [{"fait": "un fait important du guide, en une phrase", "url": "adresse EXACTE d'une page trouvée", "extrait": "passage copié MOT POUR MOT de cette page (60 à 220 caractères) qui prouve le fait"}],
 "sources": [{"media": "nom du site ou du média", "titre": "titre de la page", "url": "adresse EXACTE d'une page trouvée", "date": "AAAA-MM-JJ ou vide"}]
}
Exigences : 4 à 5 sections ; guide de 550 à 1000 mots ; au moins 6 faits, appuyés par au moins 2 pages différentes ; chaque chiffre ou date du guide doit apparaître dans un fait ; sources = les pages réellement utilisées (2 à 5)."""


def choisir_sujet(today: str) -> tuple[str, str]:
    mois = int(today.split("-")[1])
    faits = {h.get("topic") for h in a.load_json(a.HISTORY, [])}
    libres = [s for s in SUJETS if s[0] not in faits]
    de_saison = [s for s in libres if mois in s[1]]
    pool = de_saison or libres
    if not pool:
        return "", ""
    return pool[0][0], pool[0][2]


def prompt_guide(today, names, deja, sujet, retours):
    p = [f"Date du jour : {today}.",
         f"Sujet du guide : {sujet}.",
         "Cherche les informations officielles et à jour (calendrier des vacances scolaires, tarifs publics, règles, offices de tourisme, "
         "sites des stations, administrations) puis rédige le guide pour des skieurs français qui préparent la saison 2026-2027. "
         "Recoupe avec au moins deux pages différentes.",
         "Stations de la base SnowFinder (pour le champ « stations », noms exacts) : " + "; ".join(names) + ".",
         "Articles déjà publiés sur SnowFinder (ne pas refaire le même sujet) : " + " | ".join(deja[:40]) + "."]
    if retours:
        p.append("Ta version précédente a été refusée pour ces raisons, corrige-les :\n- " + "\n- ".join(retours))
    return "\n\n".join(p)


def main() -> None:
    argv = sys.argv
    if "--list" in argv:
        today = date.today().isoformat()
        faits = {h.get("topic") for h in a.load_json(a.ROOT / "guides_hebdo.json", [])}
        mois = int(today.split("-")[1])
        for k, m, t in SUJETS:
            etat = "publié" if k in faits else ("de saison" if mois in m else "hors saison")
            print(f"{k:20s} {etat:12s} {t[:80]}")
        return
    a.HISTORY = a.ROOT / "guides_hebdo.json"
    a.LABEL = "Guide"
    a.SYSTEM = SYSTEM_GUIDE + a.DOMAIN_RULE
    a.CATEGORIES = CATEGORIES_GUIDE
    a.WORDS = (300, 1200) if "--mock" in argv else (500, 1150)
    a.MIN_FAITS = 5 if "--mock" in argv else 6
    today = date.today().isoformat()
    if "--sujet" not in argv or not argv[argv.index("--sujet") + 1:] or argv[argv.index("--sujet") + 1].startswith("--") \
            or not argv[argv.index("--sujet") + 1].strip():
        key, sujet = choisir_sujet(today)
        if not sujet:
            print("ℹ️  Tous les sujets du calendrier sont publiés : rien à faire.")
            return
        a.TOPIC_KEY = key
        argv[1:1] = ["--sujet", sujet]
        # --sujet doit précéder les autres options ; si l'utilisateur a laissé un --sujet vide on l'ignore
        if argv.count("--sujet") > 1:
            i = argv.index("--sujet", 3)
            del argv[i:i + 2]
    a.build_user_prompt = prompt_guide
    a.main()


if __name__ == "__main__":
    main()
