#!/usr/bin/env python3
"""
SnowFinder — Flux RSS Pinterest (une épingle par station)
=========================================================
Chaque jour, choisit PINS_PAR_JOUR stations (ordre mélangé, stable, qui fait
tout le tour des stations avant de recommencer), fabrique pour chacune une image
verticale 1000x1500 (photo de img/ + titre + chiffres clés + snowfinder.fr) dans
img/pins/, et écrit pinterest-feed.xml (RSS) avec les épingles des FENETRE_JOURS
derniers jours. Pinterest lit ce flux et publie seul les nouveaux éléments.

Chaque image porte une ACCROCHE (l'atout n°1 de la station) écrite une seule fois
par l'IA à partir de la fiche de la station (stations-data.js uniquement), puis
mémorisée dans pinterest-hooks.json. Sans clé API, repli sur le 1er « point fort »
de la fiche. Le domaine skiable vient de pinterest-domaines.json.

Seules les photos déjà présentes dans img/ sont utilisées ; le crédit
(PHOTO_CREDITS) est repris dans la description de l'épingle.

Usage : python3 _scripts/generate_pinterest_feed.py [--date AAAA-MM-JJ]
Nécessite Pillow (pip install pillow).
"""
import os, re, json, random, unicodedata, sys, argparse, time
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

BASE = "https://snowfinder.fr"
PINS_PAR_JOUR = 3
FENETRE_JOURS = 7
W, H = 1000, 1500
SEED = "snowfinder-pinterest-v1"
PIN_VERSION = "v3"   # change-la pour régénérer toutes les images après un changement de design
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


def draw_logo(img):
    """Logo SnowFinder (logo.png à la racine) + nom, en haut à gauche."""
    d = ImageDraw.Draw(img)
    f = load_font(FONT_BOLD, 40)
    x = 56
    lp = os.path.join(ROOT, "logo.png")
    if os.path.exists(lp):
        try:
            lg = Image.open(lp).convert("RGBA")
            lg.thumbnail((92, 92), Image.LANCZOS)
            badge = Image.new("RGBA", (lg.width + 20, lg.height + 20), (0, 0, 0, 0))
            ImageDraw.Draw(badge).rounded_rectangle((0, 0, badge.width - 1, badge.height - 1),
                                                    radius=24, fill=(255, 255, 255, 235))
            img.alpha_composite(badge, (50, 46))
            img.alpha_composite(lg, (60, 56))
            x = 50 + badge.width + 18
        except Exception as e:  # noqa: BLE001
            print("⚠ logo illisible :", e)
    ty = 46 + 10 + (92 - 40) // 2
    d.text((x + 1, ty + 2), "SnowFinder", font=f, fill=(0, 0, 0, 110))
    d.text((x, ty), "SnowFinder", font=f, fill="white")


def make_pin(station, photo_path, out_path, hook=None, domaine=None):
    img = Image.open(photo_path).convert("RGB")
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((x, y, x + W, y + H))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for i in range(780):
        a = int(220 * (i / 780) ** 1.5)
        od.line([(0, H - 780 + i), (W, H - 780 + i)], fill=(8, 28, 48, a))
    for i in range(260):
        a = int(120 * (1 - i / 260) ** 1.5)
        od.line([(0, i), (W, i)], fill=(8, 28, 48, a))
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    d = ImageDraw.Draw(img)
    draw_logo(img)
    d = ImageDraw.Draw(img)

    MX, MW = 60, W - 120

    # accroche (2 lignes max, taille adaptée)
    hook_lines, hs = [], 60
    if hook:
        while hs >= 42:
            fh = load_font(FONT_BOLD, hs)
            hook_lines = wrap(d, hook, fh, MW - 34)
            if len(hook_lines) <= 3 and all(d.textlength(l_, font=fh) <= MW - 34 for l_ in hook_lines):
                break
            hs -= 4
        f_hook = load_font(FONT_BOLD, hs)
    hl = hs + 12

    # nom de la station
    name = station["name"]
    size = 84
    while size > 46:
        f_title = load_font(FONT_BOLD, size)
        lines = wrap(d, name, f_title, MW)
        if len(lines) <= 2 and all(d.textlength(l_, font=f_title) <= MW for l_ in lines):
            break
        size -= 6
    lh = size + 8

    # ligne massif · domaine (petit)
    sub = station["massif"]
    if domaine and domaine.lower() not in name.lower():
        sub += f"  ·  {domaine}"
    fsb = 36
    while fsb > 24 and d.textlength(sub, font=load_font(FONT_REG, fsb)) > MW:
        fsb -= 2
    f_sub = load_font(FONT_REG, fsb)

    # chiffres clés
    stats = []
    if station.get("alt_max"):
        stats.append(f'{station["alt_max"]} m')
    if station.get("km"):
        stats.append(f'{station["km"]} km de pistes')
    if station.get("forfait"):
        stats.append(f'forfait {station["forfait"]} €')
    stat_line = "  ·  ".join(stats)
    fs = 40
    while fs > 26 and d.textlength(stat_line, font=load_font(FONT_BOLD, fs)) > MW:
        fs -= 2
    f_stat = load_font(FONT_BOLD, fs)

    f_url = load_font(FONT_BOLD, 40)
    btn_h = 76
    # on empile de bas en haut
    y = H - 80 - btn_h
    btn_y = y
    y -= 28 + fs                      # chiffres clés
    stat_y = y
    y -= 14 + fsb + 6                 # massif · domaine
    sub_y = y
    y -= 10 + len(lines) * lh         # nom
    name_y = y
    if hook_lines:
        y -= 30 + len(hook_lines) * hl
    hook_y = y

    if hook_lines:
        bar_h = len(hook_lines) * hl - 8
        d.rounded_rectangle((MX, hook_y + 4, MX + 10, hook_y + 4 + bar_h), radius=5, fill=(237, 107, 47, 255))
        yy = hook_y
        for ln in hook_lines:
            d.text((MX + 34, yy), ln, font=f_hook, fill="white")
            yy += hl
    yy = name_y
    for ln in lines:
        d.text((MX, yy), ln, font=f_title, fill=(255, 255, 255, 255))
        yy += lh
    d.text((MX, sub_y), sub, font=f_sub, fill=(205, 225, 245, 255))
    d.text((MX, stat_y), stat_line, font=f_stat, fill="white")
    bw = int(d.textlength("snowfinder.fr", font=f_url)) + 64
    d.rounded_rectangle((MX, btn_y, MX + bw, btn_y + btn_h), radius=btn_h // 2, fill=(237, 107, 47, 255))
    d.text((MX + 32, btn_y + 15), "snowfinder.fr", font=f_url, fill="white")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.convert("RGB").save(out_path, "JPEG", quality=88, optimize=True)


# ── Accroches (écrites une fois par l'IA, mémorisées) ────────────────
HOOKS_PATH = os.path.join(ROOT, "pinterest-hooks.json")
HOOK_MODEL = os.environ.get("PIN_HOOK_MODEL", "claude-haiku-5-5")
HOOK_SYSTEM = (
    "Tu écris des accroches pour des épingles Pinterest de stations de ski françaises et européennes. "
    "Pour CHAQUE station, écris UNE accroche de 25 à 55 caractères qui donne envie de cliquer : "
    "l'atout n°1 de la station, concret et séduisant, comme « Skiez au-dessus des nuages » ou "
    "« 600 km de pistes, un seul forfait ». Règles strictes : tu t'appuies UNIQUEMENT sur la fiche fournie ; "
    "tout chiffre doit figurer dans la fiche ; aucun superlatif (meilleur, n°1, plus grand...) sauf s'il est "
    "écrit dans la fiche ; pas de point d'exclamation, pas d'emoji, pas de guillemets, pas de nom de la station "
    "dans l'accroche ; pas de majuscules sur chaque mot. Réponds UNIQUEMENT par un objet JSON "
    "{\"Nom exact de la station\": \"accroche\", ...}."
)
NUM_RE = re.compile(r"\d+")


def fiche_text(s):
    return " ".join(str(s.get(k, "")) for k in ("desc", "desc_long")) + " " + " ".join(s.get("pts") or []) + \
        " " + " ".join(str(s.get(k, "")) for k in ("alt_min", "alt_max", "km", "remontees", "forfait"))


def hook_ok(hook, s):
    if not isinstance(hook, str):
        return False
    h = hook.strip()
    if not (15 <= len(h) <= 62) or "!" in h or '"' in h or "«" in h:
        return False
    src = fiche_text(s)
    if any(n not in src for n in NUM_RE.findall(h)):
        return False
    for w in ("meilleur", "numéro 1", "n°1", "incontournable", "plus grand", "plus haut", "le plus"):
        if w in h.lower() and w not in src.lower():
            return False
    return True


def fallback_hook(s):
    for p_ in (s.get("pts") or []):
        p_ = (p_ or "").strip()
        if 15 <= len(p_) <= 62:
            return p_
    return None


def load_hooks():
    try:
        with open(HOOKS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def ensure_hooks(needed):
    """needed : stations de la fenêtre. Écrit les accroches manquantes (1 appel par lot)."""
    hooks = load_hooks()
    missing = [s for s in needed if not hook_ok(hooks.get(s["name"]), s)]
    if missing and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            client = anthropic.Anthropic()
            for i in range(0, len(missing), 20):
                batch = missing[i:i + 20]
                fiches = [{"name": s["name"], "massif": s["massif"], "desc": s.get("desc"),
                           "pts": s.get("pts"), "desc_long": (s.get("desc_long") or "")[:600],
                           "alt_max": s.get("alt_max"), "km": s.get("km")} for s in batch]
                for _ in range(2):
                    msg = client.messages.create(
                        model=HOOK_MODEL, max_tokens=2000, system=HOOK_SYSTEM,
                        messages=[{"role": "user", "content": json.dumps(fiches, ensure_ascii=False)}])
                    txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
                    try:
                        got = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
                    except Exception:  # noqa: BLE001
                        continue
                    for s in batch:
                        h = got.get(s["name"])
                        if hook_ok(h, s):
                            hooks[s["name"]] = h.strip()
                    batch = [s for s in batch if not hook_ok(hooks.get(s["name"]), s)]
                    if not batch:
                        break
        except Exception as e:  # noqa: BLE001
            print("⚠ accroches IA indisponibles :", e)
        with open(HOOKS_PATH, "w", encoding="utf-8") as f:
            json.dump(hooks, f, ensure_ascii=False, indent=1, sort_keys=True)
    elif missing:
        print("ℹ pas de clé API : repli sur les points forts de la fiche pour", len(missing), "stations")
    return hooks


def load_domaines():
    try:
        with open(os.path.join(ROOT, "pinterest-domaines.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


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


def description(s, hook=None):
    parts = []
    if hook:
        parts.append(hook)
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

    # stations de la fenêtre -> accroches
    window = []
    for back in range(FENETRE_JOURS):
        window += pins_for_day(ordered, today - timedelta(days=back))
    uniq = list({s["name"]: s for s in window}.values())
    hooks = ensure_hooks(uniq)
    domaines = load_domaines()

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
                hook = hooks.get(s["name"]) if hook_ok(hooks.get(s["name"]), s) else fallback_hook(s)
                make_pin(s, find_photo(s["name"]), out, hook=hook, domaine=domaines.get(s["name"]))
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
                  f'<description>{escape(description(s, hooks.get(s["name"]) if hook_ok(hooks.get(s["name"]), s) else None))}</description>',
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
