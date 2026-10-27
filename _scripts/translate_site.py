#!/usr/bin/env python3
"""
SnowFinder — Traduction automatique FR → EN des pages générées
================================================================
Prend les pages HTML françaises produites par les autres scripts (stations,
domaines, duels, articles, listes) et écrit leur version anglaise dans /en/…
(même arborescence : stations/x.html -> en/stations/x.html).

Principes
---------
* On ne touche PAS aux générateurs français : on traduit leur sortie.
* Chaque texte n'est traduit qu'UNE fois (cache dans i18n/cache/en/*.json).
  Relancer le script ne coûte donc rien tant que rien n'a changé.
* Les balises en ligne (liens d'affiliation, <strong>…) sont protégées par des
  marqueurs <t1>…</t1> : le modèle traduit le texte, jamais les liens.
* Contrôles automatiques sur chaque traduction : mêmes balises, mêmes nombres,
  noms de stations/domaines inchangés. Ce qui ne passe pas est consigné dans
  i18n/qa-en.json ; si les balises sont incohérentes, le texte reste en français
  (aucun lien cassé) et sera retenté au prochain passage.
* Une page n'est publiée en anglais que si TOUS ses textes sont traduits.
* Garde-fou de coût : le script s'arrête quand la dépense estimée dépasse
  BUDGET_USD (25 $ par défaut) ; le passage suivant reprend où il s'est arrêté.
* Les liens internes d'une page anglaise pointent vers la version anglaise de la
  page cible si elle existe, sinon vers la version française (jamais de 404).
* hreflang, canonical et petit sélecteur de langue sont posés des deux côtés.

Usage
-----
  python3 _scripts/translate_site.py                 # tout le site
  python3 _scripts/translate_site.py --limit 5       # test sur 5 pages variées
  python3 _scripts/translate_site.py --only stations/valthorens --limit 1
  python3 _scripts/translate_site.py --dry-run       # estime le coût, n'appelle pas l'API
  python3 _scripts/translate_site.py --mock          # faux traducteur (test sans API)

Variables d'environnement : ANTHROPIC_API_KEY, TRANSLATE_MODEL, BUDGET_USD,
PRICE_IN_PER_MTOK, PRICE_OUT_PER_MTOK, SF_ROOT (racine du site, pour les tests).
"""
import argparse
import copy
import glob
import hashlib
import html as htmllib
import json
import os
import posixpath
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup, NavigableString, Tag

sys.setrecursionlimit(20000)

SITE = "https://snowfinder.fr"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SF_ROOT") or os.path.dirname(SCRIPT_DIR)

MODEL = os.environ.get("TRANSLATE_MODEL", "claude-haiku-5-5")
PROMPT_VERSION = "1"            # à incrémenter pour forcer une retraduction complète
BUDGET_USD = float(os.environ.get("BUDGET_USD", "25"))
PRICE_IN = float(os.environ.get("PRICE_IN_PER_MTOK", "0.1"))     # $ / million de tokens (estimation)
PRICE_OUT = float(os.environ.get("PRICE_OUT_PER_MTOK", "0.5"))
WORKERS = int(os.environ.get("TRANSLATE_WORKERS", "4"))
BATCH_ITEMS, BATCH_CHARS = 40, 7000

# Pages à traduire (motifs relatifs à la racine). Les motifs sans correspondance sont ignorés.
SOURCES = [
    "stations/*.html",
    "domaines/*.html",
    "comparatifs/*.html",
    "articles/*.html",
    "stations-du-moment/*.html",
    "tous-les-comparatifs.html",
    "toutes-les-actus.html",
    "toutes-les-stations-du-moment.html",
    "domaines.html",
]
CACHE_DIR = os.path.join(ROOT, "i18n", "cache", "en")
QA_FILE = os.path.join(ROOT, "i18n", "qa-en.json")
MANIFEST_FILE = os.path.join(ROOT, "i18n", "manifest-en.json")

SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "iframe", "textarea",
             "code", "pre", "template", "math"}
INLINE = {"a", "abbr", "b", "bdi", "bdo", "br", "cite", "em", "i", "mark", "q", "s",
          "small", "span", "strong", "sub", "sup", "time", "u", "wbr", "img", "label",
          "button", "font", "del", "ins", "kbd", "samp", "var"}
VOID = {"br", "img", "wbr"}
TR_ATTRS = ("alt", "title", "placeholder", "aria-label", "aria-description")
URL_ATTRS = ("href", "src", "data-src", "poster", "action")
META_NAMES = {"description", "keywords", "twitter:title", "twitter:description"}
META_PROPS = {"og:title", "og:description", "og:image:alt"}
JSONLD_KEYS = {"headline", "alternativeHeadline", "description", "text"}

LETTERS = re.compile(r"[A-Za-zÀ-ÿŒœ]")
TOKEN = re.compile(r"<(/?)t(\d+)(/?)>")

# ─────────────────────────────────────────────────────────────────────────────
# Prompt de traduction
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are the professional translator of SnowFinder (snowfinder.fr), a ski-resort \
comparison and discovery website covering France and the rest of Europe. You translate the site's French \
text into natural, fluent, friendly British English for holidaymakers (UK, Netherlands, Belgium, \
Scandinavia, Germany). Keep the editorial tone of the original: warm, concrete, never salesy.

INPUT: a JSON object {"protected_names": [...], "texts": [...]}.
OUTPUT: ONLY a JSON array of strings: the translations of "texts", same length, same order. \
No commentary, no markdown fence.

HARD RULES
1. Markers such as <t1>…</t1> and <t2/> are HTML tags in disguise. Keep every marker, with the same \
number, the same nesting, exactly once. Never add, remove, renumber or translate them. Move them only \
as far as English word order requires. Any real HTML tag (<strong>, <br>…) is kept as it is.
2. NEVER translate or alter proper names: resorts, villages, ski areas/domains, mountains, lifts, \
pistes, hotels, restaurants, people, brands, events. Every string in "protected_names" must appear \
unchanged in the translation. Keep French names as written (Les Menuires, Val Thorens, Tignes – Val d'Isère). \
Well-known English names stay English: Mont Blanc, Tour de France, the Alps, the Pyrenees, Switzerland, \
Italy, Spain, Germany, Austria, Andorra, Slovenia, Liechtenstein, France.
3. Keep ALL numbers exactly (km, m, €, percentages, years, prices, counts). Convert only the notation: \
decimal comma → point (41,50 → 41.50), thousands separator → comma (1 700 m → 1,700 m). Keep units, \
the € sign and emoji where they are. Never round, add or remove a figure.
4. Do not invent, embellish or drop facts. If a sentence is already English, return it unchanged.
5. Keep the same level of formality ("tu"/"vous" → "you"). Keep punctuation style simple; \
use "–" where the source uses it.
6. Return plain text escapes as in the source (&amp; stays &amp;).

GLOSSARY (use consistently)
forfait / forfait journée = lift pass / day lift pass · station = resort · domaine skiable = ski area · \
grand domaine / domaine relié = linked ski area · remontées mécaniques = lifts · télésiège = chairlift · \
téléski = drag lift · télécabine = gondola · téléphérique = cable car · piste verte/bleue/rouge/noire = \
green/blue/red/black run · pistes = runs (or pistes) · hors-piste = off-piste · freeride = freeride · \
damage = grooming · enneigement = snow reliability · neige de culture = artificial snow · \
après-ski = après-ski · débutant/intermédiaire/avancé/expert = beginner/intermediate/advanced/expert · \
ESF = ESF (French ski school) · garderie = childcare · luge = sledging · raquettes = snowshoeing · \
ski de fond = cross-country skiing · ski nordique = Nordic skiing · office de tourisme = tourist office · \
site officiel = official website · hébergement = accommodation · Alpes du Nord = Northern Alps · \
Alpes du Sud = Southern Alps · Massif Central = Massif Central · Pyrénées = Pyrenees · Jura/Vosges/Corse = \
Jura/Vosges/Corsica · Savoie/Haute-Savoie/Isère stay as they are · Coupe du monde = World Cup · \
Jeux olympiques = Olympic Games · Plus Beaux Villages de France = "Plus Beaux Villages de France" · \
"Photo d'illustration" = "Illustrative photo" · "Voir la fiche complète" = "See the full resort page" · \
Duel = Head-to-head · Station du moment = Resort of the moment · \
Conseiller IA = AI Advisor · Comparateur = Comparison tool · Favoris = Favourites · Recherche = Search."""

# ─────────────────────────────────────────────────────────────────────────────
# Noms protégés (stations, domaines) — pour le contrôle qualité et le prompt
# ─────────────────────────────────────────────────────────────────────────────
# Libellés de menu / fil d'Ariane présents dans les "name" du générateur mais qui doivent être traduits
GENERIC_LABELS = {"Accueil", "Stations de ski", "Recherche", "Comparateur", "Comparatifs", "Favoris",
                  "Mentions légales", "Articles", "Actualités", "Domaines skiables", "Domaines"}


def load_protected():
    names = set()
    def add(raw):
        try:
            n = json.loads('"' + raw + '"')
        except Exception:
            n = raw
        n = n.strip()
        if len(n) >= 6 and n not in GENERIC_LABELS:
            names.add(n)
    for rel, pat in (("stations-data.js", r'"name"\s*:\s*"((?:[^"\\]|\\.)+)"'),
                     (os.path.join("_scripts", "generate_stations.py"), r'"name"\s*:\s*"((?:[^"\\]|\\.)+)"'),
                     ("generate_stations.py", r'"name"\s*:\s*"((?:[^"\\]|\\.)+)"')):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for m in re.finditer(pat, f.read()):
                    add(m.group(1))
    return names


PROTECTED = load_protected()
PROTECTED_RE = (re.compile(r"(?<!\w)(?:%s)(?!\w)" % "|".join(
    re.escape(n) for n in sorted(PROTECTED, key=len, reverse=True))) if PROTECTED else None)


def protected_in(text):
    if not PROTECTED_RE:
        return []
    return sorted(set(PROTECTED_RE.findall(text)))


# ─────────────────────────────────────────────────────────────────────────────
# Cache (fragmenté en 256 fichiers pour garder des diffs Git lisibles)
# ─────────────────────────────────────────────────────────────────────────────
def key_of(text):
    return hashlib.sha1((PROMPT_VERSION + "\0" + text).encode("utf-8")).hexdigest()


class Cache:
    def __init__(self):
        self.data = {}
        self.dirty = set()
        self.lock = threading.Lock()
        if os.path.isdir(CACHE_DIR):
            for fn in os.listdir(CACHE_DIR):
                if fn.endswith(".json"):
                    try:
                        with open(os.path.join(CACHE_DIR, fn), "r", encoding="utf-8") as f:
                            self.data.update(json.load(f))
                    except Exception as e:
                        print(f"⚠ cache {fn} illisible : {e}")

    def get(self, text):
        return self.data.get(key_of(text))

    def put(self, text, en):
        k = key_of(text)
        with self.lock:
            self.data[k] = en
            self.dirty.add(k[:2])

    def save(self):
        if not self.dirty:
            return
        os.makedirs(CACHE_DIR, exist_ok=True)
        shards = {}
        for k, v in self.data.items():
            if k[:2] in self.dirty:
                shards.setdefault(k[:2], {})[k] = v
        for sh, d in shards.items():
            with open(os.path.join(CACHE_DIR, sh + ".json"), "w", encoding="utf-8") as f:
                json.dump(dict(sorted(d.items())), f, ensure_ascii=False, indent=0)
        self.dirty.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Analyse d'une page : repère tous les textes à traduire
# ─────────────────────────────────────────────────────────────────────────────
def strip_markers(src):
    """Retire les blocs hreflang / sélecteur de langue posés par ce script sur la page française."""
    src = re.sub(r"<!--sf-i18n-->.*?<!--/sf-i18n-->", "", src, flags=re.S)
    return re.sub(r"<!--sf-lang-->.*?<!--/sf-lang-->", "", src, flags=re.S)


def has_letters(s):
    return bool(LETTERS.search(s or ""))


def is_plain_string(n):
    return type(n) is NavigableString


def no_translate(el):
    if el.get("translate") == "no":
        return True
    cls = el.get("class") or []
    return "notranslate" in cls or "sf-lang-switch" in cls


def collapse(s):
    return re.sub(r"[ \t\r\n]+", " ", s)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def unesc(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def build_placeholder(el):
    """Texte de l'élément avec ses balises en ligne remplacées par <tN>…</tN>."""
    tags = []

    def rec(node):
        out = []
        for ch in node.children:
            if isinstance(ch, Tag):
                tags.append(ch)
                i = len(tags)
                if ch.name in VOID:
                    out.append(f"<t{i}/>")
                else:
                    out.append(f"<t{i}>" + rec(ch) + f"</t{i}>")
            elif is_plain_string(ch):
                out.append(esc(str(ch)))
        return "".join(out)

    ph = collapse(rec(el)).strip()
    return ph, tags


def analyze(soup):
    """Retourne la liste ordonnée des travaux de traduction de la page."""
    info = {}

    def get_info(el):
        k = id(el)
        if k in info:
            return info[k]
        inline_only = el.name in INLINE
        has = False
        for ch in el.children:
            if isinstance(ch, Tag):
                if ch.name in SKIP_TAGS:
                    inline_only = False
                    continue
                ci, ch_has = get_info(ch)
                inline_only = inline_only and ci
                has = has or ch_has
            elif is_plain_string(ch) and has_letters(str(ch)):
                has = True
        # un élément non « en ligne » peut tout de même être une unité (div/p/li…)
        # s'il ne contient que du texte et des balises en ligne
        only_inline_children = all(
            (not isinstance(ch, Tag)) or (ch.name in INLINE and get_info(ch)[0]) for ch in el.children
            if not (isinstance(ch, Tag) and ch.name in SKIP_TAGS)
        ) and not any(isinstance(ch, Tag) and ch.name in SKIP_TAGS for ch in el.children)
        info[k] = (only_inline_children, has)
        return info[k]

    jobs = {"attr": [], "meta": [], "json": [], "orphan": [], "unit": []}

    def select(el):
        for ch in list(el.children):
            if isinstance(ch, Tag):
                if ch.name in SKIP_TAGS or no_translate(ch):
                    continue
                only_inline, has = get_info(ch)
                if has and only_inline:
                    ph, tags = build_placeholder(ch)
                    if has_letters(ph):
                        jobs["unit"].append({"el": ch, "payload": ph, "tags": tags})
                elif has:
                    select(ch)
            elif is_plain_string(ch) and has_letters(str(ch)):
                jobs["orphan"].append({"node": ch, "payload": collapse(str(ch)).strip()})

    root = soup
    select(root)

    for el in soup.find_all(True):
        if el.name in SKIP_TAGS and el.name != "script":
            continue
        for a in TR_ATTRS:
            v = el.get(a)
            if isinstance(v, str) and has_letters(v) and not v.startswith(("http", "/", "#")):
                jobs["attr"].append({"el": el, "attr": a, "payload": collapse(v).strip()})
        if el.name == "meta":
            name = (el.get("name") or "").lower()
            prop = (el.get("property") or "").lower()
            v = el.get("content")
            if isinstance(v, str) and has_letters(v) and (name in META_NAMES or prop in META_PROPS):
                jobs["meta"].append({"el": el, "payload": collapse(v).strip()})
        if el.name == "script" and (el.get("type") or "").lower() == "application/ld+json":
            raw = el.string or el.get_text()
            try:
                data = json.loads(raw)
            except Exception:
                continue
            found = []

            def walk(o, parent_type=None):
                if isinstance(o, dict):
                    t = o.get("@type")
                    for k, v in o.items():
                        if isinstance(v, (dict, list)):
                            walk(v, t if isinstance(t, str) else parent_type)
                        elif isinstance(v, str) and has_letters(v):
                            if k in JSONLD_KEYS or (k == "name" and t == "Question"):
                                found.append((o, k))
                elif isinstance(o, list):
                    for it in o:
                        walk(it, parent_type)

            walk(data)
            if found:
                jobs["json"].append({"el": el, "data": data, "found": found})
    return jobs


def all_payloads(jobs):
    out = []
    for j in jobs["attr"] + jobs["meta"] + jobs["orphan"] + jobs["unit"]:
        out.append(j["payload"])
    for j in jobs["json"]:
        for o, k in j["found"]:
            out.append(o[k])
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Contrôles qualité
# ─────────────────────────────────────────────────────────────────────────────
def tag_sig(s):
    return sorted(re.findall(r"<[^>]+>", s))


def digit_tokens(s):
    s = re.sub(r"<[^>]+>", " ", s)
    toks = re.findall(r"\d+(?:[   .,]\d+)*", s)
    return sorted(re.sub(r"\D", "", t) for t in toks)


FR_NUMBER_WORDS = {"deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8,
                   "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14,
                   "quinze": 15, "seize": 16, "vingt": 20, "trente": 30, "quarante": 40,
                   "cinquante": 50, "soixante": 60, "cent": 100, "mil": 1000, "mille": 1000}
ROMAN_VAL = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
ROMAN_RE = re.compile(r"\b([IVXL]{1,6})(?:e|er|ème|è)\b")


def roman_to_int(s):
    total = 0
    for i, c in enumerate(s):
        v = ROMAN_VAL[c]
        total += -v if i + 1 < len(s) and ROMAN_VAL[s[i + 1]] > v else v
    return total


DECADE_RE = re.compile(r"(\bann[ée]es?\s+)(\d0)\b", re.I)
ORDINAL_RE = re.compile(r"\b(\d+)(?:er|re|e|ème|è|nd|d)\b")


def digit_diff(fr, en):
    """(nombres français perdus, chiffres anglais en trop) pour une variante donnée du français."""
    best = None
    variants = [fr, DECADE_RE.sub(lambda m: m.group(1) + "19" + m.group(2), fr)]
    allowed = []
    for m in ROMAN_RE.finditer(fr):
        try:
            allowed.append(str(roman_to_int(m.group(1))))
        except Exception:
            pass
    for w in re.findall(r"[a-zéèêûîô]+", fr.lower()):
        if w in FR_NUMBER_WORDS:
            allowed.append(str(FR_NUMBER_WORDS[w]))
    optional = [re.sub(r"\D", "", x) for x in ORDINAL_RE.findall(fr)]   # 1er, 2e… peuvent devenir « first »
    for v in variants:
        rest = list(digit_tokens(en))
        lost = []
        for x in digit_tokens(v):
            if x in rest:
                rest.remove(x)
            elif x not in optional:
                lost.append(x)
        extra = [x for x in rest if x not in allowed]
        if best is None or len(lost) + len(extra) < len(best[0]) + len(best[1]):
            best = (lost, extra)
    return best


def digits_ok(fr, en):
    """Mêmes nombres FR/EN, en tolérant les conversions normales : XIIe siècle -> 12th century,
    douze -> twelve / 12, « années 70 » -> 1970s, « 1er » -> first."""
    lost, extra = digit_diff(fr, en)
    return not lost and not extra


CENTURY_RE = re.compile(r"\b([IVXL]{1,6})(?:e|er|ème|è)\s+(?:siècle|century)\b")


# Altitudes / distances en mètres : 1600 m -> 1,600 m (y compris le début d'une plage « 1600 – 3226 m »)
ALT_RE = re.compile(r"(?<![\d,.])([1-9])(\d{3})(?![\d,.])(?=\s*(?:[–-]\s*[\d,]+\s*)?m\b)")


def ordinal(n):
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def fix_en(en):
    """Corrections déterministes d'oublis fréquents : siècles en chiffres romains laissés en français
    ('XIIe siècle' -> '12th century'). S'applique aussi aux textes déjà en cache."""
    def rep(m):
        try:
            return ordinal(roman_to_int(m.group(1))) + " century"
        except Exception:
            return m.group(0)
    en = CENTURY_RE.sub(rep, en)
    return ALT_RE.sub(lambda m: m.group(1) + "," + m.group(2), en)


ARTICLE_RE = re.compile(r"^(?:Le|La|Les|L['’])\s*", re.I)


def names_missing(fr, en):
    out = []
    for n in protected_in(fr):
        if n in en:
            continue
        bare = ARTICLE_RE.sub("", n).strip()      # « Le Ballon d'Alsace » -> « The Ballon d'Alsace » est correct
        if bare and bare != n and bare in en:
            continue
        out.append(n)
    return out


def check(fr, en, strict=True):
    """Retourne (bloquant, avertissement). bloquant => on retente puis, au pire, on garde le français.
    strict=True : un nom de station/domaine perdu est bloquant (au dernier essai : simple avertissement)."""
    if not en or not en.strip():
        return "traduction vide", None
    if tag_sig(fr) != tag_sig(en):
        return "balises différentes", None
    lost, extra = digit_diff(fr, en)
    if lost or extra:
        return f"nombres différents (perdus : {', '.join(lost[:6]) or '–'} ; en trop : {', '.join(extra[:6]) or '–'})", None
    miss = names_missing(fr, en)
    if miss:
        msg = "nom modifié : " + ", ".join(miss[:3])
        if strict:
            return msg, None
        return None, msg
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Appels à l'API
# ─────────────────────────────────────────────────────────────────────────────
class Spend:
    def __init__(self):
        self.tin = self.tout = self.calls = 0
        self.lock = threading.Lock()

    def add(self, tin, tout):
        with self.lock:
            self.tin += tin
            self.tout += tout
            self.calls += 1

    @property
    def usd(self):
        return self.tin / 1e6 * PRICE_IN + self.tout / 1e6 * PRICE_OUT


SPEND = Spend()


def api_call(user_payload, extra_note=""):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY manquante")
    system = SYSTEM_PROMPT + (("\n\nNOTE: " + extra_note) if extra_note else "")
    body = {
        "model": MODEL,
        "max_tokens": 8192,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}],
    }
    data = json.dumps(body).encode("utf-8")
    for attempt in range(6):
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=data, method="POST",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                resp = json.loads(r.read().decode("utf-8"))
            u = resp.get("usage", {})
            SPEND.add(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                      + u.get("cache_read_input_tokens", 0) * 0.1, u.get("output_tokens", 0))
            return "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
        except urllib.error.HTTPError as e:
            retry_after = e.headers.get("retry-after")
            if e.code in (429, 500, 502, 503, 529) and attempt < 5:
                time.sleep(float(retry_after) if retry_after else min(60, 2 ** attempt * 3))
                continue
            raise RuntimeError(f"API {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
        except (urllib.error.URLError, TimeoutError):
            if attempt < 5:
                time.sleep(2 ** attempt * 3)
                continue
            raise
    raise RuntimeError("API : trop d'échecs")


def parse_array(txt):
    t = txt.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    a = t.find("[")
    b = t.rfind("]")
    if a < 0 or b < 0:
        raise ValueError("pas de tableau JSON")
    arr = json.loads(t[a:b + 1])
    if not isinstance(arr, list):
        raise ValueError("pas un tableau")
    return arr


def translate_call(texts, note=""):
    if MOCK:
        return ["[EN] " + t for t in texts]
    names = sorted(set(n for t in texts for n in protected_in(t)))
    out = api_call({"protected_names": names, "texts": texts}, note)
    arr = parse_array(out)
    if len(arr) != len(texts):
        raise ValueError(f"longueur {len(arr)} ≠ {len(texts)}")
    return [str(x) for x in arr]


class Translator:
    def __init__(self, cache):
        self.cache = cache
        self.qa = {}
        self.failed = set()       # textes laissés en français (balises incohérentes, erreurs)
        self.stop = False         # budget épuisé
        self.lock = threading.Lock()
        if os.path.exists(QA_FILE):
            try:
                with open(QA_FILE, "r", encoding="utf-8") as f:
                    self.qa = json.load(f)
            except Exception:
                self.qa = {}
        n_purge = 0
        for k, v in list(self.qa.items()):
            if str(v.get("issue", "")).startswith("nom modifié") and not v.get("retried"):
                if k in self.cache.data:
                    self.cache.data.pop(k, None)
                    self.cache.dirty.add(k[:2])
                v["retried"] = True
                n_purge += 1
        if n_purge:
            print(f"↻ {n_purge} traductions avec nom modifié seront retentées une fois")

    def over_budget(self):
        return SPEND.usd >= BUDGET_USD

    def handle(self, fr, en, strict=True):
        blocking, warn = check(fr, en, strict)
        if blocking:
            return blocking
        self.cache.put(fr, en)
        k = key_of(fr)
        with self.lock:
            prev = self.qa.get(k) or {}
            if warn:
                entry = {"fr": fr[:400], "en": en[:400], "issue": warn}
                if prev.get("retried"):
                    entry["retried"] = True
                self.qa[k] = entry
            else:
                self.qa.pop(k, None)
        return None

    def run_batch(self, texts):
        if self.stop:
            return
        if self.over_budget():
            self.stop = True
            return
        try:
            res = translate_call(texts)
        except Exception as e:
            if len(texts) > 1:
                mid = len(texts) // 2
                self.run_batch(texts[:mid])
                self.run_batch(texts[mid:])
            else:
                print(f"⚠ échec sur un texte ({str(e)[:120]}) : {texts[0][:60]!r}")
                with self.lock:
                    self.failed.add(texts[0])
            return
        retry = []
        for fr, en in zip(texts, res):
            problem = self.handle(fr, en)
            if problem:
                retry.append((fr, problem))
        for fr, problem in retry:
            if self.stop or self.over_budget():
                self.stop = True
                return
            ok = False
            for attempt in range(2):
                try:
                    en = translate_call([fr], note=f"A previous attempt failed a check ({problem}). "
                                        "Keep every <tN> marker and every number exactly.")[0]
                except Exception:
                    break
                problem = self.handle(fr, en, strict=(attempt == 0))
                if not problem:
                    ok = True
                    break
            if not ok:
                with self.lock:
                    self.failed.add(fr)
                    self.qa[key_of(fr)] = {"fr": fr[:400], "en": "", "issue": f"gardé en français : {problem}"}

    def translate_all(self, payloads):
        todo = [p for p in dict.fromkeys(payloads) if self.cache.get(p) is None]
        batches, cur, size = [], [], 0
        for p in todo:
            if cur and (len(cur) >= BATCH_ITEMS or size + len(p) > BATCH_CHARS):
                batches.append(cur)
                cur, size = [], 0
            cur.append(p)
            size += len(p)
        if cur:
            batches.append(cur)
        done = 0
        with ThreadPoolExecutor(max_workers=1 if MOCK else WORKERS) as ex:
            futs = [ex.submit(self.run_batch, b) for b in batches]
            for f in futs:
                f.result()
                done += 1
                if done % 10 == 0 or done == len(futs):
                    print(f"  … {done}/{len(futs)} lots — dépense estimée {SPEND.usd:.2f} $")
        self.cache.save()
        with open(QA_FILE, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(self.qa.items())), f, ensure_ascii=False, indent=1)
        return len(todo), len(batches)

    def get(self, text):
        if text in self.failed:
            return None
        en = self.cache.get(text)
        return fix_en(en) if en else en


# ─────────────────────────────────────────────────────────────────────────────
# Application des traductions + réécriture des liens
# ─────────────────────────────────────────────────────────────────────────────
def shallow_clone(soup, tag):
    return soup.new_tag(tag.name, attrs=dict(tag.attrs))


def rebuild(soup, en_ph, tags):
    """Reconstruit les nœuds d'une unité à partir du texte traduit. ValueError si incohérent."""
    stack = [(None, [])]
    seen = []
    pos = 0
    for m in TOKEN.finditer(en_ph):
        text = en_ph[pos:m.start()]
        if text:
            stack[-1][1].append(NavigableString(unesc(text)))
        pos = m.end()
        closing, idx, selfclose = m.group(1) == "/", int(m.group(2)), m.group(3) == "/"
        if idx < 1 or idx > len(tags):
            raise ValueError("marqueur inconnu")
        if selfclose:
            stack[-1][1].append(shallow_clone(soup, tags[idx - 1]))
            seen.append(idx)
        elif not closing:
            stack.append((idx, []))
            seen.append(idx)
        else:
            if stack[-1][0] != idx:
                raise ValueError("imbrication")
            i, children = stack.pop()
            node = shallow_clone(soup, tags[i - 1])
            for c in children:
                node.append(c)
            stack[-1][1].append(node)
    tail = en_ph[pos:]
    if tail:
        stack[-1][1].append(NavigableString(unesc(tail)))
    if len(stack) != 1 or sorted(seen) != list(range(1, len(tags) + 1)):
        raise ValueError("marqueurs manquants")
    return stack[0][1]


SCRIPT_REL = re.compile(r"""(["'(])((?:\.\./)+)(?=[A-Za-z0-9_\-])""")


def fix_script_paths(s):
    """Dans les attributs on*/scripts en ligne : '../img/x' -> '/img/x' (chemins relatifs cassés dans /en/)."""
    return SCRIPT_REL.sub(lambda m: m.group(1) + "/", s)


def rewrite_url(val, rel, en_set):
    v = val.strip()
    if (not v or v.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "//", "http://", "https://", "sms:", "whatsapp:"))
            or ":" in v.split("/")[0]):
        return val
    m = re.match(r"^([^?#]*)(.*)$", v)
    path, tail = m.group(1), m.group(2)
    base = posixpath.dirname(rel)
    if path == "":
        return val
    target = posixpath.normpath(posixpath.join(base, path)) if not path.startswith("/") else path.lstrip("/")
    if target in (".", ""):
        target = "index.html"
    if target.endswith("/"):
        target += "index.html"
    if target in en_set:
        return "/en/" + target + tail
    return "/" + target + tail


def lang_switch_en(rel):
    return ('<!--sf-lang--><a class="sf-lang-switch" href="/%s" hreflang="fr" lang="fr" rel="alternate">'
            '🇫🇷 Français</a>' % rel + LANG_CSS + '<!--/sf-lang-->')


def lang_switch_fr(rel):
    return ('<!--sf-lang--><a class="sf-lang-switch" href="/en/%s" hreflang="en" lang="en" rel="alternate">'
            '🇬🇧 English</a>' % rel + LANG_CSS + '<!--/sf-lang-->')


LANG_CSS = ('<style>.sf-lang-switch{position:fixed;left:10px;bottom:76px;z-index:900;background:rgba(255,255,255,.94);'
            'color:#1d4f7a;border:1px solid #d6dde4;border-radius:20px;padding:6px 12px;font:600 .74rem/1 system-ui,sans-serif;'
            'text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,.15)}.sf-lang-switch:hover{background:#fff}</style>')


# Textes fabriqués par le JavaScript des pages (météo, boutons, alertes…) : remplacés tels quels
# dans les scripts en ligne des pages anglaises. Remplacement exact, sans appel à l'API.
JS_FIXES = [
    ("['Dim','Lun','Mar','Mer','Jeu','Ven','Sam']", "['Sun','Mon','Tue','Wed','Thu','Fri','Sat']"),
    ("'Auj.'", "'Today'"),
    ("'Vent '", "'Wind '"),
    ("'Neige au sol : '", "'Snow depth: '"),
    ("'Au-dessus de la normale ('", "'Above average ('"),
    ("'Dans la normale ('", "'Normal for the time of year ('"),
    ("'En dessous de la normale ('", "'Below average ('"),
    ("'Hors saison — enneigement non significatif'", "'Off-season — no significant snow cover'"),
    ("'Météo indisponible pour cette station'", "'Weather unavailable for this resort'"),
    ("'Météo momentanément indisponible'", "'Weather temporarily unavailable'"),
    ("'Voir moins ▲'", "'Show less ▲'"),
    ("'Lire plus ▼'", "'Read more ▼'"),
    ("'Retirer des favoris'", "'Remove from favourites'"),
    ("'Ajouter aux favoris'", "'Add to favourites'"),
    ("Vous pouvez comparer 3 stations maximum. Retirez-en une avant d'en ajouter une nouvelle.",
     "You can compare up to 3 resorts. Remove one before adding another."),
    ("Vous pouvez comparer 3 domaines maximum. Retirez-en un avant d'en ajouter un nouveau.",
     "You can compare up to 3 ski areas. Remove one before adding another."),
    ("cm de neige prévus à ", "cm of snow forecast at "),
    ("Va vite réserver avant que les prix montent !", "Book soon before prices go up!"),
    ("'Tous pays'", "'All countries'"),
    ("Les notifications sont déjà activées ✅", "Notifications are already enabled ✅"),
    ("Les notifications sont bloquées dans les réglages de ton navigateur.",
     "Notifications are blocked in your browser settings."),
]

# Fil d'Ariane (nav.breadcrumb) : libellés fixes, indépendants de l'API.
BREADCRUMB_FIXES = {
    "Accueil": "Home",
    "Stations de ski": "Ski resorts",
    "Recherche": "Search",
    "Comparateur": "Comparison tool",
    "Articles": "Articles",
    "Domaines skiables": "Ski areas",
    "Comparatifs": "Comparisons",
    "Actualités": "News",
}


def apply_js_fixes(s):
    for fr, en in JS_FIXES:
        s = s.replace(fr, en)
    return s


def fix_breadcrumb(soup):
    for nav in soup.select("nav.breadcrumb, .breadcrumb, .crumbs"):
        for node in list(nav.find_all(string=True)):
            t = str(node).strip()
            if t in BREADCRUMB_FIXES:
                node.replace_with(NavigableString(str(node).replace(t, BREADCRUMB_FIXES[t])))


def apply_page(rel, src_html, tr, en_set):
    soup = BeautifulSoup(strip_markers(src_html), "html.parser")
    jobs = analyze(soup)

    # 1. attributs, meta, JSON-LD
    for j in jobs["attr"]:
        en = tr.get(j["payload"])
        if en is not None:
            j["el"][j["attr"]] = en
    for j in jobs["meta"]:
        en = tr.get(j["payload"])
        if en is not None:
            j["el"]["content"] = en
    for j in jobs["json"]:
        for o, k in j["found"]:
            en = tr.get(o[k])
            if en is not None:
                o[k] = en
        if isinstance(j["data"], dict) and "inLanguage" in j["data"]:
            j["data"]["inLanguage"] = "en"
        txt = json.dumps(j["data"], ensure_ascii=False)
        txt = txt.replace(f"{SITE}/{rel}", f"{SITE}/en/{rel}")
        j["el"].string = txt

    # 2. textes isolés, puis unités (balises en ligne reconstruites)
    for j in jobs["orphan"]:
        en = tr.get(j["payload"])
        if en is None:
            continue
        orig = str(j["node"])
        lead = " " if orig[:1].isspace() else ""
        trail = " " if orig[-1:].isspace() else ""
        j["node"].replace_with(NavigableString(lead + unesc(en) + trail))
    for j in jobs["unit"]:
        en = tr.get(j["payload"])
        if en is None:
            continue
        try:
            nodes = rebuild(soup, en, j["tags"])
        except ValueError:
            continue    # garde le français plutôt qu'un lien cassé
        j["el"].clear()
        for n in nodes:
            j["el"].append(n)

    # 3. liens internes, chemins dans les scripts en ligne
    for el in soup.find_all(True):
        for a in URL_ATTRS:
            v = el.get(a)
            if isinstance(v, str):
                el[a] = rewrite_url(v, rel, en_set)
        for a in list(el.attrs):
            if a.startswith("on") and isinstance(el[a], str):
                el[a] = fix_script_paths(el[a])
        if el.name == "script" and not el.get("src") and (el.get("type") or "").lower() != "application/ld+json":
            if el.string:
                el.string.replace_with(apply_js_fixes(fix_script_paths(str(el.string))))
    fix_breadcrumb(soup)

    # 4. langue, canonical, hreflang, sélecteur de langue
    if soup.html:
        soup.html["lang"] = "en"
    head = soup.head
    if head:
        for l in head.find_all("link"):
            r = l.get("rel") or []
            if "canonical" in r or ("alternate" in r and l.get("hreflang")):
                l.decompose()
        fr_url, en_url = f"{SITE}/{rel}", f"{SITE}/en/{rel}"
        for h in (("canonical", None, en_url), ("alternate", "fr", fr_url),
                  ("alternate", "en", en_url), ("alternate", "x-default", fr_url)):
            attrs = {"rel": h[0], "href": h[2]}
            if h[1]:
                attrs["hreflang"] = h[1]
            head.append(soup.new_tag("link", attrs=attrs))
        for m in head.find_all("meta"):
            p = (m.get("property") or "").lower()
            if p == "og:url" or (m.get("name") or "").lower() == "twitter:url":
                m["content"] = en_url
            if p == "og:locale":
                m["content"] = "en_GB"
    body = soup.body
    out = str(soup)
    sw = lang_switch_en(rel)
    if "</body>" in out:
        out = out.replace("</body>", sw + "</body>", 1)
    else:
        out += sw
    return out


def patch_french(rel, html):
    """Ajoute hreflang + sélecteur de langue sur la page française (idempotent)."""
    html = re.sub(r"<!--sf-i18n-->.*?<!--/sf-i18n-->", "", html, flags=re.S)
    html = re.sub(r"<!--sf-lang-->.*?<!--/sf-lang-->", "", html, flags=re.S)
    block = ("<!--sf-i18n-->"
             f'<link rel="alternate" hreflang="fr" href="{SITE}/{rel}">'
             f'<link rel="alternate" hreflang="en" href="{SITE}/en/{rel}">'
             f'<link rel="alternate" hreflang="x-default" href="{SITE}/{rel}">'
             "<!--/sf-i18n-->")
    if re.search(r"</head>", html, re.I):
        html = re.sub(r"</head>", lambda m: block + m.group(0), html, count=1, flags=re.I)
    sw = lang_switch_fr(rel)
    if re.search(r"</body>", html, re.I):
        html = re.sub(r"</body>", lambda m: sw + m.group(0), html, count=1, flags=re.I)
    return html


# ─────────────────────────────────────────────────────────────────────────────
# Principal
# ─────────────────────────────────────────────────────────────────────────────
def discover():
    pages = []
    for pat in SOURCES:
        for p in glob.glob(os.path.join(ROOT, pat)):
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            name = posixpath.basename(rel)
            if name.startswith("_") or name in ("404.html", "index.html"):
                continue
            pages.append(rel)
    pages = sorted(set(pages))
    keep = []
    for rel in pages:
        with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
            head = f.read(6000).lower()
        if re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', head):
            continue
        keep.append(rel)
    return keep


def pick_sample(pages, n):
    by_dir = {}
    for p in pages:
        by_dir.setdefault(posixpath.dirname(p) or ".", []).append(p)
    out, i = [], 0
    dirs = sorted(by_dir)
    while len(out) < n and any(by_dir.values()):
        d = dirs[i % len(dirs)]
        if by_dir[d]:
            out.append(by_dir[d].pop(0))
        i += 1
    return out


def load_manifest():
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def main():
    global MOCK
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="ne traiter que N pages variées (test)")
    ap.add_argument("--only", default="", help="ne traiter que les pages dont le chemin contient ce texte")
    ap.add_argument("--dry-run", action="store_true", help="estime le coût sans appeler l'API ni écrire")
    ap.add_argument("--mock", action="store_true", help="faux traducteur pour tester sans API")
    ap.add_argument("--no-patch-fr", action="store_true", help="ne pas toucher aux pages françaises")
    args = ap.parse_args()
    MOCK = args.mock

    pages = discover()
    if args.only:
        pages = [p for p in pages if args.only in p]
    if args.limit:
        pages = pick_sample(pages, args.limit)
    if not pages:
        print("Aucune page à traduire.")
        return 0
    print(f"✓ {len(pages)} page(s) à traiter — modèle {MODEL}{' (MOCK)' if MOCK else ''}")

    cache = Cache()
    tr = Translator(cache)

    # Phase 1 : repérer tous les textes
    per_page = {}
    payloads = []
    for rel in pages:
        with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
            src = f.read()
        soup = BeautifulSoup(strip_markers(src), "html.parser")
        ps = all_payloads(analyze(soup))
        per_page[rel] = ps
        payloads.extend(ps)
    uniq = list(dict.fromkeys(payloads))
    new = [p for p in uniq if cache.get(p) is None]
    chars = sum(len(p) for p in new)
    est_in = int(chars / 3.2) + 1200 * max(1, len(new) // BATCH_ITEMS)
    est_out = int(chars / 3.2)
    est_usd = est_in / 1e6 * PRICE_IN + est_out / 1e6 * PRICE_OUT
    print(f"  {len(payloads)} textes sur les pages, {len(uniq)} distincts, {len(new)} à traduire "
          f"({chars} caractères) — coût estimé ≈ {est_usd:.2f} $")
    if args.dry_run:
        return 0

    # Phase 2 : traduire
    n, nb = tr.translate_all(payloads)
    if tr.stop:
        print(f"⛔ Budget de {BUDGET_USD:.0f} $ atteint : les pages incomplètes seront terminées au prochain passage.")

    # Phase 3 : écrire les pages complètes
    complete = [rel for rel in pages if all(tr.get(p) is not None or p in tr.failed for p in per_page[rel])]
    incomplete = [rel for rel in pages if rel not in complete]
    manifest = load_manifest()
    en_set = set(complete) | manifest
    if os.path.exists(os.path.join(ROOT, "en", "index.html")):
        en_set.add("index.html")
    written = 0
    kept_fr = 0
    for rel in complete:
        with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
            src = f.read()
        out = apply_page(rel, src, tr, en_set)
        dest = os.path.join(ROOT, "en", rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(out)
        written += 1
        if not args.no_patch_fr:
            patched = patch_french(rel, src)
            if patched != src:
                with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as f:
                    f.write(patched)
    # pages disparues côté français : retirer la version anglaise
    current = set(discover())
    removed = 0
    for rel in sorted(manifest - current):
        p = os.path.join(ROOT, "en", rel)
        if os.path.exists(p):
            os.remove(p)
            removed += 1
    manifest = (manifest & current) | set(complete)
    os.makedirs(os.path.dirname(MANIFEST_FILE), exist_ok=True)
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(manifest), f, indent=0)

    qa_issues = len(tr.qa)
    summary = (f"## Traduction anglaise\n"
               f"- Pages écrites : **{written}** · incomplètes (reprise au prochain passage) : {len(incomplete)} · retirées : {removed}\n"
               f"- Textes traduits dans ce passage : {n} en {nb} lots · appels API : {SPEND.calls}\n"
               f"- Dépense estimée : **{SPEND.usd:.2f} $** (entrée {int(SPEND.tin)} / sortie {SPEND.tout} tokens)\n"
               f"- Points à relire (nombres, noms) : {qa_issues} → i18n/qa-en.json\n")
    print(summary)
    sp = os.environ.get("GITHUB_STEP_SUMMARY")
    if sp:
        with open(sp, "a", encoding="utf-8") as f:
            f.write(summary)
    return 0


MOCK = False

if __name__ == "__main__":
    raise SystemExit(main())
