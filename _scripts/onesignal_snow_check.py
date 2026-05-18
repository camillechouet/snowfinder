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

MESSAGES = [
    "{snow}cm de fraîche attendus à {name} ! Est-ce que ta station favorite en profite aussi ?",
    "❄️ Grosse chute prévue à {name} : {snow}cm ! Le bon moment pour regarder ta station.",
    "{snow}cm annoncés à {name} dans les prochains jours. Ta prochaine session se prépare maintenant !",
    "Poudreuse en vue à {name} ! {snow}cm prévus. Et chez toi, ça donne quoi ?",
    "{snow}cm de neige fraîche à {name}. Les conditions s'annoncent superbes ce week-end !",
]

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
    msg = random.choice(MESSAGES).format(name=name, snow=snow_cm)
    title = f"❄️ {snow_cm}cm prévus à {name} !"
    slug = slugify(name)
    url = f"https://snowfinder.fr/stations/{slug}.html"

    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["Total Subscriptions"],  # TOUS les abonnés
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
