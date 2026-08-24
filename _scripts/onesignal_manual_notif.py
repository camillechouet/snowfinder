#!/usr/bin/env python3
"""
SnowFinder — Envoi manuel d'une notification push.
Déclenché depuis GitHub Actions (workflow_dispatch) : Camille remplit un
formulaire (titre, texte, lien, type) et cette notif part à tous les abonnés.

Types prédéfinis (juste pour le topic OneSignal, aucun changement de contenu) :
  - station_du_moment
  - bon_plan
  - article
  - autre
"""
import os, json, urllib.request

ONESIGNAL_APP_ID  = os.environ['ONESIGNAL_APP_ID']
ONESIGNAL_API_KEY = os.environ['ONESIGNAL_API_KEY']

TITRE = os.environ.get('NOTIF_TITRE', '').strip()
CORPS = os.environ.get('NOTIF_CORPS', '').strip()
URL   = os.environ.get('NOTIF_URL', 'https://snowfinder.fr/').strip()
TYPE  = os.environ.get('NOTIF_TYPE', 'autre').strip()

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
        headers={"Content-Type": "application/json",
                 "Authorization": f"Basic {ONESIGNAL_API_KEY}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def main():
    if not TITRE or not CORPS:
        raise SystemExit("❌ Titre et corps du message sont obligatoires.")

    print(f"=== Notif manuelle — type: {TYPE} ===")
    print(f"Titre : {TITRE}")
    print(f"Corps : {CORPS}")
    print(f"URL   : {URL}")

    result = send_notif(TITRE, CORPS, URL, TYPE)
    recipients = result.get("recipients", 0)
    if "errors" in result:
        print(f"⚠️  Réponse OneSignal avec erreurs : {result['errors']}")
    print(f"\n✅ Notif envoyée → {recipients} abonné(s)")

if __name__ == "__main__":
    main()
