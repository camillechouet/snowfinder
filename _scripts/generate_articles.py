#!/usr/bin/env python3
"""
SnowFinder — Générateur de pages statiques pour les articles
==============================================================
Transforme les articles (autrefois des popups JS dans index.html, invisibles
pour Google) en vraies pages HTML crawlables : /articles/{slug}.html

PHOTOS AUTOMATIQUES : chaque section d'article peut être associée à une
station (champ "station"). Le script va chercher automatiquement les photos
uploadées dans img/ pour cette station (même convention que
generate_stations.py : img/{slug-sans-accents-ni-separateurs}N.ext) et les
insère avec une légende ("📍 Nom de la station") pour que le visiteur sache
toujours à quelle station correspond la photo.

Si aucune photo n'est trouvée pour une station mentionnée, le script ne
casse rien : il saute la photo et l'affiche dans le résumé final
("photos manquantes") pour que tu saches quoi uploader.

Usage : python3 _scripts/generate_articles.py
Doit être exécuté à la racine du repo (là où se trouve le dossier img/).
Se déclenche automatiquement via la même GitHub Action que generate_stations.py.
"""
import re, os, json, unicodedata, html

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def slugify(name):
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')

def to_photo_slug(name):
    nfkd = unicodedata.normalize('NFD', name)
    ascii_only = ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', ascii_only.lower())

def get_station_photos(name):
    """Détecte les photos uploadées pour une station (img/{slug}1.jpg, 2.jpg...).
    Retourne une liste de chemins ('/img/...') ou liste vide si rien trouvé."""
    pslug = to_photo_slug(name)
    photos = []
    for i in range(1, 21):
        found = None
        for ext in ('jpg', 'jpeg', 'png', 'webp', 'JPG', 'JPEG', 'PNG', 'WEBP'):
            p = os.path.join(root_dir, 'img', f'{pslug}{i}.{ext}')
            if os.path.exists(p):
                found = f'/img/{pslug}{i}.{ext}'
                break
        if not found:
            break
        photos.append(found)
    return photos

# ──────────────────────────────────────────────────────────────
# DONNÉES DES ARTICLES
# Chaque article = liste de "sections". Une section avec "station" renseigné
# déclenche l'insertion automatique d'une photo + légende pour cette station.
# ──────────────────────────────────────────────────────────────

ARTICLES = [
    {
        "slug": "courchevel-vs-meribel",
        "kind": "comparatif",
        "cat": "Luxe",
        "title": "Courchevel vs Méribel : laquelle choisir ?",
        "excerpt": "Deux légendes des 3 Vallées, côte à côte, mais avec des caractères bien différents. Laquelle vous correspond ?",
        "date_display": "Janvier 2025",
        "date_iso": "2025-01-15",
        "read_time": "6 min",
        "emoji": "💎",
        "sections": [
            {"h3": None, "station": None,
             "html": "<p>Deux légendes des 3 Vallées, côte à côte, mais avec des caractères bien différents. Laquelle vous correspond ?</p>"},
            {"h3": "Courchevel : l'ostentation assumée", "station": "Courchevel",
             "html": "<p>Palaces, héliport privé, restaurants Michelin en altitude, boutiques de luxe... Courchevel 1850 est la station la plus chère du monde. Elle le sait et l'assume. Le domaine skiable est exceptionnel avec un accès direct aux 3 Vallées.</p>"},
            {"h3": "Méribel : le luxe à l'anglaise", "station": "Méribel",
             "html": "<p>Fondée par des Britanniques dans les années 40, Méribel a conservé une architecture chalet homogène et une ambiance plus décontractée. L'après-ski y est légendaire, plus festif et moins formel que chez sa voisine.</p>"},
            {"h3": "Le verdict", "station": None,
             "html": "<p>Pour les familles aisées qui veulent le meilleur sans l'exhibitionnisme : Méribel. Pour une expérience ultra-premium assumée avec les meilleures tables d'altitude de France : Courchevel. Les deux partagent le même accès aux 600 km des 3 Vallées.</p>"},
        ],
    },
    {
        "slug": "10-stations-secretes-alpes",
        "kind": "article",
        "cat": "Guide",
        "title": "Les 10 stations secrètes des Alpes qui valent le détour",
        "excerpt": "Entre les mastodontes comme Courchevel ou Val d'Isère, les Alpes abritent des trésors méconnus, plus authentiques et moins bondés.",
        "date_display": "Mars 2025",
        "date_iso": "2025-03-10",
        "read_time": "5 min",
        "emoji": "🏔",
        "sections": [
            {"h3": None, "station": None,
             "html": "<p>Entre les mastodontes comme Courchevel ou Val d'Isère, les Alpes abritent des trésors méconnus. Des stations qui ont su rester authentiques, accessibles et surtout moins bondées.</p>"},
            {"h3": "1. Sainte-Foy-Tarentaise", "station": "Sainte-Foy-Tarentaise",
             "html": "<p>Le secret le mieux gardé entre Les Arcs et Val d'Isère. 25 km de pistes pour un hors-piste légendaire. Forfait à 30€/j seulement.</p>"},
            {"h3": "2. Arêches-Beaufort", "station": "Arêches-Beaufort",
             "html": "<p>Dans le Beaufortain, neige naturelle souvent exceptionnelle. La forteresse des skieurs exigeants — et le Beaufort AOP en prime.</p>"},
            {"h3": "3. Bonneval-sur-Arc", "station": "Bonneval-sur-Arc",
             "html": "<p>Le plus haut village de Savoie (1800m) sous le col de l'Iséran. Architecture classée, ambiance hors du temps.</p>"},
            {"h3": "4. Les Karellis", "station": "Les Karellis",
             "html": "<p>Station associative unique en France. Tarifs imbattables, esprit montagne sans marketing.</p>"},
            {"h3": "5. La Grave - La Meije", "station": "La Grave - La Meije",
             "html": "<p>Aucune piste balisée, 2100m de dénivelé. La Mecque mondiale du ski hors-piste. Pour experts avec guide.</p>"},
            {"h3": "6. Valfréjus", "station": "Valfréjus",
             "html": "<p>Face à la Vanoise, peu fréquentée, domaine varié et technique qui surprend toujours.</p>"},
            {"h3": "7. Aussois", "station": "Aussois",
             "html": "<p>Village fortifié Vauban face à la Vanoise. 55 km confidentiels en Haute-Maurienne.</p>"},
            {"h3": "8. Puy-Saint-Vincent", "station": "Puy-Saint-Vincent",
             "html": "<p>Joyau des Hautes-Alpes au pied des Écrins. Ensoleillement exceptionnel, tarifs parmi les plus doux des Alpes du Sud.</p>"},
            {"h3": "9. Saint-Véran", "station": "Saint-Véran",
             "html": "<p>Plus haute commune d'Europe (2042m), Plus Beau Village de France. Ski dans le Queyras préservé.</p>"},
            {"h3": "10. Orelle", "station": "Orelle",
             "html": "<p>Porte d'entrée confidentielle des 3 Vallées depuis la Maurienne. Accès direct Val Thorens et 600 km des 3 Vallées.</p>"},
        ],
    },
    {
        "slug": "bilan-neige-pyrenees-hiver-2025",
        "kind": "article",
        "cat": "Enneigement",
        "title": "Hiver 2025 : quel bilan neigeux pour les Pyrénées ?",
        "excerpt": "La saison 2024-2025 dans les Pyrénées a été marquée par une alternance de périodes fastes et de coups de chaud préoccupants. Bilan contrasté.",
        "date_display": "Mars 2025",
        "date_iso": "2025-03-05",
        "read_time": "3 min",
        "emoji": "❄️",
        "sections": [
            {"h3": None, "station": None,
             "html": "<p>La saison 2024-2025 dans les Pyrénées a été marquée par une alternance de périodes fastes et de coups de chaud préoccupants. Bilan contrasté.</p>"},
            {"h3": "Un décembre difficile", "station": None,
             "html": "<p>Les premières semaines ont été marquées par un déficit neigeux notable, forçant plusieurs stations à retarder leur ouverture ou à recourir massivement à la neige de culture.</p>"},
            {"h3": "Janvier et février sauveurs", "station": "Grand Tourmalet",
             "html": "<p>Deux épisodes neigeux importants ont rattrapé le retard. Le Grand Tourmalet a ainsi enregistré jusqu'à 180 cm de neige fraîche en altitude, permettant l'ouverture de la quasi-totalité du domaine.</p>"},
            {"h3": "Les stations les mieux loties", "station": "Piau-Engaly",
             "html": "<p>Piau-Engaly, grâce à son altitude (1850m), et Saint-Lary-Soulan ont tiré leur épingle du jeu. Font-Romeu reste tributaire de son ensoleillement exceptionnel mais pénalisant en termes de conservation de la neige.</p>"},
        ],
    },
    {
        "slug": "top-5-stations-initier-enfants-ski",
        "kind": "article",
        "cat": "Famille",
        "title": "Top 5 des stations pour initier ses enfants au ski",
        "excerpt": "Mettre des skis aux enfants pour la première fois est un moment précieux. Choisir la bonne station fait toute la différence.",
        "date_display": "Février 2025",
        "date_iso": "2025-02-12",
        "read_time": "4 min",
        "emoji": "🎿",
        "sections": [
            {"h3": None, "station": None,
             "html": "<p>Mettre des skis aux enfants pour la première fois est un moment précieux. Choisir la bonne station fait toute la différence entre passion naissante et traumatisme durable.</p>"},
            {"h3": "1. Les Gets (Portes du Soleil)", "station": "Les Gets",
             "html": "<p>Label Famille Plus, village authentique et accès aux 650 km du domaine transfrontalier quand les enfants progressent. La référence.</p>"},
            {"h3": "2. Valmorel", "station": "Valmorel",
             "html": "<p>Station piétonne, architecture savoyarde, Famille Plus. Tout est pensé pour les enfants dès la conception de la station.</p>"},
            {"h3": "3. Villard-de-Lans (Vercors)", "station": "Villard-de-Lans",
             "html": "<p>À 30 min de Grenoble, label Famille Plus, ski nordique, patinoire... Un plateau de jeux hivernal à tarifs très accessibles.</p>"},
            {"h3": "4. Les Contamines-Montjoie", "station": "Les Contamines-Montjoie",
             "html": "<p>Au pied du Mont-Blanc, dans une Réserve de Biosphère UNESCO. Calme, nature, et garderie très appréciée.</p>"},
            {"h3": "5. Les Saisies (Beaufortain)", "station": "Les Saisies",
             "html": "<p>Berceau du ski de fond olympique, excellent domaine alpin familial, Famille Plus. La montagne authentique sans stress.</p>"},
        ],
    },
    {
        "slug": "ski-de-printemps-conseils",
        "kind": "article",
        "cat": "Conseils",
        "title": "Ski de printemps : comment profiter des dernières neiges",
        "excerpt": "Mars et avril sont souvent les mois les plus agréables pour skier. Neige transformée le matin, soleil l'après-midi, terrasses animées...",
        "date_display": "Mars 2025",
        "date_iso": "2025-03-20",
        "read_time": "4 min",
        "emoji": "🎿",
        "sections": [
            {"h3": None, "station": None,
             "html": "<p>Mars et avril sont souvent les mois les plus agréables pour skier. Neige transformée le matin, soleil l'après-midi, terrasses animées... Le ski de printemps a ses adeptes.</p>"},
            {"h3": "Choisir les bonnes stations", "station": "Val Thorens",
             "html": "<p>Les stations glaciaires comme Tignes, Les 2 Alpes ou Val Thorens garantissent de la neige jusqu'en mai. Privilégiez les versants nord le matin, les versants sud l'après-midi pour profiter de la neige de printemps.</p>"},
            {"h3": "Les bons réflexes", "station": None,
             "html": "<p>Partez tôt le matin quand la neige est encore dure. Évitez les pistes sud après 11h. Profitez des terrasses et des concerts en altitude qui animent la fin de saison.</p>"},
            {"h3": "Les prix baissent", "station": None,
             "html": "<p>Forfaits, hébergements, cours : tout est moins cher au printemps. Une opportunité parfaite pour les familles qui veulent économiser sans sacrifier la qualité.</p>"},
        ],
    },
    {
        "slug": "jura-a-ski",
        "kind": "article",
        "cat": "Découverte",
        "title": "Le Jura à ski : la montagne oubliée des Français",
        "excerpt": "Coincé entre les Alpes et la Suisse, le Jura souffre d'un déficit d'image injuste. Pourtant, il offre un ski sincère et abordable.",
        "date_display": "Février 2025",
        "date_iso": "2025-02-05",
        "read_time": "5 min",
        "emoji": "🧀",
        "sections": [
            {"h3": None, "station": None,
             "html": "<p>Coincé entre les Alpes et la Suisse, le Jura souffre d'un déficit d'image injuste. Pourtant, il offre un ski sincère, abordable et des paysages d'une beauté froide et minérale.</p>"},
            {"h3": "Métabief Mont d'Or, la référence", "station": "Métabief Mont d'Or",
             "html": "<p>Plus grande station du massif avec 40 km de pistes. Label Famille Plus, vue sur les Alpes par temps clair depuis le Mont d'Or à 1463m. Un must du Jura.</p>"},
            {"h3": "Les Rousses, le paradis nordique", "station": "Les Rousses",
             "html": "<p>200 km de pistes de fond, 4 communes reliées... Les Rousses sont LE haut lieu du ski nordique français. L'alpin y est aussi de qualité, dans un cadre préservé.</p>"},
            {"h3": "Côté budget", "station": None,
             "html": "<p>Comptez 20 à 26€ pour un forfait journée. Les hébergements sont 2 à 3 fois moins chers que dans les Alpes. Le Jura reste la montagne la plus accessible de France.</p>"},
        ],
    },
    {
        "slug": "vosges-ski-accessible",
        "kind": "article",
        "cat": "Guide",
        "title": "Vosges : ski accessible à 2h de Paris et Strasbourg",
        "excerpt": "Pas besoin de traverser la France pour skier. Les Vosges offrent un ski simple, chaleureux et très abordable.",
        "date_display": "Janvier 2025",
        "date_iso": "2025-01-08",
        "read_time": "3 min",
        "emoji": "🌲",
        "sections": [
            {"h3": None, "station": None,
             "html": "<p>Pas besoin de traverser la France pour skier. Les Vosges offrent un ski simple, chaleureux et très abordable, idéal pour un weekend improvisé.</p>"},
            {"h3": "Gérardmer, la perle vosgienne", "station": "Gérardmer",
             "html": "<p>Au bord du lac de Gérardmer, la plus grande station des Vosges propose 40 km de pistes variées avec snowpark. Le tout dans un cadre lacustre unique en France.</p>"},
            {"h3": "La Bresse-Hohneck", "station": "La Bresse-Hohneck",
             "html": "<p>Face au point culminant des Vosges, domaine alpin et nordique complémentaires. La station la plus complète du massif pour les familles.</p>"},
            {"h3": "Conseil", "station": None,
             "html": "<p>Les Vosges sont sensibles aux coups de chaud. Consultez l'enneigement avant de partir et privilégiez janvier-février pour de meilleures conditions.</p>"},
        ],
    },
    {
        "slug": "ski-sur-volcan-massif-central",
        "kind": "article",
        "cat": "Découverte",
        "title": "Ski sur volcan : l'expérience unique du Massif Central",
        "excerpt": "Skier sur un volcan endormi, c'est une expérience que peu de skieurs français ont vécue. Le Massif Central offre des stations authentiques.",
        "date_display": "Décembre 2024",
        "date_iso": "2024-12-10",
        "read_time": "4 min",
        "emoji": "🌋",
        "sections": [
            {"h3": None, "station": None,
             "html": "<p>Skier sur un volcan endormi, c'est une expérience que peu de skieurs français ont vécue. Et pourtant, le Massif Central offre des stations authentiques avec un caractère unique.</p>"},
            {"h3": "Le Lioran et le Plomb du Cantal", "station": "Le Lioran",
             "html": "<p>Plus grande station du Massif Central avec 60 km de pistes. Le Plomb du Cantal à 1855m offre des panoramas vertigineux sur les volcans d'Auvergne. Village station authentique avec ses burons traditionnels.</p>"},
            {"h3": "Super Besse et le Puy de Sancy", "station": "Super Besse",
             "html": "<p>Point culminant du Massif Central (1886m), le Puy de Sancy domine Super Besse. Le lac Pavin, cratère volcanique aux eaux d'un bleu mystérieux, est à quelques kilomètres.</p>"},
            {"h3": "Pourquoi y aller ?", "station": None,
             "html": "<p>Pour l'authenticité, les prix (25-28€ le forfait), la gastronomie auvergnate et surtout pour vivre quelque chose de différent. Le Massif Central, c'est la montagne sans prétention.</p>"},
        ],
    },
    {
        "slug": "le-lioran-tour-de-france-2026",
        "kind": "station",
        "cat": "Découverte",
        "title": "Le Lioran cet été : le Tour de France débarque, et c'est le moment d'en parler",
        "excerpt": "Le Lioran, la plus grande station du Massif Central, s'apprête à vivre l'un des plus grands moments de son histoire le 14 juillet 2026.",
        "date_display": "Juillet 2026",
        "date_iso": "2026-07-01",
        "read_time": "7 min",
        "emoji": "🚴",
        "sections": [
            {"h3": None, "station": "Le Lioran", "html": (
                "<p>On fait une exception. SnowFinder, c'est la neige et les stations de ski — mais la montagne, ça se vit aussi l'été, et j'y vais moi-même tous les ans. Alors quand Le Lioran, la plus grande station du Massif Central, s'apprête à vivre l'un des plus grands moments de son histoire le <strong>14 juillet 2026</strong> avec l'arrivée d'une étape du Tour de France, impossible de ne pas en parler.</p>"
                "<p style=\"font-style:italic\">Autant vous prévenir tout de suite : je ne suis pas neutre. Le Lioran, j'y vais tous les ans, été ou hiver, si ce n'est parfois les deux.</p>")},
            {"h3": "Une station dynamique, été comme hiver", "station": None,
             "html": "<p>Dès que la neige fond, Le Lioran ne se met pas en pause — elle change juste de rythme. Le bike park est l'un des plus réputés du Massif Central : de nombreuses pistes de descente, de la verte tranquille aux noires bien engagées, avec des circuits pour tous les niveaux. Des remontées mécaniques tournent tous les jours de juin à septembre pour épargner les mollets. Petit détail qui a son importance : le tout premier pumptrack de France a vu le jour ici. Autant dire que la station a l'esprit VTT depuis longtemps.</p><p>Pour ceux qui préfèrent garder les pieds sur terre, le téléphérique du Plomb du Cantal grimpe en quelques minutes vers le sommet — un raccourci bien pratique avant d'attaquer la suite à pied.</p>"},
            {"h3": "Des randonnées à couper le souffle, volcans compris", "station": None,
             "html": "<p>Le Lioran est niché au cœur du Parc Naturel Régional des Volcans d'Auvergne, sur l'un des plus grands stratovolcans d'Europe. Depuis le sommet du téléphérique, un sentier d'une vingtaine de minutes mène au Plomb du Cantal (1855 m) et à son panorama à 360° sur tout le Massif Central. Les marcheurs plus aguerris pousseront jusqu'au Puy Griou (1690 m), silhouette conique reconnaissable entre mille.</p><p>Et il y a bien d'autres sommets où les randos sont superbes : le téton de Vénus (1669 m) et le rocher du Bec de l'Aigle (1699 m), en crête l'un à côté de l'autre, offrent un panorama à 360° sur tout le stratovolcan. Le puy de Peyre Arse (1806 m) domine littéralement le massif, juste derrière le Puy Mary. Et pour les amateurs de route, le Pas de Peyrol (1589 m), au pied du Puy Mary, est tout simplement le plus haut col routier d'Auvergne.</p><p>Impossible d'aller au Lioran sans parler truffade : ce plat auvergnat à base de pommes de terre et de tome fraîche, généreux et réconfortant, est une institution locale — la récompense parfaite après une bonne rando.</p>"},
            {"h3": "2024 : le duel Pogačar-Vingegaard", "station": None,
             "html": "<p>Si vous voulez comprendre pourquoi l'arrivée du Tour au Lioran a quelque chose de spécial, il faut reparler de la 11e étape du Tour de France 2024. Tadej Pogačar attaque dans le Pas de Peyrol, à plus de 30 km de l'arrivée, et prend jusqu'à 40 secondes d'avance. Jonas Vingegaard revient dans la montée suivante, et les deux hommes terminent en duel jusqu'à la ligne — remportée par le Danois, alors même que le Slovène conservait le maillot jaune. Alors oui, forcément, le 14 juillet 2026, j'y serai aussi.</p>"},
            {"h3": "14 juillet 2026 : une étape 100% cantalienne, une première dans l'histoire du Tour", "station": None,
             "html": "<p>Le mardi 14 juillet 2026, jour de fête nationale, la 10e étape du Tour de France reliera Aurillac au Lioran sur 167 km et près de 3 900 m de dénivelé positif — un profil de montagne exigeant, entièrement tracé sur les routes du Cantal pour la première fois de l'histoire de la course. Le peloton grimpera notamment le col de la Griffoul, le Pas de Peyrol au pied du Puy Mary, puis le col de Font de Cère avant de plonger vers l'arrivée, jugée au pied du Plomb du Cantal.</p>"},
            {"h3": "Et l'hiver, alors ?", "station": "Le Lioran",
             "html": "<p>On ne va pas se mentir, c'est aussi (surtout ?) pour ça qu'on est là d'habitude. Le Lioran reste la plus grande station de ski du Massif Central, avec un enneigement réputé froid et sec grâce à son climat volcanique. Village-station authentique avec ses burons traditionnels, elle reste une valeur sûre pour un séjour au ski en famille, l'hiver venu.</p><p style=\"font-style:italic\">On revient très vite à ce qu'on sait faire de mieux : vous aider à trouver la bonne station pour skier. Mais si jamais vous passez dans le Cantal cet été, foncez au Lioran — vous ne serez pas déçus.</p>"},
        ],
    },
]

KIND_FOLDER = {
    "article": "articles",
    "comparatif": "comparatifs",
    "station": "station-du-moment",
}
KIND_LABEL = {
    "article": "Articles",
    "comparatif": "Comparatifs",
    "station": "Station du moment",
}
# Page listant tous les contenus d'un type donné (PAS un index.html — un seul
# index.html existe sur tout le site : la page d'accueil). Le kind "station"
# n'a pas de page de listing car la homepage ne montre que la station actuelle.
KIND_LISTING_FILE = {
    "article": "toutes-les-actus.html",
    "comparatif": "tous-les-duels.html",
}
LISTING_TITLE = {
    "article": "Toutes nos actus",
    "comparatif": "Tous les duels de stations",
}

CATEGORY_COLORS = {
    "Découverte": "#6888a8", "Guide": "#3a7db8", "Enneigement": "#c47a20",
    "Famille": "#2a7a3a", "Luxe": "#a87840", "Conseils": "#1a6fa8",
}

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{title} | SnowFinder</title>
<meta name="description" content="{excerpt}">
<link rel="canonical" href="https://snowfinder.fr/{folder}/{slug}.html">
<link rel="apple-touch-icon" href="/logo.png">
<link rel="icon" type="image/png" href="/logo.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="SnowFinder">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{excerpt}">
<meta property="og:url" content="https://snowfinder.fr/{folder}/{slug}.html">
<meta property="og:image" content="{og_image}">
<meta property="og:locale" content="fr_FR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{excerpt}">
<meta name="twitter:image" content="{og_image}">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": {title_json},
  "description": {excerpt_json},
  "datePublished": "{date_iso}",
  "author": {{"@type": "Organization", "name": "SnowFinder"}},
  "publisher": {{"@type": "Organization", "name": "SnowFinder", "logo": {{"@type": "ImageObject", "url": "https://snowfinder.fr/logo.png"}}}},
  "mainEntityOfPage": "https://snowfinder.fr/{folder}/{slug}.html"
}}
</script>
<style>
:root{{--blue:#3a7db8;--blue-dark:#1a5a8a;--text:#22303e;--text-mid:#4a5a6a;--text-light:#8a97a3;--bg:#f7f9fb;--white:#fff;--cat:{cat_color}}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"DM Sans",-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}}
a{{color:var(--blue);text-decoration:none}}
.wrap{{max-width:720px;margin:0 auto;padding:0 20px}}
header{{background:var(--white);border-bottom:1px solid #e4e9ee;padding:14px 0}}
.hlogo{{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--text)}}
.hlogo img{{width:32px;height:32px;border-radius:8px}}
.breadcrumb{{font-size:.82rem;color:var(--text-light);margin:20px 0 8px}}
.breadcrumb a{{color:var(--text-light)}}
.art-cat{{display:inline-block;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--cat);background:color-mix(in srgb, var(--cat) 12%, white);padding:4px 10px;border-radius:20px;margin-bottom:14px}}
h1{{font-family:"DM Serif Display",serif;font-size:1.9rem;line-height:1.25;margin-bottom:14px;color:var(--text)}}
.art-meta{{font-size:.82rem;color:var(--text-light);margin-bottom:28px}}
.art-meta span{{margin-right:14px}}
article h3{{font-family:"DM Serif Display",serif;font-size:1.3rem;margin:28px 0 10px;color:var(--text)}}
article p{{font-size:1.02rem;color:var(--text-mid);margin-bottom:14px}}
figure{{margin:18px 0}}
figure img{{width:100%;border-radius:12px;object-fit:cover;max-height:320px;display:block}}
figcaption{{font-size:.78rem;color:var(--text-light);margin-top:6px;display:flex;align-items:center;gap:4px}}
footer{{margin:50px 0 30px;padding-top:24px;border-top:1px solid #e4e9ee;font-size:.85rem;color:var(--text-light)}}
footer a{{color:var(--blue)}}
.back-link{{display:inline-block;margin:24px 0 0;font-size:.9rem;font-weight:600}}
</style>
</head>
<body>
<header><div class="wrap"><a href="/index.html" class="hlogo"><img src="/logo.png" alt="SnowFinder">SnowFinder</a></div></header>
<div class="wrap">
  <div class="breadcrumb"><a href="/index.html">Accueil</a> › {kind_label} › {title}</div>
  <span class="art-cat">{cat}</span>
  <h1>{title}</h1>
  <div class="art-meta"><span>✍️ Rédaction SnowFinder</span><span>📅 {date_display}</span><span>⏱ {read_time} de lecture</span></div>
  <article>
{content}
  </article>
  <a class="back-link" href="/index.html">← Retour à l'accueil</a>
  <footer>
    <p><strong>SnowFinder</strong> — Le guide des stations de ski françaises</p>
    <p><a href="/recherche.html">Trouver une station</a> · <a href="/comparateur.html">Comparateur</a> · <a href="/mentions-legales.html">Mentions légales</a></p>
  </footer>
</div>
</body>
</html>
"""

LISTING_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{page_title} — SnowFinder</title>
<meta name="description" content="Comparatifs de stations, bons plans, bilans d'enneigement et guides pour bien choisir votre séjour au ski en France.">
<link rel="canonical" href="https://snowfinder.fr/{folder}/{filename}">
<link rel="apple-touch-icon" href="/logo.png">
<link rel="icon" type="image/png" href="/logo.png">
<style>
:root{{--blue:#3a7db8;--text:#22303e;--text-mid:#4a5a6a;--text-light:#8a97a3;--bg:#f7f9fb;--white:#fff}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"DM Sans",-apple-system,sans-serif;background:var(--bg);color:var(--text)}}
a{{color:inherit;text-decoration:none}}
.wrap{{max-width:900px;margin:0 auto;padding:0 20px}}
header{{background:var(--white);border-bottom:1px solid #e4e9ee;padding:14px 0}}
.hlogo{{display:flex;align-items:center;gap:10px;font-weight:700}}
.hlogo img{{width:32px;height:32px;border-radius:8px}}
.breadcrumb{{font-size:.82rem;color:var(--text-light);margin:20px 0 8px}}
.breadcrumb a{{color:var(--text-light)}}
h1{{font-family:"DM Serif Display",serif;font-size:1.8rem;margin:0 0 24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-bottom:40px}}
.card{{background:var(--white);border-radius:14px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);transition:transform .15s}}
.card:hover{{transform:translateY(-2px)}}
.card-body{{padding:16px}}
.card-cat{{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--blue);margin-bottom:8px}}
.card-title{{font-family:"DM Serif Display",serif;font-size:1.08rem;line-height:1.35;margin-bottom:8px}}
.card-excerpt{{font-size:.85rem;color:var(--text-mid);margin-bottom:10px}}
.card-meta{{font-size:.72rem;color:var(--text-light)}}
</style>
</head>
<body>
<header><div class="wrap"><a href="/index.html" class="hlogo"><img src="/logo.png" alt="SnowFinder">SnowFinder</a></div></header>
<div class="wrap">
  <div class="breadcrumb"><a href="/index.html">Accueil</a> › {page_title}</div>
  <h1>{page_title}</h1>
  <div class="grid">
{cards}
  </div>
</div>
</body>
</html>
"""

def build_content(sections):
    photos_missing = []
    html_parts = []
    for sec in sections:
        if sec["h3"]:
            html_parts.append(f'    <h3>{sec["h3"]}</h3>')
        html_parts.append(f'    {sec["html"]}')
        if sec["station"]:
            photos = get_station_photos(sec["station"])
            if photos:
                html_parts.append(
                    f'    <figure><img src="{photos[0]}" alt="{sec["station"]} - photo SnowFinder" loading="lazy">'
                    f'<figcaption>📍 {sec["station"]}</figcaption></figure>'
                )
            else:
                photos_missing.append(sec["station"])
    return "\n".join(html_parts), photos_missing

def main():
    all_missing = {}
    by_folder = {}  # folder -> list of article dicts (pour le résumé terminal uniquement)

    for art in ARTICLES:
        folder = KIND_FOLDER[art["kind"]]
        kind_label = KIND_LABEL[art["kind"]]
        out_dir = os.path.join(root_dir, folder)
        os.makedirs(out_dir, exist_ok=True)
        by_folder.setdefault(folder, []).append(art)

        content_html, missing = build_content(art["sections"])
        if missing:
            all_missing[art["slug"]] = missing

        og_image = None
        for sec in art["sections"]:
            if sec["station"]:
                photos = get_station_photos(sec["station"])
                if photos:
                    og_image = f'https://snowfinder.fr{photos[0]}'
                    break
        if not og_image:
            og_image = 'https://snowfinder.fr/logo.png'

        page = PAGE_TEMPLATE.format(
            title=html.escape(art["title"]),
            title_json=json.dumps(art["title"], ensure_ascii=False),
            excerpt=html.escape(art["excerpt"]),
            excerpt_json=json.dumps(art["excerpt"], ensure_ascii=False),
            slug=art["slug"],
            folder=folder,
            kind_label=kind_label,
            og_image=og_image,
            date_iso=art["date_iso"],
            date_display=art["date_display"],
            read_time=art["read_time"],
            cat=art["cat"],
            cat_color=CATEGORY_COLORS.get(art["cat"], "#3a7db8"),
            content=content_html,
        )
        with open(os.path.join(out_dir, f'{art["slug"]}.html'), 'w', encoding='utf-8') as f:
            f.write(page)

    print(f"✅ {len(ARTICLES)} pages générées dans 3 dossiers (aucun index.html créé dans ces dossiers — un seul index existe : la page d'accueil) :")
    for folder, arts in by_folder.items():
        print(f"  /{folder}/  ({len(arts)} page{'s' if len(arts)>1 else ''})")

    # Pages "voir tout" (PAS des index.html) pour les kinds qui en ont une
    for kind, filename in KIND_LISTING_FILE.items():
        folder = KIND_FOLDER[kind]
        arts = [a for a in ARTICLES if a["kind"] == kind]
        if not arts:
            continue
        sorted_arts = sorted(arts, key=lambda a: a["date_iso"], reverse=True)
        cards = []
        for art in sorted_arts:
            cards.append(
                f'    <a class="card" href="/{folder}/{art["slug"]}.html">'
                f'<div class="card-body"><div class="card-cat">{art["cat"]}</div>'
                f'<div class="card-title">{html.escape(art["title"])}</div>'
                f'<div class="card-excerpt">{html.escape(art["excerpt"])}</div>'
                f'<div class="card-meta">{art["date_display"]} · {art["read_time"]} de lecture</div>'
                f'</div></a>'
            )
        page = LISTING_TEMPLATE.format(
            page_title=LISTING_TITLE[kind],
            folder=folder,
            filename=filename,
            cards="\n".join(cards),
        )
        with open(os.path.join(root_dir, folder, filename), 'w', encoding='utf-8') as f:
            f.write(page)
        print(f"  /{folder}/{filename}  (liste de {len(arts)})")

    if all_missing:
        print("\n⚠️  Photos manquantes (aucune trouvée dans img/, à uploader) :")
        for slug, stations in all_missing.items():
            print(f"  - {slug}: {', '.join(stations)}")
    else:
        print("📷 Toutes les stations référencées ont au moins une photo.")

if __name__ == '__main__':
    main()
