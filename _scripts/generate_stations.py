#!/usr/bin/env python3
"""
SnowFinder — Générateur de pages statiques par station
=======================================================
Modifiez la fonction render_page() pour changer le design
de toutes les pages stations d'un coup.

Déclenchement automatique via GitHub Actions quand recherche.html change.
Ou manuellement : python3 _scripts/generate_stations.py
"""
import re, json, unicodedata, os, sys, hashlib

def slugify(name):
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')

BOOKING_CJ = 'https://www.tkqlhce.com/click-101709262-15734710'  # Booking.com via CJ

# ── PHOTOS PLACEHOLDER UNSPLASH (libres de droits) ──
# Utilisées UNIQUEMENT pour les stations sans photo locale uploadée dans img/.
# Les photos locales (valthorens1.jpg, etc.) restent prioritaires.
# Sélection déterministe par hash MD5 du nom de station :
# chaque station sans photo aura toujours le même placeholder, mais l'ensemble
# est réparti uniformément sur les 9 URLs ci-dessous.
PLACEHOLDER_URLS_ALPES_PYRENEES = [
    "https://images.unsplash.com/photo-1483921020237-2ff51e8e4b22",  # Lauterbrunnen, Suisse - forêt + montagnes
    "https://images.unsplash.com/photo-1551698618-1dfe5d97d256",     # Autriche - skieur en piste
    "https://images.unsplash.com/photo-1528659862616-22886eb53642",  # Dragobrat, Ukraine - téléphérique hiver
    "https://images.unsplash.com/photo-1551524559-8af4e6624178",     # Snowboardeur - veste marron
    "https://images.unsplash.com/photo-1482867996988-29ec3a0f1aac",  # Kastelruth, Italie - téléphérique champ enneigé
    "https://images.unsplash.com/photo-1731445289819-ed2efbdb9d83",  # Vail, USA - montagne enneigée ciel rose
    "https://images.unsplash.com/photo-1551036359-aaa8fdf6314b",     # Méribel, France - montagnes heure dorée
    "https://images.unsplash.com/photo-1588932716589-909fd383d64a",  # Hauteluce, France - montagne ciel bleu
    "https://images.unsplash.com/photo-1579525006336-c8919e3dc770",  # La Clusaz, France - station de ski
]

PLACEHOLDER_URLS_AUTRES_MASSIFS = [
    "https://images.unsplash.com/photo-1641886378875-b05544457b6a",  # Lélex, France (Jura) - skieur sur pente enneigée
    "https://images.unsplash.com/photo-1672588337559-d2ce3ad82682",  # Lettonie - paysage enneigé, arbres, ciel bleu
    "https://images.unsplash.com/photo-1612099452850-ed8efe7d58ff",  # Arbres enneigés en pleine journée
    "https://images.unsplash.com/photo-1517035993793-ab229c7faf72",  # Jura - pins enneigés, vue aérienne
    "https://images.unsplash.com/photo-1714036983985-6f6906043ba6",  # Corse - montagne enneigée près d'une forêt
    "https://images.unsplash.com/photo-1644281264389-ba63575e4c1c",  # Roumanie - montagne enneigée, forêt en arrière-plan
    "https://images.unsplash.com/photo-1490008446666-6c0841b7c060",  # Photo aérienne de pins enneigés
    "https://images.unsplash.com/photo-1701614753266-9ad5ba4f86ad",  # Tchéquie - paysage enneigé, arbres, soleil
    "https://images.unsplash.com/photo-1490701838674-320383cf293a",  # Roumanie - pins enneigés sur la montagne
    "https://images.unsplash.com/photo-1622139673657-13ba4a23918a",  # Serbie - champ enneigé et arbres
    "https://images.unsplash.com/photo-1748075048085-ed1910c3a8cc",  # Forêt-Noire, Allemagne - paysage enneigé, ciel nuageux
]

# Massifs considérés comme "Alpes/Pyrénées" (valeurs exactes du champ 'massif' dans DATA/DOMAINES)
MASSIFS_ALPES_PYRENEES = {"Alpes du Nord", "Alpes du Sud", "Pyrénées"}

def pick_placeholder(name, massif=None, w=1200):
    """Sélection déterministe d'une URL placeholder Unsplash via hash MD5 du nom.
    Chaque station/domaine sans photo locale aura toujours le même placeholder.
    Le pool utilisé dépend du massif : Alpes/Pyrénées piochent dans les 9 photos
    d'origine, tous les autres massifs (Jura, Vosges, Massif Central, Corse...)
    piochent dans le pool de 11 photos dédié."""
    pool = PLACEHOLDER_URLS_ALPES_PYRENEES if massif in MASSIFS_ALPES_PYRENEES else PLACEHOLDER_URLS_AUTRES_MASSIFS
    idx = int(hashlib.md5(name.encode('utf-8')).hexdigest(), 16) % len(pool)
    return f"{pool[idx]}?w={w}&q=80"

NIV = {"debutant":"Débutant","intermediaire":"Intermédiaire","avance":"Avancé","expert":"Expert"}
AMB = {"luxe":"Luxe","festif":"Festif","famille":"Famille","nature":"Nature","village":"Village","avance":"Technique","soleil":"Ensoleillé"}
EQ  = {"snowpark":"Snowpark","garderie":"Garderie","restaurants":"Restaurants","telesiege":"Télésiège"}

# ══════════════════════════════════════════════════════════════════
# GRANDS DOMAINES SKIABLES RELIÉS — un domaine = plusieurs stations
# connectées par les remontées mécaniques, sous un forfait commun.
# Chiffres vérifiés (sites officiels, recoupés) — saison 2025-2026.
# 'stations' utilise les noms EXACTS du champ "name" dans DATA.
# 'km_propre' donne, quand connu, le kilométrage propre à CHAQUE
# station membre (par opposition à s['km'] qui peut encore, tant que
# les fiches n'ont pas été auditées une à une, contenir le chiffre du
# domaine entier — c'est précisément ce que ce dictionnaire corrige).
# ══════════════════════════════════════════════════════════════════
DOMAINES = {
    "portes-du-soleil": {
        "name": "Les Portes du Soleil", "massif": "Alpes du Nord",
        "pays": ["France", "Suisse"],
        "stations": ["Avoriaz","Morzine","Montriond","Les Gets","Saint-Jean-d'Aulps","Abondance","La Chapelle d'Abondance","Châtel"],
        "km_propre": {"Avoriaz":80,"Morzine":50,"Les Gets":120,"Châtel":85,
                       "Montriond":15,"Saint-Jean-d'Aulps":40,"Abondance":25,"La Chapelle d'Abondance":40},
        "remontees_propre": {"Avoriaz":36},
        "alt_max_propre": {"Avoriaz":2200},
        "km_total": 600, "remontees_total": 197, "forfait_domaine": 58,
        "alt_min": 930, "alt_max": 2466,
        "pistes": {"v":80,"b":173,"r":103,"n":44},
        "short": "Portes du Soleil",
        "desc": "Douze stations, deux pays, un seul forfait : les Portes du Soleil sont nées en 1964 d'une poignée de maires français et suisses qui ont eu l'idée un peu folle de relier leurs villages par-dessus la frontière. Le résultat tient de l'aire de jeu géante — on part d'Avoriaz le matin, on déjeune en Suisse, on rentre par Châtel le soir sans jamais déchausser. Le domaine est plus rural que ses voisins savoyards : beaucoup de pistes en forêt, des villages qui ont gardé leur clocher et leurs fermes, et le fameux Mur suisse à Chavanette pour ceux qui aiment se faire peur. Attention, tout n'est pas relié à 100 % skis aux pieds : quelques navettes complètent le maillage.",
    },
    "3-vallees": {
        "name": "Les 3 Vallées", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["Courchevel","La Tania","Méribel","Brides-les-Bains","Saint-Martin-de-Belleville","Les Menuires","Val Thorens","Orelle"],
        "km_propre": {"Val Thorens":150,"Les Menuires":160,"Méribel":160,"Courchevel":150,"Saint-Martin-de-Belleville":40,"La Tania":25,"Orelle":35,"Brides-les-Bains":10},
        "km_total": 600, "remontees_total": 170, "forfait_domaine": 82,
        "alt_min": 1100, "alt_max": 3230,
        "pistes": {"v":55,"b":178,"r":113,"n":54},
        "short": "Les 3 Vallées",
        "desc": "Le plus grand domaine skiable du monde, et ce n'est pas un slogan : 600 km de pistes qui s'enchaînent sans jamais reprendre la voiture, de Courchevel à Val Thorens en passant par Méribel et Les Menuires. Trois vallées à l'origine — Saint-Bon, Allues, Belleville — auxquelles s'est greffée Orelle côté Maurienne. C'est le royaume du ski d'altitude : Val Thorens culmine à 2300 m au village, la Cime Caron dépasse 3200 m, et la neige tient de novembre à mai. Chaque station a sa personnalité tranchée, du luxe assumé de Courchevel 1850 à l'esprit familial des Menuires. Prévoir plusieurs jours : personne ne fait le tour du domaine en une journée.",
    },
    "espace-killy": {
        "name": "Tignes – Val d'Isère (Espace Killy)", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["Val d'Isère","Tignes"],
        "km_propre": {"Val d'Isère":150,"Tignes":150},
        "km_total": 300, "remontees_total": 91, "forfait_domaine": 75,
        "alt_min": 1550, "alt_max": 3456,
        "pistes": {"v":8,"b":41,"r":70,"n":36},
        "short": "Tignes – Val d'Isère",
        "desc": "Tignes et Val d'Isère, réunies depuis 1965 par le col de Fresse, forment ce que les anciens appellent encore l'Espace Killy — hommage à Jean-Claude Killy, triple médaillé d'or à Grenoble en 1968 et enfant de Val. C'est le domaine des puristes : altitude élevée du bas jusqu'en haut, glacier de la Grande Motte skiable jusqu'à 3456 m, enneigement quasi garanti d'octobre à mai. Les deux stations se complètent plus qu'elles ne se ressemblent : Val d'Isère a le charme d'un vrai village savoyard et une réputation de station chic, Tignes assume son architecture des années 60 et son ambiance sportive. Le hors-piste y est parmi les plus réputés d'Europe.",
    },
    "paradiski": {
        "name": "Paradiski", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["La Plagne","Les Arcs","Peisey-Vallandry","Montchavin-Les Coches"],
        "km_propre": {"La Plagne":225,"Les Arcs":200,"Peisey-Vallandry":60,"Montchavin-Les Coches":35},
        "km_total": 425, "remontees_total": 160, "forfait_domaine": 68,
        "alt_min": 1200, "alt_max": 3250,
        "pistes": {"v":30,"b":102,"r":62,"n":28},
        "short": "Paradiski",
        "desc": "La Plagne et Les Arcs se regardaient depuis toujours de part et d'autre de la vallée sans pouvoir se rejoindre. En 2003, le Vanoise Express a réglé le problème : deux cabines de 200 places qui traversent 1,8 km de vide en quatre minutes, l'un des plus grands téléphériques du monde. D'un coup, 425 km de pistes reliées. Les deux stations gardent des identités très différentes — La Plagne éclatée en dix villages de 1250 à 2100 m, Les Arcs alignées sur un versant en balcon face au Mont-Blanc. Peisey-Vallandry, au pied du téléphérique, est le trait d'union discret et boisé entre les deux.",
    },
    "grand-massif": {
        "name": "Le Grand Massif", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["Flaine","Les Carroz","Morillon","Samoëns","Sixt-Fer-à-Cheval"],
        "km_propre": {"Flaine":145,"Samoëns":40,"Les Carroz":45,"Morillon":35,"Sixt-Fer-à-Cheval":15},
        "km_total": 265, "remontees_total": 62, "forfait_domaine": 51,
        "alt_min": 700, "alt_max": 2500,
        "pistes": {"v":29,"b":111,"r":80,"n":31},
        "short": "Grand Massif",
        "desc": "Cinq villages du Faucigny reliés autour du plateau des Grandes Platières, à deux pas de Genève. Flaine, station-manifeste construite dans les années 60 par les architectes Marcel Breuer et Éric Boissonnas avec ses immeubles en béton brut et ses sculptures de Picasso et Dubuffet en pleine montagne — on aime ou on déteste, mais c'est unique. En contrebas, Samoëns, Morillon, Les Carroz et Sixt ont gardé leurs chalets et leurs clochers. Le domaine offre l'une des plus longues pistes des Alpes, les Cascades : 14 km de descente depuis les Grandes Platières jusqu'à Sixt, avec vue sur le cirque du Fer-à-Cheval.",
    },
    "sybelles": {
        "name": "Les Sybelles", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["La Toussuire","Le Corbier","Saint-Sorlin-d'Arves","Saint-Jean-d'Arves","Les Bottières","Saint-Colomban-des-Villards"],
        "km_propre": {},
        "km_total": 310, "remontees_total": 68, "forfait_domaine": 50,
        "alt_min": 1100, "alt_max": 2620,
        "unifie": True,
        "pistes": {"v":55,"b":120,"r":78,"n":31},
        "short": "Les Sybelles",
        "desc": "Six stations de Maurienne qui ont fusionné leurs domaines en 2003 autour du sommet de l'Ouillon, créant d'un coup l'un des plus grands domaines de France. La Toussuire, Le Corbier, Saint-Sorlin-d'Arves, Saint-Jean-d'Arves, Les Bottières et Saint-Colomban partagent le même forfait et les mêmes pistes — impossible de dire où commence l'une et où finit l'autre. C'est un domaine très ensoleillé, dominé par la silhouette des Aiguilles d'Arves, avec une majorité de pistes bleues et rouges qui en font un terrain idéal pour progresser en famille. Les tarifs restent nettement plus doux que dans les grandes stations de Tarentaise.",
    },
    "espace-diamant": {
        "name": "Espace Diamant", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["Les Saisies","Crest-Voland","Notre-Dame-de-Bellecombe","Flumet","Praz-sur-Arly","Hauteluce"],
        "km_propre": {},
        "km_total": 192, "remontees_total": 81, "forfait_domaine": 46,
        "alt_min": 910, "alt_max": 2069,
        "unifie": True,
        "pistes": {"v":40,"b":92,"r":60,"n":16},
        "short": "Espace Diamant",
        "desc": "Le plus jeune des grands domaines français, né en 2005 de l'alliance entre le Beaufortain et le Val d'Arly. Les Saisies, Crest-Voland, Notre-Dame-de-Bellecombe, Flumet, Praz-sur-Arly et Hauteluce partagent 192 km de pistes entre 910 et 2069 m. C'est un domaine d'altitude modeste mais réputé pour son enneigement : Les Saisies captent les perturbations venues de l'ouest et affichent régulièrement des cumuls parmi les meilleurs des Alpes du Nord. L'ambiance est résolument village et famille, loin des stations-usines, avec de larges pistes en forêt d'épicéas et une vue permanente sur le Mont-Blanc.",
    },
    "evasion-mont-blanc": {
        "name": "Évasion Mont-Blanc", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["Megève","Saint-Gervais","Combloux","La Giettaz","Les Contamines-Montjoie"],
        "km_propre": {"Megève":230,"Saint-Gervais":45,"Les Contamines-Montjoie":120,"Combloux":60,"La Giettaz":20},
        "km_total": 263, "remontees_total": 107, "forfait_domaine": 50,
        "alt_min": 850, "alt_max": 2353,
        "pistes": {"v":39,"b":87,"r":76,"n":28},
        "short": "Évasion Mont-Blanc",
        "desc": "Megève, Saint-Gervais, Combloux, La Giettaz et Les Contamines-Montjoie, réunies au pied du toit de l'Europe. Megève, inventée dans les années 20 par la baronne de Rothschild qui voulait un Saint-Moritz français, reste la station de l'élégance à la française : village médiéval, calèches, tables étoilées. Le ski y est plutôt doux, sur de longues pistes en forêt à l'exposition généreuse. Attention à une subtilité : sur les 445 km annoncés par le forfait, 263 km seulement sont réellement reliés par remontées — Les Contamines et Cordon nécessitent un transfert. Le panorama sur le Mont-Blanc, lui, est constant.",
    },
    "espace-san-bernardo": {
        "name": "Espace San Bernardo", "massif": "Alpes du Nord",
        "pays": ["France", "Italie"],
        "stations": ["La Rosière"],
        "km_propre": {"La Rosière": 65},
        "km_total": 156, "remontees_total": 38, "forfait_domaine": 54,
        "alt_min": 1190, "alt_max": 2800,
        "unifie": True,
        "short": "Espace San Bernardo",
        "desc": "La Rosière côté français, La Thuile côté italien, reliées par le col du Petit-Saint-Bernard — le même que franchissait Hannibal avec ses éléphants, dit la légende. C'est le seul domaine international des Alpes du Nord, et l'un des rares endroits où l'on peut déjeuner d'une assiette de pâtes en Vallée d'Aoste avant de rentrer skier en Savoie l'après-midi. La Rosière est plein sud, face au massif du Mont-Blanc, avec un ensoleillement remarquable ; La Thuile est plus ombragée et plus raide, avec la fameuse piste Franco Berthod qui accueille la Coupe du monde féminine. Vent au col : la liaison ferme parfois.",
    },
    "galibier-thabor": {
        "name": "Galibier-Thabor", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["Valloire","Valmeinier"],
        "km_propre": {},
        "km_total": 160, "remontees_total": 33, "forfait_domaine": 54,
        "alt_min": 1430, "alt_max": 2750,
        "unifie": True,
        "pistes": {"v":26,"b":60,"r":54,"n":18},
        "short": "Galibier-Thabor",
        "desc": "Valloire et Valmeinier, deux villages de Maurienne blottis sous le col du Galibier, partagent 160 km de pistes réparties sur cinq versants depuis 2007. Valloire a gardé son âme de village-rue avec son église baroque du XVIIe et son ambiance authentique ; Valmeinier, plus récente, s'étage entre un vieux village à 1500 m et une station à 1800 m. Le domaine grimpe jusqu'à 2750 m et 70 % des pistes sont au-dessus de 2000 m, ce qui assure un enneigement solide de décembre à avril. C'est aussi le terrain de jeu des cyclistes l'été, avec le Galibier et le Télégraphe à portée de guidon.",
    },
    "alpe-dhuez-grand-domaine": {
        "name": "Alpe d'Huez Grand Domaine Ski", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["Alpe d'Huez","Auris-en-Oisans"],
        "km_propre": {"Alpe d'Huez":140,"Auris-en-Oisans":30},
        "km_total": 250, "remontees_total": 67, "forfait_domaine": 62,
        "alt_min": 1130, "alt_max": 3330,
        "pistes": {"v":16,"b":68,"r":82,"n":22},
        "short": "Alpe d'Huez",
        "desc": "L'Alpe d'Huez se surnomme l'Île au Soleil, et elle ne ment pas : 300 jours d'ensoleillement par an sur un plateau exposé plein sud, à 1860 m. Le domaine grimpe jusqu'au Pic Blanc à 3330 m, d'où part la Sarenne — 16 km de descente, la plus longue piste noire d'Europe, qui rejoint le fond de la vallée dans un décor de gorges sauvages. Autour de la station-mère gravitent Auris, Oz, Vaujany et Villard-Reculas, villages plus tranquilles et souvent moins chers, tous reliés. Les 21 virages de la montée mythique du Tour de France sont juste en dessous.",
    },
    "serre-chevalier-vallee": {
        "name": "Serre Chevalier Vallée", "massif": "Alpes du Sud", "pays": ["France"],
        "stations": ["Serre Chevalier"],
        "km_propre": {},
        "km_total": 250, "remontees_total": 60, "forfait_domaine": 63,
        "alt_min": 1200, "alt_max": 2830,
        "unifie": True,
        "short": "Serre Chevalier",
        "desc": "Quatre villages étirés sur 13 km entre Briançon et Le Monêtier-les-Bains, formant le plus grand domaine des Alpes du Sud. Serre Chevalier joue une carte rare : le climat sec et ensoleillé du Sud combiné à une altitude sérieuse — 2830 m au pic de l'Yret — et à des pistes largement tracées en forêt de mélèzes, ce qui sauve les journées de mauvaise visibilité. Briançon, ville la plus haute de France et fortifications Vauban classées à l'UNESCO, ajoute une dimension patrimoniale rare en station. Le Monêtier, à l'autre bout, a ses bains d'eau chaude naturelle pour finir la journée.",
    },
    "voie-lactee": {
        "name": "La Voie Lactée (Via Lattea)", "massif": "Alpes du Sud",
        "pays": ["France", "Italie"],
        "stations": ["Montgenèvre"],
        "km_propre": {"Montgenèvre": 95},
        "km_total": 400, "remontees_total": 70, "forfait_domaine": 57,
        "alt_min": 1380, "alt_max": 2823,
        "unifie": True,
        "short": "La Voie Lactée",
        "desc": "Montgenèvre est la seule station française de la Via Lattea, immense domaine transfrontalier qui s'étend côté italien jusqu'à Sestrières, Sauze d'Oulx et Sansicario — 400 km de pistes au total. Fondée en 1907, Montgenèvre est l'une des toutes premières stations de ski de France, installée sur un col à 1860 m qui garantit un enneigement précoce. L'ambiance est franchement méridionale, avec le soleil du Briançonnais et la proximité de l'Italie qui se sent partout, du menu des refuges à l'accent des remontées. Les 95 km propres à Montgenèvre suffisent largement pour une semaine ; le reste est du bonus.",
    },
    "foret-blanche": {
        "name": "La Forêt Blanche", "massif": "Alpes du Sud", "pays": ["France"],
        "stations": ["Vars","Risoul"],
        "km_propre": {},
        "km_total": 185, "remontees_total": 51, "forfait_domaine": 46,
        "alt_min": 1650, "alt_max": 2750,
        "unifie": True,
        "pistes": {"v":26,"b":66,"r":52,"n":16},
        "short": "La Forêt Blanche",
        "desc": "Vars et Risoul se partagent 185 km de pistes de part et d'autre du col de Valbelle, dans un décor de forêts de mélèzes clairsemées typiques des Alpes du Sud. C'est le deuxième domaine de la région, et l'un des plus hauts : 83 % des pistes sont au-dessus de 2000 m, ce qui compense la latitude méridionale et assure une neige de qualité. Vars est réputée pour son Kilomètre Lancé, piste de vitesse où sont tombés plusieurs records du monde à plus de 250 km/h. Risoul, station piétonne des années 70, cultive un esprit plus familial et intime. Le soleil, lui, est partout : plus de 300 jours par an.",
    },
    "grand-tourmalet": {
        "name": "Grand Tourmalet – Pic du Midi", "massif": "Pyrénées", "pays": ["France"],
        "stations": ["La Mongie-Barèges (Tourmalet)"],
        "km_propre": {},
        "km_total": 100, "remontees_total": 28, "forfait_domaine": 46,
        "alt_min": 1250, "alt_max": 2500,
        "unifie": True,
        "short": "Grand Tourmalet",
        "desc": "Le plus grand domaine des Pyrénées françaises, réparti sur les deux versants du col du Tourmalet — Barèges d'un côté, La Mongie de l'autre. Barèges est un village thermal historique dont les eaux soignaient déjà les soldats de Louis XIV ; La Mongie, construite dans les années 60, offre un accès direct aux pistes et au Pic du Midi. Ce dernier est l'attraction unique du domaine : téléphérique jusqu'à 2877 m, observatoire astronomique centenaire, et une descente hors-piste de 1700 m de dénivelé pour skieurs aguerris. Le Tourmalet est aussi le col le plus emprunté de l'histoire du Tour de France.",
    },
    "grand-domaine-valmorel": {
        "name": "Le Grand Domaine", "massif": "Alpes du Nord", "pays": ["France"],
        "stations": ["Valmorel","Saint-François-Longchamp"],
        "km_propre": {"Valmorel": 95, "Saint-François-Longchamp": 70},
        "km_total": 165, "remontees_total": 47, "forfait_domaine": 58,
        "alt_min": 1200, "alt_max": 2550,
        "unifie": True,
        "short": "Le Grand Domaine",
        "pistes": {"v":20,"b":40,"r":32,"n":9},
        "desc": "Valmorel et Saint-François-Longchamp se rejoignent par le col de la Madeleine, formant 165 km de pistes entre Tarentaise et Maurienne. Valmorel est un cas à part dans les Alpes : construite en 1976, elle a délibérément refusé le béton pour un village entièrement piéton en bois et lauzes, avec des façades peintes et une rue centrale commerçante — un pari architectural qui a plutôt bien vieilli. Saint-François-Longchamp, côté Maurienne, est plus ensoleillée et plus discrète. Le domaine est particulièrement adapté aux familles et aux skieurs intermédiaires, avec une majorité de pistes bleues et un excellent rapport qualité-prix.",
    },
    "le-devoluy": {
        "name": "Le Dévoluy", "massif": "Alpes du Sud", "pays": ["France"],
        "stations": ["Superdévoluy","La Joue du Loup"],
        "km_propre": {},
        "km_total": 100, "remontees_total": 26, "forfait_domaine": 40,
        "alt_min": 1500, "alt_max": 2500,
        "unifie": True,
        "pistes": {"v":8,"b":22,"r":16,"n":5},
        "short": "Le Dévoluy",
        "desc": "Superdévoluy et La Joue du Loup partagent 100 km de pistes dans le massif du Dévoluy, entre Vercors et Alpes du Sud — un cirque calcaire sauvage et minéral qui ne ressemble à rien d'autre dans les Alpes. Le domaine culmine à 2500 m et bénéficie d'un enneigement souvent supérieur à ce que sa latitude laisserait imaginer, grâce aux perturbations qui viennent buter contre les falaises. Superdévoluy assume son architecture de béton des années 60 ; La Joue du Loup, construite vingt ans plus tard en bois et pierre, est nettement plus séduisante. Les tarifs restent parmi les plus doux des Alpes pour un domaine de cette taille.",
    },
    "espace-lumiere": {
        "name": "Espace Lumière", "massif": "Alpes du Sud", "pays": ["France"],
        "stations": ["Pra-Loup","Val d'Allos"],
        "km_propre": {},
        "unifie": True,
        "km_total": 180, "remontees_total": 53, "forfait_domaine": 47,
        "alt_min": 1500, "alt_max": 2600,
        "pistes": {"v":26,"b":80,"r":56,"n":12},
        "short": "Espace Lumière",
        "desc": "Pra-Loup et Val d'Allos La Foux sont reliées depuis 1972 au-dessus de la vallée de l'Ubaye, formant l'un des plus vastes domaines des Alpes du Sud avec 180 km de pistes. Pra-Loup a été fondée par Honoré Bonnet, entraîneur de l'équipe de France championne aux JO de 1968, qui voulait un terrain d'entraînement au soleil : le résultat est un domaine varié, largement boisé de mélèzes, avec un dénivelé confortable. Val d'Allos, de l'autre côté du col de l'Encombrette, ouvre sur le Parc national du Mercantour. Le climat est celui du Sud : sec, lumineux, et généreux en journées bleues.",
    },
    "grand-sancy": {
        "name": "Le Grand Sancy", "massif": "Massif Central", "pays": ["France"],
        "stations": ["Super Besse","Le Mont Dore"],
        "km_propre": {"Super Besse": 43, "Le Mont Dore": 41},
        "km_total": 84, "remontees_total": 35, "forfait_domaine": 43,
        "alt_min": 1050, "alt_max": 1850,
        "pistes": {"v":13,"b":22,"r":16,"n":4},
        "short": "Le Grand Sancy",
        "desc": "Super-Besse et Le Mont-Dore encadrent le puy de Sancy, point culminant du Massif central à 1885 m — un ancien volcan dont la silhouette domine toute l'Auvergne. Les deux stations totalisent 84 km de pistes et sont théoriquement reliées par les crêtes, mais attention : cette liaison n'est ouverte que lorsque l'enneigement le permet, ce qui est loin d'être systématique. Le Mont-Dore est une ville thermale du XIXe au charme désuet, avec son établissement thermal néo-byzantin ; Super-Besse, plus haute et plus moderne, est mieux enneigée. C'est le plus grand domaine du Massif central, et de loin le plus dépaysant volcanologiquement parlant.",
        "conditionnel": True,
    },
}

def get_domaine(station_name):
    """Retourne (slug, dict) du domaine skiable relié auquel appartient
    une station, ou (None, None) si elle est indépendante."""
    for slug, d in DOMAINES.items():
        if station_name in d["stations"]:
            return slug, d
    return None, None

def get_alt_village(domaine, station_name):
    """Altitude du village (pas du domaine) pour une station membre,
    si elle est connue précisément ; sinon None."""
    return domaine.get('alt_village', {}).get(station_name)

# Altitudes de village connues, par station (complète les stat-box).
_ALT_VILLAGE = {
    "Avoriaz":1800,"Morzine":1000,"Les Gets":1172,"Châtel":1200,
    "Montriond":1049,"Saint-Jean-d'Aulps":820,"Abondance":930,"La Chapelle d'Abondance":1010,
    "Samoëns":720,"Morillon":700,"Les Carroz":1140,"Flaine":1600,"Sixt-Fer-à-Cheval":770,
    "Megève":1113,"Saint-Gervais":850,"Les Contamines-Montjoie":1164,"Combloux":1000,"La Giettaz":1123,
    "Val Thorens":2300,"Les Menuires":1800,"Saint-Martin-de-Belleville":1450,
    "Méribel":1450,"La Tania":1350,"Courchevel":1850,"Brides-les-Bains":600,"Orelle":900,
    "Val d'Isère":1850,"Tignes":2100,
    "La Plagne":1970,"Peisey-Vallandry":1600,"Les Arcs":1800,"Montchavin-Les Coches":1450,
    "La Toussuire":1750,"Le Corbier":1550,"Saint-Sorlin-d'Arves":1600,
    "Saint-Jean-d'Arves":1200,"Les Bottières":1450,"Saint-Colomban-des-Villards":1100,
    "Les Saisies":1650,"Crest-Voland":1230,"Notre-Dame-de-Bellecombe":1150,
    "Flumet":1000,"Praz-sur-Arly":1036,"Hauteluce":1150,
    "La Rosière":1850,"Valloire":1430,"Valmeinier":1500,
    "Alpe d'Huez":1860,"Auris-en-Oisans":1600,
    "Serre Chevalier":1350,"Montgenèvre":1860,
    "Vars":1850,"Risoul":1850,
    "La Mongie-Barèges (Tourmalet)":1250,"Peyragudes":1600,"Saint-Lary-Soulan":1680,
    "Superdévoluy":1500,"La Joue du Loup":1450,
    "Super Besse":1350,"Le Mont Dore":1050,
    "Saint-François-Longchamp":1450,"Valmorel":1400,
}
for _d in DOMAINES.values():
    _d['alt_village'] = {n: _ALT_VILLAGE[n] for n in _d['stations'] if n in _ALT_VILLAGE}

# ══════════════════════════════════════════════════════════════════
# ENRICHISSEMENT ÉDITORIAL — anecdotes & orientation des villages
# ══════════════════════════════════════════════════════════════════
# Rempli progressivement, massif par massif, à partir de recherches
# vérifiées (recoupées sur au moins deux sources indépendantes :
# site officiel de la station, presse, encyclopédies spécialisées).
# Ne JAMAIS inventer un fait ici — une station sans entrée confirmée
# n'affiche simplement pas l'onglet enrichi (fallback gracieux).
#
# STATION_ANECDOTES[nom] = ["fait vérifié 1", "fait vérifié 2", ...]
#
# STATION_ORIENTATION[nom] = {
#   'expo': "Nord" | "Nord-Est" | "Est" | "Sud-Est" | "Sud" | "Sud-Ouest" | "Ouest" | "Nord-Ouest",
#   'expo_deg': 0-359 (0=Nord, 90=Est, 180=Sud, 270=Ouest — pour l'aiguille de la boussole),
#   'village_txt': description courte de l'ensoleillement du village,
#   'village_impact': impact concret sur l'ambiance / la vie du village,
#   'pistes_impact': impact concret sur la qualité et la tenue de la neige,
# }
STATION_ANECDOTES = {
    "Ghisoni - Capanelle": [
        "La station a été créée en 1974 à l'initiative du docteur Maymard et du maire de Ghisoni, M. Vignaroli, avec l'ouverture des premiers téléskis dès 1975. Son nom vient des « Capanelle », d'anciennes bergeries qui servaient déjà de refuge sur le sentier de grande randonnée GR20.",
        "C'est l'une des deux stations de ski encore en activité de Corse, installée au pied du Monte Renoso (2 352 m), 3ᵉ plus haut sommet de l'île.",
    ],
    "Val d'Ese": [
        "Depuis le sommet du téléski de Tarmini, le plus haut de la station, on aperçoit la mer et le golfe d'Ajaccio par temps clair — un panorama rare pour une station de ski.",
        "Les premières remontées mécaniques ont été installées en 1976, sur le plateau d'Ese, entre les vallées du Prunelli et du Taravo.",
    ],
    "Haut Asco": [
        "Inaugurée en 1964, la station a été détruite par d'importantes intempéries le 27 septembre 1992 et est restée fermée pendant plus de 20 ans, avant de rouvrir en 2015 après 2,5 millions d'euros de travaux.",
        "C'est la seule station de ski de Corse équipée de canons à neige, et elle sert aussi de point de départ pour l'ascension du Monte Cinto (2 706 m), le plus haut sommet de l'île, ainsi que d'étape sur le GR20.",
    ],
    "Métabief Mont d'Or": [
        "Les habitants de Métabief sont surnommés les « Chats-Gris ». Ce que l'on appelle « la station de Métabief » regroupe en réalité six communes (Métabief, Jougne, Les Hôpitaux-Neufs, Les Hôpitaux-Vieux, Longevilles-Mont-d'Or et Rochejean).",
        "Le village est situé à seulement 7 km de la frontière suisse ; son secteur de ski « Piquemiette » touche même directement cette frontière, au pied des falaises du Mont d'Or.",
    ],
    "Les Rousses": [
        "C'est la toute première station française à avoir obtenu le label « Flocon Vert », qui récompense l'engagement durable des stations de montagne.",
        "Son domaine alpin « Jura sur Léman » est en partie transfrontalier avec la Suisse — on peut littéralement skier avec un ski de chaque côté de la frontière — et offre depuis le sommet de la Dôle une vue sur la chaîne des Alpes et le Mont-Blanc.",
        "La station rassemble quatre villages (Les Rousses, Prémanon, Lamoura, Bois-d'Amont) et est un haut lieu historique du ski nordique français, qui accueille chaque année la Transjurassienne, l'une des plus grandes courses populaires de ski de fond d'Europe.",
    ],
    "Monts Jura": [
        "Monts Jura est né en 1999 de la fusion de plusieurs sites autour des villages de Mijoux et Lélex (La Faucille, Lélex-Crozet, et le site nordique de la Vattay), rejoints par Menthières en 2006.",
        "Le domaine est à seulement 20 minutes de Genève ; son versant de Crozet est en connexion directe avec le bassin lémanique.",
    ],
    "Lélex-Crozet": [
        "Le tout premier téléski du secteur a été installé dès 1936 par Gabriel Julliard, mais la station de Lélex n'a été officiellement créée qu'en 1955, avec sa première télébenne construite après cinq années de travaux.",
        "C'est le plus grand domaine skiable et le plus grand dénivelé de tout le massif jurassien, avec 30 km de pistes entre 900 m (Lélex) et 1 680 m (sommet du Monthoisey).",
    ],
    "Lamoura": [
        "Le lac de Lamoura (1 152 m) est le plus haut lac naturel du massif du Jura, vestige de l'ancienne vallée glaciaire.",
        "C'est le village de départ historique de la Transjurassienne, l'une des plus grandes courses populaires de ski de fond d'Europe, qui la relie à Mouthe dans le Doubs.",
    ],
    "Les Fourgs": [
        "Surnommé le « Toit du Doubs », le village culmine à 1 100 m d'altitude en moyenne, sur le plateau le plus élevé du département, à la frontière de la commune suisse de Sainte-Croix.",
        "Le village est resté à l'écart du réseau routier principal : depuis plus d'un siècle, plusieurs projets de route transversale (1909, 1922, 1935, 1996, 2005) n'ont jamais abouti, ce qui explique ses liens historiquement étroits avec la Suisse voisine.",
    ],
    "Menthières": [
        "La station a été créée en 1987 par un syndicat intercommunal réunissant les communes de Bellegarde-sur-Valserine, Lancrans, Confort et Chézery-Forens ; elle a rejoint le regroupement Monts Jura en 2006 et en est aujourd'hui le plus petit secteur alpin.",
    ],
    "La Source du Doubs-Mouthe": [
        "La station est installée à Mouthe, le village qui détient le record officiel de la température la plus basse jamais enregistrée en France métropolitaine : -36,7°C, le 13 janvier 1968.",
        "Elle se trouve à seulement 200 m de la source du Doubs, l'un des points de départ symboliques de ce fleuve.",
    ],
    "Les Plans d'Hotonnes": [
        "Le stade de biathlon du plateau de Retord, entièrement rénové et rendu accessible aux malvoyants grâce à des cibles sonores, a accueilli un stage d'entraînement de l'équipe de France de biathlon en 2020.",
        "Le plateau a vu grandir des biathlètes médaillés olympiques comme Sandrine Bailly et Simon Desthieux.",
    ],
    "Gérardmer": [
        "Son surnom, « La Perle des Vosges », lui a été donné par Abel Hugo — le frère aîné de Victor Hugo — dans son ouvrage La France pittoresque (1833-1835), où il célèbre la beauté du lac dans un poème.",
        "La ville a accueilli le tout premier office de tourisme de France, le « Comité des Promenades », créé en 1875.",
    ],
    "La Bresse-Hohneck": [
        "C'est le plus grand domaine skiable du Nord-Est de la France (220 hectares), face au Hohneck, point culminant des Vosges (1 363 m).",
        "La station actuelle a été créée en 1965 par la famille Rémy, après une première tentative avortée : la station voisine de Supervallée, ouverte en 1961, avait fermé dès 1972.",
    ],
    "Le Ballon d'Alsace": [
        "Le col du Ballon d'Alsace fut le tout premier col de montagne franchi dans l'histoire du Tour de France, le 11 juillet 1905 — cinq ans avant les premiers grands cols pyrénéens et alpins. Le coureur René Pottier en fut le premier à passer au sommet ; une stèle érigée à sa mémoire s'y trouve toujours.",
    ],
    "La Planche des Belles Filles": [
        "Alors qu'aucune étape du Tour de France n'y était jamais passée avant 2012, la station est devenue en une décennie l'une des arrivées de montagne les plus emblématiques de la course, avec six passages entre 2012 et 2022 — parmi les lieux les plus visités du Tour sur cette période, aux côtés de Paris et Pau.",
        "En 2022, son sommet a aussi accueilli l'arrivée de la toute première édition moderne du Tour de France Femmes.",
        "Son nom viendrait d'une légende locale de jeunes filles réfugiées au sommet de la montagne ; le site fut aussi un maquis de la Résistance pendant la Seconde Guerre mondiale.",
    ],
    "Le Lac Blanc": [
        "Fait surprenant : c'est Charles Diebold, qui avait fondé la première école de ski du Lac Blanc en 1925, qui partit ensuite créer la station expérimentale de Val d'Isère en 1932-33 — où il baptisa ses cours « cours vosgiens » en clin d'œil à ses origines alsaciennes.",
    ],
    "Le Grand Valtin": [
        "C'est, selon Wikipédia et de nombreuses sources touristiques, la plus petite station de ski d'Europe : seulement 2 pistes (1 verte, 1 bleue) et 2 téléskis, nichée dans une clairière entourée de sapins.",
    ],
    "Grand Tourmalet": [
        "Le col du Tourmalet (2 115 m), au cœur du domaine, est le col le plus franchi de toute l'histoire du Tour de France : plus de 80 passages depuis sa première ascension en 1910 par Octave Lapize, à qui une statue rend hommage au sommet.",
        "La Mongie a aussi accueilli trois arrivées d'étape du Tour de France sur ses pentes : en 1970 (victoire de Bernard Thévenet), 2002 (Lance Armstrong) et 2004 (Ivan Basso).",
        "Avec 100 km de pistes, c'est le plus grand domaine skiable des Pyrénées françaises.",
    ],
    "Saint-Lary-Soulan": [
        "La station a été lancée par le maire du village, Vincent Mir, avec la construction d'un téléphérique en 1957 menant au Pla d'Adet.",
        "Sa fille, Isabelle Mir, née à Saint-Lary-Soulan, est considérée comme la plus grande descendeuse de l'histoire du ski français, avec deux médailles d'argent (JO 1968 de Grenoble, Mondiaux 1970 de Val Gardena) et deux Globes de cristal de la descente.",
        "Avec 100 km de pistes, c'est la première station des Pyrénées françaises en fréquentation.",
    ],
    "Cauterets": [
        "Ville thermale déjà réputée depuis le Moyen Âge, elle a accueilli au XIXe siècle nombre de célébrités venues « prendre les eaux » : Chateaubriand, George Sand, Sarah Bernhardt... et Victor Hugo, qui y séjourna lors de son voyage aux Pyrénées de 1843.",
        "En 1858, c'est à Cauterets que Bernadette Soubirous — la future sainte de Lourdes — vint faire une cure pour soigner son asthme, entre deux de ses apparitions.",
    ],
    "Luchon-Superbagnères": [
        "C'est l'une des toutes premières stations de ski des Pyrénées : elle est née autour d'un train à crémaillère mis en service en 1912, qui reliait Bagnères-de-Luchon au plateau jusqu'à sa fermeture en 1966.",
        "En 1937, le plateau s'est équipé du tout premier téléski des Pyrénées, l'un des plus modernes au monde à l'époque.",
        "En hommage à cette histoire, la nouvelle télécabine mise en service en 2023 a été baptisée « Crémaillère Express ».",
    ],
    "Font-Romeu-Pyrénées 2000": [
        "Le Centre national d'entraînement en altitude, créé ici en 1966-1967 sur impulsion du général de Gaulle, avait pour but de préparer les athlètes français aux Jeux Olympiques de Mexico (1968), eux-mêmes disputés en altitude.",
        "Depuis sa création, plus de 270 médaillés olympiques, dont 104 champions, sont venus s'y préparer.",
    ],
    "Ax-3-Domaines": [
        "Le nom d'Ax vient du latin « Aquae » (les eaux) : la ville compte plus de 60 sources thermales naturelles, connues depuis l'époque romaine, dont certaines jaillissent jusqu'à 77°C.",
        "Créée en décembre 1955, la station accueille régulièrement des arrivées d'étape du Tour de France depuis 2001.",
    ],
    "Gavarnie-Gèdre": [
        "Le cirque de Gavarnie, au cœur duquel se love la station, est inscrit au patrimoine mondial de l'UNESCO depuis 1997 (au sein du site Pyrénées – Mont Perdu) — skier dans un site classé UNESCO est une rareté.",
        "Victor Hugo, qui découvrit le site en août 1843, le décrivit comme « le Colosseum de la nature » ; sa cascade, haute d'environ 422 mètres, compte parmi les plus hautes d'Europe.",
    ],
    "Peyragudes": [
        "L'altiport de la station a servi de décor pour la scène d'ouverture du James Bond « Demain ne meurt jamais » (1997), avec Pierce Brosnan — un camp afghan y avait été reconstitué. En hommage, il a été rebaptisé « Altiport 007 » en 2017, la même année qu'une piste bleue de 2,8 km a été baptisée « 007 ».",
        "Née de la fusion des stations de Peyresourde (Hautes-Pyrénées) et des Agudes (Haute-Garonne), elle est aussi une habituée du Tour de France : en 2012, lors de la première arrivée d'étape dans la station, Thomas Voeckler y a conquis son maillot à pois de meilleur grimpeur.",
    ],
    "Luz-Ardiden": [
        "L'arrivée d'étape du Tour de France, inaugurée en 1985, est devenue légendaire en 2003 : Lance Armstrong y chuta après avoir accroché le sac d'un spectateur, mais remonta aussitôt sur son vélo pour remporter l'étape et conforter sa 5e victoire dans le Tour.",
        "D'autres grands noms du cyclisme y ont marqué l'histoire : Pedro Delgado, vainqueur de la toute première arrivée en 1985, ou Greg LeMond, qui y assura en 1990 son 3e et dernier Tour de France.",
    ],
    "Gourette": [
        "C'est ici qu'a eu lieu, en novembre 1903, l'une des toutes premières descentes à ski des Pyrénées : Henri Sallenave y chaussa des skis reçus de la Manufacture de Saint-Étienne, sur le plateau alors habité seulement par des cabanes de bergers.",
    ],
    "Piau-Engaly": [
        "C'est la plus haute station de ski des Pyrénées françaises, avec un sommet de domaine à 2 600 m d'altitude — devant ses voisines Saint-Lary-Soulan et le Grand Tourmalet.",
        "Née en 1971 de la vision de l'architecte Jean-Marc Roques, qui voulait une station intégrée au paysage, elle est entièrement piétonne en son cœur et reliée à l'Espagne par le tunnel d'Aragnouet-Bielsa, l'un des rares passages routiers transpyrénéens en altitude.",
    ],
    "Les Angles": [
        "Dans les années 1960, ce village de 250 habitants, vidé par l'exode rural, a été sauvé par une idée du maire Paul Samson, surnommé « le fou du Capcir » : construire une station de ski dont les pistes arriveraient au pied du clocher. Il alla jusqu'à mettre la forêt communale en caution pour obtenir les financements.",
        "Le premier télésiège ouvre en janvier 1964 ; faute de place dans l'unique hôtel, les premiers touristes dormaient dans les granges des habitants.",
    ],
    "Hautacam": [
        "Cette arrivée d'étape du Tour de France, inaugurée en 1994, est restée dans l'histoire pour la spectaculaire victoire de Bjarne Riis en 1996, qui y mit fin au règne du quintuple vainqueur Miguel Indurain — Riis reconnaîtra en 2007 s'être dopé à l'EPO durant cette période.",
        "Le record de l'ascension établi par Riis en 1996 (34 min 40) a résisté plus de 25 ans : Tadej Pogačar n'en est passé qu'à 28 secondes en 2022.",
    ],
    "La Pierre-Saint-Martin": [
        "Le massif qui porte la station abrite l'un des plus vastes réseaux spéléologiques du monde : le gouffre de la Pierre Saint-Martin, considéré comme le gouffre le plus profond du monde dans les années 1950-1960 (-1 166 m dès 1954, puis -1 321 m dix ans plus tard).",
        "Il renferme la salle de la Verna, la plus vaste salle souterraine du monde accessible au public, avec 250 m de diamètre et 190 m de haut.",
    ],
    "Artouste": [
        "Le petit train d'Artouste, aujourd'hui touristique, a d'abord été construit dans les années 1920 pour acheminer les 2 000 ouvriers et les matériaux du chantier du barrage du lac d'Artouste, l'un des plus grands barrages des Pyrénées, mis en service en 1929. Il n'est devenu une attraction touristique qu'en 1932.",
        "Culminant à près de 2 000 m, c'est le deuxième plus haut train de France, derrière le tramway du Mont-Blanc.",
    ],
    "Puigmal": [
        "Cette petite station a connu une histoire mouvementée : mise en liquidation judiciaire en 2014 après plusieurs saisons d'enneigement insuffisant, elle a fermé ses pistes avant de rouvrir en 2019 sous une forme diversifiée.",
    ],
    "Saint-Lary-Village": [
        "La station a été lancée par le maire du village, Vincent Mir, avec la construction d'un téléphérique en 1957 menant au Pla d'Adet.",
        "Sa fille, Isabelle Mir, née à Saint-Lary-Soulan, est considérée comme la plus grande descendeuse de l'histoire du ski français, avec deux médailles d'argent (JO 1968 de Grenoble, Mondiaux 1970 de Val Gardena) et deux Globes de cristal de la descente.",
    ],
    "La Mongie-Barèges (Tourmalet)": [
        "Le col du Tourmalet (2 115 m), au cœur du domaine, est le col le plus franchi de toute l'histoire du Tour de France : plus de 80 passages depuis sa première ascension en 1910 par Octave Lapize, à qui une statue rend hommage au sommet.",
        "La Mongie a aussi accueilli trois arrivées d'étape du Tour de France sur ses pentes : en 1970 (victoire de Bernard Thévenet), 2002 (Lance Armstrong) et 2004 (Ivan Basso).",
    ],
    "Peyresourde-Balestas": [
        "L'altiport voisin a servi de décor pour la scène d'ouverture du James Bond « Demain ne meurt jamais » (1997), avec Pierce Brosnan. En hommage, il a été rebaptisé « Altiport 007 » en 2017, la même année qu'une piste bleue de 2,8 km a été baptisée « 007 ».",
    ],
    "Le Mourtis": [
        "Née en 1965 dans une ancienne zone d'estive pastorale face au massif du Cagire, c'est l'une des quatre stations de ski de la Haute-Garonne.",
        "Depuis le sommet du domaine, la vue porte jusqu'au Pic Aneto (3 408 m), point culminant de l'ensemble des Pyrénées, situé côté espagnol.",
    ],
    "Cambre d'Aze": [
        "La station est accessible par deux villages distincts, Eyne et Saint-Pierre-dels-Forcats, qui se partagent un même domaine skiable.",
    ],
    "Les Monts d'Olmes": [
        "C'est ici que Perrine Laffont, championne olympique de ski de bosses (or à Pyeongchang en 2018, bronze à Milan-Cortina en 2026) et six fois championne du monde, a appris à skier. Son père y est moniteur, et elle reste licenciée du club local, le Boss Club des Monts d'Olmes, où elle revient régulièrement.",
    ],
    "Bolquère-Pyrénées 2000": [
        "La gare de Bolquère-Eyne, à 1 592 m d'altitude, est la plus haute gare exploitée par la SNCF en France. Ouverte en 1910, elle est desservie par le Train Jaune, la ligne électrifiée la plus haute d'Europe, classée au patrimoine mondial de l'UNESCO en 2002.",
    ],
    "Formiguères": [
        "Ancienne capitale historique du Capcir, le village fut la résidence d'été des rois de Majorque aux XIIe-XIIIe siècles, appréciée pour la fraîcheur de son climat. Son église romane a été consacrée en 873.",
        "Au-dessus du village, le site de la Peyra Escrita conserve des gravures rupestres étudiées par les archéologues, dont certaines remontent au Néolithique.",
    ],
    "Serre Chevalier": [
        "Avec 250 km de pistes, c'est l'un des plus grands domaines skiables d'Europe. Il relie trois villages (Chantemerle, Villeneuve, Le Monêtier-les-Bains) à la ville de Briançon, dont les fortifications Vauban sont classées au patrimoine mondial de l'UNESCO.",
        "La piste Vauban, ouverte en 1989, permet de skier — même de nuit — directement au-dessus des remparts de Briançon illuminés, une configuration unique dans les Alpes.",
        "Le champion briançonnais Luc Alphand, plusieurs fois vainqueur en Coupe du monde de descente et de Super-G, a donné son nom à l'une des pistes emblématiques du domaine.",
    ],
    "Isola 2000": [
        "Née de toutes pièces en 1971 sur un site qui n'était auparavant qu'un pâturage de bergeries, à l'initiative d'investisseurs britanniques (Bernard Sunley Investment Trust). Son architecte-urbaniste, Gérald Hanning, avait été collaborateur de Le Corbusier.",
        "Grâce à sa proximité avec la Côte d'Azur, la station bénéficie d'un ensoleillement exceptionnel ; elle a même été la station la plus enneigée de France lors des hivers 2010-2011 et 2014-2015.",
    ],
    "Montgenèvre": [
        "C'est la plus ancienne station de ski de France : elle est née en 1907 avec la première compétition internationale de ski organisée dans le pays, à l'initiative du Club alpin français, du Touring Club de France et de l'armée.",
        "Le col de Montgenèvre est un passage historique emprunté depuis l'Antiquité — Jules César y passa lors de ses campagnes en Gaule, et Napoléon Bonaparte le traversa en 1800 pour rejoindre l'Italie.",
        "Dans les années 1930-1940, la station était un rendez-vous de la jet-set parisienne, fréquentée par Jean Cocteau, Jean Gabin, Colette ou encore Mistinguett.",
    ],
    "Vars": [
        "La piste de Chabrières, avec ses 98 % de pente à son sommet, détient le record du monde de vitesse à ski : 255,5 km/h, établi par le Français Simon Billy le 22 mars 2023 — ce qui en fait, avec la piste de Verbier en Suisse, l'une des deux seules pistes homologuées au monde pour dépasser les 200 km/h.",
        "Le record était resté en famille : le père de Simon, Philippe Billy, avait déjà été recordman du monde sur cette même piste en 1997, à 243,9 km/h — 26 ans avant son fils.",
    ],
    "Risoul": [
        "Depuis le sommet du domaine (l'Homme de Pierre, 2 361 m), la vue porte sur la place forte de Mont-Dauphin, construite par Vauban à partir de 1693 et classée au patrimoine mondial de l'UNESCO depuis 2008 au titre des fortifications Vauban.",
    ],
    "Pra-Loup": [
        "C'est ici, le 13 juillet 1975, que Bernard Thévenet a mis fin au règne d'Eddy Merckx — surnommé « le Cannibale » — sur le Tour de France, en le lâchant dans la dernière ascension pour s'emparer du maillot jaune. Cette étape reste l'une des plus légendaires de l'histoire du Tour.",
        "Créée en 1962, la station forme avec La Foux d'Allos le domaine de l'Espace Lumière (180 km de pistes).",
    ],
    "Val d'Allos": [
        "Le village voisin de Colmars-les-Alpes, dans la même vallée, est une cité fortifiée dont les remparts datent du Moyen Âge (1382) et furent renforcés sous la supervision de Vauban à la fin du XVIIe siècle — l'un des sites du réseau des places fortes Vauban.",
    ],
    "Saint-Véran": [
        "À 2 042 m d'altitude, c'est la plus haute commune habitée d'Europe occidentale (avec mairie, école et église), classée parmi les Plus Beaux Villages de France. Sa devise : « le pays où les coqs picorent les étoiles ».",
        "Le village compte 24 cadrans solaires, dont beaucoup réalisés au XIXe siècle par le célèbre cadranier piémontais Zarbula, et abrite à 2 930 m l'un des plus hauts observatoires astronomiques d'Europe — un astéroïde, 48159 Saint-Véran, porte même le nom du village.",
    ],
    "Molines-Saint-Véran": [
        "Le domaine est relié au village de Saint-Véran qui, à 2 042 m d'altitude, est la plus haute commune habitée d'Europe occidentale, classée parmi les Plus Beaux Villages de France.",
    ],
    "Molines-en-Queyras": [
        "Le domaine partagé avec Saint-Véran est le plus grand espace de ski alpin du Queyras ; Saint-Véran, à 2 042 m, est la plus haute commune habitée d'Europe occidentale.",
    ],
    "La Grave - La Meije": [
        "Surnommée « la Mecque du freeride », La Grave n'est pas une station comme les autres : hormis une unique piste bleue sur le glacier de la Girose, le domaine (créé en 1976) n'a ni pistes balisées, ni damage, ni sécurisation — uniquement des itinéraires de haute montagne, avec 2 150 m de dénivelé entre le col des Ruillans (3 200 m) et le village.",
        "Le téléphérique fait gagner une journée entière de marche : sans lui, rejoindre le col des Ruillans depuis le village représente 1 900 m de dénivelé à pied.",
    ],
    "Turini-Camp d'Argent": [
        "La petite station est perchée au col de Turini (1 600 m), l'un des lieux les plus mythiques du sport automobile mondial : c'est ici que se disputait la légendaire « Nuit du Turini » du Rallye Monte-Carlo, spéciale nocturne dans la neige et le verglas qui a forgé la légende de pilotes comme Paddy Hopkirk (vainqueur sur Mini en 1964), Sébastien Loeb et Sébastien Ogier.",
    ],
    "Orcières-Merlette": [
        "Le 8 juillet 1971, l'Espagnol Luis Ocaña y a réalisé l'un des plus grands exploits de l'histoire du Tour de France : 60 km d'échappée en solitaire pour reléguer Eddy Merckx à 8 min 42 s — le seul jour où le « Cannibale » fut réellement humilié en montagne. Merckx dira après sa victoire finale : « J'ai perdu le Tour à Orcières ».",
        "Station pionnière à plusieurs titres : premier jardin des neiges de France (1967) et premier télémix de France (2003).",
    ],
    "Orcières 1850": [
        "Le 8 juillet 1971, l'Espagnol Luis Ocaña y a réalisé l'un des plus grands exploits de l'histoire du Tour de France : 60 km d'échappée en solitaire pour reléguer Eddy Merckx à 8 min 42 s au sommet de la montée d'Orcières-Merlette.",
        "Station pionnière : premier jardin des neiges de France (1967) et premier télémix de France (2003).",
    ],
    "Superdévoluy": [
        "C'est la première station de ski du massif du Dévoluy, née en 1966, aujourd'hui reliée à sa voisine La Joue du Loup par un domaine skiable commun.",
    ],
    "La Joue du Loup": [
        "La station est reliée à Superdévoluy — la première station du massif du Dévoluy, née en 1966 — avec laquelle elle partage un domaine skiable commun.",
    ],
    "Auron": [
        "En janvier 1935, la station a accueilli la première compétition de ski en France retransmise à la radio ; deux ans plus tard, le 30 janvier 1937, elle inaugurait son téléphérique, le troisième construit en France, avant de recevoir les Championnats de France de ski dès 1938.",
        "Avec 135 km de pistes, c'est la plus grande station des Alpes-Maritimes — à seulement 1h30 de la Promenade des Anglais de Nice.",
    ],
    "Valberg": [
        "Créée en 1936, c'est la plus ancienne station des Alpes-Maritimes : le 14 mars 1936, elle inaugurait la première remontée mécanique du département, le « tire-luge » du Cloutas — des luges en bois individuelles tirées par un câble, sur lesquelles les skieurs s'accroupissaient.",
        "Son nom, officialisé en 1935, vient de l'expression locale « lou valloun des bergians » : le vallon des bergers.",
    ],
    "Beuil-les-Launes": [
        "Beuil est l'un des berceaux du ski dans les Alpes-Maritimes : son tremplin des Launes a accueilli une Coupe de France de saut à ski en 1995, puis une Coupe d'Europe réunissant 9 nations en 1996.",
    ],
    "Gréolières-les-Neiges": [
        "C'est l'une des stations de ski les plus proches de la mer en France : située sur le versant nord du massif du Cheiron, elle n'est qu'à 21 km à vol d'oiseau de la Méditerranée — par temps clair, on skie avec vue sur la mer.",
    ],
    "La Colmiane": [
        "La station abrite la plus grande tyrolienne de France (et l'une des plus grandes d'Europe), inaugurée fin 2015 : 2 663 mètres de long en deux sections, près de 300 m de dénivelé, à survoler jusqu'à 120-130 km/h.",
    ],
    "Les Orres": [
        "Ouverte en novembre 1970 sur les plans de l'architecte parisien Jean-Michel Legrand, la station — conçue sans voiture et intégrée au paysage — est classée au patrimoine architectural du XXe siècle.",
        "Sa « Bulle », un énorme ballon de football abritant l'ESF et un restaurant, était orange à l'origine : c'est elle qui a donné son logo à la station. Après un incendie, elle a été reconstruite... en blanc.",
        "Le 9 juillet 1973, la station a accueilli une arrivée d'étape du Tour de France, remportée par l'Espagnol Luis Ocaña, vainqueur final de cette édition.",
    ],
    "Puy-Saint-Vincent": [
        "Surnommée « la protégée des vents », c'est la seule commune perchée au-dessus du fond de la vallée de la Vallouise, sur un plateau abrité des vents dominants, face à la Barre des Écrins (4 102 m) et au Pelvoux.",
        "Le site avait été repéré dès les années 1930 pour y créer une station... mais c'est finalement Serre Chevalier qui fut choisi, le village étant jugé trop difficile d'accès. La station n'a vu le jour qu'en 1968.",
    ],
    "Sauze-Super-Sauze": [
        "C'est l'une des plus anciennes stations de ski de France : fondée en 1934 par Honoré Couttolenc, agriculteur visionnaire qui installa un premier remonte-pente sur ses terres, dans une ancienne ferme familiale.",
        "C'est la station de Carole Merle, originaire du Sauze et considérée comme l'une des plus grandes skieuses alpines françaises de l'histoire, qui a fait ses gammes sur la piste du Brec, face au front de neige du Super-Sauze.",
    ],
    "Montclar-les-2-Vallées": [
        "La station est née d'un pari collectif unique : dans les années 1960, les habitants ont investi leurs propres économies par actionnariat pour créer la station et sauver le village de la désertification. Elle a été inaugurée le 24 janvier 1971... sous une tempête de neige.",
        "L'eau de Montclar, captée à 1 650 m d'altitude, est la plus haute source d'eau minérale de France — et c'est elle qui coule au robinet dans toute la station.",
        "Son domaine s'étend sur deux versants et deux vallées, la Blanche et l'Ubaye — d'où son nom.",
    ],
    "Mont Serein": [
        "Oui, on skie en Provence ! Le ski sur le Mont Ventoux remonte aux années 1920 : l'écrivain, peintre et alpiniste Pierre de Champeville y organisa des démonstrations dès 1925, et les premières remontées mécaniques sont apparues sur les flancs du « Géant de Provence » dès les années 1930 — ce qui en fait l'une des plus anciennes stations de France.",
        "Son nom n'est pas un hasard : contrairement au sommet du Ventoux, balayé par les vents, le versant du Mont Serein est abrité du Mistral.",
    ],
    "Ceillac-en-Queyras": [
        "La station est née d'un élan de solidarité étonnant : après les inondations dévastatrices de juin 1957, le magazine Elle finança en grande partie les deux premiers fils-neige du village et des paires de skis distribuées aux enfants. La station-village a démarré ainsi, en 1958.",
        "Le village abrite deux églises classées aux monuments historiques : Sainte-Cécile (XIVe siècle) et Saint-Sébastien (XVIe siècle), avec son clocher à six cloches et ses fresques.",
    ],
    "Crévoux": [
        "C'est l'une des plus anciennes stations des Alpes du Sud : premier téléski en 1936, puis inauguration officielle le 25 avril 1937 par l'épouse de Léo Lagrange, figure du Front populaire — un pur produit de l'époque des premiers congés payés et du tourisme social naissant.",
        "La commune abrite aussi le deuxième plus grand domaine nordique des Hautes-Alpes, à La Chalp.",
    ],
    "Abriès-en-Queyras": [
        "Abriès fut la première commune rurale de France à être électrifiée, au tournant du XXe siècle — un monument face à l'église commémore l'événement.",
        "Le tourisme y est né avec les alpinistes anglais : le premier grand hôtel du Queyras y a été construit dès 1897, bien avant l'arrivée du ski.",
    ],
    "Vallouise": [
        "Le nom du village est un hommage royal : la vallée, appelée « Vallis Puta » (« vallée mauvaise ») à l'époque des persécutions contre les Vaudois qui s'y étaient réfugiés, fut rebaptisée « Vallis Loysia » — Vallouise — en l'honneur de Louis XI, qui fit cesser les massacres à la fin du XVe siècle.",
        "C'est l'une des portes du massif des Écrins et un haut lieu historique de l'alpinisme : depuis la vallée, on accède à la Barre des Écrins (4 102 m), gravie pour la première fois par l'Anglais Edward Whymper en 1864.",
    ],
    "Sainte-Anne-la-Condamine": [
        "Détail insolite : de 1964 à 2013, la Marine nationale a exploité à La Condamine un « Centre de Réoxygénation des Sous-Mariniers » — les équipages de sous-marins venaient y reprendre l'air (et skier à Sainte-Anne) après leurs longues missions en plongée.",
        "Le village est surplombé depuis près de 150 ans par les spectaculaires fortifications de Tournoux, accrochées à la falaise, joyau du patrimoine militaire de l'Ubaye.",
    ],
    "Réallon": [
        "La station est en balcon direct au-dessus du lac de Serre-Ponçon, l'un des plus grands lacs artificiels d'Europe : depuis les pistes, la vue plonge sur le lac — un panorama rare pour une station de ski.",
        "C'est l'une des plus jeunes stations des Alpes du Sud : elle n'a été inaugurée qu'en décembre 1985, aux portes du Parc national des Écrins.",
    ],
    "Chaillol": [
        "Exposée plein sud, avec des pistes ensoleillées jusque tard dans la journée, c'est la « station soleil » du Champsaur, blottie au pied du Vieux Chaillol (3 163 m), dans le Parc national des Écrins.",
    ],
    "Saint-Léger-les-Mélèzes": [
        "La station a été créée en 1966 par le maire du village, Jean Ariey, et son conseil municipal, avec un objectif : enrayer l'exode rural. Pari réussi — c'est l'une des stations les plus proches de Marseille (environ 1h30 d'autoroute).",
        "Le village doit son nom à sa forêt de mélèzes et abrite dans une ancienne ferme un écomusée étonnant, le « Refuge des animaux » : plus de 300 mammifères, oiseaux et reptiles naturalisés, et une belle collection d'insectes locaux.",
    ],
    "Ancelle": [
        "C'est la doyenne du Champsaur : née au milieu des années 1950 (premier téléski des Taillas en 1956), c'est la première station de ski de la vallée, vite adoptée par les Marseillais et les Gapençais.",
        "Le village est bien plus ancien que ses pistes : sa première mention écrite remonte à l'an 739, dans le testament d'Abbon, un aristocrate gallo-romain.",
    ],
    "Chabanon": [
        "La station propose du ski nocturne sur environ 3 km de pistes éclairées — l'occasion de skier sous un ciel étoilé réputé parmi les plus purs de France, dans la vallée de la Blanche.",
    ],
    "Roubion-Les Buisses": [
        "La station des Buisses, créée en 1975, est la dernière-née des Alpes-Maritimes. Elle dépend du spectaculaire village perché de Roubion, accroché à sa falaise depuis des siècles : fondé vers 800 av. J.-C. par les Celto-Ligures, il conserve ses remparts du XIIe siècle.",
        "En 2014, un trésor gaulois vieux de 2 300 ans a été découvert sur la commune, en plein Mercantour.",
    ],
    "Arvieux-en-Queyras": [
        "Le hameau de La Chalp abrite depuis 1920 la coopérative « L'Alpin chez lui – Les Jouets du Queyras », fondée par un pasteur pour lutter contre l'exode hivernal : les fameux jouets en bois peints à la main y sont toujours fabriqués, plus d'un siècle plus tard.",
        "La vallée d'Arvieux mène au col d'Izoard (2 360 m) et à sa Casse Déserte, l'un des cols les plus mythiques du Tour de France, sur la Route des Grandes Alpes inaugurée en 1934.",
    ],
    "Aiguilles": [
        "Surnommé « le village des Américains » : après les incendies qui le dévastèrent (1746, 1829), de nombreux habitants partirent faire fortune aux Amériques... et revinrent construire les belles villas bourgeoises à ferronneries qui font encore le charme du village.",
        "À ne pas manquer : la « Maison Eiffel », curieuse maison métallique attribuée aux ateliers de Gustave Eiffel, en plein cœur du bourg. On chuchote qu'elle serait brûlante l'été et glaciale l'hiver.",
    ],
    "Dormillouse-Freissinières": [
        "Dormillouse est le seul hameau habité à l'année au cœur du Parc national des Écrins — et probablement le village le plus isolé de France : aucune route n'y mène, on y accède uniquement à pied (environ 45 min l'été, bien plus en raquettes l'hiver), sans réseau électrique.",
        "Ancien refuge des Vaudois, le hameau a accueilli en 1825, dans le temple dit « maison de Félix Neff », la première école normale protestante de France.",
    ],
    "Larche": [
        "Dernier village avant le col de Larche (1 991 m) et la frontière italienne, Larche a été entièrement détruit par les combats de la fin de la Seconde Guerre mondiale — le village est resté occupé jusqu'au printemps 1945 — puis intégralement reconstruit par ses habitants.",
        "C'est aujourd'hui l'un des plus grands sites nordiques des Alpes-de-Haute-Provence, avec environ 40 km de pistes de ski de fond entre 1 700 et 2 000 m, aux portes du Parc national du Mercantour.",
    ],
    "L'Audibergue": [
        "Avec sa voisine Gréolières, c'est l'une des deux stations de ski les plus proches du littoral azuréen : à moins d'une heure de Cannes et de Grasse, on y skie en véritable balcon sur la Côte d'Azur, avec vue sur les îles de Lérins, l'Estérel et toute la Méditerranée.",
        "La station est reliée à sa jumelle La Moulière par une piste de crête d'où l'on embrasse d'un côté les sommets enneigés du Mercantour, de l'autre le lac de Saint-Cassien et le littoral.",
    ],
    "La Roche-de-Rame": [
        "Le village possède un joyau rare : un lac naturel d'origine glaciaire en plein cœur du village, alimenté par des sources souterraines, où l'on se baigne l'été dans une eau qui peut atteindre 24 °C.",
        "La légende locale voulait que ce soit un « lac sans fond » : en 1990, à la demande de la mairie, des plongeurs de l'armée ont exploré le fond... et démenti le mythe (25 m de profondeur, tout de même).",
    ],
    "Les Deux Alpes": [
        "La station possède le plus grand glacier skiable d'Europe : le glacier du Mont-de-Lans, environ 100 hectares entre 2 900 et 3 600 m, si peu pentu et peu crevassé qu'on y skie même en plein été.",
        "Du haut du glacier (3 600 m) au village de Mont-de-Lans (1 300 m), on peut enchaîner environ 2 300 m de dénivelé skis aux pieds sans reprendre une seule remontée — l'un des plus longs dénivelés sur piste au monde.",
        "Le nom ne désigne pas deux montagnes : les « deux Alpes », ce sont les deux alpages d'altitude des villages de Mont-de-Lans et de Vénosc, sur le plateau desquels la station s'est construite.",
    ],
    "La Plagne": [
        "La Plagne abrite la seule piste de bobsleigh, luge et skeleton de France : construite pour les JO d'Albertville 1992 (1 500 m, 19 virages), ouverte au grand public en fin de journée... et de nouveau olympique pour les Jeux des Alpes françaises 2030.",
        "L'histoire du bob y est plus ancienne qu'on ne le croit : dans les années 1950, les mineurs de la mine de plomb argentifère dévalaient déjà les routes gelées en bobsleigh. La piste olympique a été construite à l'endroit exact où ils s'élançaient, 50 ans plus tôt.",
        "Créée en 1961 pour sauver une vallée frappée par le déclin des mines et l'exode rural, La Plagne est devenue l'un des plus grands domaines du monde (Paradiski).",
    ],
    "Les Arcs": [
        "La station est née de la rencontre entre Robert Blanc, guide de haute montagne et berger de Tarentaise, et Roger Godino, polytechnicien, qui découvrit le site en 1961 et décida d'y bâtir une station.",
        "C'est l'œuvre majeure de Charlotte Perriand, la légendaire designer qui collabora avec Le Corbusier : de 1967 à la fin des années 1980, elle dirigea l'architecture des Arcs (avec les conseils de Jean Prouvé), imaginant les fameux immeubles étagés épousant la pente. Un patrimoine aujourd'hui mondialement reconnu.",
    ],
    "Flaine": [
        "Surnommée « le Bauhaus des Alpes », la station a été dessinée par Marcel Breuer, maître du Bauhaus et l'un des plus grands architectes du XXe siècle. Labellisée Patrimoine du XXe siècle en 2003, elle fut conçue sans voiture, sur un site entièrement vierge.",
        "Flaine est un musée à ciel ouvert : une « Tête de femme » monumentale de Picasso trône sur le Forum, aux côtés du « Boqueteau des 7 arbres » de Dubuffet et des « Trois Hexagones » de Vasarely, posés sur le toit de la galerie marchande.",
    ],
    "La Clusaz": [
        "C'est une véritable pépinière de champions : Candide Thovex, légende mondiale du freestyle, y a grandi sur les pentes de Balme (une piste porte désormais son nom), aux côtés d'Edgar Grospiron (or olympique en bosses en 1992), Régine Cavagnoud (championne du monde de super-G 2001) ou Vincent Vittoz.",
        "La Clusaz est aussi le berceau du reblochon fermier : certaines fermes de production se visitent... skis aux pieds.",
    ],
    "Le Grand-Bornand": [
        "C'est la capitale française du biathlon : depuis 2013, la Coupe du monde y fait étape sur le stade Sylvie Becaert, un stade démontable en plein village — le « circuit de Monaco » du biathlon — réputé pour l'ambiance la plus folle du circuit mondial. Le village accueillera les épreuves de biathlon des JO 2030.",
        "Le village est aussi une terre historique du reblochon fermier AOP : le fromage y est mentionné officiellement dès 1699, dans un bail de location de propriété.",
    ],
    "Les Saisies": [
        "Le 1er août 1944, le col des Saisies fut le théâtre de l'un des plus importants parachutages d'armes de la Résistance française : en plein jour, des dizaines de bombardiers B17 américains larguèrent près de 900 containers pour armer le maquis du Beaufortain du capitaine Bulle. Un monument commémore l'opération.",
        "Le plateau a accueilli les épreuves de ski de fond et de biathlon des JO d'Albertville 1992 — et c'est le fief de la famille Piccard : Franck Piccard, enfant du pays, est devenu en 1988 à Calgary le tout premier champion olympique de super-G de l'histoire.",
    ],
    "La Rosière": [
        "On y skie entre deux pays : le domaine transfrontalier Espace San Bernardo relie La Rosière à La Thuile, en Italie, via le col du Petit-Saint-Bernard. La liaison à ski fonctionne depuis 1984, alors que la route du col est fermée tout l'hiver.",
        "Le col du Petit-Saint-Bernard (2 188 m) est chargé d'histoire : un cercle de pierres de l'âge du fer y est encore visible, une voie romaine le traversait... et selon la légende, Hannibal et ses éléphants y seraient passés en 218 av. J.-C. pour marcher sur Rome.",
    ],
    "Valloire": [
        "C'est la capitale française de la sculpture éphémère : chaque janvier depuis les années 1980, des artistes du monde entier s'affrontent lors des concours internationaux de sculptures sur glace puis sur neige — une tradition importée du Québec. L'été, place au concours de sculptures... sur paille et foin.",
        "Le village est le camp de base du mythique col du Galibier (2 642 m), l'un des géants du Tour de France, qu'on atteint après avoir franchi le col du Télégraphe.",
    ],
    "Saint-Gervais": [
        "Le Tramway du Mont-Blanc, taillé à la pioche dans la pente entre 1905 et 1913, est le train le plus haut de France : il grimpe jusqu'au Nid d'Aigle (2 400 m), au pied du glacier de Bionnassay. L'ambition initiale des bâtisseurs ? Atteindre... le sommet du Mont Blanc. La Première Guerre mondiale y mit fin.",
        "Peu le savent : le sommet du Mont Blanc (4 806 m) se trouve en partie sur le territoire de la commune de Saint-Gervais, qui en est la voie d'accès la plus directe — tout en étant aussi une cité thermale réputée.",
    ],
    "Les Houches": [
        "La station abrite la mythique « Verte des Houches », alias piste du Kandahar : tracée pour les Championnats du monde 1937 (les premiers organisés en France), c'est l'une des deux seules pistes françaises historiques de descente masculine de Coupe du monde, avec la Face de Bellevarde. Une noire de 870 m de dénivelé que les meilleurs avalent en deux minutes.",
        "Son nom de « Verte » ne dit rien de sa difficulté : il vient des sapins qui la bordent et donnent à sa glace des reflets verts. « Kandahar », lui, vient de la compétition Arlberg-Kandahar, baptisée en l'honneur d'un général britannique comte de... Kandahar, en Afghanistan.",
    ],
    "Chamrousse": [
        "C'est ici, aux JO de Grenoble 1968, que Jean-Claude Killy est entré dans la légende : triplé en or (descente, géant, slalom) sur les pistes de Casserousse et du Recoin — un exploit qu'aucun skieur masculin n'a réédité aux JO depuis. La descente s'était jouée à 8 centièmes devant son ami Guy Périllat.",
        "Détail d'époque : dès décembre 1967, des milliers de militaires furent envoyés damer les pistes olympiques... à pied.",
    ],
    "Arêches-Beaufort": [
        "Chaque mois de mars depuis 1986, la station accueille la Pierra Menta, la plus mythique course de ski-alpinisme au monde : quatre jours d'ascensions par équipes de deux sur les pentes du Grand-Mont, portée par tout un village et des centaines de bénévoles.",
        "La course tire son nom de la Pierra Menta, spectaculaire dent rocheuse de 150 m qui domine le Beaufortain. La légende raconte que le géant Gargantua, traversant le massif, aurait laissé tomber ce bloc en chemin.",
        "On est aussi ici au pays du beaufort, le « prince des gruyères » : les fermes mettent leur lait en commun deux fois par jour pour le fabriquer à la coopérative.",
    ],
    "Beaufort-sur-Doron": [
        "Beaufort est la capitale du fromage éponyme, le fameux « prince des gruyères » AOP, fabriqué à la coopérative laitière du village avec le lait des vaches tarines et abondances des alpages.",
        "Le territoire, surnommé « le petit Tyrol » pour ses chalets d'alpage, abrite quatre barrages hydroélectriques dont le spectaculaire lac de Roselend, et le hameau classé de Boudin, étagé sur près de 200 m de dénivelé.",
    ],
    "Bonneval-sur-Arc": [
        "C'est le seul village de Savoie classé parmi les « Plus Beaux Villages de France » : chalets de pierre aux toits de lauze, aucun fil électrique ni antenne visible — tout le village est inscrit au patrimoine national.",
        "Perché à 1 800 m au bout de la Haute-Maurienne, il se niche au pied du col de l'Iseran (2 764 m), le plus haut col routier des Alpes. Son hameau de l'Écot, figé dans le temps à 2 000 m, a servi de décor aux films « Belle et Sébastien ».",
    ],
    "Villard-de-Lans": [
        "Berceau de la luge en France, Villard-de-Lans a accueilli les épreuves de luge des JO de Grenoble 1968 sur la piste de la Balmette : 18 courbes, l'unique piste de luge de France à l'époque, considérée par les experts comme la plus belle du monde.",
        "Le Vercors est un haut lieu de la Résistance : le hameau de Valchevrière, camp de maquisards incendié par les nazis en juillet 1944, a été volontairement laissé en l'état, pierres noircies par le feu — seule la chapelle fut épargnée.",
        "La commune a même donné son nom à une vache : la « villarde », race locale à la robe froment, presque disparue après-guerre puis sauvée par des éleveurs passionnés.",
    ],
    "Autrans-Méaudre": [
        "Autrans est le berceau du ski de fond français : le village a accueilli les épreuves nordiques des JO de Grenoble 1968 (fond, biathlon, combiné, saut sur le tremplin du Claret), et la tradition du saut à ski y remonte à 1911 — les tremplins olympiques sont toujours en activité.",
        "Héritière des JO, la Foulée Blanche est née ici, et le domaine nordique dépasse aujourd'hui les 200 km de pistes — l'un des plus grands d'Europe.",
    ],
    "Samoëns": [
        "Le village est la terre des « Frahans », les maîtres tailleurs de pierre du Giffre : réunis en confrérie dès 1659, ils furent appelés sur les plus grands chantiers d'Europe — les fortifications de Vauban, les canaux de Napoléon, jusqu'en Pologne et en Louisiane. Ils parlaient même leur propre langage secret, le mourmé.",
        "Le jardin botanique alpin de la Jaÿsinia, créé en 1906, est un cadeau : Marie-Louise Cognacq-Jaÿ, née à Samoëns et fondatrice de La Samaritaine à Paris, l'offrit à son village natal — sur le coteau même où, enfant, elle gardait ses chèvres. On y trouve plus de 2 000 espèces des montagnes des cinq continents.",
    ],
    "Sixt-Fer-à-Cheval": [
        "Le village, classé parmi les « Plus Beaux Villages de France », a 80 % de son territoire en réserve naturelle — la plus vaste de Haute-Savoie (Sixt-Passy, 10 000 ha), royaume des bouquetins, aigles royaux et gypaètes barbus.",
        "Au bout de la route, au lieu-dit « Le Bout du Monde », s'ouvre le cirque du Fer-à-Cheval : le plus grand cirque montagneux des Alpes, dont les falaises laissent jaillir des dizaines de cascades à la fonte des neiges. Non loin, celle du Rouget, 90 m de chute, est surnommée « la Reine des Alpes ».",
        "La station est reliée au Grand Massif par la piste des Cascades, une bleue de 14 km.",
    ],
    "Brides-les-Bains": [
        "Curiosité : c'est une station thermale à 580 m d'altitude... qui donne accès au plus grand domaine skiable du monde. Choisie comme village olympique des JO d'Albertville 1992, elle a obtenu à cette occasion la télécabine de l'Olympe, qui la relie en une vingtaine de minutes à Méribel et aux 3 Vallées.",
        "Ses sources thermales, connues dès l'époque romaine et exploitées depuis le début du XIXe siècle, ont fait de Brides la station leader en France pour le traitement du surpoids — au point que ses restaurants et hôtels peuvent afficher un « label diététique » unique en France.",
    ],
    "Pralognan-la-Vanoise": [
        "Environ 70 % du territoire de la commune est classé en cœur du Parc national de la Vanoise — le tout premier parc national français, créé en 1963. Bouquetins, chamois et aigles royaux y sont chez eux.",
        "En 1992, le village a accueilli les épreuves de curling des JO d'Albertville (alors sport de démonstration) dans une patinoire construite pour l'occasion, devenue depuis un centre de loisirs où l'on peut toujours s'essayer au curling.",
        "Berceau de l'alpinisme en Savoie, le village est dominé par la Grande Casse (3 855 m), point culminant de la Savoie.",
    ],
    "Val Cenis": [
        "Le col du Mont-Cenis, juste au-dessus, est l'un des plus vieux passages des Alpes : Charlemagne, les pèlerins de la Via Francigena et les armées l'ont emprunté pendant des siècles. C'est Napoléon qui, au début du XIXe siècle, fit transformer l'antique chemin muletier en véritable route carrossable — celle qu'on emprunte encore.",
        "Le magnifique lac turquoise du plateau est artificiel : le barrage construit entre 1962 et 1968 a englouti sous ses eaux le lac naturel, l'hospice séculaire et ses chalets d'alpage. La combe, italienne jusqu'en 1947, n'est redevenue française qu'avec le traité de Paris.",
    ],
    "Bessans": [
        "L'emblème du village est... un diable. En 1857, un chantre facétieux en froid avec le curé sculpta un diable emportant un curé sous le bras et le déposa sous la fenêtre du prêtre. La statuette fit des allers-retours entre les deux fenêtres, jusqu'à ce qu'un touriste de passage la remarque et l'achète. Le commerce était né : les diables de Bessans se sculptent encore aujourd'hui.",
        "Le plateau de Bessans, à 1 750 m, est l'un des grands temples du ski nordique français : plus de 120 km de pistes tracées et un stade de biathlon où s'entraînent les équipes nationales.",
    ],
    "Aussois": [
        "Le village est gardé par la Barrière de l'Esseillon : cinq forts monumentaux bâtis au début du XIXe siècle par le royaume de Piémont-Sardaigne pour... se protéger de la France. Ils portent les prénoms de la famille royale (Victor-Emmanuel, Marie-Christine, Charles-Félix...) et n'ont jamais connu le feu.",
        "Anecdote savoureuse : quand la Savoie devint française en 1860, la France s'engagea à détruire les forts. Elle commença par le fort Charles-Félix... puis s'arrêta là, et occupa militairement les autres pendant des décennies.",
        "Non loin se dresse le monolithe de Sardières, aiguille rocheuse de 93 m surgissant en pleine forêt. C'est à son pied que fut inauguré, le 26 juin 1965, le Parc national de la Vanoise.",
    ],
    "Abondance": [
        "Abondance est probablement la seule commune de France à avoir donné son nom à la fois à une vallée, à un fromage AOP et à une race de vache. Rien que ça.",
        "Le fromage est né à l'abbaye : dès le Moyen Âge, les chanoines défrichèrent la vallée et élaborèrent les secrets de sa fabrication. En 1381, ils en expédièrent quinze quintaux au conclave d'Avignon chargé d'élire un pape.",
        "L'abbaye du XIIe siècle fut, en 1875, le tout premier édifice savoyard classé Monument historique. Son cloître gothique abrite un exceptionnel cycle de peintures murales du XVe siècle — une véritable bande dessinée médiévale.",
    ],
    "Le Revard": [
        "Le Revard est considéré comme l'une des toutes premières stations de ski de France : dès l'hiver 1908-1909, le chemin de fer à crémaillère inauguré en 1892 se mit à monter les skieurs depuis Aix-les-Bains, alors qu'il ne circulait jusque-là que l'été.",
        "La station s'équipa très tôt d'une patinoire, d'une piste de bobsleigh, de tremplins de saut... et, faute de remontées mécaniques dans les années 1930, de deux autochenilles qui tractaient les skieurs. En 1935, la Fédération française de ski y créa le premier centre de formation des moniteurs.",
    ],
    "La Féclaz": [
        "Avec Le Revard et Saint-François-de-Sales, La Féclaz forme le domaine Savoie Grand Revard : environ 150 km de pistes tracées, l'espace nordique le plus fréquenté de France.",
        "Ses immenses forêts d'épicéas et ses plateaux enneigés, en plein Parc naturel régional du Massif des Bauges, lui valent le surnom de « Petit Canada » savoyard.",
    ],
    "Savoie Grand Revard": [
        "Le domaine regroupe trois stations-villages du massif des Bauges — La Féclaz, Le Revard et Saint-François-de-Sales — pour former, avec environ 150 km de pistes, l'espace nordique le plus fréquenté de France.",
        "Surnommé le « Petit Canada » savoyard pour ses vastes forêts d'épicéas, le plateau offre en prime des panoramas plongeants sur le lac du Bourget.",
    ],
    "Les Contamines-Montjoie": [
        "Les deux tiers du territoire de la commune sont classés en réserve naturelle : créée en 1979, celle des Contamines-Montjoie est la plus haute réserve naturelle de France et le seul espace protégé de ce type sur le massif du Mont-Blanc, s'étageant du village (1 100 m) à l'aiguille de Tré-la-Tête (3 892 m).",
        "Au fond de la vallée, le sanctuaire baroque de Notre-Dame de la Gorge marque la fin de la route et le départ des sentiers : c'est un passage entre France et Italie depuis l'Antiquité — une voie romaine y est encore visible, aujourd'hui empruntée par le Tour du Mont-Blanc.",
    ],
    "Valmorel": [
        "Née en 1976 sur les plans de l'architecte Michel Bezançon, Valmorel a inauguré un genre nouveau : la « station de 4e génération », conçue comme un village savoyard traditionnel — bois, pierre, toits de lauze, fresques en trompe-l'œil et rue du Bourg entièrement piétonne. Son succès a lancé la mode de l'architecture néo-régionale en montagne.",
        "Le projet est né de l'association de deux communes voulant enrayer le dépeuplement de la vallée. La station est aujourd'hui reliée à Saint-François-Longchamp, Doucy et Celliers au sein du Grand Domaine.",
    ],
    "Orelle": [
        "C'est la seule des 3 Vallées à ne pas être... dans les 3 Vallées : perchée en Maurienne, Orelle est la porte d'entrée « par l'arrière » du plus grand domaine skiable du monde, reliée à Val Thorens par-dessus la crête.",
        "Depuis le village, deux télécabines parmi les plus rapides de France hissent skieurs et piétons jusqu'à la Cime Caron (3 200 m) en une vingtaine de minutes, pour un panorama à 360° sur plus de mille sommets — du Mont Blanc aux Alpes du Sud.",
        "Le dénivelé entre Orelle et la Pointe du Bouchet, point culminant des 3 Vallées, dépasse 1 400 m.",
    ],
    "Peisey-Vallandry": [
        "C'est ici que part le Vanoise Express, l'un des plus gros téléphériques du monde : deux cabines à deux étages de 200 personnes chacune, qui franchissent la vallée du Ponturin presque à plat, sans aucun pylône intermédiaire, à 380 m au-dessus du sol et à 45 km/h. Traversée : moins de 4 minutes.",
        "Inauguré fin 2003, c'est lui qui a donné naissance à Paradiski en reliant Les Arcs à La Plagne — plus de 400 km de pistes d'un coup.",
    ],
    "Peisey-Nancroix": [
        "La commune abrite la gare motrice du Vanoise Express, l'un des plus gros téléphériques du monde : ses cabines à deux étages emportent 200 personnes et traversent la vallée du Ponturin sans le moindre pylône intermédiaire.",
        "L'ouvrage a été conçu pour franchir la vallée sans la dénaturer — c'est lui qui, depuis 2003, relie Les Arcs à La Plagne pour former le domaine Paradiski.",
    ],
    "La Tania": [
        "C'est la dernière-née des 3 Vallées : sortie de terre en pleine forêt à la fin des années 1980, elle fut inaugurée en 1990-91 puis servit de village olympique annexe pendant les JO d'Albertville 1992, accueillant athlètes et journalistes.",
        "Son architecture est signée Jacques Labro — le même architecte qu'Avoriaz. Son nom vient du hameau de la Tagna, qui signifierait « la tanière de l'ours » en patois savoyard.",
    ],
    "Sainte-Foy-Tarentaise": [
        "Discrète voisine de Val d'Isère, Tignes et Les Arcs, Sainte-Foy est une station confidentielle née seulement en 1990 — et un paradis reconnu du freeride, avec de vastes espaces non damés et des itinéraires mythiques comme la descente sur Le Monal.",
        "Le hameau du Monal, perché à 1 874 m et classé pour son intérêt patrimonial et paysager, est l'un des plus beaux exemples de « montagnettes » de Tarentaise : des chalets de pierre et de bois des XVIIIe et XIXe siècles blottis autour d'une chapelle, face au glacier du Mont Pourri.",
    ],
    "Champagny-en-Vanoise": [
        "Le village abrite une tour de glace artificielle, l'un des rares équipements du genre en France, qui accueille des compétitions internationales de cascade de glace — et où les débutants peuvent s'initier à l'escalade sur glace.",
        "Son église baroque Saint-Sigismond, reconstruite en 1683, cache derrière une façade très sobre un intérieur éclatant d'or et d'angelots sculptés — un pur trésor de l'art baroque savoyard.",
        "À quelques kilomètres, le vallon de Champagny-le-Haut, ancienne vallée glaciaire fermée par la Grande Casse, est classé site naturel depuis 1992 et sert de porte d'entrée au Parc national de la Vanoise.",
    ],
    "Saint-Sorlin-d'Arves": [
        "Le village est blotti au pied du col de la Croix de Fer, l'un des cols mythiques du Tour de France, face aux trois Aiguilles d'Arves — silhouette dentelée emblématique de la Maurienne — et au glacier de l'Étendard.",
        "Sa coopérative fromagère de la vallée des Arves se visite : on y suit toutes les étapes de fabrication du beaufort et on descend dans les caves d'affinage.",
        "Le domaine des Sybelles, dont Saint-Sorlin est l'une des portes d'entrée, est né en 2003 de la liaison de six stations-villages.",
    ],
    "Le Corbier": [
        "Sortie de terre en un temps record — premiers travaux en 1966, inauguration en décembre 1967 —, c'est une « station intégrée » de troisième génération, 100 % piétonne et skis aux pieds, avec une galerie commerciale couverte reliant le haut et le bas de la station.",
        "Ses bâtiments portent des noms qui trahissent l'époque de la conquête spatiale : Ariane, Spoutnik, Soyouz, Baïkonour, Cosmos, Pégase...",
        "Le projet est né d'une urgence : le village de Villarembert se vidait, l'école n'avait plus que sept élèves et le préfet proposait sa fusion avec la commune voisine.",
    ],
    "La Toussuire": [
        "Perchée sur un vaste plateau d'alpage plein soleil à environ 1 750 m, La Toussuire est une habituée du Tour de France : la montée depuis Saint-Jean-de-Maurienne fait 18 km pour près de 1 100 m de dénivelé, et l'arrivée y a couronné plusieurs grands noms du peloton.",
        "Elle est l'une des six stations-villages reliées au sein du domaine des Sybelles, né en 2003.",
    ],
    "Saint-François-Longchamp": [
        "La station est posée sur la route du col de la Madeleine (1 993 m), l'un des géants du Tour de France. Détail méconnu : la première route de pierre fut construite vers 1938 par des réfugiés de la guerre d'Espagne, et le goudronnage ne fut achevé qu'en 1969, pour le premier passage du Tour.",
        "Le col relie deux vallées et deux stations : Valmorel côté Tarentaise, Saint-François-Longchamp côté Maurienne — désormais reliées à ski au sein du Grand Domaine.",
        "C'est près d'ici, en août 1921, que fut tué le dernier ours des Alpes françaises. Sa dépouille naturalisée est aujourd'hui exposée au muséum d'histoire naturelle de Grenoble.",
    ],
    "Valfréjus": [
        "C'est ici qu'est né le skwal en 1992 : une planche unique sur laquelle on se tient face à la pente, les deux pieds l'un devant l'autre, inventée par Patrick « Thias » Balmain, moniteur de Modane, et Manuel Jammes.",
        "La station a aussi vu naître le speed-riding, spectaculaire mélange de ski et de parapente — elle revendique la seule école de speed-riding au monde.",
        "Créée en 1983 sur le hameau du Charmaix, c'est l'une des plus jeunes stations de France. Son nom vient de la Pointe du Fréjus, sommet frontalier culminant à 2 936 m.",
    ],
    "La Norma": [
        "Ouverte en 1971 au-dessus de Modane, La Norma est une station entièrement piétonne : on y circule à pied ou à ski, jamais en voiture.",
        "Elle fait partie de l'Espace Haute Maurienne Vanoise, un forfait commun partagé avec Aussois, Val Cenis, Valfréjus et Bonneval-sur-Arc.",
    ],
    "Valmeinier": [
        "Le village a failli disparaître : à la fin des années 1970, il ne comptait plus que quelques dizaines d'habitants permanents. La création de la station a inversé la tendance — c'est aujourd'hui l'une des plus récentes de Maurienne.",
        "Autrefois, certains paysans de la vallée partaient l'hiver exercer un métier inattendu : ramoneurs, travaillant par deux, surtout dans la région parisienne et en Bretagne.",
        "Avec Valloire, Valmeinier forme le domaine Galibier-Thabor, environ 160 km de pistes.",
    ],
    "Les Karellis": [
        "Voici une station née d'une utopie : créée au milieu des années 1970 par Pierre Lainé, figure du tourisme social, elle fut conçue non pour le profit mais pour le partage — pas de spéculation immobilière, pas de voitures, des séjours tout compris en villages de vacances.",
        "Le modèle est resté unique en France : les terrains appartiennent à la commune de Montricher-Albanne, et les commerces et restaurants sont gérés en coopérative.",
    ],
    "Les Carroz": [
        "La station a été créée dès 1936, et son premier téléski, inauguré en 1939, était alors le plus long d'Europe : 1 600 m de long, douze minutes de montée.",
        "Avant le ski, la vallée vivait de l'horlogerie : de nombreux ouvriers horlogers travaillaient en sous-traitance pour les fabriques de la région de l'Arve.",
        "Perchée sur un plateau ensoleillé face au Mont Blanc, c'est l'une des portes historiques du Grand Massif (265 km de pistes avec Flaine, Samoëns, Morillon et Sixt).",
    ],
    "Morillon": [
        "Village-station de la vallée du Giffre, Morillon fait partie du Grand Massif, l'un des plus vastes domaines reliés de France (environ 265 km de pistes avec Flaine, Les Carroz, Samoëns et Sixt-Fer-à-Cheval).",
        "L'été, le lac aménagé de Morillon, avec sa plage surveillée en pleine montagne, est l'un des points de rendez-vous les plus prisés de la vallée.",
    ],
    "Praz-de-Lys Sommand": [
        "La station est double : deux plateaux d'alpage à 1 500 m, Praz de Lys côté Taninges et Sommand côté Mieussy, reliés l'hiver par les pistes et l'été par le col de la Ramaz.",
        "Ce col est un habitué du Tour de France, qui l'a franchi à plusieurs reprises. Théâtre en 2003 d'une échappée mémorable de Richard Virenque, il offre au sommet un panorama plein cadre sur le massif du Mont-Blanc.",
        "Le domaine nordique du plateau, avec ses dizaines de kilomètres de pistes tracées, compte parmi les plus beaux de Haute-Savoie.",
    ],
    "Saint-Jean-d'Aulps": [
        "Le village s'est construit autour de l'abbaye d'Aulps, fondée à la fin du XIe siècle et devenue l'un des plus importants monastères de la Savoie médiévale.",
        "Son destin est rocambolesque : vendue comme bien national après 1792, l'abbatiale fut pillée et démolie par les villageois en 1823 pour servir de carrière de pierres — les matériaux reconstruisirent l'église du village et empierrèrent les routes. Classée Monument historique en 1902, elle abrite aujourd'hui un centre d'interprétation unique en France sur la vie quotidienne des moines de montagne.",
    ],
    "Thollon-les-Mémises": [
        "Le village est millénaire : son nom est attesté avant l'an mil. Ce n'est qu'en 1995 qu'il a pris le nom de « Thollon-les-Mémises », en référence à sa station de ski.",
        "Les rochers des Mémises constituent le tout dernier relief préalpin du territoire français en allant vers le nord — d'où le panorama plongeant sur le lac Léman et la Suisse depuis les pistes.",
    ],
    "Montriond": [
        "Le lac de Montriond, étendue turquoise cernée de falaises et de forêts, est le plus grand lac du massif du Chablais. Au fond de la vallée, la cascade d'Ardent, site classé, se contemple depuis une passerelle en bois suspendue au-dessus du vide.",
        "Dans les falaises voisines subsistent les galeries d'anciennes ardoisières, exploitées jusque dans les années 1950 — l'ardoise a longtemps couvert les toits de toute la vallée.",
        "Juste au-dessus, le hameau des Lindarets est célèbre pour ses chèvres, qui déambulent librement entre les chalets tout l'été.",
    ],
    "La Chapelle d'Abondance": [
        "Le village possède certaines des fermes traditionnelles les plus spectaculaires de France : d'immenses bâtisses à galeries de bois sculptées, coiffées de hautes cheminées pyramidales en planches sous lesquelles on fumait et affinait les fromages.",
        "Son église Saint-Maurice arbore un clocher à triple bulbe, signature du baroque savoyard d'influence austro-italienne.",
        "La station est l'une des portes d'entrée des Portes du Soleil, le plus grand domaine transfrontalier au monde, qui relie une douzaine de stations françaises et suisses.",
    ],
    "Bernex": [
        "Le village vit sous le regard de la Dent d'Oche (2 222 m), sommet emblématique du Chablais dont la silhouette domine tout le paysage. Depuis le haut des pistes, la vue embrasse le lac Léman d'un côté et le Mont Blanc de l'autre.",
        "On y déguste le berthoud, plat emblématique du Chablais : du fromage d'Abondance fondu au four avec un trait de vin blanc et une pointe d'ail.",
    ],
    "Bellevaux-Hirmentaz": [
        "Le lac de Vallon, joyau de la vallée du Brevon, est né d'une catastrophe : un gigantesque glissement de terrain en 1943 barra la vallée et engloutit une partie du hameau, créant le lac que l'on voit aujourd'hui.",
        "La commune abrite aussi les vestiges de la chartreuse de Vallon, monastère fondé au XIIe siècle, et un jardin alpin consacré à la flore locale.",
    ],
    "Notre-Dame-de-Bellecombe": [
        "Le premier remonte-pente du village, un « télétraîneau » mis en service à Noël 1937, existe toujours : exposé devant la mairie, il a été remis en état par une poignée de passionnés et glisse encore l'hiver.",
        "Le village abrite aussi la Maison des Contes de Fées, musée insolite peuplé de saynètes animées et de personnages mis en scène par des jeux de lumière.",
        "La station fait partie de l'Espace Diamant, qui relie à ski six stations-villages du Val d'Arly et du Beaufortain (environ 192 km de pistes).",
    ],
    "Crest-Voland": [
        "Longtemps simple hameau de Saint-Nicolas-la-Chapelle, difficile d'accès de l'autre côté des gorges de l'Arly, Crest-Voland possède sa propre église depuis 1585 et n'est devenu paroisse autonome qu'au XVIIe siècle.",
        "Son territoire correspond à une ancienne zone d'essartage : on y semait autrefois les grains sur brûlis, une pratique ancestrale de défrichement.",
    ],
    "Flumet": [
        "Perché au-dessus des gorges de l'Arly, Flumet a longtemps été un bourg de passage stratégique entre la Savoie et le Faucigny, avec ses hautes maisons accrochées au bord du vide.",
        "Le village fait partie du domaine du Val d'Arly, relié à Notre-Dame-de-Bellecombe et Praz-sur-Arly, lui-même intégré à l'Espace Diamant (environ 192 km de pistes).",
    ],
    "Praz-sur-Arly": [
        "Voisine immédiate de la très chic Megève, Praz-sur-Arly a gardé son visage de village de montagne — et son domaine relie Flumet et Notre-Dame-de-Bellecombe au sein du Val d'Arly.",
        "La plaine du village est un haut lieu du vol libre : ses vastes espaces dégagés face au massif du Mont-Blanc en font l'un des sites de parapente et de montgolfière les plus prisés des Alpes du Nord.",
    ],
    "Combloux": [
        "C'est Victor Hugo qui lui a offert son surnom : « la perle des Alpes dans son écrin de glaciers ». Le village fait face au Mont Blanc, avec un panorama à 360° sur les Aravis et les aiguilles de Warens.",
        "Son église Saint-Nicolas possède l'un des plus beaux clochers à bulbe de Savoie : 45 mètres de haut, double bulbe, galeries octogonales et flèche métallique faite de milliers de plaquettes d'acier. Classé Monument historique depuis 1971.",
        "Le village abrite le premier plan d'eau biotope de France ouvert à la baignade : plus de 10 000 plantes aquatiques y régénèrent l'eau, sans le moindre produit chimique.",
    ],
    "La Giettaz": [
        "Petit village-station niché au pied du col des Aravis, La Giettaz relie son domaine à Megève et Combloux au sein des Portes du Mont-Blanc.",
        "Son église Saint-Pierre-aux-Liens, joyau du baroque savoyard, abrite un retable spectaculaire — le village est aussi une étape du Sentier du Baroque du Val d'Arly.",
    ],
    "Hauteluce": [
        "Le village est une étape des « Chemins du Baroque » : son église Saint-Jacques d'Assyrie, classée Monument historique, aligne clocher à bulbe, trompe-l'œil en façade, retable à baldaquin et chaire en noyer.",
        "Au centre du village se dresse un tilleul spectaculaire planté à la Révolution — il a donc plus de deux siècles.",
        "Hauteluce a la particularité d'ouvrir sur deux domaines skiables distincts : Les Saisies et l'Espace Diamant d'un côté, le col du Joly et Les Contamines de l'autre.",
    ],
    "Les 7 Laux": [
        "La station est née de la volonté d'un syndicat de sept communes voulant développer leur montagne : il fallut près de quinze ans entre le projet initial (1962) et les premiers lits touristiques (1977).",
        "Elle est répartie sur trois sites et deux versants — Prapoutel et Pipay côté Grésivaudan, Le Pleynet côté Haut-Bréda — ce qui en fait le plus grand domaine skiable de la chaîne de Belledonne.",
        "Prapoutel et Le Pleynet ont chacune accueilli une arrivée d'étape du Tour de France, en 1980 et 1981.",
    ],
    "Col de Porte": [
        "Le col abrite l'un des observatoires de la neige les plus précieux au monde : le Centre d'études de la neige de Météo-France y mesure le manteau neigeux sans interruption depuis l'hiver 1960-61, livrant l'une des plus longues séries nivologiques existantes.",
        "Ces données sont devenues un témoin du changement climatique : en soixante ans, l'épaisseur moyenne de neige y a diminué d'environ 40 cm et la température hivernale a gagné environ 1 °C.",
        "Le site est si précieux qu'il est protégé par un grillage — pour éviter que les skieurs de la station voisine ne viennent piétiner la neige à étudier.",
    ],
    "Saint-Pierre-de-Chartreuse": [
        "Le massif de la Chartreuse est l'un des berceaux du ski français : dès 1907, des skieurs dévalaient les prairies du Sappey, et en 1927 le massif comptait déjà trois stations — dont Saint-Pierre-de-Chartreuse, équipée d'une piste de bobsleigh à Perquelin.",
        "Le village est surtout connu pour le monastère de la Grande Chartreuse, maison mère de l'ordre fondé en 1084, dont les moines gardent le secret de la fameuse liqueur verte.",
    ],
    "Semnoz - Annecy": [
        "Surnommée « le balcon des Alpes », la station domine Annecy à seulement vingt minutes de la ville — et depuis le crêt de Châtillon (1 699 m), le panorama embrasse le Mont Blanc, les Aravis, le Jura... et trois des grands lacs de Savoie : Annecy, Le Bourget et une partie du Léman.",
        "Le tourisme y est ancien : le premier hôtel-restaurant du Semnoz accueillait déjà les curieux en 1872, bien avant que les premières pistes ne soient aménagées à la fin des années 1960.",
        "Fait rare pour une station de ski : on peut y monter en bus urbain depuis Annecy, skis sur le dos.",
    ],
    "Corrençon-en-Vercors": [
        "Dernier village avant les Hauts Plateaux, Corrençon a des airs de bout du monde : c'est la porte d'entrée de la réserve naturelle des Hauts Plateaux du Vercors, la plus grande réserve naturelle terrestre de France métropolitaine.",
        "Curiosité estivale : le village abrite un golf 18 trous en pleine montagne, taillé entre clairières et forêt d'épicéas, souvent cité parmi les plus beaux parcours de montagne d'Europe.",
    ],
    "Les Aillons-Margeriaz": [
        "La station a la particularité d'être double, sur deux versants différents et deux montagnes distinctes : Aillons-Margériaz 1000 sur le mont Pelat et Aillons-Margériaz 1400 sur le mont Margériaz, séparés par une douzaine de kilomètres. Nées séparément (1964 puis 1980), les deux stations ont fusionné en 1990.",
        "Le domaine se trouve au cœur du Parc naturel régional du Massif des Bauges, labellisé Géoparc mondial UNESCO pour la richesse de son patrimoine géologique — le mont Margériaz est notamment célèbre pour ses lapiaz et son réseau de gouffres.",
    ],
    "Auris-en-Oisans": [
        "Le village est surnommé le « Nid d'aigle » : il est perché sur une vallée suspendue creusée par le glacier de la Romanche. Jusqu'en 1895, on n'y accédait que par un sentier vertigineux, « la cheminée d'Auris ».",
        "La station est bordée par la forêt de Piégut, réputée être la plus haute forêt d'épicéas d'Europe.",
        "Le nom d'Auris viendrait tout simplement de « à l'abri » — et la station, créée en 1970, revendique environ 300 jours de soleil par an, face à la Meije et aux Écrins.",
    ],
    "Alpe du Grand Serre": [
        "C'est l'une des plus anciennes stations du Dauphiné : le premier téléski, celui du Petit Mollard, fut construit dès 1937, accompagné d'un hôtel de 60 chambres. On skiait déjà sur ces pentes bien avant, depuis la fin du XIXe siècle.",
        "La station se trouve sur la commune au nom peu engageant de La Morte — un nom qui vient de la géologie : le vallon est une « vallée morte », abandonnée par ses eaux après la fonte des glaciers.",
        "Ici, pas de grand ensemble urbain : la station est éparpillée en hameaux (la Blache, le Couvent, le Désert...) entre lesquels les exploitations agricoles reprennent leurs droits l'été.",
    ],
    "Lans-en-Vercors": [
        "Lans a inventé un modèle : le « stade de neige », une station de proximité sans hébergement, pensée pour les skieurs à la journée avec des équipements volontairement légers pour ne pas dénaturer le site. Le concept y a pris ce nom officiel en 1975.",
        "Les téléskis y ont été délibérément préférés aux télésièges, par souci de rationalité — pour maintenir des tarifs accessibles.",
    ],
    "Gresse-en-Vercors": [
        "Le village-station est dominé par le Grand Veymont (2 341 m), point culminant du massif du Vercors, dont l'immense muraille rocheuse ferme l'horizon.",
        "Il se trouve aux portes de la réserve naturelle des Hauts Plateaux du Vercors, plus vaste réserve naturelle terrestre de France métropolitaine — territoire des bouquetins réintroduits et des grands espaces sans route.",
    ],
    "Col de Rousset": [
        "Le col est le point de départ de la Grande Traversée du Vercors, qui rejoint Villard-de-Lans à ski de fond l'hiver, à VTT ou à cheval l'été, en franchissant les hauts plateaux.",
        "À quelques kilomètres se trouve le stade de biathlon Raphaël Poirée, du nom du quadruple champion du monde, qui a grandi dans la région.",
        "Le col marque une frontière climatique nette : d'un côté le Vercors humide et boisé, de l'autre le Diois et ses paysages déjà méditerranéens.",
    ],
    "Font d'Urle": [
        "Surnommé « la petite Laponie », ce plateau d'alpage aux allures de toundra est l'un des meilleurs spots de snowkite de France : les crêtes balayées par le vent offrent une aérologie remarquable pour se faire tracter par une voile.",
        "Hors saison, le plateau dévoile un spectaculaire paysage karstique — lapiaz sculptés par l'érosion et scialets, ces gouffres verticaux typiques du Vercors — et l'on y croise des mouflons sur les crêtes.",
    ],
    "Lus-la-Jarjatte": [
        "Le vallon de la Jarjatte est un site inscrit : une station-village minuscule blottie au fond d'un cirque, entourée par les plus hauts sommets de la Drôme.",
        "Le hameau se trouve tout près des sources du Buëch, à la charnière entre le Vercors à l'ouest et le Dévoluy à l'est.",
    ],
    "Montchavin-Les Coches": [
        "Montchavin est né d'un pari : plutôt que de bâtir une station neuve en altitude, le maire choisit en 1972 de faire renaître un vieux hameau déserté et à moitié en ruines. Le village a gardé ses chalets de bois et de pierre, sa chapelle et même une ferme en activité.",
        "Les Coches, sa station jumelle, n'a vu le jour qu'en 1980, 200 mètres plus haut.",
        "Le site est aujourd'hui au centre névralgique de Paradiski : c'est de là que part le Vanoise Express vers Les Arcs — un emplacement idéal, sachant qu'il faut environ quatre heures pour traverser le domaine d'un bout à l'autre.",
    ],
    "Saint-Jean-d'Arves": [
        "Village traditionnel étiré en hameaux face aux trois Aiguilles d'Arves, Saint-Jean est l'une des six stations réunies en 2003 pour former les Sybelles, l'un des plus grands domaines reliés de France.",
        "Toutes les remontées des Sybelles convergent vers l'Ouillon (2 431 m), réputé être la plus haute montagne à herbe d'Europe — d'où les vastes pentes dégagées et sans obstacle du domaine.",
    ],
    "Saint-Colomban-des-Villards": [
        "Blotti dans la vallée des Villards, au confluent du Glandon et sur la route du col du même nom, le village a longtemps vécu à l'écart — on y parlait encore le patois local des Colognons.",
        "Son raccordement au domaine des Sybelles en décembre 2003 a fait passer d'un coup ce petit village d'une poignée de téléskis à l'un des plus grands domaines skiables reliés de France.",
    ],
    "Les Bottières": [
        "Petite station-village posée sur un balcon ensoleillé au-dessus de Saint-Jean-de-Maurienne, Les Bottières est l'une des six stations réunies en 2003 pour créer le domaine des Sybelles.",
        "Cette fusion fut l'œuvre d'un homme, l'exploitant Gaston Maulin, qui porta pendant des années le projet de relier ces villages-stations épars en un seul grand domaine.",
    ],
    "Bramans": [
        "Le village est bâti sur une antique voie romaine qui franchissait le Petit Mont-Cenis et le col Clapier — un passage par lequel, selon une hypothèse tenace, Hannibal et ses éléphants auraient traversé les Alpes.",
        "Ses vieilles rues sont bordées de maisons à voûtes couvertes de lauzes, architecture typique de la Haute-Maurienne.",
        "Depuis 2017, Bramans fait partie de la commune nouvelle de Val-Cenis, qui est devenue par sa superficie la deuxième plus grande commune de France métropolitaine, derrière Arles.",
    ],
    "Termignon": [
        "Le village est l'une des portes du Parc national de la Vanoise, où agriculture de montagne et tourisme cohabitent encore : c'est de là que partent les accès au Plan du Lac, l'un des plus beaux belvédères du parc sur les glaciers de la Vanoise.",
        "Depuis 2017, Termignon est le siège de la commune nouvelle de Val-Cenis, née de la fusion de cinq villages — choisi non pas parce qu'il était le plus peuplé, mais parce qu'il était le plus central.",
    ],
    "Albiez-Montrond": [
        "La station est double : deux villages de montagne, Albiez-le-Vieux et Albiez-le-Jeune, se partagent le balcon au-dessus de la vallée de l'Arvan.",
        "Le territoire de la commune s'étage de 738 m à plus de 3 300 m d'altitude — un dénivelé de plus de 2 500 m, rare pour une commune de quelques centaines d'habitants.",
    ],
    "Col de Marcieu": [
        "Petite station perchée sur le plateau des Petites Roches, au pied des grandes falaises calcaires de Chartreuse, elle a fait de sa taille un atout : on se gare et on est déjà au pied des pistes, sans un mètre de marche.",
        "Confrontée à un enneigement capricieux, elle s'est réinventée en « espace ludique » : luge, snow-tubing et snake-gliss — ce train de petites luges assemblées où c'est la première qui pilote et les dernières qui prennent le plus de sensations.",
    ],
    "Col d'Ornon": [
        "Le col (1 360 m) relie le Bourg-d'Oisans à la Matheysine et se trouve dans l'aire d'adhésion du Parc national des Écrins, entre les massifs du Taillefer et des Grandes Rousses.",
        "Bien moins célèbre que ses voisins de l'Oisans, il a pourtant été emprunté par le Tour de France — notamment lors de la mythique étape de 2013 qui gravissait deux fois l'Alpe d'Huez.",
    ],
    "Chamonix": [
        "C'est ici que sont nés les Jeux Olympiques d'hiver : du 25 janvier au 5 février 1924, Chamonix a accueilli la « Semaine Internationale des Sports d'Hiver », rétroactivement reconnue comme les premiers JO d'hiver de l'histoire — 258 athlètes de 16 nations, au pied du mont Blanc. Détail savoureux : le ski alpin n'y figurait même pas.",
        "Berceau mondial de l'alpinisme depuis la première ascension du mont Blanc (4 806 m) en 1786, la vallée a vu défiler tous les pionniers de la montagne, de Roger Frison-Roche à Gaston Rébuffat.",
    ],
    "Val d'Isère": [
        "Le Club des Sports de Val d'Isère, fondé en 1935 par l'Alsacien Charles Diebold, est le club de ski le plus titré au monde : Henri Oreiller (premier champion olympique de ski français, en 1948), les sœurs Goitschel, Jean-Claude Killy, Clément Noël... 21 médailles d'or olympiques et mondiales au total.",
        "Jean-Claude Killy, arrivé au village à 3 ans, a réalisé ici son triplé olympique légendaire de 1968 — le domaine relié avec Tignes a longtemps porté son nom, l'« Espace Killy ». En 1992, les épreuves masculines des JO d'Albertville se sont disputées sur la mythique face de Bellevarde.",
        "La station est desservie par la plus haute route des Alpes, celle du col de l'Iseran (2 764 m), inaugurée en 1937.",
    ],
    "Tignes": [
        "L'histoire de Tignes commence par un drame : en 1952, le vieux village savoyard a été dynamité puis englouti sous les eaux du barrage du Chevril — alors le plus haut d'Europe — malgré la résistance acharnée de ses 387 habitants, évacués par les CRS. Quand le niveau du lac baisse, les vestiges remontent parfois à la surface.",
        "Renée de ses cendres sur les hauteurs, Tignes est devenue l'une des plus grandes stations des Alpes, avec le glacier de la Grande Motte (3 456 m) qui permet même de skier en été.",
        "En 1992, la station a accueilli les épreuves de ski artistique des JO d'Albertville, ainsi que les Jeux Paralympiques d'hiver.",
    ],
    "Courchevel": [
        "Née le 3 mai 1946 sur le plateau vierge des Tovets, Courchevel est la première station française créée ex nihilo, entièrement pensée « skis aux pieds » — à l'origine un projet à vocation sociale du département de la Savoie, devenu... la station la plus huppée du monde, avec ses palaces et la plus forte concentration d'étoiles Michelin de toutes les stations de ski.",
        "Son altiport, inauguré en 1961 en plein milieu des pistes, est légendaire : sa piste courte et inclinée en fait l'un des aéroports les plus spectaculaires du monde. À l'époque, les clients venaient prendre leur avion... à skis.",
        "Courchevel est l'une des portes des 3 Vallées, le plus grand domaine skiable du monde avec 600 km de pistes.",
    ],
    "Val Thorens": [
        "À 2 300 m, c'est la plus haute station d'Europe — un site jugé si extrême que personne n'en voulait à l'époque du Plan Neige. Ouverte à Noël 1971 avec 3 téléskis, ses pylônes furent coulés à l'hélicoptère, une première.",
        "Station de tous les records : premier Funitel au monde (1990), et élue « meilleure station de ski du monde » aux World Ski Awards huit années de suite, de 2013 à 2020. Ici, la neige tient de novembre à mai.",
    ],
    "Les Menuires": [
        "La station doit son nom aux anciennes mines de charbon exploitées autrefois par les habitants de la vallée des Belleville.",
        "En 1992, Les Menuires ont été site olympique des JO d'Albertville : le slalom messieurs s'y est disputé.",
    ],
    "Saint-Martin-de-Belleville": [
        "Ce village savoyard authentique des 3 Vallées abrite une légende gastronomique : La Bouitte (« petite maison » en patois), née en 1976 dans un champ de pommes de terre acheté par René Meilleur, autodidacte complet. Avec son fils Maxime, ancien biathlète de l'équipe de France juniors, il a décroché 3 étoiles Michelin en 2015 — sans jamais avoir suivi d'école de cuisine.",
    ],
    "Méribel": [
        "Méribel doit son existence à un Écossais : le colonel Peter Lindsay, qui, cherchant en 1938 une alternative aux stations autrichiennes annexées par l'Allemagne, tomba amoureux de la vallée des Allues, guidé par le champion Émile Allais. Il imposa une charte architecturale stricte — bois, pierre, toits de lauze — toujours en vigueur aujourd'hui.",
        "La designer Charlotte Perriand, collaboratrice de Le Corbusier, a signé la décoration du premier chalet-hôtel de la station ; ne pouvant la payer, Lindsay lui offrit un terrain où elle bâtit son propre chalet.",
        "En 1992, Méribel a été l'un des grands sites des JO d'Albertville : toutes les épreuves féminines de ski alpin et 46 matchs de hockey sur glace s'y sont disputés.",
    ],
    "Avoriaz": [
        "Avoriaz est le rêve fou de Jean Vuarnet, enfant de Morzine devenu champion olympique de descente en 1960 (et inventeur de la position de l'œuf) : à 27 ans, il abandonne sa carrière pour bâtir une station 100 % sans voiture sur un plateau vierge à 1 800 m. Ouverte en 1966, on s'y déplace toujours à ski, à pied ou en traîneau.",
        "Son architecture organique avant-gardiste, signée Jacques Labro (Prix de Rome à 26 ans), épouse les courbes de la montagne — l'hôtel des Dromonts, immense pomme de pin de bois, en est l'emblème. L'ensemble est labellisé « Architecture contemporaine remarquable ».",
        "La station a longtemps accueilli le mythique Festival du film fantastique d'Avoriaz (1973-1993), qui a révélé de nombreux réalisateurs au public français.",
    ],
    "Morzine": [
        "Village pionnier : dès 1934, les Morzinois, empruntant eux-mêmes les fonds nécessaires, construisent le téléphérique du Pléney — le deuxième téléphérique pour skieurs de France après Chamonix. À l'époque, beaucoup le prenaient... juste pour la vue sur les Alpes.",
        "Longtemps avant le ski, la richesse de Morzine venait de ses ardoisières : les toits d'ardoise des chalets du village en témoignent encore.",
        "Morzine est au cœur des Portes du Soleil, immense domaine franco-suisse de 12 stations et 650 km de pistes, entre lac Léman, Dents du Midi et mont Blanc.",
    ],
    "Les Gets": [
        "Le village abrite un musée unique en France : le Musée de la Musique Mécanique, installé dans un ancien presbytère, avec plus de 900 instruments — boîtes à musique, orgues de Barbarie, limonaires, automates et pianos mécaniques.",
        "L'été, Les Gets est un haut lieu mondial du VTT : la station a accueilli à plusieurs reprises les Championnats du monde de mountain bike et des étapes du Tour de France.",
    ],
    "Châtel": [
        "Blottie à la frontière suisse, Châtel a une longue histoire de... contrebande : pendant des siècles, sel, tabac, café et fromages passaient clandestinement la frontière par les sentiers de montagne. La Vieille Douane du village, transformée en centre d'interprétation, raconte le jeu du chat et de la souris entre douaniers et contrebandiers.",
        "Le village n'a pas renié ses racines paysannes : une quarantaine de familles d'agriculteurs et plus de 800 vaches de race Abondance y produisent toujours le fameux fromage d'Abondance, AOC depuis 1990.",
    ],
    "Megève": [
        "Megève est née d'un caprice de baronne : lassée de croiser des Allemands à Saint-Moritz après la Première Guerre mondiale, Noémie de Rothschild envoya son moniteur de ski chercher un site français pour créer un « Saint-Moritz à la française ». Coup de foudre pour Megève : palace dès 1921, golf en 1923... L'aristocratie européenne suivit, le roi Albert Ier de Belgique parmi les premiers visiteurs.",
        "Dans les années 1960-70, la station était le rendez-vous de la jet-set — Jean Cocteau la surnommait « le 21e arrondissement de Paris ».",
    ],
    "Alpe d'Huez": [
        "Ses 21 virages sont le monument le plus mythique du Tour de France : gravis pour la première fois le 10 juillet 1952 (victoire de Fausto Coppi), ils sont devenus l'arrivée au sommet la plus empruntée de l'histoire de l'épreuve. Chaque lacet porte le nom d'un vainqueur, et le virage n°7 — le « virage des Hollandais » — est l'un des lieux de fête les plus fous du sport mondial.",
        "Détail méconnu : les numéros des 21 virages étaient à l'origine de simples bornes... destinées à guider les chasse-neige.",
    ],
    "Le Lioran": [
        "Le Lioran possède sa propre gare SNCF, sur la ligne Figeac–Arvant, avec un téléski partant directement du parvis de la gare — une configuration unique en France, permettant de venir skier en train.",
        "La station est implantée au pied du Plomb du Cantal (1 855 m), point culminant des monts du Cantal et l'un des plus grands stratovolcans d'Europe.",
        "Avec 60 km de pistes, c'est le plus grand domaine skiable du Massif Central.",
    ],
    "Super Besse": [
        "Créée en 1961 à l'initiative de Germain Gauthier, champion de ski de fond auvergnat, sur les pentes du Puy de Sancy (1 885 m), le plus haut sommet du Massif Central.",
        "Le Tour de France cycliste y a fait étape à deux reprises, en 2008 et 2011.",
    ],
    "Le Mont Dore": [
        "L'une des toutes premières stations de sports d'hiver françaises : son téléphérique, inauguré le 17 janvier 1937, fut le tout premier du Massif Central.",
        "Le funiculaire du Capucin, construit en 1898, est le premier funiculaire électrique de France ; il est aujourd'hui inscrit au titre des Monuments historiques.",
        "La Dordogne prend sa source au Mont-Dore, à la confluence de la Dore et de la Dogne.",
    ],
    "Chastreix-Sancy": [
        "La plus petite station du massif du Sancy, créée en 1961, au cœur de la Réserve naturelle nationale de Chastreix-Sancy — réputée pour son ski hors-piste plus « sauvage » que ses voisines.",
    ],
    "Chalmazel": [
        "Unique station de ski alpin du département de la Loire, sous Pierre-sur-Haute (1 631 m), point culminant des monts du Forez.",
        "L'ancienne télécabine de Pierre-sur-Haute, inaugurée en 1967 par Antoine Pinay, a connu une seconde vie après son démontage : une partie de ses cabines a été revendue à la station iranienne de Pooladkaf, dans les monts Zagros, où elles circulent toujours depuis 2009.",
    ],
    "La Loge des Gardes": [
        "Unique station de ski alpin du département de l'Allier, sur les Pierres du Jour (1 164 m), point culminant des monts de la Madeleine, en pleine forêt domaniale de l'Assise.",
    ],
    "Laguiole": [
        "Plus grande station de ski de l'Aveyron, organisée sur deux secteurs (La Source et Le Bouyssou), reliée au domaine nordique de l'Espace Aubrac.",
    ],
    "La Croix de Bauzon": [
        "Unique station de ski alpin en exploitation du département de l'Ardèche, sur les pentes du massif du Tanargue, avec un premier téléski installé dès 1937.",
    ],
    "Le Bleymard-Mont Lozère": [
        "Unique station de ski alpin du département de la Lozère, au pied du Pic de Finiels (1 702 m), point culminant du Mont Lozère, dans le Parc national des Cévennes.",
    ],
    "Les Estables-Mézenc": [
        "Les Estables est le plus haut village d'Auvergne (environ 1 350 m), au pied du Mont Mézenc (1 753 m), 3ᵉ sommet du Massif Central, connu pour son vent local caractéristique, la « burle ».",
    ],
    "Brameloup": [
        "Petite station familiale de l'Aubrac, sous le Suc de Born (1 388 m) — avec Laguiole, l'un des deux berceaux historiques du ski aveyronnais depuis les années 1970.",
    ],
    "Alti Aigoual": [
        "Unique station de sports d'hiver du département du Gard, sur les pentes du Mont Aigoual (1 567 m), point culminant du Gard. Le sommet abritait le dernier observatoire météorologique de montagne habité de France, automatisé fin décembre 2023.",
    ],
    "Prabouré": [
        "Petite station familiale des monts du Forez, la plus proche de Saint-Étienne, où le ski se pratique depuis 1954.",
    ],
    "Le Guéry": [
        "Site essentiellement nordique au col de Guéry ; le lac de Guéry, à environ 1 244 m, est le plus haut lac d'Auvergne, d'origine à la fois glaciaire et volcanique.",
    ],
    "La Chaise-Dieu": [
        "Ce n'est pas un domaine de ski alpin mais un site de ski de fond, connu pour son abbaye Saint-Robert (XIᵉ siècle) et son festival de musique classique créé en 1966 par le pianiste Georges Cziffra.",
    ],
}

STATION_ORIENTATION = {
    "Ghisoni - Capanelle": {
        "expo": "Est", "expo_deg": 90,
        "village_txt": "La station est un domaine skiable de petite taille sans village indépendant : la zone d'accueil (parkings, location, restauration) se trouve directement au pied des pistes, sur le flanc est du Monte Renoso.",
        "village_impact": "Le soleil arrive tôt le matin sur la zone d'accueil mais décline plus vite en début d'après-midi qu'une exposition sud — prévoir une petite laine pour l'après-midi.",
        "pistes_impact": "Exposition est confirmée par deux sources indépendantes : les pistes gardent une neige plutôt correcte le matin, avant qu'elle ne se ramollisse en cours de journée.",
    },
    "Super Besse": {
        "expo": "Sud-Est", "expo_deg": 135,
        "village_txt": "Le village et le bas des pistes sont au même endroit, sur le versant sud-est du Puy de Sancy — même exposition pour skier et pour se promener en station.",
        "village_impact": "Ambiance ensoleillée et chaleureuse, terrasses agréables même en plein hiver dès la matinée.",
        "pistes_impact": "L'exposition sud-est apporte un bel ensoleillement mais fait fondre la neige de surface plus vite qu'un versant nord — les meilleures conditions sont souvent le matin.",
    },
    "Le Mont Dore": {
        "expo": "Nord / Nord-Est", "expo_deg": 25,
        "village_txt": "Attention, ici village et pistes ne sont pas au même endroit : Le Mont-Dore est une ville thermale ancienne installée en fond de vallée (vallée de la Dordogne), tandis que le domaine skiable est sur le versant nord/nord-est du Puy de Sancy, plus haut. L'ensoleillement précis du centre-ville n'est pas documenté avec certitude — seule l'exposition des pistes est confirmée.",
        "village_impact": "Ville nichée en fond de vallée, entourée de reliefs — un cadre thermal préservé mais qui limite naturellement le soleil direct par rapport à une station d'altitude.",
        "pistes_impact": "Le versant nord/nord-est conserve mieux la neige : Le Mont-Dore est régulièrement cité parmi les stations les plus enneigées de France.",
    },
    "Chastreix-Sancy": {
        "expo": "Ouest", "expo_deg": 270,
        "village_txt": "Le village-station est directement au pied des pistes, sur le versant ouest du Sancy — même exposition pour le village et pour skier.",
        "village_impact": "Le soleil accompagne la station plutôt en fin de journée qu'au petit matin.",
        "pistes_impact": "Exposition ouest confirmée par la commune et l'office de tourisme du Sancy.",
    },
    "Chalmazel": {
        "expo": "Est", "expo_deg": 90,
        "village_txt": "Le domaine est situé sur le versant est de Pierre-sur-Haute, le village-station étant au pied des pistes.",
        "village_impact": "Soleil du matin agréable, ombre qui s'installe plus tôt en fin d'après-midi.",
        "pistes_impact": "Exposition est confirmée par plusieurs sources — bonnes conditions de neige le matin.",
    },
    "La Croix de Bauzon": {
        "expo": "Nord", "expo_deg": 0,
        "village_txt": "La station est sur l'ubac (versant nord) du massif du Tanargue, zone d'accueil et pistes confondues.",
        "village_impact": "Ambiance plus fraîche et ombragée qu'un versant sud, avec parfois un vent sensible sur les crêtes.",
        "pistes_impact": "L'exposition nord permet à la neige de mieux se conserver dans la journée.",
    },
    "Le Bleymard-Mont Lozère": {
        "expo": "Nord", "expo_deg": 0,
        "village_txt": "Depuis le chalet d'accueil, le domaine alpin (7 pistes) s'étend au nord, tandis que le secteur nordique se déploie au sud — deux ambiances bien différentes selon le côté.",
        "village_impact": "Le chalet d'accueil profite d'un site ouvert ; le secteur alpin, orienté nord, est plus frais.",
        "pistes_impact": "L'exposition nord du domaine alpin favorise une meilleure tenue de la neige que le secteur nordique, plus au sud.",
    },
    "Cambre d'Aze": {
        "expo": "Nord", "expo_deg": 0,
        "village_txt": "La station est accessible par deux villages distincts, Eyne et Saint-Pierre-dels-Forcats, qui se partagent le domaine skiable orienté plein nord.",
        "village_impact": "Le climat y est réputé un peu plus frais que dans les stations voisines de Cerdagne, même si l'écart reste souvent limité au quotidien.",
        "pistes_impact": "L'exposition nord est la marque de fabrique de la station : la neige y gèle plus vite qu'ailleurs, ce qui rend les pistes plus techniques — un vrai plus pour les bons skieurs, moins pour les débutants.",
    },
}



EXPO_SUN_ICON = {
    "Nord": "🌥", "Nord-Est": "🌤", "Est": "☀️", "Sud-Est": "☀️",
    "Sud": "☀️", "Sud-Ouest": "☀️", "Ouest": "🌤", "Nord-Ouest": "🌥",
}

def render_anecdote_html(name):
    """Bloc 'Le saviez-vous ?' inséré dans l'onglet Infos, sous la description.
    Retourne une chaîne vide si aucune anecdote vérifiée n'existe pour cette station."""
    items = STATION_ANECDOTES.get(name)
    if not items:
        return ''
    texts = ''.join(f'<div class="ab-text">{t}</div>' for t in items)
    return f'''
          <div class="anecdote-box">
            <div class="ab-icon">💡</div>
            <div>
              <div class="ab-label">Le saviez-vous ?</div>
              {texts}
            </div>
          </div>'''

def render_expo_html(s):
    """Contenu complet de l'onglet 'Exposition' : orientation du village,
    boussole visuelle, impact sur l'ambiance et sur la neige.
    Retourne une chaîne vide si aucune donnée vérifiée n'existe — dans ce cas
    l'onglet entier (bouton + contenu) est omis de la page (voir render_page)."""
    name = s['name']
    o = STATION_ORIENTATION.get(name)
    if not o:
        return ''
    deg = o.get('expo_deg', 180)
    sun_icon = EXPO_SUN_ICON.get(o.get('expo', 'Sud'), '☀️')
    return f'''
        <div class="section">
          <div class="section-title">Orientation du village</div>
          <div class="compass-card">
            <div class="compass-wheel">
              <div class="cw-label cw-n">N</div>
              <div class="cw-label cw-s">S</div>
              <div class="cw-label cw-e">E</div>
              <div class="cw-label cw-w">O</div>
              <div class="cw-needle" style="height:38px;transform:translate(-50%,-100%) rotate({deg}deg)"></div>
              <div class="cw-sun">{sun_icon}</div>
            </div>
            <div class="compass-info">
              <div class="compass-expo-sub">Exposition</div>
              <div class="compass-expo">{o.get('expo','')}</div>
              <p style="font-size:.85rem;line-height:1.65;color:var(--text-mid);margin-top:8px">{o.get('village_txt','')}</p>
            </div>
          </div>
        </div>
        <div class="section" style="margin-bottom:0">
          <div class="section-title">Ce que ça change concrètement</div>
          <div class="expo-impact-grid">
            <div class="expo-impact-card">
              <div class="eic-icon">🏘️</div>
              <div class="eic-title">Ambiance au village</div>
              <div class="eic-text">{o.get('village_impact','')}</div>
            </div>
            <div class="expo-impact-card">
              <div class="eic-icon">❄️</div>
              <div class="eic-title">Qualité de la neige</div>
              <div class="eic-text">{o.get('pistes_impact','')}</div>
            </div>
          </div>
        </div>'''

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

def to_photo_slug(name):
    """Slug pour les noms de fichiers photos : tout en minuscules,
    sans accents, sans tirets, sans espaces, sans apostrophes.
    Convention : 'Val Thorens' -> 'valthorens', 'Saint-Lary-Soulan' -> 'saintlarysoulan',
    'Alpe d'Huez' -> 'alpedhuez', 'Chamonix' -> 'chamonix'."""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_only = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    return re.sub(r'[^a-z0-9]', '', ascii_only.lower())

def get_station_photos(name):
    """Détecte toutes les photos uploadées pour une station.
    Pattern : {photo_slug}1.jpg, {photo_slug}2.jpg, ... (jusqu'au premier trou, max 20).
    Slug photo = lowercase, no accents, no separators (e.g. valthorens1.jpg).
    Supporte .jpg, .jpeg, .png, .webp.
    Retourne une liste de chemins relatifs ('../img/...') ou liste vide."""
    pslug = to_photo_slug(name)
    photos = []
    for i in range(1, 21):
        found = None
        for ext in ('jpg', 'jpeg', 'png', 'webp', 'JPG', 'JPEG', 'PNG', 'WEBP'):
            p = os.path.join(root_dir, 'img', f'{pslug}{i}.{ext}')
            if os.path.exists(p):
                found = f'../img/{pslug}{i}.{ext}'
                break
        if not found:
            break  # stop au premier trou
        photos.append(found)
    return photos

def get_domaine_photos(slug):
    """Détecte toutes les photos uploadées pour un domaine skiable relié.
    Pattern : {slug-sans-tirets}1.jpg, {slug-sans-tirets}2.jpg, ... (jusqu'au premier trou, max 20).
    Ex : slug 'portes-du-soleil' -> fichiers portesdusoleil1.jpg, portesdusoleil2.jpg...
         slug '3-vallees' -> fichiers 3vallees1.jpg, 3vallees2.jpg...
    Même logique que get_station_photos, juste basée sur la clé du dict DOMAINES.
    Supporte .jpg, .jpeg, .png, .webp. Retourne une liste de chemins relatifs ('../img/...') ou liste vide."""
    dslug = slug.replace('-', '')
    photos = []
    for i in range(1, 21):
        found = None
        for ext in ('jpg', 'jpeg', 'png', 'webp', 'JPG', 'JPEG', 'PNG', 'WEBP'):
            p = os.path.join(root_dir, 'img', f'{dslug}{i}.{ext}')
            if os.path.exists(p):
                found = f'../img/{dslug}{i}.{ext}'
                break
        if not found:
            break  # stop au premier trou
        photos.append(found)
    return photos

def get_domaine_photos_smart(slug, d):
    """Photos d'un domaine skiable relié, avec cascade de fiabilité :
    1. Photos dédiées au domaine (portesdusoleil1.jpg, portesdusoleil2.jpg...)
    2. Sinon, recomposition automatique à partir des photos déjà uploadées pour les
       stations membres (1 photo par station qui en a, dans l'ordre du dict DOMAINES) —
       évite de dupliquer un upload déjà fait côté station.
    3. Sinon, 1 photo de secours Unsplash déterministe (jamais de hero vide).
    Retourne (liste_de_photos, source) où source vaut 'own', 'borrowed' ou 'placeholder'."""
    own = get_domaine_photos(slug)
    if own:
        return own, 'own'
    borrowed = []
    for station_name in d['stations']:
        sp = get_station_photos(station_name)
        if sp:
            borrowed.append(sp[0])
        if len(borrowed) >= 12:  # assez pour un carrousel, pas la peine d'aller plus loin
            break
    if borrowed:
        return borrowed, 'borrowed'
    return [pick_placeholder(d['name'], massif=d.get('massif'), w=1400)], 'placeholder'

DATA = json.loads(m.group(1))
print(f"✓ {len(DATA)} stations chargées")

# Extraire les coordonnées GPS depuis recherche.html (dict COORDS par nom de station)
STATION_COORDS = {}
m_coords = re.search(r'const COORDS = (\{[^;]+?\});', content, re.DOTALL)
if m_coords:
    try:
        raw_coords = json.loads(m_coords.group(1))
        # Convertir [lat, lng] en {'lat':..,'lon':..} indexé par nom
        for name, latlng in raw_coords.items():
            if isinstance(latlng, list) and len(latlng) >= 2:
                STATION_COORDS[name] = {'lat': latlng[0], 'lon': latlng[1]}
        print(f"✓ {len(STATION_COORDS)} coordonnées GPS chargées")
    except Exception as e:
        print(f"⚠ Erreur parsing COORDS: {e}")
else:
    print("⚠ const COORDS non trouvé dans recherche.html — la météo sera désactivée")

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
            # On ignore sim.get('photo') car le DATA contient parfois des URLs incorrectes
            # (visages, gratte-ciels, couchers de soleil). Seules les photos uploadées
            # localement dans img/ sont conservées ; sinon, placeholder Unsplash réparti
            # de façon déterministe sur les 9 photos de PLACEHOLDER_URLS.
            photo = pick_placeholder(sim['name'], massif=sim.get('massif'), w=400)
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
    """Génère un avis éditorial riche et personnalisé (5-6 phrases) par station."""
    ambs  = s.get('amb', [])
    nivs  = s.get('niv', [])
    equip = s.get('equip', [])
    _dslug, _dom = get_domaine(s['name'])
    km    = _dom.get('km_propre', {}).get(s['name'], s['km']) if _dom else s['km']
    alt   = s['alt_max']
    alt_v = _dom.get('alt_village', {}).get(s['name'], s['alt_min']) if _dom else s['alt_min']
    if _dom and s['name'] in _dom.get('remontees_propre', {}):
        rem = _dom['remontees_propre'][s['name']]
    elif _dom and s['name'] in _dom.get('km_propre', {}) and _dom.get('km_total'):
        rem = round(_dom['remontees_total'] * _dom['km_propre'][s['name']] / _dom['km_total'])
    else:
        rem = s.get('remontees', 0)
    forfait = s['forfait']
    name  = s['name']
    massif = s.get('massif', '')
    pistes = s.get('pistes', {})
    total_pistes = sum(pistes.values()) if pistes else 0

    parts = []

    # ── ACCROCHE (domaine + positionnement) ──
    if km >= 300:
        parts.append(
            f"{name} fait partie des rares stations à offrir plus de {km} km de pistes skiables "
            f"— un domaine colossal que même les skieurs les plus rapides ne parcourent pas en une semaine. "
            f"Avec {rem} remontées mécaniques et {total_pistes} pistes répertoriées, c'est une destination "
            f"qui peut absorber tous les flux touristiques sans jamais donner l'impression d'être bondée."
        )
    elif km >= 150:
        parts.append(
            f"Le domaine de {name} avec ses {km} km de pistes représente une belle offre pour tous les profils : "
            f"suffisamment grand pour ne pas tourner en rond pendant une semaine, mais aussi assez compact "
            f"pour retrouver ses secteurs favoris facilement. "
            f"Les {rem} remontées mécaniques permettent d'enchaîner les descentes sans longues attentes."
        )
    elif km >= 80:
        parts.append(
            f"{name} propose {km} km de pistes bien balisées — un domaine de taille intermédiaire "
            f"idéal pour passer 4 à 5 jours sans jamais faire deux fois exactement la même chose. "
            f"Les {rem} remontées mécaniques sont généralement suffisantes pour absorber le débit en haute saison."
        )
    elif km >= 30:
        parts.append(
            f"Station à dimension humaine, {name} mise sur la qualité de l'accueil et la proximité plutôt que "
            f"sur les chiffres impressionnants. Ses {km} km de pistes conviennent parfaitement pour un séjour "
            f"de 3 à 4 jours, surtout en famille ou pour les skieurs qui n'ont pas besoin de renouveler "
            f"constamment leur terrain de jeu."
        )
    else:
        parts.append(
            f"{name} est une station confidentielle à l'échelle modeste — {km} km de pistes "
            f"pour une expérience de ski intimiste, loin de l'agitation des grandes stations. "
            f"C'est ici qu'on vient chercher le calme, l'authenticité et des files d'attente inexistantes "
            f"aux remontées."
        )

    # ── AMBIANCE / PUBLIC ──
    if 'luxe' in ambs:
        parts.append(
            f"L'ADN de {name}, c'est le haut de gamme : les hébergements, les restaurants d'altitude "
            f"et les services en station reflètent une clientèle qui ne compte pas. "
            f"Avec un forfait journée à {forfait}€, le séjour a un prix, mais l'expérience est à la hauteur "
            f"pour qui veut se faire plaisir sans compromis."
        )
    elif 'festif' in ambs and 'famille' not in ambs:
        parts.append(
            f"La station est reconnue pour son après-ski animé — bars, concerts au pied des pistes, "
            f"ambiance internationale dès que les remontées ferment. "
            f"Si tu cherches autant à profiter de la montagne le jour que des soirées le soir, "
            f"{name} est clairement l'une des meilleures options de son massif."
        )
    elif 'famille' in ambs and 'debutant' in nivs:
        parts.append(
            f"La réputation familiale de {name} n'est pas usurpée : espaces débutants dédiés, "
            f"{'garderie bien organisée, ' if 'garderie' in equip else ''}pistes vertes bien entretenues "
            f"et ambiance bon enfant au pied des remontées. "
            f"C'est une des stations les plus rassurantes du {massif} pour poser les bases du ski "
            f"avec des enfants."
        )
    elif 'rider' in ambs or 'expert' in nivs:
        noir_count = pistes.get('n', 0)
        rouge_count = pistes.get('r', 0)
        parts.append(
            f"Le terrain technique est roi à {name} : avec {noir_count} pistes noires et "
            f"{rouge_count} rouges au programme, les skieurs confirmés trouveront de quoi se challenger "
            f"sérieusement. "
            f"Le hors-piste et le freeride y sont pratiqués dans des conditions souvent excellentes "
            f"grâce à l'altitude et l'exposition des versants."
        )
    elif 'nature' in ambs or 'village' in ambs:
        parts.append(
            f"{name} a su préserver une identité de village montagnard authentique, loin des stations "
            f"bétonnées des années 70. "
            f"Ici, on vient pour l'air pur, les paysages intacts et une ambiance humaine qui tranche "
            f"avec l'industrialisation du ski dans certains grands domaines."
        )
    elif 'festif' in ambs and 'famille' in ambs:
        parts.append(
            f"Rare équilibre, {name} réussit à plaire autant aux familles qu'aux groupes d'amis "
            f"cherchant à s'amuser. "
            f"L'animation est présente sans être envahissante, et les secteurs se prêtent bien "
            f"à une organisation souple selon les envies de chacun."
        )
    else:
        parts.append(
            f"Station polyvalente par excellence, {name} convient à un groupe hétérogène "
            f"sans que personne ne soit lésé. "
            f"Les niveaux débutant à avancé trouvent leur compte, et le forfait à {forfait}€/jour "
            f"reste dans la moyenne raisonnable du massif."
        )

    # ── ALTITUDE / ENNEIGEMENT ──
    if alt >= 3000:
        parts.append(
            f"Côté enneigement, {name} est en position de force avec son point culminant à {alt} m — "
            f"même lors des hivers capricieux, les pistes du haut tiennent bien jusqu'en avril. "
            f"Le village à {alt_v} m est également bien situé pour garantir des conditions confortables "
            f"du départ dès la mi-décembre."
        )
    elif alt >= 2500:
        parts.append(
            f"Avec un sommet à {alt} m et un village à {alt_v} m, l'enneigement de {name} est globalement "
            f"fiable de janvier à fin mars. "
            f"Quelques hivers exceptionnellement doux peuvent créer des tensions en début de saison, "
            f"mais la situation se rétablit rapidement dès les premières chutes sérieuses."
        )
    elif alt >= 2000:
        parts.append(
            f"L'altitude de {name} ({alt_v} m au départ, {alt} m en haut) lui permet de maintenir "
            f"un enneigement correct en plein hiver. "
            f"Les mois de janvier et février sont les plus fiables ; en décembre et mars, il vaut mieux "
            f"vérifier les conditions avant de finaliser une réservation."
        )
    else:
        parts.append(
            f"L'altitude modérée de {name} — départ à {alt_v} m, sommet à {alt} m — "
            f"la rend sensible aux variations climatiques. "
            f"Les mois de janvier et février restent les plus sûrs pour un enneigement optimal. "
            f"En dehors de cette fenêtre, le suivi des bulletins d'enneigement avant le départ est "
            f"fortement conseillé."
        )

    # ── VALEUR / RAPPORT QUALITÉ-PRIX ──
    if forfait <= 22:
        parts.append(
            f"Avec un forfait journée à seulement {forfait}€, {name} est l'une des destinations "
            f"les plus accessibles de France. "
            f"Pour les familles à budget maîtrisé ou les skieurs qui veulent multiplier les sorties "
            f"sans se ruiner, c'est une adresse sincère et souvent méconnue."
        )
    elif forfait <= 35:
        parts.append(
            f"Le forfait journée à {forfait}€ reste raisonnable pour la qualité du domaine offert. "
            f"En comptant hébergement, ski et repas, {name} s'adresse à ceux qui veulent passer "
            f"une belle semaine sans que la note finale ne les fasse tomber de leur chaise."
        )
    elif forfait <= 50:
        parts.append(
            f"Le forfait journée à {forfait}€ place {name} dans la catégorie des stations "
            f"intermédiaires côté budget — ni donné, ni exorbitant. "
            f"La qualité du domaine et des équipements justifie ce tarif pour la plupart des skieurs."
        )
    else:
        parts.append(
            f"Le budget séjour à {name} est clairement élevé : {forfait}€ le forfait journée, "
            f"auxquels s'ajoutent des hébergements et des restaurants d'altitude parmi les plus chers "
            f"des Alpes. "
            f"C'est le prix de l'excellence — mais il faut en avoir conscience avant de partir."
        )

    # ── BILAN FINAL ──
    if km >= 150 and alt >= 2500 and forfait <= 50:
        parts.append(
            f"Au final, {name} est une valeur sûre du ski français : grand domaine, bon enneigement "
            f"et tarifs encore justifiés. Une destination qui mérite sa réputation."
        )
    elif 'famille' in ambs and 'village' in ambs:
        parts.append(
            f"En résumé : {name} est une de ces rares stations qui réunit un vrai village, "
            f"une ambiance familiale sincère et des pistes adaptées à tous. "
            f"Difficile de rater son séjour ici."
        )
    elif 'luxe' in ambs:
        parts.append(
            f"En résumé : {name} n'est pas pour tout le monde, mais pour qui peut se l'offrir, "
            f"c'est probablement l'une des meilleures expériences de ski en Europe."
        )
    elif km < 50:
        parts.append(
            f"En résumé : {name} ne rivalise pas avec les géants du ski mais ne le prétend pas. "
            f"C'est une destination honnête, souvent sous-estimée, qui mérite d'être (re)découverte."
        )
    else:
        parts.append(
            f"En résumé : {name} tient bien ses promesses. "
            f"Une station du {massif} qui saura convenir à la majorité des profils sans décevoir."
        )

    return ' '.join(parts)


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
def get_official_url(name):
    return OFFICIAL_URLS.get(name, f"https://www.google.com/search?q={name.replace(' ', '+').replace(chr(39), '+')}+station+ski+site+officiel")


def render_page(s):
    slug = slugify(s['name'])
    canonical = f"https://snowfinder.fr/stations/{slug}.html"
    # Détection automatique de toutes les photos uploadées : slug photo (sans tirets) + numéro
    # Convention : chamonix1.jpg, valthorens1.jpg, alpedhuez1.jpg, saintlarysoulan1.jpg
    all_photos = get_station_photos(s['name'])
    photo_is_placeholder = not all_photos
    hero_illu_note = '<div class="hero-illu-note">Photo d\'illustration</div>' if photo_is_placeholder else ''
    if all_photos:
        photo = all_photos[0]  # photo 1 = hero
    else:
        # On ignore s.get('photo') car le DATA contient parfois des URLs incorrectes
        # (visages, gratte-ciels, couchers de soleil). Seules les photos uploadées
        # localement dans img/ sont conservées ; sinon, placeholder Unsplash réparti
        # de façon déterministe sur les 9 photos de PLACEHOLDER_URLS.
        photo = pick_placeholder(s['name'], massif=s.get('massif'), w=1200)
    # Photo 2 (utilisée dans "Notre avis" comme aujourd'hui)
    photo_station = all_photos[1] if len(all_photos) >= 2 else None
    # Toutes les photos pour le carrousel (au moins 1 — la photo hero ou fallback)
    carousel_sources = list(all_photos) if all_photos else [photo]
    # HTML des slides du carrousel
    carousel_slides_html = "\n".join(
        f'    <img class="hero-slide{" active" if i==0 else ""}" data-idx="{i}" src="{p}" alt="{s["name"]} photo {i+1}" loading="{("eager" if i==0 else "lazy")}" onclick="heroLightbox({i})">'
        for i, p in enumerate(carousel_sources)
    )
    # JS array des URLs pour le lightbox du carrousel
    carousel_urls_js = "[" + ",".join(f'"{p}"' for p in carousel_sources) + "]"
    # Indicateurs (dots) seulement si plus d'1 photo
    if len(carousel_sources) > 1:
        carousel_dots_html = "\n".join(
            f'      <button class="hero-dot{" active" if i==0 else ""}" data-idx="{i}" onclick="heroGoTo({i})" aria-label="Photo {i+1}"></button>'
            for i in range(len(carousel_sources))
        )
        carousel_nav_html = f'''  <button class="hero-nav hero-prev" onclick="heroPrev()" aria-label="Précédente">‹</button>
  <button class="hero-nav hero-next" onclick="heroNext()" aria-label="Suivante">›</button>
  <div class="hero-dots">
{carousel_dots_html}
  </div>'''
    else:
        carousel_nav_html = ''
    # Photos supplémentaires (3, 4, 5, ...) — utilisées par le carrousel hero uniquement
    extra_photos = all_photos[2:] if len(all_photos) >= 3 else []
    # Pas de galerie séparée : les photos sont toutes dans le carrousel hero
    gallery_html = ''
    gallery_urls_js = carousel_urls_js
    # (Galerie séparée supprimée — toutes les photos sont dans le carrousel hero)
    if False:
        pass
    prix_nuit = round(s['forfait'] * 2.4)
    niveaux = ", ".join(NIV.get(n, n) for n in s.get('niv', []))
    pts = s.get('pts', [])
    pts_html = "\n".join(f'<li style="padding:5px 0;border-bottom:1px solid #f7efe2">{p}</li>' for p in pts)
    anecdote_html = render_anecdote_html(s['name'])
    expo_html = render_expo_html(s)
    expo_tab_btn = '<button class="tab-btn" onclick="switchTab(\'expo\',this)">🧭 Exposition</button>' if expo_html else ''
    # ── Domaine skiable relié (si la station en fait partie) ──
    domaine_slug, domaine = get_domaine(s['name'])
    if domaine:
        domaine_url = f"../domaines/{domaine_slug}.html"
        soeurs = [n for n in domaine['stations'] if n != s['name']]
        domaine_badge_html = f'''<a href="{domaine_url}" class="domaine-box">
    <div class="domaine-box-head">
      <div class="domaine-box-tag">🏔️ Domaine skiable relié</div>
      <div class="domaine-box-name">{domaine['name']} <span class="domaine-box-arrow">→</span></div>
    </div>
    <div class="domaine-box-stats">
      <div><div class="dbs-val">{domaine['km_total']} km</div><div class="dbs-lbl">Pistes du domaine</div></div>
      <div><div class="dbs-val">{domaine['alt_min']}-{domaine['alt_max']}m</div><div class="dbs-lbl">Altitude</div></div>
      <div><div class="dbs-val">{domaine['remontees_total']}</div><div class="dbs-lbl">Remontées</div></div>
      <div><div class="dbs-val">{domaine['forfait_domaine']}€</div><div class="dbs-lbl">Forfait domaine/j</div></div>
    </div>
    <div class="domaine-box-foot">{len(domaine['stations'])} stations reliées, dont {s['name']} · voir la fiche complète du domaine</div>
  </a>'''
        domaine_tab_btn = '<button class="tab-btn" onclick="switchTab(\'domaine\',this)">🏔️ Domaine</button>'
        soeurs_cards = "\n".join(
            f'''<a href="{slugify(n)}.html" class="domaine-soeur-card">
        <div class="domaine-soeur-name">{n}</div>
        <div class="domaine-soeur-stats">
          <span>🏘 {get_alt_village(domaine, n) or '?'}m</span>
          <span>🎿 {domaine.get('km_propre', {}).get(n, '—')}{' km' if domaine.get('km_propre', {}).get(n) else ''}</span>
        </div>
        <div class="domaine-soeur-sub">Voir la fiche →</div>
      </a>''' for n in soeurs
        )
        domaine_tab_html = f'''<div class="tab-content" id="tab-domaine">
        <div class="dt-hero">
          <h3>🏔️ {domaine['name']}</h3>
          <p>{domaine['desc']}</p>
        </div>
        <div class="domaine-stats-mini">
          <div><strong>{domaine['km_total']} km</strong><span>de pistes reliées</span></div>
          <div><strong>{domaine['remontees_total']}</strong><span>remontées</span></div>
          <div><strong>{domaine['forfait_domaine']}€</strong><span>forfait domaine/j</span></div>
          <div><strong>{domaine['alt_min']}-{domaine['alt_max']}m</strong><span>altitude</span></div>
        </div>
        {'<p class="dt-warn">⚠️ Liaison ouverte selon enneigement uniquement.</p>' if domaine.get('conditionnel') else ''}
        <a href="{domaine_url}" class="domaine-see-all">Voir la fiche complète du domaine →</a>
        {f'<h4 class="dt-subtitle">Les autres stations du domaine</h4><div class="domaine-soeurs-grid">{soeurs_cards}</div>' if soeurs else ''}
      </div>'''
    else:
        domaine_badge_html = ''
        domaine_tab_btn = ''
        domaine_tab_html = ''
    # Valeurs affichées dans les stat-box principales : on privilégie le chiffre
    # PROPRE à la station quand il est connu (domaine['km_propre'] / alt_village),
    # pour ne pas confondre "km de la station" et "km du domaine entier"
    # (le domaine entier reste affiché séparément dans l'encadré or + l'onglet Domaine).
    if domaine:
        _unifie = domaine.get('unifie', False)
        _km_p = domaine.get('km_propre', {}).get(s['name'])
        display_alt_min = domaine.get('alt_village', {}).get(s['name'], s['alt_min'])
        display_alt_max = domaine.get('alt_max_propre', {}).get(s['name'], s['alt_max'])
        alt_max_lbl = "Sommet" if s['name'] in domaine.get('alt_max_propre', {}) else ("Sommet" if _unifie else "Sommet (domaine)")
        if _km_p:
            # Chiffre propre à la station, vérifié
            display_km = _km_p
            km_lbl = "Pistes skiables"
            if s['name'] in domaine.get('remontees_propre', {}):
                display_remontees = domaine['remontees_propre'][s['name']]
                remontees_lbl = "Remontées"
            else:
                display_remontees = round(domaine['remontees_total'] * _km_p / domaine['km_total'])
                remontees_lbl = "Remontées (estim.)"
        elif _unifie:
            # Domaine réellement mutualisé : aucune source ne publie de découpage
            # par village, les stations partagent le même domaine skiable.
            display_km = domaine['km_total']
            km_lbl = "Pistes (domaine partagé)"
            display_remontees = domaine['remontees_total']
            remontees_lbl = "Remontées (partagées)"
        else:
            display_km = s['km']
            km_lbl = "Pistes (secteur)"
            display_remontees = s['remontees']
            remontees_lbl = "Remontées (domaine)"
    else:
        display_km = s['km']
        display_alt_min = s['alt_min']
        km_lbl = "Pistes skiables"
        display_alt_max = s['alt_max']
        alt_max_lbl = "Sommet"
        display_remontees = s['remontees']
        remontees_lbl = "Remontées"
    from urllib.parse import quote as _q
    _bk_base = f"https://www.booking.com/searchresults.fr.html?ss={_q(s['name']+' ski france')}&lang=fr"
    booking_url = f"{BOOKING_CJ}?sid=station-{slug}&url={_q(_bk_base)}"
    _exp_base = "https://www.expedia.fr/go/hotel/search/Destination/?CityName=" + _q(s['name']) + "&City=" + _q(s['name']) + "&SortBy=distance&NumRoom=1&NumAdult1=1"
    expedia_url = f"https://www.jdoqocy.com/click-101709262-13904689?sid=station-{slug}&url={_q(_exp_base)}"
    verdict = generate_verdict(s)
    pour_qui = generate_pour_qui(s)
    periode = generate_meilleure_periode(s)

    # Fiabilité enneigement (pré-calculé pour éviter backslash dans f-string — Python < 3.12)
    if s['alt_max'] >= 2000:
        snow_reliability = "Au-dessus de 2 000 m, la neige est generalement garantie de mi-decembre a fin mars."
    elif s['alt_max'] >= 1500:
        snow_reliability = "A cette altitude, l'enneigement depend des conditions de l'annee. Verifiez l'etat des pistes avant de partir."
    else:
        snow_reliability = "L'altitude moderee rend l'enneigement sensible aux variations climatiques. Privilegiez les mois de janvier-fevrier."

    # Références neige village/sommet (estimations basées sur l'altitude et s['snow'])
    snow_ref = s.get('snow', 100)
    alt_range = max(1, s['alt_max'] - s['alt_min'])
    # Village = ~50-65% de la référence station (stations situées en bas)
    snow_ref_village = max(10, round(snow_ref * 0.55))
    # Sommet = ~130-160% de la référence selon le dénivelé
    snow_ref_sommet  = round(snow_ref * (1.0 + min(0.6, alt_range / 2000)))

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
    official_url = get_official_url(s['name'])
    coords = STATION_COORDS.get(s['name'], {})
    snow_lat = coords.get('lat', 'null')
    snow_lon = coords.get('lon', 'null')
    station_name_esc = s['name'].replace("'", "\\'")
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
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
  <title>{s['name']} — Station de ski : pistes, enneigement, hébergements | SnowFinder</title>
  <meta name="description" content="{s['name']} : {display_km} km de pistes, altitude {display_alt_min}-{display_alt_max}m, forfait {s['forfait']}€/jour. {s.get('desc','')[:100]}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="SnowFinder">
  <meta property="og:url" content="{canonical}">
  <meta property="og:title" content="{s['name']} — Station de ski | SnowFinder">
  <meta property="og:description" content="{display_km} km · {display_alt_max}m · {s['forfait']}€/j · {s['massif']}">
  <meta property="og:image" content="{photo}">
  <meta property="og:locale" content="fr_FR">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{s['name']} — Station de ski | SnowFinder">
  <meta name="twitter:image" content="{photo}">
  <script type="application/ld+json">{schema}</script>
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{
        appId: "9530c745-8578-41e9-ad9f-2fa5348ad0b8",
        safari_web_id: "web.onesignal.auto.5c6acdd7-2576-4d7e-9cb0-efba7bf8602e",
        serviceWorkerPath: "../sw.js",
        notifyButton: {{ enable: false }},
      }});
    }});
  </script>
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
    html,body{{touch-action:pan-x pan-y;overflow-x:hidden;max-width:100%}}
    /* Filet de sécurité : aucun média ou tableau ne peut élargir la page */
    img,table,pre,iframe{{max-width:100%}}
    body{{font-family:"DM Sans",sans-serif;color:var(--text);background:linear-gradient(135deg,#e8f3fb 0%,#d0e7f5 50%,#e8f3fb 100%);background-attachment:fixed;min-height:100vh;position:relative;padding-top:58px;padding-bottom:66px}}
    /* Le canvas des flocons est au-dessus du fond mais sous tout contenu */
    #snowCanvas{{position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:1;mix-blend-mode:screen}}
    /* Tout le reste passe au-dessus du canvas */
    .nav,.hero,.container,.mobile-bar,.footer,#officialSheet,#officialOverlay{{position:relative;z-index:2}}
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
    /* CARROUSEL HERO */
    .hero-slides{{position:absolute;inset:0;width:100%;height:100%}}
    .hero-slide{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;opacity:0;transition:opacity .45s ease-in-out;cursor:zoom-in}}
    .hero-slide.active{{opacity:1;z-index:1}}
    .hero-nav{{
      position:absolute;top:50%;transform:translateY(-50%);width:44px;height:44px;border-radius:50%;
      background:rgba(255,255,255,.18);border:none;color:white;font-size:1.7rem;cursor:pointer;z-index:6;
      display:flex;align-items:center;justify-content:space-around;backdrop-filter:blur(6px);
      transition:background .15s,transform .15s;line-height:1;padding-bottom:4px
    }}
    .hero-nav:hover{{background:rgba(255,255,255,.32);transform:translateY(-50%) scale(1.06)}}
    .hero-prev{{left:14px}}
    .hero-next{{right:14px}}
    .hero-dots{{
      position:absolute;bottom:14px;left:50%;transform:translateX(-50%);z-index:6;
      display:flex;gap:7px;background:rgba(0,0,0,.32);padding:6px 12px;border-radius:20px;backdrop-filter:blur(6px)
    }}
    .hero-dot{{
      width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,.45);border:none;cursor:pointer;
      padding:0;transition:background .2s,transform .2s
    }}
    .hero-dot.active{{background:white;transform:scale(1.3)}}
    .hero-dot:hover{{background:rgba(255,255,255,.75)}}
    /* CROIX DE FERMETURE */
    .hero-close{{
      position:absolute;top:18px;right:18px;width:42px;height:42px;border-radius:50%;
      background:rgba(0,0,0,.5);backdrop-filter:blur(8px);border:1.5px solid rgba(255,255,255,.35);
      color:white;font-size:1.1rem;cursor:pointer;z-index:20;
      display:flex;align-items:center;justify-content:center;transition:all .15s
    }}
    .hero-close:hover{{background:rgba(0,0,0,.75);transform:scale(1.08)}}
    /* Décaler le score pour pas chevaucher la croix */
    .hero-overlay{{
      position:absolute;inset:0;z-index:3;
      background:linear-gradient(to top,rgba(0,0,0,.88) 0%,rgba(0,0,0,.3) 45%,rgba(0,0,0,.05) 100%)
    }}
    .hero-score{{
      position:absolute;top:22px;right:74px;z-index:15;
      background:var(--wood);color:white;font-weight:700;font-size:.95rem;
      padding:6px 13px;border-radius:9px;box-shadow:0 2px 8px rgba(0,0,0,.25)
    }}
    .hero-content{{position:absolute;bottom:0;left:0;right:0;padding:28px 28px 32px;z-index:10}}
    .hero-massif{{
      display:inline-block;background:rgba(255,255,255,.16);
      border:1px solid rgba(255,255,255,.28);border-radius:22px;
      padding:4px 14px;font-size:.7rem;font-weight:700;color:rgba(255,255,255,.92);
      text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;backdrop-filter:blur(8px)
    }}
    h1{{font-family:"DM Serif Display",serif;font-size:clamp(2rem,6vw,3.2rem);color:white;line-height:1.05;margin-bottom:6px}}
    .hero-region{{color:rgba(255,255,255,.75);font-size:.85rem;display:flex;align-items:center;gap:5px}}
    .hero-illu-note{{position:absolute;bottom:8px;right:14px;z-index:6;font-style:italic;font-size:.66rem;color:rgba(255,255,255,.55);text-shadow:0 1px 4px rgba(0,0,0,.6)}}

    /* CONTAINER */
    .container{{max-width:980px;margin:0 auto;padding:20px 14px 50px}}
    @media(max-width:480px){{.container{{padding:16px 10px 40px}}}}
    @media(min-width:1200px){{
      .container{{max-width:1240px}}
      .main-grid{{grid-template-columns:minmax(0,1fr) 400px;gap:28px}}
      .hero{{border-radius:22px}}
      .stats-grid{{gap:14px}}
    }}

    /* BREADCRUMB */
    .breadcrumb{{font-size:.75rem;color:var(--text-light);margin-bottom:24px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
    .breadcrumb a{{color:var(--blue-mid);font-weight:500}}
    .breadcrumb a:hover{{text-decoration:underline}}

    /* STATS */
    .stats-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:14px}}
    @media(max-width:700px){{.stats-grid{{grid-template-columns:repeat(3,1fr);gap:6px}}}}
    /* Grille de tuiles (ambiance, niveaux) : colonnes fixes et prévisibles,
       jamais d'auto-fill dont le calcul peut déborder dans certaines WebView */
    .tile-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
    @media(min-width:480px) and (max-width:700px){{.tile-grid{{grid-template-columns:repeat(3,1fr)}}}}
    @media(min-width:700px){{.tile-grid{{grid-template-columns:repeat(4,1fr)}}}}

    /* ONGLETS — pleine largeur sous le hero, TOUT est visible (pas de scroll horizontal) */
    .tab-nav-wrap{{position:relative;background:white;border-bottom:1px solid var(--border);box-shadow:0 2px 8px rgba(0,0,0,.04)}}
    .tab-nav{{display:flex;flex-wrap:nowrap;gap:0;max-width:1240px;margin:0 auto;padding:0 2px}}
    .tab-btn{{flex:1 1 0;min-width:0;padding:10px 2px 8px;border:none;background:transparent;cursor:pointer;font-family:"DM Sans",sans-serif;font-size:.62rem;font-weight:700;color:var(--text-light);transition:color .15s,border-color .15s;letter-spacing:0;white-space:normal;word-break:normal;overflow-wrap:break-word;border-bottom:3px solid transparent;text-align:center;line-height:1.15}}
    .tab-btn.active{{color:var(--blue-dark);border-bottom-color:var(--blue-mid);background:transparent}}
    .tab-btn:hover:not(.active){{color:var(--blue-mid)}}
    .tab-content{{display:none;background:white;border:1px solid var(--border);border-radius:14px;padding:18px 14px;min-height:200px}}
    .tab-content.active{{display:block}}
    /* LIRE PLUS / VOIR MOINS — textes longs (avis, description) */
    .readmore-wrap{{position:relative;max-height:118px;overflow:hidden;transition:max-height .35s ease}}
    .readmore-wrap.expanded{{max-height:3000px}}
    .readmore-wrap:not(.expanded)::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:38px;background:linear-gradient(transparent,var(--rm-bg,white))}}
    .readmore-btn{{display:flex;align-items:center;justify-content:center;gap:4px;margin-top:10px;font-size:.78rem;font-weight:800;color:var(--blue-mid);cursor:pointer;padding:6px;user-select:none}}

    /* ORIENTATION / EXPOSITION */
    .compass-card{{display:flex;align-items:center;gap:22px;background:linear-gradient(135deg,var(--blue-light),var(--wood-pale));border-radius:14px;padding:22px;margin-bottom:18px;flex-wrap:wrap}}
    .compass-wheel{{width:110px;height:110px;flex:0 0 110px;border-radius:50%;background:white;border:2px solid var(--border);position:relative;box-shadow:0 2px 10px rgba(0,0,0,.08)}}
    .compass-wheel .cw-label{{position:absolute;font-size:.62rem;font-weight:800;color:var(--text-light)}}
    .compass-wheel .cw-n{{top:4px;left:50%;transform:translateX(-50%)}}
    .compass-wheel .cw-s{{bottom:4px;left:50%;transform:translateX(-50%)}}
    .compass-wheel .cw-e{{right:6px;top:50%;transform:translateY(-50%)}}
    .compass-wheel .cw-w{{left:6px;top:50%;transform:translateY(-50%)}}
    .compass-wheel .cw-needle{{position:absolute;top:50%;left:50%;width:4px;border-radius:3px;background:linear-gradient(var(--blue-mid),var(--blue-mid));transform-origin:bottom center}}
    .compass-wheel .cw-sun{{position:absolute;font-size:1.3rem;top:50%;left:50%;transform:translate(-50%,-50%)}}
    .compass-info{{flex:1;min-width:180px}}
    .compass-expo{{font-family:"DM Serif Display",serif;font-size:1.25rem;color:var(--text)}}
    .compass-expo-sub{{font-size:.78rem;color:var(--text-light);margin-top:2px;text-transform:uppercase;letter-spacing:.05em;font-weight:700}}
    .expo-impact-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
    @media(max-width:560px){{.expo-impact-grid{{grid-template-columns:1fr}}}}
    .expo-impact-card{{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:14px 16px}}
    .expo-impact-card .eic-icon{{font-size:1.3rem;margin-bottom:6px}}
    .expo-impact-card .eic-title{{font-family:"DM Serif Display",serif;font-size:.92rem;color:var(--text);margin-bottom:4px}}
    .expo-impact-card .eic-text{{font-size:.83rem;line-height:1.6;color:var(--text-mid)}}
    .anecdote-box{{display:flex;gap:14px;background:linear-gradient(135deg,#fff8ec,#f7efe2);border:1px solid var(--wood-light);border-left:4px solid var(--wood);border-radius:12px;padding:16px 18px;margin-top:14px}}
    .anecdote-box .ab-icon{{font-size:1.4rem;flex:0 0 auto}}
    .anecdote-box .ab-label{{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--wood-dark);margin-bottom:4px}}
    .anecdote-box .ab-text{{font-size:.87rem;line-height:1.68;color:var(--text-mid)}}
    .anecdote-box .ab-text + .ab-text{{margin-top:10px}}

    /* BOOKING/EXPEDIA INLINE */
    .be-cards{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:6px}}
    .be-card{{border-radius:12px;overflow:hidden;text-decoration:none;display:block;transition:transform .18s,box-shadow .18s}}
    .be-card:hover{{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.14)}}
    .be-card-img{{width:100%;height:90px;object-fit:cover}}
    .be-card-body{{padding:10px 12px;background:#f8f6f3}}
    .be-card-brand{{font-size:.62rem;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--text-light)}}
    .be-card-txt{{font-size:.82rem;font-weight:700;color:var(--text);margin-top:2px;line-height:1.3}}
    .stat-box{{
      background:var(--white);border-radius:10px;
      padding:9px 4px;text-align:center;
      box-shadow:0 2px 8px rgba(0,0,0,.05);border:1px solid var(--wood-light)
    }}
    .stat-val{{font-family:"DM Serif Display",serif;font-size:1.05rem;color:var(--blue-dark);line-height:1}}
    .stat-lbl{{font-size:.56rem;color:var(--text-light);text-transform:uppercase;letter-spacing:.02em;margin-top:3px;line-height:1.2}}

    /* SECTIONS */
    .section{{background:var(--white);border-radius:var(--radius);padding:18px 16px;min-width:0;margin-bottom:14px;box-shadow:0 2px 10px rgba(0,0,0,.05);border:1px solid var(--wood-light)}}
    .section-title{{font-family:"DM Serif Display",serif;font-size:1rem;color:var(--text-mid);margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid var(--wood-pale)}}

    /* PISTES */
    .piste-row{{display:flex;align-items:center;gap:14px;padding:13px 0;border-bottom:1px solid var(--wood-pale)}}
    .piste-row:last-child{{border-bottom:none}}
    .piste-dot{{width:15px;height:15px;border-radius:50%;flex-shrink:0}}
    .piste-bar-wrap{{flex:1;height:7px;background:var(--wood-pale);border-radius:4px;overflow:hidden}}
    .piste-bar{{height:100%;border-radius:4px;transition:width .4s ease}}
    .piste-count{{font-weight:800;font-size:1rem;min-width:30px;text-align:right;color:var(--text)}}

    /* TAGS */
    .tag{{display:inline-block;border-radius:22px;padding:4px 12px;font-size:.73rem;font-weight:600;margin:3px 2px}}
    .tag-niv{{background:var(--blue-light);color:var(--blue-dark)}}
    .tag-amb{{background:var(--wood-pale);color:var(--wood-dark)}}
    .tag-eq{{background:#e6f5eb;color:#1a6a2a}}

    /* PHOTO STATION */
    .photo-station{{width:100%;height:200px;object-fit:cover;border-radius:10px;margin-bottom:16px;display:block}}

    /* GALERIE PHOTOS (3+ photos supplémentaires) */
    .photo-gallery{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px}}
    .photo-gallery-item{{position:relative;aspect-ratio:4/3;border-radius:10px;overflow:hidden;cursor:pointer;background:#e8f3fb;transition:transform .2s,box-shadow .2s}}
    .photo-gallery-item:hover{{transform:translateY(-2px);box-shadow:0 6px 18px rgba(26,90,138,.25)}}
    .photo-gallery-item img{{width:100%;height:100%;object-fit:cover;display:block;transition:transform .4s ease}}
    .photo-gallery-item:hover img{{transform:scale(1.06)}}
    .photo-gallery-item::after{{
      content:"🔍";position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,.55);color:white;
      width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;
      font-size:.78rem;opacity:0;transition:opacity .2s;backdrop-filter:blur(4px)
    }}
    .photo-gallery-item:hover::after{{opacity:1}}
    @media(max-width:600px){{.photo-gallery{{grid-template-columns:repeat(2,1fr);gap:6px}}}}

    /* LIGHTBOX */
    .lightbox{{
      position:fixed;inset:0;background:rgba(0,0,0,.93);z-index:1000;display:none;
      align-items:center;justify-content:center;padding:20px;
      animation:lbFadeIn .25s ease
    }}
    .lightbox.open{{display:flex}}
    @keyframes lbFadeIn{{from{{opacity:0}}to{{opacity:1}}}}
    .lightbox-img{{max-width:100%;max-height:88vh;object-fit:contain;border-radius:8px;box-shadow:0 10px 40px rgba(0,0,0,.5)}}
    .lightbox-close{{
      position:absolute;top:18px;right:20px;width:44px;height:44px;border-radius:50%;
      background:rgba(255,255,255,.16);border:none;color:white;font-size:1.5rem;cursor:pointer;
      display:flex;align-items:center;justify-content:center;backdrop-filter:blur(8px);transition:background .15s
    }}
    .lightbox-close:hover{{background:rgba(255,255,255,.28)}}
    .lightbox-nav{{
      position:absolute;top:50%;transform:translateY(-50%);width:54px;height:54px;border-radius:50%;
      background:rgba(255,255,255,.14);border:none;color:white;font-size:1.6rem;cursor:pointer;
      display:flex;align-items:center;justify-content:center;backdrop-filter:blur(8px);transition:background .15s
    }}
    .lightbox-nav:hover{{background:rgba(255,255,255,.26)}}
    .lightbox-prev{{left:20px}}
    .lightbox-next{{right:20px}}
    .lightbox-count{{
      position:absolute;bottom:22px;left:50%;transform:translateX(-50%);color:rgba(255,255,255,.85);
      font-size:.85rem;font-weight:600;background:rgba(0,0,0,.45);padding:6px 14px;border-radius:20px;backdrop-filter:blur(8px)
    }}
    @media(max-width:600px){{
      .lightbox-nav{{width:42px;height:42px;font-size:1.2rem}}
      .lightbox-prev{{left:8px}}
      .lightbox-next{{right:8px}}
    }}

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
    .main-grid{{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px;align-items:start}}
    .main-grid>*{{min-width:0}}
    .tab-nav-wrap,.tab-content,.section{{max-width:100%}}
    @media(max-width:800px){{.main-grid{{grid-template-columns:minmax(0,1fr)}}}}

    /* SIDEBAR STICKY */
    .sidebar{{position:sticky;top:74px}}

    /* WIDGET MÉTÉO */
    .meteo-widget{{
      background:linear-gradient(135deg,#1a5a8a 0%,#3a7db8 100%);
      border-radius:var(--radius);padding:22px 26px;margin-bottom:16px;
      color:white;box-shadow:0 6px 22px rgba(26,90,138,.25);position:relative;overflow:hidden
    }}
    .meteo-widget::before{{
      content:"";position:absolute;top:-20px;right:-20px;width:140px;height:140px;
      background:radial-gradient(circle,rgba(255,255,255,.18) 0%,transparent 70%);pointer-events:none
    }}
    .meteo-head{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px;gap:12px}}
    .meteo-title{{font-family:"DM Serif Display",serif;font-size:1.15rem;line-height:1.2;color:white}}
    .meteo-sub{{font-size:.78rem;color:rgba(255,255,255,.72);margin-top:3px}}
    .meteo-now{{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.12);border-radius:12px;padding:8px 14px;backdrop-filter:blur(6px)}}
    .meteo-now-temp{{font-family:"DM Serif Display",serif;font-size:1.7rem;line-height:1;color:white}}
    .meteo-now-ico{{font-size:1.7rem;line-height:1}}
    .meteo-now-snow{{font-size:.72rem;color:rgba(255,255,255,.78);margin-top:2px}}
    .meteo-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}}
    .meteo-day{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.14);border-radius:10px;padding:9px 4px;text-align:center;transition:background .15s}}
    .meteo-day:hover{{background:rgba(255,255,255,.18)}}
    .meteo-day-lbl{{font-size:.68rem;font-weight:700;color:rgba(255,255,255,.82);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}}
    .meteo-day-ico{{font-size:1.2rem;margin-bottom:3px}}
    .meteo-day-t{{font-size:.78rem;font-weight:700;color:white}}
    .meteo-day-snow{{font-size:.65rem;color:#a8d8ff;margin-top:3px;font-weight:600}}
    .meteo-loading{{text-align:center;padding:14px 0;font-size:.85rem;color:rgba(255,255,255,.7)}}
    .meteo-error{{text-align:center;padding:14px 0;font-size:.82rem;color:rgba(255,255,255,.7)}}
    @media(max-width:520px){{
      .meteo-grid{{grid-template-columns:repeat(5,1fr);gap:4px}}
      .meteo-day{{padding:7px 2px}}
      .meteo-day-lbl{{font-size:.6rem}}
      .meteo-day-t{{font-size:.72rem}}
    }}

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

    /* ÉTOILE FAVORIS */
    .fav-star{{
      position:absolute;top:18px;left:18px;z-index:15;
      background:rgba(255,255,255,.92);backdrop-filter:blur(8px);
      border:2.5px solid #ffd451;border-radius:50%;
      width:58px;height:58px;display:flex;align-items:center;justify-content:center;
      cursor:pointer;font-size:1.7rem;transition:all .2s;
      box-shadow:0 4px 14px rgba(0,0,0,.25);color:#d49b00;
    }}
    .fav-star:hover{{background:#fff7d6;border-color:#ffb900;transform:scale(1.08)}}
    .fav-star.active{{background:rgba(255,255,255,.95);border-color:#ffb900;box-shadow:0 4px 16px rgba(255,180,0,.5)}}

    /* DOMAINE SKIABLE RELIÉ — encadré riche, couleur distincte (ambre/or) */
    .domaine-box{{
      display:block;text-decoration:none;color:inherit;margin:18px 0;border-radius:18px;overflow:hidden;
      background:linear-gradient(145deg,#0d3a6e 0%,#1a5a8a 100%);border:1px solid #0d3a6e;color:#fff;
      box-shadow:0 4px 18px rgba(13,58,110,.22);transition:transform .15s,box-shadow .15s
    }}
    .domaine-box:hover{{transform:translateY(-2px);box-shadow:0 8px 26px rgba(13,58,110,.32)}}
    .domaine-box-head{{padding:16px 20px 10px;display:flex;flex-direction:column;gap:3px}}
    .domaine-box-tag{{font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:rgba(255,255,255,.7)}}
    .domaine-box-name{{font-family:"DM Serif Display",serif;font-size:1.35rem;color:#fff;display:flex;align-items:center;gap:8px}}
    .domaine-box-arrow{{font-size:1.1rem;color:rgba(255,255,255,.75)}}
    .domaine-box-stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:0;padding:0 12px;border-top:1px solid rgba(255,255,255,.18);border-bottom:1px solid rgba(255,255,255,.18)}}
    .domaine-box-stats>div{{text-align:center;padding:12px 4px;min-width:0}}
    .dbs-val{{font-family:"DM Serif Display",serif;font-size:1.05rem;color:#fff;line-height:1.15;word-break:break-word;overflow-wrap:break-word}}
    .dbs-lbl{{font-size:.6rem;color:rgba(255,255,255,.7);text-transform:uppercase;letter-spacing:.03em;margin-top:3px}}
    @media(max-width:600px){{.domaine-box-stats{{grid-template-columns:repeat(2,1fr)}}}}
    .domaine-box-foot{{padding:10px 20px;font-size:.76rem;color:rgba(255,255,255,.78);font-weight:600}}

    /* Onglet Domaine */
    .dt-hero{{background:linear-gradient(145deg,#0d3a6e 0%,#1a5a8a 100%);border:1px solid #0d3a6e;border-radius:14px;padding:16px 18px;margin-bottom:16px}}
    .dt-hero h3{{font-family:"DM Serif Display",serif;font-size:1.3rem;color:#fff;margin-bottom:6px}}
    .dt-hero p{{color:rgba(255,255,255,.85);font-size:.88rem;line-height:1.6}}
    .dt-warn{{font-size:.8rem;color:#a05a2c;background:#fff4e6;padding:8px 12px;border-radius:8px;margin:12px 0}}
    .dt-subtitle{{margin:22px 0 12px;font-size:1.02rem;font-family:"DM Serif Display",serif;color:var(--text)}}
    .domaine-stats-mini{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}}
    .domaine-stats-mini div{{background:#f0f6fb;border-radius:10px;padding:12px 8px;text-align:center}}
    .domaine-stats-mini strong{{display:block;font-size:1.15rem;color:#0d3a6e;font-family:"DM Serif Display",serif}}
    .domaine-stats-mini span{{font-size:.65rem;color:var(--text-mid);text-transform:uppercase;letter-spacing:.04em}}
    @media(max-width:480px){{.domaine-stats-mini{{grid-template-columns:repeat(2,1fr)}}}}
    .domaine-see-all{{display:inline-block;margin-top:2px;color:#1a5a8a;font-weight:700;text-decoration:none;font-size:.85rem}}
    .domaine-see-all:hover{{text-decoration:underline}}
    .domaine-soeurs-grid{{display:grid;grid-template-columns:1fr;gap:12px}}
    @media(min-width:420px){{.domaine-soeurs-grid{{grid-template-columns:repeat(2,1fr)}}}}
    @media(min-width:700px){{.domaine-soeurs-grid{{grid-template-columns:repeat(3,1fr)}}}}
    .domaine-soeur-card{{
      display:block;background:var(--white);border:1px solid var(--wood-light);border-radius:12px;padding:14px 16px;text-decoration:none;
      transition:transform .15s,box-shadow .15s;box-shadow:0 2px 8px rgba(0,0,0,.04)
    }}
    .domaine-soeur-card:hover{{transform:translateY(-2px);box-shadow:0 6px 16px rgba(0,0,0,.1);border-color:#1a5a8a}}
    .domaine-soeur-name{{font-weight:800;color:var(--text);font-size:.92rem;margin-bottom:6px}}
    .domaine-soeur-stats{{display:flex;gap:10px;font-size:.75rem;color:var(--text-mid);margin-bottom:6px}}
    .domaine-soeur-sub{{font-size:.72rem;color:#1a5a8a;font-weight:700}}

    /* FOOTER */
    .mobile-bar{{
      display:none;position:fixed;bottom:52px;left:0;right:0;
      background:white;border-top:1.5px solid var(--wood-light);
      padding:10px 14px 12px;gap:10px;z-index:80;
      box-shadow:0 -4px 20px rgba(0,0,0,.1)
    }}
    @media(max-width:800px){{
      .mobile-bar{{display:flex}}
      body{{padding-bottom:132px}}
    }}
    .mobile-bar-btn{{
      flex:1;padding:12px 8px;border-radius:12px;font-weight:700;
      font-size:.88rem;text-align:center;cursor:pointer;border:none;
      font-family:"DM Sans",sans-serif;text-decoration:none;display:flex;
      align-items:center;justify-content:center;gap:6px
    }}
    .mobile-bar-official{{background:var(--wood-pale);color:var(--text-mid);border:2px solid var(--wood-light)}}
    .mobile-bar-booking{{background:#003580;color:white}}

    /* BOUTON SITE OFFICIEL */
    .official-btn{{
      width:100%;border:2px solid var(--wood);border-radius:var(--radius);
      padding:0;cursor:pointer;overflow:hidden;
      margin-bottom:16px;position:relative;
      box-shadow:0 6px 24px rgba(139,94,60,.28);
      display:block;min-height:126px;
      transition:transform .15s,box-shadow .15s
    }}
    .official-btn:hover{{transform:translateY(-2px);box-shadow:0 10px 32px rgba(139,94,60,.38)}}
    .official-btn-bg{{
      position:absolute;inset:0;
      background-image:url('https://images.unsplash.com/photo-1491555103944-7c647fd857e6?w=800&q=80');
      background-size:cover;background-position:center;
    }}
    .official-btn-bg::after{{
      content:'';position:absolute;inset:0;
      background:linear-gradient(150deg,rgba(20,42,26,.92) 0%,rgba(139,94,60,.86) 100%);
    }}
    .official-btn-badge{{
      position:absolute;top:12px;right:12px;z-index:2;
      background:#ffcc00;color:#2a1f14;font-weight:800;font-size:.62rem;
      text-transform:uppercase;letter-spacing:.05em;
      padding:4px 10px;border-radius:20px;
      box-shadow:0 2px 8px rgba(0,0,0,.25)
    }}
    .official-btn-content{{
      position:relative;z-index:1;padding:18px 18px 16px;
      text-align:left;color:white;
    }}
    .official-btn-chips{{
      display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;
    }}
    .official-btn-chip{{
      background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.32);
      border-radius:14px;padding:3px 9px;font-size:.68rem;font-weight:700;
      color:white;backdrop-filter:blur(4px);white-space:nowrap
    }}
    .official-btn-cta{{
      display:inline-flex;align-items:center;gap:5px;margin-top:8px;
      background:white;color:var(--wood-dark);font-weight:800;font-size:.8rem;
      padding:6px 14px;border-radius:20px
    }}

    /* FOOTER */
    .footer{{background:var(--blue-dark);color:rgba(255,255,255,.65);text-align:center;padding:26px 20px;font-size:.78rem;margin-top:40px;line-height:1.8}}
    .footer a{{color:rgba(255,255,255,.85);font-weight:600}}
    .footer a:hover{{color:white}}

    /* ══ TOPBAR / BOTTOM NAV APP ══ */
    .sf-topbar{{position:fixed;top:0;left:0;right:0;height:58px;background:rgba(255,255,255,.96);backdrop-filter:blur(6px);border-bottom:2px solid var(--wood-light);display:flex;align-items:center;justify-content:space-between;padding:0 14px;z-index:600;transition:transform .28s ease;overflow:visible}}
    .sf-topbar.sf-hide{{transform:translateY(-100%)}}
    .sf-topbar-logo{{display:flex;align-items:center;gap:7px;text-decoration:none;flex-shrink:0}}
    .sf-topbar-logo img{{width:42px;height:42px;border-radius:10px;object-fit:contain;box-shadow:0 4px 12px rgba(0,0,0,.18);background:white;flex-shrink:0}}
    .sf-topbar-logo span{{font-family:"DM Serif Display",serif;font-size:1.02rem;color:var(--blue-dark);white-space:nowrap}}
    .sf-topbar-app{{display:flex;align-items:center;gap:5px;background:linear-gradient(135deg,var(--blue-light),#eaf4ff);border:1px solid var(--blue-mid);border-radius:16px;padding:5px 12px;font-size:.72rem;font-weight:700;color:var(--blue-dark);text-decoration:none;white-space:nowrap;box-shadow:0 2px 8px rgba(58,125,184,.18)}}
    .sf-topbar-fav{{display:flex;align-items:center;gap:4px;text-decoration:none;color:var(--blue-dark);font-weight:700;font-size:.85rem;flex-shrink:0;padding:5px 9px;border-radius:16px}}
    @media(max-width:480px){{.sf-topbar-logo span{{display:none}}.sf-topbar-app{{font-size:.68rem;padding:5px 9px}}}}
    .sf-bottomnav{{position:fixed;bottom:0;left:0;right:0;height:52px;background:rgba(255,255,255,.98);backdrop-filter:blur(6px);border-top:2px solid var(--wood-light);display:flex;align-items:center;justify-content:space-around;z-index:550;box-shadow:0 -2px 16px rgba(0,0,0,.08);padding-bottom:env(safe-area-inset-bottom)}}
    .sf-bn-item{{flex:1;display:flex;align-items:center;justify-content:center;height:52px;font-size:1.25rem;text-decoration:none;color:var(--text-mid);position:relative}}
    .sf-bn-home{{flex:0 0 52px;margin-top:-20px}}
    .sf-bn-home-circle{{width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,var(--blue-dark),var(--blue-mid));display:flex;align-items:center;justify-content:center;font-size:1.4rem;box-shadow:0 6px 18px rgba(26,90,138,.4);border:3px solid var(--white)}}
  </style>
</head>
<body>
<canvas id="snowCanvas"></canvas>
<script>
(function(){{
  var canvas=document.getElementById('snowCanvas');
  if(!canvas) return;
  var ctx=canvas.getContext('2d');
  var W,H,flakes=[];
  function resize(){{W=canvas.width=window.innerWidth;H=canvas.height=window.innerHeight;}}
  function init(){{
    flakes=[];
    var N=Math.min(120,Math.round(W*H/14000));
    for(var i=0;i<N;i++){{
      flakes.push({{x:Math.random()*W,y:Math.random()*H,r:1+Math.random()*2.6,vy:0.3+Math.random()*1.1,vx:-0.4+Math.random()*0.8,o:0.35+Math.random()*0.5}});
    }}
  }}
  function tick(){{
    ctx.clearRect(0,0,W,H);
    for(var i=0;i<flakes.length;i++){{
      var f=flakes[i];
      f.y+=f.vy;f.x+=f.vx;
      if(f.y>H+5){{f.y=-5;f.x=Math.random()*W;}}
      if(f.x>W+5)f.x=-5;
      if(f.x<-5)f.x=W+5;
      ctx.globalAlpha=f.o;
      ctx.beginPath();
      ctx.arc(f.x,f.y,f.r,0,Math.PI*2);
      ctx.fillStyle='#ffffff';
      ctx.fill();
    }}
    ctx.globalAlpha=1;
    requestAnimationFrame(tick);
  }}
  resize();init();tick();
  window.addEventListener('resize',function(){{resize();init();}});
}})();
</script>

<div class="sf-topbar" id="sfTopbar">
  <a href="../index.html" class="sf-topbar-logo">
    <img src="../logo.png" alt="SnowFinder">
    <span>SnowFinder</span>
  </a>
  <a href="https://play.google.com/store/apps/details?id=fr.snowfinder.twa" class="sf-topbar-app">📲 L'app est dispo !</a>
  <a href="../favoris.html" class="sf-topbar-fav">⭐ <span id="sfFavCount">0</span></a>
</div>
<script>
(function(){{
  var bar = document.getElementById("sfTopbar");
  var lastY = window.scrollY, ticking = false;
  window.addEventListener("scroll", function(){{
    if(ticking) return;
    ticking = true;
    requestAnimationFrame(function(){{
      var y = window.scrollY;
      if(y > lastY && y > 60) bar.classList.add("sf-hide");
      else bar.classList.remove("sf-hide");
      lastY = y;
      ticking = false;
    }});
  }}, {{passive:true}});
  function updateFavCount(){{
    var favs = [];
    try {{ favs = JSON.parse(localStorage.getItem("sf_favorites")||"[]"); }} catch(e){{}}
    var el = document.getElementById("sfFavCount");
    if(el) el.textContent = favs.length;
  }}
  updateFavCount();
  window.addEventListener("storage", updateFavCount);
  window.addEventListener("focus", updateFavCount);
}})();
</script>

<div class="hero">
  <div class="hero-slides">
{carousel_slides_html}
  </div>
  <div class="hero-overlay"></div>
  <button class="hero-close" onclick="closeStation()" title="Retour" aria-label="Retour">✕</button>
  <div class="hero-score">{s['score']:.1f} ⭐</div>
  <button class="fav-star" id="favBtn" onclick="toggleFav()" title="Ajouter aux favoris">☆</button>
{carousel_nav_html}
  <div class="hero-content">
    <div class="hero-massif">⛷ {s['massif']}</div>
    <h1>{s['name']}</h1>
    <div class="hero-region">📍 {s['region']}</div>
  </div>
  {hero_illu_note}
</div>

<!-- NAVIGATION ONGLETS — pleine largeur, juste sous le hero, tout visible -->
<div class="tab-nav-wrap" id="tabNavWrap">
  <div class="tab-nav" id="tabNav">
    <button class="tab-btn active" onclick="switchTab('infos',this)">🎿 Infos</button>
    <button class="tab-btn" onclick="switchTab('pourqui',this)">👥 Pour qui ?</button>
    {domaine_tab_btn}
    {expo_tab_btn}
    <button class="tab-btn" onclick="switchTab('meteo',this)">🌤 Météo</button>
    <button class="tab-btn" onclick="switchTab('neige',this)">❄️ Enneigement</button>
    <button class="tab-btn" onclick="switchTab('avis',this)">✍️ Notre avis</button>
  </div>
</div>

<script>
var STATION_ID = {s['id']};
function getFavs(){{return JSON.parse(localStorage.getItem('sf_favorites')||'[]');}}
function saveFavs(f){{localStorage.setItem('sf_favorites',JSON.stringify(f));}}
function updateStar(){{
  var favs=getFavs();
  var isFav=favs.indexOf(STATION_ID)!==-1;
  var btn=document.getElementById('favBtn');
  if(isFav){{
    if(btn){{btn.textContent='⭐';btn.classList.add('active');btn.title='Retirer des favoris';}}
  }}else{{
    if(btn){{btn.textContent='☆';btn.classList.remove('active');btn.title='Ajouter aux favoris';}}
  }}
}}
function toggleFav(){{
  var favs=getFavs();
  var idx=favs.indexOf(STATION_ID);
  if(idx===-1){{
    favs.push(STATION_ID);
    showFavToast(true);
    checkSnowForNewFav();
    if(typeof OneSignal!=='undefined') OneSignal.User.addTag('fav_'+STATION_ID,'1');
  }}else{{
    favs.splice(idx,1);
    showFavToast(false);
    if(typeof OneSignal!=='undefined') OneSignal.User.removeTag('fav_'+STATION_ID);
  }}
  saveFavs(favs);updateStar();
}}
function checkSnowForNewFav(){{
  var coords={{lat:{snow_lat},lon:{snow_lon}}};
  if(!coords.lat) return;
  fetch('https://api.open-meteo.com/v1/forecast?latitude='+coords.lat+'&longitude='+coords.lon+'&daily=snowfall_sum&forecast_days=5&timezone=Europe%2FParis')
    .then(function(r){{return r.json();}})
    .then(function(data){{
      var maxSnow=Math.round(Math.max.apply(null,data.daily.snowfall_sum.map(function(v){{return v||0;}})));
      if(maxSnow>=15){{
        setTimeout(function(){{
          var t=document.createElement('div');
          t.innerHTML='🌨️ <strong>'+maxSnow+'cm de neige prévus à {station_name_esc} !</strong><br><span style="font-size:.78rem;opacity:.85">Va vite réserver avant que les prix montent !</span>';
          t.style.cssText='position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:#1a3f6e;color:white;padding:14px 22px;border-radius:16px;font-size:.88rem;font-weight:700;z-index:999;box-shadow:0 6px 28px rgba(0,0,0,.35);pointer-events:none;text-align:center;max-width:280px;line-height:1.5;transition:opacity .4s';
          document.body.appendChild(t);
          setTimeout(function(){{t.style.opacity='0';}},3500);
          setTimeout(function(){{t.remove();}},4000);
        }},500);
      }}
    }}).catch(function(){{}});
}}
function showFavToast(added){{
  var t=document.createElement('div');
  t.textContent=added?'⭐ Ajouté aux favoris !':'☆ Retiré des favoris';
  t.style.cssText='position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:#2a1f14;color:white;padding:12px 22px;border-radius:30px;font-size:.88rem;font-weight:700;z-index:999;box-shadow:0 4px 20px rgba(0,0,0,.3);pointer-events:none;transition:opacity .3s';
  document.body.appendChild(t);
  setTimeout(function(){{t.style.opacity='0';}},1800);
  setTimeout(function(){{t.remove();}},2100);
}}
updateStar();

// ── ONGLETS ──
function switchTab(name, btn){{
  document.querySelectorAll('.tab-content').forEach(function(el){{el.classList.remove('active');}});
  document.querySelectorAll('.tab-btn').forEach(function(el){{el.classList.remove('active');}});
  document.getElementById('tab-'+name).classList.add('active');
  btn.classList.add('active');
}}
function toggleReadMore(id, btn){{
  var el = document.getElementById(id);
  var expanded = el.classList.toggle('expanded');
  btn.textContent = expanded ? 'Voir moins ▲' : 'Lire plus ▼';
}}
(function(){{
  var nav = document.getElementById('tabNav'), wrap = document.getElementById('tabNavWrap'), hint = document.getElementById('tabScrollHint');
  if(!nav||!wrap) return;
  function check(){{
    var overflow = nav.scrollWidth > nav.clientWidth + 4;
    if(hint) hint.classList.toggle('show', overflow);
    wrap.classList.toggle('scrolled-end', nav.scrollLeft + nav.clientWidth >= nav.scrollWidth - 4);
  }}
  nav.addEventListener('scroll', check);
  window.addEventListener('resize', check);
  check();
}})();

// ── MÉTÉO LIVE (Open-Meteo) ──
(function loadMeteo(){{
  var lat={snow_lat}, lon={snow_lon};
  if(lat===null||lon===null||isNaN(parseFloat(lat))){{
    var ld=document.getElementById('meteoLoading');
    if(ld) ld.textContent='Météo indisponible pour cette station';
    return;
  }}
  var url='https://api.open-meteo.com/v1/forecast?latitude='+lat+'&longitude='+lon+'&current=temperature_2m,weathercode,snow_depth,wind_speed_10m&daily=weathercode,temperature_2m_max,temperature_2m_min,snowfall_sum&timezone=Europe%2FParis&forecast_days=5';
  function ico(c){{
    if(c==null) return '☁️';
    if(c===0) return '☀️';
    if(c<=3) return '🌤️';
    if(c<=48) return '🌫️';
    if(c<=57) return '🌦️';
    if(c<=67) return '🌧️';
    if(c<=77) return '❄️';
    if(c<=82) return '🌧️';
    if(c<=86) return '🌨️';
    return '⛈️';
  }}
  var DAY_LBL=['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'];
  fetch(url).then(function(r){{return r.json();}}).then(function(d){{
    var ld=document.getElementById('meteoLoading');
    if(ld) ld.style.display='none';
    if(d.current){{
      var nowEl=document.getElementById('meteoNow');
      var t=Math.round(d.current.temperature_2m);
      document.getElementById('meteoNowTemp').textContent=t+'°';
      document.getElementById('meteoNowIco').textContent=ico(d.current.weathercode);
      var sd=d.current.snow_depth;
      var sub='';
      if(sd!=null&&sd>0) sub='Neige au sol : '+Math.round(sd*100)+' cm';
      else if(d.current.wind_speed_10m!=null) sub='Vent '+Math.round(d.current.wind_speed_10m)+' km/h';
      document.getElementById('meteoNowSnow').textContent=sub;
      nowEl.style.display='flex';

      // ── Onglet Enneigement : valeurs comparatives ──
      var snowCm = (sd!=null&&sd>0) ? Math.round(sd*100) : 0;

      // "Actuellement"
      var nowEl2=document.getElementById('snowNowVal');
      if(nowEl2) nowEl2.textContent=snowCm;

      // Moyenne mensuelle estimée (mois en cours + altitude + référence annuelle)
      // Facteur mensuel basé sur la climatologie alpine typique
      var monthFactors=[0,0.90,1.00,0.80,0.45,0.10,0,0,0,0,0.05,0.20,0.50];
      var altMax={s['alt_max']};
      // Bonus altitude : stations hautes gardent la neige plus longtemps
      var altBonus = altMax >= 3000 ? 1.8 : altMax >= 2500 ? 1.5 : altMax >= 2000 ? 1.2 : altMax >= 1500 ? 0.9 : 0.6;
      var curMonth = new Date().getMonth()+1; // 1-12
      var factor = (monthFactors[curMonth]||0) * altBonus;
      var snowAnnual = {s.get('snow', 100)};
      var snowMonthTypical = Math.round(snowAnnual * factor);

      var monthEl=document.getElementById('snowMonthVal');
      if(monthEl) monthEl.textContent=snowMonthTypical;

      // Barre de comparaison actuel vs mois
      var barWrap=document.getElementById('snowCompareBar');
      var barFill=document.getElementById('snowBarFill');
      var barLabel=document.getElementById('snowCompareLabel');
      if(barWrap&&barFill&&barLabel&&snowMonthTypical>0){{
        barWrap.style.display='block';
        var pct=Math.min(150,Math.round((snowCm/snowMonthTypical)*100));
        barFill.style.width=Math.min(100,pct)+'%';
        barFill.style.background=pct>=90?'#2ea84e':pct>=60?'#f0a500':'#cc2200';
        var txt=pct>=110?'Au-dessus de la normale ('+pct+'%)':pct>=80?'Dans la normale ('+pct+'%)':'En dessous de la normale ('+pct+'%)';
        barLabel.textContent=txt;
      }}else if(barWrap&&snowMonthTypical===0){{
        barWrap.style.display='block';
        if(barFill) barFill.style.width='0%';
        if(barLabel) barLabel.textContent='Hors saison — enneigement non significatif';
      }}
    }}
    if(d.daily&&d.daily.time){{
      var g=document.getElementById('meteoGrid');
      var h='';
      var DAY_LBL=['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'];
      for(var i=0;i<d.daily.time.length;i++){{
        var dt=new Date(d.daily.time[i]+'T12:00:00');
        var lbl=i===0?'Auj.':DAY_LBL[dt.getDay()];
        var tmax=Math.round(d.daily.temperature_2m_max[i]);
        var tmin=Math.round(d.daily.temperature_2m_min[i]);
        var sf=Math.round(d.daily.snowfall_sum[i]||0);
        h+='<div class="meteo-day">'
          +'<div class="meteo-day-lbl">'+lbl+'</div>'
          +'<div class="meteo-day-ico">'+ico(d.daily.weathercode[i])+'</div>'
          +'<div class="meteo-day-t">'+tmax+'° / '+tmin+'°</div>'
          +(sf>0?'<div class="meteo-day-snow">❄ '+sf+'cm</div>':'')
          +'</div>';
      }}
      g.innerHTML=h;
      g.style.display='grid';

      // Barres de chutes prévues dans l'onglet Enneigement
      var barsEl=document.getElementById('snowForecastBars');
      var lblsEl=document.getElementById('snowForecastLabels');
      if(barsEl&&lblsEl&&d.daily.snowfall_sum){{
        var sfArr=d.daily.snowfall_sum.map(function(v){{return Math.round(v||0);}});
        var sfMax=Math.max(1,Math.max.apply(null,sfArr));
        var bH='';var bL='';
        for(var i=0;i<sfArr.length;i++){{
          var dt=new Date(d.daily.time[i]+'T12:00:00');
          var lbl=i===0?'Auj.':DAY_LBL[dt.getDay()];
          var pct=Math.round((sfArr[i]/sfMax)*100);
          var color=sfArr[i]>0?'#3a7db8':'#e0eaf5';
          bH+='<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px">'
            +'<div style="font-size:.68rem;font-weight:700;color:#1a5a8a">'+(sfArr[i]>0?sfArr[i]+'cm':'')+'</div>'
            +'<div style="width:100%;background:'+color+';border-radius:4px 4px 0 0;height:'+Math.max(4,pct*0.55)+'px;transition:height .3s"></div>'
            +'</div>';
          bL+='<div style="flex:1;text-align:center;font-size:.65rem;color:var(--text-light);font-weight:600">'+lbl+'</div>';
        }}
        barsEl.style.cssText='display:flex;gap:6px;align-items:flex-end;height:80px;padding-bottom:0';
        barsEl.innerHTML=bH;
        lblsEl.style.cssText='display:flex;gap:6px;margin-top:4px';
        lblsEl.innerHTML=bL;
      }}
    }}
  }}).catch(function(){{
    var ld=document.getElementById('meteoLoading');
    if(ld) ld.textContent='Météo momentanément indisponible';
  }});
}})();

// ── CARROUSEL HERO ──
var HERO_URLS = {carousel_urls_js};
var heroIdx = 0;
var heroAuto = null;
function heroShow(i){{
  if(!HERO_URLS.length) return;
  heroIdx = (i + HERO_URLS.length) % HERO_URLS.length;
  document.querySelectorAll('.hero-slide').forEach(function(el){{
    el.classList.toggle('active', parseInt(el.dataset.idx) === heroIdx);
  }});
  document.querySelectorAll('.hero-dot').forEach(function(el){{
    el.classList.toggle('active', parseInt(el.dataset.idx) === heroIdx);
  }});
}}
function heroNext(){{ heroShow(heroIdx + 1); resetHeroAuto(); }}
function heroPrev(){{ heroShow(heroIdx - 1); resetHeroAuto(); }}
function heroGoTo(i){{ heroShow(i); resetHeroAuto(); }}
function resetHeroAuto(){{
  if(heroAuto) clearInterval(heroAuto);
  if(HERO_URLS.length > 1) heroAuto = setInterval(function(){{ heroShow(heroIdx + 1); }}, 5000);
}}
// Démarrer le défilement auto si plus d'1 photo
if(HERO_URLS.length > 1) resetHeroAuto();
// Pause au survol (desktop)
var heroEl = document.querySelector('.hero');
if(heroEl && HERO_URLS.length > 1){{
  heroEl.addEventListener('mouseenter', function(){{ if(heroAuto) clearInterval(heroAuto); }});
  heroEl.addEventListener('mouseleave', resetHeroAuto);
}}
// Swipe sur mobile
if(heroEl && HERO_URLS.length > 1){{
  var sx = 0;
  heroEl.addEventListener('touchstart', function(e){{ sx = e.touches[0].clientX; }}, {{passive:true}});
  heroEl.addEventListener('touchend', function(e){{
    var dx = e.changedTouches[0].clientX - sx;
    if(dx > 50) heroPrev();
    else if(dx < -50) heroNext();
  }});
}}

// Clic sur slide = ouvrir lightbox
function heroLightbox(i){{
  if(typeof openLightbox === 'function') openLightbox(i);
}}

// CROIX DE FERMETURE : retour à la page précédente (filtres préservés via sessionStorage côté recherche.html)
function closeStation(){{
  if(document.referrer && document.referrer.indexOf(window.location.origin) === 0){{
    history.back();
  }} else {{
    window.location.href = '../recherche.html';
  }}
}}
</script>

<div class="container">

  <nav class="breadcrumb">
    <a href="../index.html">Accueil</a> ›
    <a href="../recherche.html">Stations de ski</a> ›
    <a href="../recherche.html">{s['massif']}</a> ›
    <span>{s['name']}</span>
  </nav>

  <!-- STATS 5 colonnes -->
  <div class="stats-grid">
    <div class="stat-box">
      <div class="stat-val">{display_km} km</div>
      <div class="stat-lbl">{km_lbl}</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{display_alt_min}m</div>
      <div class="stat-lbl">Village</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{display_alt_max}m</div>
      <div class="stat-lbl">{alt_max_lbl}</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{display_remontees}</div>
      <div class="stat-lbl">{remontees_lbl}</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{s['forfait']}€</div>
      <div class="stat-lbl">Forfait / jour</div>
    </div>
  </div>

  {domaine_badge_html}

  <div class="main-grid">

    <!-- COLONNE PRINCIPALE : 5 ONGLETS -->
    <div>

      <!-- ONGLET 1 : INFOS -->
      <div class="tab-content active" id="tab-infos">

        <!-- À PROPOS -->
        <div class="section">
          <div class="section-title">À propos de {s['name']}</div>
          {f'<img src="{photo_station}" alt="{s["name"]} pistes de ski" class="photo-station" loading="lazy">' if photo_station else ''}
          <div class="readmore-wrap" id="rm-desc">
            <p style="font-size:.85rem;line-height:1.7;color:var(--text-mid)">{desc_long}</p>
          </div>
          <div class="readmore-btn" onclick="toggleReadMore('rm-desc',this)">Lire plus ▼</div>
          {f'<ul style="margin-top:14px;padding-left:0;list-style:none">{pts_html}</ul>' if pts_html else ''}
          {anecdote_html}
        </div>

        <!-- PISTES -->
        <div class="section">
          <div class="section-title">Domaine skiable — {display_km} km · {display_alt_min}m à {display_alt_max}m</div>
          <div class="piste-row">
            <div class="piste-dot" style="background:#2ea84e"></div>
            <span style="flex:0 0 76px;font-size:.88rem;font-weight:600;color:var(--text-mid)">Vertes</span>
            <div class="piste-bar-wrap"><div class="piste-bar" style="background:#2ea84e;width:{min(100, s['pistes']['v']*5)}%"></div></div>
            <span class="piste-count">{s['pistes']['v']}</span>
          </div>
          <div class="piste-row">
            <div class="piste-dot" style="background:#3a7db8"></div>
            <span style="flex:0 0 76px;font-size:.88rem;font-weight:600;color:var(--text-mid)">Bleues</span>
            <div class="piste-bar-wrap"><div class="piste-bar" style="background:#3a7db8;width:{min(100, s['pistes']['b']*3)}%"></div></div>
            <span class="piste-count">{s['pistes']['b']}</span>
          </div>
          <div class="piste-row">
            <div class="piste-dot" style="background:#cc2200"></div>
            <span style="flex:0 0 76px;font-size:.88rem;font-weight:600;color:var(--text-mid)">Rouges</span>
            <div class="piste-bar-wrap"><div class="piste-bar" style="background:#cc2200;width:{min(100, s['pistes']['r']*3)}%"></div></div>
            <span class="piste-count">{s['pistes']['r']}</span>
          </div>
          <div class="piste-row">
            <div class="piste-dot" style="background:#222"></div>
            <span style="flex:0 0 76px;font-size:.88rem;font-weight:600;color:var(--text-mid)">Noires</span>
            <div class="piste-bar-wrap"><div class="piste-bar" style="background:#333;width:{min(100, s['pistes']['n']*6)}%"></div></div>
            <span class="piste-count">{s['pistes']['n']}</span>
          </div>
        </div>

        <!-- INFOS PRATIQUES -->
        <div class="section" style="margin-bottom:0">
          <div class="section-title">Informations pratiques</div>
          <p style="font-size:.83rem;line-height:1.65;color:var(--text-mid)">
            <strong>{s['name']}</strong> est une station de ski du massif <strong>{s['massif']}</strong>,
            en <strong>{s['region']}</strong>. Le domaine s'étend sur
            <strong>{display_km} km de pistes</strong> entre {display_alt_min} m et {display_alt_max} m,
            desservi par {display_remontees} remontées mécaniques. Forfait journée à partir de
            <strong>{s['forfait']}€</strong> par adulte.
          </p>
        </div>

      </div>

      <!-- ONGLET 2 : POUR QUI ? -->
      <div class="tab-content" id="tab-pourqui">

        <div class="section">
          <div class="section-title">Ambiance &amp; caractère</div>
          <div class="tile-grid" style="margin-bottom:4px">
            {amb_tiles}
          </div>
        </div>

        <div class="section">
          <div class="section-title">Niveaux recommandés</div>
          <div class="tile-grid">
            {niv_tiles}
          </div>
        </div>

        <div class="section">
          <div class="section-title">Pour qui ?</div>
          <div style="padding-top:4px">{pour_qui_html}</div>
        </div>

        <div class="section" style="margin-bottom:0">
          <div class="section-title">Meilleure période pour skier</div>
          <div style="display:flex;gap:4px;margin-top:4px">{periode_html}</div>
          <p style="font-size:.73rem;color:var(--text-light);margin-top:10px">Basé sur l'altitude et l'enneigement historique de la station</p>
        </div>

      </div>

      {domaine_tab_html}

      <!-- ONGLET EXPOSITION : ORIENTATION DU VILLAGE ET DU DOMAINE (omis si aucune donnée vérifiée) -->
      {f'<div class="tab-content" id="tab-expo">{expo_html}</div>' if expo_html else ''}

      <!-- ONGLET 3 : MÉTÉO -->
      <div class="tab-content" id="tab-meteo">
        <div class="meteo-widget" id="meteoWidget">
          <div class="meteo-head">
            <div>
              <div class="meteo-title">❄️ Météo à {s['name']}</div>
              <div class="meteo-sub">Conditions actuelles &amp; prévisions 5 jours</div>
            </div>
            <div class="meteo-now" id="meteoNow" style="display:none">
              <span class="meteo-now-ico" id="meteoNowIco">☁️</span>
              <div>
                <div class="meteo-now-temp" id="meteoNowTemp">—°</div>
                <div class="meteo-now-snow" id="meteoNowSnow"></div>
              </div>
            </div>
          </div>
          <div class="meteo-loading" id="meteoLoading">Chargement…</div>
          <div class="meteo-grid" id="meteoGrid" style="display:none"></div>
        </div>
        <p style="font-size:.75rem;color:rgba(255,255,255,.6);text-align:center;margin-top:10px">Source : Open-Meteo.com · Données actualisées en temps réel</p>
      </div>

      <!-- ONGLET 4 : ENNEIGEMENT -->
      <div class="tab-content" id="tab-neige">

        <!-- Lecture principale : actuel vs période -->
        <div style="background:linear-gradient(135deg,#e8f3fb,#d0e7f5);border-radius:14px;padding:20px;margin-bottom:14px">
          <div style="font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:#3a7db8;margin-bottom:14px">❄️ Enneigement en ce moment (altitude station)</div>

          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px">
            <div style="background:white;border-radius:10px;padding:12px;text-align:center">
              <div style="font-size:.62rem;font-weight:700;color:var(--text-light);text-transform:uppercase;margin-bottom:6px">Actuellement</div>
              <div id="snowNowVal" style="font-family:'DM Serif Display',serif;font-size:2rem;color:#1a5a8a;line-height:1">—</div>
              <div style="font-size:.68rem;color:#3a7db8;font-weight:600;margin-top:2px">cm</div>
            </div>
            <div style="background:white;border-radius:10px;padding:12px;text-align:center">
              <div style="font-size:.62rem;font-weight:700;color:var(--text-light);text-transform:uppercase;margin-bottom:6px">Moy. ce mois</div>
              <div id="snowMonthVal" style="font-family:'DM Serif Display',serif;font-size:2rem;color:#2a6090;line-height:1">—</div>
              <div style="font-size:.68rem;color:#3a7db8;font-weight:600;margin-top:2px">cm</div>
            </div>
            <div style="background:white;border-radius:10px;padding:12px;text-align:center">
              <div style="font-size:.62rem;font-weight:700;color:var(--text-light);text-transform:uppercase;margin-bottom:6px">Moy. annuelle</div>
              <div style="font-family:'DM Serif Display',serif;font-size:2rem;color:#3a7db8;line-height:1">{s.get('snow','—')}</div>
              <div style="font-size:.68rem;color:#3a7db8;font-weight:600;margin-top:2px">cm</div>
            </div>
          </div>

          <!-- Barre de comparaison actuel vs mois -->
          <div id="snowCompareBar" style="display:none">
            <div style="font-size:.65rem;color:#3a7db8;font-weight:700;margin-bottom:6px">Actuel vs moyenne du mois</div>
            <div style="background:rgba(255,255,255,.6);border-radius:8px;height:12px;overflow:hidden;margin-bottom:4px">
              <div id="snowBarFill" style="height:100%;background:#1a5a8a;border-radius:8px;transition:width .6s ease"></div>
            </div>
            <div id="snowCompareLabel" style="font-size:.68rem;color:#1a5a8a;font-weight:700"></div>
          </div>
        </div>

        <!-- Village vs Sommet : informatif, pas de faux chiffres -->
        <div style="background:white;border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:14px">
          <div style="font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:var(--text-light);margin-bottom:12px">📍 Village ({display_alt_min} m) vs Sommet ({s['alt_max']} m)</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div style="padding:12px;background:#f8f9ff;border-radius:10px">
              <div style="font-size:.72rem;font-weight:700;color:var(--text);margin-bottom:6px">🏘 Au village</div>
              <div style="font-size:.8rem;color:var(--text-mid);line-height:1.5">
                {'Neige garantie dès novembre — village à haute altitude.' if display_alt_min >= 1800 else
                 'Bonne couverture de janvier à mars en moyenne.' if display_alt_min >= 1200 else
                 'Enneigement variable selon les années — vérifier avant de partir.'}
              </div>
            </div>
            <div style="padding:12px;background:#e8f3fb;border-radius:10px">
              <div style="font-size:.72rem;font-weight:700;color:#1a5a8a;margin-bottom:6px">⛰ Au sommet</div>
              <div style="font-size:.8rem;color:var(--text-mid);line-height:1.5">
                {"Glacier permanent — ouverture quasi toute l'année." if s['alt_max'] >= 3200 else
                 'Neige de qualité de décembre à avril.' if s['alt_max'] >= 2500 else
                 'Bonne neige de janvier à mars.' if s['alt_max'] >= 2000 else
                 "Conditions variables selon l'hiver."}
              </div>
            </div>
          </div>
        </div>

        <!-- Chutes de neige prévues -->
        <div style="background:white;border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:14px">
          <div style="font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:var(--text-light);margin-bottom:10px">🌨 Chutes de neige prévues — 5 jours</div>
          <div id="snowForecastBars" style="display:flex;gap:8px;align-items:flex-end;height:80px">
            <div style="color:var(--text-light);font-size:.75rem">Chargement…</div>
          </div>
          <div id="snowForecastLabels" style="display:flex;gap:8px;margin-top:6px"></div>
        </div>

        <!-- Analyse fiabilité -->
        <div style="background:linear-gradient(135deg,#f8f5f0,#f0e8da);border:1px solid var(--wood-pale);border-radius:12px;padding:16px">
          <div style="font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.07em;color:var(--text-light);margin-bottom:10px">📊 Fiabilité enneigement</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div>
              <div style="font-size:.68rem;font-weight:700;color:var(--text-light);margin-bottom:4px">Meilleure période</div>
              <div style="font-size:.85rem;font-weight:700;color:var(--text)">{'Déc → Avr ✓' if s['alt_max'] >= 3000 else 'Jan → Mar ✓' if s['alt_max'] >= 2500 else 'Jan → Fév ✓' if s['alt_max'] >= 2000 else 'Jan uniquement'}</div>
            </div>
            <div>
              <div style="font-size:.68rem;font-weight:700;color:var(--text-light);margin-bottom:4px">Fiabilité globale</div>
              <div style="font-size:.85rem;font-weight:700;color:{'#2ea84e' if s['alt_max'] >= 2500 else '#f0a500' if s['alt_max'] >= 2000 else '#cc2200'}">{'Excellente ●●●' if s['alt_max'] >= 2500 else 'Bonne ●●○' if s['alt_max'] >= 2000 else 'Moyenne ●○○'}</div>
            </div>
            <div>
              <div style="font-size:.68rem;font-weight:700;color:var(--text-light);margin-bottom:4px">Altitude de départ</div>
              <div style="font-size:.85rem;font-weight:700;color:var(--text)">{display_alt_min} m {'✓' if display_alt_min >= 1500 else '⚠️'}</div>
            </div>
            <div>
              <div style="font-size:.68rem;font-weight:700;color:var(--text-light);margin-bottom:4px">Enneigement pic saison</div>
              <div style="font-size:.85rem;font-weight:700;color:var(--text)">{s.get('snow','—')} cm moy.</div>
            </div>
          </div>
          <p style="font-size:.68rem;color:var(--text-light);margin-top:10px;line-height:1.5">{snow_reliability} Données en temps réel : Open-Meteo (modèle météo). Moyennes mensuelles : estimations basées sur les données historiques de la station.</p>
        </div>

      </div>

      <!-- ONGLET 5 : NOTRE AVIS -->
      <div class="tab-content" id="tab-avis">

        <div class="section" style="border-left:4px solid var(--blue-mid);background:linear-gradient(135deg,var(--white) 0%,var(--blue-light) 100%);--rm-bg:var(--blue-light)">
          <div class="section-title" style="color:var(--blue-dark)">✍️ Notre avis sur {s['name']}</div>
          <div class="readmore-wrap" id="rm-avis">
            <p style="font-size:.85rem;line-height:1.7;color:var(--text-mid)">{verdict}</p>
          </div>
          <div class="readmore-btn" onclick="toggleReadMore('rm-avis',this)">Lire plus ▼</div>
        </div>

{gallery_html}

        {similar_html}

      </div>

    </div>

    <!-- SIDEBAR -->
    <div class="sidebar">

      <!-- SITE OFFICIEL (avec interstitiel) — mis en avant en premier -->
      <button onclick="showOfficialSheet()" class="official-btn">
        <div class="official-btn-bg"></div>
        <div class="official-btn-badge">✓ Officiel</div>
        <div class="official-btn-content">
          <div class="official-btn-chips">
            <span class="official-btn-chip">📹 Webcams</span>
            <span class="official-btn-chip">🗺️ Plan des pistes</span>
            <span class="official-btn-chip">ℹ️ Infos officielles</span>
          </div>
          <div style="font-size:1.05rem;font-weight:900;letter-spacing:-.01em;line-height:1.3">Site officiel de {s['name']}</div>
          <div class="official-btn-cta">C'est par ici →</div>
        </div>
      </button>

      <!-- BOOKING / EXPEDIA — style index -->
      <div style="border-radius:16px;overflow:hidden;box-shadow:0 8px 28px rgba(13,34,64,.18);margin-bottom:16px">

        <a href="{booking_url}" target="_blank" rel="noopener sponsored"
           style="display:block;text-decoration:none;overflow:hidden;position:relative"
           onmouseover="this.querySelector('img').style.transform='scale(1.05)'"
           onmouseout="this.querySelector('img').style.transform='scale(1)'">
          <div style="position:relative;overflow:hidden;height:130px">
            <img src="../img/chalet-booking.jpg" alt="Réserver sur Booking" loading="lazy"
                 style="width:100%;height:100%;object-fit:cover;display:block;transition:transform .5s ease"
                 onerror="this.src='https://images.unsplash.com/photo-1502784444187-359ac186c5bb?w=600&q=80'">
            <div style="position:absolute;inset:0;background:linear-gradient(to right,rgba(0,35,110,.82) 0%,rgba(0,35,110,.4) 55%,transparent 100%);display:flex;align-items:center;padding:0 18px;gap:12px">
              <span style="font-size:1.7rem;filter:drop-shadow(0 2px 6px rgba(0,0,0,.5))">🏨</span>
              <div>
                <div style="color:white;font-weight:800;font-size:.95rem;text-shadow:0 1px 5px rgba(0,0,0,.6)">Booking.com</div>
                <div style="color:rgba(255,255,255,.82);font-size:.7rem;margin-top:1px">Dès ~{prix_nuit}€/nuit · Annulation gratuite</div>
              </div>
              <div style="margin-left:auto;background:white;color:#003d96;font-size:.75rem;font-weight:800;padding:6px 12px;border-radius:20px;white-space:nowrap">Voir →</div>
            </div>
          </div>
        </a>

        <a href="{expedia_url}" target="_blank" rel="noopener sponsored"
           style="display:block;text-decoration:none;overflow:hidden;position:relative;border-top:2px solid white"
           onmouseover="this.querySelector('img').style.transform='scale(1.05)'"
           onmouseout="this.querySelector('img').style.transform='scale(1)'">
          <div style="position:relative;overflow:hidden;height:130px">
            <img src="../img/chalet-expedia.jpg" alt="Réserver sur Expedia" loading="lazy"
                 style="width:100%;height:100%;object-fit:cover;display:block;transition:transform .5s ease"
                 onerror="this.src='https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=600&q=80'">
            <div style="position:absolute;inset:0;background:linear-gradient(to right,rgba(140,95,0,.85) 0%,rgba(140,95,0,.4) 55%,transparent 100%);display:flex;align-items:center;padding:0 18px;gap:12px">
              <span style="font-size:1.7rem;filter:drop-shadow(0 2px 6px rgba(0,0,0,.5))">✈️</span>
              <div>
                <div style="color:white;font-weight:800;font-size:.95rem;text-shadow:0 1px 5px rgba(0,0,0,.6)">Expedia</div>
                <div style="color:rgba(255,255,255,.82);font-size:.7rem;margin-top:1px">Vol + Hôtel · Packs ski</div>
              </div>
              <div style="margin-left:auto;background:#ffcc00;color:#1a2060;font-size:.75rem;font-weight:800;padding:6px 12px;border-radius:20px;white-space:nowrap">Réserver →</div>
            </div>
          </div>
        </a>

        <div style="text-align:center;font-size:.62rem;color:var(--text-light);padding:7px 0;background:#faf9f7">Liens affiliés — prix identiques pour vous</div>
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

</div>

<!-- BOTTOM SHEET INTERSTITIEL -->
<div id="officialOverlay" onclick="hideOfficialSheet()" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:900;backdrop-filter:blur(4px)"></div>
<div id="officialSheet" style="display:none;position:fixed;bottom:0;left:0;right:0;z-index:901;background:#f5f1ec;border-radius:26px 26px 0 0;padding:0 0 36px;box-shadow:0 -12px 50px rgba(0,0,0,.3);transform:translateY(100%);transition:transform .38s cubic-bezier(.32,.72,0,1);max-height:92vh;overflow-y:auto">

  <!-- Poignée -->
  <div style="padding:14px 0 0;display:flex;justify-content:center">
    <div style="width:44px;height:5px;background:#ddd;border-radius:3px"></div>
  </div>

  <!-- Header -->
  <div style="padding:18px 24px 14px;text-align:center">
    <div style="font-size:1.7rem;font-weight:900;color:#2a1f14;margin-bottom:6px">🏔️ Hop, une seconde !</div>
    <p style="font-size:1.05rem;font-weight:700;color:#2a1f14;margin-bottom:8px">T'as pensé à dormir où à <span style="color:#1a5a8a">{s['name']}</span> ?</p>
    <p style="font-size:.9rem;color:#5c4a35;line-height:1.7">Les hébergements à {s['name']} partent vite en haute saison — surtout pendant les vacances scolaires.<br>Deux clics maintenant, et t'éviteras de dormir dans ta voiture. 🚗❄️</p>
  </div>

  <!-- Cards hébergement -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:0 20px 16px">

    <!-- Booking -->
    <a href="{booking_url}" target="_blank" rel="noopener sponsored" onclick="hideOfficialSheet()" style="text-decoration:none;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.15);display:block">
      <div style="position:relative;height:120px;overflow:hidden">
        <img src="../img/chalet-booking.jpg" alt="Chalet ski Booking" onerror="this.src='https://images.unsplash.com/photo-1502784444187-359ac186c5bb?w=400&q=80'" style="width:100%;height:100%;object-fit:cover">
        <div style="position:absolute;inset:0;background:linear-gradient(to top,rgba(0,35,128,.9) 0%,rgba(0,35,128,.3) 60%,transparent 100%)"></div>
        <div style="position:absolute;bottom:10px;left:12px;right:8px">
          <div style="color:white;font-weight:900;font-size:1rem">🏨 Booking</div>
          <div style="color:rgba(255,255,255,.85);font-size:.72rem;font-weight:600">Dès ~{prix_nuit}€/nuit</div>
        </div>
      </div>
      <div style="background:#003580;padding:11px 12px;text-align:center">
        <span style="color:white;font-weight:800;font-size:.88rem">Voir les offres →</span>
      </div>
    </a>

    <!-- Expedia -->
    <a href="{expedia_url}" target="_blank" rel="noopener sponsored" onclick="hideOfficialSheet()" style="text-decoration:none;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.15);display:block">
      <div style="position:relative;height:120px;overflow:hidden">
        <img src="../img/chalet-expedia.jpg" alt="Chalet montagne Expedia" onerror="this.src='https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400&q=80'" style="width:100%;height:100%;object-fit:cover">
        <div style="position:absolute;inset:0;background:linear-gradient(to top,rgba(0,35,100,.85) 0%,rgba(0,0,0,.2) 60%,transparent 100%)"></div>
        <div style="position:absolute;bottom:10px;left:12px;right:8px">
          <div style="color:white;font-weight:900;font-size:1rem">✈️ Expedia</div>
          <div style="color:rgba(255,255,255,.85);font-size:.72rem;font-weight:600">Comparer les prix</div>
        </div>
      </div>
      <div style="background:#ffcc00;padding:11px 12px;text-align:center">
        <span style="color:#003580;font-weight:800;font-size:.88rem">Réserver →</span>
      </div>
    </a>

  </div>

  <!-- Lien site officiel -->
  <div style="text-align:center;padding:0 24px">
    <a href="{official_url}" target="_blank" rel="noopener" onclick="hideOfficialSheet()" style="display:inline-block;font-size:.88rem;color:#5c4a35;font-weight:600;text-decoration:underline;padding:8px 16px">
      Non merci — continuer vers le site officiel de {s['name']} →
    </a>
  </div>

</div>

<!-- BARRE MOBILE FIXE -->
<div class="mobile-bar">
  <button onclick="showOfficialSheet()" class="mobile-bar-btn mobile-bar-official">
    🎿 Site officiel
  </button>
  <a href="{booking_url}" target="_blank" rel="noopener sponsored" class="mobile-bar-btn mobile-bar-booking">
    🏨 Réserver
  </a>
</div>

<script>
function showOfficialSheet(){{
  document.getElementById('officialOverlay').style.display='block';
  var s = document.getElementById('officialSheet');
  s.style.display='block';
  requestAnimationFrame(function(){{
    requestAnimationFrame(function(){{
      s.style.transform='translateY(0)';
    }});
  }});
  document.body.style.overflow='hidden';
}}
function hideOfficialSheet(){{
  var s = document.getElementById('officialSheet');
  s.style.transform='translateY(100%)';
  document.getElementById('officialOverlay').style.display='none';
  document.body.style.overflow='';
  setTimeout(function(){{ s.style.display='none'; }}, 380);
}}
</script>

<footer class="footer">
  <strong>SnowFinder</strong> — Le guide complet des stations de ski françaises<br>
  <a href="../index.html">Accueil</a> · <a href="../recherche.html">Recherche</a> · <a href="../comparateur.html">Comparateur</a> · <a href="../mentions-legales.html">Mentions légales</a><br>
  <span style="font-size:.7rem;opacity:.7">Données indicatives · Forfaits haute saison adulte · À vérifier sur le site officiel de chaque station</span>
</footer>

<!-- LIGHTBOX GALERIE -->
<div class="lightbox" id="lightbox" onclick="if(event.target===this)closeLightbox()">
  <button class="lightbox-close" onclick="closeLightbox()" aria-label="Fermer">✕</button>
  <button class="lightbox-nav lightbox-prev" onclick="lightboxPrev()" aria-label="Précédente">‹</button>
  <img class="lightbox-img" id="lightboxImg" src="" alt="">
  <button class="lightbox-nav lightbox-next" onclick="lightboxNext()" aria-label="Suivante">›</button>
  <div class="lightbox-count" id="lightboxCount"></div>
</div>
<script>
var GALLERY_URLS = {gallery_urls_js};
var lbIdx = 0;
function openLightbox(i){{
  if(!GALLERY_URLS.length) return;
  lbIdx = i;
  document.getElementById('lightboxImg').src = GALLERY_URLS[lbIdx];
  document.getElementById('lightboxCount').textContent = (lbIdx+1)+' / '+GALLERY_URLS.length;
  document.getElementById('lightbox').classList.add('open');
  document.body.style.overflow = 'hidden';
}}
function closeLightbox(){{
  document.getElementById('lightbox').classList.remove('open');
  document.body.style.overflow = '';
}}
function lightboxPrev(){{
  if(!GALLERY_URLS.length) return;
  lbIdx = (lbIdx - 1 + GALLERY_URLS.length) % GALLERY_URLS.length;
  document.getElementById('lightboxImg').src = GALLERY_URLS[lbIdx];
  document.getElementById('lightboxCount').textContent = (lbIdx+1)+' / '+GALLERY_URLS.length;
}}
function lightboxNext(){{
  if(!GALLERY_URLS.length) return;
  lbIdx = (lbIdx + 1) % GALLERY_URLS.length;
  document.getElementById('lightboxImg').src = GALLERY_URLS[lbIdx];
  document.getElementById('lightboxCount').textContent = (lbIdx+1)+' / '+GALLERY_URLS.length;
}}
document.addEventListener('keydown', function(e){{
  if(!document.getElementById('lightbox').classList.contains('open')) return;
  if(e.key==='Escape') closeLightbox();
  else if(e.key==='ArrowLeft') lightboxPrev();
  else if(e.key==='ArrowRight') lightboxNext();
}});
</script>

<nav class="sf-bottomnav">
  <a href="../recherche.html" class="sf-bn-item" title="Trouver ma station">🔍</a>
  <a href="../enneigement.html" class="sf-bn-item" title="Météo & enneigement">❄️</a>
  <a href="../index.html" class="sf-bn-item sf-bn-home" title="Accueil"><span class="sf-bn-home-circle">🏡</span></a>
  <a href="../tinder.html" class="sf-bn-item" title="Tinder du ski">💕</a>
  <a href="../hebergement.html" class="sf-bn-item" title="Hébergement">🛏️</a>
</nav>

</body>
</html>"""

def render_domaine_page(slug, d):
    canonical = f"https://snowfinder.fr/domaines/{slug}.html"
    pays_txt = " · ".join(d["pays"])

    # ── Photos du domaine : cascade domaine dédié -> stations membres -> placeholder ──
    dm_carousel_sources, dm_photo_source = get_domaine_photos_smart(slug, d)
    dm_hero_illu_note = '<div class="hero-illu-note">Photo d\'illustration</div>' if dm_photo_source == 'placeholder' else ''
    dm_carousel_slides_html = "\n".join(
        f'  <img class="hero-slide{" active" if i==0 else ""}" data-idx="{i}" src="{p}" alt="{d["name"]} photo {i+1}" loading="{("eager" if i==0 else "lazy")}">'
        for i, p in enumerate(dm_carousel_sources)
    )
    dm_carousel_urls_js = "[" + ",".join(f'"{p}"' for p in dm_carousel_sources) + "]"
    if len(dm_carousel_sources) > 1:
        dm_carousel_dots_html = "\n".join(
            f'    <button class="hero-dot{" active" if i==0 else ""}" data-idx="{i}" onclick="dmHeroGoTo({i})" aria-label="Photo {i+1}"></button>'
            for i in range(len(dm_carousel_sources))
        )
        dm_carousel_nav_html = f'''<button class="hero-nav hero-prev" onclick="dmHeroPrev()" aria-label="Précédente">‹</button>
<button class="hero-nav hero-next" onclick="dmHeroNext()" aria-label="Suivante">›</button>
<div class="hero-dots">
{dm_carousel_dots_html}
</div>'''
    else:
        dm_carousel_nav_html = ''

    # Classement par taille parmi tous les domaines
    rang = sorted(DOMAINES.values(), key=lambda x: -x['km_total']).index(d) + 1
    rang_txt = ("Top 3 des plus grands domaines de France" if rang <= 3
                else f"{rang}e plus grand domaine référencé")

    # Stations membres présentes dans DATA
    membres = [x for x in DATA if x['name'] in d['stations']]
    membres.sort(key=lambda x: -(d.get('km_propre', {}).get(x['name']) or 0))

    transfrontalier_badge = (
        f'<div class="dm-flag">🌍 Domaine transfrontalier — {pays_txt}</div>'
        if len(d["pays"]) > 1 else ''
    )
    conditionnel_html = (
        '<div class="dm-warn">⚠️ La liaison entre les stations de ce domaine n\'est ouverte que lorsque '
        'l\'enneigement le permet — vérifiez son statut avant de partir.</div>'
        if d.get('conditionnel') else ''
    )
    unifie_html = (
        '<div class="dm-note">ℹ️ Les stations de ce domaine partagent le même domaine skiable : '
        'les kilomètres de pistes ne sont pas répartis village par village.</div>'
        if d.get('unifie') and len(d['stations']) > 1 else ''
    )

    # ── Répartition des pistes ──
    pistes_html = ''
    P = d.get('pistes')
    if P and sum(P.values()) > 0:
        tot = sum(P.values())
        rows = []
        for key, lbl, col in (("v","Vertes","#2ea84e"),("b","Bleues","#3a7db8"),
                              ("r","Rouges","#cc2200"),("n","Noires","#333")):
            pc = round(P[key] / tot * 100)
            rows.append(f'''<div class="dm-piste-row">
        <span class="dm-piste-dot" style="background:{col}"></span>
        <span class="dm-piste-lbl">{lbl}</span>
        <span class="dm-piste-bar"><i style="background:{col};width:{pc}%"></i></span>
        <span class="dm-piste-n">{P[key]}</span>
      </div>''')
        pistes_html = f'''<div class="dm-section">
  <div class="dm-section-title">Les {tot} pistes du domaine</div>
  <div class="dm-card">{"".join(rows)}</div>
</div>'''

    # ── Chiffres clés dérivés ──
    faits = []
    if membres:
        moins_cher = min(membres, key=lambda x: x['forfait'])
        faits.append(("💶", f"{moins_cher['forfait']}€", f"Forfait le moins cher — {moins_cher['name']}"))
        plus_haut = max(membres, key=lambda x: d.get('alt_village', {}).get(x['name'], x['alt_min']))
        av = d.get('alt_village', {}).get(plus_haut['name'], plus_haut['alt_min'])
        faits.append(("🏔️", f"{av}m", f"Village le plus haut — {plus_haut['name']}"))
        mieux_note = max(membres, key=lambda x: x['score'])
        faits.append(("⭐", f"{mieux_note['score']:.1f}/5", f"Mieux notée — {mieux_note['name']}"))
    faits.append(("📏", f"{d['alt_max'] - d['alt_min']}m", "Dénivelé total du domaine"))
    faits_html = "".join(
        f'<div class="dm-fait"><span class="dm-fait-ico">{i}</span>'
        f'<span class="dm-fait-val">{v}</span><span class="dm-fait-lbl">{l}</span></div>'
        for i, v, l in faits
    )

    # ── Tableau comparatif des stations ──
    rows = []
    for st in membres:
        km_p = d.get('km_propre', {}).get(st['name'])
        km_txt = f"{km_p} km" if km_p else ("partagé" if d.get('unifie') else "—")
        av = d.get('alt_village', {}).get(st['name'], st['alt_min'])
        tags = "".join(f'<span class="dm-tag">{AMB.get(a, a)}</span>' for a in st.get('amb', [])[:3])
        rows.append(f'''<tr onclick="location.href='../stations/{slugify(st['name'])}.html'">
      <td class="dm-t-name">{st['name']}</td>
      <td>{av}m</td><td>{km_txt}</td><td>{st['forfait']}€</td>
      <td>⭐{st['score']:.1f}</td>
      <td class="dm-t-tags">{tags}</td>
      <td class="dm-t-go">→</td>
    </tr>''')
    tableau_html = f'''<div class="dm-section">
  <div class="dm-section-title">Les {len(d['stations'])} stations du domaine</div>
  <div class="dm-card dm-table-wrap">
    <table class="dm-table">
      <thead><tr><th>Station</th><th>Village</th><th>Pistes</th><th>Forfait</th><th>Note</th><th>Ambiance</th><th></th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>
</div>'''

    # ── Cartes stations (visuel) ──
    cards = []
    for st in membres:
        km_p = d.get('km_propre', {}).get(st['name'])
        km_line = f"🎿 {km_p} km propres" if km_p else "🎿 domaine partagé"
        av = d.get('alt_village', {}).get(st['name'], st['alt_min'])
        cards.append(f'''<a href="../stations/{slugify(st['name'])}.html" class="dm-station-card">
      <div class="dm-station-name">{st['name']}</div>
      <div class="dm-station-meta">🏘 {av}m · ⛰ {st['alt_max']}m · 💶 {st['forfait']}€</div>
      <div class="dm-station-km">{km_line}</div>
      <div class="dm-station-cta">Voir la fiche →</div>
    </a>''')
    stations_html = "\n".join(cards)

    # ── Autres domaines du même massif ──
    autres = [(s2, d2) for s2, d2 in DOMAINES.items()
              if d2['massif'] == d['massif'] and s2 != slug]
    autres_html = ''
    if autres:
        links = "".join(
            f'<a href="{s2}.html" class="dm-other">{d2["name"]}<span>{d2["km_total"]} km</span></a>'
            for s2, d2 in sorted(autres, key=lambda x: -x[1]['km_total'])[:6]
        )
        autres_html = f'''<div class="dm-section">
  <div class="dm-section-title">Autres domaines — {d['massif']}</div>
  <div class="dm-other-grid">{links}</div>
</div>'''

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>{d['name']} — Domaine skiable {d['km_total']} km, {len(d['stations'])} stations | SnowFinder</title>
<meta name="description" content="{d['name']} : {d['km_total']} km de pistes reliées, {len(d['stations'])} stations ({', '.join(d['stations'][:4])}...). Forfait {d['forfait_domaine']}€/jour, altitude {d['alt_min']}-{d['alt_max']}m.">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="SnowFinder">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{d['name']} — {d['km_total']} km reliés">
<meta property="og:description" content="{d['km_total']} km · {d['remontees_total']} remontées · {d['forfait_domaine']}€/j · {len(d['stations'])} stations reliées">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&family=DM+Serif+Display&display=swap" rel="stylesheet">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"SkiResort","name":"{d['name']}","url":"{canonical}",
"description":"{d['desc']}","containedInPlace":{{"@type":"Place","name":"{d['massif']}"}}}}
</script>
<style>
  :root{{--wood-pale:#f7efe2;--wood-light:#eddcbf;--wood:#c49a6c;--wood-dark:#8b5e3c;--blue:#5b9fd4;--blue-light:#e8f3fb;--blue-mid:#3a7db8;--blue-dark:#1a5a8a;--text:#2a1f14;--text-mid:#5c4a35;--text-light:#8a7060;--navy:#1a5a8a;--border:#e8d8c4;--bg:#f5f1ec}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{touch-action:pan-x pan-y;overflow-x:hidden;max-width:100%}}
  body{{font-family:"DM Sans",sans-serif;color:var(--text);background:linear-gradient(135deg,#e8f3fb 0%,#d0e7f5 50%,#e8f3fb 100%);background-attachment:fixed;min-height:100vh;padding-bottom:76px}}
  a{{color:inherit}}
  .dm-wrap{{max-width:980px;margin:0 auto}}
  @media(min-width:1200px){{.dm-wrap{{max-width:1180px}}}}
  .dm-hero{{position:relative;overflow:hidden;height:clamp(300px,46vh,480px);display:flex;align-items:flex-end;color:white}}
  /* CARROUSEL HERO (photos du domaine) — identique au hero des fiches stations */
  .hero-slides{{position:absolute;inset:0;width:100%;height:100%;z-index:0}}
  .hero-slide{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;opacity:0;transition:opacity .45s ease-in-out}}
  .hero-slide.active{{opacity:1}}
  .dm-hero-overlay{{position:absolute;inset:0;z-index:1;background:linear-gradient(to top,rgba(0,0,0,.88) 0%,rgba(0,0,0,.3) 45%,rgba(0,0,0,.05) 100%)}}
  .dm-hero-content{{position:relative;z-index:2;padding:0 28px 30px;text-align:center;width:100%}}
  .hero-nav{{position:absolute;top:50%;transform:translateY(-50%);width:38px;height:38px;border-radius:50%;background:rgba(255,255,255,.18);border:none;color:white;font-size:1.5rem;cursor:pointer;z-index:6;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(6px);transition:background .15s;line-height:1;padding-bottom:3px}}
  .hero-nav:hover{{background:rgba(255,255,255,.32)}}
  .hero-prev{{left:12px}}
  .hero-next{{right:12px}}
  .hero-dots{{position:absolute;bottom:14px;left:50%;transform:translateX(-50%);z-index:6;display:flex;gap:7px;background:rgba(0,0,0,.32);padding:6px 12px;border-radius:20px;backdrop-filter:blur(6px)}}
  .hero-dot{{width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,.45);border:none;cursor:pointer;padding:0;transition:background .2s,transform .2s}}
  .hero-dot.active{{background:white;transform:scale(1.3)}}
  .dm-hero-massif{{display:inline-block;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.3);border-radius:20px;padding:5px 14px;font-size:.75rem;font-weight:700;margin-bottom:10px}}
  .dm-hero h1{{font-family:"DM Serif Display",serif;font-size:clamp(1.8rem,5vw,2.4rem);margin-bottom:8px;line-height:1.15;text-shadow:0 2px 12px rgba(0,0,0,.5)}}
  .dm-hero p{{opacity:.92;font-size:.92rem;max-width:560px;margin:0 auto;text-shadow:0 1px 8px rgba(0,0,0,.4)}}
  .hero-illu-note{{position:absolute;bottom:8px;right:14px;z-index:6;font-style:italic;font-size:.66rem;color:rgba(255,255,255,.55);text-shadow:0 1px 4px rgba(0,0,0,.6)}}
  .dm-rank{{display:inline-block;margin-top:12px;background:linear-gradient(135deg,#d4a017,#b8860b);color:white;font-weight:700;font-size:.78rem;padding:6px 14px;border-radius:20px;box-shadow:0 2px 8px rgba(0,0,0,.25)}}
  .dm-fav{{position:absolute;top:18px;left:18px;z-index:20;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);
    border:2.5px solid #ffd451;border-radius:50%;width:44px;height:44px;display:flex;align-items:center;justify-content:center;
    cursor:pointer;font-size:1.3rem;transition:all .2s;box-shadow:0 4px 14px rgba(0,0,0,.25);color:#d49b00}}
  .dm-fav:hover{{background:#fff7d6;border-color:#ffb900;transform:scale(1.08)}}
  .dm-fav.active{{background:rgba(255,255,255,.95);border-color:#ffb900;box-shadow:0 4px 16px rgba(255,180,0,.5)}}
  .dm-close{{position:absolute;top:18px;right:18px;width:42px;height:42px;border-radius:50%;background:rgba(0,0,0,.5);backdrop-filter:blur(8px);border:1.5px solid rgba(255,255,255,.35);color:white;font-size:1.1rem;display:flex;align-items:center;justify-content:center;text-decoration:none;cursor:pointer;z-index:20;transition:all .15s}}
  .dm-close:hover{{background:rgba(0,0,0,.75);transform:scale(1.08)}}
  .dm-breadcrumb{{padding:14px 20px 0;font-size:.78rem;color:var(--text-mid)}}
  .dm-breadcrumb a{{text-decoration:none;color:#1a5a8a;font-weight:600}}
  .dm-flag,.dm-warn,.dm-note{{margin:14px 20px;padding:11px 16px;border-radius:10px;font-size:.82rem;font-weight:600;line-height:1.5}}
  .dm-flag{{background:var(--blue-light);color:var(--blue-dark)}}
  .dm-warn{{background:#fff4e6;color:#a05a2c}}
  .dm-note{{background:var(--wood-pale);color:var(--text-mid)}}
  .dm-stats{{margin:18px 0;padding:0 20px;display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}
  @media(min-width:620px){{.dm-stats{{grid-template-columns:repeat(4,1fr)}}}}
  .dm-stat{{background:white;border-radius:14px;padding:16px 10px;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.05);border:1px solid var(--wood-light)}}
  .dm-stat-val{{font-family:"DM Serif Display",serif;font-size:1.4rem;color:var(--navy);line-height:1.1}}
  .dm-stat-lbl{{font-size:.66rem;color:var(--text-mid);text-transform:uppercase;letter-spacing:.05em;margin-top:3px}}
  .dm-section{{margin:26px 0;padding:0 20px}}
  .dm-section-title{{font-family:"DM Serif Display",serif;font-size:1.15rem;color:var(--text-mid);margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid var(--wood-pale)}}
  .dm-card{{background:white;border-radius:14px;padding:18px 20px;box-shadow:0 2px 10px rgba(0,0,0,.05);border:1px solid var(--wood-light)}}
  .dm-desc{{font-size:.93rem;line-height:1.75;color:var(--text-mid)}}
  .dm-faits{{display:grid;grid-template-columns:repeat(2,1fr);gap:11px}}
  @media(min-width:620px){{.dm-faits{{grid-template-columns:repeat(4,1fr)}}}}
  .dm-fait{{background:white;border-radius:12px;padding:14px 12px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.04);border:1px solid var(--wood-light)}}
  .dm-fait-ico{{display:block;font-size:1.3rem}}
  .dm-fait-val{{display:block;font-family:"DM Serif Display",serif;font-size:1.15rem;color:var(--navy);margin:3px 0}}
  .dm-fait-lbl{{display:block;font-size:.66rem;color:var(--text-mid);line-height:1.35}}
  .dm-piste-row{{display:flex;align-items:center;gap:9px;margin-bottom:9px}}
  .dm-piste-row:last-child{{margin-bottom:0}}
  .dm-piste-dot{{width:11px;height:11px;border-radius:50%;flex-shrink:0}}
  .dm-piste-lbl{{flex:0 0 58px;font-size:.83rem;color:var(--text-mid)}}
  .dm-piste-bar{{flex:1;height:8px;background:var(--wood-pale);border-radius:5px;overflow:hidden}}
  .dm-piste-bar i{{display:block;height:100%;border-radius:5px}}
  .dm-piste-n{{flex:0 0 30px;text-align:right;font-weight:800;font-size:.85rem}}
  .dm-reco-grid{{display:grid;grid-template-columns:1fr;gap:11px}}
  @media(min-width:520px){{.dm-reco-grid{{grid-template-columns:repeat(2,1fr)}}}}
  .dm-reco{{display:block;background:white;border-radius:12px;padding:14px 16px;text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,.05);border:1px solid var(--wood-light);border-left:4px solid var(--blue-dark);transition:transform .15s}}
  .dm-reco:hover{{transform:translateX(3px)}}
  .dm-reco-t{{font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:var(--text-mid)}}
  .dm-reco-n{{font-family:"DM Serif Display",serif;font-size:1.1rem;color:var(--navy);margin:2px 0}}
  .dm-reco-w{{font-size:.76rem;color:var(--text-light)}}
  .dm-table-wrap{{padding:6px 8px;overflow-x:auto}}
  .dm-table{{width:100%;border-collapse:collapse;font-size:.84rem}}
  .dm-table th{{text-align:left;font-size:.66rem;text-transform:uppercase;letter-spacing:.05em;color:var(--text-light);padding:9px 8px;border-bottom:1px solid var(--border)}}
  .dm-table td{{padding:11px 8px;border-bottom:1px solid var(--wood-pale)}}
  .dm-table tr:last-child td{{border-bottom:none}}
  .dm-table tbody tr{{cursor:pointer;transition:background .12s}}
  .dm-table tbody tr:hover{{background:var(--wood-pale)}}
  .dm-t-name{{font-weight:800;color:var(--text)}}
  .dm-t-go{{color:var(--navy);font-weight:800;text-align:right}}
  .dm-t-tags{{white-space:nowrap}}
  .dm-tag{{display:inline-block;background:var(--wood-pale);color:var(--text-mid);border-radius:20px;padding:3px 9px;font-size:.68rem;font-weight:700;margin-right:4px}}
  .dm-stations-grid{{display:grid;grid-template-columns:1fr;gap:12px}}
  @media(min-width:460px){{.dm-stations-grid{{grid-template-columns:repeat(2,1fr)}}}}
  @media(min-width:760px){{.dm-stations-grid{{grid-template-columns:repeat(3,1fr)}}}}
  .dm-station-card{{display:block;background:white;border-radius:14px;padding:15px 17px;text-decoration:none;box-shadow:0 2px 10px rgba(0,0,0,.05);border:1px solid var(--wood-light);transition:transform .15s,box-shadow .15s}}
  .dm-station-card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,.1)}}
  .dm-station-name{{font-weight:800;font-size:1.03rem;margin-bottom:4px}}
  .dm-station-meta{{font-size:.76rem;color:var(--text-mid);margin-bottom:5px}}
  .dm-station-km{{font-size:.74rem;color:#1a5a8a;font-weight:700}}
  .dm-station-cta{{margin-top:8px;font-size:.78rem;font-weight:800;color:var(--navy)}}
  .dm-other-grid{{display:grid;grid-template-columns:1fr;gap:9px}}
  @media(min-width:520px){{.dm-other-grid{{grid-template-columns:repeat(2,1fr)}}}}
  .dm-other{{display:flex;justify-content:space-between;align-items:center;background:white;border-radius:10px;padding:12px 15px;text-decoration:none;font-weight:700;font-size:.87rem;box-shadow:0 2px 8px rgba(0,0,0,.04);border:1px solid var(--wood-light)}}
  .dm-other span{{color:var(--text-light);font-size:.78rem;font-weight:800}}
  .footer{{text-align:center;padding:30px 20px 20px;font-size:.8rem;color:var(--text-mid)}}
  .footer a{{color:#1a5a8a;text-decoration:none;font-weight:600}}
  .sf-bottomnav{{position:fixed;bottom:0;left:0;right:0;background:white;display:flex;justify-content:space-around;align-items:center;padding:8px 0;box-shadow:0 -2px 10px rgba(0,0,0,.08);z-index:80}}
  .sf-bn-item{{text-decoration:none;font-size:1.3rem;padding:6px 10px}}
  .sf-bn-home-circle{{background:var(--navy);color:white;border-radius:50%;width:42px;height:42px;display:flex;align-items:center;justify-content:center;font-size:1.2rem}}
</style>
</head>
<body>

<div class="dm-hero">
  <div class="hero-slides">
{dm_carousel_slides_html}
  </div>
  <div class="dm-hero-overlay"></div>
  <a href="#" class="dm-close" id="dmClose" aria-label="Retour">✕</a>
  <button class="dm-fav" id="dmFav" type="button" aria-label="Ajouter aux favoris">☆</button>
  {dm_carousel_nav_html}
  <div class="dm-hero-content">
    <div class="dm-hero-massif">⛷ {d['massif']}</div>
    <h1>🏔️ {d['name']}</h1>
    <p>{d['km_total']} km de pistes reliées · {len(d['stations'])} stations · {d['forfait_domaine']}€ le forfait domaine/jour</p>
    <div class="dm-rank">{rang_txt}</div>
  </div>
  {dm_hero_illu_note}
</div>

<div class="dm-wrap">

<div class="dm-breadcrumb">
  <a href="../index.html">Accueil</a> › <a href="../recherche.html">Stations de ski</a> › {d['name']}
</div>

{transfrontalier_badge}
{conditionnel_html}
{unifie_html}

<div class="dm-stats">
  <div class="dm-stat"><div class="dm-stat-val">{d['km_total']} km</div><div class="dm-stat-lbl">Pistes reliées</div></div>
  <div class="dm-stat"><div class="dm-stat-val">{d['remontees_total']}</div><div class="dm-stat-lbl">Remontées</div></div>
  <div class="dm-stat"><div class="dm-stat-val">{d['forfait_domaine']}€</div><div class="dm-stat-lbl">Forfait / jour</div></div>
  <div class="dm-stat"><div class="dm-stat-val">{d['alt_min']}-{d['alt_max']}m</div><div class="dm-stat-lbl">Altitude</div></div>
</div>

<div class="dm-section">
  <div class="dm-section-title">À propos du domaine</div>
  <div class="dm-card dm-desc">{d['desc']}</div>
</div>

<div class="dm-section">
  <div class="dm-section-title">Chiffres clés</div>
  <div class="dm-faits">{faits_html}</div>
</div>

{pistes_html}

{tableau_html}

<div class="dm-section">
  <div class="dm-section-title">Explorer les stations</div>
  <div class="dm-stations-grid">
    {stations_html}
  </div>
</div>

{autres_html}

<footer class="footer">
  <strong>SnowFinder</strong> — Le guide complet des stations de ski françaises<br>
  <a href="../index.html">Accueil</a> · <a href="../recherche.html">Recherche</a> · <a href="../comparateur.html">Comparateur</a> · <a href="../mentions-legales.html">Mentions légales</a><br>
  <span style="font-size:.7rem;opacity:.7">Données indicatives · Forfaits haute saison adulte · À vérifier sur le site officiel du domaine</span>
</footer>

</div>

<nav class="sf-bottomnav">
  <a href="../recherche.html" class="sf-bn-item" title="Trouver ma station">🔍</a>
  <a href="../enneigement.html" class="sf-bn-item" title="Météo &amp; enneigement">❄️</a>
  <a href="../index.html" class="sf-bn-item sf-bn-home" title="Accueil"><span class="sf-bn-home-circle">🏡</span></a>
  <a href="../tinder.html" class="sf-bn-item" title="Tinder du ski">💕</a>
  <a href="../hebergement.html" class="sf-bn-item" title="Hébergement">🛏️</a>
</nav>

<script>
// ── CARROUSEL HERO (photos du domaine) ──
var DM_HERO_URLS = {dm_carousel_urls_js};
var dmHeroIdx = 0, dmHeroAuto = null;
function dmHeroShow(i){{
  if(!DM_HERO_URLS.length) return;
  dmHeroIdx = (i + DM_HERO_URLS.length) % DM_HERO_URLS.length;
  document.querySelectorAll('.hero-slide').forEach(function(el){{
    el.classList.toggle('active', parseInt(el.dataset.idx) === dmHeroIdx);
  }});
  document.querySelectorAll('.hero-dot').forEach(function(el){{
    el.classList.toggle('active', parseInt(el.dataset.idx) === dmHeroIdx);
  }});
}}
function dmHeroNext(){{ dmHeroShow(dmHeroIdx + 1); dmResetHeroAuto(); }}
function dmHeroPrev(){{ dmHeroShow(dmHeroIdx - 1); dmResetHeroAuto(); }}
function dmHeroGoTo(i){{ dmHeroShow(i); dmResetHeroAuto(); }}
function dmResetHeroAuto(){{
  if(dmHeroAuto) clearInterval(dmHeroAuto);
  if(DM_HERO_URLS.length > 1) dmHeroAuto = setInterval(function(){{ dmHeroShow(dmHeroIdx + 1); }}, 5000);
}}
if(DM_HERO_URLS.length > 1) dmResetHeroAuto();
var dmHeroEl = document.querySelector('.dm-hero');
if(dmHeroEl && DM_HERO_URLS.length > 1){{
  dmHeroEl.addEventListener('mouseenter', function(){{ if(dmHeroAuto) clearInterval(dmHeroAuto); }});
  dmHeroEl.addEventListener('mouseleave', dmResetHeroAuto);
  var dsx = 0;
  dmHeroEl.addEventListener('touchstart', function(e){{ dsx = e.touches[0].clientX; }}, {{passive:true}});
  dmHeroEl.addEventListener('touchend', function(e){{
    var ddx = e.changedTouches[0].clientX - dsx;
    if(ddx > 50) dmHeroPrev(); else if(ddx < -50) dmHeroNext();
  }});
}}

// ── Favoris DOMAINES (clé séparée des favoris stations) ──
var DOM_SLUG = "{slug}";
function domFavs(){{
  try {{ return JSON.parse(localStorage.getItem('sf_fav_domaines') || '[]'); }}
  catch(e) {{ return []; }}
}}
function renderDomFav(){{
  var b = document.getElementById('dmFav');
  var on = domFavs().indexOf(DOM_SLUG) !== -1;
  b.textContent = on ? '⭐' : '☆';
  b.classList.toggle('active', on);
  b.title = on ? 'Retirer des favoris' : 'Ajouter aux favoris';
}}
document.getElementById('dmFav').addEventListener('click', function(){{
  var f = domFavs(), i = f.indexOf(DOM_SLUG);
  if (i === -1) f.push(DOM_SLUG); else f.splice(i, 1);
  try {{ localStorage.setItem('sf_fav_domaines', JSON.stringify(f)); }} catch(e) {{}}
  renderDomFav();
}});
renderDomFav();

// La croix revient à la page précédente (fiche station d'origine),
// avec repli sur la recherche si on est arrivé directement sur cette page.
document.getElementById('dmClose').addEventListener('click', function(e){{
  e.preventDefault();
  if (document.referrer && document.referrer.indexOf(location.host) !== -1 && history.length > 1) {{
    history.back();
  }} else {{
    location.href = '../recherche.html';
  }}
}});
</script>

</body>
</html>"""


def render_domaines_index():
    """Page racine listant les 19 grands domaines skiables reliés."""
    massifs = sorted({d['massif'] for d in DOMAINES.values()})
    filtres = "".join(
        f'<button class="di-f" data-m="{m}">{m}</button>' for m in massifs
    )
    cards = []
    for slug, d in sorted(DOMAINES.items(), key=lambda x: -x[1]['km_total']):
        membres = [x for x in DATA if x['name'] in d['stations']]
        chips = "".join(f'<span class="di-chip">{n}</span>' for n in d['stations'][:5])
        if len(d['stations']) > 5:
            chips += f'<span class="di-chip di-chip-more">+{len(d["stations"])-5}</span>'
        flags = ''
        if len(d['pays']) > 1:
            flags += f'<span class="di-flag">🌍 {" · ".join(d["pays"])}</span>'
        if d.get('conditionnel'):
            flags += '<span class="di-flag di-flag-warn">⚠️ Liaison selon enneigement</span>'
        score_badge = ''
        if membres:
            avg = sum(x["score"] for x in membres) / len(membres)
            score_badge = f'<span class="di-score-tag">⭐ {avg:.1f}</span>'

        # Photo de vignette : cascade domaine dédié -> stations membres -> placeholder
        dom_photos, _dom_src = get_domaine_photos_smart(slug, d)
        dom_thumb = dom_photos[0]
        illu_note = '<div class="di-illu-note">Photo d\'illustration</div>' if _dom_src == 'placeholder' else ''

        # Mini répartition des pistes (mêmes puces colorées que les vignettes stations)
        P = d.get('pistes')
        pistes_dots = ''
        if P and sum(P.values()) > 0:
            pistes_dots = f'''<div class="di-pistes">
        <span class="pd pd-v"><span class="pd-dot"></span>{P.get('v',0)}</span>
        <span class="pd pd-b"><span class="pd-dot"></span>{P.get('b',0)}</span>
        <span class="pd pd-r"><span class="pd-dot"></span>{P.get('r',0)}</span>
        <span class="pd pd-n"><span class="pd-dot"></span>{P.get('n',0)}</span>
      </div>'''

        cards.append(f'''<a href="domaines/{slug}.html" class="di-card" data-m="{d['massif']}">
      <div class="di-top" style="background-image:url('{dom_thumb}')">
        <div class="di-top-overlay"></div>
        <div class="di-massif-tag">⛷ {d['massif']}</div>
        <div class="di-km-tag">{d['km_total']} km</div>
        <div class="di-top-text">
          <div class="di-name">{d['name']}</div>
          <div class="di-region-inline">{len(d['stations'])} station{'s' if len(d['stations'])>1 else ''} reliées</div>
        </div>
        {illu_note}
      </div>
      <div class="di-body">
        <div class="di-stats">
          <span>🚡 {d['remontees_total']} remontées</span>
          <span>⛰ {d['alt_min']}-{d['alt_max']}m</span>
          {score_badge}
        </div>
        {pistes_dots}
        {f'<div class="di-flags">{flags}</div>' if flags else ''}
        <div class="di-chips">{chips}</div>
      </div>
      <div class="di-footer">
        <div><span class="di-price">{d['forfait_domaine']}€</span><span class="di-price-lbl">/jour</span></div>
        <div class="di-go">Voir le domaine →</div>
      </div>
    </a>''')
    cards_html = "\n".join(cards)
    total_km = sum(d['km_total'] for d in DOMAINES.values())
    total_st = len({s for d in DOMAINES.values() for s in d['stations']})

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Les grands domaines skiables reliés de France | SnowFinder</title>
<meta name="description" content="Les {len(DOMAINES)} grands domaines skiables reliés de France : Portes du Soleil, 3 Vallées, Paradiski, Grand Massif... Kilomètres de pistes, stations membres, forfaits et altitudes.">
<link rel="canonical" href="https://snowfinder.fr/domaines.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="SnowFinder">
<meta property="og:title" content="Les grands domaines skiables reliés de France">
<meta property="og:description" content="{len(DOMAINES)} domaines, {total_st} stations reliées. Comparez les kilomètres de pistes, forfaits et altitudes.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&family=DM+Serif+Display&display=swap" rel="stylesheet">
<style>
  :root{{--wood-pale:#f7efe2;--wood-light:#eddcbf;--wood:#c49a6c;--wood-dark:#8b5e3c;--blue:#5b9fd4;--blue-light:#e8f3fb;--blue-mid:#3a7db8;--blue-dark:#1a5a8a;--text:#2a1f14;--text-mid:#5c4a35;--text-light:#8a7060;--navy:#1a5a8a;--border:#e8d8c4;--bg:#f5f1ec}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{touch-action:pan-x pan-y;overflow-x:hidden;max-width:100%}}
  body{{font-family:"DM Sans",sans-serif;color:var(--text);background:linear-gradient(135deg,#e8f3fb 0%,#d0e7f5 50%,#e8f3fb 100%);background-attachment:fixed;min-height:100vh;padding-bottom:76px}}
  a{{color:inherit}}
  .di-hero{{background:linear-gradient(160deg,var(--blue-dark) 0%,var(--blue-mid) 50%,var(--blue) 100%);color:white;padding:40px 20px 32px;text-align:center;position:relative}}
  .di-hero h1{{font-family:"DM Serif Display",serif;font-size:2rem;margin-bottom:9px;line-height:1.15}}
  .di-hero p{{opacity:.88;font-size:.9rem;max-width:560px;margin:0 auto}}
  .di-close{{position:absolute;top:16px;right:16px;width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.35);color:white;font-size:1.05rem;display:flex;align-items:center;justify-content:center;text-decoration:none}}
  .di-tot{{display:flex;justify-content:center;gap:22px;margin-top:16px;flex-wrap:wrap}}
  .di-tot div{{text-align:center}}
  .di-tot b{{display:block;font-family:"DM Serif Display",serif;font-size:1.35rem}}
  .di-tot span{{font-size:.64rem;text-transform:uppercase;letter-spacing:.06em;opacity:.8}}
  .di-wrap{{max-width:1080px;margin:0 auto;padding:0 20px}}
  .di-filters{{display:flex;gap:8px;flex-wrap:wrap;padding:20px 0 6px}}
  .di-f{{padding:8px 15px;border-radius:20px;border:1.5px solid var(--border);background:white;
    font-family:"DM Sans",sans-serif;font-size:.8rem;font-weight:700;color:var(--text-mid);cursor:pointer;transition:all .15s}}
  .di-f:hover{{border-color:var(--blue-dark);color:var(--blue-dark)}}
  .di-f.on{{background:var(--blue-dark);border-color:var(--blue-dark);color:white}}
  .di-count{{font-size:.78rem;color:var(--text-mid);padding:6px 0 14px}}
  .di-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px;padding-bottom:30px}}
  /* CARTE — même structure que les vignettes stations (.card) */
  .di-card{{display:block;background:white;border-radius:16px;border:1px solid rgba(200,220,240,.6);overflow:hidden;
    text-decoration:none;box-shadow:0 4px 18px rgba(20,60,120,.10);transition:box-shadow .35s,transform .25s;position:relative}}
  .di-card:hover{{transform:translateY(-4px);box-shadow:0 12px 40px rgba(0,0,0,.15)}}
  .di-top{{height:190px;position:relative;display:flex;align-items:flex-end;padding:16px;background-size:cover;background-position:center}}
  .di-top-overlay{{position:absolute;inset:0;background:linear-gradient(to top,rgba(8,28,58,.82) 0%,rgba(10,30,60,.25) 50%,transparent 100%)}}
  .di-massif-tag{{position:absolute;top:11px;left:11px;background:rgba(0,0,0,.55);backdrop-filter:blur(6px);color:white;font-size:.62rem;font-weight:700;padding:3px 9px;border-radius:20px;text-transform:uppercase;letter-spacing:.05em;z-index:1}}
  .di-km-tag{{position:absolute;top:11px;right:11px;background:var(--wood);color:white;font-size:.78rem;font-weight:700;padding:3px 9px;border-radius:20px;z-index:1}}
  .di-top-text{{position:relative;z-index:1}}
  .di-name{{font-family:"DM Serif Display",serif;font-size:1.28rem;color:white;text-shadow:0 2px 10px rgba(0,0,0,.7);line-height:1.2;letter-spacing:-.01em}}
  .di-region-inline{{font-size:.7rem;color:rgba(255,255,255,.75);margin-top:2px}}
  .di-illu-note{{position:absolute;bottom:6px;right:11px;z-index:1;font-style:italic;font-size:.6rem;color:rgba(255,255,255,.5);text-shadow:0 1px 4px rgba(0,0,0,.6)}}
  .di-body{{padding:12px 15px 8px}}
  .di-stats{{display:flex;flex-wrap:wrap;align-items:center;gap:5px 12px;font-size:.78rem;color:var(--text-mid);margin-bottom:9px;font-weight:500}}
  .di-score-tag{{display:inline-flex;align-items:center;gap:4px;background:linear-gradient(135deg,#d4a017,#b8860b);color:white;border-radius:20px;padding:3px 10px;font-size:.72rem;font-weight:700;white-space:nowrap}}
  .di-pistes{{display:flex;gap:6px;align-items:center;margin-bottom:9px;flex-wrap:wrap}}
  .pd{{display:flex;align-items:center;gap:3px;background:var(--bg);border-radius:6px;padding:3px 7px;font-size:.72rem;font-weight:700}}
  .pd-dot{{width:9px;height:9px;border-radius:50%;flex-shrink:0}}
  .pd-v .pd-dot{{background:#2ea84e}}.pd-b .pd-dot{{background:#3a7db8}}.pd-r .pd-dot{{background:#cc2200}}.pd-n .pd-dot{{background:#222}}
  .pd-v{{color:#1a7a38}}.pd-b{{color:#1a4a8a}}.pd-r{{color:#aa1800}}.pd-n{{color:#111}}
  .di-flags{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:9px}}
  .di-flag{{font-size:.66rem;font-weight:700;background:var(--blue-light);color:var(--blue-dark);padding:3px 9px;border-radius:20px}}
  .di-flag-warn{{background:#fff4e6;color:#a05a2c}}
  .di-chips{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:2px}}
  .di-chip{{font-size:.68rem;font-weight:600;background:var(--wood-pale);color:var(--wood-dark)}}
  .di-chip{{padding:3px 9px;border-radius:20px}}
  .di-chip-more{{background:var(--blue-dark);color:white;font-weight:800}}
  .di-footer{{padding:10px 15px 13px;border-top:1px solid rgba(200,220,240,.5);display:flex;align-items:center;justify-content:space-between;background:linear-gradient(135deg,#f0f7ff,#f8f9ff)}}
  .di-price{{font-family:"DM Serif Display",serif;font-size:1.15rem;color:var(--blue-mid)}}
  .di-price-lbl{{font-size:.7rem;color:var(--text-light);margin-left:3px}}
  .di-go{{font-size:.78rem;font-weight:800;color:var(--blue-dark)}}
  .di-empty{{text-align:center;padding:40px 20px;color:var(--text-mid);font-size:.9rem}}
  .footer{{text-align:center;padding:26px 20px 20px;font-size:.8rem;color:var(--text-mid)}}
  .footer a{{color:var(--blue-dark);text-decoration:none;font-weight:600}}
  .sf-bottomnav{{position:fixed;bottom:0;left:0;right:0;background:white;display:flex;justify-content:space-around;align-items:center;padding:8px 0;box-shadow:0 -2px 10px rgba(0,0,0,.08);z-index:80}}
  .sf-bn-item{{text-decoration:none;font-size:1.3rem;padding:6px 10px}}
  .sf-bn-home-circle{{background:var(--blue-dark);color:white;border-radius:50%;width:42px;height:42px;display:flex;align-items:center;justify-content:center;font-size:1.2rem}}
</style>
</head>
<body>

<div class="di-hero">
  <a href="recherche.html" class="di-close" aria-label="Retour">✕</a>
  <h1>🏔️ Les grands domaines reliés</h1>
  <p>Plusieurs stations connectées skis aux pieds, sous un seul forfait. Le vrai critère quand on cherche du grand ski.</p>
  <div class="di-tot">
    <div><b>{len(DOMAINES)}</b><span>domaines</span></div>
    <div><b>{total_st}</b><span>stations reliées</span></div>
    <div><b>{total_km}</b><span>km cumulés</span></div>
  </div>
</div>

<div class="di-wrap">
  <div class="di-filters">
    <button class="di-f on" data-m="">Tous</button>
    {filtres}
  </div>
  <div class="di-count" id="diCount"></div>
  <div class="di-grid" id="diGrid">
    {cards_html}
  </div>
  <div class="di-empty" id="diEmpty" style="display:none">Aucun domaine dans ce massif.</div>
</div>

<footer class="footer">
  <strong>SnowFinder</strong> — Le guide complet des stations de ski françaises<br>
  <a href="index.html">Accueil</a> · <a href="recherche.html">Recherche</a> · <a href="comparateur.html">Comparateur</a> · <a href="mentions-legales.html">Mentions légales</a><br>
  <span style="font-size:.7rem;opacity:.7">Données indicatives · Forfaits haute saison adulte · À vérifier sur le site officiel du domaine</span>
</footer>

<nav class="sf-bottomnav">
  <a href="recherche.html" class="sf-bn-item" title="Trouver ma station">🔍</a>
  <a href="enneigement.html" class="sf-bn-item" title="Météo &amp; enneigement">❄️</a>
  <a href="index.html" class="sf-bn-item sf-bn-home" title="Accueil"><span class="sf-bn-home-circle">🏡</span></a>
  <a href="tinder.html" class="sf-bn-item" title="Tinder du ski">💕</a>
  <a href="hebergement.html" class="sf-bn-item" title="Hébergement">🛏️</a>
</nav>

<script>
(function(){{
  var cards = [].slice.call(document.querySelectorAll('.di-card'));
  var btns  = [].slice.call(document.querySelectorAll('.di-f'));
  var count = document.getElementById('diCount');
  var empty = document.getElementById('diEmpty');
  function apply(m){{
    var n = 0;
    cards.forEach(function(c){{
      var ok = !m || c.dataset.m === m;
      c.style.display = ok ? '' : 'none';
      if (ok) n++;
    }});
    count.textContent = n + (n > 1 ? ' domaines' : ' domaine');
    empty.style.display = n ? 'none' : 'block';
  }}
  btns.forEach(function(b){{
    b.addEventListener('click', function(){{
      btns.forEach(function(x){{ x.classList.remove('on'); }});
      b.classList.add('on');
      apply(b.dataset.m);
    }});
  }});
  apply('');
}})();
</script>

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

# Générer les fiches domaines
domaines_dir = os.path.join(root_dir, 'domaines')
os.makedirs(domaines_dir, exist_ok=True)
dcount = 0
derrors = []
for dslug, d in DOMAINES.items():
    try:
        dhtml = render_domaine_page(dslug, d)
        with open(os.path.join(domaines_dir, f'{dslug}.html'), 'w', encoding='utf-8') as f:
            f.write(dhtml)
        dcount += 1
    except Exception as e:
        derrors.append(f"{dslug}: {e}")

print(f"✓ {dcount}/{len(DOMAINES)} fiches domaines générées dans domaines/")
if derrors:
    print("Erreurs domaines:", derrors)
if errors:
    print("Erreurs:", errors)

# Générer la page index des domaines
try:
    with open(os.path.join(root_dir, 'domaines.html'), 'w', encoding='utf-8') as f:
        f.write(render_domaines_index())
    print("✓ domaines.html généré à la racine")
except Exception as e:
    print("Erreur domaines.html :", e)
