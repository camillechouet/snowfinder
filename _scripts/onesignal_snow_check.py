#!/usr/bin/env python3
"""
SnowFinder — Notifications push.

Logique :
  - Saison (nov-avril) :
      * Cascade neige en 4 étapes selon la fiabilité des prévisions météo :
          J-10ish (leadtime 8-11j) : "tendance" — pas de chiffre ferme, juste un signal
          J-7ish  (leadtime 5-7j)  : première fourchette (large)
          J-4ish  (leadtime 2-4j)  : fourchette resserrée
          J-1ish  (leadtime 0-1j)  : prévision ferme
        Un "épisode neigeux" = une date cible + un massif détectés une fois,
        puis suivi au fil des jours (état persisté dans snow_episodes_state.json,
        committé par le workflow). Chaque étape n'est envoyée qu'une seule fois
        par épisode, dans l'ordre. Max 1 notif neige / jour.
      * Vacances scolaires (J-14/J-7, toute l'année)
      * Enneigement exceptionnel (fallback si pas d'épisode en cours) — 1x max/semaine
  - Hors saison (mai-oct) : 1 message humoristique toutes les 2 semaines (lundi)

Seuil de détection : 20cm cumulés sur 2 jours (D et D+1) sur au moins 1 station
d'un massif → on considère qu'il y a un signal "épisode neigeux" pour ce massif.
C'est un seuil arbitraire à ajuster avec le retour terrain (confiance : moyenne).
"""
import os, json, urllib.request, unicodedata, re, random
from datetime import date, timedelta

ONESIGNAL_APP_ID  = os.environ['ONESIGNAL_APP_ID']
ONESIGNAL_API_KEY = os.environ['ONESIGNAL_API_KEY']

STATE_FILE = os.path.join(os.path.dirname(__file__), 'snow_episodes_state.json')

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

MASSIFS = sorted({s["massif"] for s in STATIONS})

# ─── SEUILS & ÉTAPES ──────────────────────────────────────────────────────────
SNOW_THRESHOLD = 20   # cm cumulés sur 2 jours pour déclencher un épisode
STAGE_ORDER = ["j10", "j7", "j4", "j1"]

def stage_for_leadtime(leadtime):
    """Retourne l'étape correspondant au nombre de jours avant la date cible."""
    if leadtime >= 8:
        return "j10"
    if leadtime >= 5:
        return "j7"
    if leadtime >= 2:
        return "j4"
    if leadtime >= 0:
        return "j1"
    return None  # date passée → épisode terminé

# ─── MESSAGES CASCADE NEIGE ───────────────────────────────────────────────────
MSG_J10 = [  # tendance — pas de chiffre ferme obligatoire, mais on peut donner un ordre de grandeur
    ("{snow}cm attendus dans les {massif} dans une dizaine de jours ! À surveiller 😍❄️",
     "Signal neige dans les {massif} d'ici une dizaine de jours ({snow}cm à confirmer) 👀❄️"),
    ("Tendance à surveiller : possible épisode neigeux dans les {massif} d'ici 10 jours ❄️",
     "Ça pourrait bouger dans les {massif} dans une dizaine de jours... on garde un œil 👀"),
]
MSG_J7 = [  # première fourchette large — plus de confiance
    ("Ça se confirme ! Jusqu'à {snow}cm attendus sur des stations comme {station} ! Go 🚗",
     "{snow}cm en vue à {station} d'ici la semaine prochaine. On croise les doigts 🤞❄️"),
    ("La tendance se précise : jusqu'à {snow}cm à {station} la semaine prochaine ❄️",
     "Épisode neigeux qui se confirme sur {station} : jusqu'à {snow}cm prévus 🏔️"),
]
MSG_J4 = [  # fourchette resserrée
    ("Neige confirmée à {station} : autour de {snow}cm attendus dans les prochains jours 🎿",
     "{station} va être blanchie : ~{snow}cm prévus d'ici quelques jours. On prépare les skis ?"),
    ("On resserre : {snow}cm bien partis pour tomber sur {station} cette semaine ❄️",
     "Prévision qui se confirme : {snow}cm à {station} dans les prochains jours 🏔️"),
]
MSG_J1 = [  # prévision ferme
    ("C'est pour très bientôt : {snow}cm attendus à {station} ! Direction les pistes 🎿",
     "{snow}cm à {station} dans les prochaines 24h. Cette fois c'est du sûr ❄️"),
    ("Neige fraîche imminente à {station} : {snow}cm annoncés. On y va ? 🚗❄️",
     "C'est officiel : {snow}cm à {station}. Les conditions seront parfaites 🏔️"),
]
STAGE_MESSAGES = {"j10": MSG_J10, "j7": MSG_J7, "j4": MSG_J4, "j1": MSG_J1}
STAGE_TOPIC    = {"j10": "snow_j10", "j7": "snow_j7", "j4": "snow_j4", "j1": "snow_j1"}

MSG_ENNEI = [
    ("L'enneigement est au top en ce moment ! C'est le genre de conditions qui font des regrets ⛷️",
     "Conditions parfaites dans les {massif} ❄️ Quelqu'un a dit poudreuse ?"),
    ("Snowreport : les {massif} sont dans leur meilleure forme de la saison 🏔️",
     "Bonne nouvelle du jour : conditions excellentes sur les pistes en ce moment 🎿"),
]

# ─── MESSAGES VACANCES (toute l'année) ────────────────────────────────────────
MSG_VACANCES = [
    ("Dans {days} jours c'est les vacances ! Les hébergements montagne se remplissent déjà 🎿",
     "Les vacances arrivent dans {days} jours. Ta station idéale t'attend 🏔️"),
    ("J-{days} avant les vacances ⛷️ T'as pensé à la montagne dans tout ça ?",
     "Rappel amical : dans {days} jours c'est les vacances. Les prix, eux, n'attendent pas 😅"),
    ("Vacances dans {days} jours 🎉 Les stations font de l'œil. Et toi ?",
     "J-{days} ⏳ Ta station idéale est à 2 clics sur SnowFinder 🏔️"),
]

# ─── MESSAGES HORS SAISON (mai-oct) ──────────────────────────────────────────
MSG_ETE = [
    ("Allez, plus que quelques mois avant de retrouver la plus belle période de l'année. Courage 🏔️",
     "La montagne t'attend. Encore un peu de patience, promis ça vaut le coup ❄️"),
    ("Bientôt le retour des raclettes 🧀 On compte les jours avec toi.",
     "Le fromage fondu et la neige fraîche te manquent déjà ? On comprend 🧀❄️"),
    ("On sait, on sait, l'été c'est long quand on pense ski toute l'année ⛷️",
     "Patience... Les pistes reviendront. En attendant, on prépare la saison pour toi 🎿"),
]

VACANCES = [
    ("Noël 2025",      date(2025, 12, 20), date(2026,  1,  4)),
    ("Hiver 2026",     date(2026,  2,  7), date(2026,  2, 22)),
    ("Printemps 2026", date(2026,  4, 11), date(2026,  4, 26)),
    ("Noël 2026",      date(2026, 12, 19), date(2027,  1,  3)),
    ("Hiver 2027",     date(2027,  2,  6), date(2027,  2, 21)),
]
JOURS_PREVENANCE = [14, 7]

def slugify(name):
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', name.lower())).strip('-')

def get_forecast(lat, lon, days=16):
    url = (f"https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}"
           f"&daily=snowfall_sum&forecast_days={days}&timezone=Europe/Paris")
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    dates = data["daily"]["time"]
    snow  = [round(v or 0) for v in data["daily"]["snowfall_sum"]]
    return list(zip(dates, snow))  # [(date_str, cm), ...] index 0 = aujourd'hui

def send_notif(title, body, url, topic):
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["All"],
        "headings": {"fr": title, "en": title},
        "contents": {"fr": body,  "en": body},
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
        return json.loads(r.read()).get("recipients", 0)

def check_vacances():
    today = date.today()
    for nom, debut, _ in VACANCES:
        for j in JOURS_PREVENANCE:
            if today == debut - timedelta(days=j):
                return nom, j
    return None, None

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"episodes": {}}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# ─── COLLECTE MÉTÉO ────────────────────────────────────────────────────────────
def collect_forecasts():
    """Retourne { station_id: [(date_str, cm), ...] } pour toutes les stations."""
    out = {}
    for s in STATIONS:
        try:
            out[s["id"]] = get_forecast(s["lat"], s["lon"])
        except Exception as e:
            print(f"  ⚠️  {s['name']}: {e}")
    return out

def best_2day_window(forecasts, station_id, day_index):
    """Somme sur (day_index, day_index+1) pour une station donnée, si dispo."""
    data = forecasts.get(station_id)
    if not data or day_index >= len(data):
        return 0
    total = data[day_index][1]
    if day_index + 1 < len(data):
        total += data[day_index + 1][1]
    return total

def top_station_for_massif_day(forecasts, massif, day_index):
    """Renvoie (station, cm_2j) la station avec le meilleur cumul 2j pour ce massif/jour."""
    best = None
    for s in STATIONS:
        if s["massif"] != massif:
            continue
        cm = best_2day_window(forecasts, s["id"], day_index)
        if best is None or cm > best[1]:
            best = (s, cm)
    return best

def find_new_or_updated_episodes(forecasts, state, today):
    """
    Parcourt les jours 1..15 pour chaque massif, détecte un signal neige
    (>=SNOW_THRESHOLD cm sur 2j sur au moins 1 station) et crée/actualise
    l'épisode correspondant dans le state (clé = massif + semaine ISO cible).
    """
    for massif in MASSIFS:
        best_candidate = None  # (day_index, station, cm)
        for day_index in range(1, 16):
            top = top_station_for_massif_day(forecasts, massif, day_index)
            if top is None:
                continue
            station, cm = top
            if cm >= SNOW_THRESHOLD:
                if best_candidate is None or cm > best_candidate[2]:
                    best_candidate = (day_index, station, cm)
        if not best_candidate:
            continue
        day_index, station, cm = best_candidate
        target_date = today + timedelta(days=day_index)
        week_key = f"{massif}_{target_date.isocalendar()[0]}-W{target_date.isocalendar()[1]:02d}"
        ep = state["episodes"].get(week_key)
        if ep is None:
            state["episodes"][week_key] = {
                "massif": massif,
                "target_date": target_date.isoformat(),
                "top_station": station["name"],
                "snow_cm": cm,
                "stages_sent": [],
            }
        else:
            # Mise à jour de l'estimation (la prévision s'affine avec le temps)
            ep["target_date"] = target_date.isoformat()
            ep["top_station"] = station["name"]
            ep["snow_cm"] = cm

def process_episodes(state, today, daily_cap=1):
    """
    Pour chaque épisode suivi, calcule l'étape due et envoie la notif si
    elle n'a pas déjà été envoyée. Retourne le nb de notifs neige envoyées.
    Nettoie les épisodes expirés (date cible dépassée).
    """
    sent = 0
    expired = []
    # Trie par urgence (étape la plus avancée / date la plus proche en premier)
    items = sorted(
        state["episodes"].items(),
        key=lambda kv: date.fromisoformat(kv[1]["target_date"])
    )
    for key, ep in items:
        target_date = date.fromisoformat(ep["target_date"])
        leadtime = (target_date - today).days
        stage = stage_for_leadtime(leadtime)
        if stage is None:
            expired.append(key)
            continue
        if stage not in ep["stages_sent"] and sent < daily_cap:
            titre, corps = random.choice(STAGE_MESSAGES[stage])
            titre = titre.format(snow=ep["snow_cm"], name=ep["top_station"],
                                  station=ep["top_station"], massif=ep["massif"])
            corps = corps.format(snow=ep["snow_cm"], name=ep["top_station"],
                                  station=ep["top_station"], massif=ep["massif"])
            url = f"https://snowfinder.fr/stations/{slugify(ep['top_station'])}.html"
            print(f"\n🚨 Épisode [{ep['massif']}] étape {stage} → {ep['top_station']} "
                  f"({ep['snow_cm']}cm, J-{leadtime})")
            n = send_notif(titre, corps, url, STAGE_TOPIC[stage])
            print(f"✅ Notif {stage} envoyée → {n} abonné(s)")
            ep["stages_sent"].append(stage)
            sent += 1
    for key in expired:
        del state["episodes"][key]
    return sent

def main():
    today = date.today()
    en_saison = today.month in [11, 12, 1, 2, 3, 4]
    notifs_envoyees = 0

    print(f"=== SnowFinder — {today} — {'saison' if en_saison else 'hors saison'} ===")

    # ── 1. VACANCES (tous les jours, J-14 et J-7, toute l'année) ─────────────
    nom_vac, days = check_vacances()
    if nom_vac:
        print(f"\n📅 Vacances '{nom_vac}' dans {days} jours !")
        titre, corps = random.choice(MSG_VACANCES)
        titre = titre.format(days=days)
        corps = corps.format(days=days)
        n = send_notif(titre, corps, "https://snowfinder.fr/recherche.html", "vacances")
        print(f"✅ Notif vacances envoyée → {n} abonné(s)")
        notifs_envoyees += 1

    # ── 2. HORS SAISON : 1 message humour toutes les 2 semaines (lundi) ──────
    if not en_saison:
        semaine_paire = today.isocalendar()[1] % 2 == 0
        if today.weekday() == 0 and semaine_paire and notifs_envoyees == 0:
            titre, corps = random.choice(MSG_ETE)
            print(f"\n☀️ Message hors-saison (lundi, semaine paire)")
            send_notif(titre, corps, "https://snowfinder.fr/recherche.html", "off_season")
            print("✅ Notif été envoyée")
        else:
            print("\nHors saison — pas le bon lundi (1x/2 semaines) ou déjà 1 notif.")
        return

    # ── 3. CASCADE NEIGE (tous les jours en saison) ──────────────────────────
    print("\n❄️ Vérification enneigement (16 jours)...")
    forecasts = collect_forecasts()

    state = load_state()
    find_new_or_updated_episodes(forecasts, state, today)

    remaining_cap = max(0, 1 - notifs_envoyees) if False else 1  # cap neige indépendant de vacances
    sent = process_episodes(state, today, daily_cap=1)
    notifs_envoyees += sent
    save_state(state)

    if state["episodes"]:
        print("\n📋 Épisodes suivis :")
        for key, ep in state["episodes"].items():
            print(f"  {key} → {ep['top_station']} ({ep['snow_cm']}cm) "
                  f"étapes envoyées: {ep['stages_sent']}")

    # ── 4. Fallback enneigement exceptionnel (si aucun épisode ce jour, 1x/sem) ──
    if sent == 0 and today.weekday() == 0:
        best_massif = None
        for massif in MASSIFS:
            top = top_station_for_massif_day(forecasts, massif, 0)
            if top and top[1] >= 50:
                best_massif = massif
                break
        if best_massif:
            titre, corps = random.choice(MSG_ENNEI)
            titre = titre.format(massif=best_massif)
            corps = corps.format(massif=best_massif)
            print(f"\n🏔️ Enneigement top : {best_massif}")
            send_notif(titre, corps, "https://snowfinder.fr/enneigement.html", "enneigement_top")
            print("✅ Notif enneigement envoyée")

    print(f"\n=== Total : {notifs_envoyees} notif(s) neige/vacances ===")

if __name__ == "__main__":
    main()
