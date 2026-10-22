#!/usr/bin/env python3
"""
generate_contenus.py — SnowFinder
─────────────────────────────────
Lit le manifeste contenus.json et reconstruit, sans toucher au reste du site :
  1. index.html            : bloc « Nos derniers articles » (1 héros + 2 bandeaux)
                             bloc « Duel de stations »      (1 héros + 2 bandeaux)
  2. toutes-les-actus.html : grille complète des articles (articles/ ou racine)

Ce script NE touche PAS aux pages de duels ni à tous-les-comparatifs.html
(ils restent générés par generate_comparatifs.py).

Utilisation :
    python3 _scripts/generate_contenus.py            # écrit les fichiers
    python3 _scripts/generate_contenus.py --check    # n'écrit rien, signale ce qui changerait
    python3 _scripts/generate_contenus.py --root DOSSIER   # racine du dépôt (tests)

Sécurité : si une ancre est introuvable ou si le bloc à remplacer paraît anormal
(contient <script>, <footer>, <section>, <style> ou dépasse 20 000 caractères),
le fichier est laissé intact et le script se termine en erreur.
"""

from __future__ import annotations
import argparse
import html
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

MONTHS_LONG = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
               "août", "septembre", "octobre", "novembre", "décembre"]
MONTHS_SHORT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.",
                "août", "sept.", "oct.", "nov.", "déc."]

ANCHOR_ARTICLES = "<!-- NOS DERNIERS ARTICLES -->"
ANCHOR_DUELS = "<!-- DUEL DE STATIONS -->"
ANCHOR_FOOTER = "<footer"

REQUIRED_ARTICLE = ("slug", "title", "category", "excerpt", "img", "date", "read_min")
REQUIRED_DUEL = ("a", "b", "img")


# ── Utilitaires ──────────────────────────────────────────────────────────────

def esc(s: str) -> str:
    return html.escape(s, quote=False)


def slugify(name: str) -> str:
    """Identique à generate_comparatifs.py (slug canonique du site)."""
    s = name.lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = re.sub(r"['’\s]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def day_label(d: date) -> str:
    return "1er" if d.day == 1 else str(d.day)


def date_long(a: dict) -> str:
    if a.get("date_label"):
        return a["date_label"]
    d = date.fromisoformat(a["date"])
    return f"{day_label(d)} {MONTHS_LONG[d.month - 1]} {d.year}"


def date_short(a: dict) -> str:
    d = date.fromisoformat(a["date"])
    return f"{day_label(d)} {MONTHS_SHORT[d.month - 1]}"


def meta_line(a: dict) -> str:
    return f"{date_long(a)} · {a['read_min']} min de lecture"


# ── Chargement / validation du manifeste ─────────────────────────────────────

def load_manifest(path: Path) -> tuple[list[dict], list[dict]]:
    if not path.exists():
        sys.exit(f"❌ Manifeste introuvable : {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"❌ contenus.json invalide (ligne {e.lineno}, colonne {e.colno}) : {e.msg}")

    errors = []
    articles = data.get("articles", [])
    duels = data.get("duels", [])
    seen = set()
    for i, a in enumerate(articles):
        for k in REQUIRED_ARTICLE:
            if k not in a or a[k] in ("", None):
                errors.append(f"article #{i + 1} ({a.get('slug', '?')}) : champ « {k} » manquant")
        if a.get("slug") in seen:
            errors.append(f"article en double : {a['slug']}")
        seen.add(a.get("slug"))
        try:
            date.fromisoformat(a.get("date", ""))
        except ValueError:
            errors.append(f"article {a.get('slug', '?')} : date « {a.get('date')} » invalide (format AAAA-MM-JJ)")
    for i, d in enumerate(duels):
        for k in REQUIRED_DUEL:
            if k not in d or d[k] in ("", None):
                errors.append(f"duel #{i + 1} : champ « {k} » manquant")
    if len(articles) < 3:
        errors.append("il faut au moins 3 articles (1 héros + 2 bandeaux)")
    if len(duels) < 3:
        errors.append("il faut au moins 3 duels (1 héros + 2 bandeaux)")
    if errors:
        sys.exit("❌ Manifeste incorrect :\n  - " + "\n  - ".join(errors))

    # Tri : plus récent d'abord (tri stable → l'ordre du fichier départage les égalités)
    articles = sorted(articles, key=lambda a: a["date"], reverse=True)
    for d in duels:
        d["slug"] = f"{slugify(d['a'])}-vs-{slugify(d['b'])}"
    return articles, duels


def sanity_warnings(root: Path, articles: list[dict], duels: list[dict]) -> list[str]:
    """Avertissements non bloquants : pages ou images manquantes, articles non référencés."""
    warns = []
    art_dir = root / "articles"
    if art_dir.is_dir():
        known = {a["slug"] for a in articles}
        for a in articles:
            if not (art_dir / f"{a['slug']}.html").exists():
                warns.append(f"article sans page : articles/{a['slug']}.html")
        for p in sorted(art_dir.glob("*.html")):
            if p.stem not in known and p.stem != "toutes-les-actus":
                warns.append(f"page non référencée dans contenus.json : articles/{p.name}")
    comp_dir = root / "comparatifs"
    if comp_dir.is_dir():
        for d in duels:
            if not (comp_dir / f"{d['slug']}.html").exists():
                warns.append(f"duel sans page : comparatifs/{d['slug']}.html")
    img_dir = root / "img"
    if img_dir.is_dir():
        for item in articles + duels:
            img = item["img"]
            if img.startswith("/img/") and not (root / img.lstrip("/")).exists():
                warns.append(f"image absente : {img}")
    return warns


# ── Rendu : toutes-les-actus.html ────────────────────────────────────────────

def render_card(a: dict) -> str:
    return (
        f'    <a class="card" href="/articles/{a["slug"]}.html">\n'
        f'      <div class="card-img" style="background-image:url({a["img"]})"></div>\n'
        f'      <div class="card-body">\n'
        f'        <div class="card-cat">{esc(a["category"])}</div>\n'
        f'        <div class="card-title">{esc(a["title"])}</div>\n'
        f'        <div class="card-excerpt">{esc(a["excerpt"])}</div>\n'
        f'        <div class="card-meta">{meta_line(a)}</div>\n'
        f'      </div>\n'
        f'    </a>'
    )


GRID_RE = re.compile(
    r'(<h1>Toutes nos actus</h1>\s*<div class="grid">)(.*?)(</div>\s*</div>\s*</body>)',
    re.S,
)


def build_actus_page(page: str, articles: list[dict]) -> str | None:
    if not GRID_RE.search(page):
        return None
    cards = "\n\n".join(render_card(a) for a in articles)
    return GRID_RE.sub(lambda m: m.group(1) + "\n\n" + cards + "\n\n  " + m.group(3), page, count=1)


# ── Rendu : index.html ───────────────────────────────────────────────────────

HERO_CONTAINER = ('display:block;position:relative;height:260px;text-decoration:none;'
                  'border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(13,34,64,.18);margin-bottom:8px')
HERO_GRADIENT = 'linear-gradient(180deg,rgba(8,20,45,.05) 0%,rgba(8,20,45,.25) 45%,rgba(8,20,45,.88) 100%)'
BADGE_STYLE = ('position:absolute;top:14px;left:14px;background:{bg};backdrop-filter:blur(6px);'
               'border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:5px 12px;font-size:.68rem;'
               'font-weight:700;color:#fff;text-transform:uppercase;letter-spacing:.06em')
BAND_CONTAINER = ('display:flex;align-items:center;gap:10px;position:relative;border-radius:12px;overflow:hidden;'
                  'height:64px;text-decoration:none;box-shadow:0 2px 10px rgba(0,0,0,.22);padding:0 14px')
BAND_GRADIENT = 'linear-gradient(90deg,rgba(8,20,45,.88) 0%,rgba(8,20,45,.62) 55%,rgba(8,20,45,.3) 100%)'
BAND_TITLE = ("font-family:'DM Serif Display',serif;font-style:italic;font-size:1.05rem;color:white;"
              "white-space:nowrap;overflow:hidden;text-overflow:ellipsis")


def hero(href: str, img: str, badge: str, badge_bg: str, title: str, title_size: str, sub: str) -> str:
    return (
        f'  <a href="{href}" style="{HERO_CONTAINER}">\n'
        f'    <div style="position:absolute;inset:0;background:url({img}) center/cover no-repeat"></div>\n'
        f'    <div style="position:absolute;inset:0;background:{HERO_GRADIENT}"></div>\n'
        f'    <div style="{BADGE_STYLE.format(bg=badge_bg)}">{esc(badge)}</div>\n'
        f'    <div style="position:absolute;bottom:0;left:0;right:0;padding:18px 20px 20px">\n'
        f"      <div style=\"font-family:'DM Serif Display',serif;font-style:italic;font-size:{title_size};"
        f'color:white;line-height:1.15;margin-bottom:6px">{esc(title)}</div>\n'
        f'      <div style="font-size:.78rem;color:rgba(255,255,255,.7)">{esc(sub)}</div>\n'
        f'    </div>\n'
        f'  </a>'
    )


def band(href: str, img: str, title: str, date_txt: str, cta: str) -> str:
    date_span = (f'\n          <span style="font-size:.68rem;color:rgba(255,255,255,.65);white-space:nowrap">'
                 f'{date_txt}</span>') if date_txt else ''
    return (
        f'    <a href="{href}" style="{BAND_CONTAINER}">\n'
        f'      <div style="position:absolute;inset:0;background:url({img}) center/cover no-repeat"></div>\n'
        f'      <div style="position:absolute;inset:0;background:{BAND_GRADIENT}"></div>\n'
        f'      <div style="position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;width:100%;gap:10px">\n'
        f'        <div style="display:flex;align-items:baseline;gap:8px;min-width:0">\n'
        f'          <span style="{BAND_TITLE}">{esc(title)}</span>{date_span}\n'
        f'        </div>\n'
        f'        <span style="font-size:.7rem;color:#ffd97a;font-weight:700;white-space:nowrap">{cta}</span>\n'
        f'      </div>\n'
        f'    </a>'
    )


def build_articles_block(articles: list[dict]) -> str:
    h, b1, b2 = articles[0], articles[1], articles[2]
    hero_html = hero("/articles/" + h["slug"] + ".html", h["img"], h["category"],
                     "rgba(58,125,184,.85)", h["title"], "1.5rem", meta_line(h))
    return (
        f'{ANCHOR_ARTICLES}\n'
        f'<div class="section" style="padding-bottom:8px">\n'
        f'  <div class="section-header">\n'
        f'    <div class="section-title">Nos derniers articles</div>\n'
        f'    <a href="/articles/toutes-les-actus.html" class="section-link">Voir tous les articles →</a>\n'
        f'  </div>\n\n'
        f'  <!-- Hero : article le plus récent -->\n'
        f'{hero_html}\n\n'
        f'  <!-- Bandeaux : 2 articles suivants -->\n'
        f'  <div style="display:flex;flex-direction:column;gap:8px">\n'
        + "\n".join(
            band("/articles/" + a["slug"] + ".html", a["img"], a.get("short") or a["title"], date_short(a), "Lire →")
            for a in (b1, b2)
        )
        + '\n  </div>\n</div>\n\n'
    )


def build_duels_block(duels: list[dict], badge_text: str) -> str:
    h, b1, b2 = duels[0], duels[1], duels[2]
    hero_html = hero("/comparatifs/" + h["slug"] + ".html", h["img"], badge_text,
                     "rgba(168,120,64,.85)", h["a"] + " vs " + h["b"], "1.6rem",
                     "Notre comparatif détaillé")
    return (
        f'{ANCHOR_DUELS}\n'
        f'<div class="section" style="padding-bottom:20px">\n'
        f'  <div class="section-header">\n'
        f'    <div class="section-title">Duel de stations</div>\n'
        f'    <a href="/comparatifs/tous-les-comparatifs.html" class="section-link">Voir tous les duels →</a>\n'
        f'  </div>\n\n'
        f'  <!-- Hero : duel le plus récent -->\n'
        f'{hero_html}\n\n'
        f'  <!-- Bandeaux : 2 duels suivants -->\n'
        f'  <div style="display:flex;flex-direction:column;gap:8px">\n'
        + "\n".join(
            band("/comparatifs/" + d["slug"] + ".html", d["img"], d["a"] + " vs " + d["b"], "", "Voir →")
            for d in (b1, b2)
        )
        + '\n  </div>\n</div>\n\n\n\n\n'
    )


def replace_block(text: str, start: str, end: str, new_block: str) -> tuple[str | None, str | None]:
    """Remplace text[start:end] par new_block, avec garde-fous. Retourne (texte, erreur)."""
    i = text.find(start)
    if i < 0:
        return None, f"ancre introuvable : {start}"
    j = text.find(end, i + len(start))
    if j < 0:
        return None, f"fin de bloc introuvable ({end}) après {start}"
    old = text[i:j]
    if len(old) > 20000:
        return None, f"bloc à remplacer anormalement long ({len(old)} caractères) après {start}"
    for bad in ("<script", "<footer", "<section", "<style"):
        if bad in old:
            return None, f"le bloc après {start} contient {bad} : remplacement refusé"
    return text[:i] + new_block + text[j:], None


def old_duel_badge(text: str) -> str:
    """Récupère le libellé actuel du badge du héros « Duel », pour ne pas changer le wording."""
    i = text.find(ANCHOR_DUELS)
    if i >= 0:
        m = re.search(r'letter-spacing:\.06em">([^<]+)</div>', text[i:i + 6000])
        if m:
            return html.unescape(m.group(1))
    return "Duel du moment"


def build_index(page: str, articles: list[dict], duels: list[dict]) -> tuple[str | None, str | None]:
    out, err = replace_block(page, ANCHOR_ARTICLES, ANCHOR_DUELS, build_articles_block(articles))
    if err:
        return None, err
    badge = old_duel_badge(out)
    return replace_block(out, ANCHOR_DUELS, ANCHOR_FOOTER, build_duels_block(duels, badge))


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="n'écrit rien, indique ce qui changerait")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="racine du dépôt")
    args = ap.parse_args()
    root: Path = args.root.resolve()

    print(f"📍 Racine : {root}")
    articles, duels = load_manifest(root / "contenus.json")
    print(f"✓ {len(articles)} articles, {len(duels)} duels dans contenus.json")

    warns = sanity_warnings(root, articles, duels)
    for w in warns[:12]:
        print(f"⚠️  {w}")
    if len(warns) > 12:
        print(f"⚠️  … et {len(warns) - 12} autre(s) avertissement(s)")

    failed = False
    changed = 0

    def apply(path: Path, builder) -> None:
        nonlocal failed, changed
        old = path.read_text(encoding="utf-8")
        new, err = builder(old)
        if err or new is None:
            print(f"❌ {path.relative_to(root)} : {err or 'structure non reconnue'} — fichier laissé intact")
            failed = True
            return
        if new == old:
            print(f"= {path.relative_to(root)} : déjà à jour")
            return
        changed += 1
        if args.check:
            print(f"~ {path.relative_to(root)} : serait modifié")
        else:
            path.write_text(new, encoding="utf-8")
            print(f"✏️  {path.relative_to(root)} : mis à jour")

    index = root / "index.html"
    if index.exists():
        apply(index, lambda t: build_index(t, articles, duels))
    else:
        print("⚠️  index.html introuvable")

    actus_candidates = [root / "articles" / "toutes-les-actus.html", root / "toutes-les-actus.html"]
    found = [p for p in actus_candidates if p.exists()]
    if not found:
        print("⚠️  toutes-les-actus.html introuvable (articles/ ni racine)")
    for p in found:
        apply(p, lambda t: (build_actus_page(t, articles), None) if GRID_RE.search(t)
              else (None, "grille « Toutes nos actus » non reconnue"))

    print()
    if failed:
        sys.exit("❌ Terminé avec des erreurs (voir ci-dessus).")
    print(f"🎉 Terminé : {changed} fichier(s) {'à modifier' if args.check else 'modifié(s)'}.")


if __name__ == "__main__":
    main()
