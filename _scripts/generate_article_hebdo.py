#!/usr/bin/env python3
"""
generate_article_hebdo.py — SnowFinder : UN article « classement chiffré » par semaine.

Aucune IA : tous les chiffres viennent de stations-data.js, les textes sont des gabarits.
Donc zéro risque d'invention, zéro coût d'API.

Ce que fait le script :
  1. choisit un sujet pas encore publié (format × zone), ex. « les stations les moins chères en Savoie »
     — la France d'abord, sans refaire deux fois le même format/la même zone d'affilée ;
  2. construit la page articles/<slug>.html (mise en page des articles SnowFinder, liens vers les
     fiches, liens Booking + Expedia en affiliation CJ, données structurées Article + ItemList) ;
  3. ajoute l'article en tête de contenus.json (accueil + « Toutes nos actus ») et le note dans
     articles_hebdo.json (historique pour ne pas se répéter).

Le workflow article-hebdo.yml ouvre ensuite une pull request : rien n'est publié avant votre « Merge ».

Utilisation :
  python3 _scripts/generate_article_hebdo.py --list                 # sujets possibles, du plus au moins prioritaire
  python3 _scripts/generate_article_hebdo.py --key prix:savoie      # sujet imposé
  python3 _scripts/generate_article_hebdo.py --dry-run               # n'écrit rien
  python3 _scripts/generate_article_hebdo.py --review-out /tmp/r.md # compte rendu pour la pull request
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from datetime import date
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_comparatifs as gc  # noqa: E402

ROOT = gc.REPO_ROOT
ARTICLES_DIR = ROOT / "articles"
HISTORY = ROOT / "articles_hebdo.json"
CONTENUS = ROOT / "contenus.json"
BASE_URL = gc.BASE_URL
NBSP = " "


# ── Zones (où) ───────────────────────────────────────────────────────────────

def _dept(s: dict) -> str:
    return (s.get("region") or "").split(",")[-1].strip()


# clé : (libellé « en … », slug, niveau, filtre pays/zone)
SCOPES = {
    "france":      ("en France", "france", 0, lambda s: not s.get("pays")),
    "savoie":      ("en Savoie", "savoie", 1, lambda s: not s.get("pays") and _dept(s) == "Savoie"),
    "haute-savoie": ("en Haute-Savoie", "haute-savoie", 1, lambda s: not s.get("pays") and _dept(s) == "Haute-Savoie"),
    "isere":       ("en Isère", "isere", 1, lambda s: not s.get("pays") and _dept(s) == "Isère"),
    "hautes-alpes": ("dans les Hautes-Alpes", "hautes-alpes", 1, lambda s: not s.get("pays") and _dept(s) == "Hautes-Alpes"),
    "alpes-maritimes": ("dans les Alpes-Maritimes", "alpes-maritimes", 1, lambda s: not s.get("pays") and _dept(s) == "Alpes-Maritimes"),
    "hautes-pyrenees": ("dans les Hautes-Pyrénées", "hautes-pyrenees", 1, lambda s: not s.get("pays") and _dept(s) == "Hautes-Pyrénées"),
    "alpes-du-nord": ("dans les Alpes du Nord françaises", "alpes-du-nord", 1, lambda s: not s.get("pays") and s.get("massif") == "Alpes du Nord"),
    "alpes-du-sud": ("dans les Alpes du Sud", "alpes-du-sud", 1, lambda s: not s.get("pays") and s.get("massif") == "Alpes du Sud"),
    "pyrenees":    ("dans les Pyrénées françaises", "pyrenees", 1, lambda s: not s.get("pays") and s.get("massif") == "Pyrénées"),
    "vosges":      ("dans les Vosges", "vosges", 1, lambda s: not s.get("pays") and s.get("massif") == "Vosges"),
    "jura":        ("dans le Jura", "jura", 1, lambda s: not s.get("pays") and s.get("massif") == "Jura"),
    "massif-central": ("dans le Massif central", "massif-central", 1, lambda s: not s.get("pays") and s.get("massif") == "Massif Central"),
    "autriche":    ("en Autriche", "autriche", 2, lambda s: s.get("pays") == "AT"),
    "suisse":      ("en Suisse", "suisse", 2, lambda s: s.get("pays") == "CH"),
    "italie":      ("en Italie", "italie", 2, lambda s: s.get("pays") == "IT"),
}
NO_PRICE_SCOPES = {"suisse"}   # forfaits suisses : devise à vérifier avant de comparer des prix

MIN_KM_PRICE = 20              # pour les classements de prix : on ignore les mini-domaines


# ── Formats (quoi) ───────────────────────────────────────────────────────────

def _pistes_total(s):
    p = s.get("pistes") or {}
    return sum(p.get(k, 0) for k in ("v", "b", "r", "n"))


def _share_easy(s):
    p, t = s.get("pistes") or {}, _pistes_total(s)
    return (p.get("v", 0) + p.get("b", 0)) / t if t else 0


FORMATS = {
    "domaines": dict(
        slug="plus-grands-domaines-skiables", needs_price=False,
        eligible=lambda s: s.get("km", 0) > 0,
        value=lambda s: s["km"], reverse=True, dedupe_domain=True,
        title=lambda n, sc: f"Les {n} plus grands domaines skiables {sc}",
        cat_line="longueur du domaine skiable (km de pistes)"),
    "prix": dict(
        slug="stations-ski-moins-cheres", needs_price=True,
        eligible=lambda s: s.get("forfait", 0) > 0 and s.get("km", 0) >= MIN_KM_PRICE,
        value=lambda s: s["forfait"], reverse=False, dedupe_domain=False,
        title=lambda n, sc: f"Les {n} stations de ski les moins chères {sc} : forfait journée",
        cat_line="prix du forfait journée adulte"),
    "altitude": dict(
        slug="stations-ski-plus-hautes", needs_price=False,
        eligible=lambda s: s.get("alt_max", 0) > 0 and s.get("km", 0) >= 10,
        value=lambda s: s["alt_max"], reverse=True, dedupe_domain=True,
        title=lambda n, sc: f"Les {n} domaines skiables où l'on skie le plus haut {sc}",
        cat_line="point culminant du domaine skiable"),
    "rapport": dict(
        slug="meilleur-rapport-pistes-prix", needs_price=True,
        eligible=lambda s: s.get("forfait", 0) > 0 and s.get("km", 0) >= MIN_KM_PRICE,
        value=lambda s: round(s["km"] / s["forfait"], 2), reverse=True, dedupe_domain=True,
        title=lambda n, sc: f"Les {n} stations au meilleur rapport km de pistes / prix du forfait {sc}",
        cat_line="kilomètres de pistes par euro de forfait journée"),
    "debutants": dict(
        slug="meilleures-stations-ski-debutants", needs_price=False,
        eligible=lambda s: _pistes_total(s) >= 10 and s.get("km", 0) >= 10,
        value=lambda s: round(_share_easy(s) * 100), reverse=True, dedupe_domain=False,
        title=lambda n, sc: f"Les {n} stations de ski les plus adaptées aux débutants {sc}",
        cat_line="part de pistes vertes et bleues"),
    "notes": dict(
        slug="stations-ski-mieux-notees", needs_price=False,
        eligible=lambda s: s.get("score", 0) > 0 and s.get("km", 0) >= 10,
        value=lambda s: s["score"], reverse=True, dedupe_domain=False,
        title=lambda n, sc: f"Les {n} stations de ski les mieux notées {sc}",
        cat_line="note SnowFinder"),
}

MIN_ENTRIES = 6

# Formats volontairement suspendus : le champ « km » des fiches ne mesure pas toujours le domaine relié
# (ex. Val d'Isère = 150 km sur la fiche, 300 km avec Tignes), donc un classement « plus grands domaines »
# ou « km par euro » serait faux. À réactiver quand les domaines reliés (DOMAINES) serviront de source.
DISABLED_FORMATS = {"domaines", "rapport"}


# ── Données ──────────────────────────────────────────────────────────────────

def load_stations() -> list:
    c = gc.STATIONS_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.SF_DATA\s*=\s*(\[.*\]);", c, re.DOTALL)
    if not m:
        raise SystemExit("❌ window.SF_DATA introuvable dans stations-data.js")
    return [s for s in json.loads(m.group(1)) if s.get("ok", True) and not s.get("ferme")]


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def fmt_n(n) -> str:
    return f"{int(n):,}".replace(",", NBSP)


# Domaines skiables reliés : une seule station par domaine dans les classements (évite les doublons).
DOMAIN_GROUPS = {
    "trois-vallees": ["Courchevel", "Méribel", "Val Thorens", "Les Menuires", "Saint-Martin-de-Belleville", "La Tania", "Orelle", "Brides-les-Bains", "Les Allues"],
    "paradiski": ["Les Arcs", "La Plagne", "Peisey-Vallandry", "Champagny-en-Vanoise", "Montchavin-Les Coches", "Bourg-Saint-Maurice"],
    "espace-killy": ["Val d'Isère", "Tignes"],
    "alpe-d-huez": ["Alpe d'Huez", "Auris", "Oz-en-Oisans", "Vaujany", "Villard-Reculas"],
    "sybelle": ["La Toussuire", "Le Corbier", "Saint-Sorlin-d'Arves", "Saint-Jean-d'Arves", "Les Bottières", "Saint-Colomban-des-Villards"],
    "grand-massif": ["Flaine", "Samoëns", "Morillon", "Les Carroz", "Sixt-Fer-à-Cheval"],
    "portes-du-soleil": ["Morzine", "Avoriaz", "Les Gets", "Châtel", "Morgins", "Champéry", "Abondance", "La Chapelle-d'Abondance", "Saint-Jean-d'Aulps"],
    "evasion-mont-blanc": ["Megève", "Saint-Gervais", "Combloux", "Saint-Nicolas-de-Véroce", "Les Contamines-Montjoie", "Les Houches"],
    "serre-chevalier": ["Serre Chevalier", "Briançon", "Le Monêtier-les-Bains"],
    "vars-risoul": ["Vars", "Risoul"],
    "val-d-allos": ["Pra-Loup", "Val d'Allos"],
    "quatre-vallees": ["Verbier", "Nendaz", "Veysonnaz", "Thyon", "La Tzoumaz"],
    "matterhorn": ["Zermatt", "Breuil-Cervinia", "Valtournenche"],
    "monte-rosa": ["Champoluc", "Gressoney-La-Trinité", "Alagna Valsesia"],
    "laax": ["Laax", "Flims", "Falera"],
    "arosa-lenzerheide": ["Arosa", "Lenzerheide"],
    "silvretta": ["Ischgl", "Samnaun"],
    "tonale": ["Ponte di Legno", "Passo del Tonale"],
    "arlberg": ["St. Anton am Arlberg", "St. Christoph", "Stuben", "Lech", "Zürs", "Warth-Schröcken"],
    "skiwelt": ["Söll", "Ellmau", "Scheffau", "Going", "Brixen im Thale", "Westendorf", "Hopfgarten"],
    "saalbach": ["Saalbach", "Hinterglemm", "Leogang", "Fieberbrunn"],
    "kitzbuhel": ["Kitzbühel", "Kirchberg in Tirol"],
    "serfaus": ["Serfaus", "Fiss", "Ladis"],
    "zillertal": ["Zell am Ziller", "Gerlos", "Königsleiten", "Hochkrimml"],
    "val-gardena": ["Ortisei", "Santa Cristina", "Selva di Val Gardena"],
    "campiglio": ["Madonna di Campiglio", "Pinzolo", "Folgarida", "Marilleva"],
    "grandvalira": ["Pas de la Casa", "Grau Roig", "Soldeu", "El Tarter", "Canillo", "Encamp"],
    
}
DOMAIN_NAMES = {
    "trois-vallees": "Les Trois Vallées", "paradiski": "Paradiski", "espace-killy": "Tignes – Val d'Isère",
    "alpe-d-huez": "Alpe d'Huez Grand Domaine", "sybelle": "Les Sybelles", "grand-massif": "Le Grand Massif",
    "portes-du-soleil": "Les Portes du Soleil", "evasion-mont-blanc": "Évasion Mont-Blanc", "serre-chevalier": "Serre Chevalier Vallée",
    "vars-risoul": "Vars – Risoul (Forêt Blanche)", "val-d-allos": "Pra-Loup – Val d'Allos (Espace Lumière)",
    "quatre-vallees": "Les 4 Vallées", "matterhorn": "Zermatt – Cervinia (Matterhorn)", "monte-rosa": "Monterosa Ski",
    "laax": "Flims – Laax – Falera", "arosa-lenzerheide": "Arosa – Lenzerheide", "silvretta": "Ischgl – Samnaun",
    "tonale": "Ponte di Legno – Tonale", "arlberg": "Ski Arlberg", "skiwelt": "SkiWelt Wilder Kaiser – Brixental",
    "saalbach": "Saalbach – Hinterglemm – Leogang – Fieberbrunn", "kitzbuhel": "Kitzbühel – Kirchberg", "serfaus": "Serfaus – Fiss – Ladis",
    "zillertal": "Zillertal Arena", "val-gardena": "Val Gardena", "campiglio": "Madonna di Campiglio – Pinzolo",
    "grandvalira": "Grandvalira",
}
_DOMAIN_OF = {n: k for k, ns in DOMAIN_GROUPS.items() for n in ns}


def domain_key(s: dict):
    if s["name"] in _DOMAIN_OF:
        return ("grp", _DOMAIN_OF[s["name"]])
    if s.get("km", 0) >= 30:
        return (s.get("pays"), s.get("massif"), s["km"], s.get("alt_max"))
    return None


def ranking(fmt_key: str, scope_key: str, stations: list):
    """Retourne (entrées classées, nombre de stations étudiées) ; entrées = dict(station, value, shared)."""
    fmt, scope = FORMATS[fmt_key], SCOPES[scope_key]
    pool = [s for s in stations if scope[3](s) and fmt["eligible"](s)]
    studied = len(pool)
    pool.sort(key=lambda s: (-fmt["value"](s) if fmt["reverse"] else fmt["value"](s),
                             -s.get("score", 0), -s.get("km", 0), s["name"]))
    entries, seen = [], {}
    for s in pool:
        k = domain_key(s) if fmt["dedupe_domain"] else None
        if k is not None and k in seen:
            seen[k]["shared"].append(s["name"])
            continue
        e = {"s": s, "value": fmt["value"](s), "shared": [], "group": k[1] if (k and k[0] == "grp") else None}
        entries.append(e)
        if k is not None:
            seen[k] = e
    for e in entries:
        if not e["shared"]:
            e["group"] = None          # station seule dans la base : on garde son nom
    return entries, studied


def n_for(count: int) -> int:
    return 10 if count >= 15 else 8 if count >= 10 else 6 if count >= MIN_ENTRIES else 0


def all_candidates(stations: list, history: list) -> list:
    """Sujets possibles non encore publiés, avec leur priorité (plus grand = mieux)."""
    done = {h["key"] for h in history}
    last = history[-1] if history else {}
    out = []
    for fk, fmt in FORMATS.items():
        for sk, sc in SCOPES.items():
            key = f"{fk}:{sk}"
            if fk in DISABLED_FORMATS or key in done or (fmt["needs_price"] and sk in NO_PRICE_SCOPES):
                continue
            entries, studied = ranking(fk, sk, stations)
            n = n_for(len(entries))
            if not n:
                continue
            prio = (3.0 if sc[2] <= 1 else 0.0)                       # la France d'abord
            prio += 1.0 if last.get("format") != fk else 0.0           # varier le format
            prio += 1.0 if last.get("scope") != sk else 0.0            # varier la zone
            prio += 0.8 if sk == "france" else 0.5 if sc[2] == 1 and sk in ("savoie", "haute-savoie", "alpes-du-nord") else 0.0
            prio += math.log(max(studied, 2)) / 10                    # zones plus larges = plus de recherches
            out.append((prio, key, n, studied))
    out.sort(key=lambda t: (-t[0], t[1]))
    return out


# ── Texte ────────────────────────────────────────────────────────────────────

def link_station(name: str) -> str:
    return f'<a href="/stations/{gc.slugify(name)}.html">{escape(name)}</a>'


def detail_html(e: dict) -> str:
    """Description détaillée de la station (texte SnowFinder) ; pour un domaine, présentée comme un zoom sur sa station la plus haute."""
    s = e["s"]
    d = (s.get("desc_long") or s.get("desc") or "").strip()
    if not d:
        return ""
    lead = f"<strong>Zoom sur {escape(s['name'])} :</strong> " if e.get("group") else ""
    return f"    <p>{lead}{escape(d)}</p>\n"


def entry_name(e: dict) -> str:
    """Nom affiché : le domaine (si station reliée à d'autres) sinon la station."""
    return DOMAIN_NAMES.get(e.get("group"), e["s"]["name"]) if e.get("group") else e["s"]["name"]


def metric_text(fk: str, e: dict) -> str:
    s, v = e["s"], e["value"]
    return {
        "domaines": f"{fmt_n(v)}{NBSP}km de pistes",
        "prix": f"{v}{NBSP}€ le forfait journée",
        "altitude": f"{fmt_n(v)}{NBSP}m",
        "rapport": f"{str(v).replace('.', ',')}{NBSP}km par euro",
        "debutants": f"{v}{NBSP}% de pistes vertes et bleues",
        "notes": f"note {str(v).replace('.', ',')}/5",
    }[fk]


def entry_sentence(fk: str, e: dict) -> str:
    s, v = e["s"], e["value"]
    p = s.get("pistes") or {}
    km, rem = s["km"], s.get("remontees")
    rem_t = f" ({rem} remontées)" if rem else ""
    alt = f"entre {fmt_n(s['alt_min'])}{NBSP}et{NBSP}{fmt_n(s['alt_max'])}{NBSP}m"
    prix = f" Forfait journée adulte : {s['forfait']}{NBSP}€." if s.get("forfait") else ""
    if fk == "domaines":
        t = f"{escape(s['name'])} ouvre un domaine de {fmt_n(km)}{NBSP}km de pistes{rem_t}, {alt}.{prix}"
        if e["shared"]:
            t += " Ce domaine est aussi celui de " + ", ".join(escape(n) for n in e["shared"]) + "."
        return t
    if fk == "prix":
        return (f"Forfait journée adulte à {s['forfait']}{NBSP}€, pour un domaine de {fmt_n(km)}{NBSP}km de pistes"
                f"{rem_t}, {alt}.")
    if fk == "altitude":
        if e.get("group"):
            t = (f"Ce domaine relie plusieurs stations et culmine à {fmt_n(s['alt_max'])}{NBSP}m, "
                 f"à {escape(s['name'])}." + (f" Forfait journée adulte à {escape(s['name'])} : {s['forfait']}{NBSP}€." if s.get("forfait") else ""))
            if e["shared"]:
                t += " Il comprend aussi " + ", ".join(escape(n) for n in e["shared"]) + "."
            return t
        t = (f"Le domaine culmine à {fmt_n(s['alt_max'])}{NBSP}m (point bas : {fmt_n(s['alt_min'])}{NBSP}m), "
             f"sur {fmt_n(km)}{NBSP}km de pistes.{prix}")
        if e["shared"]:
            t += " Ce domaine est aussi celui de " + ", ".join(escape(n) for n in e["shared"]) + "."
        return t
    if fk == "rapport":
        t = (f"{fmt_n(km)}{NBSP}km de pistes pour un forfait journée à {s['forfait']}{NBSP}€ : "
             f"environ {str(v).replace('.', ',')}{NBSP}km de pistes par euro.")
        if e["shared"]:
            t += " Ce domaine est aussi celui de " + ", ".join(escape(n) for n in e["shared"]) + "."
        return t
    if fk == "debutants":
        tot = _pistes_total(s)
        if p.get("pct"):
            body = f"{p['v']}{NBSP}% de pistes vertes et {p['b']}{NBSP}% de bleues"
        else:
            body = f"{p['v']} pistes vertes et {p['b']} bleues sur {tot}"
        return f"{body}, soit {v}{NBSP}% de pistes faciles, sur un domaine de {fmt_n(km)}{NBSP}km.{prix}"
    return f"Note SnowFinder de {str(v).replace('.', ',')}/5, pour {fmt_n(km)}{NBSP}km de pistes {alt}.{prix}"


def points_text(s: dict) -> str:
    pts = [x.strip().rstrip(".") for x in (s.get("pts") or [])[:2] if x and x.strip()]
    return ("À retenir : " + " ; ".join(escape(x) for x in pts) + ".") if pts else ""


def intro(fk: str, sc_en: str, studied: int, n: int, entries: list) -> list:
    where = sc_en
    base = f"Nous avons passé en revue les {studied} stations de notre base {where} qui entrent dans ce classement."
    d = {
        "domaines": f"Quelle est la plus grande station de ski {where} ? Pour répondre, nous avons classé les domaines skiables selon leur longueur, en kilomètres de pistes. {base}",
        "prix": f"Skier sans se ruiner, c'est possible : voici les stations de ski les moins chères {where}, classées selon le prix du forfait journée adulte. {base} Pour éviter les mini-domaines, nous ne gardons que ceux d'au moins {MIN_KM_PRICE}{NBSP}km de pistes.",
        "altitude": f"L'altitude est le meilleur indice d'un enneigement durable. Voici les domaines skiables où l'on skie le plus haut {where}, classés selon leur point culminant. Une station reliée à d'autres est comptée avec son domaine. {base}",
        "rapport": f"Beaucoup de pistes pour peu d'euros : c'est le meilleur rapport qualité-prix sur la neige. Nous avons divisé les kilomètres de pistes de chaque domaine par le prix de son forfait journée adulte pour classer les stations {where}. {base} Seuls les domaines d'au moins {MIN_KM_PRICE}{NBSP}km sont retenus.",
        "debutants": f"Pour une première semaine de ski, mieux vaut un domaine aux pistes douces. Nous avons classé les stations {where} selon la part de pistes vertes et bleues dans leur domaine. {base}",
        "notes": f"Quelles sont les stations les mieux notées {where} ? Voici le classement établi à partir de la note SnowFinder, qui combine le domaine, l'enneigement, l'ambiance et l'équipement. {base}",
    }[fk]
    out = [d]
    if FORMATS[fk]["dedupe_domain"]:
        out.append("Les stations reliées entre elles forment un seul domaine skiable : nous les regroupons et classons le domaine, représenté par sa station la plus haute. Les autres stations du domaine sont citées dans sa description.")
    return out


def _names(entries, k=3):
    return [escape(entry_name(e)) for e in entries[:k]]


def analysis(fk: str, sc_en: str, entries: list, entries_all: list, n: int) -> list:
    """Paragraphes d'analyse tirés des chiffres du classement (aucune donnée inventée)."""
    a, z = entries[0], entries[-1]
    A, Z = escape(entry_name(a)), escape(entry_name(z))
    va, vz = a["value"], z["value"]
    groups = [e for e in entries if e.get("group")]
    out = []
    if fk == "altitude":
        above = sum(1 for e in entries if e["value"] >= 3000)
        out.append(f"{A} domine ce classement avec {fmt_n(va)}{NBSP}m, soit {fmt_n(va - vz)}{NBSP}m de plus que le n°{n}, {Z} ({fmt_n(vz)}{NBSP}m). "
                   f"{above} domaine{'s' if above > 1 else ''} sur {n} {'dépassent' if above > 1 else 'dépasse'} les 3{NBSP}000{NBSP}m.")
        out.append("Pourquoi l'altitude compte : en moyenne, la température baisse d'environ 0,6 °C tous les 100 mètres. "
                   "Plus un domaine monte haut, plus la neige a de chances de tenir longtemps, surtout en début et en fin de saison. "
                   "Le point culminant n'est toutefois pas l'altitude des villages : un domaine peut culminer à 3 000 m tout en étant bâti à 1 800 m, "
                   "et l'exposition des pistes pèse aussi sur la qualité de la neige.")
        if groups:
            out.append(f"{len(groups)} entrée{'s' if len(groups) > 1 else ''} de ce classement "
                       f"{'sont des domaines qui regroupent' if len(groups) > 1 else 'est un domaine qui regroupe'} plusieurs stations reliées par les pistes "
                       f"({', '.join(_names(groups, 3))}…). Elles sont comptées une seule fois, avec leur point le plus haut.")
    elif fk == "prix":
        out.append(f"{A} est la moins chère du classement ({metric_text(fk, a)}), contre {metric_text(fk, z)} pour {Z}, "
                   f"soit {va and (vz - va)}{NBSP}€ d'écart sur une journée de ski.")
        out.append("Le forfait journée adulte est le tarif public affiché : il baisse souvent avec un forfait de plusieurs jours, "
                   "un achat en ligne à l'avance ou une période creuse hors vacances scolaires. Sur une semaine, l'écart entre ces stations se creuse.")
    elif fk == "debutants":
        out.append(f"{A} arrive en tête avec {metric_text(fk, a)}, devant {_names(entries[1:2])[0] if n > 1 else ''}. "
                   f"Le n°{n}, {Z}, affiche encore {metric_text(fk, z)}.")
        out.append("Une piste verte est très facile, une bleue facile : plus leur part est élevée, plus le domaine pardonne les premiers virages. "
                   "Pensez aussi aux jardins des neiges, aux écoles de ski et aux remontées adaptées aux débutants avant de choisir.")
    else:
        out.append(f"{A} prend la tête du classement ({metric_text(fk, a)}), {Z} ferme la marche du top {n} ({metric_text(fk, z)}).")
        out.append("Ce classement repose sur nos données chiffrées. Il donne un point de départ : le mieux est ensuite de comparer deux ou trois stations côte à côte.")
    return out


def faq_items(fk: str, sc_en: str, entries: list, entries_all: list, n: int) -> list:
    """Questions / réponses (texte brut, sans HTML) tirées du classement."""
    a = entries[0]
    A, ma = entry_name(a), metric_text(fk, a).replace(NBSP, " ")
    top3 = ", ".join(entry_name(e) for e in entries[:3])
    if fk == "altitude":
        return [
            (f"Où skie-t-on le plus haut {sc_en} ?", f"D'après les données SnowFinder, {A} est le domaine qui culmine le plus haut {sc_en} : {ma}."),
            (f"Quels domaines choisir pour avoir de la neige plus longtemps ?", f"Les domaines les plus hauts du classement ({top3}) sont généralement les plus sûrs en début et fin de saison, mais l'enneigement dépend aussi de la météo de l'année."),
            ("Un point culminant élevé garantit-il de la neige partout ?", "Non. Le point culminant indique où le domaine monte, pas où se trouvent les villages ni toutes les pistes. Consultez l'enneigement en temps réel avant de partir."),
        ]
    if fk == "prix":
        prices = [x["s"]["forfait"] for x in entries_all_price(entries_all)]
        med = int(statistics.median(prices)) if prices else None
        q2 = (f"Le forfait journée adulte médian {sc_en} est d'environ {med} € pour les stations d'au moins {MIN_KM_PRICE} km de pistes." if med else "Les tarifs varient selon la station et la date.")
        return [
            (f"Quelle est la station de ski la moins chère {sc_en} ?", f"D'après nos données, {A} est la moins chère : {ma}."),
            (f"Combien coûte un forfait de ski {sc_en} ?", q2),
            ("Comment payer moins cher son forfait ?", "Acheter en ligne à l'avance, choisir un forfait de plusieurs jours et éviter les vacances scolaires permettent en général de réduire la facture."),
        ]
    if fk == "debutants":
        return [
            (f"Quelle station choisir pour débuter {sc_en} ?", f"{A} arrive en tête de notre classement avec {ma}. Suivent {', '.join(entry_name(e) for e in entries[1:3])}."),
            ("Que veut dire une piste verte ou bleue ?", "Une piste verte est très facile et une bleue facile : ce sont les plus adaptées aux premiers jours de ski."),
            ("Faut-il prendre des cours quand on débute ?", "Les cours collectifs avec un moniteur permettent de progresser plus vite et en sécurité ; réservez-les avec le séjour."),
        ]
    return [
        (f"Quel est le n°1 de ce classement {sc_en} ?", f"D'après les données SnowFinder, {A} arrive en tête : {ma}."),
        ("Comment ce classement est-il établi ?", "À partir des données de notre base de stations, sans avis subjectif ; les critères sont détaillés plus bas."),
        ("Peut-on comparer ces stations ?", "Oui, avec notre comparateur et nos duels de stations."),
    ]


def conclusion(fk: str, sc_en: str, entries: list, n: int) -> list:
    a, z = entries[0], entries[-1]
    A, Z = escape(entry_name(a)), escape(entry_name(z))
    unit = "domaines" if FORMATS[fk]["dedupe_domain"] else "stations"
    crit = {"altitude": "l'altitude", "prix": "le prix du forfait", "debutants": "la facilité des pistes",
            "domaines": "la taille du domaine", "rapport": "le rapport km de pistes / prix", "notes": "la note SnowFinder"}[fk]
    return [f"En résumé, {A} prend la première place de ce classement {sc_en} ({metric_text(fk, a)}) et {Z} clôt le top {n} ({metric_text(fk, z)}). "
            f"Mais {crit} n'est qu'un critère parmi d'autres : l'ambiance, la taille du domaine, l'hébergement et votre budget comptent autant pour choisir.",
            f"Pour affiner, consultez les fiches détaillées de ces {unit}, comparez-en deux ou trois dans notre comparateur, "
            "ou filtrez toutes les stations selon vos critères."]


def fiches_html(entries: list, stations: list) -> str:
    by_name = {s["name"]: s for s in stations}
    items = []
    for e in entries:
        names = [e["s"]["name"]] + list(e["shared"])
        links = [f'<a href="/stations/{gc.slugify(n)}.html">{escape(n)}</a>' for n in names if n in by_name]
        if not links:
            continue
        label = f"<strong>{escape(entry_name(e))}</strong> : " if e.get("group") else ""
        items.append(f"<li>{label}{' · '.join(links)}</li>")
    return "    <ul>\n      " + "\n      ".join(items) + "\n    </ul>"


def keys_text(fk: str, sc_en: str, entries: list, vals_all: list, n: int) -> str:
    a, z = entries[0], entries[-1]
    A, Z = escape(entry_name(a)), escape(entry_name(z))
    ma, mz = metric_text(fk, a), metric_text(fk, z)
    second = entries[1]
    B, mb = escape(entry_name(second)), metric_text(fk, second)
    extra = ""
    if fk in ("prix", "rapport"):
        prices = [x["s"]["forfait"] for x in entries_all_price(vals_all)]
        if prices:
            extra = f" · forfait journée médian {sc_en} (stations d'au moins {MIN_KM_PRICE}{NBSP}km) : {int(statistics.median(prices))}{NBSP}€"
    lead = {"prix": "la moins chère", "domaines": "la plus grande", "altitude": "le domaine où l'on skie le plus haut",
            "rapport": "la mieux placée", "debutants": "la plus facile", "notes": "la mieux notée"}[fk]
    return (f"<strong>À retenir :</strong> {A} est {lead} ({ma}), devant {B} ({mb}) · "
            f"la {n}<sup>e</sup> du classement, {Z}, affiche {mz}{extra}.")


def entries_all_price(entries_all: list) -> list:
    return [{"s": e["s"]} for e in entries_all if e["s"].get("forfait")]


# ── Page HTML ────────────────────────────────────────────────────────────────

PAGE_CSS = """:root{--blue:#3a7db8;--blue-dark:#1a5a8a;--text:#22303e;--text-mid:#4a5a6a;--text-light:#8a97a3;--bg:#f7f9fb;--white:#fff;--cat:#1a5a8a}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"DM Sans",-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
a{color:var(--blue);text-decoration:none}
article a{text-decoration:underline}
.wrap{max-width:720px;margin:0 auto;padding:0 20px}
.breadcrumb{font-size:.82rem;color:var(--text-light);margin:20px 0 8px}
.breadcrumb a{color:var(--text-light)}
.art-cat{display:inline-block;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--cat);background:color-mix(in srgb, var(--cat) 12%, white);padding:4px 10px;border-radius:20px;margin-bottom:14px}
h1{font-family:"DM Serif Display",serif;font-size:1.9rem;line-height:1.25;margin-bottom:14px;color:var(--text)}
.art-meta{font-size:.82rem;color:var(--text-light);margin-bottom:28px;white-space:nowrap;overflow:hidden}
.art-meta span{margin-right:12px}
article h2{font-family:"DM Serif Display",serif;font-size:1.45rem;margin:34px 0 10px;color:var(--text)}
article h3{font-family:"DM Serif Display",serif;font-size:1.3rem;margin:28px 0 8px;color:var(--text)}
article p{font-size:1.02rem;color:var(--text-mid);margin-bottom:14px}
article ul{margin:0 0 14px 20px;color:var(--text-mid)}
article li{margin-bottom:6px;font-size:1.02rem}
.keys{background:#e8f3fb;border-left:4px solid var(--blue);border-radius:10px;padding:14px 16px;margin:20px 0}
.keys p{margin:0;color:var(--text)}
figure{margin:18px 0}
figure img{width:100%;border-radius:12px;object-fit:cover;max-height:320px;display:block}
figcaption{font-size:.78rem;color:var(--text-light);margin-top:6px}
.rank{display:flex;align-items:baseline;gap:10px}
.rank .n{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:var(--blue-dark);color:#fff;font-weight:700;font-size:1rem;font-family:"DM Sans",sans-serif}
.metric{display:inline-block;background:#e8f3fb;color:var(--blue-dark);font-weight:700;font-size:.88rem;padding:3px 11px;border-radius:14px;margin:0 0 10px}
.links{display:flex;flex-wrap:wrap;gap:8px;margin:2px 0 6px}
.links a{display:inline-block;font-size:.84rem;font-weight:700;padding:7px 13px;border-radius:18px;text-decoration:none!important;border:1.5px solid #d3e3f1;background:#fff;color:var(--blue-dark)}
.links a.bk{background:#003d96;border-color:#003d96;color:#fff}
.links a.ex{background:#ffcc00;border-color:#ffcc00;color:#1a2060}
.disc{font-size:.72rem;color:var(--text-light);margin:4px 0 0}
.src{font-size:.82rem;color:var(--text-light);margin-top:22px}
footer{margin:50px 0 30px;padding-top:24px;border-top:1px solid #e4e9ee;font-size:.85rem;color:var(--text-light)}
footer a{color:var(--blue)}
.back-link{display:inline-block;margin:24px 0 0;font-size:.9rem;font-weight:600}
"""
PAGE_CSS += gc.SF_BAR_CSS.replace("%MAXW%", "720px") + gc.SF_BOTTOMNAV_CSS


MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]


def fr_date(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d}{'er' if d == 1 else ''} {MONTHS[m - 1]} {y}"


def related_duels(names: set) -> list:
    cont = load_json(CONTENUS, {})
    out = []
    for d in cont.get("duels", []):
        if d.get("a") in names or d.get("b") in names:
            slug = f"{gc.slugify(d['a'])}-vs-{gc.slugify(d['b'])}"
            if (gc.COMPARATIFS_DIR / f"{slug}.html").exists():
                out.append((slug, d["a"], d["b"]))
    return out[:3]


def render_page(*, slug: str, title: str, excerpt: str, category: str, body: str, today: str,
                read_min: int, hero_photo: str = "", extra_graph: list | None = None) -> str:
    """Gabarit commun à tous les articles automatiques (classements, actualités, portraits…)."""
    url = f"{BASE_URL}/articles/{slug}.html"
    og_img = f"{BASE_URL}{hero_photo}" if hero_photo else f"{BASE_URL}/logo.png"
    ld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article", "headline": title, "description": excerpt, "datePublished": today, "dateModified": today,
             "author": {"@type": "Organization", "name": "SnowFinder"},
             "publisher": {"@type": "Organization", "name": "SnowFinder",
                           "logo": {"@type": "ImageObject", "url": f"{BASE_URL}/logo.png"}},
             "image": og_img, "mainEntityOfPage": url},
        ] + list(extra_graph or [])}, ensure_ascii=False, indent=2)

    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{escape(title)} | SnowFinder</title>
<meta name="description" content="{escape(excerpt, quote=True)}">
<link rel="canonical" href="{url}">
<link rel="apple-touch-icon" href="/logo.png">
<link rel="icon" type="image/png" href="/logo.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="SnowFinder">
<meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(excerpt, quote=True)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_img}">
<meta property="og:locale" content="fr_FR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(title, quote=True)}">
<meta name="twitter:description" content="{escape(excerpt, quote=True)}">
<meta name="twitter:image" content="{og_img}">
<script type="application/ld+json">
{ld}
</script>
<style>
{PAGE_CSS}</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
</head>
<body>
{gc.SF_TOPBAR}
{gc.sf_bar_html('/articles/toutes-les-actus.html', '📰 Toutes nos actus')}<div class="wrap">
  <div class="breadcrumb"><a href="/index.html">Accueil</a> › <a href="/articles/toutes-les-actus.html">Actus</a> › {escape(title)}</div>
  <span class="art-cat">{escape(category)}</span>
  <h1>{escape(title)}</h1>
  <div class="art-meta"><span>✍️ Rédaction SnowFinder</span><span>📅 {fr_date(today)}</span><span>⏱ {read_min} min</span></div>
  <article>
{body}
  </article>
  <a class="back-link" href="/articles/toutes-les-actus.html">← Toutes nos actus</a>
  <footer>
    <p><strong>SnowFinder</strong> — Le guide des stations de ski en France et en Europe</p>
    <p><a href="/recherche.html">Trouver une station</a> · <a href="/comparateur.html">Comparateur</a> · <a href="/mentions-legales.html">Mentions légales</a></p>
  </footer>
</div>
{gc.SF_BOTTOMNAV_HTML}</body>
</html>
"""
    return gc.add_ga(page)


def build(fk: str, sk: str, stations: list, today: str) -> dict:
    fmt, scope = FORMATS[fk], SCOPES[sk]
    sc_en = scope[0]
    entries_all, studied = ranking(fk, sk, stations)
    n = n_for(len(entries_all))
    if not n:
        raise SystemExit(f"❌ Pas assez de stations pour {fk}:{sk}")
    entries = entries_all[:n]
    title = fmt["title"](n, sc_en)
    slug = f"{fmt['slug']}-{scope[1]}"

    unit_pl = "domaines skiables" if fmt["dedupe_domain"] else "stations"
    hero_name = entries[0]["s"]["name"]
    hero_photo = gc.station_photo(hero_name)
    hero_is_real = bool(hero_photo)
    hero_src = hero_photo or gc.RESCUE_PHOTOS[entries[0]["s"]["id"] % len(gc.RESCUE_PHOTOS)]
    caption = (f"{escape(entry_name(entries[0]))}, n°1 de ce classement." if hero_is_real
               else f"Photo d'illustration — {escape(entry_name(entries[0]))} est n°1 de ce classement.")

    first_metric = metric_text(fk, entries[0])
    excerpt = (f"{entry_name(entries[0])} arrive en tête ({first_metric.replace(NBSP, ' ')}) : le classement chiffré "
               f"des {n} {unit_pl} {sc_en}, à partir des données SnowFinder.")

    body = []
    for t in intro(fk, sc_en, studied, n, entries):
        body.append(f"    <p>{t}</p>")
    body.append(f'    <figure>\n      <img src="{hero_src}" alt="{escape(hero_name)}" loading="lazy">\n      <figcaption>{caption}</figcaption>\n    </figure>')
    body.append(f'    <div class="keys"><p>{keys_text(fk, sc_en, entries, entries_all, n)}</p></div>')
    body.append(f"    <h2>Le classement : {n} {unit_pl}</h2>")
    for i, e in enumerate(entries, 1):
        s = e["s"]
        sl = gc.slugify(s["name"])
        pts = points_text(s)
        body.append(
            f'    <h3 class="rank"><span class="n">{i}</span><span>{escape(entry_name(e))}</span></h3>\n'
            f'    <span class="metric">{metric_text(fk, e)}</span>\n'
            f'    <p>{entry_sentence(fk, e)}</p>\n'
            f'{detail_html(e)}'
            f'    <div class="links">\n'
            f'      <a href="/stations/{sl}.html">{"Fiche de " + escape(s["name"]) if e.get("group") else "Fiche complète"}</a>\n'
            f'      <a class="bk" href="{gc.booking_url(s["name"], sl)}" target="_blank" rel="noopener sponsored">🏨 Booking</a>\n'
            f'      <a class="ex" href="{gc.expedia_url(s["name"], sl)}" target="_blank" rel="noopener sponsored">✈️ Expedia</a>\n'
            f'    </div>')
    body.append('    <p class="disc">Liens affiliés — prix identiques, aucune commission prélevée sur vous.</p>')

    body.append("    <h2>Ce que révèle ce classement</h2>")
    for t_ in analysis(fk, sc_en, entries, entries_all, n):
        body.append(f"    <p>{t_}</p>")
    faq = faq_items(fk, sc_en, entries, entries_all, n)
    body.append("    <h2>Questions fréquentes</h2>")
    for q_, a_ in faq:
        body.append(f"    <h3>{escape(q_)}</h3>\n    <p>{escape(a_)}</p>")
    body.append("    <h2>Conclusion</h2>")
    for t_ in conclusion(fk, sc_en, entries, n):
        body.append(f"    <p>{t_}</p>")
    body.append("    <h2>Les fiches des stations de ce classement</h2>")
    body.append(fiches_html(entries, stations))
    body.append("    <h2>Comment lire ce classement ?</h2>")
    body.append(f"    <p>Le critère est le suivant : {fmt['cat_line']}. Les chiffres viennent de la base SnowFinder (domaine, altitudes, remontées, pistes). "
                "Les prix sont des forfaits journée adulte au tarif public, donnés à titre indicatif : ils changent selon la date, la durée et les offres en ligne, "
                "vérifiez-les sur le site de la station avant de réserver.</p>")

    names = {e["s"]["name"] for e in entries}
    rel = related_duels(names)
    more = []
    for slug_d, a, b in rel:
        more.append(f'<li>Duel : <a href="/comparatifs/{slug_d}.html">{escape(a)} vs {escape(b)}</a></li>')
    more.append('<li>Filtrer toutes les stations selon vos critères : <a href="/recherche.html">trouver ma station</a></li>')
    more.append('<li>Comparer plusieurs stations côte à côte : <a href="/comparateur.html">le comparateur</a></li>')
    more.append('<li>Tous nos duels : <a href="/comparatifs/tous-les-comparatifs.html">comparatifs de stations</a></li>')
    body.append("    <h2>Pour aller plus loin</h2>\n    <ul>\n      " + "\n      ".join(more) + "\n    </ul>")
    body.append(f'    <p class="src">Sources : données SnowFinder (domaines skiables, forfaits publics adulte 1 jour), sites officiels des stations. Mis à jour le {fr_date(today)}.</p>')

    text_words = len(re.sub(r"<[^>]+>", " ", "\n".join(body)).split())
    read_min = max(3, math.ceil(text_words / 200))
    item_list = {"@type": "ItemList", "name": title, "itemListOrder": "https://schema.org/ItemListOrderAscending",
                 "numberOfItems": n,
                 "itemListElement": [{"@type": "ListItem", "position": i, "name": entry_name(e),
                                      "url": f"{BASE_URL}/stations/{gc.slugify(e['s']['name'])}.html"}
                                     for i, e in enumerate(entries, 1)]}
    page = render_page(slug=slug, title=title, excerpt=excerpt, category="Classement", body="\n".join(body),
                       today=today, read_min=read_min, hero_photo=hero_photo if hero_is_real else "",
                       extra_graph=[item_list, {"@type": "FAQPage", "mainEntity": [
                           {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in faq]}])
    return {"words": text_words, "slug": slug, "title": title, "excerpt": excerpt, "html": page, "read_min": read_min,
            "img": hero_photo or hero_src, "entries": entries, "studied": studied, "n": n,
            "hero_real": hero_is_real, "related": rel}


# ── Contrôles ────────────────────────────────────────────────────────────────

def verify(art: dict, fk: str) -> list:
    pb, h = [], art["html"]
    fmt = FORMATS[fk]
    vals = [e["value"] for e in art["entries"]]
    srt = sorted(vals, reverse=fmt["reverse"])
    if vals != srt:
        pb.append("classement mal ordonné")
    if len({e["s"]["id"] for e in art["entries"]}) != len(art["entries"]):
        pb.append("station en double")
    if len(art["entries"]) < MIN_ENTRIES:
        pb.append("trop peu de stations")
    if "tkqlhce.com" not in h or "jdoqocy.com" not in h:
        pb.append("liens CJ Booking/Expedia absents")
    if re.search(r'href="https://www\.(booking|expedia)', h):
        pb.append("lien Booking/Expedia direct (non CJ)")
    if h.count('class="bk"') != len(art["entries"]) or h.count('class="ex"') != len(art["entries"]):
        pb.append("une station sans lien Booking/Expedia")
    words = len(re.sub(r"<[^>]+>", " ", h[h.find("<h1"):h.find("Pour aller plus loin")]).split())
    if words < 700:
        pb.append(f"article trop court ({words} mots)")
    if not art["hero_real"] and "Photo d'illustration" not in h:
        pb.append("photo de secours sans légende")
    return pb


# ── Enregistrement + compte rendu ────────────────────────────────────────────

def enregistrer(art: dict, fk: str, sk: str, today: str) -> None:
    ARTICLES_DIR.mkdir(exist_ok=True)
    (ARTICLES_DIR / f"{art['slug']}.html").write_text(art["html"], encoding="utf-8")
    hist = load_json(HISTORY, [])
    hist.append({"key": f"{fk}:{sk}", "format": fk, "scope": sk, "slug": art["slug"],
                 "title": art["title"], "date": today})
    HISTORY.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cont = load_json(CONTENUS, {"articles": [], "duels": []})
    cont["articles"] = [a for a in cont.get("articles", []) if a.get("slug") != art["slug"]]
    cont["articles"].insert(0, {"slug": art["slug"], "title": art["title"], "category": "Classement",
                                "excerpt": art["excerpt"], "img": art["img"], "date": today,
                                "read_min": art["read_min"]})
    CONTENUS.write_text(json.dumps(cont, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def review_md(art: dict, fk: str, sk: str, problems: list) -> str:
    lines = [f"## 📰 Article de la semaine : {art['title']}", "",
             f"Classement automatique (sans IA) — {art['studied']} stations étudiées, {art['n']} retenues. "
             f"Page : `articles/{art['slug']}.html`", "",
             "| # | Station / domaine | Valeur |", "|---|---|---|"]
    for i, e in enumerate(art["entries"], 1):
        lines.append(f"| {i} | {entry_name(e)} | {metric_text(fk, e).replace(NBSP, ' ')} |")
    photo_txt = "photo réelle" if art["hero_real"] else "photo de secours avec la légende Photo d'illustration"
    lines += ["", "### Plan de l'article (page complète : onglet « Files changed »)", "",
              "1. Introduction · 2. Photo du n°1 · 3. « À retenir » · 4. Classement détaillé (texte + fiche + Booking + Expedia)",
              "5. Analyse du classement · 6. Questions fréquentes · 7. Conclusion · 8. Fiches de toutes les stations citées",
              f"({art.get('words', '?')} mots)"]
    lines += ["", "### À vérifier avant de fusionner", "",
              "- Le classement vous paraît-il cohérent ? (un nom de station ou un chiffre qui jure = refuser)",
              f"- Photo du n°1 : {photo_txt}",
              "- Liens Booking et Expedia : contrôlés automatiquement (CJ)"]
    if problems:
        lines += ["", "### ⚠️ Contrôles en échec", ""] + [f"- {p}" for p in problems]
    else:
        lines += ["", "### Contrôles automatiques", "", "- classement ordonné, aucune station en double, liens CJ sur chaque station : OK"]
    lines += ["", "**Merge = publication** (accueil et « Toutes nos actus » se mettent à jour tout seuls). "
              "Pour refuser : fermer la pull request sans la fusionner."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--key", help="sujet imposé, ex. prix:savoie")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--review-out")
    args = ap.parse_args()

    stations = load_stations()
    hist = load_json(HISTORY, [])
    cands = all_candidates(stations, hist)

    if args.list:
        for prio, key, n, studied in cands:
            print(f"{prio:5.2f}  {key:28s} top {n:2d} sur {studied} stations")
        print(f"\n{len(cands)} sujets disponibles, {len(hist)} déjà publiés.")
        return

    if args.key:
        key = args.key
        if key not in {c[1] for c in cands}:
            raise SystemExit(f"❌ Sujet indisponible ou déjà publié : {key} (voir --list)")
    else:
        if not cands:
            raise SystemExit("❌ Plus aucun sujet disponible.")
        key = cands[0][1]
    fk, sk = key.split(":")
    today = date.today().isoformat()
    art = build(fk, sk, stations, today)
    problems = verify(art, fk)
    print(f"📰 {art['title']}  [{key}]  ({art['studied']} stations étudiées, top {art['n']})")
    for i, e in enumerate(art["entries"], 1):
        print(f"  {i:2d}. {e['s']['name']:32s} {metric_text(fk, e).replace(NBSP, ' ')}")
    if problems:
        raise SystemExit("❌ Contrôles en échec : " + " ; ".join(problems))
    md = review_md(art, fk, sk, problems)
    if args.review_out:
        Path(args.review_out).write_text(md, encoding="utf-8")
    if args.dry_run:
        print("\n(dry-run : rien n'est écrit)")
        return
    enregistrer(art, fk, sk, today)
    print(f"\n✅ articles/{art['slug']}.html + articles_hebdo.json + contenus.json")


if __name__ == "__main__":
    main()
