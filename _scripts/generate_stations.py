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
        slug = slugify(sim['name'])
        photo = sim.get('photo') or 'https://images.unsplash.com/photo-1551524559-8af4e6624178?w=400&q=80'
        prix_nuit = round(sim['forfait'] * 2.4)
        cards += f"""
        <a href="{slug}.html" style="display:block;border-radius:10px;overflow:hidden;background:white;box-shadow:0 2px 10px rgba(0,0,0,.08);text-decoration:none;transition:transform .2s,box-shadow .2s" onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 6px 20px rgba(0,0,0,.12)'" onmouseout="this.style.transform='';this.style.boxShadow='0 2px 10px rgba(0,0,0,.08)'">
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
    photo = s.get('photo') or 'https://images.unsplash.com/photo-1551524559-8af4e6624178?w=1200&q=80'
    prix_nuit = round(s['forfait'] * 2.4)
    niveaux = ", ".join(NIV.get(n, n) for n in s.get('niv', []))
    pts = s.get('pts', [])
    pts_html = "\n".join(f'<li style="padding:5px 0;border-bottom:1px solid #f7efe2">{p}</li>' for p in pts)
    booking_url = f"https://www.booking.com/searchresults.fr.html?ss={s['name'].replace(' ', '+')}+ski+france&aid=SnowFinder"
    expedia_url = f"https://www.expedia.fr/Hotel-Search?destination={s['name'].replace(' ', '+')}+ski&affcid=SnowFinder"
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

    # Construire le HTML ligne par ligne pour éviter les triple-quotes
    lines = []
    lines.append("<!DOCTYPE html>")
    lines.append("<html lang=\"fr\">")
    lines.append("<head>")
    lines.append("  <meta charset=\"UTF-8\">")
    lines.append("  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">")
    lines.append(f"  <title>{s['name']} — Station de ski : pistes, enneigement, hébergements | SnowFinder</title>")
    lines.append(f"  <meta name=\"description\" content=\"{s['name']} : {s['km']} km de pistes, altitude {s['alt_min']}-{s['alt_max']}m, forfait {s['forfait']}€/jour. {s.get('desc','')[:100]}\">")
    lines.append(f"  <link rel=\"canonical\" href=\"{canonical}\">")
    lines.append(f"  <meta property=\"og:type\" content=\"website\">")
    lines.append(f"  <meta property=\"og:site_name\" content=\"SnowFinder\">")
    lines.append(f"  <meta property=\"og:url\" content=\"{canonical}\">")
    lines.append(f"  <meta property=\"og:title\" content=\"{s['name']} — Station de ski | SnowFinder\">")
    lines.append(f"  <meta property=\"og:description\" content=\"{s['km']} km · {s['alt_max']}m · {s['forfait']}€/j · {s['massif']}\">")
    lines.append(f"  <meta property=\"og:image\" content=\"{photo}\">")
    lines.append(f"  <meta property=\"og:locale\" content=\"fr_FR\">")
    lines.append(f"  <meta name=\"twitter:card\" content=\"summary_large_image\">")
    lines.append(f"  <meta name=\"twitter:title\" content=\"{s['name']} — Station de ski | SnowFinder\">")
    lines.append(f"  <meta name=\"twitter:image\" content=\"{photo}\">")
    lines.append(f"  <script type=\"application/ld+json\">{schema}</script>")
    lines.append("  <link rel=\"manifest\" href=\"/manifest.json\">")
    lines.append("  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">")
    lines.append("  <link href=\"https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">")
    lines.append("""  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    :root{--wood-pale:#f7efe2;--wood-light:#eddcbf;--wood:#c49a6c;--wood-dark:#8b5e3c;--blue-light:#e8f3fb;--blue-mid:#3a7db8;--blue-dark:#1a5a8a;--text:#2a1f14;--text-mid:#5c4a35;--text-light:#8a7060;--white:#fff;--radius:10px}
    body{font-family:"DM Sans",sans-serif;color:var(--text);background:#f4f0eb;min-height:100vh}
    a{color:inherit;text-decoration:none}
    .nav{background:var(--white);border-bottom:2px solid var(--wood-light);padding:0 20px;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.06)}
    .nav-logo{display:flex;align-items:center;gap:8px;font-family:"DM Serif Display",serif;font-size:1.1rem;color:var(--blue-dark)}
    .nav-logo img{width:36px;height:36px;border-radius:8px}
    .nav-back{display:flex;align-items:center;gap:6px;font-size:.85rem;font-weight:600;color:var(--blue-mid);background:var(--blue-light);padding:7px 14px;border-radius:20px}
    .hero{position:relative;height:300px;overflow:hidden}
    .hero img{width:100%;height:100%;object-fit:cover}
    .hero-overlay{position:absolute;inset:0;background:linear-gradient(to top,rgba(0,0,0,.82) 0%,rgba(0,0,0,.15) 55%,transparent 100%)}
    .hero-content{position:absolute;bottom:0;left:0;right:0;padding:20px}
    .hero-massif{display:inline-block;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.3);border-radius:20px;padding:3px 12px;font-size:.72rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;backdrop-filter:blur(6px)}
    h1{font-family:"DM Serif Display",serif;font-size:clamp(1.8rem,6vw,2.8rem);color:white;line-height:1.05}
    .hero-region{color:rgba(255,255,255,.8);font-size:.82rem;margin-top:3px}
    .hero-score{position:absolute;top:14px;right:14px;background:var(--wood);color:white;font-weight:700;font-size:.95rem;padding:5px 11px;border-radius:8px}
    .container{max-width:860px;margin:0 auto;padding:20px 16px 48px}
    .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    @media(max-width:600px){.grid-2{grid-template-columns:1fr}}
    .card{background:var(--white);border-radius:var(--radius);padding:16px;box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:12px}
    .card-title{font-family:"DM Serif Display",serif;font-size:.9rem;color:var(--text-light);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;padding-bottom:7px;border-bottom:2px solid var(--wood-pale)}
    .stats-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:16px}
    .stat-box{background:var(--wood-pale);border-radius:8px;padding:11px;text-align:center}
    .stat-val{font-family:"DM Serif Display",serif;font-size:1.35rem;color:var(--blue-dark)}
    .stat-lbl{font-size:.68rem;color:var(--text-light);text-transform:uppercase;letter-spacing:.04em;margin-top:2px}
    .piste-row{display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid var(--wood-pale)}
    .piste-dot{width:11px;height:11px;border-radius:50%;flex-shrink:0}
    .tag{display:inline-block;border-radius:20px;padding:3px 10px;font-size:.72rem;font-weight:600;margin:2px}
    .tag-niv{background:var(--blue-light);color:var(--blue-dark)}
    .tag-amb{background:var(--wood-pale);color:var(--wood-dark)}
    .tag-eq{background:#e6f5eb;color:#1a6a2a}
    .related-link{display:flex;align-items:center;justify-content:space-between;padding:9px 13px;background:var(--white);border-radius:8px;margin-bottom:7px;border:1.5px solid var(--wood-light);font-size:.82rem;font-weight:600;color:var(--blue-mid)}
    .breadcrumb{font-size:.76rem;color:var(--text-light);margin-bottom:14px;display:flex;align-items:center;gap:5px;flex-wrap:wrap}
    .breadcrumb a{color:var(--blue-mid);font-weight:500}
    .footer{background:var(--blue-dark);color:rgba(255,255,255,.7);text-align:center;padding:22px 20px;font-size:.78rem;margin-top:36px}
    .footer a{color:rgba(255,255,255,.9);font-weight:600}
  </style>
</head>""")
    lines.append("<body>")
    lines.append("""<nav class="nav">
  <a href="../index.html" class="nav-logo">
    <img src="../logo.png" alt="SnowFinder">
    <span>SnowFinder</span>
  </a>
  <a href="../recherche.html" class="nav-back">← Toutes les stations</a>
</nav>""")
    lines.append(f"""<div class="hero">
  <img src="{photo}" alt="{s['name']} station de ski" loading="eager">
  <div class="hero-overlay"></div>
  <div class="hero-score">{s['score']:.1f} ⭐</div>
  <div class="hero-content">
    <div class="hero-massif">⛷ {s['massif']}</div>
    <h1>{s['name']}</h1>
    <div class="hero-region">📍 {s.get('region','')}</div>
  </div>
</div>""")
    lines.append(f"""<div class="container">
  <nav class="breadcrumb">
    <a href="../index.html">Accueil</a> ›
    <a href="../recherche.html">Stations de ski</a> ›
    <a href="../recherche.html">{s['massif']}</a> ›
    <span>{s['name']}</span>
  </nav>
  <div class="stats-grid">
    <div class="stat-box"><div class="stat-val">{s['km']} km</div><div class="stat-lbl">Pistes skiables</div></div>
    <div class="stat-box"><div class="stat-val">{s['alt_max']}m</div><div class="stat-lbl">Altitude max</div></div>
    <div class="stat-box"><div class="stat-val">{s['remontees']}</div><div class="stat-lbl">Remontées</div></div>
    <div class="stat-box"><div class="stat-val">{s['forfait']}€</div><div class="stat-lbl">Forfait/jour</div></div>
  </div>
  {snow_html}
  <div class="grid-2">
    <div>
      <div class="card">
        <div class="card-title">À propos</div>
        <p style="font-size:.88rem;line-height:1.7;color:var(--text-mid)">{desc_long}</p>
        <ul style="margin-top:10px;padding-left:0;list-style:none">{pts_html}</ul>
      </div>
      <div class="card">
        <div class="card-title">Pistes</div>
        <div class="piste-row"><div class="piste-dot" style="background:#1a8a3a"></div><span style="flex:1">Vertes</span><strong>{s['pistes']['v']}</strong></div>
        <div class="piste-row"><div class="piste-dot" style="background:#1a5ab8"></div><span style="flex:1">Bleues</span><strong>{s['pistes']['b']}</strong></div>
        <div class="piste-row"><div class="piste-dot" style="background:#c0392b"></div><span style="flex:1">Rouges</span><strong>{s['pistes']['r']}</strong></div>
        <div class="piste-row" style="border:0"><div class="piste-dot" style="background:#1a1a1a"></div><span style="flex:1">Noires</span><strong>{s['pistes']['n']}</strong></div>
      </div>
      <div class="card">
        <div class="card-title">Niveaux & Ambiance</div>
        <div style="margin-bottom:8px">{' '.join(f'<span class="tag tag-niv">{NIV.get(n,n)}</span>' for n in s.get('niv',[]))}</div>
        <div>{' '.join(f'<span class="tag tag-amb">{AMB.get(a,a)}</span>' for a in s.get('amb',[]))}</div>
      </div>
    </div>
    <div>
      <div class="card">
        <div class="card-title">Hébergement & Forfaits</div>
        <div style="background:#1a3a5c;border-radius:8px;overflow:hidden;margin-bottom:8px">
          <div style="padding:10px 12px;display:flex;align-items:center;gap:8px">
            <span style="font-size:1.4rem">🏔</span>
            <div><div style="color:white;font-weight:700;font-size:.95rem">{s['name']}</div>
            <div style="color:rgba(255,255,255,.7);font-size:.72rem">Trouvez les meilleures offres</div></div>
          </div>
          <div style="display:flex;gap:5px;padding:7px 10px;background:#f7efe2;flex-wrap:wrap">
            <span style="font-size:.67rem;font-weight:600;background:rgba(42,138,58,.1);color:#1a6a2a;border-radius:20px;padding:2px 7px">✓ Annulation gratuite</span>
            <span style="font-size:.67rem;font-weight:600;background:rgba(26,90,138,.1);color:#1a3a5c;border-radius:20px;padding:2px 7px">✓ Paiement sécurisé</span>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr">
            <a href="{booking_url}" target="_blank" rel="noopener sponsored" style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:13px 8px;background:#003580;text-decoration:none;gap:2px">
              <span>🏨</span><span style="color:white;font-weight:700;font-size:.8rem">Booking.com</span>
              <span style="color:rgba(255,255,255,.7);font-size:.66rem">Voir les offres →</span>
            </a>
            <a href="{expedia_url}" target="_blank" rel="noopener sponsored" style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:13px 8px;background:#ffcc00;text-decoration:none;gap:2px;border-left:1px solid rgba(0,0,0,.08)">
              <span>✈️</span><span style="color:#003580;font-weight:700;font-size:.8rem">Expedia</span>
              <span style="color:#003580;font-size:.66rem;opacity:.7">Réserver →</span>
            </a>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">Équipements</div>
        <div>{' '.join(f'<span class="tag tag-eq">{EQ.get(e,e)}</span>' for e in s.get('equip',[]))}</div>
      </div>
    </div>
  </div>
  {similar_html}
</div>""")
    lines.append("""<footer class="footer">
  <strong>SnowFinder</strong> — Le guide complet des stations de ski françaises<br>
  <a href="../index.html">Accueil</a> · <a href="../recherche.html">Recherche</a> · <a href="../comparateur.html">Comparateur</a> · <a href="../mentions-legales.html">Mentions légales</a>
</footer>
</body>
</html>""")
    return "\n".join(lines)


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
