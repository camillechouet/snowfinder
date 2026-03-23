// ============================================================
//  STATION DU MOMENT — SOURCE UNIQUE
//  Pour changer la station, modifiez uniquement ce fichier.
//  → Changez SOTM_ID avec l'id de la nouvelle station
//  → Changez SOTM_PHOTO avec une URL Unsplash ou autre
//  → Changez SOTM_EDITO pour le texte éditorial personnalisé
// ============================================================

var SOTM_ID = 42; // Sainte-Foy-Tarentaise

// Photo de couverture (URL Unsplash recommandée)
var SOTM_PHOTO = "https://images.unsplash.com/photo-1548133612-cb5a8c886b4c?w=900&q=80";

// Texte éditorial (laissez vide "" pour utiliser la description standard de la station)
var SOTM_EDITO = "Le secret le mieux gardé entre Les Arcs et Val d'Isère. Un domaine préservé, un hors-piste légendaire et une neige poudreuse quasi garantie. Pour les skieurs qui fuient les foules sans sacrifier la qualité.";

// Libellés niveau / ambiance (mapping)
var NIV_LABELS = {debutant:"🟢 Débutant", intermediaire:"🔵 Intermédiaire", avance:"🔴 Avancé", expert:"⚫ Expert"};
var AMB_LABELS = {famille:"👨‍👩‍👧 Famille", festif:"🎉 Festif", luxe:"💎 Luxe", nature:"🌿 Nature", avance:"🎿 Avancé", village:"🏘 Village"};
var EQUIP_LABELS = {snowpark:"🛷 Snowpark", garderie:"👶 Garderie", restaurants:"🍽 Restaurants", telesiege:"🚡 Télésiège", spa:"💆 Spa"};

// ============================================================
//  FONCTIONS D'INJECTION — ne pas modifier
// ============================================================

function sotmGetStation() {
  if (typeof DATA === "undefined") return null;
  return DATA.find(function(s){ return s.id === SOTM_ID; }) || null;
}

// Injecte le bloc SOTW sur index.html
function sotmRenderIndex() {
  var s = sotmGetStation();
  if (!s) return;
  var desc = SOTM_EDITO || s.desc;

  var nameEl   = document.getElementById("sotwName");
  var regionEl = document.getElementById("sotwRegion");
  var descEl   = document.getElementById("sotwDesc");
  var stat1    = document.getElementById("sotwStat1");
  var stat2    = document.getElementById("sotwStat2");
  var stat3    = document.getElementById("sotwStat3");
  var ctaEl    = document.getElementById("sotwCta");
  var imgEl    = document.getElementById("sotwImg");

  if (nameEl)   nameEl.textContent   = s.name;
  if (regionEl) regionEl.textContent = "📍 " + s.region;
  if (descEl)   descEl.textContent   = desc;
  if (stat1)    stat1.innerHTML      = "<div class='sotw-stat-val'>" + s.alt_max + "m</div><div class='sotw-stat-lbl'>Altitude max</div>";
  if (stat2)    stat2.innerHTML      = "<div class='sotw-stat-val'>" + s.km + " km</div><div class='sotw-stat-lbl'>Pistes</div>";
  if (stat3)    stat3.innerHTML      = "<div class='sotw-stat-val'>" + s.forfait + "€</div><div class='sotw-stat-lbl'>Forfait/j</div>";
  if (ctaEl)    ctaEl.onclick        = function(){ window.location.href = "station-du-moment.html"; };
  if (imgEl)    imgEl.style.backgroundImage = "url(" + SOTM_PHOTO + ")";
}

// Injecte la fiche complète sur station-du-moment.html
function sotmRenderPage() {
  var s = sotmGetStation();
  if (!s) return;
  var desc = SOTM_EDITO || s.desc;

  // Meta & titre
  document.title = "Station du moment — " + s.name + " · SnowFinder";
  var metaDesc = document.querySelector("meta[name='description']");
  if (metaDesc) metaDesc.content = s.name + ", la station du moment sélectionnée par SnowFinder.";

  // Hero
  setEl("sotmName",     s.name);
  setEl("sotmSubtitle", "📍 " + s.region + " · " + s.massif);
  setEl("sotmScore",    "⭐ " + s.score.toFixed(1) + " / 5");

  // Fiche img
  var img = document.getElementById("ficheImg");
  if (img) img.style.backgroundImage = "url(" + SOTM_PHOTO + ")";

  // Corps
  setEl("ficheMassif",  "🏔 " + s.massif);
  setEl("ficheRegion",  "📍 " + s.region);
  setEl("ficheDesc",    desc);

  // Stats
  setEl("ficheStat1",   s.alt_max + " m");
  setEl("ficheStat2",   s.km + " km");
  setEl("ficheStat3",   s.remontees + "");
  setEl("ficheStat4",   s.forfait + " €");

  // Points forts
  var ptsEl = document.getElementById("fichePts");
  if (ptsEl && s.pts) {
    ptsEl.innerHTML = s.pts.map(function(p){
      return "<div class='fiche-pt'>" + p + "</div>";
    }).join("");
  }

  // Pistes
  var pistesEl = document.getElementById("fichePistes");
  if (pistesEl) {
    pistesEl.innerHTML =
      "<div class='piste piste-v'><span class='piste-num'>" + s.pistes.v + "</span> Vertes</div>" +
      "<div class='piste piste-b'><span class='piste-num'>" + s.pistes.b + "</span> Bleues</div>" +
      "<div class='piste piste-r'><span class='piste-num'>" + s.pistes.r + "</span> Rouges</div>" +
      "<div class='piste piste-n'><span class='piste-num'>" + s.pistes.n + "</span> Noires</div>";
  }

  // Altitude bar
  var fillEl = document.getElementById("ficheAltFill");
  var lblLow = document.getElementById("ficheAltLow");
  var lblHigh = document.getElementById("ficheAltHigh");
  if (fillEl) fillEl.style.width = ((s.alt_max - s.alt_min) / s.alt_max * 100) + "%";
  if (lblLow)  lblLow.textContent  = s.alt_min + " m (départ)";
  if (lblHigh) lblHigh.textContent = s.alt_max + " m (sommet)";

  // Tags niveaux
  var tagEl = document.getElementById("ficheTags");
  if (tagEl) {
    tagEl.innerHTML =
      s.niv.map(function(n){ return "<span class='fiche-tag'>" + (NIV_LABELS[n]||n) + "</span>"; }).join("") +
      s.amb.map(function(a){ return "<span class='fiche-tag'>" + (AMB_LABELS[a]||a) + "</span>"; }).join("");
  }

  // Équipements
  var equipEl = document.getElementById("ficheEquip");
  if (equipEl) {
    equipEl.innerHTML = s.equip.map(function(e){
      return "<span class='fiche-tag'>" + (EQUIP_LABELS[e]||e) + "</span>";
    }).join("");
  }

  // Bouton favoris
  var SOTM_ID_LOCAL = s.id;
  var favBtn = document.getElementById("favBtnSotm");
  function updateFavBtn(){
    var favs = JSON.parse(localStorage.getItem("sf_favorites")||"[]");
    if(favs.includes(SOTM_ID_LOCAL)){
      favBtn.textContent = "⭐ Dans mes favoris";
      favBtn.style.borderColor = "#f5c518";
      favBtn.style.color = "#b8860b";
    } else {
      favBtn.textContent = "☆ Ajouter aux favoris";
      favBtn.style.borderColor = "";
      favBtn.style.color = "";
    }
  }
  if (favBtn) {
    favBtn.onclick = function(){
      var favs = JSON.parse(localStorage.getItem("sf_favorites")||"[]");
      if(favs.includes(SOTM_ID_LOCAL)){
        favs = favs.filter(function(x){return x!==SOTM_ID_LOCAL;});
      } else {
        favs.push(SOTM_ID_LOCAL);
        if(navigator.vibrate) navigator.vibrate(40);
      }
      localStorage.setItem("sf_favorites", JSON.stringify(favs));
      updateFavBtn();
    };
    updateFavBtn();
  }

  // Lien fiche complète
  var ficheLink = document.getElementById("ficheLinkRecherche");
  if (ficheLink) ficheLink.href = "recherche.html?station=" + s.id;
}

function setEl(id, txt) {
  var el = document.getElementById(id);
  if (el) el.textContent = txt;
}
