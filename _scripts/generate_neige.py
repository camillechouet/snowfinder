#!/usr/bin/env python3
"""
SnowFinder — Relevés de neige officiels (haut / bas du domaine) → neige.json
=============================================================================
Lit chaque jour le bulletin d'enneigement des domaines listés dans
_scripts/neige-sources.json (relevés transmis par les stations, repris par Skipass)
et écrit neige.json, que le bandeau « Enneigement » de la page d'accueil affiche.

Règles (aucune valeur inventée) :
* On ne garde un domaine que si le bulletin donne les DEUX hauteurs (haut et bas du domaine)
  avec leurs altitudes, et qu'il est daté de moins de MAX_AGE_DAYS jours (3 par défaut).
* Lecture par expressions régulières (gratuit). Si la mise en page change et que la lecture
  échoue, repli sur Claude Haiku (quelques centimes par mois), avec les mêmes contrôles.
* Une valeur absurde (négative, > 800 cm, altitude haut <= altitude bas) est refusée.
* Si le site de lecture est injoignable pour (presque) tous les domaines, neige.json existant
  est conservé tel quel : le bandeau ignore de lui-même les relevés de plus de 4 jours.

Usage
-----
  python3 _scripts/generate_neige.py                    # lecture réelle
  python3 _scripts/generate_neige.py --dry-run          # affiche sans écrire neige.json
  python3 _scripts/generate_neige.py --fixtures DIR     # lit DIR/<slug>.html au lieu du web (tests)
  python3 _scripts/generate_neige.py --no-llm           # sans repli Haiku

Variables : ANTHROPIC_API_KEY, NEIGE_MODEL (défaut claude-haiku-5-5), MAX_AGE_DAYS, SF_ROOT, NEIGE_TODAY (tests, AAAA-MM-JJ)
"""
import argparse
import datetime as dt
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SF_ROOT") or os.path.dirname(SCRIPT_DIR)
SOURCES_FILE = os.path.join(SCRIPT_DIR, "neige-sources.json")
OUT_FILE = os.path.join(ROOT, "neige.json")

MODEL = os.environ.get("NEIGE_MODEL", "claude-haiku-5-5")
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "3"))
MAX_CM = 800
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

MOIS = {"janv": 1, "janvier": 1, "fevr": 2, "févr": 2, "février": 2, "fevrier": 2, "mars": 3, "avr": 4, "avril": 4,
        "mai": 5, "juin": 6, "juil": 7, "juillet": 7, "aout": 8, "août": 8, "sept": 9, "septembre": 9,
        "oct": 10, "octobre": 10, "nov": 11, "novembre": 11, "dec": 12, "déc": 12, "décembre": 12, "decembre": 12}


def today():
    t = os.environ.get("NEIGE_TODAY")
    return dt.date.fromisoformat(t) if t else dt.date.today()


# ─────────────────────────────────────────────────────────────────────────────
# Lecture d'une page
# ─────────────────────────────────────────────────────────────────────────────
def page_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    txt = soup.get_text("\n")
    txt = txt.replace("\xa0", " ").replace(" ", " ")
    txt = re.sub(r"[ \t\r]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt


def month_num(word):
    w = word.lower().strip(". ")
    return MOIS.get(w) or MOIS.get(w[:4]) or MOIS.get(w[:3])


def infer_date(day, month, text, ref):
    """Date du bulletin. Année lue dans « Bulletin du 5 octobre 2026 » si possible, sinon la plus récente <= ref+1."""
    m = re.search(r"Bulletin du\s+%d\s+([A-Za-zéûèôî]+)\s+(\d{4})" % day, text)
    if m and month_num(m.group(1)) == month:
        try:
            return dt.date(int(m.group(2)), month, day)
        except ValueError:
            return None
    for y in (ref.year, ref.year - 1):
        try:
            d = dt.date(y, month, day)
        except ValueError:
            continue
        if d <= ref + dt.timedelta(days=1):
            return d
    return None


# « Enneigement du 5 oct. » puis, quelques caractères plus loin (libellé « Montagnes »…),
# « 20 cm à 3450m » et « 0 cm à 1550m »
RE_MAIN = re.compile(
    r"Enneigement du\s+(\d{1,2})\s+([A-Za-zéûèôî]+)\.?\D{0,80}?"
    r"(\d{1,4})\s*cm\s*(?:à|a|@)\s*(\d{3,4})\s*m\D{0,60}?"
    r"(\d{1,4})\s*cm\s*(?:à|a|@)\s*(\d{3,4})\s*m", re.I | re.S)


def parse_regex(text, ref):
    m = RE_MAIN.search(text)
    if not m:
        return None
    day, mon = int(m.group(1)), month_num(m.group(2))
    if not mon:
        return None
    d = infer_date(day, mon, text, ref)
    if not d:
        return None
    a_cm, a_alt, b_cm, b_alt = int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
    return {"date": d, "cm1": a_cm, "alt1": a_alt, "cm2": b_cm, "alt2": b_alt}


def validate(raw, ref):
    """raw : date + 2 mesures (cm, altitude). Retourne (résultat, raison_du_refus)."""
    if raw is None:
        return None, "bulletin non lu"
    d = raw["date"]
    age = (ref - d).days
    if age < -1:
        return None, f"date dans le futur ({d})"
    if age > MAX_AGE_DAYS:
        return None, f"bulletin trop ancien ({d}, {age} j)"
    pts = sorted([(raw["alt1"], raw["cm1"]), (raw["alt2"], raw["cm2"])])
    (alt_bas, cm_bas), (alt_haut, cm_haut) = pts
    if alt_haut <= alt_bas:
        return None, "altitudes incohérentes"
    if not (500 <= alt_bas <= 4000 and 1000 <= alt_haut <= 4900):
        return None, f"altitudes hors plage ({alt_bas}/{alt_haut})"
    for v in (cm_bas, cm_haut):
        if v < 0 or v > MAX_CM:
            return None, f"hauteur absurde ({v} cm)"
    return {"haut": cm_haut, "bas": cm_bas, "alt_haut": alt_haut, "alt_bas": alt_bas, "date": d.isoformat()}, None


# ─────────────────────────────────────────────────────────────────────────────
# Repli : Claude Haiku (seulement si les expressions régulières ne lisent rien)
# ─────────────────────────────────────────────────────────────────────────────
LLM_SYSTEM = ("Tu lis le texte d'une page de bulletin d'enneigement d'une station de ski française. "
              "Réponds UNIQUEMENT par un objet JSON : "
              '{"date":"AAAA-MM-JJ","cm_haut":N,"alt_haut":N,"cm_bas":N,"alt_bas":N} '
              "où date = date du bulletin d'enneigement, cm_haut/alt_haut = hauteur de neige (cm) et altitude (m) en haut "
              "du domaine, cm_bas/alt_bas = idem en bas. Si la page ne donne pas clairement les DEUX hauteurs avec leurs "
              'altitudes et une date, réponds {"date":null}. N\'invente rien, ne déduis rien, ne convertis rien.')


def llm_read(text, ref):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    i = text.find("Enneigement")
    excerpt = text[max(0, i - 300): i + 2500] if i >= 0 else text[:2800]
    body = {"model": MODEL, "max_tokens": 200, "system": LLM_SYSTEM,
            "messages": [{"role": "user", "content": f"Date du jour : {ref.isoformat()}\n\n{excerpt}"}]}
    data = json.dumps(body).encode("utf-8")
    for attempt in range(3):
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=data, method="POST",
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                              "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read().decode("utf-8"))
            out = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
            a, b = out.find("{"), out.rfind("}")
            j = json.loads(out[a:b + 1])
            if not j.get("date"):
                return None
            return {"date": dt.date.fromisoformat(j["date"]), "cm1": int(j["cm_haut"]), "alt1": int(j["alt_haut"]),
                    "cm2": int(j["cm_bas"]), "alt2": int(j["alt_bas"])}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            return None
        except Exception:
            return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Téléchargement
# ─────────────────────────────────────────────────────────────────────────────
def fetch(url):
    """(html, erreur). 404 = page inexistante (pas une panne)."""
    last = None
    for attempt in range(3):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9",
                                                   "Accept": "text/html,application/xhtml+xml"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, "404"
            last = f"HTTP {e.code}"
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(6 * (attempt + 1))
                continue
            return None, last
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
            if attempt < 2:
                time.sleep(4 * (attempt + 1))
                continue
    return None, last


def get_page(slug, url_tpl, fixtures):
    if fixtures:
        p = os.path.join(fixtures, slug + ".html")
        if not os.path.exists(p):
            return None, "404"
        with open(p, "r", encoding="utf-8") as f:
            return f.read(), None
    time.sleep(random.uniform(2.0, 4.0))
    return fetch(url_tpl.format(slug=slug))


# ─────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fixtures", default="")
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()

    ref = today()
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    out, log, net_errors = {}, [], 0
    for dom in cfg["domaines"]:
        nom = dom["nom"]
        res, why, tried = None, "page introuvable", []
        for slug in dom["slugs"]:
            html, err = get_page(slug, cfg["url_modele"], args.fixtures)
            tried.append(f"{slug}:{err or 'ok'}")
            if err == "404":
                continue
            if err:
                why = f"réseau ({err})"
                net_errors += 1
                break
            text = page_text(html)
            if re.search(r"Pas de bulletine? neige à jour", text, re.I):
                res, why = None, "Skipass : pas de bulletin à jour"
                break
            raw = parse_regex(text, ref)
            how = "regex"
            if raw is None and not args.no_llm and "nneigement" in text:
                raw = llm_read(text, ref)
                how = "llm"
            res, why = validate(raw, ref)
            if res:
                res["via"] = how
                break
        if res:
            via = res.pop("via", "regex")
            out[nom] = {**res, "couvre": dom["couvre"]}
            log.append(f"✓ {nom}: {res['haut']} cm à {res['alt_haut']} m / {res['bas']} cm à {res['alt_bas']} m ({res['date']}, {via})")
        else:
            log.append(f"– {nom}: ignoré — {why} [{', '.join(tried)}]")

    print("\n".join(log))
    total = len(cfg["domaines"])
    summary = (f"## Relevés de neige\n- Domaines lus : **{len(out)} / {total}** (date du jour : {ref})\n"
               + "\n".join("  - " + l for l in log) + "\n")
    sp = os.environ.get("GITHUB_STEP_SUMMARY")
    if sp:
        with open(sp, "a", encoding="utf-8") as f:
            f.write(summary)

    if net_errors >= max(3, int(total * 0.8)):
        print("⚠ Site de lecture injoignable pour presque tous les domaines : neige.json conservé tel quel.")
        return 0
    if args.dry_run:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    payload = {"maj": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ") if not os.environ.get("NEIGE_TODAY") else ref.isoformat(),
               "source": cfg.get("source_nom", ""),
               "stations": out}
    new_txt = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    old = ""
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            old = f.read()
    # ne pas réécrire (donc ne pas committer) si seules les heures de mise à jour changent
    def core(t):
        try:
            j = json.loads(t)
            return json.dumps(j.get("stations", {}), sort_keys=True)
        except Exception:
            return t
    if core(old) == core(new_txt):
        print("✓ Aucun changement dans les relevés.")
        return 0
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(new_txt)
    print(f"✓ neige.json écrit ({len(out)} domaines).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
