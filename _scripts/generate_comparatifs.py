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
# ── URL officielles des stations (copiées de generate_stations.py) ───────────

OFFICIAL_URLS = {
    # SAVOIE / TARENTAISE
    "Val d'Isère":                  "https://www.valdisere.com",
    "Tignes":                       "https://www.tignes.net",
    "Les Arcs":                     "https://www.lesarcs.com",
    "La Plagne":                    "https://www.la-plagne.com",
    "Courchevel":                   "https://www.courchevel.com",
    "Méribel":                      "https://www.meribel.net",
    "Val Thorens":                  "https://www.valthorens.com",
    "Les Menuires":                 "https://www.lesmenuires.com",
    "Saint-Martin-de-Belleville":   "https://www.saintmartindebelleville.com",
    "La Tania":                     "https://www.latania.com",
    "Orelle":                       "https://www.orelle.net",
    "Sainte-Foy-Tarentaise":        "https://www.saintefoy.net",
    "La Rosière":                   "https://www.larosiere.net",
    "Champagny-en-Vanoise":         "https://www.champagny.com",
    "Peisey-Vallandry":             "https://www.peisey-vallandry.com",
    "Montchavin-Les Coches":        "https://www.montchavin-lescoches.com",
    "Pralognan-la-Vanoise":         "https://www.pralognan.com",
    "Brides-les-Bains":             "https://www.brides-les-bains.com",
    "Valmorel":                     "https://www.valmorel.com",
    "Arêches-Beaufort":             "https://www.areches-beaufort.com",
    "Beaufort-sur-Doron":           "https://www.areches-beaufort.com",
    "Hauteluce":                    "https://www.hauteluce.com",
    "Les Saisies":                  "https://www.lessaisies.com",
    "Peisey-Nancroix":              "https://www.peisey-nancroix.com",
    # SAVOIE / MAURIENNE
    "Valloire":                     "https://www.valloire.net",
    "Valmeinier":                   "https://www.valmeinier.com",
    "Val Cenis":                    "https://www.valcenis.com",
    "Aussois":                      "https://www.aussois.com",
    "Bonneval-sur-Arc":             "https://www.bonneval-sur-arc.com",
    "Bessans":                      "https://www.bessans.com",
    "Valfréjus":                    "https://www.valfreejus.fr",
    "La Norma":                     "https://www.la-norma.com",
    "Albiez-Montrond":              "https://www.albiez-montrond.com",
    "Saint-François-Longchamp":     "https://www.saintfrancois-longchamp.com",
    "Les Karellis":                 "https://www.leskarellis.com",
    "La Toussuire":                 "https://www.latoussuire.com",
    "Le Corbier":                   "https://www.le-corbier.com",
    "Saint-Sorlin-d'Arves":         "https://www.saint-sorlin-arves.com",
    "Saint-Jean-d'Arves":           "https://www.saint-jean-arves.com",
    "Saint-Colomban-des-Villards":  "https://www.saintcolombandesvillards.com",
    "Termignon":                    "https://www.termignon.fr",
    # SAVOIE / AVANT-PAYS & ANNECY
    "Savoie Grand Revard":          "https://www.grand-revard.com",
    "Le Revard":                    "https://www.lerevard.com",
    "La Féclaz":                    "https://www.la-feclaz.com",
    "Semnoz - Annecy":              "https://www.semnoz.fr",
    # HAUTE-SAVOIE / MONT-BLANC
    "Chamonix":                     "https://www.chamonix.com",
    "Megève":                       "https://www.megeve.com",
    "Saint-Gervais":                "https://www.saintgervais.com",
    "Les Houches":                  "https://www.leshouches.com",
    "Combloux":                     "https://www.combloux.com",
    "Les Contamines-Montjoie":      "https://www.lescontamines.com",
    "Praz-sur-Arly":                "https://www.praz-sur-arly.com",
    "Flumet":                       "https://www.flumet-montblanc.com",
    "Crest-Voland":                 "https://www.crest-voland-cohennoz.com",
    "Notre-Dame-de-Bellecombe":     "https://www.notre-dame-de-bellecombe.com",
    "La Giettaz":                   "https://www.la-giettaz.fr",
    "Montriond":                    "https://www.montriond.com",
    "Thollon-les-Mémises":          "https://www.thollon.com",
    # HAUTE-SAVOIE / PORTES DU SOLEIL
    "Avoriaz":                      "https://www.avoriaz.com",
    "Morzine":                      "https://www.morzine.com",
    "Les Gets":                     "https://www.lesgets.com",
    "Châtel":                       "https://www.chatel.com",
    "La Chapelle d'Abondance":      "https://www.lachapelle-abondance.com",
    "Abondance":                    "https://www.abondance.com",
    "Saint-Jean-d'Aulps":           "https://www.saint-jean-daulps.com",
    # HAUTE-SAVOIE / GRAND MASSIF
    "Flaine":                       "https://www.flaine.com",
    "Les Carroz":                   "https://www.lescarroz.com",
    "Samoëns":                      "https://www.samoens.com",
    "Morillon":                     "https://www.morillon.fr",
    "Praz-de-Lys Sommand":          "https://www.prazdelys-sommand.com",
    # HAUTE-SAVOIE / ARAVIS
    "La Clusaz":                    "https://www.laclusaz.com",
    "Le Grand-Bornand":             "https://www.legrandbornand.com",
    # ISÈRE
    "Chamrousse":                   "https://www.chamrousse.com",
    "Les 7 Laux":                   "https://www.les7laux.com",
    "Alpe d'Huez":                  "https://www.alpedhuez.com",
    "Les Deux Alpes":               "https://www.les2alpes.com",
    "Auris-en-Oisans":              "https://www.auris-en-oisans.com",
    "Alpe du Grand Serre":          "https://www.algrandserre.com",
    "Villard-de-Lans":              "https://www.villarddelans.com",
    "Corrençon-en-Vercors":         "https://www.correncon.com",
    "Autrans-Méaudre":              "https://www.autrans-meaudre.fr",
    "Lans-en-Vercors":              "https://www.lans-en-vercors.fr",
    # HAUTES-ALPES / BRIANÇONNAIS
    "Serre Chevalier":              "https://www.serre-chevalier.com",
    "Montgenèvre":                  "https://www.montgenevre.com",
    "La Grave - La Meije":          "https://www.lagrave-lameije.com",
    "Vallouise":                    "https://www.vallouise-pelvoux.fr",
    # HAUTES-ALPES / CHAMPSAUR-DÉVOLUY
    "Orcières-Merlette":            "https://www.orcieres.com",
    "Orcières 1850":                "https://www.orcieres.com",
    "Superdévoluy":                 "https://www.superdevoluy.com",
    "La Joue du Loup":              "https://www.joue-du-loup.com",
    # HAUTES-ALPES / EMBRUN & QUEYRAS
    "Vars":                         "https://www.vars.com",
    "Risoul":                       "https://www.risoul.com",
    "Les Orres":                    "https://www.lesorres.com",
    "Puy-Saint-Vincent":            "https://www.puy-saint-vincent.com",
    "Saint-Léger-les-Mélèzes":      "https://www.saintlegerlesmeleze.com",
    "Abriès-en-Queyras":            "https://www.abriesqueyras.com",
    "Arvieux-en-Queyras":           "https://www.arvieux.fr",
    "Molines-Saint-Véran":          "https://www.molines-en-queyras.com",
    "Aiguilles":                    "https://www.aiguilles-queyras.com",
    # ALPES-DE-HAUTE-PROVENCE
    "Pra-Loup":                     "https://www.praloup.com",
    "Val d'Allos":                  "https://www.valdeallos.com",
    "Chabanon":                     "https://www.chabanon-selonnet.com",
    "Sauze-Super-Sauze":            "https://www.sauze.com",
    "Mont Serein":                  "https://www.mont-serein.fr",
    # ALPES-MARITIMES
    "Isola 2000":                   "https://www.isola2000.com",
    "Auron":                        "https://www.auron.com",
    # PYRÉNÉES / HAUTES-PYRÉNÉES
    "Grand Tourmalet":              "https://www.grand-tourmalet.com",
    "La Mongie-Barèges (Tourmalet)":"https://www.grand-tourmalet.com",
    "Saint-Lary-Soulan":            "https://www.saintlary.com",
    "Saint-Lary-Village":           "https://www.saintlary.com",
    "Piau-Engaly":                  "https://www.piau-engaly.com",
    "Luz-Ardiden":                  "https://www.luz-ardiden.com",
    "Cauterets":                    "https://www.cauterets.com",
    "Gavarnie-Gèdre":               "https://www.gavarnie-gedre.com",
    "Val-Louron":                   "https://www.val-louron.com",
    "Peyragudes":                   "https://www.peyragudes.com",
    "Luchon-Superbagnères":         "https://www.luchon-superbagneres.com",
    "Peyresourde-Balestas":         "https://www.peyresourde-balestas.com",
    # PYRÉNÉES-ATLANTIQUES & ARIÈGE
    "Gourette":                     "https://www.gourette.com",
    "La Pierre-Saint-Martin":       "https://www.lapierresaintmartin.fr",
    "Ax-3-Domaines":                "https://www.ax-ski.com",
    "Les Monts d'Olmes":            "https://www.monts-olmes.com",
    # PYRÉNÉES-ORIENTALES
    "Font-Romeu-Pyrénées 2000":     "https://www.font-romeu.fr",
    "Les Angles":                   "https://www.lesangles.com",
    "Bolquère-Pyrénées 2000":       "https://www.bolquere.com",
    "Formiguères":                  "https://www.formigueres.com",
    "Cambre d'Aze":                 "https://www.cambred-aze.com",
    "Guzet":                        "https://www.guzet.com",
    # VOSGES
    "Gérardmer":                    "https://www.gerardmer-montagne.com",
    "La Bresse-Hohneck":            "https://www.labresse.net",
    "Le Markstein":                 "https://www.lemarkstein.fr",
    # JURA
    "Métabief Mont d'Or":           "https://www.metabief.com",
    "Les Rousses":                  "https://www.lesrousses.com",
    "Monts Jura":                   "https://www.montsjura.com",
    "Lamoura":                      "https://www.station-lamoura.com",
    "Mijoux-La Valserine":          "https://www.station-mijoux.com",
    "Lélex-Crozet":                 "https://www.lelex.com",
    # MASSIF CENTRAL
    "Le Lioran":                    "https://www.lelioran.com",
    "Super Besse":                  "https://www.superbesse.com",
    "Le Mont Dore":                 "https://www.sancy.com",
    "Chastreix-Sancy":              "https://www.chastreix-sancy.com",
    "Chalmazel":                    "https://www.chalmazel.fr",
    # CORSE
    "Ghisoni - Capanelle":          "https://www.ski-capanelle.com",
}

def official_url(name: str) -> str:
    """Retourne l'URL officielle de la station, ou un Google search en fallback."""
    return OFFICIAL_URLS.get(
        name,
        f"https://www.google.com/search?q={name.replace(' ', '+').replace(chr(39), '+')}+station+ski+site+officiel"
    )




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
        "profils": [
            ("👨‍👩‍👧‍👦 Famille avec jeunes enfants", "Les Menuires",
             "Front de neige doux à La Croisette, label Espaces ludiques, garderies, et tarif d'hébergement 25-35% inférieur."),
            ("🎿 Skieurs confirmés en quête de grand domaine", "Val Thorens",
             "Altitude 2300-3230 m, neige fiable de novembre à mai, accès direct aux 600 km des 3 Vallées."),
            ("🎉 Fêtards et après-ski animé", "Val Thorens",
             "La Folie Douce historique, La Cabane, ambiance qui ne dort jamais. Les Menuires reste plus calme côté soirées."),
            ("💰 Budget serré", "Les Menuires",
             "Même forfait 3 Vallées, hébergement bien moins cher. Astuce : loger aux Menuires et faire 1 journée à Val Tho via la liaison."),
            ("🏘️ Authenticité de village", "Les Menuires",
             "Saint-Martin-de-Belleville (relié à ski) garde un charme de vieux village savoyard que Val Thorens, station d'altitude pure, n'a pas."),
        ],
        "verdict": (
            "Pas de gagnant universel : tout dépend de votre profil. "
            "<strong>Val Thorens</strong> est imbattable pour l'altitude, le grand ski et la fête. "
            "<strong>Les Menuires</strong> sont parfaites pour la famille, le budget et le charme du village. "
            "Astuce maligne : loger aux Menuires (moins cher) et profiter du domaine 3 Vallées commun."
        ),
        "faq": [
            ("Val Thorens ou Les Menuires : laquelle est la moins chère ?",
             "Les Menuires reste 25 à 35% moins chère que Val Thorens sur l'hébergement, avec un forfait 3 Vallées commun. En janvier hors vacances scolaires, on trouve des appartements à 350-450 € la semaine aux Menuires contre 600 € minimum à Val Thorens."),
            ("Peut-on skier dans tout le domaine des 3 Vallées depuis les deux stations ?",
             "Oui, avec un forfait 3 Vallées (600 km, 170 remontées), depuis Val Thorens comme depuis Les Menuires vous avez accès à Courchevel, Méribel, La Tania et toutes les stations du domaine. La liaison Menuires-Val Thorens prend une trentaine de minutes à ski."),
            ("Val Thorens est-elle vraiment la plus haute station d'Europe ?",
             "Oui, Val Thorens culmine à 2300 m avec un domaine montant jusqu'à 3230 m via la Cime Caron. C'est ce qui lui garantit un enneigement fiable de fin novembre à début mai."),
            ("Les Menuires sont-elles adaptées aux enfants débutants ?",
             "Très bien adaptées : label Espaces ludiques, grand front de neige doux côté La Croisette, plusieurs zones débutants et garderies. Val Thorens accueille aussi les familles mais l'altitude la rend moins évidente pour les tout-petits."),
        ],
    },
    {
        "a": "Avoriaz",
        "b": "Morzine",
        "img_a": "avoriaz1",
        "img_b": "morzine1",
        "teaser": (
            "Deux poids lourds des Portes du Soleil, deux philosophies opposées. "
            "Avoriaz, station piétonne à 1800 m, garantit la neige et le ski aux pieds. "
            "Morzine, village savoyard authentique à 1000 m, séduit par son charme toute l'année."
        ),
        "profils": [
            ("👨‍👩‍👧‍👦 Famille avec enfants en bas âge", "Avoriaz",
             "Station 100% piétonne — aucune voiture, hébergement skis aux pieds, traîneaux à cheval. Sécurité totale et logistique simplifiée."),
            ("🎿 Skieurs intermédiaires/confirmés", "Avoriaz",
             "Position centrale dans les Portes du Soleil (650 km), neige fiable à 1800 m, accès direct aux pistes mythiques (Hauts-Forts, Chavanette)."),
            ("🛹 Freestylers et riders", "Avoriaz",
             "Le Stash et Lil'Stash sont des références mondiales. Plusieurs zones freestyle au cœur du domaine."),
            ("🍷 Couples / non-skieurs / vie de village", "Morzine",
             "Vraie vie de village toute l'année : restaurants, cinéma, palais des sports, balades autour du lac de Montriond. Avoriaz est minérale et tournée 100% ski."),
            ("💰 Budget hébergement", "Morzine",
             "Hôtels et locations 20-30% moins chers qu'à Avoriaz pour un domaine skiable identique (le forfait Portes du Soleil est commun)."),
            ("🚗 Week-end depuis Genève", "Morzine",
             "1h depuis l'aéroport, accès rapide. Avoriaz demande de monter ensuite à la station via télécabine ou route fermée."),
        ],
        "verdict": (
            "<strong>Avoriaz</strong> est conçue pour les skieurs : piétonne, en altitude, ski aux pieds, snowpark de classe mondiale. "
            "<strong>Morzine</strong> est conçue pour les vacances : vraie vie de village, accessible, polyvalente. "
            "Bonne nouvelle : le domaine skiable est le même (650 km des Portes du Soleil), vous ne perdez rien à choisir l'une ou l'autre."
        ),
        "faq": [
            ("Morzine et Avoriaz partagent-elles le même domaine skiable ?",
             "Oui. Les deux donnent accès aux 650 km des Portes du Soleil, le domaine franco-suisse qui relie 12 stations dont Châtel, Les Gets, Champéry et Champoussin. Depuis Morzine, la télécabine du Pléney ou celle d'Avoriaz vous amènent au cœur du domaine en quelques minutes."),
            ("Avoriaz est-elle vraiment 100% piétonne ?",
             "Oui, totalement. Les voitures restent au parking en entrée de station, les déplacements se font à pied, en luge, en traîneau à chevaux ou en navette. C'est un atout majeur pour les familles avec enfants en bas âge."),
            ("Quelle station choisir si je ne suis pas skieur tous les jours ?",
             "Morzine sans hésiter. Le village vit toute l'année, propose de nombreux restaurants, des balades autour du lac de Montriond, un cinéma, un palais des sports avec patinoire et piscine. Avoriaz est moins agréable pour les non-skieurs."),
            ("Avoriaz est-elle adaptée aux débutants ?",
             "Oui, très bien. Grand espace débutants au cœur de la station et pistes vertes/bleues parfaitement adaptées. Les écoles ESF et internationale sont reconnues. Morzine fait aussi très bien le job côté débutants avec le Pléney."),
        ],
    },
    {
        "a": "Val d'Isère",
        "b": "Tignes",
        "img_a": "valdisere1",
        "img_b": "tignes1",
        "teaser": (
            "Le duo mythique de l'Espace Killy partage 300 km de pistes mais cultive deux identités farouches. "
            "Val d'Isère, village historique chic au cachet préservé. Tignes, station d'altitude moderne avec glacier."
        ),
        "profils": [
            ("✨ Voyageurs haut de gamme / gastronomes", "Val d'Isère",
             "Centre-village historique avec église baroque, palaces, tables étoilées (L'Atelier d'Edmond, La Table de l'Ours). Ambiance grand chic alpin."),
            ("🎿 Riders et amateurs de poudreuse", "Val d'Isère",
             "La Face de Bellevarde et les couloirs du Solaise sont des terrains de jeu mythiques. Plus de spots freeride engagés qu'à Tignes."),
            ("🏂 Freestylers et snowparkers", "Tignes",
             "Le snowpark de Tignes (Val Claret) est régulièrement classé parmi les meilleurs au monde — pros mondiaux y viennent s'entraîner."),
            ("☀️ Skieurs qui veulent skier longtemps", "Tignes",
             "Glacier de la Grande Motte ouvert d'octobre à mai. Val d'Isère ferme classiquement début mai."),
            ("💰 Budget plus accessible", "Tignes",
             "Tignes le Lac et Val Claret sont 15-25% moins chers que le centre de Val d'Isère pour un domaine commun (Espace Killy)."),
            ("👨‍👩‍👧‍👦 Famille avec jeunes enfants", "Val d'Isère",
             "Village plus à taille humaine, garderies de qualité, espaces débutants accessibles. Tignes est aussi familiale mais l'architecture moins chaleureuse."),
        ],
        "verdict": (
            "Aucune des deux ne gagne dans l'absolu : elles ciblent des profils différents. "
            "<strong>Val d'Isère</strong> est faite pour ceux qui veulent une expérience village haut de gamme, du freeride engagé et de la gastronomie. "
            "<strong>Tignes</strong> est faite pour ceux qui veulent skier longtemps, freestyler et payer moins cher."
        ),
        "faq": [
            ("Val d'Isère et Tignes partagent-elles le même forfait ?",
             "Oui, le forfait Espace Killy donne accès aux 300 km communs aux deux stations, incluant le glacier de la Grande Motte et le mythique Pisaillas."),
            ("Quelle station a le meilleur enneigement ?",
             "Les deux affichent un enneigement très fiable grâce à l'altitude (Val d'Isère 1850 m, Tignes 1550-2100 m). Tignes a l'avantage du glacier qui permet de skier d'octobre à mai."),
            ("Pour un freestyleur, laquelle choisir ?",
             "Tignes sans débat. Le snowpark de Tignes (Val Claret) est régulièrement classé parmi les meilleurs au monde, avec plusieurs lignes adaptées à tous les niveaux."),
            ("Tignes est-elle vraiment moins chic que Val d'Isère ?",
             "Architecturalement oui — Tignes a été construite dans les années 60-70. Val d'Isère a gardé son centre-village historique. Côté hôtellerie haut de gamme, les deux ont leurs palaces, mais Val d'Isère concentre plus de tables étoilées."),
        ],
    },
    {
        "a": "La Plagne",
        "b": "Les Arcs",
        "img_a": "laplagne1",
        "img_b": "lesarcs1",
        "teaser": (
            "Les deux mastodontes de Paradiski (425 km) sont reliés par le Vanoise Express, "
            "mais incarnent deux conceptions très différentes du ski."
        ),
        "profils": [
            ("👨‍👩‍👧‍👦 Famille avec jeunes enfants / débutants", "La Plagne",
             "L'archétype de la station familiale : domaine très progressif, hébergement ski aux pieds dans presque tous les villages, garderies omniprésentes."),
            ("🎿 Skieurs intermédiaires/confirmés cherchant du relief", "Les Arcs",
             "Pistes plus techniques, dénivelés marqués, descentes mythiques depuis l'Aiguille Rouge (3226 m → 1200 m à Villaroger)."),
            ("🏘️ Charme du village", "Les Arcs",
             "Arc 1950 est une vraie réussite architecturale : station piétonne récente en style village savoyard, sans voitures."),
            ("🛹 Freeride / hors-piste sérieux", "Les Arcs",
             "L'Aiguille Rouge offre du dénivelé impressionnant et des itinéraires engagés. La Plagne propose des hors-pistes plus accessibles."),
            ("🎪 Activités annexes / animation enfants", "La Plagne",
             "Piste de bobsleigh olympique, luge sur rail, animation jeunesse omniprésente. La Plagne est pensée pour les vacances complètes."),
            ("🏔️ Vue sur le Mont-Blanc", "Les Arcs",
             "Position et orientation permettent une vue spectaculaire sur le massif depuis les sommets — un argument photo non négligeable."),
        ],
        "verdict": (
            "<strong>La Plagne</strong> est le choix le plus sûr pour une famille avec enfants ou des skieurs débutants. "
            "<strong>Les Arcs</strong> conviennent mieux à des skieurs déjà autonomes qui cherchent du relief, du caractère architectural et un peu plus de gros ski. "
            "Le bonus : le forfait Paradiski permet d'explorer les deux via le Vanoise Express."
        ),
        "faq": [
            ("La Plagne et Les Arcs sont-elles reliées à ski ?",
             "Oui, via le Vanoise Express, télécabine impressionnante (1800 m de portée) qui relie les deux domaines en 4 minutes. L'ensemble forme Paradiski, 3e plus grand domaine skiable du monde avec 425 km de pistes."),
            ("Quelle station choisir pour une première semaine de ski ?",
             "La Plagne, sans hésiter. Plagne Centre ou Belle Plagne sont conçues pour les débutants : front de neige adapté, tapis roulants, écoles ESF nombreuses."),
            ("Arc 1950 vaut-elle le détour ?",
             "Oui, c'est une réussite architecturale rare : station piétonne récente conçue dans un style village savoyard contemporain, sans voitures dans les rues, avec une vraie âme."),
            ("Quel est le meilleur ski hors-piste, La Plagne ou Les Arcs ?",
             "Les Arcs prennent l'avantage avec l'Aiguille Rouge (3226 m) et ses descentes vers Villaroger ou Le Pré qui offrent un dénivelé impressionnant."),
        ],
    },
    {
        "a": "Alpe d'Huez",
        "b": "Les Deux Alpes",
        "img_a": "alpedhuez1",
        "img_b": "lesdeuxalpes1",
        "teaser": (
            "Les deux stars de l'Oisans, à 30 km à vol d'oiseau, s'opposent presque en tout. "
            "L'Alpe d'Huez mise sur le soleil et la famille. Les Deux Alpes sur le glacier et l'after-ski."
        ),
        "profils": [
            ("👨‍👩‍👧‍👦 Famille équilibrée", "Alpe d'Huez",
             "Label Famille Plus, grand domaine progressif, 300 jours de soleil par an, plus d'animations enfants. La station idéale pour une semaine sans stress."),
            ("☀️ Skieurs qui détestent le froid", "Alpe d'Huez",
             "L'ensoleillement record (record en France) rend les journées beaucoup plus agréables. Les Deux Alpes, plus encaissée, voit moins le soleil."),
            ("🏂 Freestylers", "Les Deux Alpes",
             "Le snowpark perché sur le glacier est l'une des références mondiales, ouvert hiver ET été. Les pros y viennent."),
            ("🎉 Ambiance jeune / fêtard", "Les Deux Alpes",
             "Vie de soirée intense, public plus jeune, bars qui ferment tard. L'Alpe d'Huez est plus posée."),
            ("☃️ Ski d'été", "Les Deux Alpes",
             "Le plus grand glacier skiable d'Europe accessible l'été (mi-juin à fin août). L'Alpe d'Huez ferme son glacier de Sarenne en avril."),
            ("🏔️ Skieurs expérimentés cherchant LA descente", "Alpe d'Huez",
             "La Sarenne : 16 km depuis le Pic Blanc (3330 m), la plus longue piste noire d'Europe. Une expérience à vivre."),
        ],
        "verdict": (
            "<strong>L'Alpe d'Huez</strong> est l'option famille équilibrée : soleil garanti, domaine large, label Famille Plus. "
            "<strong>Les Deux Alpes</strong> attirent les freestyleurs, les amateurs de ski sur glacier et les fêtards. "
            "Pas besoin de choisir si vous y allez en été — seule Les Deux Alpes a son glacier ouvert."
        ),
        "faq": [
            ("Peut-on skier entre l'Alpe d'Huez et Les Deux Alpes ?",
             "Une liaison à skis via le col du Lac Blanc existe mais n'est plus opérationnelle de façon fiable depuis plusieurs années. Concrètement, on choisit l'une ou l'autre. Une navette routière permet de passer de l'une à l'autre en 1h-1h30."),
            ("Quelle station a le meilleur snowpark ?",
             "Les Deux Alpes, c'est même l'une de ses signatures. Le snowpark, perché sur le glacier, fonctionne en hiver comme en été et accueille régulièrement les pros mondiaux."),
            ("La piste de la Sarenne est-elle vraiment la plus longue noire d'Europe ?",
             "Oui, 16 km depuis le Pic Blanc (3330 m) jusqu'à Sarenne, soit 2 000 m de dénivelé. Attention, malgré son label noire, la majorité du parcours est rouge — accessible à un bon skieur."),
            ("Peut-on skier sur le glacier des Deux Alpes en été ?",
             "Oui, c'est le plus grand glacier skiable d'Europe accessible l'été (de mi-juin à fin août en général). Idéal pour les amateurs de ski estival et les stages de freestyle."),
        ],
    },

    # ── NOUVEAUX COMPARATIFS ──────────────────────────────────────────────

    {
        "a": "Super Besse",
        "b": "Le Lioran",
        "img_a": "superbesse1",
        "img_b": "lelioran1",
        "teaser": (
            "Le duel des deux poids lourds du Massif Central. Super Besse au cœur du Sancy, animée et familiale. "
            "Le Lioran face au Plomb du Cantal, plus grand domaine d'Auvergne et ambiance volcan brut."
        ),
        "profils": [
            ("👨‍👩‍👧‍👦 Famille avec enfants débutants", "Super Besse",
             "Front de neige large, plusieurs espaces ludiques, école ESF active, animations enfants au village (lac, luge, raquettes). Côté logistique, c'est plus simple."),
            ("🎿 Skieurs cherchant un vrai domaine en Massif Central", "Le Lioran",
             "60 km de pistes, le plus grand d'Auvergne. Domaine plus varié et plus vaste que Super Besse (43 km)."),
            ("🌋 Authenticité auvergnate / paysages volcaniques", "Le Lioran",
             "Vue spectaculaire sur le Plomb du Cantal et le Puy Mary, ambiance plus brute et préservée. Super Besse est plus station, Le Lioran plus montagne."),
            ("🚗 Week-end depuis Clermont / Lyon / Paris", "Super Besse",
             "Accès Clermont en 1h, Lyon en 3h, Paris en 5h. Le Lioran est 1h plus loin de Clermont (Sud Cantal)."),
            ("❄️ Enneigement le plus fiable", "Le Lioran",
             "Position plus élevée (1255-1850 m vs 1300-1850 m pour Besse) et exposition nord. Le Lioran tient en général un peu mieux la neige en milieu de saison."),
            ("🎉 Animation / vie de station le soir", "Super Besse",
             "Plus de bars, restaurants et animations en soirée. Le Lioran est très calme une fois les remontées fermées."),
        ],
        "verdict": (
            "<strong>Super Besse</strong> est le bon choix pour une famille en week-end ou pour ceux qui veulent une station vivante et bien équipée. "
            "<strong>Le Lioran</strong> séduira les skieurs autonomes qui cherchent un vrai domaine, des paysages volcaniques et une ambiance plus authentique. "
            "Pour un séjour découverte du Massif Central, l'idéal est de combiner les deux : 4 jours à Besse, 2 jours au Lioran."
        ),
        "faq": [
            ("Super Besse ou Le Lioran : quel est le plus grand domaine ?",
             "Le Lioran, avec 60 km de pistes, est le plus grand domaine skiable du Massif Central. Super Besse propose environ 43 km de pistes — un domaine respectable mais plus petit."),
            ("Quelle station est la plus accessible depuis Paris ou Lyon ?",
             "Super Besse est plus proche : environ 5h depuis Paris et 3h depuis Lyon. Le Lioran ajoute ~1h supplémentaire car situé plus au sud dans le Cantal."),
            ("L'enneigement est-il fiable au Lioran et à Super Besse ?",
             "Les deux stations bénéficient d'une bonne enneigement de mi-décembre à mi-mars en saison normale, avec un avantage léger au Lioran (altitude légèrement supérieure et exposition nord). Les deux disposent également de canons à neige pour sécuriser le bas du domaine."),
            ("Quelle station choisir pour des enfants qui apprennent à skier ?",
             "Super Besse a un léger avantage : front de neige plus large, plus d'espaces ludiques visibles, et une école ESF particulièrement active sur les cours enfants. Mais Le Lioran propose aussi de très bonnes structures débutants côté Font d'Alagnon."),
        ],
    },
    {
        "a": "Chamonix",
        "b": "Megève",
        "img_a": "chamonix1",
        "img_b": "megeve1",
        "teaser": (
            "Deux légendes de la Haute-Savoie au pied du Mont-Blanc, mais deux mondes opposés. "
            "Chamonix, capitale mondiale de l'alpinisme, brute et engagée. Megève, village chic et raffiné lancé par les Rothschild dans les années 20."
        ),
        "profils": [
            ("🏔️ Skieurs experts / freeriders", "Chamonix",
             "La Vallée Blanche, les Grands Montets, le Brévent : terrain de jeu mythique pour le ski engagé. Megève est ludique mais sans le même grand frisson."),
            ("✨ Voyageurs haut de gamme / luxe discret", "Megève",
             "Architecture village préservée, palaces (Les Fermes de Marie, Le Chalet du Mont d'Arbois), gastronomie étoilée. Chic à l'ancienne sans ostentation."),
            ("👨‍👩‍👧‍👦 Famille avec enfants", "Megève",
             "Domaine plus accessible, espaces débutants pléthoriques, ambiance posée. Chamonix est plus rude pour les jeunes enfants."),
            ("🍷 Gastronomie de haut niveau", "Megève",
             "Plusieurs étoilés Michelin (Flocons de Sel, La Table de l'Alpaga), tradition gastronomique forte. Chamonix a aussi de bonnes tables mais moins d'étoilés."),
            ("⛰️ Ambiance montagne authentique / aventure", "Chamonix",
             "Capitale mondiale de l'alpinisme, ambiance bigarrée, internationale, énergie unique. C'est de la vraie haute montagne."),
            ("🚗 Accès depuis Genève (1h)", "Chamonix",
             "1h depuis Genève en voiture, accès TGV via Saint-Gervais. Megève est aussi accessible mais demande un peu plus de route depuis l'aéroport."),
        ],
        "verdict": (
            "<strong>Chamonix</strong> est faite pour les skieurs qui veulent vivre la haute montagne et le ski engagé. "
            "<strong>Megève</strong> est faite pour ceux qui cherchent un séjour chic, gastronomique et reposant. "
            "Les deux sont d'excellentes destinations, mais elles attirent des publics différents — choisissez selon votre humeur de vacances."
        ),
        "faq": [
            ("Chamonix et Megève partagent-elles un forfait commun ?",
             "Le forfait Mont-Blanc Unlimited de Chamonix couvre tout son domaine (Brévent-Flégère, Grands Montets, Aiguille du Midi, Les Houches) plus quelques bonus comme Courmayeur. Megève fait partie du domaine Évasion Mont-Blanc (Megève, Saint-Gervais, Combloux, La Giettaz) : c'est un forfait distinct."),
            ("Quelle station est adaptée aux débutants ?",
             "Megève sans hésiter. Le domaine du Mont d'Arbois et de Rochebrune propose de nombreuses pistes bleues et vertes parfaitement adaptées. Chamonix a des espaces débutants à Brévent ou Planards, mais l'esprit général de la vallée est plutôt orienté ski engagé."),
            ("Peut-on faire la Vallée Blanche en famille ?",
             "Non, la Vallée Blanche est une descente glaciaire de 20 km au cœur d'un environnement de haute montagne, qui nécessite un guide et une expérience minimum en ski. C'est l'expérience emblématique de Chamonix mais réservée à un public confirmé."),
            ("Megève est-elle vraiment chère ?",
             "Sur le très haut de gamme (palaces, étoilés), oui — Megève est dans le club fermé des stations les plus chères de France. Mais on trouve aussi des hébergements abordables en location, et les forfaits sont moins chers qu'à Val d'Isère ou Courchevel."),
        ],
    },
    {
        "a": "Courchevel",
        "b": "Méribel",
        "img_a": "courchevel1",
        "img_b": "meribel1",
        "teaser": (
            "Les deux sœurs des 3 Vallées, distantes de quelques kilomètres et reliées à ski, "
            "incarnent deux visions différentes du luxe. Courchevel 1850, vitrine ultra-chic. Méribel, sa version plus chaleureuse."
        ),
        "profils": [
            ("💎 Luxe absolu / jet-set", "Courchevel",
             "Courchevel 1850 concentre la plus haute densité de palaces et étoilés Michelin des Alpes. Architecture, boutiques, restaurants : du très haut de gamme."),
            ("🏡 Famille aisée cherchant un chalet authentique", "Méribel",
             "Charte architecturale stricte en bois, chalets de standing dans un cadre plus chaleureux et naturel. Plus accessible que Courchevel 1850 sans sacrifier le standing."),
            ("🎿 Position centrale dans les 3 Vallées", "Méribel",
             "Méribel est littéralement au cœur des 3 Vallées : on accède partout en quelques télécabines (Val Thorens, Courchevel, La Tania). Idéal pour explorer le grand domaine."),
            ("🍷 Gastronomie étoilée Michelin", "Courchevel",
             "Plusieurs étoilés (Le 1947 chez Yannick Alléno, Le Chabichou, Le Sarkara). Méribel a quelques bonnes tables mais reste moins étoilée."),
            ("👨‍👩‍👧‍👦 Famille avec enfants", "Méribel",
             "Méribel-Mottaret et Méribel Centre offrent des fronts de neige doux, écoles ESF actives et un domaine progressif. Courchevel 1650 ou 1550 sont aussi très bien pour les familles, mais le 1850 est moins évident."),
            ("💼 Stations plus accessibles côté budget", "Méribel",
             "Méribel reste haut de gamme mais ses hébergements 4* et locations sont 20-40% moins chers qu'à Courchevel 1850."),
        ],
        "verdict": (
            "<strong>Courchevel</strong> est faite pour qui veut le luxe assumé, la gastronomie étoilée et le statut. "
            "<strong>Méribel</strong> est faite pour qui veut un séjour haut de gamme dans un cadre plus chaleureux et naturel, idéalement placé dans les 3 Vallées. "
            "Bonne nouvelle : les deux partagent le même domaine de 600 km, vous ne perdez rien à choisir l'une ou l'autre."
        ),
        "faq": [
            ("Courchevel et Méribel partagent-elles le même domaine ?",
             "Oui, les deux sont au cœur des 3 Vallées (600 km, 170 remontées). Avec un forfait 3 Vallées, vous accédez à l'ensemble du domaine incluant Val Thorens, Les Menuires, La Tania et Saint-Martin-de-Belleville."),
            ("Courchevel est-elle vraiment réservée aux riches ?",
             "Courchevel a 4 niveaux d'altitude (1300, 1550, 1650, 1850), et le 1850 est effectivement très haut de gamme. Mais Courchevel 1550 (Le Praz) ou 1300 (Saint-Bon) sont beaucoup plus accessibles, avec des locations à des prix raisonnables."),
            ("Quel est le meilleur point central pour explorer les 3 Vallées ?",
             "Méribel sans hésiter. Sa position géographique permet de rayonner facilement vers Val Thorens (30 min à ski) comme vers Courchevel (15 min), ce qui en fait la base idéale pour skier l'ensemble du domaine."),
            ("Méribel est-elle adaptée aux familles ?",
             "Très bien adaptée. Méribel-Mottaret et Méribel Centre disposent de fronts de neige doux, d'écoles ESF actives et de garderies. La station a une vraie culture famille, particulièrement à Méribel-Village ou aux Allues."),
        ],
    },
    {
        "a": "La Clusaz",
        "b": "Le Grand-Bornand",
        "img_a": "laclusaz1",
        "img_b": "legrandbornand1",
        "teaser": (
            "Les deux pépites des Aravis, à 10 km l'une de l'autre, jouent la carte du village savoyard authentique. "
            "La Clusaz, plus sportive et caractérielle. Le Grand-Bornand, ultra-familial et serein."
        ),
        "profils": [
            ("👨‍👩‍👧‍👦 Famille avec jeunes enfants", "Le Grand-Bornand",
             "Label Famille Plus, fronts de neige doux et nombreux, espaces ludiques omniprésents, ambiance ultra-tranquille. Référence française pour le ski en famille."),
            ("🎿 Skieurs intermédiaires/confirmés", "La Clusaz",
             "Domaine plus varié (132 km vs 90 km), pistes plus techniques, accès au massif de l'Aiguille et au Beauregard. Plus de relief et de challenge."),
            ("🏘️ Charme du village savoyard", "La Clusaz",
             "Village classé, architecture traditionnelle préservée, animation en cœur de station. Le Grand-Bornand est joli aussi mais plus dispersé."),
            ("🏂 Freestyle / freeride accessible", "La Clusaz",
             "Snowpark de référence (Les Confins), plus de spots hors-piste et zones freeride accessibles. Le Grand-Bornand est plus orienté piste tracée."),
            ("🚗 Week-end depuis Lyon / Genève", "Le Grand-Bornand",
             "Position plus accessible depuis Annecy, parking et logistique plus simples. La Clusaz est plus encaissée."),
            ("🌄 Calme et nature préservée", "Le Grand-Bornand",
             "Le village s'étire dans une grande vallée, ambiance pastorale, moins de monde sur les pistes en semaine."),
        ],
        "verdict": (
            "<strong>Le Grand-Bornand</strong> est probablement la meilleure station française pour skier en famille avec de jeunes enfants. "
            "<strong>La Clusaz</strong> conviendra mieux à des skieurs déjà autonomes qui cherchent un peu plus de relief et de caractère. "
            "Astuce : le forfait Aravis permet de skier sur les deux stations, ce qui peut être malin sur un séjour d'une semaine."
        ),
        "faq": [
            ("La Clusaz et Le Grand-Bornand sont-elles reliées à ski ?",
             "Non, les deux stations ne sont pas reliées directement à ski. Une navette gratuite relie les deux villages (15 min de route), ce qui permet de skier sur les deux avec le forfait commun Aravis."),
            ("Quelle station choisir avec de très jeunes enfants ?",
             "Le Grand-Bornand sans hésiter. Le front de neige du Chinaillon est large, doux et progressif. La station est labellisée Famille Plus et propose des espaces ludiques exceptionnels, des garderies de qualité et une ambiance ultra-calme."),
            ("La Clusaz a-t-elle un domaine adapté aux skieurs confirmés ?",
             "Oui, c'est même un de ses atouts dans les Aravis. Le domaine de l'Étale, du Massif de l'Aiguille et de Beauregard offre 132 km variés, avec des pistes techniques et des zones freeride accessibles depuis le sommet."),
            ("L'enneigement est-il fiable dans les Aravis ?",
             "C'est leur petit point faible : les Aravis sont à altitude modérée (1100-2600 m). Les saisons varient, et le bas du domaine peut souffrir en milieu de saison douce. Les deux stations disposent de canons à neige bien équipés pour sécuriser le retour station."),
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

.profil-grid {{
  display:grid; grid-template-columns:1fr; gap:12px;
}}
.profil-card {{
  background:#fff; border:1px solid var(--border); border-radius:var(--radius);
  padding:18px 22px; box-shadow:var(--shadow);
  border-left:4px solid var(--wood-dark);
}}
.profil-head {{
  display:flex; align-items:center; justify-content:space-between; gap:14px;
  margin-bottom:6px; flex-wrap:wrap;
}}
.profil-label {{
  font-weight:700; color:var(--text); font-size:1rem;
}}
.profil-pick {{
  background:var(--wood-pale); color:var(--wood-dark);
  padding:5px 12px; border-radius:14px; font-weight:700;
  font-size:.88rem; white-space:nowrap;
}}
.profil-pick::before {{ content:"→ "; opacity:.6; }}
.profil-reason {{
  color:var(--text-mid); font-size:.93rem; margin:0; line-height:1.55;
}}

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
  display:block; text-align:center; margin-top:10px; font-size:.88rem;
  color:var(--blue-dark); text-decoration:none; font-weight:600;
}}
.detail-link:hover {{ text-decoration:underline; }}
.officiel-link {{
  display:block; text-align:center; margin-top:12px; padding:9px 14px;
  background:var(--wood-pale); color:var(--wood-dark); border-radius:10px;
  font-size:.88rem; font-weight:700; text-decoration:none;
  border:1px solid var(--wood-light);
  transition:background .15s;
}}
.officiel-link:hover {{ background:var(--wood-light); }}
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
    <img src="/img/{img_a}.jpg" alt="{a}" loading="eager"
         onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=800&q=80'">
    <div class="tag">{a}</div>
  </div>
  <div class="hero-card">
    <img src="/img/{img_b}.jpg" alt="{b}" loading="eager"
         onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1483921020237-2ff51e8e4b22?w=800&q=80'">
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

<h2>👤 Pour quel profil quelle station ?</h2>
<div class="profil-grid">
{profil_rows}
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
      <a href="{officiel_a}" target="_blank" rel="noopener" class="officiel-link">🎿 Site officiel de {a}</a>
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
      <a href="{officiel_b}" target="_blank" rel="noopener" class="officiel-link">🎿 Site officiel de {b}</a>
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


def render_profils(profils_list: list) -> str:
    """Renders the persona-based recommendation cards."""
    return "\n".join(
        f'<div class="profil-card">'
        f'<div class="profil-head"><div class="profil-label">{label}</div>'
        f'<div class="profil-pick">{pick}</div></div>'
        f'<p class="profil-reason">{reason}</p>'
        f'</div>'
        for label, pick, reason in profils_list
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
        profil_rows=render_profils(comp["profils"]),
        officiel_a=official_url(a), officiel_b=official_url(b),
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
                <img src="/img/{c["img_a"]}.jpg" alt="{c["a"]}" loading="lazy"
                     onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=600&q=80'">
                <img src="/img/{c["img_b"]}.jpg" alt="{c["b"]}" loading="lazy"
                     onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1483921020237-2ff51e8e4b22?w=600&q=80'">
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
  <h1>Comparatifs : quelle station pour quel profil ?</h1>
  <p class="lead">Hésitation entre deux stations ? Nos comparatifs vous aident à trancher selon votre profil : famille, sportif, fêtard, budget, débutant…</p>
  <div class="grid">
{cards}
  </div>
</main>
</body>
</html>
"""


# ── Snippet à insérer dans index.html ────────────────────────────────────────

def build_snippet(comparaisons_meta: list) -> str:
    """
    Génère un snippet compact pour l'index.html.
    On limite à 4 cartes (les plus populaires) + lien "Voir tous les comparatifs".
    """
    # 4 premières comparaisons = les plus populaires (Val Tho/Menuires, Avoriaz/Morzine, Val d'Isère/Tignes, La Plagne/Les Arcs)
    featured = comparaisons_meta[:4]
    total = len(comparaisons_meta)

    cards = "\n".join(
        f'''  <a href="/comparatifs/{slug}.html" class="comparatif-card">
    <div class="comparatif-imgs">
      <img src="/img/{c["img_a"]}.jpg" alt="{c["a"]}" loading="lazy"
           onerror="this.onerror=null;this.src=\'https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=600&q=80\'">
      <img src="/img/{c["img_b"]}.jpg" alt="{c["b"]}" loading="lazy"
           onerror="this.onerror=null;this.src=\'https://images.unsplash.com/photo-1483921020237-2ff51e8e4b22?w=600&q=80\'">
    </div>
    <div class="comparatif-body">
      <div class="comparatif-title">{c["a"]} <span class="vs">vs</span> {c["b"]}</div>
    </div>
  </a>'''
        for slug, c in featured
    )

    return f"""<!-- ═════════════════════════════════════════════════════════════════════
     Section "Comparatifs" — version compacte pour index.html
     ═════════════════════════════════════════════════════════════════════ -->

<style>
.comparatif-section {{ max-width:1100px; margin:48px auto; padding:0 20px; }}
.comparatif-section h2 {{
  font-family:"DM Serif Display",serif; font-size:1.7rem;
  margin:0 0 4px; color:var(--text,#2a1f14);
}}
.comparatif-section .comparatif-lead {{
  color:var(--text-light,#8a7060); margin-bottom:20px; font-size:.95rem;
}}
.comparatif-grid {{
  display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:14px;
}}
.comparatif-card {{
  background:#fff; border:1px solid var(--border,#e8d8c4); border-radius:12px;
  overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,.08); text-decoration:none;
  color:inherit; transition:transform .15s, box-shadow .15s; display:flex; flex-direction:column;
}}
.comparatif-card:hover {{ transform:translateY(-3px); box-shadow:0 6px 20px rgba(0,0,0,.12); }}
.comparatif-imgs {{
  display:grid; grid-template-columns:1fr 1fr;
  height:100px; min-height:100px; max-height:100px;
  overflow:hidden; background:#eddcbf; flex-shrink:0;
}}
.comparatif-imgs img {{
  width:100%; height:100px; object-fit:cover; display:block; background:#eddcbf;
}}
.comparatif-body {{ padding:11px 14px; background:#fff; }}
.comparatif-title {{ font-family:"DM Serif Display",serif; font-size:1rem; color:#2a1f14; line-height:1.25; }}
.comparatif-title .vs {{ color:#8b5e3c; font-style:italic; font-size:.8rem; padding:0 3px; }}
.comparatif-section .all-link {{
  display:inline-block; margin-top:18px; color:#8b5e3c;
  font-weight:600; text-decoration:none; font-size:.95rem;
}}
.comparatif-section .all-link:hover {{ text-decoration:underline; }}
</style>

<section class="comparatif-section">
  <h2>Comparatifs : quelle station pour quel profil ?</h2>
  <p class="comparatif-lead">Nos guides détaillés pour vous aider à trancher selon votre profil de skieur.</p>
  <div class="comparatif-grid">
{cards}
  </div>
  <a href="/comparatifs/" class="all-link">Voir nos {total} comparatifs →</a>
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
