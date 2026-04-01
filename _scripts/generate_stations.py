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
 
GRAND_DOMAINS = {
    "Avoriaz":{"name":"Portes du Soleil","km":650,"remontees":196,"pistes":{"v":80,"b":173,"r":103,"n":44}},
    "Morzine":{"name":"Portes du Soleil","km":650,"remontees":196,"pistes":{"v":80,"b":173,"r":103,"n":44}},
    "Les Gets":{"name":"Portes du Soleil","km":650,"remontees":196,"pistes":{"v":80,"b":173,"r":103,"n":44}},
    "Châtel":{"name":"Portes du Soleil","km":650,"remontees":196,"pistes":{"v":80,"b":173,"r":103,"n":44}},
    "Courchevel":{"name":"Les 3 Vallées","km":600,"remontees":170,"pistes":{"v":55,"b":178,"r":113,"n":54}},
    "Méribel":{"name":"Les 3 Vallées","km":600,"remontees":170,"pistes":{"v":55,"b":178,"r":113,"n":54}},
    "Val Thorens":{"name":"Les 3 Vallées","km":600,"remontees":170,"pistes":{"v":55,"b":178,"r":113,"n":54}},
    "Les Menuires":{"name":"Les 3 Vallées","km":600,"remontees":170,"pistes":{"v":55,"b":178,"r":113,"n":54}},
    "Saint-Martin-de-Belleville":{"name":"Les 3 Vallées","km":600,"remontees":170,"pistes":{"v":55,"b":178,"r":113,"n":54}},
    "Val d'Isère":{"name":"Espace Killy","km":300,"remontees":91,"pistes":{"v":8,"b":41,"r":70,"n":36}},
    "Tignes":{"name":"Espace Killy","km":300,"remontees":91,"pistes":{"v":8,"b":41,"r":70,"n":36}},
    "Les Arcs":{"name":"Paradiski","km":425,"remontees":143,"pistes":{"v":30,"b":102,"r":62,"n":28}},
    "La Plagne":{"name":"Paradiski","km":425,"remontees":143,"pistes":{"v":30,"b":102,"r":62,"n":28}},
    "Peisey-Vallandry":{"name":"Paradiski","km":425,"remontees":143,"pistes":{"v":30,"b":102,"r":62,"n":28}},
    "Montchavin-Les Coches":{"name":"Paradiski","km":425,"remontees":143,"pistes":{"v":30,"b":102,"r":62,"n":28}},
    "Flaine":{"name":"Grand Massif","km":265,"remontees":88,"pistes":{"v":29,"b":111,"r":80,"n":31}},
    "Les Carroz":{"name":"Grand Massif","km":265,"remontees":88,"pistes":{"v":29,"b":111,"r":80,"n":31}},
    "Samoëns":{"name":"Grand Massif","km":265,"remontees":88,"pistes":{"v":29,"b":111,"r":80,"n":31}},
    "Morillon":{"name":"Grand Massif","km":265,"remontees":88,"pistes":{"v":29,"b":111,"r":80,"n":31}},
    "La Toussuire":{"name":"Les Sybelles","km":310,"remontees":58,"pistes":{"v":55,"b":120,"r":78,"n":31}},
    "Le Corbier":{"name":"Les Sybelles","km":310,"remontees":58,"pistes":{"v":55,"b":120,"r":78,"n":31}},
    "Saint-Sorlin-d'Arves":{"name":"Les Sybelles","km":310,"remontees":58,"pistes":{"v":55,"b":120,"r":78,"n":31}},
    "Vars":{"name":"Forêt Blanche","km":185,"remontees":51,"pistes":{"v":26,"b":66,"r":52,"n":16}},
    "Risoul":{"name":"Forêt Blanche","km":185,"remontees":51,"pistes":{"v":26,"b":66,"r":52,"n":16}},
    "Montgenèvre":{"name":"Via Lattea (F+I)","km":400,"remontees":100,"pistes":{"v":50,"b":146,"r":106,"n":53}},
    "Pra-Loup":{"name":"Espace Lumière","km":180,"remontees":53,"pistes":{"v":26,"b":80,"r":56,"n":12}},
    "Val d'Allos":{"name":"Espace Lumière","km":180,"remontees":53,"pistes":{"v":26,"b":80,"r":56,"n":12}},
    "Valloire":{"name":"Galibier-Thabor","km":160,"remontees":33,"pistes":{"v":26,"b":60,"r":54,"n":18}},
    "Valmeinier":{"name":"Galibier-Thabor","km":160,"remontees":33,"pistes":{"v":26,"b":60,"r":54,"n":18}},
    "Alpe d'Huez":{"name":"Grand Domaine","km":250,"remontees":82,"pistes":{"v":16,"b":68,"r":82,"n":22}},
    "Auris-en-Oisans":{"name":"Grand Domaine","km":250,"remontees":82,"pistes":{"v":16,"b":68,"r":82,"n":22}},
    "Serre Chevalier":{"name":"Serre Chevalier Vallée","km":250,"remontees":71,"pistes":{"v":16,"b":76,"r":58,"n":32}},
    "Grand Tourmalet":{"name":"Grand Tourmalet","km":100,"remontees":29,"pistes":{"v":25,"b":60,"r":45,"n":15}},
    "Les Saisies":{"name":"Espace Diamant","km":150,"remontees":48,"pistes":{"v":40,"b":92,"r":60,"n":16}},
}
 
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
        cards += (
            '<a href="' + slug + '.html" style="display:block;border-radius:12px;overflow:hidden;background:white;'
            'box-shadow:0 2px 12px rgba(0,0,0,.08);text-decoration:none;transition:transform .2s,box-shadow .2s" '
            'onmouseover="this.style.transform=\'translateY(-3px)\';this.style.boxShadow=\'0 8px 24px rgba(0,0,0,.14)\'" '
            'onmouseout="this.style.transform=\'\';this.style.boxShadow=\'0 2px 12px rgba(0,0,0,.08)\'">'
            '<div style="position:relative;height:100px;overflow:hidden">'
            '<img src="' + photo + '" alt="' + sim['name'] + '" style="width:100%;height:100%;object-fit:cover" loading="lazy" '
            'onerror="this.src=\'https://images.unsplash.com/photo-1551524559-8af4e6624178?w=400&q=80\'">'
            '<div style="position:absolute;inset:0;background:linear-gradient(to top,rgba(0,0,0,.65),transparent)"></div>'
            '<div style="position:absolute;bottom:7px;left:9px;color:white;font-family:\'DM Serif Display\',serif;font-size:.88rem;font-weight:400">' + sim['name'] + '</div>'
            '<div style="position:absolute;top:6px;right:6px;background:#c49a6c;color:white;font-size:.65rem;font-weight:700;padding:2px 7px;border-radius:20px">' + f"{sim['score']:.1f}" + ' ⭐</div>'
            '</div>'
            '<div style="padding:8px 10px;display:flex;justify-content:space-between;align-items:center">'
            '<span style="font-size:.75rem;color:#5c4a35;font-weight:600">' + str(sim['km']) + ' km · ' + str(sim['alt_max']) + 'm</span>'
            '<span style="font-size:.72rem;color:#3a7db8;font-weight:700">~' + str(prix_nuit) + '€/nuit</span>'
            '</div></a>'
        )
    return (
        '<div style="margin-top:28px;padding-top:20px;border-top:2px solid #f0ebe3">'
        '<div style="font-family:\'DM Serif Display\',serif;font-size:1.05rem;color:#8a7060;text-transform:uppercase;'
        'letter-spacing:.05em;margin-bottom:14px">⛷ Autres stations ' + s['massif'] + '</div>'
        '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px">' + cards + '</div>'
        '<a href="../recherche.html" style="display:block;text-align:center;margin-top:14px;padding:10px;'
        'background:#f7efe2;border-radius:10px;font-size:.82rem;font-weight:600;color:#3a7db8;border:1.5px solid #eddcbf">'
        'Voir toutes les stations ' + s['massif'] + ' →</a></div>'
    )
 
def piste_bar(count, color, label):
    return (
        '<div style="display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid #f0ebe3">'
        '<div style="display:flex;align-items:center;gap:9px">'
        '<div style="width:12px;height:12px;border-radius:50%;background:' + color + ';flex-shrink:0"></div>'
        '<span style="font-size:.85rem;color:#5c4a35">' + label + '</span>'
        '</div>'
        '<strong style="font-size:.9rem;color:#2a1f14">' + str(count) + '</strong>'
        '</div>'
    )
 
def render_page(s):
    slug = slugify(s['name'])
    canonical = 'https://snowfinder.fr/stations/' + slug + '.html'
    photo = s.get('photo') or 'https://images.unsplash.com/photo-1551524559-8af4e6624178?w=1200&q=80'
    prix_nuit = round(s['forfait'] * 2.4)
    pts = s.get('pts', [])
    booking_url = 'https://www.booking.com/searchresults.fr.html?ss=' + s['name'].replace(' ', '+') + '+ski+france&aid=SnowFinder'
    expedia_url = 'https://www.expedia.fr/Hotel-Search?destination=' + s['name'].replace(' ', '+') + '+ski&affcid=SnowFinder'
    desc_long = s.get('desc_long') or s.get('desc', '')
    gd = GRAND_DOMAINS.get(s['name'])
    similar_html = render_similar_section(s)
 
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
                "address": {"@type": "PostalAddress", "addressCountry": "FR", "addressRegion": s.get("region", "")},
                "aggregateRating": {"@type": "AggregateRating", "ratingValue": str(round(s.get("score", 4.0), 1)), "bestRating": "5", "worstRating": "1", "ratingCount": "50"},
                "amenityFeature": [
                    {"@type": "LocationFeatureSpecification", "name": "Pistes de ski", "value": str(s["km"]) + " km"},
                    {"@type": "LocationFeatureSpecification", "name": "Remontees mecaniques", "value": str(s["remontees"])},
                    {"@type": "LocationFeatureSpecification", "name": "Altitude maximale", "value": str(s["alt_max"]) + " m"},
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
            {"@type": "Offer", "name": "Forfait ski " + s["name"], "price": str(s["forfait"]), "priceCurrency": "EUR", "description": "Forfait journée adulte", "url": canonical}
        ]
    }
    schema = json.dumps(schema_obj, ensure_ascii=False)
 
    # Points forts
    pts_html = ''.join('<li style="padding:6px 0;border-bottom:1px solid #f0ebe3;font-size:.88rem;color:#4a3a2a;display:flex;align-items:center;gap:8px"><span style="color:#2a8a4a;font-weight:700">✓</span>' + p + '</li>' for p in pts)
 
    # Zone pistes station
    p = s['pistes']
    pistes_station = (
        '<div style="background:#f7efe2;border-radius:10px;padding:14px 16px;margin-bottom:10px">'
        '<div style="font-size:.72rem;font-weight:700;color:#8a7060;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">'
        '🎿 Station — ' + str(s["km"]) + ' km</div>'
        + piste_bar(p["v"], "#1a8a3a", "Vertes")
        + piste_bar(p["b"], "#1a5ab8", "Bleues")
        + piste_bar(p["r"], "#c0392b", "Rouges")
        + '<div style="display:flex;align-items:center;justify-content:space-between;padding:7px 0">'
        '<div style="display:flex;align-items:center;gap:9px">'
        '<div style="width:12px;height:12px;border-radius:50%;background:#1a1a1a;flex-shrink:0"></div>'
        '<span style="font-size:.85rem;color:#5c4a35">Noires</span></div>'
        '<strong style="font-size:.9rem;color:#2a1f14">' + str(p["n"]) + '</strong></div>'
        '</div>'
    )
 
    # Zone pistes grand domaine
    pistes_gd = ''
    if gd:
        gp = gd['pistes']
        pistes_gd = (
            '<div style="background:#e8f3fb;border-radius:10px;padding:14px 16px">'
            '<div style="font-size:.72rem;font-weight:700;color:#3a7db8;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">'
            '🏔 ' + gd["name"] + ' — ' + str(gd["km"]) + ' km</div>'
            + piste_bar(gp["v"], "#1a8a3a", "Vertes")
            + piste_bar(gp["b"], "#1a5ab8", "Bleues")
            + piste_bar(gp["r"], "#c0392b", "Rouges")
            + '<div style="display:flex;align-items:center;justify-content:space-between;padding:7px 0">'
            '<div style="display:flex;align-items:center;gap:9px">'
            '<div style="width:12px;height:12px;border-radius:50%;background:#1a1a1a;flex-shrink:0"></div>'
            '<span style="font-size:.85rem;color:#5c4a35">Noires</span></div>'
            '<strong style="font-size:.9rem;color:#2a1f14">' + str(gp["n"]) + '</strong></div>'
            '</div>'
        )
 
    # Enneigement
    snow_html = ''
    if s.get('snow'):
        snow_html = (
            '<div style="background:linear-gradient(135deg,#e8f3fb,#d0e8f8);border-radius:10px;padding:12px 16px;'
            'display:flex;align-items:center;gap:12px;margin-bottom:16px">'
            '<span style="font-size:1.6rem">❄️</span>'
            '<div><div style="font-weight:700;color:#1a5a8a;font-size:1.2rem">' + str(s["snow"]) + ' cm</div>'
            '<div style="font-size:.75rem;color:#5a8ab8;font-weight:500">Enneigement actuel</div></div>'
            '</div>'
        )
 
    # Tags niveaux et ambiances
    niv_tags = ''.join('<span style="display:inline-block;background:#e8f3fb;color:#1a5a8a;border-radius:20px;padding:4px 12px;font-size:.75rem;font-weight:600;margin:3px">' + NIV.get(n, n) + '</span>' for n in s.get('niv', []))
    amb_tags = ''.join('<span style="display:inline-block;background:#f7efe2;color:#8b5e3c;border-radius:20px;padding:4px 12px;font-size:.75rem;font-weight:600;margin:3px">' + AMB.get(a, a) + '</span>' for a in s.get('amb', []))
    eq_tags  = ''.join('<span style="display:inline-block;background:#e6f5eb;color:#1a6a2a;border-radius:20px;padding:4px 12px;font-size:.75rem;font-weight:600;margin:3px">' + EQ.get(e, e) + '</span>' for e in s.get('equip', []))
 
    html = (
        '<!DOCTYPE html>'
        '<html lang="fr">'
        '<head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>' + s['name'] + ' — Station de ski : pistes, enneigement, hébergements | SnowFinder</title>'
        '<meta name="description" content="' + s['name'] + ' : ' + str(s['km']) + ' km de pistes, altitude ' + str(s['alt_min']) + '-' + str(s['alt_max']) + 'm, forfait ' + str(s['forfait']) + '€/jour. ' + s.get('desc','')[:100] + '">'
        '<link rel="canonical" href="' + canonical + '">'
        '<meta property="og:type" content="website">'
        '<meta property="og:site_name" content="SnowFinder">'
        '<meta property="og:url" content="' + canonical + '">'
        '<meta property="og:title" content="' + s['name'] + ' — Station de ski | SnowFinder">'
        '<meta property="og:description" content="' + str(s['km']) + ' km · ' + str(s['alt_max']) + 'm · ' + str(s['forfait']) + '€/j · ' + s['massif'] + '">'
        '<meta property="og:image" content="' + photo + '">'
        '<meta property="og:locale" content="fr_FR">'
        '<meta name="twitter:card" content="summary_large_image">'
        '<meta name="twitter:title" content="' + s['name'] + ' — Station de ski | SnowFinder">'
        '<meta name="twitter:image" content="' + photo + '">'
        '<script type="application/ld+json">' + schema + '</script>'
        '<link rel="manifest" href="/manifest.json">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">'
        '<style>'
        '*{box-sizing:border-box;margin:0;padding:0}'
        ':root{--wood-pale:#f7efe2;--wood-light:#eddcbf;--wood:#c49a6c;--wood-dark:#8b5e3c;--blue-light:#e8f3fb;--blue-mid:#3a7db8;--blue-dark:#1a5a8a;--text:#2a1f14;--text-mid:#5c4a35;--text-light:#8a7060;--white:#fff;--radius:12px;--green:#1a8a3a}'
        'body{font-family:"DM Sans",sans-serif;color:var(--text);background:#f4f0eb;min-height:100vh}'
        'a{color:inherit;text-decoration:none}'
        '.nav{background:var(--white);border-bottom:2px solid var(--wood-light);padding:0 20px;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.06)}'
        '.nav-logo{display:flex;align-items:center;gap:8px;font-family:"DM Serif Display",serif;font-size:1.1rem;color:var(--blue-dark)}'
        '.nav-logo img{width:36px;height:36px;border-radius:8px}'
        '.nav-back{display:flex;align-items:center;gap:6px;font-size:.85rem;font-weight:600;color:var(--blue-mid);background:var(--blue-light);padding:7px 14px;border-radius:20px;transition:background .15s}'
        '.nav-back:hover{background:#d0e8f8}'
        '.hero{position:relative;height:320px;overflow:hidden;background:#1a3a5c}'
        '.hero img{width:100%;height:100%;object-fit:cover;display:block}'
        '.hero-overlay{position:absolute;inset:0;background:linear-gradient(to top,rgba(0,0,0,.85) 0%,rgba(0,0,0,.2) 50%,transparent 100%)}'
        '.hero-content{position:absolute;bottom:0;left:0;right:0;padding:22px 20px}'
        '.hero-massif{display:inline-block;background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.35);border-radius:20px;padding:4px 13px;font-size:.72rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.07em;margin-bottom:7px;backdrop-filter:blur(8px)}'
        'h1{font-family:"DM Serif Display",serif;font-size:clamp(2rem,7vw,3rem);color:white;line-height:1.05}'
        '.hero-region{color:rgba(255,255,255,.8);font-size:.85rem;margin-top:4px}'
        '.hero-score{position:absolute;top:16px;right:16px;background:var(--wood);color:white;font-weight:700;font-size:1rem;padding:6px 13px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.3)}'
        '.container{max-width:900px;margin:0 auto;padding:22px 16px 52px}'
        '.breadcrumb{font-size:.76rem;color:var(--text-light);margin-bottom:18px;display:flex;align-items:center;gap:5px;flex-wrap:wrap}'
        '.breadcrumb a{color:var(--blue-mid);font-weight:500}'
        '.score-bar{display:flex;align-items:center;gap:12px;background:white;border-radius:12px;padding:13px 16px;margin-bottom:16px;box-shadow:0 2px 10px rgba(0,0,0,.06)}'
        '.score-badge{background:var(--wood);color:white;font-weight:700;font-size:1.1rem;padding:6px 13px;border-radius:8px;white-space:nowrap}'
        '.desc-box{background:var(--wood-pale);border-radius:12px;padding:14px 16px;margin-bottom:16px;font-size:.88rem;color:var(--text-mid);line-height:1.7;border-left:3px solid var(--wood)}'
        '.desc-long{font-style:italic;font-size:.88rem;color:var(--text-mid);line-height:1.75;padding:0 2px;margin-bottom:16px}'
        '.stats-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:16px}'
        '@media(min-width:500px){.stats-grid{grid-template-columns:repeat(4,1fr)}}'
        '.stat-box{background:white;border-radius:10px;padding:13px 10px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.06)}'
        '.stat-val{font-family:"DM Serif Display",serif;font-size:1.4rem;color:var(--blue-dark);line-height:1}'
        '.stat-lbl{font-size:.67rem;color:var(--text-light);text-transform:uppercase;letter-spacing:.04em;margin-top:4px}'
        '.section-title{font-family:"DM Serif Display",serif;font-size:.9rem;color:var(--text-light);text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px;padding-bottom:7px;border-bottom:2px solid var(--wood-pale)}'
        '.card{background:white;border-radius:var(--radius);padding:18px;box-shadow:0 2px 12px rgba(0,0,0,.06);margin-bottom:14px}'
        '.heb-card{background:#1a3a5c;border-radius:12px;overflow:hidden;margin-bottom:14px}'
        '.heb-img{width:100%;height:130px;object-fit:cover;display:block;opacity:.7}'
        '.heb-body{padding:14px 16px;background:#1a3a5c}'
        '.heb-title{color:rgba(255,255,255,.7);font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px}'
        '.heb-offer{color:white;font-family:"DM Serif Display",serif;font-size:1.3rem;margin-bottom:8px}'
        '.heb-badges{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}'
        '.heb-badge{background:rgba(255,255,255,.15);color:rgba(255,255,255,.9);border-radius:20px;padding:3px 10px;font-size:.68rem;font-weight:600}'
        '.heb-btns{display:grid;grid-template-columns:1fr 1fr;gap:0}'
        '.btn-booking{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:14px 8px;background:#003580;text-decoration:none;gap:3px}'
        '.btn-expedia{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:14px 8px;background:#ffcc00;text-decoration:none;gap:3px;border-left:1px solid rgba(0,0,0,.08)}'
        '.footer{background:var(--blue-dark);color:rgba(255,255,255,.7);text-align:center;padding:24px 20px;font-size:.78rem;margin-top:36px}'
        '.footer a{color:rgba(255,255,255,.9);font-weight:600}'
        '.pts-list{list-style:none;padding:0}'
        '</style>'
        '</head>'
        '<body>'
        '<nav class="nav">'
        '<a href="../index.html" class="nav-logo"><img src="../logo.png" alt="SnowFinder"><span>SnowFinder</span></a>'
        '<a href="../recherche.html" class="nav-back">← Toutes les stations</a>'
        '</nav>'
        '<div class="hero">'
        '<img src="' + photo + '" alt="' + s['name'] + ' station de ski" loading="eager" onerror="this.onerror=null;this.src=\'https://images.unsplash.com/photo-1551524559-8af4e6624178?w=1200&q=80\'">'
        '<div class="hero-overlay"></div>'
        '<div class="hero-score">' + f"{s['score']:.1f}" + ' ⭐</div>'
        '<div class="hero-content">'
        '<div class="hero-massif">⛷ ' + s['massif'] + '</div>'
        '<h1>' + s['name'] + '</h1>'
        '<div class="hero-region">📍 ' + s.get('region','') + '</div>'
        '</div></div>'
        '<div class="container">'
        '<nav class="breadcrumb">'
        '<a href="../index.html">Accueil</a> › '
        '<a href="../recherche.html">Stations de ski</a> › '
        '<a href="../recherche.html">' + s['massif'] + '</a> › '
        '<span>' + s['name'] + '</span>'
        '</nav>'
        '<div class="score-bar">'
        '<div class="score-badge">' + f"{s['score']:.1f}" + ' ⭐</div>'
        '<div style="font-size:.88rem;color:var(--text-mid)">📍 ' + s.get('region','') + '</div>'
        '</div>'
        '<div class="desc-box">' + s.get('desc','') + '</div>'
        + snow_html +
        '<div class="stats-grid">'
        '<div class="stat-box"><div class="stat-val">' + str(s['alt_min']) + '–' + str(s['alt_max']) + 'm</div><div class="stat-lbl">Altitude</div></div>'
        '<div class="stat-box"><div class="stat-val">' + str(s['km']) + ' km</div><div class="stat-lbl">Pistes</div></div>'
        '<div class="stat-box"><div class="stat-val">' + str(s['remontees']) + '</div><div class="stat-lbl">Remontées</div></div>'
        '<div class="stat-box"><div class="stat-val">' + str(s['forfait']) + '€</div><div class="stat-lbl">Forfait/j HS</div></div>'
        '</div>'
        '<div class="card">'
        '<div class="section-title">À propos</div>'
        '<p class="desc-long">' + desc_long + '</p>'
        + ('<ul class="pts-list">' + pts_html + '</ul>' if pts_html else '') +
        '</div>'
        '<div class="card">'
        '<div class="section-title">Pistes</div>'
        + pistes_station + pistes_gd +
        '</div>'
        '<div class="heb-card">'
        '<div class="heb-body">'
        '<div class="heb-title">Où dormir à ' + s['name'] + ' ?</div>'
        '<div class="heb-offer">Chalets &amp; appartements<br><span style="color:#ffcc00;font-family:\'DM Sans\',sans-serif;font-weight:700">dès ' + str(prix_nuit) + '€</span> <span style="font-size:.75rem;color:rgba(255,255,255,.7);font-family:\'DM Sans\',sans-serif">/ nuit · annulation gratuite</span></div>'
        '<div class="heb-badges"><span class="heb-badge">✓ Paiement sécurisé</span><span class="heb-badge">⭐ Meilleur prix garanti</span></div>'
        '<div class="heb-btns">'
        '<a href="' + booking_url + '" target="_blank" rel="noopener sponsored" class="btn-booking">'
        '<span>🏨</span><span style="color:white;font-weight:700;font-size:.82rem">Booking.com</span>'
        '<span style="color:rgba(255,255,255,.7);font-size:.67rem">Voir les offres →</span></a>'
        '<a href="' + expedia_url + '" target="_blank" rel="noopener sponsored" class="btn-expedia">'
        '<span>✈️</span><span style="color:#003580;font-weight:700;font-size:.82rem">Expedia</span>'
        '<span style="color:#003580;font-size:.67rem;opacity:.7">Réserver →</span></a>'
        '</div></div></div>'
        '<div class="card">'
        '<div class="section-title">Niveaux &amp; Ambiance</div>'
        '<div style="margin-bottom:10px">' + niv_tags + '</div>'
        '<div>' + amb_tags + '</div>'
        '</div>'
        + ('<div class="card"><div class="section-title">Équipements</div><div>' + eq_tags + '</div></div>' if eq_tags else '') +
        similar_html +
        '</div>'
        '<footer class="footer">'
        '<strong>SnowFinder</strong> — Le guide complet des stations de ski françaises<br>'
        '<a href="../index.html">Accueil</a> · <a href="../recherche.html">Recherche</a> · '
        '<a href="../comparateur.html">Comparateur</a> · <a href="../mentions-legales.html">Mentions légales</a>'
        '</footer>'
        '</body></html>'
    )
    return html
 
 
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
