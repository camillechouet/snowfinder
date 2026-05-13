#!/usr/bin/env python3
"""
SnowFinder — Générateur de pages statiques par station
=======================================================
Modifiez la fonction render_page() pour changer le design
de toutes les pages stations d'un coup.

Déclenchement automatique via GitHub Actions quand recherche.html change.
Ou manuellement : python3 _scripts/generate_stations.py
"""
import re, json, unicodedata, os, sys

def slugify(name):
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')

BOOKING_AID = 'SnowFinder'  # ← REMPLACER par le vrai AID Booking.com une fois approuvé

NIV = {"debutant":"Débutant","intermediaire":"Intermédiaire","avance":"Avancé","expert":"Expert"}
AMB = {"luxe":"Luxe","festif":"Festif","famille":"Famille","nature":"Nature","village":"Village","avance":"Technique","soleil":"Ensoleillé"}
EQ  = {"snowpark":"Snowpark","garderie":"Garderie","restaurants":"Restaurants","telesiege":"Télésiège"}

# Charger les données depuis recherche.html
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
recherche_path = os.path.join(root_dir, 'recherche.html')

with open(recherche_path, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'const DATA = (\[.*?\]);', content, re.DOTALL)
if not m:
    print("ERREUR: const DATA non trouvé dans recherche.html")
    sys.exit(1)

DATA = json.loads(m.group(1))
print(f"✓ {len(DATA)} stations chargées")

# Index par massif pour les liens internes
by_massif = {}
for s in DATA:
    by_massif.setdefault(s['massif'], []).append(s)

def get_similar(s, n=4):
    candidates = [x for x in by_massif[s['massif']] if x['id'] != s['id']]
    candidates.sort(key=lambda x: -x['score'])
    return candidates[:n]

def render_similar_section(s):
    similar = get_similar(s, 4)
    if not similar:
        return ''
    cards = ''
    for sim in similar:
        sim_slug = slugify(sim['name'])
        sim_local = os.path.join(root_dir, 'img', f'{sim_slug}1.jpg')
        if os.path.exists(sim_local):
            photo = f'../img/{sim_slug}1.jpg'
        else:
            photo = sim.get('photo') or 'https://images.unsplash.com/photo-1551524559-8af4e6624178?w=400&q=80'
        prix_nuit = round(sim['forfait'] * 2.4)
        cards += f"""
        <a href="{sim_slug}.html" style="display:block;border-radius:10px;overflow:hidden;background:white;box-shadow:0 2px 10px rgba(0,0,0,.08);text-decoration:none;transition:transform .2s,box-shadow .2s" onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 6px 20px rgba(0,0,0,.12)'" onmouseout="this.style.transform='';this.style.boxShadow='0 2px 10px rgba(0,0,0,.08)'">
          <div style="position:relative;height:90px;overflow:hidden">
            <img src="{photo}" alt="{sim['name']}" style="width:100%;height:100%;object-fit:cover" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1551524559-8af4e6624178?w=400&q=80'">
            <div style="position:absolute;inset:0;background:linear-gradient(to top,rgba(0,0,0,.6),transparent)"></div>
            <div style="position:absolute;bottom:6px;left:8px;color:white;font-family:'DM Serif Display',serif;font-size:.85rem">{sim['name']}</div>
            <div style="position:absolute;top:6px;right:6px;background:#c49a6c;color:white;font-size:.65rem;font-weight:700;padding:2px 6px;border-radius:4px">{sim['score']:.1f} ⭐</div>
          </div>
          <div style="padding:8px 10px;display:flex;justify-content:space-between;align-items:center">
            <span style="font-size:.75rem;color:#5c4a35;font-weight:600">{sim['km']} km · {sim['alt_max']}m</span>
            <span style="font-size:.72rem;color:#3a7db8;font-weight:700">~{prix_nuit}€/nuit</span>
          </div>
        </a>"""
    return f"""
  <div style="margin-top:20px">
    <div style="font-family:'DM Serif Display',serif;font-size:1rem;color:#8a7060;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px;padding-bottom:7px;border-bottom:2px solid #f7efe2">
      ⛷ Autres stations {s['massif']}
    </div>
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px">
      {cards}
    </div>
    <a href="../recherche.html" style="display:block;text-align:center;margin-top:12px;padding:9px;background:#f7efe2;border-radius:8px;font-size:.82rem;font-weight:600;color:#3a7db8;border:1.5px solid #eddcbf">
      Voir toutes les stations {s['massif']} →
    </a>
  </div>"""

AMB_EMOJI = {
    "luxe": "💎", "festif": "🎉", "famille": "👨‍👩‍👧", 
    "nature": "🌿", "village": "🏡", "rider": "⚡", "soleil": "☀️"
}
AMB_DESC = {
    "luxe": "Destination premium, hébergements et services haut de gamme",
    "festif": "Après-ski animé, soirées et ambiance garantie",
    "famille": "Infrastructures pensées pour les enfants, pistes douces",
    "nature": "Cadre sauvage, authenticité, loin des grandes foules",
    "village": "Charme montagnard, architecture traditionnelle préservée",
    "rider": "Terrain technique, freeride et freestyle au programme",
    "soleil": "Exposition idéale, ensoleillement généreux en saison"
}
NIV_EMOJI = {"debutant": "🟢", "intermediaire": "🔵", "avance": "🔴", "expert": "⚫"}
NIV_DESC = {
    "debutant": "Larges pistes vertes et bleues, écoles de ski accessibles",
    "intermediaire": "Beau choix de bleues et rouges variées",
    "avance": "Rouges exigeantes et noires bien présentes",
    "expert": "Terrain technique, hors-piste et pentes raides"
}

def generate_verdict(s):
    """Génère 3 phrases éditoriales personnalisées par station."""
    sentences = []
    ambs = s.get('amb', [])
    nivs = s.get('niv', [])
    km = s['km']
    alt = s['alt_max']
    forfait = s['forfait']
    name = s['name']

    # Phrase 1 — domaine
    if km >= 200:
        sentences.append(
            f"Avec ses {km} km de pistes, {name} figure parmi les plus grands domaines skiables de France — "
            f"une semaine n'y suffit pas pour tout explorer."
        )
    elif km >= 100:
        sentences.append(
            f"Le domaine de {name} et ses {km} km offrent assez de variété pour skier toute une semaine "
            f"sans jamais repasser deux fois sur la même piste."
        )
    elif km >= 50:
        sentences.append(
            f"Avec {km} km de pistes bien tracées, {name} propose un domaine équilibré, "
            f"idéal pour progresser sans se sentir à l'étroit."
        )
    else:
        sentences.append(
            f"Station à taille humaine avec ses {km} km de pistes, {name} mise sur la qualité "
            f"plutôt que la quantité — une adresse sincère, loin de l'usine à ski."
        )

    # Phrase 2 — ambiance + public cible
    if 'luxe' in ambs:
        if forfait > 55:
            sentences.append(
                f"C'est clairement une destination haut de gamme : le forfait à {forfait}€/jour "
                f"et les hébergements premium font que le budget peut vite grimper, "
                f"surtout en vacances scolaires."
            )
        else:
            sentences.append(
                f"La station cultive une ambiance raffinée tout en restant relativement accessible "
                f"avec un forfait à {forfait}€/jour."
            )
    elif 'festif' in ambs and 'famille' not in ambs:
        sentences.append(
            f"L'après-ski est ici une vraie institution — si tu pars entre amis et veux autant "
            f"profiter de la montagne que des soirées, tu es à la bonne adresse."
        )
    elif 'famille' in ambs and 'debutant' in nivs:
        sentences.append(
            f"C'est l'une des stations les plus adaptées aux familles avec enfants : "
            f"pistes douces, garderies bien organisées et ambiance chaleureuse au pied des remontées."
        )
    elif 'rider' in ambs:
        sentences.append(
            f"Le freeride et le terrain technique sont ici des religions — "
            f"si tu cherches du challenge et de la poudreuse à dévaler, {name} coche toutes les cases."
        )
    elif 'nature' in ambs or 'village' in ambs:
        sentences.append(
            f"Loin des grandes stations industrielles, {name} a su garder son âme de village montagnard "
            f"— idéal si tu cherches l'authenticité plutôt que la foule et les néons."
        )
    elif 'expert' in nivs and 'debutant' not in nivs:
        sentences.append(
            f"Station orientée skieurs confirmés : les pistes noires et le relief exigeant "
            f"en font une destination peu recommandée pour les débutants, mais un terrain de jeu "
            f"exceptionnel pour les avancés."
        )
    else:
        sentences.append(
            f"Station polyvalente, {name} convient à des groupes aux niveaux variés "
            f"— un bon compromis si vous n'êtes pas tous du même niveau autour de la table."
        )

    # Phrase 3 — altitude / enneigement
    if alt >= 3000:
        sentences.append(
            f"L'altitude maximale de {alt}m assure un enneigement fiable de décembre à avril, "
            f"même lors des hivers doux — c'est l'un des gros atouts de la station."
        )
    elif alt >= 2500:
        sentences.append(
            f"Avec un point culminant à {alt}m, les conditions restent bonnes de janvier à fin mars "
            f"et les risques de manque de neige en milieu de saison sont limités."
        )
    elif alt >= 2000:
        sentences.append(
            f"L'enneigement est globalement fiable de mi-janvier à mi-mars. "
            f"En début ou fin de saison, mieux vaut vérifier les conditions avant de réserver."
        )
    else:
        sentences.append(
            f"L'altitude modérée ({alt}m) peut rendre les conditions aléatoires en début et fin de saison. "
            f"Janvier et février restent les mois les plus sûrs pour un enneigement optimal."
        )

    return ' '.join(sentences)


def generate_pour_qui(s):
    """Génère les profils de voyageurs recommandés."""
    ambs = s.get('amb', [])
    nivs = s.get('niv', [])
    items = []
    if 'famille' in ambs or 'debutant' in nivs:
        items.append(("👨‍👩‍👧", "Familles", "Parfait pour initier les enfants"))
    if 'festif' in ambs:
        items.append(("🎉", "Groupes d'amis", "Ambiance et après-ski au top"))
    if 'luxe' in ambs:
        items.append(("💎", "Voyageurs premium", "Services et hébergements haut de gamme"))
    if 'rider' in ambs or 'expert' in nivs:
        items.append(("🏂", "Riders & experts", "Terrain technique et off-piste"))
    if 'nature' in ambs or 'village' in ambs:
        items.append(("🌿", "Amoureux de nature", "Authenticité et cadre préservé"))
    if 'intermediaire' in nivs and len(items) < 3:
        items.append(("🔵", "Skieurs intermédiaires", "Beau choix de bleues et rouges"))
    if not items:
        items.append(("⛷", "Tous profils", "Station polyvalente et accessible"))
    return items


def generate_meilleure_periode(s):
    """Génère la meilleure période de visite selon l'altitude."""
    alt = s['alt_max']
    if alt >= 2800:
        return [
            ("Décembre", "⭐⭐⭐", "#2ea84e"),
            ("Janvier", "⭐⭐⭐⭐⭐", "#2ea84e"),
            ("Février", "⭐⭐⭐⭐⭐", "#2ea84e"),
            ("Mars", "⭐⭐⭐⭐", "#2ea84e"),
            ("Avril", "⭐⭐⭐", "#f0a500"),
        ]
    elif alt >= 2000:
        return [
            ("Décembre", "⭐⭐", "#f0a500"),
            ("Janvier", "⭐⭐⭐⭐⭐", "#2ea84e"),
            ("Février", "⭐⭐⭐⭐⭐", "#2ea84e"),
            ("Mars", "⭐⭐⭐⭐", "#2ea84e"),
            ("Avril", "⭐⭐", "#f0a500"),
        ]
    else:
        return [
            ("Décembre", "⭐⭐", "#f0a500"),
            ("Janvier", "⭐⭐⭐⭐", "#2ea84e"),
            ("Février", "⭐⭐⭐⭐", "#2ea84e"),
            ("Mars", "⭐⭐⭐", "#f0a500"),
            ("Avril", "⭐", "#cc2200"),
        ]


def render_page(s):
    slug = slugify(s['name'])
    canonical = f"https://snowfinder.fr/stations/{slug}.html"
    local_photo_path = os.path.join(root_dir, 'img', f'{slug}1.jpg')
    if os.path.exists(local_photo_path):
        photo = f'../img/{slug}1.jpg'
    else:
        photo = s.get('photo') or 'https://images.unsplash.com/photo-1551524559-8af4e6624178?w=1200&q=80'
    local_station_path = os.path.join(root_dir, 'img', f'{slug}2.jpg')
    photo_station = f'../img/{slug}2.jpg' if os.path.exists(local_station_path) else None
    prix_nuit = round(s['forfait'] * 2.4)
    niveaux = ", ".join(NIV.get(n, n) for n in s.get('niv', []))
    pts = s.get('pts', [])
    pts_html = "\n".join(f'<li style="padding:5px 0;border-bottom:1px solid #f7efe2">{p}</li>' for p in pts)
    booking_url = f"https://www.booking.com/searchresults.fr.html?ss={s['name'].replace(' ', '+')}+ski+france&aid={BOOKING_AID}&sid=station-{slug}"
    from urllib.parse import quote as _q
    _exp_base = "https://www.expedia.fr/go/hotel/search/Destination/?CityName=" + _q(s['name']) + "&City=" + _q(s['name']) + "&SortBy=distance&NumRoom=1&NumAdult1=1"
    expedia_url = f"http://www.dpbolvw.net/click-7570830-101709262?sid=station-{slug}&url={_q(_exp_base)}"
    verdict = generate_verdict(s)
    pour_qui = generate_pour_qui(s)
    periode = generate_meilleure_periode(s)

    # HTML "Pour qui?"
    pour_qui_html = ''.join(f'''
      <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 0;border-bottom:1px solid var(--wood-pale)">
        <span style="font-size:1.6rem;flex-shrink:0">{ico}</span>
        <div>
          <div style="font-weight:700;font-size:.88rem;color:var(--text);margin-bottom:2px">{label}</div>
          <div style="font-size:.78rem;color:var(--text-light)">{desc}</div>
        </div>
      </div>''' for ico, label, desc in pour_qui)

    # HTML période
    periode_html = ''.join(f'''
      <div style="text-align:center;flex:1">
        <div style="font-size:.68rem;font-weight:700;color:var(--text-light);margin-bottom:4px">{mois}</div>
        <div style="font-size:.7rem">{stars}</div>
      </div>''' for mois, stars, col in periode)

    # HTML profil ambiance (grandes tuiles)
    amb_tiles = ''.join(f'''
      <div style="background:var(--wood-pale);border-radius:12px;padding:14px 12px;text-align:center;border:1.5px solid var(--wood-light)">
        <div style="font-size:1.8rem;margin-bottom:5px">{AMB_EMOJI.get(a,"⛷")}</div>
        <div style="font-weight:700;font-size:.82rem;color:var(--text-mid);margin-bottom:3px">{AMB.get(a,a)}</div>
        <div style="font-size:.68rem;color:var(--text-light);line-height:1.4">{AMB_DESC.get(a,"")}</div>
      </div>''' for a in s.get('amb', []))

    # HTML niveaux (grandes tuiles)
    niv_tiles = ''.join(f'''
      <div style="background:var(--blue-light);border-radius:12px;padding:14px 12px;text-align:center;border:1.5px solid #c8dff0">
        <div style="font-size:1.5rem;margin-bottom:5px">{NIV_EMOJI.get(n,"⛷")}</div>
        <div style="font-weight:700;font-size:.82rem;color:var(--blue-dark);margin-bottom:3px">{NIV.get(n,n)}</div>
        <div style="font-size:.68rem;color:#4a7a9b;line-height:1.4">{NIV_DESC.get(n,"")}</div>
      </div>''' for n in s.get('niv', []))
    desc_long = s.get('desc_long') or s.get('desc', '')
    schema_obj = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "TouristAttraction",
                "@id": canonical + "#attraction",
                "name": s["name"],
                "description": s.get("desc", ""),
                "url": canonical,
                "image": photo,
                "touristType": "Skier",
                "address": {
                    "@type": "PostalAddress",
                    "addressCountry": "FR",
                    "addressRegion": s.get("region", "")
                },
                "aggregateRating": {
                    "@type": "AggregateRating",
                    "ratingValue": str(round(s.get("score", 4.0), 1)),
                    "bestRating": "5",
                    "worstRating": "1",
                    "ratingCount": "50"
                },
                "amenityFeature": [
                    {"@type": "LocationFeatureSpecification", "name": "Pistes de ski", "value": str(s["km"]) + " km"},
                    {"@type": "LocationFeatureSpecification", "name": "Remontees mecaniques", "value": str(s["remontees"])},
                    {"@type": "LocationFeatureSpecification", "name": "Altitude maximale", "value": str(s["alt_max"]) + " m"},
                    {"@type": "LocationFeatureSpecification", "name": "Altitude minimale", "value": str(s["alt_min"]) + " m"}
                ]
            },
            {
                "@type": "WebPage",
                "@id": canonical + "#webpage",
                "url": canonical,
                "name": s["name"] + " — Station de ski : pistes, enneigement, hébergements | SnowFinder",
                "isPartOf": {"@id": "https://snowfinder.fr/#website"},
                "inLanguage": "fr-FR",
                "breadcrumb": {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "Accueil", "item": "https://snowfinder.fr/"},
                        {"@type": "ListItem", "position": 2, "name": "Stations de ski", "item": "https://snowfinder.fr/recherche.html"},
                        {"@type": "ListItem", "position": 3, "name": s["massif"], "item": "https://snowfinder.fr/recherche.html"},
                        {"@type": "ListItem", "position": 4, "name": s["name"], "item": canonical}
                    ]
                }
            },
            {
                "@type": "Offer",
                "@id": canonical + "#offer",
                "name": "Forfait ski " + s["name"],
                "price": str(s["forfait"]),
                "priceCurrency": "EUR",
                "description": "Forfait journée adulte",
                "url": canonical
            }
        ]
    }
    schema = json.dumps(schema_obj, ensure_ascii=False)
    similar_html = render_similar_section(s)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{s['name']} — Station de ski : pistes, enneigement, hébergements | SnowFinder</title>
  <meta name="description" content="{s['name']} : {s['km']} km de pistes, altitude {s['alt_min']}-{s['alt_max']}m, forfait {s['forfait']}€/jour. {s.get('desc','')[:100]}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="SnowFinder">
  <meta property="og:url" content="{canonical}">
  <meta property="og:title" content="{s['name']} — Station de ski | SnowFinder">
  <meta property="og:description" content="{s['km']} km · {s['alt_max']}m · {s['forfait']}€/j · {s['massif']}">
  <meta property="og:image" content="{photo}">
  <meta property="og:locale" content="fr_FR">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{s['name']} — Station de ski | SnowFinder">
  <meta name="twitter:image" content="{photo}">
  <script type="application/ld+json">{schema}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    :root{{
      --wood-pale:#f7efe2;--wood-light:#eddcbf;--wood:#c49a6c;--wood-dark:#8b5e3c;
      --blue-light:#e8f3fb;--blue-mid:#3a7db8;--blue-dark:#1a5a8a;
      --text:#2a1f14;--text-mid:#5c4a35;--text-light:#8a7060;
      --white:#fff;--bg:#f5f1ec;--radius:14px;
    }}
    body{{font-family:"DM Sans",sans-serif;color:var(--text);background:var(--bg);min-height:100vh}}
    a{{color:inherit;text-decoration:none}}

    /* NAV */
    .nav{{
      background:var(--white);border-bottom:1.5px solid var(--wood-light);
      padding:0 24px;height:58px;display:flex;align-items:center;
      justify-content:space-between;position:sticky;top:0;z-index:100;
      box-shadow:0 2px 12px rgba(0,0,0,.06)
    }}
    .nav-logo{{display:flex;align-items:center;gap:9px;font-family:"DM Serif Display",serif;font-size:1.15rem;color:var(--blue-dark)}}
    .nav-logo img{{width:34px;height:34px;border-radius:8px}}
    .nav-back{{
      display:flex;align-items:center;gap:6px;font-size:.83rem;font-weight:600;
      color:var(--blue-mid);background:var(--blue-light);
      padding:7px 16px;border-radius:22px;transition:background .15s
    }}
    .nav-back:hover{{background:#d4eaf8}}

    /* HERO */
    .hero{{position:relative;height:clamp(320px,52vh,560px);overflow:hidden}}
    .hero img{{width:100%;height:100%;object-fit:cover;display:block}}
    .hero-overlay{{
      position:absolute;inset:0;
      background:linear-gradient(to top,rgba(0,0,0,.88) 0%,rgba(0,0,0,.3) 45%,rgba(0,0,0,.05) 100%)
    }}
    .hero-score{{
      position:absolute;top:18px;right:18px;
      background:var(--wood);color:white;font-weight:700;font-size:.95rem;
      padding:6px 13px;border-radius:9px;box-shadow:0 2px 8px rgba(0,0,0,.25)
    }}
    .hero-content{{position:absolute;bottom:0;left:0;right:0;padding:28px 28px 32px}}
    .hero-massif{{
      display:inline-block;background:rgba(255,255,255,.16);
      border:1px solid rgba(255,255,255,.28);border-radius:22px;
      padding:4px 14px;font-size:.7rem;font-weight:700;color:rgba(255,255,255,.92);
      text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;backdrop-filter:blur(8px)
    }}
    h1{{font-family:"DM Serif Display",serif;font-size:clamp(2rem,6vw,3.2rem);color:white;line-height:1.05;margin-bottom:6px}}
    .hero-region{{color:rgba(255,255,255,.75);font-size:.85rem;display:flex;align-items:center;gap:5px}}

    /* CONTAINER */
    .container{{max-width:980px;margin:0 auto;padding:32px 20px 60px}}

    /* BREADCRUMB */
    .breadcrumb{{font-size:.75rem;color:var(--text-light);margin-bottom:24px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
    .breadcrumb a{{color:var(--blue-mid);font-weight:500}}
    .breadcrumb a:hover{{text-decoration:underline}}

    /* STATS */
    .stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:28px}}
    @media(max-width:600px){{.stats-grid{{grid-template-columns:repeat(2,1fr)}}}}
    .stat-box{{
      background:var(--white);border-radius:var(--radius);
      padding:18px 12px;text-align:center;
      box-shadow:0 2px 10px rgba(0,0,0,.05);border:1px solid var(--wood-light)
    }}
    .stat-val{{font-family:"DM Serif Display",serif;font-size:1.55rem;color:var(--blue-dark);line-height:1}}
    .stat-lbl{{font-size:.67rem;color:var(--text-light);text-transform:uppercase;letter-spacing:.05em;margin-top:5px}}

    /* SECTIONS */
    .section{{background:var(--white);border-radius:var(--radius);padding:24px 28px;margin-bottom:16px;box-shadow:0 2px 10px rgba(0,0,0,.05);border:1px solid var(--wood-light)}}
    .section-title{{font-family:"DM Serif Display",serif;font-size:1.05rem;color:var(--text-mid);margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid var(--wood-pale)}}

    /* PISTES */
    .piste-row{{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--wood-pale)}}
    .piste-row:last-child{{border-bottom:none}}
    .piste-dot{{width:13px;height:13px;border-radius:50%;flex-shrink:0}}
    .piste-bar-wrap{{flex:1;height:6px;background:var(--wood-pale);border-radius:3px;overflow:hidden}}
    .piste-bar{{height:100%;border-radius:3px;transition:width .4s ease}}
    .piste-count{{font-weight:700;font-size:.92rem;min-width:28px;text-align:right}}

    /* TAGS */
    .tag{{display:inline-block;border-radius:22px;padding:4px 12px;font-size:.73rem;font-weight:600;margin:3px 2px}}
    .tag-niv{{background:var(--blue-light);color:var(--blue-dark)}}
    .tag-amb{{background:var(--wood-pale);color:var(--wood-dark)}}
    .tag-eq{{background:#e6f5eb;color:#1a6a2a}}

    /* PHOTO STATION */
    .photo-station{{width:100%;height:200px;object-fit:cover;border-radius:10px;margin-bottom:16px;display:block}}

    /* BOOKING CTA */
    .booking-cta{{
      background:linear-gradient(135deg,#1a5a8a 0%,#2e7ab5 100%);
      border-radius:var(--radius);overflow:hidden;margin-bottom:16px;
      box-shadow:0 4px 20px rgba(26,90,138,.22)
    }}
    .booking-cta-top{{padding:22px 24px 18px}}
    .booking-cta-label{{color:rgba(255,255,255,.7);font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}}
    .booking-cta-price{{font-family:"DM Serif Display",serif;color:white;font-size:1.8rem;line-height:1}}
    .booking-cta-sub{{color:rgba(255,255,255,.65);font-size:.78rem;margin-top:2px}}
    .booking-cta-badges{{display:flex;gap:7px;margin-top:12px;flex-wrap:wrap}}
    .booking-badge{{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22);border-radius:20px;padding:3px 10px;font-size:.68rem;color:rgba(255,255,255,.88);font-weight:600}}
    .booking-btns{{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid rgba(255,255,255,.12)}}
    .btn-booking{{
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      padding:15px 10px;background:#003580;text-decoration:none;gap:2px;transition:background .15s
    }}
    .btn-booking:hover{{background:#00286a}}
    .btn-expedia{{
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      padding:15px 10px;background:#ffcc00;text-decoration:none;gap:2px;
      border-left:1px solid rgba(0,0,0,.08);transition:background .15s
    }}
    .btn-expedia:hover{{background:#f0be00}}
    .btn-label{{font-weight:700;font-size:.82rem}}
    .btn-sub{{font-size:.66rem;opacity:.75}}

    /* EXPLORER LINKS */
    .related-link{{
      display:flex;align-items:center;justify-content:space-between;
      padding:11px 14px;background:var(--bg);border-radius:9px;margin-bottom:8px;
      border:1.5px solid var(--wood-light);font-size:.83rem;font-weight:600;
      color:var(--blue-mid);transition:background .15s,border-color .15s
    }}
    .related-link:hover{{background:var(--blue-light);border-color:var(--blue-mid)}}
    .related-link:last-child{{margin-bottom:0}}

    /* MAIN GRID */
    .main-grid{{display:grid;grid-template-columns:1fr 340px;gap:16px;align-items:start}}
    @media(max-width:800px){{.main-grid{{grid-template-columns:1fr}}}}

    /* SIDEBAR STICKY */
    .sidebar{{position:sticky;top:74px}}

    /* BIG CTA BOTTOM */
    .big-cta{{
      background:linear-gradient(135deg,#1a5a8a,#3a7db8);
      border-radius:var(--radius);padding:32px 28px;text-align:center;margin-top:8px;
      box-shadow:0 6px 28px rgba(26,90,138,.25)
    }}
    .big-cta h2{{font-family:"DM Serif Display",serif;color:white;font-size:1.5rem;margin-bottom:8px}}
    .big-cta p{{color:rgba(255,255,255,.78);font-size:.88rem;margin-bottom:20px}}
    .big-cta-btns{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}}
    .big-cta-btn{{font-weight:700;padding:13px 28px;border-radius:28px;font-size:.9rem;transition:transform .15s,box-shadow .15s}}
    .big-cta-btn:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.2)}}

    /* FOOTER */
    .footer{{background:var(--blue-dark);color:rgba(255,255,255,.65);text-align:center;padding:26px 20px;font-size:.78rem;margin-top:40px;line-height:1.8}}
    .footer a{{color:rgba(255,255,255,.85);font-weight:600}}
    .footer a:hover{{color:white}}
  </style>
</head>
<body>

<nav class="nav">
  <a href="../index.html" class="nav-logo">
    <img src="../logo.png" alt="SnowFinder">
    <span>SnowFinder</span>
  </a>
  <a href="../recherche.html" class="nav-back">← Toutes les stations</a>
</nav>

<div class="hero">
  <img src="{photo}" alt="{s['name']} station de ski" loading="eager">
  <div class="hero-overlay"></div>
  <div class="hero-score">{s['score']:.1f} ⭐</div>
  <div class="hero-content">
    <div class="hero-massif">⛷ {s['massif']}</div>
    <h1>{s['name']}</h1>
    <div class="hero-region">📍 {s['region']}</div>
  </div>
</div>

<div class="container">

  <nav class="breadcrumb">
    <a href="../index.html">Accueil</a> ›
    <a href="../recherche.html">Stations de ski</a> ›
    <a href="../recherche.html">{s['massif']}</a> ›
    <span>{s['name']}</span>
  </nav>

  <!-- STATS 4 colonnes -->
  <div class="stats-grid">
    <div class="stat-box">
      <div class="stat-val">{s['km']} km</div>
      <div class="stat-lbl">Pistes skiables</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{s['alt_max']}m</div>
      <div class="stat-lbl">Altitude max</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{s['remontees']}</div>
      <div class="stat-lbl">Remontées mécaniques</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{s['forfait']}€</div>
      <div class="stat-lbl">Forfait / jour</div>
    </div>
  </div>

  <div class="main-grid">

    <!-- COLONNE PRINCIPALE -->
    <div>

      <!-- NOTRE AVIS -->
      <div class="section" style="border-left:4px solid var(--blue-mid);background:linear-gradient(135deg,var(--white) 0%,var(--blue-light) 100%)">
        <div class="section-title" style="color:var(--blue-dark)">✍️ Notre avis sur {s['name']}</div>
        <p style="font-size:.97rem;line-height:1.85;color:var(--text-mid);font-style:italic">{verdict}</p>
      </div>

      <!-- À PROPOS -->
      <div class="section">
        <div class="section-title">À propos de {s['name']}</div>
        {f'<img src="{photo_station}" alt="{s["name"]} pistes de ski" class="photo-station" loading="lazy">' if photo_station else ''}
        <p style="font-size:.92rem;line-height:1.78;color:var(--text-mid)">{desc_long}</p>
        {f'<ul style="margin-top:14px;padding-left:0;list-style:none">{pts_html}</ul>' if pts_html else ''}
      </div>

      <!-- PISTES -->
      <div class="section">
        <div class="section-title">Domaine skiable — {s['km']} km · {s['alt_min']}m à {s['alt_max']}m</div>
        <div class="piste-row">
          <div class="piste-dot" style="background:#2ea84e"></div>
          <span style="flex:0 0 70px;font-size:.85rem;color:var(--text-mid)">Vertes</span>
          <div class="piste-bar-wrap"><div class="piste-bar" style="background:#2ea84e;width:{min(100, s['pistes']['v']*5)}%"></div></div>
          <span class="piste-count">{s['pistes']['v']}</span>
        </div>
        <div class="piste-row">
          <div class="piste-dot" style="background:#3a7db8"></div>
          <span style="flex:0 0 70px;font-size:.85rem;color:var(--text-mid)">Bleues</span>
          <div class="piste-bar-wrap"><div class="piste-bar" style="background:#3a7db8;width:{min(100, s['pistes']['b']*3)}%"></div></div>
          <span class="piste-count">{s['pistes']['b']}</span>
        </div>
        <div class="piste-row">
          <div class="piste-dot" style="background:#cc2200"></div>
          <span style="flex:0 0 70px;font-size:.85rem;color:var(--text-mid)">Rouges</span>
          <div class="piste-bar-wrap"><div class="piste-bar" style="background:#cc2200;width:{min(100, s['pistes']['r']*3)}%"></div></div>
          <span class="piste-count">{s['pistes']['r']}</span>
        </div>
        <div class="piste-row">
          <div class="piste-dot" style="background:#222"></div>
          <span style="flex:0 0 70px;font-size:.85rem;color:var(--text-mid)">Noires</span>
          <div class="piste-bar-wrap"><div class="piste-bar" style="background:#333;width:{min(100, s['pistes']['n']*6)}%"></div></div>
          <span class="piste-count">{s['pistes']['n']}</span>
        </div>
      </div>

      <!-- PROFIL — Ambiance -->
      <div class="section">
        <div class="section-title">Ambiance & caractère</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;margin-bottom:4px">
          {amb_tiles}
        </div>
      </div>

      <!-- PROFIL — Niveaux -->
      <div class="section">
        <div class="section-title">Niveaux recommandés</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px">
          {niv_tiles}
        </div>
      </div>

      <!-- POUR QUI ? -->
      <div class="section">
        <div class="section-title">Pour qui ?</div>
        <div style="padding-top:4px">
          {pour_qui_html}
        </div>
      </div>

      <!-- MEILLEURE PÉRIODE -->
      <div class="section">
        <div class="section-title">Meilleure période pour skier</div>
        <div style="display:flex;gap:4px;margin-top:4px">
          {periode_html}
        </div>
        <p style="font-size:.73rem;color:var(--text-light);margin-top:10px">Basé sur l'altitude et l'enneigement historique de la station</p>
      </div>

      <!-- INFOS PRATIQUES -->
      <div class="section">
        <div class="section-title">Informations pratiques</div>
        <p style="font-size:.88rem;line-height:1.72;color:var(--text-mid)">
          <strong>{s['name']}</strong> est une station de ski du massif <strong>{s['massif']}</strong>,
          située en <strong>{s['region']}</strong>. Le domaine skiable s'étend sur
          <strong>{s['km']} km de pistes</strong> entre {s['alt_min']} et {s['alt_max']} mètres d'altitude,
          desservi par {s['remontees']} remontées mécaniques. Le forfait journée est affiché à partir de
          <strong>{s['forfait']}€</strong> par adulte. Station recommandée pour les niveaux {niveaux.lower()}.
        </p>
      </div>

      {similar_html}

    </div>

    <!-- SIDEBAR -->
    <div class="sidebar">

      <!-- BOOKING CTA -->
      <div class="booking-cta">
        <div class="booking-cta-top">
          <div class="booking-cta-label">🏡 Hébergement à {s['name']}</div>
          <div class="booking-cta-price">Dès ~{prix_nuit}€</div>
          <div class="booking-cta-sub">par nuit · annulation gratuite</div>
          <div class="booking-cta-badges">
            <span class="booking-badge">✓ Paiement sécurisé</span>
            <span class="booking-badge">✓ Meilleur prix garanti</span>
          </div>
        </div>
        <div class="booking-btns">
          <a href="{booking_url}" target="_blank" rel="noopener sponsored" class="btn-booking">
            <span style="font-size:1.2rem">🏨</span>
            <span class="btn-label" style="color:white">Booking.com</span>
            <span class="btn-sub" style="color:rgba(255,255,255,.7)">Voir les offres →</span>
          </a>
          <a href="{expedia_url}" target="_blank" rel="noopener sponsored" class="btn-expedia">
            <span style="font-size:1.2rem">✈️</span>
            <span class="btn-label" style="color:#003580">Expedia</span>
            <span class="btn-sub" style="color:#003580">Réserver →</span>
          </a>
        </div>
      </div>

      <!-- EXPLORER -->
      <div class="section" style="margin-bottom:0">
        <div class="section-title">Explorer</div>
        <a href="../recherche.html" class="related-link">📍 Autres stations {s['massif']} <span>→</span></a>
        <a href="../comparateur.html" class="related-link">⚖️ Comparer des stations <span>→</span></a>
        <a href="../enneigement.html" class="related-link">❄️ Enneigement en direct <span>→</span></a>
        <a href="../hebergement.html" class="related-link">🏨 Rechercher un hébergement <span>→</span></a>
      </div>

    </div>
  </div>

  <!-- BIG CTA BAS DE PAGE -->
  <div class="big-cta">
    <h2>Réserver à {s['name']}</h2>
    <p>Annulation gratuite sur la plupart des offres · Paiement sécurisé</p>
    <div class="big-cta-btns">
      <a href="{booking_url}" target="_blank" rel="noopener sponsored" class="big-cta-btn" style="background:white;color:#003580">🏨 Booking.com</a>
      <a href="{expedia_url}" target="_blank" rel="noopener sponsored" class="big-cta-btn" style="background:#ffcc00;color:#003580">✈️ Expedia</a>
    </div>
  </div>

</div>

<footer class="footer">
  <strong>SnowFinder</strong> — Le guide complet des stations de ski françaises<br>
  <a href="../index.html">Accueil</a> · <a href="../recherche.html">Recherche</a> · <a href="../comparateur.html">Comparateur</a> · <a href="../mentions-legales.html">Mentions légales</a><br>
  <span style="font-size:.7rem;opacity:.7">Données indicatives · Forfaits haute saison adulte · À vérifier sur le site officiel de chaque station</span>
</footer>

</body>
</html>"""

# Générer
stations_dir = os.path.join(root_dir, 'stations')
os.makedirs(stations_dir, exist_ok=True)
count = 0
errors = []
for s in DATA:
    slug = slugify(s['name'])
    try:
        html = render_page(s)
        with open(os.path.join(stations_dir, f'{slug}.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        count += 1
    except Exception as e:
        errors.append(f"{s['name']}: {e}")

print(f"✓ {count}/{len(DATA)} pages générées dans stations/")
if errors:
    print("Erreurs:", errors)
