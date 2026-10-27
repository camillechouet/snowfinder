#!/usr/bin/env python3
"""
check_site.py — SnowFinder
──────────────────────────
Contrôle automatique du site après génération. Gratuit, aucune clé nécessaire.

Vérifie :
  1. Grammaire des noms de stations (« à Les Menuires », « de Le Lioran », « de Avoriaz »…)
  2. Texte cassé : {accolades} non remplies, undefined, NaN, None
  3. Une page par station (stations/xxx.html) et pages non vides
  4. Coordonnées GPS présentes pour chaque station (carte + météo)
  5. Liens internes et images locales qui existent vraiment
  6. (info) nombre de stations sans site officiel (lien Google de secours)

Utilisation :  python3 _scripts/check_site.py
Code de sortie : 1 si au moins une erreur (le workflow GitHub passe alors au rouge
et GitHub t'envoie un e-mail), 0 sinon.
"""
from __future__ import annotations
import json, os, re, sys, unicodedata
from html import unescape
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
DOSSIERS_PAGES = ["stations", "domaines", "comparatifs", "articles"]
PAGES_RACINE = ["index.html", "recherche.html", "comparateur.html", "enneigement.html",
                "hebergement.html", "tinder.html", "favoris.html", "domaines.html"]

erreurs: dict[str, list[str]] = {}
infos: list[str] = []


def err(cat: str, msg: str) -> None:
    erreurs.setdefault(cat, []).append(msg)


def slugify(name: str) -> str:
    s = name.lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")   # même règle que generate_stations.py


def charger_stations() -> list[dict]:
    txt = (ROOT / "stations-data.js").read_text(encoding="utf-8")
    m = re.search(r"window\.SF_DATA\s*=\s*(\[.*\]);", txt, re.S)
    if not m:
        sys.exit("❌ window.SF_DATA introuvable dans stations-data.js")
    return json.loads(m.group(1))


def texte_visible(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    return unescape(re.sub(r"<[^>]+>", " ", html))


def de_a_attendus(nom: str):
    """Renvoie (faux_de, faux_a) : les tournures fautives pour ce nom, ou None si le nom n'en pose pas."""
    fautes = []
    if re.match(r"^Les ", nom):
        fautes += [f"de {nom}", f"à {nom}"]
    elif re.match(r"^Le ", nom):
        fautes += [f"de {nom}", f"à {nom}"]
    elif re.match(r"^L['’]", nom):
        fautes += [f"de {nom}", f"à {nom}", f"de L {nom[2:]}"]
    elif re.match(r"^[AEIOUÀÂÉÈÊÎÔÛŒ]", nom):
        fautes += [f"de {nom}"]
    return fautes


def fichiers_html() -> list[Path]:
    out = []
    for d in DOSSIERS_PAGES:
        p = ROOT / d
        if p.is_dir():
            out += sorted(p.glob("*.html"))
    out += [ROOT / n for n in PAGES_RACINE if (ROOT / n).exists()]
    return out


def main() -> int:
    stations = charger_stations()
    noms = [s["name"] for s in stations]
    pages = fichiers_html()
    print(f"📍 Racine : {ROOT}")
    print(f"✓ {len(stations)} stations, {len(pages)} pages HTML à contrôler")

    # ── 1 & 2. Grammaire + texte cassé ───────────────────────────────────────
    motifs_fautes = []
    for n in noms:
        for f in de_a_attendus(n):
            motifs_fautes.append((n, f, re.compile(r"(?<![\wÀ-ÿ'’])" + re.escape(f) + r"(?![\wÀ-ÿ])")))
    casse = re.compile(r"\{[a-z_]+\}|\bundefined\b|\bNaN\b|\bNone\b|\{\{|\}\}")
    for f in pages:
        rel = f.relative_to(ROOT).as_posix()
        html = f.read_text(encoding="utf-8", errors="replace")
        txt = texte_visible(html)
        for n, faute, rx in motifs_fautes:
            if rx.search(txt):
                err("Grammaire", f"{rel} : « {faute} » (à corriger en contraction)")
        for m in casse.finditer(txt):
            ctx = txt[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
            err("Texte cassé", f"{rel} : …{ctx.strip()}…")
            break  # une alerte par page suffit
        if len(html) < 3000 and rel.split("/")[0] in ("stations", "domaines"):
            err("Page vide", f"{rel} ({len(html)} octets)")

    # ── 3. Une page par station ──────────────────────────────────────────────
    for n in noms:
        if not (ROOT / "stations" / f"{slugify(n)}.html").exists():
            err("Page station manquante", n)

    # ── 4. Coordonnées ───────────────────────────────────────────────────────
    rech = (ROOT / "recherche.html").read_text(encoding="utf-8")
    m = re.search(r"const COORDS_MAP\s*=\s*(\{.*?\});", rech, re.S)
    coords = json.loads(m.group(1)) if m else {}
    if not coords:
        err("Coordonnées", "tableau COORDS_MAP introuvable dans recherche.html")
    for n in noms:
        c = coords.get(n)
        if not c:
            err("Coordonnées", f"{n} : absente de la carte")
        elif not (-90 <= c[0] <= 90 and -180 <= c[1] <= 180) or (c[0] == 0 and c[1] == 0):
            err("Coordonnées", f"{n} : valeurs impossibles {c}")

    # ── 5. Liens internes et images locales ──────────────────────────────────
    attr = re.compile(r'(?:href|src)="([^"]+)"')
    deja = set()
    for f in pages:
        rel = f.relative_to(ROOT).as_posix()
        html = f.read_text(encoding="utf-8", errors="replace")
        html = re.sub(r"(?is)<script\b.*?</script>", " ", html)  # liens fabriqués en JavaScript : hors contrôle
        for m in attr.finditer(html):
            u = m.group(1).strip()
            if (not u or u.startswith(("http:", "https:", "//", "#", "mailto:", "tel:", "javascript:", "data:", "whatsapp:", "intent:"))
                    or "{" in u or "'+" in u or "' +" in u):
                continue
            u = unquote(u.split("#")[0].split("?")[0])
            if not u:
                continue
            cible = (ROOT / u.lstrip("/")) if u.startswith("/") else (f.parent / u)
            cible = Path(os.path.normpath(cible))
            if cible.is_dir():
                cible = cible / "index.html"
            if not cible.exists():
                if (u) in deja:
                    continue
                deja.add(u)
                err("Lien ou image introuvable", f"{u}  (vu dans {rel})")

    # ── 6. Info : stations sans site officiel ────────────────────────────────
    off = 0
    for n in noms:
        p = ROOT / "stations" / f"{slugify(n)}.html"
        if p.exists() and "google.com/search" in p.read_text(encoding="utf-8", errors="replace") and "site+officiel" in p.read_text(encoding="utf-8", errors="replace"):
            off += 1
    infos.append(f"{off} stations sans site officiel (lien Google de secours)")

    # ── Rapport ──────────────────────────────────────────────────────────────
    lignes = ["# Contrôle du site SnowFinder", ""]
    total = sum(len(v) for v in erreurs.values())
    if total == 0:
        lignes.append("✅ **Aucune erreur détectée.**")
    else:
        lignes.append(f"❌ **{total} problème(s) détecté(s)**")
        for cat, items in erreurs.items():
            lignes += ["", f"### {cat} ({len(items)})"]
            lignes += [f"- {i}" for i in items[:40]]
            if len(items) > 40:
                lignes.append(f"- … et {len(items) - 40} autres")
    lignes += ["", "### Infos"] + [f"- {i}" for i in infos]
    rapport = "\n".join(lignes)
    print(rapport)
    resume = os.environ.get("GITHUB_STEP_SUMMARY")
    if resume:
        with open(resume, "a", encoding="utf-8") as fh:
            fh.write(rapport + "\n")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
