#!/usr/bin/env python3
"""
SnowFinder — Notifications push automatiques.
3 types : alerte neige / vacances scolaires / enneigement top du moment.
"""
import os, json, urllib.request, urllib.parse, unicodedata, re, random
from datetime import date, timedelta

ONESIGNAL_APP_ID  = os.environ['ONESIGNAL_APP_ID']
ONESIGNAL_API_KEY = os.environ['ONESIGNAL_API_KEY']

# ─── STATIONS ────────────────────────────────────────────────────────────────
STATIONS = [
    {"id":1,  "name":"Val d'Isère",       "massif":"Alpes du Nord", "lat":45.448,"lon":6.969},
    {"id":2,  "name":"Tignes",            "massif":"Alpes du Nord", "lat":45.469,"lon":6.908},
    {"id":3,  "name":"Les Arcs",          "massif":"Alpes du Nord", "lat":45.574,"lon":6.781},
    {"id":4,  "name":"La Plagne",         "massif":"Alpes du Nord", "lat":45.510,"lon":6.676},
    {"id":5,  "name":"Chamonix",          "massif":"Alpes du Nord", "lat":45.924,"lon":6.870},
    {"id":6,  "name":"Avoriaz",           "massif":"Alpes du Nord", "lat":46.193,"lon":6.762},
    {"id":7,  "name":"Courchevel",        "massif":"Alpes du Nord", "lat":45.416,"lon":6.634},
    {"id":8,  "name":"Méribel",           "massif":"Alpes du Nord", "lat":45.393,"lon":6.564},
    {"id":9,  "name":"Val Thorens",       "massif":"Alpes du Nord", "lat":45.298,"lon":6.582},
    {"id":10, "name":"Les Menuires",      "massif":"Alpes du Nord", "lat":45.319,"lon":6.537},
    {"id":14, "name":"Megève",            "massif":"Alpes du Nord", "lat":45.856,"lon":6.617},
    {"id":19, "name":"Morzine",           "massif":"Alpes du Nord", "lat":46.178,"lon":6.707},
    {"id":20, "name":"Les Gets",          "massif":"Alpes du Nord", "lat":46.161,"lon":6.667},
    {"id":21, "name":"Châtel",            "massif":"Alpes du Nord", "lat":46.271,"lon":6.836},
    {"id":28, "name":"Flaine",            "massif":"Alpes du Nord", "lat":46.002,"lon":6.676},
    {"id":33, "name":"La Clusaz",         "massif":"Alpes du Nord", "lat":45.906,"lon":6.430},
    {"id":40, "name":"Les Saisies",       "massif":"Alpes du Nord", "lat":45.749,"lon":6.527},
    {"id":56, "name":"Valloire",          "massif":"Alpes du Nord", "lat":45.170,"lon":6.432},
    {"id":58, "name":"Val Cenis",         "massif":"Alpes du Nord", "lat":45.198,"lon":6.930},
    {"id":70, "name":"Chamrousse",        "massif":"Alpes du Nord", "lat":45.119,"lon":5.880},
    {"id":72, "name":"Alpe d'Huez",       "massif":"Alpes du Nord", "lat":45.090,"lon":6.070},
    {"id":73, "name":"Les Deux Alpes",    "massif":"Alpes du Nord", "lat":45.016,"lon":6.120},
    {"id":89, "name":"Serre Chevalier",   "massif":"Alpes du Sud",  "lat":44.920,"lon":6.497},
    {"id":90, "name":"Montgenèvre",       "massif":"Alpes du Sud",  "lat":44.932,"lon":6.720},
    {"id":91, "name":"Vars",              "massif":"Alpes du Sud",  "lat":44.584,"lon":6.693},
    {"id":95, "name":"Orcières-Merlette", "massif":"Alpes du Sud",  "lat":44.683,"lon":6.322},
    {"id":104,"name":"Pra-Loup",          "massif":"Alpes du Sud",  "lat":44.348,"lon":6.599},
    {"id":110,"name":"Isola 2000",        "massif":"Alpes du Sud",  "lat":44.191,"lon":7.167},
    {"id":123,"name":"Saint-Lary-Soulan", "massif":"Pyrénées",      "lat":42.826,"lon":0.328},
    {"id":126,"name":"Cauterets",         "massif":"Pyrénées",      "lat":42.889,"lon":-0.095},
    {"id":156,"name":"Gérardmer",         "massif":"Vosges",        "lat":48.071,"lon":6.884},
    {"id":173,"name":"Les Rousses",       "massif":"Jura",          "lat":46.500,"lon":5.993},
    {"id":182,"name":"Super Besse",       "massif":"Massif Central","lat":45.499,"lon":2.840},
    {"id":183,"name":"Le Mont Dore",      "massif":"Massif Central","lat":45.574,"lon":2.820},
]

# ─── MESSAGES ALERTE NEIGE ───────────────────────────────────────────────────
MSG_NEIGE = [
    ("{snow}cm attendus à {name} ! Allez feu, on part maintenant ? 🔥",
     "❄️ {snow}cm à {name} — et t'es encore au chaud chez toi ?"),

    ("Poudreuse incoming à {name} ❄️ {snow}cm prévus. T'as encore tes skis sortis ?",
     "Alerte météo sérieuse : {snow}cm à {name}. Tes carres sont prêtes ?"),

    ("{snow}cm à {name} dans les prochains jours. Ton forfait va pas se payer tout seul 👀",
     "Petit rappel : {snow}cm de fraîche attendus à {name}. Tu fais quoi ce week-end ?"),

    ("Météo validée ✅ {snow}cm de fraîche à {name}. C'est maintenant ou jamais !",
     "La montagne a parlé : {snow}cm à {name}. On écoute ou pas ?"),

    ("Alerte poudreuse ⚠️ {snow}cm à {name}. Quelqu'un prévient les collègues ou on se barre discrètement ?",
     "{snow}cm prévus à {name} 🏔️ On dit juste..."),

    ("{snow}cm de neige fraîche à {name}. La montagne t'appelle. T'as le droit de ne pas décrocher mais quand même 🎿",
     "Breaking news : {snow}cm à {name} 📰 On arrête tout ?"),

    ("Hey ! {snow}cm annoncés à {name}. Petit rappel : tes skis sont au fond du garage 🎿",
     "{snow}cm à {name} ce week-end. C'est le genre d'info qui fait changer les plans 👀"),

    ("La météo a décidé : {snow}cm à {name}. Et toi t'as décidé quoi ? ⛷️",
     "{snow}cm de fraîche à {name} 🌨️ Honnêtement, t'attends quoi ?"),

    ("Info importante : {snow}cm à {name}. Info encore plus importante : ça se réserve vite ⏱️",
     "Neige fraîche chez {name} : {snow}cm. C'est le moment ou jamais 🎿"),

    ("{snow}cm ici, {snow}cm là... {name} va être incroyable 🏔️",
     "On a vérifié la météo pour toi : {snow}cm à {name}. De rien 😌"),

    ("T'as vu ? {snow}cm prévus à {name} ! On te laisse organiser le covoiturage 🚗",
     "{snow}cm à {name}. Les excuses du style 'il fait pas assez de neige' ça marche plus 😄"),

    ("Fraîche garantie à {name} : {snow}cm dans les prochains jours ❄️ Conditions parfaites !",
     "{name} va se blanchir sérieusement : {snow}cm prévus. Spoiler : c'est beau 🏔️"),

    ("Le genre de news qui font sourire : {snow}cm à {name} cette semaine ⛷️",
     "{snow}cm annoncés à {name}. La montagne n'attend pas, toi si ? 🎿"),

    ("Enneigement en vue à {name} 🌨️ {snow}cm prévus. Conditions qui s'annoncent superbes !",
     "Chute de neige à {name} ! {snow}cm attendus. Tes carres ont soif ❄️"),

    ("On a les yeux rivés sur la météo pour toi : {snow}cm à {name} 👀 C'est du sérieux !",
     "{snow}cm de poudreuse en vue à {name}. Ce week-end, les pistes ont l'air d'accord 🎿"),
]

# ─── MESSAGES VACANCES SCOLAIRES ─────────────────────────────────────────────
MSG_VACANCES = [
    ("Dans {days} jours c'est les vacances ! Les hébergements montagne se remplissent déjà 🎿",
     "Les vacances arrivent dans {days} jours. Ta station idéale t'attend 🏔️"),

    ("J-{days} avant les vacances ⛷️ T'as pensé à la montagne dans tout ça ?",
     "Rappel amical : dans {days} jours c'est les vacances. Les prix, eux, n'attendent pas 😅"),

    ("Soyons honnêtes : dans {days} jours t'aurais pu être sur les pistes 🎿 C'est encore jouable !",
     "Dans {days} jours les pistes t'attendent. Les bons hébergements aussi... pour l'instant 👀"),

    ("Vacances dans {days} jours 🎉 Les stations de ski font de l'œil. Et toi ?",
     "J-{days} ⏳ Après c'est les vacances. Ta station idéale est à 2 clics sur SnowFinder"),

    ("T'as {days} jours pour décider où tu pars au ski. On peut t'aider 😉 🎿",
     "Dans {days} jours c'est les vacances ! Montagne ou pas montagne ? (mauvaise question) 🏔️"),

    ("Tic tac ⏰ Dans {days} jours c'est les vacances. Les pistes de ski n'attendent que toi !",
     "Breaking : dans {days} jours les vacances commencent 🎉 Ta station préférée est prête ?"),

    ("Les vacances approchent dans {days} jours ! Toujours pas de station choisie ? On s'en occupe 🎿",
     "Plus que {days} jours avant les vacances. La montagne : 2400m d'arguments pour y aller ❄️"),
]

# ─── MESSAGES ENNEIGEMENT TOP ─────────────────────────────────────────────────
MSG_ENNEI = [
    ("L'enneigement est au top en ce moment ! C'est le genre de conditions qui font des regrets ⛷️",
     "Conditions parfaites dans les {massif} ❄️ Quelqu'un a dit poudreuse ?"),

    ("Snowreport : les {massif} sont dans leur meilleure forme de la saison 🏔️ Pour info...",
     "Bonne nouvelle du jour : conditions excellentes sur les pistes en ce moment 🎿"),

    ("La montagne est belle en ce moment. Vraiment belle. C'est tout ce qu'on voulait dire 🏔️",
     "Conditions top, météo validée, pistes ouvertes. Il manque juste toi ⛷️"),

    ("On a regardé les conditions ce matin dans les {massif}... et on pense fort à toi 🎿",
     "Si t'attendais le bon moment pour partir au ski, c'est maintenant ❄️"),

    ("Honnêtement, les conditions sont vraiment bonnes en ce moment. On dit ça, on dit rien 😌🎿",
     "Beau soleil + pistes bien enneigées dans les {massif}. Tout ce qu'on aime ☀️❄️"),

    ("Les pistes des {massif} sont au top cette semaine. Tes skis méritent mieux que le garage 🎿",
     "Enneigement au beau fixe dans les {massif} ! C'est maintenant qu'il faut y aller 🏔️"),

    ("Cette semaine dans les {massif} : pistes en parfait état, enneigement généreux ❄️ On valide.",
     "Conditions quasi parfaites dans les {massif} en ce moment. Juste parfaites. Voilà 🎿"),
]

def slugify(name):
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', name.lower())).strip('-')

def get_snow(lat, lon):
    url = (f"https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}"
           f"&daily=snowfall_sum&forecast_days=5&timezone=Europe/Paris")
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    vals = [v or 0 for v in data["daily"]["snowfall_sum"]]
    return round(max(vals))

def send_notif(title, body, url, topic):
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["All"],
        "headings": {"fr": title, "en": title},
        "contents": {"fr": body, "en": body},
        "url": url,
        "chrome_web_icon": "https://snowfinder.fr/logo.png",
        "web_push_topic": topic,
    }
    req = urllib.request.Request(
        "https://onesignal.com/api/v1/notifications",
        data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json",
                 "Authorization":f"Basic {ONESIGNAL_API_KEY}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
    return resp.get("recipients", 0)

# ─── VACANCES SCOLAIRES 2025-2026 (Zone B — majoritaire) ─────────────────────
VACANCES = [
    ("Noël 2025",    date(2025, 12, 20), date(2026,  1,  4)),
    ("Hiver 2026",   date(2026,  2,  7), date(2026,  2, 22)),
    ("Printemps 2026", date(2026, 4, 11), date(2026, 4, 26)),
    ("Noël 2026",    date(2026, 12, 19), date(2027,  1,  3)),
]
PREVENANCE_JOURS = [21, 14, 7]  # Envoyer J-21, J-14 et J-7

def check_vacances():
    today = date.today()
    for nom, debut, fin in VACANCES:
        for j in PREVENANCE_JOURS:
            if today == debut - timedelta(days=j):
                return nom, j
    return None, None

def check_enneigement_top(resultats):
    """Retourne True si 3+ stations ont >50cm prévus."""
    return sum(1 for r in resultats if r["snow"] >= 50) >= 3

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("=== SnowFinder — Notifications push ===")
    today = date.today()
    month = today.month
    en_saison = month in [11, 12, 1, 2, 3, 4]

    # 1. VACANCES SCOLAIRES (toute l'année, J-21/14/7)
    nom_vac, days = check_vacances()
    if nom_vac:
        print(f"\n📅 Vacances {nom_vac} dans {days} jours !")
        titre, corps = random.choice(MSG_VACANCES)
        titre = titre.format(days=days)
        corps = corps.format(days=days)
        n = send_notif(titre, corps, "https://snowfinder.fr/recherche.html", "vacances")
        print(f"✅ Notification vacances envoyée → {n} abonné(s)")

    # Hors saison : on s'arrête là
    if not en_saison:
        print(f"\nMois {month} — hors saison, pas de vérification neige.")
        return

    # 2. VÉRIFICATION NEIGE
    print("\n❄️ Vérification enneigement...")
    resultats = []
    for s in STATIONS:
        try:
            snow = get_snow(s["lat"], s["lon"])
            print(f"  {s['name']:25} → {snow}cm")
            resultats.append({"station": s, "snow": snow})
        except Exception as e:
            print(f"  ⚠️  {s['name']}: {e}")

    # 3. ALERTE NEIGE (station avec le plus de neige > 15cm)
    top_neige = sorted([r for r in resultats if r["snow"] >= 15],
                       key=lambda x: x["snow"], reverse=True)
    if top_neige:
        best = top_neige[0]
        name = best["station"]["name"]
        snow = best["snow"]
        slug = slugify(name)
        titre, corps = random.choice(MSG_NEIGE)
        titre = titre.format(snow=snow, name=name)
        corps = corps.format(snow=snow, name=name)
        print(f"\n🚨 Alerte neige : {name} → {snow}cm")
        n = send_notif(titre, corps,
                       f"https://snowfinder.fr/stations/{slug}.html",
                       "snow_alert")
        print(f"✅ Notification neige envoyée → {n} abonné(s)")
    else:
        print("\nAucune chute significative — pas d'alerte neige.")

    # 4. ENNEIGEMENT TOP (si 3+ stations ont >50cm)
    if check_enneigement_top(resultats):
        massifs_top = list({r["station"]["massif"] for r in resultats if r["snow"] >= 50})
        massif_str = " & ".join(massifs_top[:2])
        titre, corps = random.choice(MSG_ENNEI)
        titre = titre.format(massif=massif_str)
        corps = corps.format(massif=massif_str)
        print(f"\n🏔️ Enneigement top : {massif_str}")
        n = send_notif(titre, corps,
                       "https://snowfinder.fr/enneigement.html",
                       "enneigement_top")
        print(f"✅ Notification enneigement envoyée → {n} abonné(s)")

    print("\n=== Terminé ===")

if __name__ == "__main__":
    main()
