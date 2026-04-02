"""
PATCH — Ajouter Les Folies Douces dans les fiches stations
===========================================================
Dans _scripts/generate_stations.py, deux modifications à faire :

──────────────────────────────────────────────────────────
1. AJOUTER cette constante Python en haut du script
   (après les imports, avant la fonction generate_page)
──────────────────────────────────────────────────────────
"""

FOLIES_DOUCES_IDS = {1, 3, 5, 6, 7, 8, 9, 14, 72}
# 1=Val d'Isère  3=Les Arcs     5=Chamonix (FD Hôtel)  6=Avoriaz
# 7=Courchevel   8=Méribel      9=Val Thorens  14=Megève  72=Alpe d'Huez

"""
──────────────────────────────────────────────────────────
2. AJOUTER ce bloc HTML dans la fonction generate_page(),
   juste AVANT la section hébergement (cherchez la ligne
   qui contient "Booking" ou "Réserver" ou "heberg")
──────────────────────────────────────────────────────────
"""

# Code à insérer dans generate_page() :
FOLIES_DOUCES_HTML = """
  <!-- Folies Douces -->
  {fd_section}
"""

FOLIES_DOUCES_SECTION = """
  <div style="background:linear-gradient(135deg,#1a0a2e,#3b0764);border-radius:12px;padding:16px 20px;margin:20px 0;display:flex;align-items:center;gap:14px">
    <div style="font-size:2rem;flex-shrink:0">🎶</div>
    <div style="flex:1">
      <div style="color:white;font-family:'DM Serif Display',serif;font-size:1.05rem;font-weight:700">Les Folies Douces</div>
      <div style="color:rgba(255,255,255,.7);font-size:.8rem;margin-top:3px">Après-ski premium · Musique live · Rooftop au pied des pistes</div>
      <a href="https://www.lesfoliesdouces.com" target="_blank" rel="noopener" style="color:#c084fc;font-size:.75rem;font-weight:600;text-decoration:none">lesfoliesdouces.com ↗</a>
    </div>
  </div>
"""

# Dans generate_page(), chercher la ligne qui build le HTML final
# et ajouter cette logique :
#
#   fd_html = FOLIES_DOUCES_SECTION if station_id in FOLIES_DOUCES_IDS else ""
#
# Puis dans le template HTML, remplacer {fd_section} par fd_html

"""
──────────────────────────────────────────────────────────
EXEMPLE d'intégration dans generate_page() :

def generate_page(station):
    station_id = station["id"]
    ...
    fd_html = FOLIES_DOUCES_SECTION if station_id in FOLIES_DOUCES_IDS else ""
    
    html = f'''
    ...votre template...
    {fd_html}
    ...section hébergement...
    '''
    return html
──────────────────────────────────────────────────────────
"""
