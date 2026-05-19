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

def get_station_photos(slug):
    """Détecte toutes les photos uploadées pour une station.
    Pattern : {slug}1.jpg, {slug}2.jpg, {slug}3.jpg, ... (jusqu'au premier trou, max 20).
    Supporte .jpg, .jpeg, .png, .webp.
    Retourne une liste de chemins relatifs ('../img/...') ou liste vide."""
    photos = []
    for i in range(1, 21):
        found = None
        for ext in ('jpg', 'jpeg', 'png', 'webp', 'JPG', 'JPEG', 'PNG', 'WEBP'):
            p = os.path.join(root_dir, 'img', f'{slug}{i}.{ext}')
            if os.path.exists(p):
                found = f'../img/{slug}{i}.{ext}'
                break
        if not found:
            break  # stop au premier trou
        photos.append(found)
    return photos

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
    # Détection automatique de toutes les photos uploadées : slug1.jpg, slug2.jpg, ...
    all_photos = get_station_photos(slug)
    if all_photos:
        photo = all_photos[0]  # photo 1 = hero
    else:
        photo = s.get('photo') or 'https://images.unsplash.com/photo-1551524559-8af4e6624178?w=1200&q=80'
    # Photo 2 (utilisée dans "Notre avis" comme aujourd'hui)
    photo_station = all_photos[1] if len(all_photos) >= 2 else None
    # Photos supplémentaires (3, 4, 5, ...) pour la galerie
    extra_photos = all_photos[2:] if len(all_photos) >= 3 else []
    if extra_photos:
        gallery_items = "\n".join(
            f'        <div class="photo-gallery-item" data-idx="{i}" onclick="openLightbox({i})"><img src="{p}" alt="{s["name"]} photo {i+1}" loading="lazy"></div>'
            for i, p in enumerate(extra_photos)
        )
        # JS array des chemins pour le lightbox
        gallery_urls_js = "[" + ",".join(f'"{p}"' for p in extra_photos) + "]"
        gallery_html = f'''
      <!-- GALERIE PHOTOS -->
      <div class="section">
        <div class="section-title">📷 La station en images</div>
        <div class="photo-gallery">
{gallery_items}
        </div>
      </div>'''
    else:
        gallery_html = ''
        gallery_urls_js = "[]"
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
  <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
  <script>
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(async function(OneSignal) {{
      await OneSignal.init({{
        appId: "9530c745-8578-41e9-ad9f-2fa5348ad0b8",
        safari_web_id: "web.onesignal.auto.5c6acdd7-2576-4d7e-9cb0-efba7bf8602e",
        serviceWorkerPath: "../sw.js",
        notifyButton: {{ enable: true }},
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
    body{{font-family:"DM Sans",sans-serif;color:var(--text);background:linear-gradient(135deg,#e8f3fb 0%,#d0e7f5 50%,#e8f3fb 100%);background-attachment:fixed;min-height:100vh;position:relative}}
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
    .main-grid{{display:grid;grid-template-columns:1fr 340px;gap:16px;align-items:start}}
    @media(max-width:800px){{.main-grid{{grid-template-columns:1fr}}}}

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
    .fav-star.active{{background:#ffd451;border-color:#d49b00;color:#5c3d00;}}

    /* BOUTON FAVORIS SECONDAIRE (dans le corps de la page) */
    .fav-cta{{
      display:flex;align-items:center;gap:14px;background:linear-gradient(135deg,#fff8e1 0%,#ffecb3 100%);
      border:2px solid #ffd451;border-radius:14px;padding:14px 18px;margin:18px 0;cursor:pointer;
      transition:all .2s;font-family:"DM Sans",sans-serif;width:100%;text-align:left
    }}
    .fav-cta:hover{{background:linear-gradient(135deg,#ffecb3 0%,#ffd451 100%);transform:translateY(-1px);box-shadow:0 6px 18px rgba(255,180,0,.25)}}
    .fav-cta.active{{background:linear-gradient(135deg,#ffd451 0%,#ffb900 100%);border-color:#d49b00}}
    .fav-cta-icon{{font-size:2rem;flex-shrink:0}}
    .fav-cta-txt{{flex:1}}
    .fav-cta-title{{font-weight:800;color:#5c3d00;font-size:1rem;margin-bottom:2px}}
    .fav-cta-sub{{font-size:.78rem;color:#7a5500;line-height:1.4}}

    /* FOOTER */
    .mobile-bar{{
      display:none;position:fixed;bottom:0;left:0;right:0;
      background:white;border-top:1.5px solid var(--wood-light);
      padding:10px 14px 18px;gap:10px;z-index:80;
      box-shadow:0 -4px 20px rgba(0,0,0,.1)
    }}
    @media(max-width:800px){{
      .mobile-bar{{display:flex}}
      body{{padding-bottom:80px}}
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
      width:100%;border:none;border-radius:var(--radius);
      padding:0;cursor:pointer;overflow:hidden;
      margin-bottom:16px;position:relative;
      box-shadow:0 4px 20px rgba(0,0,0,.25);
      display:block;min-height:110px;
      transition:transform .15s,box-shadow .15s
    }}
    .official-btn:hover{{transform:translateY(-2px);box-shadow:0 8px 28px rgba(0,0,0,.3)}}
    .official-btn-bg{{
      position:absolute;inset:0;
      background-image:url('https://images.unsplash.com/photo-1491555103944-7c647fd857e6?w=800&q=80');
      background-size:cover;background-position:center;
    }}
    .official-btn-bg::after{{
      content:'';position:absolute;inset:0;
      background:linear-gradient(135deg,rgba(26,90,138,.88) 0%,rgba(196,154,108,.75) 100%);
    }}
    .official-btn-content{{
      position:relative;z-index:1;padding:20px 18px;
      text-align:left;color:white;
    }}

    /* FOOTER */
    .footer{{background:var(--blue-dark);color:rgba(255,255,255,.65);text-align:center;padding:26px 20px;font-size:.78rem;margin-top:40px;line-height:1.8}}
    .footer a{{color:rgba(255,255,255,.85);font-weight:600}}
    .footer a:hover{{color:white}}
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
  <button class="fav-star" id="favBtn" onclick="toggleFav()" title="Ajouter aux favoris">☆</button>
  <div class="hero-content">
    <div class="hero-massif">⛷ {s['massif']}</div>
    <h1>{s['name']}</h1>
    <div class="hero-region">📍 {s['region']}</div>
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
  var btn2=document.getElementById('favBtn2');
  if(isFav){{
    if(btn){{btn.textContent='⭐';btn.classList.add('active');btn.title='Retirer des favoris';}}
    if(btn2){{btn2.classList.add('active');btn2.querySelector('.fav-cta-title').textContent='⭐ Dans tes favoris';btn2.querySelector('.fav-cta-sub').textContent='Clique pour retirer';}}
  }}else{{
    if(btn){{btn.textContent='☆';btn.classList.remove('active');btn.title='Ajouter aux favoris';}}
    if(btn2){{btn2.classList.remove('active');btn2.querySelector('.fav-cta-title').textContent='☆ Ajouter aux favoris';btn2.querySelector('.fav-cta-sub').textContent='Garde un œil sur cette station — neige, prix, dispos';}}
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
    }}
    if(d.daily&&d.daily.time){{
      var g=document.getElementById('meteoGrid');
      var h='';
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
    }}
  }}).catch(function(){{
    var ld=document.getElementById('meteoLoading');
    if(ld) ld.textContent='Météo momentanément indisponible';
  }});
}})();
</script>

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

  <!-- BOUTON FAVORI BIEN VISIBLE -->
  <button class="fav-cta" id="favBtn2" onclick="toggleFav()" type="button">
    <span class="fav-cta-icon">☆</span>
    <div class="fav-cta-txt">
      <div class="fav-cta-title">☆ Ajouter aux favoris</div>
      <div class="fav-cta-sub">Garde un œil sur cette station — neige, prix, dispos</div>
    </div>
  </button>

  <div class="main-grid">

    <!-- COLONNE PRINCIPALE -->
    <div>

      <!-- MÉTÉO LIVE -->
      <div class="meteo-widget" id="meteoWidget">
        <div class="meteo-head">
          <div>
            <div class="meteo-title">❄️ Météo à {s['name']}</div>
            <div class="meteo-sub">Conditions actuelles & prévisions 5 jours</div>
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

      <!-- NOTRE AVIS -->
      <div class="section" style="border-left:4px solid var(--blue-mid);background:linear-gradient(135deg,var(--white) 0%,var(--blue-light) 100%)">
        <div class="section-title" style="color:var(--blue-dark)">✍️ Notre avis sur {s['name']}</div>
        <p style="font-size:.97rem;line-height:1.85;color:var(--text-mid);font-style:italic">{verdict}</p>
      </div>
{gallery_html}

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

      <!-- SITE OFFICIEL (avec interstitiel) -->
      <button onclick="showOfficialSheet()" class="official-btn">
        <div class="official-btn-bg"></div>
        <div class="official-btn-content">
          <div style="font-size:2rem;margin-bottom:6px">🏔️</div>
          <div style="font-size:1.1rem;font-weight:900;letter-spacing:-.01em;margin-bottom:5px">Webcams · Plan des pistes · Infos officielles</div>
          <div style="font-size:.95rem;font-weight:700;opacity:.9">Site officiel de {s['name']} → C'est par ici</div>
        </div>
      </button>

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
