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
    desc_long = s.get('desc_long') or s.get('desc', '')
    snow_html = f'''<div style="background:linear-gradient(135deg,#e8f3fb,#d0e8f8);border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:10px;margin-bottom:12px"><span style="font-size:1.5rem">❄️</span><div><div style="font-weight:700;color:#1a5a8a;font-size:1.1rem">{s["snow"]} cm</div><div style="font-size:.78rem;color:#5a8ab8">Enneigement actuel</div></div></div>''' if s.get('snow') else ''
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

      <!-- PROFIL -->
      <div class="section">
        <div class="section-title">Profil de la station</div>
        <div style="margin-bottom:14px">
          <div style="font-size:.7rem;color:var(--text-light);margin-bottom:6px;font-weight:700;text-transform:uppercase;letter-spacing:.05em">Niveaux</div>
          {''.join(f'<span class="tag tag-niv">{NIV.get(n,n)}</span>' for n in s.get('niv',[]))}
        </div>
        <div style="margin-bottom:14px">
          <div style="font-size:.7rem;color:var(--text-light);margin-bottom:6px;font-weight:700;text-transform:uppercase;letter-spacing:.05em">Ambiance</div>
          {''.join(f'<span class="tag tag-amb">{AMB.get(a,a)}</span>' for a in s.get('amb',[]))}
        </div>
        {f'''<div>
          <div style="font-size:.7rem;color:var(--text-light);margin-bottom:6px;font-weight:700;text-transform:uppercase;letter-spacing:.05em">Équipements</div>
          {''.join(f'<span class="tag tag-eq">{EQ.get(e,e)}</span>' for e in s.get('equip',[]))}
        </div>''' if s.get('equip') else ''}
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
