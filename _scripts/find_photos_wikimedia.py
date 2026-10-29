#!/usr/bin/env python3
"""
SnowFinder — Chercheur de photos libres (Wikimedia Commons)
===========================================================
Pour les stations SANS photo dans img/, cherche sur Wikimedia Commons une photo à
licence libre (CC0, domaine public, CC BY, CC BY-SA — jamais NC/ND), la télécharge,
GRAVE LE CRÉDIT directement sur l'image (bandeau centré en bas) et la nomme comme
tes photos habituelles (valthorens1.jpg). Le dossier de sortie est zippé par le
workflow : tu le télécharges, tu gardes les bonnes photos et tu les envoies dans img/.

Le crédit est centré et assez court pour rester visible quand l'image est recadrée en
portrait pour les épingles Pinterest (recadrage central).

Sorties (dossier photos-out/) :
  <slug>1.jpg      photo prête à envoyer dans img/ (crédit gravé si la licence l'exige)
  liste.csv        station, fichier, titre, auteur, licence, page Commons, score
  non-trouvees.txt stations sans photo exploitable

Usage : python3 _scripts/find_photos_wikimedia.py [--limit 40] [--offset 0] [--only "Valloire"]
"""
import os, re, sys, json, csv, time, html, argparse, unicodedata, urllib.request, urllib.parse, urllib.error, io

from PIL import Image, ImageDraw, ImageFont, ImageStat, ImageChops

ROOT = os.environ.get("SF_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://commons.wikimedia.org/w/api.php"
UA = "SnowFinderPhotoBot/1.0 (https://snowfinder.fr; photos libres pour fiches de stations)"
OUT = os.path.join(ROOT, "photos-out")
MAX_W = 2000
MIN_W, MIN_H = 1500, 900
MIN_SCORE = 6.0      # sous ce score, la photo n'est pas proposée
N_KEEP = 3           # 1 principale + 2 alternatives (dossier autres/)
MIN_SATURATION = 0.04  # refuse le noir et blanc (une photo de neige reste peu saturée : ne pas monter)
MIN_BRIGHT = 0.40      # refuse les photos de nuit
MAX_GREEN = 0.06       # refuse les photos d'été (beaucoup d'herbe)
MIN_SNOW = 0.12        # refuse les photos sans neige visible
FONT_REG = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"]

BAD_TITLE = re.compile(r"\b(map|carte|plan|logo|panneau|sign|diagram|schema|schéma|poster|affiche|flyer|"
                       r"portrait|interior|intérieur|parking|bus|train|car|voiture|facture|document|blason|"
                       r"coat of arms|flag|drapeau|anefo|bestanddeelnr|royal|koninklijke|prins|prince|princess|king|queen|"
                       r"president|président|minister|ministre|visit|visite|meeting|interview|vacation|vakantie|"
                       r"championship|championnat|world cup|coupe du monde|race|course|athlete|biathlon|olympic|"
                       r"olympique|ceremony|cérémonie|crash|accident|wreck|fire|incendie|"
                       r"church|kirche|chiesa|chapelle|chapel|crocifisso|crucifix|interno|interior|innen|bahnhof|"
                       r"stadion|stadium|hotel|villa|castle|burg|ruine|ruins|carnaval|carnival|procession|pride|"
                       r"kuhstall|hexenkuche|hexenküche|restaurant|bar|pub|apres|après|brücke|bridge|bench|"
                       r"bahn station|railway|gare|tunnel|cemetery|friedhof|museum|musée)\b", re.I)
WINTER = re.compile(r"\b(ski|skiing|piste|pistes|neige|snow|snowy|hiver|winter|télésiège|telesiege|chairlift|"
                    r"remontée|remontee|cable|téléphérique|station|resort|enneigé|poudreuse)\b", re.I)
SUMMER = re.compile(r"\b(été|summer|hiking|randonnée|vtt|bike|biking|lac|lake|fleur|flower|vache|cow)\b", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ASCII", "ignore").decode("ASCII").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def photo_slug(name):
    n = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"[^a-z0-9]", "", n.lower())


def has_own_photo(s):
    ps = photo_slug(s["name"])
    for ext in ("jpg", "jpeg", "png", "webp", "JPG", "JPEG", "PNG", "WEBP"):
        if os.path.exists(os.path.join(ROOT, "img", f"{ps}1.{ext}")):
            return True
    if s.get("photo") and os.path.exists(os.path.join(ROOT, s["photo"].lstrip("/"))):
        return True
    return False


# ── Wikimedia ─────────────────────────────────────────────────────────
def http_get(url, binary=False, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            return data if binary else data.decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            raise
        except Exception:
            if i < tries - 1:
                time.sleep(3)
                continue
            raise


def api_search(query):
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": query,
              "gsrnamespace": "6", "gsrlimit": "40", "prop": "imageinfo",
              "iiprop": "url|size|mime|extmetadata", "iiurlwidth": str(MAX_W)}
    data = json.loads(http_get(API + "?" + urllib.parse.urlencode(params)))
    return list((data.get("query") or {}).get("pages", {}).values())


def meta(info, key):
    return html.unescape(re.sub(r"<[^>]+>", "", (info.get("extmetadata", {}).get(key, {}) or {}).get("value", "") or "")).strip()


def license_kind(info):
    """'pd' (aucun crédit exigé), 'by' (crédit exigé) ou None (refusée)."""
    lic = (meta(info, "LicenseShortName") or meta(info, "UsageTerms")).lower()
    if not lic:
        return None
    toks = set(re.split(r"[\s\-_/]+", lic))
    if "nc" in toks or "nd" in toks or "fair" in toks or "gfdl" in toks and "cc" not in toks:
        return None
    if lic.startswith("cc0") or "public domain" in lic or lic.startswith("pd") or "domaine public" in lic:
        return "pd"
    if lic.startswith("cc by"):
        return "by"
    return None


def score_candidate(page, station):
    info = (page.get("imageinfo") or [{}])[0]
    if info.get("mime") != "image/jpeg":
        return None
    w, h = info.get("width", 0), info.get("height", 0)
    if w < MIN_W or h < MIN_H or not (1.25 <= w / h <= 2.3):
        return None
    kind = license_kind(info)
    if not kind:
        return None
    title = re.sub(r"^File:|\.jpe?g$", "", page.get("title", ""), flags=re.I)
    if BAD_TITLE.search(title):
        return None
    desc = meta(info, "ImageDescription")
    cats = meta(info, "Categories")
    text = norm(" ".join([title, desc, cats]))
    key = norm(station["name"])
    if key not in text:
        return None          # on exige le nom de la station : évite les mauvais lieux
    sc = 0.0
    if key in norm(title):
        sc += 5
    blob = " ".join([title, desc, cats])
    sc += min(len(WINTER.findall(blob)), 4) * 1.2
    sc -= min(len(SUMMER.findall(blob)), 3) * 1.5
    sc += min(w / 4000, 1)
    return {"score": sc, "info": info, "kind": kind, "title": title, "w": w, "h": h,
            "page_url": info.get("descriptionurl", ""), "artist": meta(info, "Artist") or "Wikimedia Commons",
            "license": meta(info, "LicenseShortName") or meta(info, "UsageTerms")}


def candidates_for(station):
    """Candidats triés par score décroissant (sans doublons de titre)."""
    queries = [f'"{station["name"]}" ski', f'"{station["name"]}" neige', f'"{station["name"]}"']
    found = {}
    for q in queries:
        try:
            pages = api_search(q)
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠ recherche « {q} » : {e!r}")
            continue
        time.sleep(1)
        for p in pages:
            c = score_candidate(p, station)
            if c and c["score"] >= MIN_SCORE and c["title"] not in found:
                found[c["title"]] = c
        if len(found) >= 6 and max(c["score"] for c in found.values()) >= 8:
            break
    return sorted(found.values(), key=lambda c: -c["score"])


def best_for(station):
    cs = candidates_for(station)
    return cs[0] if cs else None


# ── Crédit gravé sur l'image ──────────────────────────────────────────
def load_font(size):
    for p in FONT_REG:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def credit_text(c):
    artist = re.sub(r"\s+", " ", c["artist"]).strip()
    artist = re.sub(r"^(user|utilisateur)\s*:\s*", "", artist, flags=re.I)
    if len(artist) > 34:
        artist = artist[:33].rstrip() + "…"
    lic = re.sub(r"\s+", " ", c["license"]).strip()
    return f"© {artist} / {lic}"


def burn_credit(img, text):
    """Bandeau centré en bas, assez étroit pour survivre au recadrage portrait 2:3 des épingles."""
    w, h = img.size
    crop_w = (2 * h / 3)                       # largeur conservée par le recadrage portrait central
    max_w = min(crop_w * 0.92, w * 0.9)
    size = max(14, int(min(w, crop_w) * 0.04))   # taille proportionnelle à la partie visible (épingle)
    d = ImageDraw.Draw(img)
    f = load_font(size)
    while d.textlength(text, font=f) > max_w and size > 12:
        size -= 1
        f = load_font(size)
    t = text
    while d.textlength(t, font=f) > max_w and len(t) > 12:   # dernier recours : on raccourcit
        t = t[:-2].rstrip() + "…"
    tw = d.textlength(t, font=f)
    pad_x, pad_y = int(size * 0.7), int(size * 0.35)
    x0 = (w - tw) / 2 - pad_x
    y1 = h - int(size * 0.5)
    y0 = y1 - size - 2 * pad_y
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle((x0, y0, x0 + tw + 2 * pad_x, y1), radius=int(size * 0.5), fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    ImageDraw.Draw(img).text(((w - tw) / 2, y0 + pad_y - 1), t, font=f, fill=(255, 255, 255, 235))
    return img.convert("RGB")


def _frac(mask):
    """Part de pixels allumés (255) dans un masque 'L'."""
    return ImageStat.Stat(mask).mean[0] / 255.0


def image_problem(img):
    """None si la photo a l'air d'une photo d'hiver de jour ; sinon la raison du refus.
    Pillow seul (pas de numpy : le workflow n'installe que Pillow)."""
    t = img.copy()
    t.thumbnail((400, 400))
    t = t.convert("RGB")
    h, s_, v = t.convert("HSV").split()
    if ImageStat.Stat(s_).mean[0] / 255.0 < MIN_SATURATION:
        return "noir et blanc"
    # sépia / photo ancienne : presque tous les pixels clairs sont orange-jaune
    warm = ImageChops.multiply(ImageChops.multiply(h.point(lambda x: 255 if 8 <= x <= 36 else 0),
                                                   s_.point(lambda x: 255 if x >= 30 else 0)),
                               v.point(lambda x: 255 if x >= 90 else 0))
    lit = v.point(lambda x: 255 if x >= 90 else 0)
    if ImageStat.Stat(warm).mean[0] / max(ImageStat.Stat(lit).mean[0], 1) > 0.70:
        return "sépia (photo ancienne)"
    if ImageStat.Stat(v).mean[0] / 255.0 < MIN_BRIGHT:
        return "trop sombre (nuit ?)"
    r, g, b = t.split()
    # vert dominant : g > 1.08 r, g > 1.08 b, v > 0.2
    r108 = r.point(lambda x: min(255, int(x * 1.08)))
    b108 = b.point(lambda x: min(255, int(x * 1.08)))
    gr = ImageChops.subtract(g, r108).point(lambda x: 255 if x > 0 else 0)
    gb = ImageChops.subtract(g, b108).point(lambda x: 255 if x > 0 else 0)
    vm = v.point(lambda x: 255 if x > 51 else 0)
    green = ImageChops.multiply(ImageChops.multiply(gr, gb), vm)
    if _frac(green) > MAX_GREEN:
        return "trop d'herbe (été ?)"
    # neige : pixels clairs et peu saturés
    snow = ImageChops.multiply(s_.point(lambda x: 255 if x < 77 else 0),
                               v.point(lambda x: 255 if x > 158 else 0))
    if _frac(snow) < MIN_SNOW:
        return "pas assez de neige"
    return None


def too_dull(img):
    return image_problem(img) is not None


def process(station, cand, rank=0):
    """rank 0 = photo principale (racine) ; 1, 2 = alternatives (dossier autres/).
    Renvoie le chemin relatif écrit, ou la raison du refus (texte) si la photo est refusée."""
    url = cand["info"].get("thumburl") or cand["info"].get("url")
    raw = http_get(url, binary=True)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    prob = image_problem(img)
    if prob:
        return prob
    if img.width > MAX_W:
        img = img.resize((MAX_W, int(img.height * MAX_W / img.width)), Image.LANCZOS)
    if cand["kind"] == "by":
        img = burn_credit(img, credit_text(cand))
    base = photo_slug(station["name"])
    if rank == 0:
        rel = f"{base}1.jpg"
    else:
        rel = os.path.join("autres", f"{base}1-{'bc'[rank - 1]}.jpg")
    os.makedirs(os.path.dirname(os.path.join(OUT, rel)) or OUT, exist_ok=True)
    img.save(os.path.join(OUT, rel), "JPEG", quality=85, optimize=True)
    return rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--only", default="")
    a = ap.parse_args()

    with open(os.path.join(ROOT, "stations-data.js"), encoding="utf-8") as f:
        data = json.loads(re.search(r"window\.SF_DATA\s*=\s*(\[.*\]);", f.read(), re.DOTALL).group(1))
    todo = [s for s in data if s.get("ok") and not has_own_photo(s)]
    todo.sort(key=lambda s: (-(s.get("score") or 0), s["name"]))
    if a.only:
        todo = [s for s in todo if norm(a.only) in norm(s["name"])]
    total = len(todo)
    batch = todo[a.offset:a.offset + a.limit]
    print(f"ℹ {total} stations sans photo ; lot de {len(batch)} (offset {a.offset})")

    os.makedirs(OUT, exist_ok=True)
    rows, missing = [], []
    for i, s in enumerate(batch, 1):
        print(f"[{i}/{len(batch)}] {s['name']}")
        try:
            kept = 0
            for c in candidates_for(s):
                rel = process(s, c, rank=kept)
                if rel in ("noir et blanc", "trop sombre (nuit ?)", "trop d'herbe (été ?)", "pas assez de neige"):
                    print(f"   — refusée ({rel}) : {c['title'][:60]}")
                    continue
                rows.append([s["name"], rel.replace(os.sep, "/"), "principale" if kept == 0 else "alternative",
                             c["title"], re.sub(r"\s+", " ", c["artist"]), c["license"],
                             c["page_url"], round(c["score"], 1), c["w"]])
                print(f"   ✓ {rel} ({c['license']}, score {c['score']:.1f})")
                kept += 1
                if kept >= N_KEEP:
                    break
            if not kept:
                missing.append(s["name"]); print("   — aucune photo exploitable")
        except Exception as e:  # noqa: BLE001
            missing.append(s["name"]); print(f"   ⚠ échec : {e!r}")
        time.sleep(1)

    with open(os.path.join(OUT, "liste.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["station", "fichier", "rang", "titre Commons", "auteur", "licence", "page Commons", "score", "largeur"])
        w.writerows(rows)
    with open(os.path.join(OUT, "non-trouvees.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(missing) + "\n")
    nxt = a.offset + a.limit
    print(f"✓ {len({r[0] for r in rows})} stations avec photo ({len(rows)} fichiers), {len(missing)} sans résultat. Prochain lot : offset = {nxt} (reste {max(total - nxt, 0)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
