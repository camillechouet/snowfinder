#!/usr/bin/env python3
"""
SnowFinder — Notifications push.
Logique :
  - Vacances scolaires : J-14 et J-7 avant chaque période (tous les jours)
  - Neige / Enneigement : lundi et jeudi uniquement (max 2/semaine)
  - Combo neige+vacances : jusqu'à 3 notifs cette semaine-là
"""
import os, json, urllib.request, unicodedata, re, random
from datetime import date, timedelta

ONESIGNAL_APP_ID  = os.environ['ONESIGNAL_APP_ID']
ONESIGNAL_API_KEY = os.environ['ONESIGNAL_API_KEY']

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
    ("T'as vu ? {snow}cm prévus à {name} ! On te laisse organiser le covoiturage 🚗❄️",
     "{snow}cm à {name}. Les excuses 'il fait pas assez de neige' ça marche plus 😄"),
    ("Fraîche garantie à {name} : {snow}cm cette semaine ❄️ Conditions parfaites !",
     "{name} va se blanchir sérieusement : {snow}cm prévus. Spoiler : c'est beau 🏔️"),
    ("Le genre de news qui font sourire : {snow}cm à {name} cette semaine ⛷️",
     "{snow}cm annoncés à {name}. La montagne n'attend pas, toi si ? 🎿"),
    ("On a les yeux rivés sur la météo pour toi : {snow}cm à {name} 👀",
     "{snow}cm de poudreuse en vue à {name}. Ce week-end a l'air d'accord 🎿"),
    ("Info capitale : {snow}cm à {name} ⏱️ Ça se réserve avant que tout parte !",
     "Neige fraîche chez {name} : {snow}cm. C'est le moment ou jamais 🎿"),
    ("{snow}cm ici, {snow}cm là... {name} va être incroyable 🏔️",
     "On a vérifié la météo pour toi : {snow}cm à {name}. De rien 😌"),
    ("Ce week-end à {name} : {snow}cm de fraîche prévus. Tes skis méritent ça 🎿",
     "{snow}cm à {name}. Conditions prometteuses. T'es encore là toi ? 🏔️"),
]

MSG_VACANCES = [
    ("Dans {days} jours c'est les vacances ! Les hébergements montagne se remplissent déjà 🎿",
     "Les vacances arrivent dans {days} jours. Ta station idéale t'attend 🏔️"),
    ("J-{days} avant les vacances ⛷️ T'as pensé à la montagne dans tout ça ?",
     "Rappel amical : dans {days} jours c'est les vacances. Les prix, eux, n'attendent pas 😅"),
    ("Soyons honnêtes : dans {days} jours t'aurais pu être sur les pistes 🎿 C'est encore jouable !",
     "Dans {days} jours les pistes t'attendent. Les bons hébergements aussi... pour l'instant 👀"),
    ("Vacances dans {days} jours 🎉 Les stations font de l'œil. Et toi ?",
     "J-{days} ⏳ Ta station idéale est à 2 clics sur SnowFinder 🏔️"),
    ("T'as {days} jours pour décider où tu pars au ski. On peut t'aider 😉 🎿",
     "Dans {days} jours c'est les vacances ! Montagne ou pas montagne ? (mauvaise question) 🏔️"),
    ("Tic tac ⏰ Dans {days} jours c'est les vacances. Les pistes n'attendent que toi !",
     "Plus que {days} jours. La montagne : 2400m d'arguments pour y aller ❄️"),
    ("Les vacances approchent dans {days} jours ! Toujours pas de station choisie ? On s'en occupe 🎿",
     "Dans {days} jours tu pourrais être sur les pistes. C'est un fait 🎿"),
]

MSG_ENNEI = [
    ("L'enneigement est au top en ce moment ! C'est le genre de conditions qui font des regrets ⛷️",
     "Conditions parfaites dans les {massif} ❄️ Quelqu'un a dit poudreuse ?"),
    ("Snowreport : les {massif} sont dans leur meilleure forme de la saison 🏔️",
     "Bonne nouvelle du jour : conditions excellentes sur les pistes en ce moment 🎿"),
    ("La montagne est belle en ce moment. Vraiment belle. C'est tout ce qu'on voulait dire 🏔️",
     "Conditions top, météo validée, pistes ouvertes. Il manque juste toi ⛷️"),
    ("On a regardé les conditions ce matin dans les {massif}... et on pense fort à toi 🎿",
     "Si t'attendais le bon moment pour partir au ski, c'est maintenant ❄️"),
    ("Honnêtement, les conditions sont vraiment bonnes en ce moment. On dit ça, on dit rien 😌🎿",
     "Beau soleil + pistes bien enneigées dans les {massif} ☀️❄️"),
    ("Les pistes des {massif} sont au top cette semaine. Tes skis méritent mieux que le garage 🎿",
     "Enneigement au beau fixe dans les {massif} ! C'est maintenant qu'il faut y aller 🏔️"),
    ("Cette semaine dans les {massif} : pistes en parfait état ❄️ On valide.",
     "Conditions quasi parfaites dans les {massif}. Juste parfaites. Voilà 🎿"),
    ("Les {massif} brillent cette semaine ☀️❄️ Pistes et enneigement au top !",
     "Pas grand chose à dire, juste que les {massif} sont magnifiques en ce moment 🏔️"),
]

# Vacances scolaires — Zone B (la plus courante)
VACANCES = [
    ("Noël 2025",      date(2025, 12, 20), date(2026,  1,  4)),
    ("Hiver 2026",     date(2026,  2,  7), date(2026,  2, 22)),
    ("Printemps 2026", date(2026,  4, 11), date(2026,  4, 26)),
    ("Noël 2026",      date(2026, 12, 19), date(2027,  1,  3)),
    ("Hiver 2027",     date(2027,  2,  6), date(2027,  2, 21)),
]
JOURS_PREVENANCE = [14, 7]  # 2 alertes par période uniquement

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
    return round(max(v or 0 for v in data["daily"]["snowfall_sum"]))

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

def main():
    today = date.today()
    weekday  = today.weekday()   # 0=lundi, 3=jeudi
    en_saison = today.month in [11, 12, 1, 2, 3, 4]
    notifs_envoyees = 0

    print(f"=== SnowFinder — {today} (jour {weekday}) ===")

    # ── 1. VACANCES (tous les jours, J-14 et J-7) ────────────────────────────
    nom_vac, days = check_vacances()
    if nom_vac:
        print(f"\n📅 Vacances '{nom_vac}' dans {days} jours !")
        titre, corps = random.choice(MSG_VACANCES)
        titre = titre.format(days=days)
        corps = corps.format(days=days)
        n = send_notif(titre, corps, "https://snowfinder.fr/recherche.html", "vacances")
        print(f"✅ Notif vacances envoyée → {n} abonné(s)")
        notifs_envoyees += 1

    # ── 2. NEIGE / ENNEIGEMENT — lundi (0) et jeudi (3) uniquement ───────────
    if weekday not in [0, 3]:
        print(f"\nPas de vérification neige aujourd'hui (jour {weekday})")
        return

    if not en_saison:
        print(f"\nHors saison (mois {today.month}) — pas de vérification neige")
        return

    # Limite : si déjà 2 notifs ce jour (vacances + autre), on vérifie quand même
    # car un jour vacances+neige peut atteindre 2 (combo autorisé)
    limit = 3 if nom_vac else 2

    print("\n❄️ Vérification enneigement...")
    resultats = []
    for s in STATIONS:
        try:
            snow = get_snow(s["lat"], s["lon"])
            print(f"  {s['name']:25} → {snow}cm")
            resultats.append({"station": s, "snow": snow})
        except Exception as e:
            print(f"  ⚠️  {s['name']}: {e}")

    if notifs_envoyees >= limit:
        print(f"\nLimite de {limit} notifs atteinte cette semaine.")
        return

    # ── 3. ALERTE NEIGE ───────────────────────────────────────────────────────
    top_neige = sorted([r for r in resultats if r["snow"] >= 15],
                       key=lambda x: x["snow"], reverse=True)
    if top_neige:
        best  = top_neige[0]
        name  = best["station"]["name"]
        snow  = best["snow"]
        titre, corps = random.choice(MSG_NEIGE)
        titre = titre.format(snow=snow, name=name)
        corps = corps.format(snow=snow, name=name)
        print(f"\n🚨 Alerte neige : {name} → {snow}cm")
        n = send_notif(titre, corps,
                       f"https://snowfinder.fr/stations/{slugify(name)}.html",
                       "snow_alert")
        print(f"✅ Notif neige envoyée → {n} abonné(s)")
        notifs_envoyees += 1

    # ── 4. ENNEIGEMENT TOP (si pas d'alerte neige et conditions excellentes) ──
    elif sum(1 for r in resultats if r["snow"] >= 50) >= 3:
        massifs = list({r["station"]["massif"] for r in resultats if r["snow"] >= 50})
        massif_str = " & ".join(massifs[:2])
        titre, corps = random.choice(MSG_ENNEI)
        titre = titre.format(massif=massif_str)
        corps = corps.format(massif=massif_str)
        print(f"\n🏔️ Enneigement top : {massif_str}")
        n = send_notif(titre, corps,
                       "https://snowfinder.fr/enneigement.html",
                       "enneigement_top")
        print(f"✅ Notif enneigement envoyée → {n} abonné(s)")
    else:
        print("\nPas de neige significative ni d'enneigement top — pas de notif.")

    print(f"\n=== Total envoyé aujourd'hui : {notifs_envoyees} notif(s) ===")

if __name__ == "__main__":
    main()
