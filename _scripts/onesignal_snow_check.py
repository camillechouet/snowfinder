#!/usr/bin/env python3
"""
SnowFinder — Alerte neige quotidienne à 18h.
Trouve les meilleures chutes prévues et envoie une notif à tous les abonnés.
"""
import os, json, urllib.request, urllib.parse, unicodedata, re

ONESIGNAL_APP_ID  = os.environ['ONESIGNAL_APP_ID']
ONESIGNAL_API_KEY = os.environ['ONESIGNAL_API_KEY']

STATIONS = [
    {"id": 1,  "name": "Val d'Isère",       "lat": 45.448, "lon": 6.969},
    {"id": 2,  "name": "Tignes",            "lat": 45.469, "lon": 6.908},
    {"id": 3,  "name": "Les Arcs",          "lat": 45.574, "lon": 6.781},
    {"id": 4,  "name": "La Plagne",         "lat": 45.510, "lon": 6.676},
    {"id": 5,  "name": "Chamonix",          "lat": 45.924, "lon": 6.870},
    {"id": 6,  "name": "Avoriaz",           "lat": 46.193, "lon": 6.762},
    {"id": 7,  "name": "Courchevel",        "lat": 45.416, "lon": 6.634},
    {"id": 8,  "name": "Méribel",           "lat": 45.393, "lon": 6.564},
    {"id": 9,  "name": "Val Thorens",       "lat": 45.298, "lon": 6.582},
    {"id": 10, "name": "Les Menuires",      "lat": 45.319, "lon": 6.537},
    {"id": 14, "name": "Megève",            "lat": 45.856, "lon": 6.617},
    {"id": 19, "name": "Morzine",           "lat": 46.178, "lon": 6.707},
    {"id": 20, "name": "Les Gets",          "lat": 46.161, "lon": 6.667},
    {"id": 21, "name": "Châtel",            "lat": 46.271, "lon": 6.836},
    {"id": 28, "name": "Flaine",            "lat": 46.002, "lon": 6.676},
    {"id": 33, "name": "La Clusaz",         "lat": 45.906, "lon": 6.430},
    {"id": 40, "name": "Les Saisies",       "lat": 45.749, "lon": 6.527},
    {"id": 56, "name": "Valloire",          "lat": 45.170, "lon": 6.432},
    {"id": 58, "name": "Val Cenis",         "lat": 45.198, "lon": 6.930},
    {"id": 70, "name": "Chamrousse",        "lat": 45.119, "lon": 5.880},
    {"id": 72, "name": "Alpe d'Huez",       "lat": 45.090, "lon": 6.070},
    {"id": 73, "name": "Les Deux Alpes",    "lat": 45.016, "lon": 6.120},
    {"id": 89, "name": "Serre Chevalier",   "lat": 44.920, "lon": 6.497},
    {"id": 90, "name": "Montgenèvre",       "lat": 44.932, "lon": 6.720},
    {"id": 91, "name": "Vars",              "lat": 44.584, "lon": 6.693},
    {"id": 95, "name": "Orcières-Merlette", "lat": 44.683, "lon": 6.322},
    {"id": 104,"name": "Pra-Loup",          "lat": 44.348, "lon": 6.599},
    {"id": 110,"name": "Isola 2000",        "lat": 44.191, "lon": 7.167},
    {"id": 123,"name": "Saint-Lary-Soulan", "lat": 42.826, "lon": 0.328},
    {"id": 126,"name": "Cauterets",         "lat": 42.889, "lon": -0.095},
    {"id": 156,"name": "Gérardmer",         "lat": 48.071, "lon": 6.884},
    {"id": 173,"name": "Les Rousses",       "lat": 46.500, "lon": 5.993},
    {"id": 182,"name": "Super Besse",       "lat": 45.499, "lon": 2.840},
    {"id": 183,"name": "Le Mont Dore",      "lat": 45.574, "lon": 2.820},
]

# Messages par station
MESSAGES_STATION = [
    "{snow}cm de fraîche attendus à {name} ! Est-ce que ta station favorite en profite aussi ?",
    "❄️ {snow}cm annoncés à {name} dans les prochains jours. Ta prochaine session se prépare !",
    "Poudreuse en vue à {name} ! {snow}cm prévus. Et chez toi, ça donne quoi ?",
    "{snow}cm de neige fraîche à {name}. Les conditions s'annoncent superbes !",
    "⛷ {name} va se poudrer : {snow}cm attendus. Tu regardes ta station ?",
    "Il va neiger à {name} ! {snow}cm prévus dans les 5 prochains jours.",
    "{snow}cm à {name}... La montagne se réveille. Et ta station favorite ?",
    "Alerte fraîche ❄️ {snow}cm prévus à {name}. Conditions à surveiller !",
]

# Messages par massif (quand plusieurs stations d'un même massif sont enneigées)
MESSAGES_MASSIF = {
    "Alpes du Nord": [
        "Encore de la fraîche dans les Alpes du Nord ! {snow}cm prévus à {name}.",
        "Les Alpes du Nord se couvrent de blanc ❄️ {snow}cm attendus à {name}.",
        "Chute de neige en vue dans les Alpes du Nord — {snow}cm à {name}.",
    ],
    "Alpes du Sud": [
        "Les Alpes du Sud ne sont pas en reste : {snow}cm prévus à {name} !",
        "Fraîche dans le sud ❄️ {snow}cm attendus à {name}.",
    ],
    "Pyrénées": [
        "Encore quelques flocons au-dessus de 1800m dans les Pyrénées ! {snow}cm à {name}.",
        "Les Pyrénées s'enneigent : {snow}cm prévus à {name}.",
        "Belle chute de neige dans les Pyrénées ❄️ {snow}cm attendus à {name}.",
        "La neige revient dans les Pyrénées ! {snow}cm à {name} dans les prochains jours.",
    ],
    "Vosges": [
        "Les Vosges sous la neige ! {snow}cm prévus à {name}.",
        "Conditions hivernales dans les Vosges : {snow}cm à {name}.",
    ],
    "Jura": [
        "Le Jura se couvre ❄️ {snow}cm attendus à {name}.",
        "Bonne nouvelle pour le Jura : {snow}cm à {name} dans les prochains jours.",
    ],
    "Massif Central": [
        "Le Massif Central sous la neige ! {snow}cm prévus à {name}.",
        "Retour de l'hiver au Massif Central : {snow}cm à {name}.",
    ],
}

MASSIF_MAP = {
    1:"Alpes du Nord",2:"Alpes du Nord",3:"Alpes du Nord",4:"Alpes du Nord",
    5:"Alpes du Nord",6:"Alpes du Nord",7:"Alpes du Nord",8:"Alpes du Nord",
    9:"Alpes du Nord",10:"Alpes du Nord",14:"Alpes du Nord",19:"Alpes du Nord",
    20:"Alpes du Nord",21:"Alpes du Nord",28:"Alpes du Nord",33:"Alpes du Nord",
    40:"Alpes du Nord",56:"Alpes du Nord",58:"Alpes du Nord",70:"Alpes du Nord",
    72:"Alpes du Nord",73:"Alpes du Nord",89:"Alpes du Sud",90:"Alpes du Sud",
    91:"Alpes du Sud",95:"Alpes du Sud",104:"Alpes du Sud",110:"Alpes du Sud",
    123:"Pyrénées",126:"Pyrénées",156:"Vosges",173:"Jura",182:"Massif Central",
    183:"Massif Central",
}

import random

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
    return round(max(vals)), vals

def send_notification(name, snow_cm, station_id):
    massif = MASSIF_MAP.get(station_id)
    massif_msgs = MESSAGES_MASSIF.get(massif, []) if massif else []
    pool = (massif_msgs + MESSAGES_STATION) if massif_msgs else MESSAGES_STATION
    msg = random.choice(pool).format(name=name, snow=snow_cm)
    title = f"❄️ {snow_cm}cm prévus à {name} !"
    slug = slugify(name)
    url = f"https://snowfinder.fr/stations/{slug}.html"

    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["All"],  # TOUS les abonnés
        "headings": {"fr": title, "en": title},
        "contents": {"fr": msg, "en": msg},
        "url": url,
        "chrome_web_icon": "https://snowfinder.fr/logo.png",
        "web_push_topic": "daily_snow_alert",  # remplace la notif précédente
    }

    req = urllib.request.Request(
        "https://onesignal.com/api/v1/notifications",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {ONESIGNAL_API_KEY}",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
    return resp

def main():
    print("=== SnowFinder — Alerte neige du soir ===")
    results = []

    for s in STATIONS:
        try:
            snow_cm, vals = get_snow(s["lat"], s["lon"])
            print(f"  {s['name']:25} → {snow_cm}cm")
            if snow_cm >= 10:
                results.append({"station": s, "snow": snow_cm})
        except Exception as e:
            print(f"  ⚠️  {s['name']}: {e}")

    if not results:
        print("\nAucune chute significative prévue — pas de notification envoyée.")
        return

    # Envoyer UNE seule notif pour la station avec le plus de neige
    results.sort(key=lambda x: x["snow"], reverse=True)
    best = results[0]
    print(f"\n🏆 Meilleure chute : {best['station']['name']} → {best['snow']}cm")

    resp = send_notification(best["station"]["name"], best["snow"], best["station"]["id"])
    recipients = resp.get("recipients", 0)
    print(f"✅ Notification envoyée → {recipients} abonné(s)")
    print(f"   Message : {best['snow']}cm à {best['station']['name']}")

if __name__ == "__main__":
    main()
