#!/usr/bin/env python3
"""
generate_comparatifs.py — SnowFinder
─────────────────────────────────────
Génère 5 pages de comparaison entre stations populaires, plus un snippet
HTML à coller dans index.html.

Utilisation :
    python3 _scripts/generate_comparatifs.py

Sorties :
    /comparatifs/{slug}.html         (5 pages)
    /comparatifs/index.html          (page d'accueil des comparatifs)
    /_scripts/_index_snippet.html    (à copier-coller dans index.html)
"""

from __future__ import annotations
import json
import re
import urllib.parse
from datetime import date
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://snowfinder.fr"
REPO_ROOT = Path(__file__).resolve().parent.parent
RECHERCHE_HTML = REPO_ROOT / "recherche.html"
COMPARATIFS_DIR = REPO_ROOT / "comparatifs"
SNIPPET_OUT = REPO_ROOT / "_scripts" / "_index_snippet.html"

# Slug canonique partagé avec generate_sitemap.py
def slugify(name: str) -> str:
    import unicodedata
    s = name.lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = re.sub(r"['\u2019\s]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def load_stations() -> dict:
    """Charge IA_STATIONS depuis recherche.html, indexé par nom."""
    content = RECHERCHE_HTML.read_text(encoding="utf-8")
    m = re.search(r"const\s+IA_STATIONS\s*=\s*(\[.*?\]);", content, re.DOTALL)
    if not m:
        raise SystemExit("❌ IA_STATIONS introuvable dans recherche.html")
    arr = json.loads(m.group(1))
    return {s["name"]: s for s in arr}


# ── Données des comparatifs ──────────────────────────────────────────────────
# Chaque comparatif définit :
#  - a, b           : noms exacts (doivent matcher IA_STATIONS)
#  - img_a, img_b   : noms des fichiers photos dans /img/ (minuscules, sans tiret)
#  - teaser         : 1-2 phrases qui plantent le décor
#  - winner         : dict {critère: nom_station_qui_gagne}
#  - verdict        : conseil final (≈4 lignes)
#  - faq            : 4 paires (question, réponse)

COMPARAISONS = [
    {
        "a": "Val Thorens",
        "b": "Les Menuires",
        "img_a": "valthorens1",
        "img_b": "lesmenuires1",
        "teaser": (
            "Deux portes d'entrée des 3 Vallées, deux ambiances radicalement différentes. "
            "Val Thorens vous offre la plus haute altitude d'Europe et une vie nocturne légendaire. "
            "Les Menuires joue la carte du budget malin et de l'esprit familial."
        ),
        "winner": {
            "Famille avec jeunes enfants": "Les Menuires",
            "Budget serré": "Les Menuires",
            "Neige garantie toute la saison": "Val Thorens",
            "Ambiance festive & après-ski": "Val Thorens",
            "Ski freeride et hors-piste": "Val Thorens",
            "Village authentique": "Les Menuires (Saint-Martin proche)",
            "Skieurs débutants": "Les Menuires",
            "Glacier en avril-mai": "Val Thorens",
        },
        "verdict": (
            "Si la priorité est l'enneigement à toute épreuve et une ambiance qui ne dort jamais, "
            "<strong>Val Thorens</strong> reste imbattable. Mais pour une semaine en famille "
            "avec des enfants à équiper ou un budget contraint, <strong>Les Menuires</strong> "
            "offre exactement le même domaine 3 Vallées à 25-30% moins cher. "
            "Astuce : loger aux Menuires et passer une journée à Val Thorens via la liaison."
        ),
        "faq": [
            ("Val Thorens ou Les Menuires : laquelle est la moins chère ?",
             "Les Menuires reste 25 à 35% moins chère que Val Thorens sur l'hébergement, avec des forfaits comparables (le forfait 3 Vallées étant commun). En janvier hors vacances scolaires, on trouve facilement des appartements à 350-450 € la semaine aux Menuires contre 600 € minimum à Val Thorens."),
            ("Peut-on skier dans tout le domaine des 3 Vallées depuis les deux stations ?",
             "Oui, avec un forfait 3 Vallées (600 km, 170 remontées), depuis Val Thorens comme depuis Les Menuires vous avez accès à Courchevel, Méribel, La Tania et toutes les stations du domaine. La liaison Menuires-Val Thorens prend une trentaine de minutes à ski."),
            ("Val Thorens est-elle vraiment la plus haute station d'Europe ?",
             "Oui, Val Thorens culmine à 2300 m avec un domaine montant jusqu'à 3230 m via le glacier de la Cime Caron. C'est ce qui lui garantit un enneigement fiable de fin novembre à début mai, là où Les Menuires (1800 m) reste également bien enneigée mais sur une fenêtre plus classique."),
            ("Les Menuires est-elle adaptée aux enfants débutants ?",
             "Très bien adaptée : la station dispose du label « Espaces ludiques », d'un grand front de neige doux côté La Croisette, de plusieurs zones débutants ainsi que de garderies. Val Thorens accueille aussi les familles mais l'altitude (vents, froid, dénivelé immédiat) la rend moins évidente pour les tout-petits."),
        ],
    },
    {
        "a": "Avoriaz",
        "b": "Morzine",
        "img_a": "avoriaz1",
        "img_b": "morzine1",
        "teaser": (
            "Deux poids lourds des Portes du Soleil, deux philosophies opposées. "
            "Avoriaz, station piétonne à 1800 m d'altitude, sort tout droit des années 60 et garantit la neige. "
            "Morzine, village savoyard authentique à 1000 m, séduit par son charme et son ambiance toute l'année."
        ),
        "winner": {
            "Ski aux pieds": "Avoriaz",
            "Charme d'un village authentique": "Morzine",
            "Neige garantie": "Avoriaz",
            "Sortir au restaurant le soir": "Morzine",
            "Famille avec enfants en bas âge": "Avoriaz (piétonne)",
            "Ski freestyle & snowparks": "Avoriaz",
            "Budget hébergement": "Morzine",
            "Accessibilité depuis Genève": "Morzine (1h)",
        },
        "verdict": (
            "<strong>Avoriaz</strong> gagne haut la main si vos critères sont : ski aux pieds, "
            "enneigement garanti, snowpark, et zéro voiture autour des enfants. "
            "<strong>Morzine</strong> l'emporte si vous voulez retrouver l'âme d'un vrai village savoyard, "
            "varier les soirées, et profiter d'un domaine identique (les 650 km des Portes du Soleil) "
            "à un tarif d'hébergement plus doux."
        ),
        "faq": [
            ("Morzine et Avoriaz partagent-elles le même domaine skiable ?",
             "Oui. Les deux stations donnent accès aux 650 km des Portes du Soleil, le domaine franco-suisse qui relie 12 stations dont Châtel, Les Gets, Champéry et Champoussin. Depuis Morzine, la télécabine du Pléney ou celle d'Avoriaz vous amènent au cœur du domaine en quelques minutes."),
            ("Avoriaz est-elle vraiment 100% piétonne ?",
             "Oui, totalement. Les voitures restent au parking en entrée de station, les déplacements se font à pied, en luge, en traîneau à chevaux ou en navette. C'est un atout majeur pour les familles avec enfants en bas âge — pas de risque de circulation, et tous les hébergements sont à skis aux pieds."),
            ("Quelle station choisir si je ne suis pas skieur tous les jours ?",
             "Morzine sans hésiter. Le village vit toute l'année, propose de nombreux restaurants, des balades autour du lac de Montriond, un cinéma, un palais des sports avec patinoire et piscine. Avoriaz, plus minérale et tournée 100% ski, est moins agréable pour les non-skieurs."),
            ("Avoriaz est-elle adaptée aux débutants ?",
             "Oui, très bien. La station dispose d'un grand espace débutants au cœur de la station et de pistes vertes/bleues parfaitement adaptées sur le plateau d'Avoriaz. Les écoles ESF et internationale sont reconnues. Morzine fait aussi très bien le job côté débutants avec le Pléney."),
        ],
    },
    {
        "a": "Val d'Isère",
        "b": "Tignes",
        "img_a": "valdisere1",
        "img_b": "tignes1",
        "teaser": (
            "Le duo mythique de l'Espace Killy partage 300 km de pistes mais cultive deux identités farouches. "
            "Val d'Isère, village historique chic au cachet préservé. Tignes, station d'altitude moderne, "
            "glacier ouvert presque toute l'année et ambiance plus jeune."
        ),
        "winner": {
            "Charme et architecture": "Val d'Isère",
            "Enneigement record (glacier)": "Tignes",
            "Restaurants gastronomiques": "Val d'Isère",
            "Snowpark de référence mondiale": "Tignes",
            "Famille": "Val d'Isère",
            "Budget hébergement": "Tignes",
            "Ski d'été": "Tignes (Grande Motte)",
            "Freeride légendaire": "Val d'Isère (Face de Bellevarde)",
        },
        "verdict": (
            "<strong>Val d'Isère</strong> est le choix évident si vous cherchez une expérience haut "
            "de gamme : village vivant, gastronomie, freeride mythique, ambiance « grande station historique ». "
            "<strong>Tignes</strong> séduira ceux qui veulent skier le plus longtemps possible "
            "(glacier ouvert d'octobre à mai), accéder à un snowpark de classe mondiale, "
            "ou simplement payer moins cher leur hébergement pour le même domaine."
        ),
        "faq": [
            ("Val d'Isère et Tignes partagent-elles le même forfait ?",
             "Oui, le forfait Espace Killy donne accès aux 300 km de pistes communes aux deux stations, incluant le glacier de la Grande Motte et le mythique Pisaillas. Il est en revanche possible de prendre un forfait limité à une seule des deux stations si vous restez sur place."),
            ("Quelle station a le meilleur enneigement ?",
             "Les deux affichent un enneigement très fiable grâce à l'altitude (Val d'Isère 1850 m, Tignes 1550-2100 m). Tignes a un avantage sur la saison étendue : le glacier de la Grande Motte permet de skier d'octobre à mai. Val d'Isère ferme classiquement début mai."),
            ("Tignes est-elle vraiment moins chic que Val d'Isère ?",
             "Architecturalement oui — Tignes a été construite dans les années 60-70 en bord de lac avec un look station d'altitude assumé. Val d'Isère a gardé son centre-village historique avec église baroque et chalets. Côté hôtellerie haut de gamme, les deux ont leurs palaces, mais Val d'Isère concentre plus de tables étoilées."),
            ("Pour un freestyleur, laquelle choisir ?",
             "Tignes sans débat. Le snowpark de Tignes (Val Claret) est régulièrement classé parmi les meilleurs au monde, avec plusieurs lignes adaptées à tous les niveaux et un airbag. Val d'Isère a un snowpark correct mais c'est son terrain freeride (off-piste, couloirs) qui fait sa réputation."),
        ],
    },
    {
        "a": "La Plagne",
        "b": "Les Arcs",
        "img_a": "laplagne1",
        "img_b": "lesarcs1",
        "teaser": (
            "Les deux mastodontes de Paradiski (425 km) sont reliés par le Vanoise Express, "
            "mais incarnent deux conceptions très différentes du ski. "
            "La Plagne, archétype de la station 100% familiale. Les Arcs, plus sportive et "
            "architecturalement audacieuse, du village d'Arc 1950 aux pistes mythiques."
        ),
        "winner": {
            "Famille avec jeunes enfants": "La Plagne",
            "Skieurs intermédiaires / confirmés": "Les Arcs",
            "Variété du domaine en intra-station": "Les Arcs",
            "Architecture village (Arc 1950)": "Les Arcs",
            "Animation enfants": "La Plagne",
            "Bobsleigh olympique": "La Plagne",
            "Vue sur le Mont-Blanc": "Les Arcs",
            "Hors-piste": "Les Arcs (Aiguille Rouge)",
        },
        "verdict": (
            "<strong>La Plagne</strong> est le choix le plus sûr pour une famille avec enfants : "
            "domaine très progressif, garderies omniprésentes, hébergement « ski aux pieds » dans "
            "presque tous les villages, et activités annexes (bob, luge). "
            "<strong>Les Arcs</strong> conviendra mieux à des skieurs déjà autonomes qui cherchent "
            "des pistes variées et techniques, et apprécient le cachet d'Arc 1950."
        ),
        "faq": [
            ("La Plagne et Les Arcs sont-elles reliées à ski ?",
             "Oui, via le Vanoise Express, télécabine impressionnante (1800 m de portée) qui relie les deux domaines en 4 minutes. L'ensemble forme Paradiski, 3e plus grand domaine skiable du monde avec 425 km de pistes. Le forfait Paradiski couvre l'ensemble."),
            ("Quelle station choisir pour une première semaine de ski ?",
             "La Plagne, sans hésiter. Plagne Centre ou Belle Plagne sont conçues pour les débutants : front de neige adapté, tapis roulants, écoles ESF nombreuses. Les Arcs proposent aussi des espaces débutants mais le relief général est plus marqué."),
            ("Arc 1950 vaut-elle le détour ?",
             "Oui, c'est une réussite architecturale rare : station piétonne récente conçue dans un style village savoyard contemporain, sans voitures dans les rues, avec une vraie âme. C'est l'argument fort des Arcs face aux stations cubes des années 70."),
            ("Quel est le meilleur ski hors-piste, La Plagne ou Les Arcs ?",
             "Les Arcs prennent l'avantage avec l'Aiguille Rouge (3226 m) et ses descentes vers Villaroger ou Le Pré qui offrent un dénivelé impressionnant. Le hors-piste y est plus engagé. La Plagne propose des itinéraires plus accessibles côté Bellecôte et Roche de Mio."),
        ],
    },
    {
        "a": "Alpe d'Huez",
        "b": "Les Deux Alpes",
        "img_a": "alpedhuez1",
        "img_b": "lesdeuxalpes1",
        "teaser": (
            "Les deux stars de l'Oisans, à seulement 30 km à vol d'oiseau, s'opposent presque en tout. "
            "L'Alpe d'Huez mise sur le soleil (300 jours/an), la longue piste noire Sarenne et "
            "une ambiance familiale. Les Deux Alpes joue le glacier, le snowpark et l'after-ski endiablé."
        ),
        "winner": {
            "Soleil et ensoleillement": "Alpe d'Huez",
            "Ski d'été": "Les Deux Alpes (glacier)",
            "Famille avec enfants": "Alpe d'Huez",
            "Snowpark & freestyle": "Les Deux Alpes",
            "Ambiance soirée jeune": "Les Deux Alpes",
            "Longue piste noire (Sarenne 16 km)": "Alpe d'Huez",
            "Vue à 360°": "Les Deux Alpes (Dôme de la Lauze)",
            "Domaine débutant à l'arrivée": "Alpe d'Huez",
        },
        "verdict": (
            "<strong>L'Alpe d'Huez</strong> est l'option famille équilibrée : soleil garanti, "
            "domaine large et progressif, label Famille Plus, plus la mythique Sarenne pour les "
            "skieurs aguerris. <strong>Les Deux Alpes</strong> attirera les freestyleurs, les "
            "amateurs de ski sur glacier et les groupes d'amis qui veulent enchaîner les soirées. "
            "Astuce : pas besoin de choisir si vous y allez en été — seule Les Deux Alpes a son glacier ouvert."
        ),
        "faq": [
            ("Peut-on skier entre l'Alpe d'Huez et Les Deux Alpes ?",
             "Une liaison à skis via le col du Lac Blanc existe mais elle n'est plus opérationnelle de façon fiable depuis plusieurs années. Concrètement, on choisit l'une ou l'autre. Une navette routière permet de passer de l'une à l'autre en 1h-1h30."),
            ("Quelle station a le meilleur snowpark ?",
             "Les Deux Alpes, c'est même l'une de ses signatures. Le snowpark, perché sur le glacier, fonctionne en hiver comme en été et accueille régulièrement les pros mondiaux. L'Alpe d'Huez a un snowpark correct mais sans la même réputation."),
            ("La piste de la Sarenne est-elle vraiment la plus longue noire d'Europe ?",
             "Oui, 16 km depuis le Pic Blanc (3330 m) jusqu'à Sarenne, soit 2 000 m de dénivelé. Attention, malgré son label « noire », la majorité du parcours est rouge — seul le départ et quelques sections sont vraiment exigeants. Accessible à un bon skieur."),
            ("Peut-on skier sur le glacier des Deux Alpes en été ?",
             "Oui, c'est le plus grand glacier skiable d'Europe accessible l'été (de mi-juin à fin août en général). Idéal pour les amateurs de ski estival, les stages de freestyle et les équipes nationales qui viennent s'entraîner. L'Alpe d'Huez ferme son glacier de Sarenne en avril."),
        ],
    },
]


# ── Template HTML d'une page de comparaison ──────────────────────────────────

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{a} vs {b} : quelle station choisir ? — SnowFinder</title>
<meta name="description" content="{a} ou {b} ? Comparatif complet : enneigement, prix, ambiance, domaine skiable. Notre avis pour vous aider à choisir la station idéale.">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{a} vs {b} : le comparatif complet">
<meta property="og:description" content="Quelle station choisir entre {a} et {b} ? Le guide SnowFinder.">
<meta property="og:image" content="{BASE_URL}/img/{img_a}.jpg">
<meta property="og:type" content="article">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Serif+Display&display=swap" rel="stylesheet">

<style>
:root {{
  --bg:#faf6f0;
  --wood-dark:#8b5e3c;
  --wood:#a87547;
  --wood-light:#eddcbf;
  --wood-pale:#f7efe2;
  --text:#2a1f14;
  --text-mid:#5c4a35;
  --text-light:#8a7060;
  --border:#e8d8c4;
  --blue-dark:#1a5a8a;
  --blue:#5b9fd4;
  --shadow:0 1px 4px rgba(0,0,0,.08);
  --shadow-md:0 6px 20px rgba(0,0,0,.12);
  --radius:14px;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--bg); color:var(--text);
  font-family:'DM Sans',-apple-system,sans-serif; line-height:1.6;
}}
.nav {{
  background:#fff; border-bottom:1px solid var(--border); padding:14px 20px;
  display:flex; align-items:center; gap:18px; position:sticky; top:0; z-index:10;
}}
.nav a.brand {{ font-family:"DM Serif Display",serif; font-size:1.4rem; color:var(--text); text-decoration:none; }}
.nav .navlinks {{ display:flex; gap:18px; margin-left:auto; }}
.nav .navlinks a {{ color:var(--text-mid); text-decoration:none; font-size:.95rem; }}
.nav .navlinks a:hover {{ color:var(--wood-dark); }}

.page {{ max-width:1100px; margin:0 auto; padding:36px 24px 80px; }}
.crumbs {{ font-size:.85rem; color:var(--text-light); margin-bottom:14px; }}
.crumbs a {{ color:var(--text-light); text-decoration:none; }}
.crumbs a:hover {{ color:var(--wood-dark); }}

h1 {{
  font-family:"DM Serif Display",serif; font-size:2.4rem; line-height:1.15;
  margin:0 0 12px; color:var(--text);
}}
.subtitle {{ font-size:1.05rem; color:var(--text-mid); margin-bottom:32px; }}

.hero-pair {{
  display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:0 0 32px;
}}
.hero-card {{
  position:relative; border-radius:var(--radius); overflow:hidden; box-shadow:var(--shadow);
  background:#fff; aspect-ratio:16/10;
}}
.hero-card img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.hero-card .tag {{
  position:absolute; left:14px; top:14px; background:rgba(255,255,255,.92);
  padding:6px 12px; border-radius:8px; font-weight:700; font-size:.95rem;
  color:var(--text); box-shadow:var(--shadow);
}}
@media (max-width:700px) {{
  .hero-pair {{ grid-template-columns:1fr; }}
  h1 {{ font-size:1.7rem; }}
  .page {{ padding:24px 16px 60px; }}
}}

.teaser {{
  background:var(--wood-pale); border-left:4px solid var(--wood-dark);
  padding:18px 22px; border-radius:0 var(--radius) var(--radius) 0;
  margin:0 0 36px; font-size:1.02rem;
}}

h2 {{
  font-family:"DM Serif Display",serif; font-size:1.7rem;
  margin:48px 0 18px; color:var(--text); border-bottom:1px solid var(--border); padding-bottom:10px;
}}

.specs {{
  display:grid; grid-template-columns:1fr 1fr; gap:14px;
}}
.spec-card {{
  background:#fff; border:1px solid var(--border); border-radius:var(--radius);
  padding:22px; box-shadow:var(--shadow);
}}
.spec-card h3 {{ margin:0 0 14px; font-family:"DM Serif Display",serif; font-size:1.3rem; color:var(--wood-dark); }}
.spec-card .row {{ display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px dotted var(--border); font-size:.95rem; }}
.spec-card .row:last-child {{ border-bottom:none; }}
.spec-card .row span:first-child {{ color:var(--text-light); }}
.spec-card .row span:last-child {{ font-weight:600; color:var(--text); }}
@media (max-width:700px) {{ .specs {{ grid-template-columns:1fr; }} }}

.winner-table {{
  background:#fff; border:1px solid var(--border); border-radius:var(--radius);
  overflow:hidden; box-shadow:var(--shadow);
}}
.winner-row {{
  display:grid; grid-template-columns:1fr 1.2fr; padding:14px 20px;
  border-bottom:1px solid var(--border); align-items:center; gap:12px;
}}
.winner-row:last-child {{ border-bottom:none; }}
.winner-row:nth-child(even) {{ background:var(--wood-pale); }}
.winner-criterion {{ font-weight:500; color:var(--text-mid); font-size:.95rem; }}
.winner-pick {{ font-weight:700; color:var(--wood-dark); font-size:.95rem; }}
.winner-pick::before {{ content:"🏆 "; }}

.verdict {{
  background:linear-gradient(135deg,#fff 0%,var(--wood-pale) 100%);
  border:2px solid var(--wood-light); border-radius:var(--radius);
  padding:28px 30px; box-shadow:var(--shadow-md); font-size:1.05rem; margin:30px 0;
}}
.verdict h2 {{ margin-top:0; border:none; padding-bottom:0; color:var(--wood-dark); }}

.faq-item {{
  background:#fff; border:1px solid var(--border); border-radius:var(--radius);
  margin-bottom:12px; padding:18px 22px; box-shadow:var(--shadow);
}}
.faq-item h3 {{ margin:0 0 8px; font-size:1.05rem; color:var(--text); }}
.faq-item p {{ margin:0; color:var(--text-mid); }}

.book-cta {{
  background:#fff; border:1px solid var(--border); border-radius:var(--radius);
  padding:24px; box-shadow:var(--shadow-md); margin:40px 0 0;
}}
.book-cta h2 {{ margin-top:0; border:none; padding-bottom:0; text-align:center; }}
.book-cta p {{ text-align:center; color:var(--text-mid); margin:0 0 22px; }}
.book-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
.book-station h3 {{
  margin:0 0 12px; color:var(--wood-dark); font-family:"DM Serif Display",serif;
  font-size:1.25rem; text-align:center;
}}
.book-stack {{
  border-radius:14px; overflow:hidden;
  box-shadow:0 6px 20px rgba(13,34,64,.14); margin-bottom:10px;
}}
.book-card {{
  display:block; text-decoration:none; overflow:hidden;
  position:relative; transition:transform .15s;
}}
.book-card + .book-card {{ border-top:2px solid white; }}
.book-card .img-wrap {{ position:relative; overflow:hidden; height:120px; }}
.book-card img {{
  width:100%; height:100%; object-fit:cover; display:block;
  transition:transform .5s ease;
}}
.book-card:hover img {{ transform:scale(1.05); }}
.book-card .overlay {{
  position:absolute; inset:0; display:flex; align-items:center;
  padding:0 18px; gap:12px;
}}
.book-card .icon {{
  font-size:1.7rem; filter:drop-shadow(0 2px 6px rgba(0,0,0,.5));
}}
.book-card .text {{ flex:1; }}
.book-card .title {{
  color:white; font-weight:800; font-size:.95rem;
  text-shadow:0 1px 5px rgba(0,0,0,.6);
}}
.book-card .sub {{
  color:rgba(255,255,255,.82); font-size:.72rem; margin-top:2px;
}}
.book-card .btn-pill {{
  background:white; color:#003d96; font-size:.78rem; font-weight:800;
  padding:7px 14px; border-radius:20px; white-space:nowrap;
  box-shadow:0 3px 10px rgba(0,0,0,.25);
}}
.book-card.expedia .btn-pill {{ background:#ffcc00; color:#1a2060; }}
.book-card.booking .overlay {{
  background:linear-gradient(to right,rgba(0,35,110,.78) 0%,rgba(0,35,110,.38) 55%,transparent 100%);
}}
.book-card.expedia .overlay {{
  background:linear-gradient(to right,rgba(140,95,0,.8) 0%,rgba(140,95,0,.38) 55%,transparent 100%);
}}
.book-disclaimer {{
  text-align:center; font-size:.62rem; color:var(--text-light); margin-top:6px;
}}
.detail-link {{
  display:block; text-align:center; margin-top:14px; font-size:.88rem;
  color:var(--blue-dark); text-decoration:none; font-weight:600;
}}
.detail-link:hover {{ text-decoration:underline; }}
@media (max-width:700px) {{ .book-grid {{ grid-template-columns:1fr; }} }}

footer {{
  text-align:center; padding:30px 20px; color:var(--text-light); font-size:.85rem;
  border-top:1px solid var(--border); margin-top:40px;
}}
footer a {{ color:var(--text-light); }}
</style>

<script type="application/ld+json">
{json_ld}
</script>
</head>
<body>

<nav class="nav">
  <a href="/" class="brand">SnowFinder</a>
  <div class="navlinks">
    <a href="/recherche.html">Stations</a>
    <a href="/comparatifs/">Comparatifs</a>
    <a href="/tinder.html">Découvrir</a>
  </div>
</nav>

<main class="page">

<div class="crumbs">
  <a href="/">Accueil</a> · <a href="/comparatifs/">Comparatifs</a> · {a} vs {b}
</div>

<h1>{a} vs {b} : quelle station choisir ?</h1>
<div class="subtitle">Comparatif complet : domaine, enneigement, ambiance, budget. Notre verdict pour vous aider à trancher.</div>

<div class="hero-pair">
  <div class="hero-card">
    <img src="/img/{img_a}.jpg" alt="{a}" loading="eager">
    <div class="tag">{a}</div>
  </div>
  <div class="hero-card">
    <img src="/img/{img_b}.jpg" alt="{b}" loading="eager">
    <div class="tag">{b}</div>
  </div>
</div>

<div class="teaser">{teaser}</div>

<h2>📊 Les chiffres face à face</h2>
<div class="specs">
  <div class="spec-card">
    <h3>{a}</h3>
    {spec_a}
  </div>
  <div class="spec-card">
    <h3>{b}</h3>
    {spec_b}
  </div>
</div>

<h2>🏆 Quel critère pour quelle station ?</h2>
<div class="winner-table">
{winner_rows}
</div>

<div class="verdict">
  <h2>💡 Notre verdict</h2>
  <p>{verdict}</p>
</div>

<h2>❓ Questions fréquentes</h2>
{faq_html}

<div class="book-cta">
  <h2>🏨 Réserver votre séjour</h2>
  <p>Comparez les hébergements sur Booking et Expedia, ou découvrez la fiche détaillée de chaque station.</p>
  <div class="book-grid">
    <div>
      <h3>{a}</h3>
      <div class="book-stack">
        <a href="{booking_a}" target="_blank" rel="noopener sponsored" class="book-card booking">
          <div class="img-wrap">
            <img src="/img/chalet-booking.jpg" alt="Réserver sur Booking" onerror="this.src='https://images.unsplash.com/photo-1502784444187-359ac186c5bb?w=600&q=80'">
            <div class="overlay">
              <span class="icon">🏨</span>
              <div class="text">
                <div class="title">Réserver sur Booking.com</div>
                <div class="sub">Hôtels · Chalets · Appartements</div>
              </div>
              <div class="btn-pill">Voir les offres →</div>
            </div>
          </div>
        </a>
        <a href="{expedia_a}" target="_blank" rel="noopener sponsored" class="book-card expedia">
          <div class="img-wrap">
            <img src="/img/chalet-expedia.jpg" alt="Réserver sur Expedia" onerror="this.src='https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=600&q=80'">
            <div class="overlay">
              <span class="icon">✈️</span>
              <div class="text">
                <div class="title">Vol + Hôtel sur Expedia</div>
                <div class="sub">Packs ski · Économisez jusqu'à 30%</div>
              </div>
              <div class="btn-pill">Réserver →</div>
            </div>
          </div>
        </a>
      </div>
      <a href="/stations/{slug_a}.html" class="detail-link">→ Fiche complète de {a}</a>
    </div>
    <div>
      <h3>{b}</h3>
      <div class="book-stack">
        <a href="{booking_b}" target="_blank" rel="noopener sponsored" class="book-card booking">
          <div class="img-wrap">
            <img src="/img/chalet-booking.jpg" alt="Réserver sur Booking" onerror="this.src='https://images.unsplash.com/photo-1502784444187-359ac186c5bb?w=600&q=80'">
            <div class="overlay">
              <span class="icon">🏨</span>
              <div class="text">
                <div class="title">Réserver sur Booking.com</div>
                <div class="sub">Hôtels · Chalets · Appartements</div>
              </div>
              <div class="btn-pill">Voir les offres →</div>
            </div>
          </div>
        </a>
        <a href="{expedia_b}" target="_blank" rel="noopener sponsored" class="book-card expedia">
          <div class="img-wrap">
            <img src="/img/chalet-expedia.jpg" alt="Réserver sur Expedia" onerror="this.src='https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=600&q=80'">
            <div class="overlay">
              <span class="icon">✈️</span>
              <div class="text">
                <div class="title">Vol + Hôtel sur Expedia</div>
                <div class="sub">Packs ski · Économisez jusqu'à 30%</div>
              </div>
              <div class="btn-pill">Réserver →</div>
            </div>
          </div>
        </a>
      </div>
      <a href="/stations/{slug_b}.html" class="detail-link">→ Fiche complète de {b}</a>
    </div>
  </div>
  <div class="book-disclaimer">Liens affiliés — prix identiques, aucune commission prélevée sur vous</div>
</div>

</main>

<footer>
  © 2026 SnowFinder &nbsp;·&nbsp; <a href="/mentions-legales.html">Mentions légales</a> &nbsp;·&nbsp; <a href="/">Accueil</a>
</footer>

</body>
</html>
"""


# ── Construction des URL d'affiliation (format identique au site) ────────────

def booking_url(station_name: str) -> str:
    ss = station_name.lower().replace("'", "").replace(" ", "+") + "+france"
    return (f"https://www.booking.com/searchresults.fr.html"
            f"?ss={ss}&aid=SnowFinder&nflt=review_score%3D80")

def expedia_url(station_name: str, slug: str) -> str:
    """Wraps Expedia URL in CJ deep link for affiliate tracking (same format as index.html)."""
    city = station_name.replace("'", "").replace(" ", "%20")
    target = (f"https://www.expedia.fr/go/hotel/search/Destination/"
              f"?CityName={city}&City={city}&SortBy=distance&NumRoom=1&NumAdult1=1")
    encoded = urllib.parse.quote(target, safe="")
    return (f"https://www.jdoqocy.com/click-101709262-13904689"
            f"?sid=comparatif-{slug}&url={encoded}")


# ── Rendu d'une page ─────────────────────────────────────────────────────────

def render_spec(station: dict) -> str:
    p = station["pistes"]
    return "\n    ".join([
        f'<div class="row"><span>Altitude</span><span>{station["alt_min"]} – {station["alt_max"]} m</span></div>',
        f'<div class="row"><span>Domaine skiable</span><span>{station["km"]} km</span></div>',
        f'<div class="row"><span>Remontées</span><span>{station["remontees"]}</span></div>',
        f'<div class="row"><span>Pistes (V/B/R/N)</span><span>{p["v"]}/{p["b"]}/{p["r"]}/{p["n"]}</span></div>',
        f'<div class="row"><span>Forfait journée</span><span>{station["forfait"]} €</span></div>',
        f'<div class="row"><span>Note SnowFinder</span><span>{station["score"]} / 5</span></div>',
        f'<div class="row"><span>Région</span><span>{station["region"]}</span></div>',
    ])


def render_winners(winner_dict: dict) -> str:
    return "\n".join(
        f'<div class="winner-row"><div class="winner-criterion">{crit}</div>'
        f'<div class="winner-pick">{pick}</div></div>'
        for crit, pick in winner_dict.items()
    )


def render_faq(faq_list: list) -> tuple[str, list]:
    """Retourne (html, json_ld_entries)."""
    html = "\n".join(
        f'<div class="faq-item"><h3>{q}</h3><p>{a}</p></div>'
        for q, a in faq_list
    )
    json_entries = [
        {"@type": "Question", "name": q,
         "acceptedAnswer": {"@type": "Answer", "text": a}}
        for q, a in faq_list
    ]
    return html, json_entries


def build_page(comp: dict, stations_db: dict) -> tuple[str, str]:
    a, b = comp["a"], comp["b"]
    if a not in stations_db or b not in stations_db:
        raise ValueError(f"Station manquante dans IA_STATIONS : {a} ou {b}")
    sa, sb = stations_db[a], stations_db[b]
    slug_a, slug_b = slugify(a), slugify(b)
    page_slug = f"{slug_a}-vs-{slug_b}"
    canonical = f"{BASE_URL}/comparatifs/{page_slug}.html"

    faq_html, faq_entries = render_faq(comp["faq"])
    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "FAQPage", "mainEntity": faq_entries},
            {"@type": "Article",
             "headline": f"{a} vs {b} : quelle station choisir ?",
             "image": f"{BASE_URL}/img/{comp['img_a']}.jpg",
             "datePublished": date.today().isoformat(),
             "author": {"@type": "Organization", "name": "SnowFinder"}}
        ]
    }, ensure_ascii=False, indent=2)

    html = PAGE_TEMPLATE.format(
        a=a, b=b,
        canonical=canonical,
        BASE_URL=BASE_URL,
        img_a=comp["img_a"], img_b=comp["img_b"],
        slug_a=slug_a, slug_b=slug_b,
        teaser=comp["teaser"],
        spec_a=render_spec(sa), spec_b=render_spec(sb),
        winner_rows=render_winners(comp["winner"]),
        verdict=comp["verdict"],
        faq_html=faq_html,
        booking_a=booking_url(a), booking_b=booking_url(b),
        expedia_a=expedia_url(a, slug_a), expedia_b=expedia_url(b, slug_b),
        json_ld=json_ld,
    )
    return page_slug, html


# ── Page d'index des comparatifs ─────────────────────────────────────────────

def build_index(comparaisons_meta: list) -> str:
    cards = "\n".join(
        f'''<a href="/comparatifs/{slug}.html" class="comp-card">
              <div class="comp-imgs">
                <img src="/img/{c["img_a"]}.jpg" alt="{c["a"]}" loading="lazy">
                <img src="/img/{c["img_b"]}.jpg" alt="{c["b"]}" loading="lazy">
              </div>
              <div class="comp-body">
                <div class="comp-title">{c["a"]} <span class="vs">vs</span> {c["b"]}</div>
                <div class="comp-sub">Notre comparatif détaillé</div>
              </div>
            </a>'''
        for slug, c in comparaisons_meta
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Comparatifs de stations de ski — SnowFinder</title>
<meta name="description" content="Hésitation entre deux stations de ski françaises ? Découvrez nos comparatifs détaillés pour choisir la station qui vous correspond.">
<link rel="canonical" href="{BASE_URL}/comparatifs/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Serif+Display&display=swap" rel="stylesheet">
<style>
:root {{ --bg:#faf6f0; --wood-dark:#8b5e3c; --wood-light:#eddcbf; --wood-pale:#f7efe2;
        --text:#2a1f14; --text-mid:#5c4a35; --text-light:#8a7060; --border:#e8d8c4;
        --shadow:0 1px 4px rgba(0,0,0,.08); --shadow-md:0 6px 20px rgba(0,0,0,.12); --radius:14px; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family:'DM Sans',sans-serif; }}
.nav {{ background:#fff; border-bottom:1px solid var(--border); padding:14px 20px;
       display:flex; align-items:center; gap:18px; }}
.nav a.brand {{ font-family:"DM Serif Display",serif; font-size:1.4rem; color:var(--text); text-decoration:none; }}
.nav .navlinks {{ display:flex; gap:18px; margin-left:auto; }}
.nav .navlinks a {{ color:var(--text-mid); text-decoration:none; font-size:.95rem; }}
.page {{ max-width:1100px; margin:0 auto; padding:36px 24px 80px; }}
h1 {{ font-family:"DM Serif Display",serif; font-size:2.4rem; margin:0 0 10px; }}
.lead {{ font-size:1.05rem; color:var(--text-mid); margin-bottom:32px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:18px; }}
.comp-card {{ background:#fff; border:1px solid var(--border); border-radius:var(--radius);
            overflow:hidden; box-shadow:var(--shadow); text-decoration:none; color:inherit;
            transition:transform .15s, box-shadow .15s; display:block; }}
.comp-card:hover {{ transform:translateY(-3px); box-shadow:var(--shadow-md); }}
.comp-imgs {{ display:grid; grid-template-columns:1fr 1fr; height:160px; }}
.comp-imgs img {{ width:100%; height:100%; object-fit:cover; }}
.comp-body {{ padding:16px 18px; }}
.comp-title {{ font-family:"DM Serif Display",serif; font-size:1.2rem; }}
.comp-title .vs {{ color:var(--wood-dark); font-style:italic; font-size:.9rem; padding:0 4px; }}
.comp-sub {{ font-size:.85rem; color:var(--text-light); margin-top:4px; }}
</style>
</head>
<body>
<nav class="nav">
  <a href="/" class="brand">SnowFinder</a>
  <div class="navlinks">
    <a href="/recherche.html">Stations</a>
    <a href="/comparatifs/">Comparatifs</a>
    <a href="/tinder.html">Découvrir</a>
  </div>
</nav>
<main class="page">
  <h1>Comparatifs de stations</h1>
  <p class="lead">Hésitation entre deux stations populaires ? Nos comparatifs détaillés vous aident à choisir selon votre profil, votre budget et vos envies.</p>
  <div class="grid">
{cards}
  </div>
</main>
</body>
</html>
"""


# ── Snippet à insérer dans index.html ────────────────────────────────────────

def build_snippet(comparaisons_meta: list) -> str:
    cards = "\n".join(
        f'''  <a href="/comparatifs/{slug}.html" class="comparatif-card">
    <div class="comparatif-imgs">
      <img src="/img/{c["img_a"]}.jpg" alt="{c["a"]}" loading="lazy">
      <img src="/img/{c["img_b"]}.jpg" alt="{c["b"]}" loading="lazy">
    </div>
    <div class="comparatif-body">
      <div class="comparatif-title">{c["a"]} <span class="vs">vs</span> {c["b"]}</div>
      <div class="comparatif-sub">Lire le comparatif →</div>
    </div>
  </a>'''
        for slug, c in comparaisons_meta
    )

    return f"""<!-- ═════════════════════════════════════════════════════════════════════
     Section "Comparatifs" — à insérer dans index.html
     Place-la après ta section Tinder/recherche et avant les stations populaires
     ═════════════════════════════════════════════════════════════════════ -->

<style>
.comparatif-section {{ max-width:1100px; margin:60px auto; padding:0 20px; }}
.comparatif-section h2 {{
  font-family:"DM Serif Display",serif; font-size:2rem;
  margin:0 0 6px; color:var(--text,#2a1f14);
}}
.comparatif-section .comparatif-lead {{
  color:var(--text-light,#8a7060); margin-bottom:24px;
}}
.comparatif-grid {{
  display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:16px;
}}
.comparatif-card {{
  background:#fff; border:1px solid var(--border,#e8d8c4); border-radius:14px;
  overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,.08); text-decoration:none;
  color:inherit; transition:transform .15s, box-shadow .15s; display:block;
}}
.comparatif-card:hover {{ transform:translateY(-3px); box-shadow:0 6px 20px rgba(0,0,0,.12); }}
.comparatif-imgs {{ display:grid; grid-template-columns:1fr 1fr; height:140px; }}
.comparatif-imgs img {{ width:100%; height:100%; object-fit:cover; }}
.comparatif-body {{ padding:14px 16px; }}
.comparatif-title {{ font-family:"DM Serif Display",serif; font-size:1.1rem; color:#2a1f14; }}
.comparatif-title .vs {{ color:#8b5e3c; font-style:italic; font-size:.85rem; padding:0 4px; }}
.comparatif-sub {{ font-size:.85rem; color:#8a7060; margin-top:4px; }}
.comparatif-section .all-link {{
  display:inline-block; margin-top:18px; color:#8b5e3c;
  font-weight:600; text-decoration:none; font-size:.95rem;
}}
.comparatif-section .all-link:hover {{ text-decoration:underline; }}
</style>

<section class="comparatif-section">
  <h2>Comparatifs : quelle station choisir ?</h2>
  <p class="comparatif-lead">Nos guides détaillés pour vous aider à trancher entre deux stations populaires.</p>
  <div class="comparatif-grid">
{cards}
  </div>
  <a href="/comparatifs/" class="all-link">Voir tous les comparatifs →</a>
</section>

<!-- ═════════════════════════════════════════════════════════════════════
     Fin de la section "Comparatifs"
     ═════════════════════════════════════════════════════════════════════ -->
"""


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"📍 Racine : {REPO_ROOT}")
    stations_db = load_stations()
    print(f"✓ {len(stations_db)} stations chargées depuis recherche.html")

    COMPARATIFS_DIR.mkdir(exist_ok=True)
    print(f"✓ Dossier : {COMPARATIFS_DIR.relative_to(REPO_ROOT)}")

    meta = []
    for comp in COMPARAISONS:
        slug, html = build_page(comp, stations_db)
        out = COMPARATIFS_DIR / f"{slug}.html"
        out.write_text(html, encoding="utf-8")
        print(f"  → {out.relative_to(REPO_ROOT)}")
        meta.append((slug, comp))

    # Index des comparatifs
    (COMPARATIFS_DIR / "index.html").write_text(build_index(meta), encoding="utf-8")
    print(f"  → comparatifs/index.html")

    # Snippet pour index.html
    SNIPPET_OUT.parent.mkdir(exist_ok=True)
    SNIPPET_OUT.write_text(build_snippet(meta), encoding="utf-8")
    print(f"  → {SNIPPET_OUT.relative_to(REPO_ROOT)}")

    print()
    print(f"🎉 {len(COMPARAISONS)} comparatifs générés.")
    print()
    print("📸 Photos requises dans /img/ :")
    photos_needed = set()
    for c in COMPARAISONS:
        photos_needed.add(f"{c['img_a']}.jpg")
        photos_needed.add(f"{c['img_b']}.jpg")
    for p in sorted(photos_needed):
        print(f"   - {p}")


if __name__ == "__main__":
    main()
