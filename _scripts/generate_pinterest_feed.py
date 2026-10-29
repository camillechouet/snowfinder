#!/usr/bin/env python3
"""
SnowFinder — Flux RSS Pinterest (une épingle par station)
=========================================================
Chaque jour, choisit PINS_PAR_JOUR stations (ordre mélangé, stable, qui fait
tout le tour des stations avant de recommencer), fabrique pour chacune une image
verticale 1000x1500 (photo de img/ + titre + chiffres clés + snowfinder.fr) dans
img/pins/, et écrit pinterest-feed.xml (RSS) avec les épingles des FENETRE_JOURS
derniers jours. Pinterest lit ce flux et publie seul les nouveaux éléments.

Seules les photos déjà présentes dans img/ sont utilisées ; le crédit
(PHOTO_CREDITS) est repris dans la description de l'épingle.

Usage : python3 _scripts/generate_pinterest_feed.py [--date AAAA-MM-JJ]
Nécessite Pillow (pip install pillow).
"""
import os, re, json, random, unicodedata, sys, argparse
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

BASE = "https://snowfinder.fr"
PINS_PAR_JOUR = 3
FENETRE_JOURS = 7
W, H = 1000, 1500
SEED = "snowfinder-pinterest-v1"
PIN_VERSION = "v2"   # change-la pour régénérer toutes les images après un changement de design
FONT_BOLD = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]
FONT_REG = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf"]

# Crédits photo : mêmes valeurs que PHOTO_CREDITS dans generate_stations.py
PHOTO_CREDITS = {
    "Sainte-Foy-Tarentaise": "David André",
    "Pralognan-la-Vanoise": "Pierre Guilbaud",
}

ROOT = os.environ.get("SF_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slugify(name):  # identique à generate_stations.py
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]+', '-', name).strip('-')


def photo_slug(name):  # identique à to_photo_slug()
    n = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    return re.sub(r'[^a-z0-9]', '', n.lower())


def find_photo(name):
    ps = photo_slug(name)
    for ext in ('jpg', 'jpeg', 'png', 'webp', 'JPG', 'JPEG', 'PNG', 'WEBP'):
        p = os.path.join(ROOT, 'img', f'{ps}1.{ext}')
        if os.path.exists(p):
            return p
    return None


def load_font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap(draw, text, font, max_w):
    """Retour à la ligne aux espaces ET après les tirets (Saint-Martin-de-Belleville)."""
    pieces = []  # (texte, espace_avant)
    for wi, word in enumerate(text.split()):
        for pi, part in enumerate(re.findall(r'[^-]+-?|-', word)):
            pieces.append((part, wi > 0 and pi == 0))
    lines, cur = [], ""
    for part, sp in pieces:
        t = cur + (" " if sp and cur else "") + part
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = part
    if cur:
        lines.append(cur)
    return lines


def make_pin(station, photo_path, out_path):
    img = Image.open(photo_path).convert("RGB")
    # recadrage "cover" vers 1000x1500
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((x, y, x + W, y + H))
    # dégradé sombre bas + léger haut
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for i in range(700):
        a = int(215 * (i / 700) ** 1.6)
        od.line([(0, H - 700 + i), (W, H - 700 + i)], fill=(8, 28, 48, a))
    for i in range(260):
        a = int(120 * (1 - i / 260) ** 1.5)
        od.line([(0, i), (W, i)], fill=(8, 28, 48, a))
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    d = ImageDraw.Draw(img)

    f_top = load_font(FONT_BOLD, 38)
    f_title = load_font(FONT_BOLD, 108)
    f_sub = load_font(FONT_REG, 46)
    f_stat = load_font(FONT_BOLD, 50)
    f_url = load_font(FONT_BOLD, 42)

    d.text((60, 60), "❄ SNOWFINDER" if False else "SNOWFINDER", font=f_top, fill=(255, 255, 255, 235))

    # titre (réduit si trop long)
    name = station["name"]
    size = 108
    while size > 56:
        f_title = load_font(FONT_BOLD, size)
        lines = wrap(d, name, f_title, W - 120)
        if len(lines) <= 2 and all(d.textlength(l_, font=f_title) <= W - 120 for l_ in lines):
            break
        size -= 8
    lh = size + 12
    sub = f'{station["massif"]}'
    stats = []
    if station.get("alt_max"):
        stats.append(f'{station["alt_max"]} m')
    if station.get("km"):
        stats.append(f'{station["km"]} km de pistes')
    if station.get("forfait"):
        stats.append(f'forfait {station["forfait"]} €')
    stat_line = "  ·  ".join(stats)

    fs = 50
    while fs > 30 and d.textlength(stat_line, font=load_font(FONT_BOLD, fs)) > W - 120:
        fs -= 2
    f_stat = load_font(FONT_BOLD, fs)
    # --- bloc "À savoir" : 2 points forts de la station ---
    f_lab = load_font(FONT_BOLD, 30)
    f_pt = load_font(FONT_BOLD, 40)
    pts = [p.strip() for p in (station.get("pts") or []) if p and p.strip()][:2]
    pt_lines = []
    for p_ in pts:
        wl = wrap(d, p_, f_pt, W - 120 - 90)[:2]
        pt_lines.append(wl)
    box_h = 0
    if pt_lines:
        box_h = 28 + 44 + sum(len(wl) * 52 + 14 for wl in pt_lines) + 14

    block_h = len(lines) * lh + 70 + 80 + 120
    y = H - 90 - block_h
    if pt_lines:
        top = y - box_h - 40
        bx = Image.new("RGBA", (W - 80, box_h), (0, 0, 0, 0))
        ImageDraw.Draw(bx).rounded_rectangle((0, 0, W - 81, box_h - 1), radius=28, fill=(8, 28, 48, 175))
        img.alpha_composite(bx, (40, top))
        d = ImageDraw.Draw(img)
        d.text((70, top + 24), "A SAVOIR", font=f_lab, fill=(255, 150, 90, 255))
        yy = top + 24 + 52
        for wl in pt_lines:
            d.text((70, yy), "•", font=f_pt, fill=(255, 150, 90, 255))
            for ln_ in wl:
                d.text((112, yy), ln_, font=f_pt, fill="white")
                yy += 52
            yy += 14
    for ln in lines:
        d.text((60, y), ln, font=f_title, fill="white")
        y += lh
    d.text((60, y + 8), sub, font=f_sub, fill=(220, 235, 248, 255))
    y += 70
    d.text((60, y + 10), stat_line, font=f_stat, fill=(255, 255, 255, 255))
    y += 110
    d.rounded_rectangle((60, y, 60 + 560, y + 78), radius=39, fill=(237, 107, 47, 255))
    d.text((90, y + 17), "snowfinder.fr", font=f_url, fill="white")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.convert("RGB").save(out_path, "JPEG", quality=88, optimize=True)


def load_stations():
    with open(os.path.join(ROOT, "stations-data.js"), encoding="utf-8") as f:
        js = f.read()
    m = re.search(r'window\.SF_DATA\s*=\s*(\[.*\]);', js, re.DOTALL)
    data = json.loads(m.group(1))
    return [s for s in data if s.get("ok") and find_photo(s["name"])]


def order(stations):
    names = sorted(s["name"] for s in stations)
    random.Random(SEED).shuffle(names)
    by = {s["name"]: s for s in stations}
    return [by[n] for n in names]


def pins_for_day(ordered, day):
    n = len(ordered)
    k = day.toordinal() * PINS_PAR_JOUR
    return [ordered[(k + i) % n] for i in range(PINS_PAR_JOUR)]


def description(s):
    parts = []
    d = (s.get("desc") or "").strip()
    if d:
        parts.append(d)
    pts = s.get("pts") or []
    if pts:
        parts.append(" • ".join(pts[:3]))
    cred = PHOTO_CREDITS.get(s["name"])
    if cred:
        parts.append(f"Photo © {cred}")
    parts.append("Compare les stations de ski sur SnowFinder.fr")
    txt = " — ".join(parts)
    return txt[:480]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    a = ap.parse_args()
    today = date.fromisoformat(a.date) if a.date else datetime.now(timezone.utc).date()

    stations = load_stations()
    if len(stations) < 20:
        print("⚠ Moins de 20 stations avec photo — flux NON écrit (sécurité).")
        return 1
    ordered = order(stations)

    items = []
    keep_files = set()
    for back in range(FENETRE_JOURS):
        day = today - timedelta(days=back)
        for j, s in enumerate(pins_for_day(ordered, day)):
            slug = slugify(s["name"])
            fname = f"{slug}-{PIN_VERSION}.jpg"
            keep_files.add(fname)
            out = os.path.join(ROOT, "img", "pins", fname)
            if not os.path.exists(out):
                make_pin(s, find_photo(s["name"]), out)
            dt = datetime(day.year, day.month, day.day, 5, 40 + 5 * j, tzinfo=timezone.utc)
            items.append((dt, s, slug, fname, day))

    # nettoyage des anciennes images
    pdir = os.path.join(ROOT, "img", "pins")
    for f in os.listdir(pdir):
        if f.endswith(".jpg") and f not in keep_files:
            os.remove(os.path.join(pdir, f))

    items.sort(key=lambda t: t[0], reverse=True)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom">',
             '<channel>',
             '<title>SnowFinder — stations de ski</title>',
             f'<link>{BASE}/</link>',
             '<description>Comparateur de stations de ski en France et en Europe</description>',
             '<language>fr</language>',
             f'<atom:link href="{BASE}/pinterest-feed.xml" rel="self" type="application/rss+xml"/>']
    for dt, s, slug, fname, day in items:
        link = f"{BASE}/stations/{slug}.html"
        img = f"{BASE}/img/pins/{fname}"
        title = f'{s["name"]} : pistes, altitude et forfait'
        # guid unique par station ET par jour => un cycle suivant republie la station
        guid = f"{BASE}/stations/{slug}.html#pin-{day.isoformat()}"
        size = os.path.getsize(os.path.join(pdir, fname))
        lines += ['<item>',
                  f'<title>{escape(title)}</title>',
                  f'<link>{escape(link)}</link>',
                  f'<guid isPermaLink="false">{escape(guid)}</guid>',
                  f'<pubDate>{format_datetime(dt)}</pubDate>',
                  f'<description>{escape(description(s))}</description>',
                  f'<enclosure url="{escape(img)}" length="{size}" type="image/jpeg"/>',
                  f'<media:content url="{escape(img)}" medium="image" type="image/jpeg" width="{W}" height="{H}"/>',
                  '</item>']
    lines += ['</channel>', '</rss>']
    with open(os.path.join(ROOT, "pinterest-feed.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"✓ pinterest-feed.xml : {len(items)} épingles, {len(stations)} stations éligibles")
    for dt, s, *_ in items[:PINS_PAR_JOUR]:
        print("   aujourd'hui :", s["name"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
