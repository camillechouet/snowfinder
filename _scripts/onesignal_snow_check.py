#!/usr/bin/env python3
"""
SnowFinder — Vérification quotidienne de l'enneigement et alertes push OneSignal.
Lancé chaque matin par GitHub Actions.
"""
import os, json, urllib.request, urllib.parse

ONESIGNAL_APP_ID  = os.environ['ONESIGNAL_APP_ID']
ONESIGNAL_API_KEY = os.environ['ONESIGNAL_API_KEY']

# Coordonnées GPS des stations surveillées
STATIONS = [
    {"id": 1,  "name": "Val d'Isère",      "lat": 45.448, "lon": 6.969},
    {"id": 2,  "name": "Tignes",           "lat": 45.469, "lon": 6.908},
    {"id": 3,  "name": "Les Arcs",         "lat": 45.574, "lon": 6.781},
    {"id": 4,  "name": "La Plagne",        "lat": 45.510, "lon": 6.676},
    {"id": 5,  "name": "Chamonix",         "lat": 45.924, "lon": 6.870},
    {"id": 6,  "name": "Avoriaz",          "lat": 46.193, "lon": 6.762},
    {"id": 7,  "name": "Courchevel",       "lat": 45.416, "lon": 6.634},
    {"id": 8,  "name": "Méribel",          "lat": 45.393, "lon": 6.564},
    {"id": 9,  "name": "Val Thorens",      "lat": 45.298, "lon": 6.582},
    {"id": 10, "name": "Les Menuires",     "lat": 45.319, "lon": 6.537},
    {"id": 14, "name": "Megève",           "lat": 45.856, "lon": 6.617},
    {"id": 16, "name": "Les Houches",      "lat": 45.887, "lon": 6.801},
    {"id": 19, "name": "Morzine",          "lat": 46.178, "lon": 6.707},
    {"id": 20, "name": "Les Gets",         "lat": 46.161, "lon": 6.667},
    {"id": 21, "name": "Châtel",           "lat": 46.271, "lon": 6.836},
    {"id": 28, "name": "Flaine",           "lat": 46.002, "lon": 6.676},
    {"id": 33, "name": "La Clusaz",        "lat": 45.906, "lon": 6.430},
    {"id": 34, "name": "Le Grand-Bornand", "lat": 45.943, "lon": 6.426},
    {"id": 40, "name": "Les Saisies",      "lat": 45.749, "lon": 6.527},
    {"id": 56, "name": "Valloire",         "lat": 45.170, "lon": 6.432},
    {"id": 58, "name": "Val Cenis",        "lat": 45.198, "lon": 6.930},
    {"id": 70, "name": "Chamrousse",       "lat": 45.119, "lon": 5.880},
    {"id": 72, "name": "Alpe d'Huez",      "lat": 45.090, "lon": 6.070},
    {"id": 73, "name": "Les Deux Alpes",   "lat": 45.016, "lon": 6.120},
    {"id": 89, "name": "Serre Chevalier",  "lat": 44.920, "lon": 6.497},
    {"id": 90, "name": "Montgenèvre",      "lat": 44.932, "lon": 6.720},
    {"id": 91, "name": "Vars",             "lat": 44.584, "lon": 6.693},
    {"id": 95, "name": "Orcières-Merlette","lat": 44.683, "lon": 6.322},
    {"id": 104,"name": "Pra-Loup",         "lat": 44.348, "lon": 6.599},
    {"id": 110,"name": "Isola 2000",       "lat": 44.191, "lon": 7.167},
    {"id": 123,"name": "Saint-Lary-Soulan","lat": 42.826, "lon": 0.328},
    {"id": 126,"name": "Cauterets",        "lat": 42.889, "lon": -0.095},
    {"id": 139,"name": "Font-Romeu",       "lat": 42.507, "lon": 2.051},
    {"id": 156,"name": "Gérardmer",        "lat": 48.071, "lon": 6.884},
    {"id": 173,"name": "Les Rousses",      "lat": 46.500, "lon": 5.993},
    {"id": 182,"name": "Super Besse",      "lat": 45.499, "lon": 2.840},
    {"id": 183,"name": "Le Mont Dore",     "lat": 45.574, "lon": 2.820},
]

SNOW_THRESHOLD_CM = 1  # Temporaire pour test  # Seuil déclenchement alerte

def get_snow_forecast(lat, lon):
    """Retourne le max de neige prévu sur 5 jours (cm)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=snowfall_sum"
        f"&forecast_days=5"
        f"&timezone=Europe/Paris"
    )
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    values = [v or 0 for v in data["daily"]["snowfall_sum"]]
    return round(max(values)), values

def send_onesignal_notification(station_id, station_name, snow_cm, snow_days):
    """Envoie une notification push aux abonnés qui ont cette station en favori."""
    # Trouver le jour avec le plus de neige
    max_idx = snow_days.index(max(snow_days))
    day_labels = ["aujourd'hui", "demain", "après-demain", "dans 3 jours", "dans 4 jours"]
    best_day = day_labels[max_idx] if max_idx < len(day_labels) else "prochainement"

    title = f"❄️ Neige à {station_name} !"
    body  = f"{snow_cm}cm prévus {best_day}. Les conditions s'annoncent superbes !"

    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "filters": [
            {"field": "tag", "key": f"fav_{station_id}", "relation": "=", "value": "1"}
        ],
        "headings": {"fr": title, "en": title},
        "contents": {"fr": body,  "en": body},
        "url": f"https://snowfinder.fr/stations/{station_name.lower().replace(' ','-').replace(chr(39),'-')}.html",
        "chrome_web_icon": "https://snowfinder.fr/logo.png",
        "firefox_icon":    "https://snowfinder.fr/logo.png",
        "web_push_topic":  f"snow_{station_id}",  # évite les doublons
    }

    req = urllib.request.Request(
        "https://onesignal.com/api/v1/notifications",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Basic {ONESIGNAL_API_KEY}",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
    return resp

def main():
    print("=== SnowFinder — Vérification enneigement ===")
    alerts_sent = 0

    for s in STATIONS:
        try:
            snow_cm, snow_days = get_snow_forecast(s["lat"], s["lon"])
            print(f"  {s['name']:25} → {snow_cm}cm prévus sur 5j", end="")

            if snow_cm >= SNOW_THRESHOLD_CM:
                resp = send_onesignal_notification(s["id"], s["name"], snow_cm, snow_days)
                recipients = resp.get("recipients", 0)
                print(f"  🚨 ALERTE envoyée → {recipients} abonnés")
                alerts_sent += 1
            else:
                print()

        except Exception as e:
            print(f"  ⚠️  Erreur pour {s['name']}: {e}")

    print(f"\n✅ {alerts_sent} alerte(s) envoyée(s)")

if __name__ == "__main__":
    main()
