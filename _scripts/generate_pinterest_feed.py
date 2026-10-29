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
import os, re, json, random, unicodedata, sys, argparse, time, hashlib
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


def _first_existing(base):
    for ext in ('jpg', 'jpeg', 'png', 'webp', 'JPG', 'JPEG', 'PNG', 'WEBP'):
        p = os.path.join(ROOT, 'img', f'{base}.{ext}')
        if os.path.exists(p):
            return p
    return None


def find_photo(name, station=None, domaine=None):
    """1) photo propre de la station (img/<slug>1.jpg) ; 2) fichier indiqué dans le champ
    « photo » de la fiche ; 3) photo du domaine skiable relié (img/<domaine>1.jpg)."""
    p = _first_existing(f'{photo_slug(name)}1')
    if p:
        return p
    if station and station.get("photo"):
        q = os.path.join(ROOT, station["photo"].lstrip("/"))
        if os.path.exists(q):
            return q
    if domaine:
        return _first_existing(f'{photo_slug(domaine)}1')
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

    # accroche : UNE ligne si possible (taille 60 -> 38), sinon 2 lignes (60 -> 40)
    hook_lines, hs = [], 60
    if hook:
        found = False
        for size_ in range(60, 37, -2):
            fh = load_font(FONT_BOLD, size_)
            if d.textlength(hook, font=fh) <= MW - 34:
                hook_lines, hs, found = [hook], size_, True
                break
        if not found:
            for size_ in range(60, 39, -2):
                fh = load_font(FONT_BOLD, size_)
                ls = wrap(d, hook, fh, MW - 34)
                if len(ls) <= 2 and all(d.textlength(l_, font=fh) <= MW - 34 for l_ in ls):
                    hook_lines, hs, found = ls, size_, True
                    break
        if not found:
            fh = load_font(FONT_BOLD, 40)
            hook_lines, hs = wrap(d, hook, fh, MW - 34)[:2], 40
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
HOOK_MODEL = os.environ.get("PIN_HOOK_MODEL", "claude-sonnet-5-5")
HOOK_FALLBACK_MODELS = ["claude-haiku-5-5"]
HOOK_SYSTEM = (
    "Tu écris des accroches pour des épingles Pinterest de stations de ski françaises et européennes. "
    "Objectif : donner envie de cliquer. Pour CHAQUE station, écris UNE accroche de 25 à 50 caractères qui "
    "promet un bénéfice ou éveille la curiosité, à partir de l'atout n°1 de la station : ce que le skieur va "
    "vivre, ressentir ou trouver là-bas. Ton chaleureux et imagé, phrase courte, souvent à l'impératif. "
    "Exemples de style : « Skiez au-dessus des nuages », « Le grand huit des 3 Vallées », "
    "« Le ski en famille, sans stress », « Un glacier pour skier jusqu'en mai », "
    "« Glissez jusqu'au pied du village ». "
    "Règles strictes : l'image peut être évocatrice, mais le fait qui la porte doit figurer dans la fiche "
    "fournie (n'invente rien) ; tout chiffre doit figurer dans la fiche ; aucun superlatif (meilleur, n°1, "
    "plus grand...) sauf s'il est écrit dans la fiche ; INTERDIT : labels et jargon administratif "
    "(« Label Famille Plus », classements, appellations), simple liste de caractéristiques, dates d'histoire, "
    "point d'exclamation, emoji, guillemets, nom de la station, majuscules sur chaque mot. "
    "Varie les débuts de phrase : au plus une accroche sur quatre commence par « Skiez », et évite de répéter les mêmes tournures (« vrai village », « sans voiture »...) d'une station à l'autre. Deux stations ne doivent pas avoir la même accroche. Réponds UNIQUEMENT par un objet JSON "
    "{\"Nom exact de la station\": \"accroche\", ...}."
)
PROMPT_VERSION = "v2"   # change-la pour faire réécrire toutes les accroches
NUM_RE = re.compile(r"\d+")


def fiche_text(s):
    return " ".join(str(s.get(k, "")) for k in ("desc", "desc_long")) + " " + " ".join(s.get("pts") or []) + \
        " " + " ".join(str(s.get(k, "")) for k in ("alt_min", "alt_max", "km", "remontees", "forfait"))


def hook_reason(hook, s):
    """None si l'accroche est valable, sinon la raison du rejet."""
    if not isinstance(hook, str):
        return "pas du texte"
    h = hook.strip()
    if not (15 <= len(h) <= 70):
        return f"longueur {len(h)} (15-70 attendus)"
    if "!" in h or '"' in h or "«" in h or "»" in h:
        return "ponctuation interdite (! ou guillemets)"
    src = fiche_text(s)
    for n in NUM_RE.findall(h):
        if n not in src:
            return f"chiffre {n} absent de la fiche"
    for w in ("meilleur", "numéro 1", "n°1", "incontournable", "plus grand", "plus haut", "le plus"):
        if w in h.lower() and w not in src.lower():
            return f"superlatif « {w} » absent de la fiche"
    return None


def hook_ok(hook, s):
    return hook_reason(hook, s) is None


def fallback_hook(s):
    for p_ in (s.get("pts") or []):
        p_ = (p_ or "").strip()
        if 15 <= len(p_) <= 62:
            return p_
    return None


def load_hooks():
    try:
        with open(HOOKS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:  # noqa: BLE001
        return {}
    if data.get("_prompt") != PROMPT_VERSION:
        print("ℹ consignes d'accroches modifiées : toutes les accroches seront réécrites")
        return {}
    return data


def _ask_hooks(client, model, fiches):
    """Un appel : renvoie (dict d'accroches ou None). Journalise toute réponse vide."""
    msg = client.messages.create(
        model=model, max_tokens=8000, system=HOOK_SYSTEM,
        messages=[{"role": "user", "content":
                   "Fiches des stations (JSON) :\n" + json.dumps(fiches, ensure_ascii=False) +
                   "\n\nRéponds maintenant uniquement par l'objet JSON demandé."}])
    txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    if not txt.strip():
        types = [getattr(b, "type", "?") for b in msg.content]
        print(f"⚠ réponse vide ({model}) : stop_reason={msg.stop_reason}, blocs={types}")
        return None
    try:
        return json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
    except Exception:  # noqa: BLE001
        print(f"⚠ réponse illisible ({model}) : {txt[:200]!r}")
        return None


def ensure_hooks(needed):
    """needed : stations de la fenêtre. Écrit les accroches manquantes.
    Ordre : lot de 20 avec le modèle principal, puis modèle de secours, puis station par station."""
    hooks = load_hooks()
    hooks.pop("_prompt", None)
    missing = [s for s in needed if not hook_ok(hooks.get(s["name"]), s)]
    print(f"ℹ accroches : {len(needed) - len(missing)} déjà valides, {len(missing)} à écrire")
    if missing and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            client = anthropic.Anthropic()

            def fiche(s):
                return {"name": s["name"], "massif": s["massif"], "desc": s.get("desc"),
                        "pts": s.get("pts"), "desc_long": (s.get("desc_long") or "")[:600],
                        "alt_max": s.get("alt_max"), "km": s.get("km")}

            def absorb(got, batch):
                norm = {slugify(k): v for k, v in (got or {}).items()}
                for s in batch:
                    h = (got or {}).get(s["name"]) or norm.get(slugify(s["name"]))
                    if h is None:
                        continue
                    why = hook_reason(h, s)
                    if why is None and any(v == (h or "").strip() for k, v in hooks.items() if k != s["name"]):
                        why = "identique à celle d'une autre station"
                    if why is None:
                        hooks[s["name"]] = h.strip()
                    else:
                        print(f"⚠ accroche rejetée pour {s['name']} ({why}) : {h!r}")

            def todo(batch):
                return [s for s in batch if not hook_ok(hooks.get(s["name"]), s)]

            models = [HOOK_MODEL] + [m for m in HOOK_FALLBACK_MODELS if m != HOOK_MODEL]
            for i in range(0, len(missing), 15):
                batch = missing[i:i + 15]
                for model in models:
                    for _ in range(2):
                        if not batch:
                            break
                        absorb(_ask_hooks(client, model, [fiche(s) for s in batch]), batch)
                        batch = todo(batch)
                # dernier recours : une station à la fois
                for s in batch:
                    for model in models:
                        absorb(_ask_hooks(client, model, [fiche(s)]), [s])
                        if hook_ok(hooks.get(s["name"]), s):
                            break
                for s in todo(missing[i:i + 15]):
                    print(f"⚠ pas d'accroche IA pour {s['name']} : repli sur la fiche")
        except Exception as e:  # noqa: BLE001
            print("⚠ accroches IA indisponibles :", repr(e))
        with open(HOOKS_PATH, "w", encoding="utf-8") as f:
            json.dump({**hooks, "_prompt": PROMPT_VERSION}, f, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"ℹ pinterest-hooks.json : {len([k for k in hooks if k != '_prompt'])} accroches enregistrées")
    elif missing:
        print("ℹ pas de clé API (ANTHROPIC_API_KEY) : repli sur les points forts de la fiche pour", len(missing), "stations")
    return hooks


MANUEL_PATH = os.path.join(ROOT, "pinterest-hooks-manuel.json")


def apply_manual(hooks, stations):
    """pinterest-hooks-manuel.json : {"Station": "accroche"} écrase l'accroche de l'IA.
    Même contrôle (chiffres présents dans la fiche, longueur, ponctuation)."""
    try:
        with open(MANUEL_PATH, encoding="utf-8") as f:
            manual = json.load(f)
    except Exception:  # noqa: BLE001
        return hooks
    by = {s["name"]: s for s in stations}
    n = 0
    for name, h in manual.items():
        if name.startswith("_") or name not in by:
            continue
        why = hook_reason(h, by[name])
        if why:
            print(f"⚠ accroche manuelle ignorée pour {name} ({why}) : {h!r}")
        else:
            hooks[name] = h.strip()
            n += 1
    if n:
        print(f"ℹ {n} accroche(s) manuelle(s) appliquée(s)")
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
    dom = load_domaines()
    allok = [s for s in data if s.get("ok")]
    elig = [s for s in allok if find_photo(s["name"], s, dom.get(s["name"]))]
    own = sum(1 for s in elig if _first_existing(f'{photo_slug(s["name"])}1'))
    print(f"ℹ {len(allok)} stations actives : {len(elig)} avec photo exploitable "
          f"({own} photo propre, {len(elig) - own} via fiche/domaine), {len(allok) - len(elig)} sans photo (ignorées)")
    return elig


STATE_PATH = os.path.join(ROOT, "pinterest-state.json")


def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            st = json.load(f)
        st.setdefault("days", {})
        st.setdefault("seen", [])
        return st
    except Exception:  # noqa: BLE001
        return {"days": {}, "seen": []}


def pick_day(stations, state, day):
    """Choisit les stations du jour : d'abord celles JAMAIS épinglées (ex. photo tout juste
    ajoutée), puis les plus anciennement épinglées. Ordre stable (hash) à égalité."""
    last = {}
    for d_, names in state["days"].items():
        for n in names:
            if d_ > last.get(n, ""):
                last[n] = d_
    seen = set(state.get("seen") or [])
    # station "nouvelle" = éligible aujourd'hui mais pas au passage précédent (photo tout juste ajoutée)
    def is_new(n):
        return bool(seen) and n not in seen
    cand = sorted(stations, key=lambda s: (0 if is_new(s["name"]) else 1, last.get(s["name"], ""),
                                           hashlib.md5((SEED + s["name"]).encode("utf-8")).hexdigest()))
    return [s["name"] for s in cand[:PINS_PAR_JOUR]]


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
    by_name = {s["name"]: s for s in stations}
    state = load_state()
    changed = False
    current = sorted(by_name)
    days_win = [today - timedelta(days=back) for back in range(FENETRE_JOURS - 1, -1, -1)]  # ancien -> récent
    for day in days_win:
        k = day.isoformat()
        if k not in state["days"]:
            state["days"][k] = pick_day(stations, state, day)
            changed = True
            print(f"ℹ {k} : {', '.join(state['days'][k])}")
    if sorted(state.get("seen") or []) != current:
        state["seen"] = current
        changed = True
    if changed:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1, sort_keys=True)

    def pins_for_day(_ordered, day):  # stations du jour encore éligibles (photo toujours là)
        return [by_name[n] for n in state["days"].get(day.isoformat(), []) if n in by_name]

    ordered = None

    # stations de la fenêtre -> accroches
    window = []
    for back in range(FENETRE_JOURS):
        window += pins_for_day(ordered, today - timedelta(days=back))
    uniq = list({s["name"]: s for s in window}.values())
    hooks = apply_manual(ensure_hooks(uniq), uniq)
    domaines = load_domaines()

    items = []
    keep_files = set()
    for back in range(FENETRE_JOURS):
        day = today - timedelta(days=back)
        for j, s in enumerate(pins_for_day(ordered, day)):
            slug = slugify(s["name"])
            h_ = hooks.get(s["name"]) if hook_ok(hooks.get(s["name"]), s) else fallback_hook(s)
            tag = hashlib.md5((h_ or "").encode("utf-8")).hexdigest()[:6]
            fname = f"{slug}-{PIN_VERSION}-{tag}.jpg"
            keep_files.add(fname)
            out = os.path.join(ROOT, "img", "pins", fname)
            if not os.path.exists(out):
                hook = hooks.get(s["name"]) if hook_ok(hooks.get(s["name"]), s) else fallback_hook(s)
                make_pin(s, find_photo(s["name"], s, domaines.get(s["name"])), out, hook=hook, domaine=domaines.get(s["name"]))
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
