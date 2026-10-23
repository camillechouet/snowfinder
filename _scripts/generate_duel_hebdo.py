#!/usr/bin/env python3
"""
generate_duel_hebdo.py — SnowFinder
───────────────────────────────────
Prépare le duel de la semaine :
  1. choisit une paire de stations qui se ressemblent (même massif et même pays,
     domaines de taille proche, forfaits proches, jamais déjà comparées) ;
  2. fait rédiger le texte par Claude Opus, UNIQUEMENT à partir des fiches de
     stations-data.js (aucune autre source) ;
  3. contrôle le texte par script (chaque nombre doit venir des fiches, structure,
     HTML autorisé, noms des stations) puis par une relecture factuelle de Claude ;
  4. enregistre le brouillon dans duels_hebdo.json et en tête de contenus.json ;
  5. écrit un compte rendu lisible (pour la description de la pull request).

Les pages HTML sont ensuite produites par generate_comparatifs.py (qui lit
duels_hebdo.json) et l'accueil par generate_contenus.py.

Utilisation :
    python3 _scripts/generate_duel_hebdo.py                     # choisit la paire et rédige
    python3 _scripts/generate_duel_hebdo.py --list              # top 15 des paires candidates
    python3 _scripts/generate_duel_hebdo.py --pair "A|B"        # impose une paire
    python3 _scripts/generate_duel_hebdo.py --dry-run           # n'écrit aucun fichier
    python3 _scripts/generate_duel_hebdo.py --mock ok|bad       # test sans clé API

Variables d'environnement :
    ANTHROPIC_API_KEY   clé API (secret GitHub)
    DUEL_MODEL          modèle (défaut : claude-opus-5-5)
"""

from __future__ import annotations
import argparse
import itertools
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_comparatifs as gc  # noqa: E402

ROOT = gc.REPO_ROOT
HEBDO = ROOT / "duels_hebdo.json"
CONTENUS = ROOT / "contenus.json"
MODEL = os.environ.get("DUEL_MODEL", "claude-opus-5-5")
MAX_TRIES = 3
FALLBACK_IMG = "https://images.unsplash.com/photo-1483921020237-2ff51e8e4b22?w=600&q=80"

FIELDS_FOR_LLM = ("name", "massif", "region", "pays", "alt_min", "alt_max", "alt_village", "km",
                  "remontees", "pistes", "forfait", "score", "niv", "amb", "tags", "equip",
                  "desc", "pts", "desc_long")


# ── Utilitaires ──────────────────────────────────────────────────────────────

def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def pair_key(a: str, b: str) -> frozenset:
    return frozenset((gc.slugify(a), gc.slugify(b)))


def complete(s: dict) -> bool:
    p = s.get("pistes") or {}
    return (s.get("ok") is not False and not s.get("ferme")
            and all(s.get(k) for k in ("name", "massif", "region", "alt_min", "alt_max",
                                       "km", "remontees", "forfait", "score"))
            and all(k in p for k in "vbrn"))


# ── 1. Choix de la paire ─────────────────────────────────────────────────────

def known_pairs() -> tuple[set, Counter]:
    names = [(c["a"], c["b"]) for c in gc.COMPARAISONS]
    names += [(c["a"], c["b"]) for c in load_json(HEBDO, [])]
    names += [(d["a"], d["b"]) for d in load_json(CONTENUS, {}).get("duels", [])]
    keys = {pair_key(a, b) for a, b in names}
    usage: Counter = Counter()
    for k in keys:
        for slug in k:
            usage[slug] += 1
    return keys, usage


def similar(a: dict, b: dict) -> bool:
    if a["name"] == b["name"] or a["massif"] != b["massif"] or a.get("pays") != b.get("pays"):
        return False
    if not 0.6 <= a["km"] / b["km"] <= 1 / 0.6:
        return False
    if abs(a["forfait"] - b["forfait"]) / max(a["forfait"], b["forfait"]) > 0.25:
        return False
    if min(a["km"], b["km"]) < 10:
        return False
    # même domaine skiable partagé sous deux noms (même pays, même nombre de km) : duel sans intérêt
    if a["km"] == b["km"]:
        return False
    return True


def departement(s: dict) -> str:
    """Dernier élément de la région (« Tarentaise, Savoie » -> « savoie »)."""
    return (s.get("region") or "").split(",")[-1].strip().lower()


def priority(a: dict, b: dict, usage: Counter) -> float:
    note = (a["score"] + b["score"]) / 2
    taille = math.log10(min(a["km"], b["km"]))
    proche = abs(math.log(a["km"] / b["km"]))
    france = 2.5 if not a.get("pays") else 0.0          # public français : la France d'abord
    voisines = 0.7 if departement(a) == departement(b) else 0.0
    reuse = 1.5 * (usage[gc.slugify(a["name"])] + usage[gc.slugify(b["name"])])
    return note + taille + france + voisines - proche - reuse


def candidates(db: dict) -> list[tuple[float, dict, dict]]:
    keys, usage = known_pairs()
    usable = [s for s in db.values() if complete(s)]
    out = []
    for a, b in itertools.combinations(usable, 2):
        if pair_key(a["name"], b["name"]) in keys or not similar(a, b):
            continue
        out.append((priority(a, b, usage), a, b))
    out.sort(key=lambda t: (-t[0], t[1]["name"], t[2]["name"]))
    return out


# ── 2. Rédaction ─────────────────────────────────────────────────────────────

SYSTEM_REDACTION = """Tu rédiges des comparatifs de stations de ski pour SnowFinder, un site français.
RÈGLES ABSOLUES :
1. Tu n'utilises QUE les informations des deux fiches JSON et du bloc CALCULS fournis. Aucune autre connaissance : pas de noms de pistes, remontées, restaurants, hôtels, personnes, événements, labels, dates, prix ni chiffres absents des fiches.
2. Chaque nombre que tu cites doit apparaître tel quel dans les fiches ou dans le bloc CALCULS.
3. Si une information manque pour traiter un sujet, ne l'invente pas : choisis un autre angle appuyé sur les fiches.
4. Pas d'affirmation sur l'enneigement d'une saison précise, ni sur les prix d'hébergement ou de restauration.
5. Ton factuel et utile, sans superlatifs creux. Français correct, vouvoiement implicite (pas de « tu »).
6. Ta réponse est un unique objet JSON, sans texte autour."""


def prompt_redaction(a: dict, b: dict, retours: list[str]) -> str:
    fa = {k: a.get(k) for k in FIELDS_FOR_LLM}
    fb = {k: b.get(k) for k in FIELDS_FOR_LLM}
    calc = calculs(a, b)
    schema = {
        "teaser": "2 à 3 phrases qui posent le duel (250 à 500 caractères)",
        "profils": [["emoji + profil de voyageur", f"{a['name']} OU {b['name']} OU Égalité", "1 à 2 phrases justifiant le choix"]],
        "verdict": f"3 à 4 phrases ; les noms {a['name']} et {b['name']} chacun entouré de <strong></strong>",
        "faq": [["question que se pose un internaute", "réponse factuelle en 1 à 3 phrases"]],
    }
    txt = (f"FICHE A :\n{json.dumps(fa, ensure_ascii=False, indent=1)}\n\n"
           f"FICHE B :\n{json.dumps(fb, ensure_ascii=False, indent=1)}\n\n"
           f"CALCULS (seuls nombres dérivés autorisés) :\n{json.dumps(calc, ensure_ascii=False)}\n\n"
           f"Rédige le comparatif « {a['name']} vs {b['name']} » au format JSON suivant "
           f"(5 ou 6 profils, exactement 4 questions de FAQ, seul <strong> est autorisé comme HTML) :\n"
           f"{json.dumps(schema, ensure_ascii=False, indent=1)}")
    if retours:
        txt += ("\n\nTa tentative précédente a été refusée pour ces raisons, corrige-les :\n- "
                + "\n- ".join(retours))
    return txt


def calculs(a: dict, b: dict) -> dict:
    ecart = abs(a["forfait"] - b["forfait"])
    return {
        "ecart_forfait_euros": round(ecart, 2),
        "ecart_forfait_pourcent": round(100 * ecart / max(a["forfait"], b["forfait"])),
        "ecart_domaine_km": abs(a["km"] - b["km"]),
        "ecart_altitude_max_m": abs(a["alt_max"] - b["alt_max"]),
        "station_forfait_le_moins_cher": (a if a["forfait"] <= b["forfait"] else b)["name"],
        "station_domaine_le_plus_grand": (a if a["km"] >= b["km"] else b)["name"],
    }


SYSTEM_RELECTURE = """Tu es relecteur factuel pour SnowFinder. On te donne deux fiches de stations (la SEULE source de vérité) et un texte de comparatif.
Pour chaque affirmation du texte, vérifie qu'elle est soutenue par les fiches. Signale : tout fait absent des fiches, toute contradiction, tout chiffre faux, tout choix de profil illogique par rapport aux chiffres.
Ne signale PAS les formulations de style. Réponds par un unique objet JSON : {"problemes": ["…", "…"]} (liste vide si tout est soutenu)."""


def call_llm(system: str, user: str, max_tokens: int = 4500) -> str:
    import anthropic  # importé ici : inutile en mode --mock
    client = anthropic.Anthropic()
    msg = client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                 messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def extract_json(txt: str) -> dict:
    i, j = txt.find("{"), txt.rfind("}")
    if i < 0 or j < 0:
        raise ValueError("pas de JSON dans la réponse")
    return json.loads(txt[i:j + 1], strict=False)


# ── 3. Contrôles par script ──────────────────────────────────────────────────

NUM_RE = re.compile(r"\d+(?:[   ]\d{3})*(?:[.,]\d+)?")
UNIT_RE = re.compile(r"^\s*(km|m\b|€|%|remont|pistes|heures?|h\b|jours?|ans)")


def to_float(tok: str) -> float:
    return float(re.sub(r"[   ]", "", tok).replace(",", "."))


def numbers_in(text: str) -> list[tuple[float, str, str]]:
    return [(to_float(m.group()), m.group(), text[m.end():m.end() + 12]) for m in NUM_RE.finditer(text)]


def allowed_numbers(a: dict, b: dict) -> set[float]:
    src = json.dumps({"a": {k: a.get(k) for k in FIELDS_FOR_LLM},
                      "b": {k: b.get(k) for k in FIELDS_FOR_LLM},
                      "c": calculs(a, b)}, ensure_ascii=False)
    return {v for v, _, _ in numbers_in(src)}


def all_texts(d: dict) -> list[str]:
    out = [d.get("teaser", ""), d.get("verdict", "")]
    for p in d.get("profils", []):
        out += [str(x) for x in p]
    for q in d.get("faq", []):
        out += [str(x) for x in q]
    return out


def check_draft(d: dict, a: dict, b: dict) -> list[str]:
    errs = []
    A, B = a["name"], b["name"]
    if not isinstance(d, dict):
        return ["la réponse n'est pas un objet JSON"]
    for k in ("teaser", "profils", "verdict", "faq"):
        if k not in d:
            errs.append(f"clé « {k} » manquante")
    if errs:
        return errs
    if not (150 <= len(d["teaser"]) <= 700):
        errs.append(f"teaser de {len(d['teaser'])} caractères (attendu 150 à 700)")
    profils = d["profils"]
    if not (5 <= len(profils) <= 6) or not all(isinstance(p, list) and len(p) == 3 for p in profils):
        errs.append("il faut 5 ou 6 profils au format [libellé, choix, raison]")
    else:
        for p in profils:
            if p[1] not in (A, B, "Égalité"):
                errs.append(f"choix de profil invalide : « {p[1]} » (attendu {A}, {B} ou Égalité)")
        picks = {p[1] for p in profils}
        if A not in picks or B not in picks:
            errs.append("chaque station doit être recommandée pour au moins un profil")
    faq = d["faq"]
    if len(faq) != 4 or not all(isinstance(q, list) and len(q) == 2 for q in faq):
        errs.append("il faut exactement 4 questions de FAQ au format [question, réponse]")
    v = d["verdict"]
    if f"<strong>{A}</strong>" not in v or f"<strong>{B}</strong>" not in v:
        errs.append("le verdict doit contenir les deux noms entourés de <strong></strong>")
    if re.search(r"<(?!/?strong>)", v):
        errs.append("seul le HTML <strong> est autorisé dans le verdict")
    for t in [d["teaser"]] + [str(x) for p in profils for x in p] + [str(x) for q in faq for x in q]:
        if "<" in t or ">" in t:
            errs.append("du HTML est présent en dehors du verdict")
            break
    for t in all_texts(d):
        if re.search(r"https?://|www\.", t):
            errs.append("les liens sont interdits dans le texte")
            break
    ok_nums = allowed_numbers(a, b)
    bad = set()
    for t in all_texts(d):
        for val, tok, after in numbers_in(re.sub(r"</?strong>", "", t)):
            significatif = val >= 10 or bool(UNIT_RE.match(after))
            if significatif and not any(abs(val - x) < 1e-6 for x in ok_nums):
                bad.add(tok.strip())
    if bad:
        errs.append("nombres absents des fiches : " + ", ".join(sorted(bad)))
    return errs


def relecture(d: dict, a: dict, b: dict) -> list[str]:
    fa = {k: a.get(k) for k in FIELDS_FOR_LLM}
    fb = {k: b.get(k) for k in FIELDS_FOR_LLM}
    user = (f"FICHE A :\n{json.dumps(fa, ensure_ascii=False)}\n\nFICHE B :\n{json.dumps(fb, ensure_ascii=False)}\n\n"
            f"CALCULS :\n{json.dumps(calculs(a, b), ensure_ascii=False)}\n\n"
            f"TEXTE À RELIRE :\n{json.dumps({k: d[k] for k in ('teaser', 'profils', 'verdict', 'faq')}, ensure_ascii=False)}")
    res = extract_json(MOCK_RELECTURE if MOCK else call_llm(SYSTEM_RELECTURE, user, 1500))
    return [str(p) for p in res.get("problemes", [])]


# ── Mode test (sans clé API) ─────────────────────────────────────────────────

MOCK = None
MOCK_RELECTURE = '{"problemes": []}'


def mock_redaction(kind: str, a: dict, b: dict) -> str:
    A, B = a["name"], b["name"]
    gros = a if a["km"] >= b["km"] else b
    petit = b if gros is a else a
    km_extra = " Environ 800 km de pistes les séparent du Mont-Blanc." if kind == "bad" else ""
    d = {
        "teaser": (f"{A} et {B} sont deux stations de {a['massif']} aux profils proches, avec respectivement "
                   f"{a['km']} km et {b['km']} km de domaine skiable. Le forfait journée s'affiche à "
                   f"{a['forfait']} € d'un côté et {b['forfait']} € de l'autre.{km_extra}"),
        "profils": [
            ["🎿 Skieurs en quête d'un grand domaine", gros["name"], f"Avec {gros['km']} km de pistes, {gros['name']} offre le plus de terrain."],
            ["💰 Budget serré", (a if a['forfait'] <= b['forfait'] else b)["name"], f"Forfait journée à {min(a['forfait'], b['forfait'])} €."],
            ["⛰️ Altitude maximale", (a if a['alt_max'] >= b['alt_max'] else b)["name"], f"Le point culminant atteint {max(a['alt_max'], b['alt_max'])} m."],
            ["🏔️ Domaine plus compact", petit["name"], f"Avec {petit['km']} km, {petit['name']} se parcourt plus vite."],
            ["⭐ Note SnowFinder", (a if a['score'] >= b['score'] else b)["name"], f"Note de {max(a['score'], b['score'])} / 5."],
        ],
        "verdict": (f"<strong>{gros['name']}</strong> offre le plus grand domaine ({gros['km']} km) alors que "
                    f"<strong>{petit['name']}</strong> propose {petit['km']} km. Le choix dépend donc de la taille de "
                    f"domaine recherchée."),
        "faq": [
            [f"Quelle station a le plus grand domaine, {A} ou {B} ?", f"{gros['name']}, avec {gros['km']} km contre {petit['km']} km."],
            [f"Quel est le forfait journée à {A} ?", f"{a['forfait']} € d'après la fiche SnowFinder."],
            [f"Quel est le forfait journée à {B} ?", f"{b['forfait']} € d'après la fiche SnowFinder."],
            [f"Quelle station monte le plus haut ?", f"{(a if a['alt_max'] >= b['alt_max'] else b)['name']}, jusqu'à {max(a['alt_max'], b['alt_max'])} m."],
        ],
    }
    return json.dumps(d, ensure_ascii=False)


def rediger(a: dict, b: dict) -> tuple[dict, list[str]]:
    retours: list[str] = []
    notes: list[str] = []
    for essai in range(1, MAX_TRIES + 1):
        raw = mock_redaction(MOCK if essai == 1 else "ok", a, b) if MOCK else call_llm(SYSTEM_REDACTION, prompt_redaction(a, b, retours))
        try:
            d = extract_json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            retours = [f"réponse illisible ({e})"]
            notes.append(f"essai {essai} : {retours[0]}")
            continue
        erreurs = check_draft(d, a, b)
        if erreurs:
            retours = erreurs
            notes.append(f"essai {essai} refusé par le contrôle : " + " ; ".join(erreurs))
            continue
        problemes = relecture(d, a, b)
        if problemes:
            retours = problemes
            notes.append(f"essai {essai} refusé par la relecture : " + " ; ".join(problemes))
            continue
        notes.append(f"essai {essai} : contrôle des chiffres et relecture factuelle OK")
        return d, notes
    raise SystemExit("❌ Aucun texte valide après %d essais :\n  - %s" % (MAX_TRIES, "\n  - ".join(notes)))


# ── 4. Enregistrement + compte rendu ─────────────────────────────────────────

def img_name(s: dict) -> str:
    """Nom du fichier photo n°1 de la station (convention img/valthorens1.jpg), '' si absent du dépôt."""
    p = gc.station_photo(s["name"])
    return Path(p).stem if p else ""


def img_path_or_fallback(s: dict) -> str:
    p = gc.station_photo(s["name"])
    return p or gc.RESCUE_PHOTOS[s["id"] % len(gc.RESCUE_PHOTOS)]


def enregistrer(d: dict, a: dict, b: dict) -> None:
    entry = {"a": a["name"], "b": b["name"], "img_a": img_name(a) or "", "img_b": img_name(b) or "",
             "teaser": d["teaser"], "profils": d["profils"], "verdict": d["verdict"], "faq": d["faq"],
             "date": date.today().isoformat(), "modele": "mock" if MOCK else MODEL}
    hebdo = load_json(HEBDO, [])
    hebdo.append(entry)
    HEBDO.write_text(json.dumps(hebdo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cont = load_json(CONTENUS, {"articles": [], "duels": []})
    cont.setdefault("duels", []).insert(0, {"a": a["name"], "b": b["name"],
                                            "img": img_path_or_fallback(a), "img_b": img_path_or_fallback(b)})
    CONTENUS.write_text(json.dumps(cont, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compte_rendu(d: dict, a: dict, b: dict, notes: list[str], rang: int, total: int) -> str:
    lignes = [f"## Duel proposé : {a['name']} vs {b['name']}", "",
              f"Page : `/comparatifs/{gc.slugify(a['name'])}-vs-{gc.slugify(b['name'])}.html` "
              f"· paire n°{rang} sur {total} candidates", "",
              "### Chiffres des fiches",
              f"| | {a['name']} | {b['name']} |", "|---|---|---|",
              f"| Massif | {a['massif']} | {b['massif']} |",
              f"| Altitude | {a['alt_min']}–{a['alt_max']} m | {b['alt_min']}–{b['alt_max']} m |",
              f"| Domaine | {a['km']} km | {b['km']} km |",
              f"| Forfait | {a['forfait']} € | {b['forfait']} € |",
              f"| Note | {a['score']} | {b['score']} |", "",
              "### Texte à valider", "", f"**Introduction** : {d['teaser']}", "", "**Profils**", ""]
    lignes += [f"- {p[0]} → **{p[1]}** : {p[2]}" for p in d["profils"]]
    lignes += ["", f"**Verdict** : {d['verdict']}", "", "**FAQ**", ""]
    lignes += [f"- *{q[0]}* {q[1]}" for q in d["faq"]]
    lignes += ["", "### Contrôles", ""] + [f"- {n}" for n in notes]
    lignes += ["", "Pour refuser ce duel : fermer la pull request sans la fusionner."]
    return "\n".join(lignes) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    global MOCK
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--pair", help='« Station A|Station B »')
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", choices=["ok", "bad"])
    ap.add_argument("--review-out", type=Path, default=Path("/tmp/duel_review.md"))
    args = ap.parse_args()
    MOCK = args.mock

    db = gc.load_stations()
    cands = candidates(db)
    print(f"✓ {len(db)} stations, {len(cands)} paires candidates non encore comparées")

    if args.list:
        for i, (p, a, b) in enumerate(cands[:15], 1):
            print(f"{i:>2}. {p:5.2f}  {a['name']} vs {b['name']}  ({a['km']} / {b['km']} km, {a['forfait']} / {b['forfait']} €)")
        return

    if args.pair:
        na, nb = [x.strip() for x in args.pair.split("|")]
        if na not in db or nb not in db:
            sys.exit(f"❌ Station inconnue dans stations-data.js : {na} ou {nb}")
        a, b = db[na], db[nb]
        if not (complete(a) and complete(b)):
            sys.exit("❌ Fiche incomplète pour l'une des stations")
        if pair_key(na, nb) in known_pairs()[0]:
            sys.exit("❌ Cette paire existe déjà")
        rang, total = 0, len(cands)
    else:
        if not cands:
            sys.exit("❌ Aucune paire candidate")
        _, a, b = cands[0]
        rang, total = 1, len(cands)

    print(f"→ Paire retenue : {a['name']} vs {b['name']}")
    d, notes = rediger(a, b)
    review = compte_rendu(d, a, b, notes, rang, total)
    if args.dry_run:
        print(review)
        return
    enregistrer(d, a, b)
    args.review_out.write_text(review, encoding="utf-8")
    print(f"✏️  duels_hebdo.json et contenus.json mis à jour · compte rendu : {args.review_out}")


if __name__ == "__main__":
    main()
