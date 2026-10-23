#!/usr/bin/env python3
"""
generate_actu_hebdo.py — SnowFinder : UN article d'actualité sourcé, toutes les deux semaines.

Principe (pensé pour qu'une erreur ne passe pas) :
  1. Claude Opus cherche sur le web les actualités récentes des stations de ski (outil de recherche web
     de l'API Anthropic), choisit un sujet utile aux skieurs français et rédige l'article UNIQUEMENT
     à partir des pages trouvées. S'il n'y a rien de notable : aucun article n'est produit.
  2. Pour chaque fait important, Claude doit fournir l'adresse de la source + un extrait copié mot pour mot.
  3. Le script contrôle :
       - la structure, la longueur, aucun lien/HTML dans le texte ;
       - que chaque source citée fait bien partie des pages réellement trouvées par la recherche ;
       - que chaque chiffre du texte figure dans les faits sourcés ou dans les fiches stations ;
       - qu'au moins une station de la base SnowFinder est concernée (liens internes + Booking/Expedia CJ) ;
       - en rouvrant les pages sources : que l'extrait cité s'y trouve vraiment.
  4. Une seconde relecture (Opus, sans recherche) traque tout ce qui n'est pas soutenu par les faits.
  5. Jusqu'à 3 essais ; puis la page est écrite et le workflow ouvre une pull request avec les sources
     cliquables : rien n'est publié avant votre « Merge ».

Utilisation :
  ANTHROPIC_API_KEY=... python3 _scripts/generate_actu_hebdo.py --review-out /tmp/r.md
  python3 _scripts/generate_actu_hebdo.py --sujet "ouverture des stations"    # thème imposé
  python3 _scripts/generate_actu_hebdo.py --mock ok --dry-run                  # test sans API
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import math
import os
import re
import sys
import urllib.request
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_comparatifs as gc  # noqa: E402
import generate_article_hebdo as ah  # noqa: E402
import generate_duel_hebdo as dh  # noqa: E402  (extraction des nombres, JSON)

ROOT = gc.REPO_ROOT
ARTICLES_DIR = ROOT / "articles"
HISTORY = ROOT / "actus_hebdo.json"
CONTENUS = ROOT / "contenus.json"
MODEL = os.environ.get("ACTU_MODEL", "claude-opus-5-5")
MAX_TRIES = 3
SEARCH_MAX_USES = 8
NBSP = " "
MOCK = None
WORDS = (320, 850)      # longueur attendue de l'article (mots)
MIN_FAITS = 5
LABEL = "Actualité"
TOPIC_KEY = ""           # renseigné par le guide saisonnier (sujet du calendrier)

CATEGORIES = ["Actualités", "Enneigement", "Forfaits & budget", "Calendrier hiver", "Saison d'automne",
              "Météo", "Remontées mécaniques", "Vacances scolaires", "Stations"]


# ── Utilitaires ──────────────────────────────────────────────────────────────

def load_json(path: Path, default):
    return ah.load_json(path, default)


def norm_url(u: str) -> str:
    p = urlsplit(u.strip())
    return f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/')}"


def norm_text(t: str) -> str:
    t = htmllib.unescape(t).lower()
    t = t.replace("’", "'").replace("‘", "'").replace("«", " ").replace("»", " ").replace("“", " ").replace("”", " ")
    t = t.replace('"', " ").replace(" ", " ").replace(" ", " ").replace(" ", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# ── Rédaction (recherche web + rédaction) ────────────────────────────────────

SYSTEM = """Tu es rédacteur pour SnowFinder, un site français de comparaison et de découverte des stations de ski.
Tu rédiges UN article d'actualité fiable, utile aux skieurs, à partir de pages web que tu trouves toi-même avec l'outil de recherche.

RÈGLES ABSOLUES
- Tu n'utilises QUE des faits présents dans les pages trouvées par la recherche, jamais ta mémoire. Aucun chiffre, date, nom ou citation inventé.
- Tu reformules : aucune phrase copiée d'une source (les extraits demandés dans « faits » sont internes, ils ne figurent pas dans l'article).
- Dates toujours en toutes lettres avec le jour et le mois (« mardi 20 octobre »), jamais « hier » ou « cette semaine » seuls.
- Ton neutre, informatif, utile ; pas d'accroche racoleuse, pas d'affirmation sur l'avenir qui ne soit pas dans une source ; pas d'accusation contre une personne ou une entreprise.
- Pas de HTML, pas de lien, pas de markdown dans les textes.
- Si la recherche ne donne rien de notable et récent (moins de 12 jours) pour des skieurs français, réponds {"pas_d_actu": true}.

FORMAT DE RÉPONSE : un unique objet JSON, rien d'autre :
{
 "pas_d_actu": false,
 "categorie": "une valeur parmi : %CATS%",
 "titre": "titre clair avec le sujet et la station ou la zone (≤ 95 caractères)",
 "excerpt": "1 à 2 phrases de résumé (100 à 240 caractères)",
 "chapeau": "paragraphe d'introduction (200 à 450 caractères) qui pose les faits essentiels",
 "a_retenir": ["3 à 4 points courts, chiffres et dates compris"],
 "sections": [{"titre": "intertitre sous forme de question ou de thème", "paragraphes": ["1 à 3 paragraphes de 250 à 600 caractères"]}],
 "conseils": ["2 à 4 conseils pratiques pour le lecteur, fondés sur les faits"],
 "stations": ["1 à 4 noms de stations concernées, exactement comme dans la liste fournie"],
 "faits": [{"fait": "un fait important de l'article, en une phrase", "url": "adresse EXACTE d'une page trouvée", "extrait": "passage copié MOT POUR MOT de cette page (60 à 220 caractères) qui prouve le fait"}],
 "sources": [{"media": "nom du média", "titre": "titre de la page", "url": "adresse EXACTE d'une page trouvée", "date": "AAAA-MM-JJ ou vide"}]
}
Exigences : 3 à 5 sections ; article total de 380 à 750 mots ; au moins 5 faits, appuyés par au moins 2 pages différentes ; chaque chiffre ou date de l'article doit apparaître dans un fait ; sources = les pages réellement utilisées (2 à 5)."""


# ── Cohérence stations / domaines skiables ──────────────────────────────────
BIG_DOMAINS = ["Trois Vallées", "3 Vallées", "Paradiski", "Portes du Soleil", "Grand Massif", "Sybelles", "4 Vallées",
               "Quatre Vallées", "Ski Arlberg", "Grandvalira", "SkiWelt", "Zillertal Arena", "Évasion Mont-Blanc"]
DOMAIN_RULE = (
    "\n\nVOCABULAIRE : une STATION est un lieu (Val Thorens, Méribel, La Plagne…) ; un DOMAINE SKIABLE est un ensemble de pistes reliées "
    "qui peut regrouper plusieurs stations (Les Trois Vallées, Paradiski, Les Portes du Soleil, Tignes – Val d'Isère…). "
    "Ne dis jamais « la station des Trois Vallées » ou « la station de Paradiski » : dis « le domaine des Trois Vallées » et cite les stations qu'il comprend. "
    "N'emploie plus le nom « Espace Killy » : il s'appelle désormais « Tignes – Val d'Isère ». "
    "Ne donne pas à une station les kilomètres de pistes ou les chiffres de tout un domaine sans le préciser. "
    "Domaines reliés connus de la base : " + " ; ".join(f"{ah.DOMAIN_NAMES.get(k, k)} = " + ", ".join(v) for k, v in ah.DOMAIN_GROUPS.items()) + "."
)
SYSTEM += DOMAIN_RULE

_VOC_RE = re.compile(r"\bstations?\s+(?:de\s+|du\s+|des\s+|d['’])?(?:les\s+|la\s+|l['’])?(?:" + "|".join(re.escape(x) for x in BIG_DOMAINS) + r")\b", re.I)


def vocabulary_errors(d: dict) -> list:
    txt = " ".join(article_texts(d))
    errs = []
    if re.search(r"espace\s+killy", txt, re.I):
        errs.append("« Espace Killy » est un ancien nom : écrire « Tignes – Val d'Isère »")
    m = _VOC_RE.search(txt)
    if m:
        errs.append(f"confusion station / domaine : « {m.group(0)} » (un domaine n'est pas une station)")
    return errs


def build_user_prompt(today: str, stations_names: list, deja: list, sujet: str, retours: list) -> str:
    p = [f"Date du jour : {today}.",
         "Cherche l'actualité des stations de ski des 12 derniers jours qui intéressera le plus des skieurs français : "
         "dates d'ouverture ou de fermeture, enneigement et météo de montagne, tarifs des forfaits, remontées mécaniques, "
         "nouveautés ou événements marquants. Privilégie des médias fiables (presse régionale et nationale, Météo-France, "
         "offices de tourisme, magazines spécialisés). Recoupe avec au moins deux pages différentes quand c'est possible.",
         "Stations de la base SnowFinder (pour le champ « stations », noms exacts) : " + "; ".join(stations_names) + ".",
         "Articles déjà publiés sur SnowFinder (ne pas refaire le même sujet) : " + " | ".join(deja[:30]) + "."]
    if sujet:
        p.append(f"Thème imposé pour cette fois : {sujet}.")
    if retours:
        p.append("Ta version précédente a été refusée pour ces raisons, corrige-les :\n- " + "\n- ".join(retours))
    return "\n\n".join(p)


def call_search_llm(system: str, user: str):
    """Appelle Claude avec l'outil de recherche web. Retourne (texte final, URL réellement trouvées)."""
    import anthropic  # importé ici : inutile en mode --mock
    client = anthropic.Anthropic()
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": SEARCH_MAX_USES,
              "user_location": {"type": "approximate", "country": "FR", "timezone": "Europe/Paris"}}]
    messages = [{"role": "user", "content": user}]
    urls: set = set()
    for _ in range(6):
        resp = client.messages.create(model=MODEL, max_tokens=9000, system=system, tools=tools, messages=messages)
        for b in resp.content:
            if getattr(b, "type", "") == "web_search_tool_result":
                c = getattr(b, "content", None)
                if isinstance(c, list):
                    for r in c:
                        u = getattr(r, "url", None)
                        if u:
                            urls.add(u)
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in resp.content]})
            continue
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text"), urls
    raise SystemExit("❌ La recherche web n'a pas abouti (trop de pauses).")


SYSTEM_RELECTURE = """Tu es relecteur factuel pour SnowFinder. On te donne un article d'actualité et la liste des FAITS sourcés (fait + extrait de la page source). Les faits sont la SEULE source de vérité, avec les fiches stations fournies.
Signale : toute affirmation de l'article absente des faits ou des fiches, toute contradiction, tout chiffre ou date faux, toute spéculation présentée comme un fait, tout propos pouvant mettre en cause une personne ou une entreprise.
Ne signale PAS le style. Réponds par un unique objet JSON : {"problemes": ["…"]} (liste vide si tout est soutenu)."""


def article_texts(d: dict) -> list:
    out = [d.get("titre", ""), d.get("excerpt", ""), d.get("chapeau", "")]
    out += [str(x) for x in d.get("a_retenir", [])]
    for s in d.get("sections", []):
        out.append(s.get("titre", ""))
        out += [str(x) for x in s.get("paragraphes", [])]
    out += [str(x) for x in d.get("conseils", [])]
    return out


def relecture(d: dict, stations_info: str) -> list:
    if MOCK:
        return []
    import anthropic
    client = anthropic.Anthropic()
    user = ("ARTICLE :\n" + "\n\n".join(article_texts(d)) +
            "\n\nFAITS SOURCÉS :\n" + "\n".join(f"- {f['fait']}  [extrait : « {f['extrait']} »]" for f in d["faits"]) +
            "\n\nFICHES STATIONS :\n" + stations_info)
    msg = client.messages.create(model=MODEL, max_tokens=1500, system=SYSTEM_RELECTURE,
                                 messages=[{"role": "user", "content": user}])
    txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    try:
        return [str(x) for x in dh.extract_json(txt).get("problemes", [])]
    except Exception:
        return ["la relecture a renvoyé une réponse illisible"]


# ── Contrôles par script ─────────────────────────────────────────────────────

def words(d: dict) -> int:
    return len(" ".join(article_texts(d)).split())


def check_draft(d: dict, urls_seen: set, names: set, stations_blob: str, today: str) -> list:
    errs = []
    if not isinstance(d, dict):
        return ["la réponse n'est pas un objet JSON"]
    for k in ("categorie", "titre", "excerpt", "chapeau", "a_retenir", "sections", "conseils", "stations", "faits", "sources"):
        if k not in d:
            errs.append(f"clé « {k} » manquante")
    if errs:
        return errs
    if d["categorie"] not in CATEGORIES:
        errs.append(f"catégorie invalide : {d['categorie']}")
    if not (20 <= len(d["titre"]) <= 100):
        errs.append(f"titre de {len(d['titre'])} caractères (attendu 20 à 100)")
    if not (80 <= len(d["excerpt"]) <= 280):
        errs.append(f"excerpt de {len(d['excerpt'])} caractères (attendu 80 à 280)")
    if not (150 <= len(d["chapeau"]) <= 520):
        errs.append(f"chapeau de {len(d['chapeau'])} caractères (attendu 150 à 520)")
    if not (3 <= len(d["a_retenir"]) <= 4):
        errs.append("« a_retenir » doit contenir 3 ou 4 points")
    if not (3 <= len(d["sections"]) <= 5) or not all(isinstance(s, dict) and s.get("titre") and s.get("paragraphes") for s in d["sections"]):
        errs.append("il faut 3 à 5 sections {titre, paragraphes}")
    if not (2 <= len(d["conseils"]) <= 4):
        errs.append("« conseils » doit contenir 2 à 4 éléments")
    w = words(d)
    if not (WORDS[0] <= w <= WORDS[1]):
        errs.append(f"article de {w} mots (attendu {WORDS[0]} à {WORDS[1]})")
    for t in article_texts(d):
        if "<" in t or ">" in t or re.search(r"https?://|www\.", t):
            errs.append("HTML ou lien présent dans le texte de l'article")
            break
    errs += vocabulary_errors(d)
    st = d["stations"]
    if not (1 <= len(st) <= 4) or any(s not in names for s in st):
        errs.append("« stations » : 1 à 4 noms exactement comme dans la liste fournie")
    faits = d["faits"]
    if len(faits) < MIN_FAITS or not all(isinstance(f, dict) and f.get("fait") and f.get("url") and f.get("extrait") for f in faits):
        errs.append(f"il faut au moins {MIN_FAITS} faits {{fait, url, extrait}}")
    seen_n = {norm_url(u) for u in urls_seen}
    for f in faits:
        if isinstance(f, dict) and f.get("url") and norm_url(f["url"]) not in seen_n:
            errs.append(f"fait rattaché à une page non trouvée par la recherche : {f['url']}")
    if len({norm_url(f["url"]) for f in faits if isinstance(f, dict) and f.get("url")}) < 2:
        errs.append("les faits doivent s'appuyer sur au moins 2 pages différentes")
    srcs = d["sources"]
    if not (2 <= len(srcs) <= 5) or not all(isinstance(s, dict) and s.get("media") and s.get("url") for s in srcs):
        errs.append("il faut 2 à 5 sources {media, titre, url, date}")
    else:
        for s in srcs:
            if norm_url(s["url"]) not in seen_n:
                errs.append(f"source non trouvée par la recherche : {s['url']}")
    # chaque nombre sensible du texte doit venir des faits ou des fiches stations
    allowed = {v for v, _, _ in dh.numbers_in(" ".join(f"{f.get('fait', '')} {f.get('extrait', '')}" for f in faits if isinstance(f, dict)))}
    allowed |= {v for v, _, _ in dh.numbers_in(stations_blob)}
    allowed |= {float(y) for y in range(date.today().year - 1, date.today().year + 3)}
    allowed |= {float(x) for x in today.replace("-", " ").split()}
    bad = []
    for t in article_texts(d):
        for v, tok, after in dh.numbers_in(t):
            if (v >= 10 or dh.UNIT_RE.match(after)) and v not in allowed:
                bad.append(tok)
    if bad:
        errs.append("chiffres absents des faits sourcés : " + ", ".join(sorted(set(bad))[:8]))
    return errs


UA = "Mozilla/5.0 (compatible; SnowFinderBot/1.0; +https://snowfinder.fr)"


def fetch_text(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr,en;q=0.8"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read(3_000_000)
            enc = r.headers.get_content_charset() or "utf-8"
        t = raw.decode(enc, errors="replace")
    except Exception:
        return None
    t = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return norm_text(t)


def verify_extraits(d: dict, do_fetch: bool) -> tuple[list, list]:
    """Rouvre les pages sources et vérifie que chaque extrait y figure. Retourne (problèmes, lignes de compte rendu)."""
    if not do_fetch:
        return [], ["vérification des extraits non faite (mode test)"]
    pages, notes, ok, ko, na = {}, [], 0, 0, 0
    for f in d["faits"]:
        u = f["url"]
        if u not in pages:
            pages[u] = fetch_text(u)
        t = pages[u]
        if t is None or len(t) < 1500:
            na += 1
            notes.append(f"❔ page non lisible automatiquement : {u}")
            continue
        if norm_text(f["extrait"]) in t:
            ok += 1
        else:
            ko += 1
            notes.append(f"⚠️ extrait introuvable dans la page : « {f['extrait'][:90]}… » ({u})")
    probs = []
    if ko > max(1, (ok + ko) // 2):
        probs.append(f"{ko} extraits cités sur {ok + ko} sont introuvables dans les pages sources : recopier les extraits mot pour mot")
    notes.insert(0, f"extraits retrouvés dans les pages : {ok} ; introuvables : {ko} ; pages illisibles : {na}")
    return probs, notes


# ── Mode test ────────────────────────────────────────────────────────────────

def mock_draft(kind: str, stations: list) -> tuple[dict, set]:
    s = next(x for x in stations if x["name"] == "Tignes") if any(x["name"] == "Tignes" for x in stations) else stations[0]
    n = s["name"]
    u1, u2 = "https://www.exemple-presse.fr/neige-octobre", "https://www.meteo-exemple.fr/prevision-alpes"
    para = ("Les premières chutes de neige de la saison se sont déposées sur les hauts sommets et les équipes des domaines "
            "préparent déjà l'ouverture annoncée. Les prévisions restent prudentes pour les jours à venir, avec des températures "
            "encore douces en dessous de la limite pluie-neige, et les conditions peuvent évoluer rapidement en montagne.")
    d = {"pas_d_actu": False, "categorie": CATEGORIES[0],
         "titre": f"Première neige de la saison sur {n} : ce qu'il faut savoir avant l'ouverture",
         "excerpt": f"Les premières chutes de neige touchent le domaine de {n} avant l'ouverture annoncée le 21 novembre 2026.",
         "chapeau": f"À quelques semaines de l'ouverture, {n} reçoit sa première neige de la saison. Voici ce que disent les sources "
                    "sur les cumuls attendus, la limite pluie-neige et les dates d'ouverture annoncées pour cet hiver.",
         "a_retenir": ["ouverture annoncée le 21 novembre 2026", "limite pluie-neige vers 1 800 m", "jusqu'à 30 cm sur les sommets"],
         "sections": [{"titre": "Que disent les prévisions ?", "paragraphes": [para, para]},
                      {"titre": "Quelles dates d'ouverture ?", "paragraphes": [para, para]},
                      {"titre": "Et pour les skieurs ?", "paragraphes": [para, para]}],
         "conseils": ["Suivre les conditions avant de partir.", "Réserver tôt les hébergements des vacances."],
         "stations": [n],
         "faits": [{"fait": "Ouverture annoncée le 21 novembre 2026", "url": u1, "extrait": "ouverture prévue le 21 novembre 2026 pour la saison"},
                   {"fait": "Limite pluie-neige vers 1 800 m", "url": u2, "extrait": "la limite pluie-neige se situe autour de 1 800 m"},
                   {"fait": "Jusqu'à 30 cm de neige sur les sommets", "url": u2, "extrait": "jusqu'à 30 cm de neige fraîche sur les sommets"},
                   {"fait": "Températures douces sous la limite", "url": u1, "extrait": "températures encore douces en dessous de la limite"},
                   {"fait": "Prévisions prudentes pour les jours à venir", "url": u1, "extrait": "les prévisions restent prudentes"}],
         "sources": [{"media": "Exemple Presse", "titre": "Neige d'octobre", "url": u1, "date": date.today().isoformat()},
                     {"media": "Météo Exemple", "titre": "Prévision Alpes", "url": u2, "date": date.today().isoformat()}]}
    if kind == "bad":
        d["sections"][0]["paragraphes"][0] += " Le cumul pourrait atteindre 85 cm dans les 48 heures."
        d["stations"] = [n, "Station Inexistante"]
    return d, {u1, u2}


def rediger(stations: list, deja: list, sujet: str, today: str) -> tuple[dict, list, set]:
    names = {s["name"] for s in stations}
    names_sorted = sorted(names)
    retours, notes = [], []
    for essai in range(1, MAX_TRIES + 1):
        if MOCK:
            d, urls = mock_draft(MOCK, stations)
            if MOCK == "bad" and essai >= 3:
                d, urls = mock_draft("ok", stations)
        else:
            txt, urls = call_search_llm(SYSTEM.replace("%CATS%", " | ".join(CATEGORIES)),
                                        build_user_prompt(today, names_sorted, deja, sujet, retours))
            try:
                d = dh.extract_json(txt)
            except Exception as e:  # noqa: BLE001
                retours = [f"réponse illisible ({e}) : renvoie uniquement l'objet JSON demandé"]
                notes.append(f"essai {essai} : réponse illisible")
                continue
        if d.get("pas_d_actu"):
            return d, notes + ["Claude n'a rien trouvé de notable et de récent"], urls
        blob = " ".join(json.dumps({k: s.get(k) for k in dh.FIELDS_FOR_LLM}, ensure_ascii=False)
                        for s in stations if s["name"] in (d.get("stations") or []))
        errs = check_draft(d, urls, names, blob, today)
        if not errs:
            probs, vnotes = verify_extraits(d, do_fetch=not MOCK and not os.environ.get("ACTU_NO_FETCH"))
            errs = probs
            notes += [f"essai {essai} : " + n for n in vnotes]
        if not errs:
            info = "\n".join(json.dumps({k: s.get(k) for k in dh.FIELDS_FOR_LLM}, ensure_ascii=False)
                             for s in stations if s["name"] in d["stations"])
            errs = relecture(d, info)
            if errs:
                notes.append(f"essai {essai} refusé par la relecture : " + " ; ".join(errs))
        else:
            notes.append(f"essai {essai} refusé par les contrôles : " + " ; ".join(errs))
        if not errs:
            notes.append(f"essai {essai} : contrôles et relecture OK")
            return d, notes, urls
        retours = errs
    raise SystemExit("❌ Aucun article valide après %d essais :\n  - %s" % (MAX_TRIES, "\n  - ".join(notes)))


# ── Page ─────────────────────────────────────────────────────────────────────

def linkify(paras: list, stations: list, used: set) -> list:
    """Échappe le texte et lie (une seule fois par article) les noms de stations de la base."""
    names = sorted({s["name"] for s in stations if len(s["name"]) >= 5}, key=len, reverse=True)
    if not names:
        return [escape(p) for p in paras]
    rx = re.compile(r"(?<![\w-])(" + "|".join(re.escape(n) for n in names) + r")(?![\w-])")
    out = []
    for p in paras:
        res, pos = [], 0
        for m in rx.finditer(p):
            res.append(escape(p[pos:m.start()]))
            nm = m.group(1)
            if nm in used:
                res.append(escape(nm))
            else:
                used.add(nm)
                res.append(f'<a href="/stations/{gc.slugify(nm)}.html">{escape(nm)}</a>')
            pos = m.end()
        res.append(escape(p[pos:]))
        out.append("".join(res))
    return out


def fr_date_short(iso: str) -> str:
    try:
        return ah.fr_date(iso)
    except Exception:  # noqa: BLE001
        return ""


def slug_for(title: str, today: str) -> str:
    base = gc.slugify(title)
    if len(base) > 70:
        base = base[:70].rsplit("-", 1)[0]
    base = base.strip("-")
    y, m, _ = today.split("-")
    suffix = f"{ah.MONTHS[int(m) - 1]}-{y}"
    return base if y in base else f"{base}-{suffix}"


def build(d: dict, stations: list, today: str) -> dict:
    by_name = {s["name"]: s for s in stations}
    cited = [by_name[n] for n in d["stations"]]
    used: set = set()
    body = []
    body += [f"    <p>{p}</p>" for p in linkify([d["chapeau"]], stations, used)]

    first = cited[0]
    photo = gc.station_photo(first["name"])
    hero_src = photo or gc.RESCUE_PHOTOS[first["id"] % len(gc.RESCUE_PHOTOS)]
    cap = (f"{escape(first['name'])}." if photo else "Photo d'illustration.")
    hero_alt = escape(first["name"]) if photo else "Paysage de montagne enneigé (photo d'illustration)"
    body.append(f'    <figure>\n      <img src="{hero_src}" alt="{hero_alt}" loading="lazy">\n      <figcaption>{cap}</figcaption>\n    </figure>')
    body.append('    <div class="keys"><p><strong>À retenir :</strong> ' + " · ".join(escape(x) for x in d["a_retenir"]) + "</p></div>")
    for s in d["sections"]:
        body.append(f"    <h3>{escape(s['titre'])}</h3>")
        body += [f"    <p>{p}</p>" for p in linkify(s["paragraphes"], stations, used)]
    lis = [f"<li>{p}</li>" for p in linkify(d["conseils"], stations, used)]
    lis.append('<li><strong>Pour suivre le manteau neigeux :</strong> consultez notre page <a href="/enneigement.html">Enneigement</a>, qui rassemble les conditions station par station.</li>')
    body.append("    <h3>Nos conseils</h3>\n    <ul>\n      " + "\n      ".join(lis) + "\n    </ul>")
    body.append("    <h2>Les stations à retenir</h2>")
    body.append("    " + ah.PISTES_LEGEND)
    for s in cited:
        body.append(ah.station_card(s))
    body.append('    <p class="disc">Liens affiliés — prix identiques, aucune commission prélevée sur vous.</p>')
    src_items = []
    for s in d["sources"]:
        dt = fr_date_short(s.get("date", "")) if s.get("date") else ""
        label = escape(s["media"]) + (f" ({dt})" if dt else "")
        src_items.append(f'<a href="{escape(s["url"], quote=True)}" target="_blank" rel="noopener">{label}</a>')
    body.append('    <p class="src">Sources : ' + ", ".join(src_items) + ".</p>")
    body.append("    <p>Envie de recevoir l'alerte dès que ça tombe fort ? Activez les notifications SnowFinder depuis le menu ☰ en haut de page.</p>")

    text_words = len(re.sub(r"<[^>]+>", " ", "\n".join(body)).split())
    read_min = max(3, math.ceil(text_words / 200))
    slug = slug_for(d["titre"], today)
    page = ah.render_page(slug=slug, title=d["titre"], excerpt=d["excerpt"], category=d["categorie"], body="\n".join(body),
                          today=today, read_min=read_min, hero_photo=photo)
    return {"slug": slug, "html": page, "read_min": read_min, "img": photo or hero_src, "cited": cited}


def verify_page(art: dict) -> list:
    h, pb = art["html"], []
    if "tkqlhce.com" not in h or "jdoqocy.com" not in h:
        pb.append("liens CJ Booking/Expedia absents")
    if re.search(r'href="https://www\.(booking|expedia)', h):
        pb.append("lien Booking/Expedia direct (non CJ)")
    if h.count('class="bk"') != len(art["cited"]):
        pb.append("une station sans lien Booking")
    if 'class="src"' not in h:
        pb.append("ligne Sources absente")
    return pb


# ── Enregistrement + compte rendu ────────────────────────────────────────────

def enregistrer(d: dict, art: dict, today: str) -> None:
    ARTICLES_DIR.mkdir(exist_ok=True)
    (ARTICLES_DIR / f"{art['slug']}.html").write_text(art["html"], encoding="utf-8")
    hist = load_json(HISTORY, [])
    hist.append({"slug": art["slug"], "title": d["titre"], "date": today, "sources": [s["url"] for s in d["sources"]],
                 **({"topic": TOPIC_KEY} if TOPIC_KEY else {})})
    HISTORY.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cont = load_json(CONTENUS, {"articles": [], "duels": []})
    cont["articles"] = [a for a in cont.get("articles", []) if a.get("slug") != art["slug"]]
    cont["articles"].insert(0, {"slug": art["slug"], "title": d["titre"], "category": d["categorie"],
                                "excerpt": d["excerpt"], "img": art["img"], "date": today, "read_min": art["read_min"]})
    CONTENUS.write_text(json.dumps(cont, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def review_md(d: dict, art: dict, notes: list, problems: list) -> str:
    L = [f"## 📰 {LABEL} : {d['titre']}", "",
         f"Page : `articles/{art['slug']}.html` · catégorie : {d['categorie']} · stations liées : {', '.join(s['name'] for s in art['cited'])}", "",
         "### ⚠️ À faire avant de fusionner (2 minutes)", "",
         "1. Ouvrez **au moins deux sources** ci-dessous et vérifiez que l'article dit la même chose (dates, chiffres, noms).",
         "2. Lisez l'article en entier : rien ne doit vous sembler affirmé sans source.",
         "3. En cas de doute : fermez la pull request sans la fusionner.", "", "### Sources", ""]
    for s in d["sources"]:
        L.append(f"- [{s['media']} — {s.get('titre') or s['url']}]({s['url']}) {('(' + s['date'] + ')') if s.get('date') else ''}")
    L += ["", "### Faits contrôlés (fait → extrait de la source)", ""]
    for f in d["faits"]:
        L.append(f"- **{f['fait']}** — « {f['extrait']} » ([page]({f['url']}))")
    L += ["", "### Contrôles automatiques", ""] + [f"- {n}" for n in notes]
    if problems:
        L += ["", "### ⚠️ Points d'attention", ""] + [f"- {p}" for p in problems]
    L += ["", "**Merge = publication** (accueil et « Toutes nos actus » se mettent à jour tout seuls)."]
    return "\n".join(L) + "\n"


def main() -> None:
    global MOCK
    ap = argparse.ArgumentParser()
    ap.add_argument("--sujet", default="", help="thème imposé (facultatif)")
    ap.add_argument("--mock", choices=["ok", "bad"], help="test sans API")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--review-out")
    args = ap.parse_args()
    MOCK = args.mock
    if not MOCK and not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("❌ ANTHROPIC_API_KEY absente (secret GitHub à créer).")

    stations = ah.load_stations()
    today = date.today().isoformat()
    deja = [a["title"] for a in load_json(CONTENUS, {}).get("articles", [])] + [h["title"] for h in load_json(HISTORY, [])]
    try:
        d, notes, urls = rediger(stations, deja, args.sujet, today)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        hint = (" — la recherche web doit être activée dans la console Anthropic"
                if "web_search" in msg.lower() or "web search" in msg.lower() else "")
        raise SystemExit(f"❌ Erreur d'appel à l'API : {msg[:300]}{hint}")
    if d.get("pas_d_actu"):
        print(f"ℹ️  {LABEL} : rien de notable cette fois, aucun article produit.")
        return
    art = build(d, stations, today)
    problems = verify_page(art)
    print(f"📰 {d['titre']}  ({d['categorie']}) — {words(d)} mots, {len(d['faits'])} faits, {len(d['sources'])} sources")
    for n in notes:
        print("  ·", n)
    if problems:
        raise SystemExit("❌ Contrôles de page en échec : " + " ; ".join(problems))
    md = review_md(d, art, notes, problems)
    if args.review_out:
        Path(args.review_out).write_text(md, encoding="utf-8")
    if args.dry_run:
        print("\n(dry-run : rien n'est écrit)")
        return
    enregistrer(d, art, today)
    print(f"\n✅ articles/{art['slug']}.html + {HISTORY.name} + contenus.json")


if __name__ == "__main__":
    main()
