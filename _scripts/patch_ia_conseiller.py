#!/usr/bin/env python3
"""
patch_ia_conseiller.py
======================
Remplace le panneau "Conseiller IA" dans recherche.html par une zone de
texte libre alimentée par le moteur ia_engine (parsing sémantique JS).

Avant : 6 étapes de questionnaire à boutons.
Après : input texte libre + 6 suggestions cliquables + top 5 résultats.

Le bouton FAB et le panneau overlay sont conservés (mêmes IDs, mêmes
classes, mêmes points d'entrée openIaPanel/closeIaPanel/iaGoStation),
donc aucun code ailleurs sur le site n'a besoin d'être modifié.

Usage :
  python3 patch_ia_conseiller.py [--root .]
"""
import argparse
import re
from pathlib import Path

# ── NOUVEAU PANNEAU HTML ───────────────────────────────────────────────────
NEW_PANEL_HTML = '''<div class="ia-panel-overlay" id="iaPanelOverlay">
  <div class="ia-panel" id="iaPanel">
    <div class="ia-panel-handle"></div>
    <div class="ia-panel-header">
      <div class="ia-panel-title">✨ Conseiller IA</div>
      <button class="ia-panel-close" onclick="closeIaPanel()">✕</button>
    </div>
    <div class="ia-body">
      <div class="ia-intro" id="iaIntro">
        <div class="ia-question">Quelle est ta station idéale&nbsp;?</div>
        <div class="ia-hint">Décris en quelques mots ce que tu cherches&nbsp;: budget, ambiance, niveau, massif, altitude, activités…</div>
      </div>

      <div class="ia-input-wrap" id="iaInputWrap">
        <textarea id="iaQuery" class="ia-textarea" rows="4" autocomplete="off"
          placeholder="Ex : Je cherche une station pas trop chère dans les Pyrénées, à moins de 1500m, avec de belles balades et un domaine quand même assez grand"></textarea>

        <div class="ia-sugg-label">Inspirations rapides&nbsp;:</div>
        <div class="ia-sugg-row">
          <button type="button" class="ia-sugg" data-q="Station famille pas trop chère avec garderie et beaucoup de pistes vertes">👨‍👩‍👧 Famille budget</button>
          <button type="button" class="ia-sugg" data-q="Domaine d'altitude pour skieur expert, freeride et hors-piste">⚡ Expert freeride</button>
          <button type="button" class="ia-sugg" data-q="Petit village authentique pas trop haut, ambiance tranquille proche de la nature">🏡 Village authentique</button>
          <button type="button" class="ia-sugg" data-q="Grande station festive entre amis avec après-ski animé">🎉 Entre amis</button>
          <button type="button" class="ia-sugg" data-q="Station luxe avec spa et bonne table">💎 Luxe & spa</button>
          <button type="button" class="ia-sugg" data-q="Pyrénées petit budget pour débutants">🏔️ Pyrénées débutants</button>
        </div>

        <button class="ia-search-btn" id="iaSearchBtn" onclick="iaSearch()">✨ Trouve-moi des stations</button>
      </div>

      <div class="ia-loading" id="iaLoading">
        <div class="ia-loading-spin"></div>
        <div class="ia-loading-text" id="iaLoadingText">Analyse de ta demande…</div>
      </div>

      <div class="ia-results" id="iaResults"></div>
    </div>
  </div>
</div>'''

# ── CSS SUPPLÉMENTAIRE (à injecter une seule fois dans le <style>) ─────────
EXTRA_CSS = '''
/* === CONSEILLER IA TEXTE LIBRE === */
.ia-intro{padding:6px 4px 14px}
.ia-intro .ia-question{font-family:"DM Serif Display",serif;font-size:1.35rem;color:var(--text);margin-bottom:6px;line-height:1.25}
.ia-intro .ia-hint{font-size:.85rem;color:var(--text-light);line-height:1.5}
.ia-input-wrap{display:block}
.ia-textarea{width:100%;border:2px solid var(--wood-light);border-radius:14px;padding:14px 16px;font-family:"DM Sans",sans-serif;font-size:.95rem;color:var(--text);background:var(--wood-pale);resize:none;transition:border-color .2s,background .2s;line-height:1.5}
.ia-textarea:focus{outline:none;border-color:var(--blue-mid);background:white}
.ia-textarea::placeholder{color:var(--text-light);font-style:italic}
.ia-sugg-label{font-size:.78rem;color:var(--text-light);margin:14px 4px 8px;font-weight:600}
.ia-sugg-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:18px}
.ia-sugg{padding:7px 12px;border-radius:18px;border:1.5px solid var(--border);background:white;font-family:"DM Sans",sans-serif;font-size:.78rem;cursor:pointer;color:var(--text-mid);transition:all .15s;font-weight:500}
.ia-sugg:hover{background:var(--blue-light);border-color:var(--blue-mid);color:var(--blue-dark)}
.ia-search-btn{width:100%;padding:14px 20px;background:linear-gradient(135deg,var(--blue-mid),var(--blue-dark));color:white;border:none;border-radius:14px;font-family:"DM Sans",sans-serif;font-size:.95rem;font-weight:700;cursor:pointer;transition:transform .15s,box-shadow .15s;box-shadow:0 4px 16px rgba(58,125,184,.3)}
.ia-search-btn:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 6px 20px rgba(58,125,184,.4)}
.ia-search-btn:disabled{opacity:.55;cursor:not-allowed;transform:none}
.ia-loading{display:none;text-align:center;padding:36px 16px}
.ia-loading.show{display:block}
.ia-loading-spin{width:40px;height:40px;border:3px solid var(--wood-light);border-top-color:var(--blue-mid);border-radius:50%;animation:iaspin 1s linear infinite;margin:0 auto 14px}
.ia-loading-text{font-size:.88rem;color:var(--text-mid);font-style:italic}
@keyframes iaspin{to{transform:rotate(360deg)}}
.ia-results{display:none;padding-top:10px}
.ia-results.show{display:block}
.ia-results-header{margin-bottom:14px}
.ia-results-intro{font-family:"DM Serif Display",serif;font-size:1.1rem;color:var(--text);margin-bottom:6px}
.ia-results-sub{font-size:.82rem;color:var(--text-light);line-height:1.5}
.ia-results-warn{background:var(--wood-pale);border:1.5px solid var(--wood-light);border-radius:12px;padding:12px 14px;margin-bottom:14px;font-size:.85rem;color:var(--text-mid);line-height:1.5}
.ia-result-card{background:white;border:1.5px solid var(--border);border-radius:14px;padding:14px;margin-bottom:10px;cursor:pointer;transition:all .2s;display:flex;gap:12px;align-items:flex-start}
.ia-result-card:hover{border-color:var(--blue-mid);transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.08)}
.ia-result-rank{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--blue-mid),var(--blue-dark));color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.95rem;flex-shrink:0;font-family:"DM Serif Display",serif}
.ia-result-body{flex:1;min-width:0}
.ia-result-name{font-family:"DM Serif Display",serif;font-size:1.05rem;color:var(--text);margin-bottom:2px}
.ia-result-meta{font-size:.74rem;color:var(--text-light);margin-bottom:8px}
.ia-result-reasons{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}
.ia-result-reason{font-size:.7rem;background:var(--blue-light);color:var(--blue-dark);padding:3px 8px;border-radius:6px;font-weight:500}
.ia-result-stats{display:flex;gap:10px;font-size:.74rem;color:var(--text-mid);flex-wrap:wrap}
.ia-result-stats span{display:inline-flex;align-items:center;gap:3px}
.ia-result-foot{display:flex;gap:8px;margin-top:18px;padding-top:14px;border-top:1px solid var(--wood-light)}
.ia-foot-btn{flex:1;padding:10px 14px;border-radius:10px;font-family:"DM Sans",sans-serif;font-size:.82rem;font-weight:600;border:none;cursor:pointer;text-align:center;text-decoration:none;color:var(--text-mid);background:var(--wood-pale);transition:all .15s}
.ia-foot-btn:hover{background:var(--wood-light);color:var(--text)}
.ia-foot-btn.primary{background:var(--blue-mid);color:white}
.ia-foot-btn.primary:hover{background:var(--blue-dark)}
'''

# ── NOUVEAU JS DU CONSEILLER ───────────────────────────────────────────────
NEW_JS = '''/* ══ CONSEILLER IA TEXTE LIBRE ══ */
/* Moteur de parsing sémantique : extrait critères depuis une phrase libre */
(function(){
  function nrm(s){return (s||"").toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g,"");}
  const KW = {
    budget:{
      eco:["pas cher","peu cher","abordable","economique","petit budget","bon marche","low cost","pas trop cher","pas tres cher","pas trop chere","pas chere","budget serre","budget reduit"],
      luxe:["luxe","luxueux","haut de gamme","premium","prestige","5 etoiles","chic","high end"]
    },
    niveau:{
      debutant:["debutant","debute","novice","pour debuter","je commence","jamais skie","premiere fois","apprendre","initiation","pistes vertes","vertes"],
      intermediaire:["intermediaire","moyen","bleu","pistes bleues"],
      avance:["avance","confirme","rouge","pistes rouges","bon skieur"],
      expert:["expert","freeride","hors piste","hors-piste","off piste","noir","noires","pistes noires","poudreuse","engage","steep","couloir"]
    },
    groupe:{
      famille:["famille","familles","enfant","enfants","bebe","kids","garderie","poussette"],
      couple:["couple","en couple","romantique","amoureux","tete a tete","mon copain","ma copine","mon mari","ma femme"],
      amis:["ami","amis","entre amis","groupe d ami","pote","potes","bande"],
      solo:["solo","seul","seule","tout seul","je pars seul"]
    },
    ambiance:{
      famille:["famille","familial","enfant","enfants"],
      festif:["festif","fete","apres ski","apres-ski","party","soiree","animee","animation","animations","vie nocturne"],
      luxe:["luxe","chic","prestige","haut de gamme"],
      nature:["nature","tranquille","calme","authentique","paisible","depaysant","sauvage","reculee","peu de monde","pas trop de monde","randonnee","randonnees","balade","balades","ballade","ballades","rando","randos","foret","prairie"],
      village:["village","authentique","traditionnel","typique","petit village","petite station","tradition","charme","charmant"]
    },
    massif:{
      "Alpes du Nord":["alpes du nord","tarentaise","savoie","haute savoie","haute-savoie","mont blanc","mont-blanc","beaufortain","maurienne","bauges","chablais","val d isere","tignes","chamonix","la plagne","les arcs","3 vallees","trois vallees","meribel","courchevel","val thorens","espace killy","paradiski","portes du soleil"],
      "Alpes du Sud":["alpes du sud","alpes-maritimes","alpes maritimes","hautes-alpes","hautes alpes","alpes de haute provence","provence","ubaye","queyras","briancon","isola","auron","serre chevalier","vars","risoul","orcieres","devoluy"],
      "Pyrénées":["pyrenees","pyrenee","pyrennees","catalan","pays basque","basque","ariege","hautes pyrenees","tourmalet","peyragudes","saint lary","luchon","cauterets","bareges","la mongie","formigueres","font romeu","ax 3 domaines","piau"],
      "Vosges":["vosges","vosgienne","gerardmer","la bresse","schlucht"],
      "Jura":["jura","jurassien","metabief","les rousses"],
      "Massif Central":["massif central","auvergne","cantal","puy de dome","sancy","lioran","super besse","besse","le mont-dore","le mont dore","mezenc"]
    },
    priorite:{
      neige:["neige","enneigement","altitude","haute altitude","poudreuse","glacier","neige garantie","neige sure"],
      ambiance:["ambiance","animation","apres ski","apres-ski","festif","vie nocturne"],
      nature:["nature","calme","tranquille","randonnee","balades","balade","foret","authentique","paisible"],
      domaine:["grand domaine","vaste domaine","beaucoup de pistes","grande etendue","etendu","etendue","immense","assez grand","tres grand","grands domaines"]
    },
    horsSki:{
      restaurants:["restaurant","restaurants","gastronomie","gastronomique","bonne table","bonnes tables","chef"],
      spa:["spa","sauna","jacuzzi","bien etre","bien-etre","massage","massages","hammam","wellness","thermal","thermes"],
      shopping:["shopping","boutique","boutiques","magasins"]
    }
  };

  function extractNumbers(text){
    const t = nrm(text); const out = {};
    let m = t.match(/(?:moins de|sous|en dessous de|max(?:imum)?|pas plus de|pas plus haute? que|inferieure? a|jusqu a|jusqu'a)\\s*(\\d{3,4})\\s*m?(?:[\\u00e8\\u00e9]tres?)?/);
    if(m) out.altMax = parseInt(m[1],10);
    if(/pas trop haut|pas trop haute|altitude basse|basse altitude/.test(t)) out.altMax = Math.min(out.altMax||9999, 1500);
    if(/(?:^|\\s)haute? altitude|en altitude|haute montagne/.test(t) && !out.altMax) out.altMin = 1800;
    m = t.match(/(?:moins de|sous|max(?:imum)?|inferieur a)\\s*(\\d{2,3})\\s*(?:\\u20ac|euros?|e\\b)/);
    if(m) out.forfaitMax = parseInt(m[1],10);
    m = t.match(/(?:plus de|au moins|minimum|au minimum)\\s*(\\d{2,4})\\s*(?:km|kilom)/);
    if(m) out.kmMin = parseInt(m[1],10);
    if(/grand domaine|vaste domaine|assez grand|tres grand|enorme/.test(t) && !out.kmMin) out.kmMin = 80;
    if(/petit domaine|petite station|domaine modeste|domaine reduit/.test(t)) out.kmMax = 50;
    return out;
  }

  function detectCategories(text){
    const t = " "+nrm(text)+" ";
    const out = {budget:null,niveau:null,groupe:null,ambiance:[],massif:null,priorite:[],horsSki:[]};
    function hitAny(g,k){const w = KW[g][k]; for(let i=0;i<w.length;i++){if(t.indexOf(w[i])>-1) return true;} return false;}
    if(hitAny("budget","eco")) out.budget="eco";
    else if(hitAny("budget","luxe")) out.budget="luxe";
    if(hitAny("niveau","expert")) out.niveau="expert";
    else if(hitAny("niveau","avance")) out.niveau="avance";
    else if(hitAny("niveau","debutant")) out.niveau="debutant";
    else if(hitAny("niveau","intermediaire")) out.niveau="intermediaire";
    if(hitAny("groupe","famille")) out.groupe="famille";
    else if(hitAny("groupe","couple")) out.groupe="couple";
    else if(hitAny("groupe","amis")) out.groupe="amis";
    else if(hitAny("groupe","solo")) out.groupe="solo";
    ["famille","festif","luxe","nature","village"].forEach(k=>{if(hitAny("ambiance",k)) out.ambiance.push(k);});
    ["Alpes du Nord","Alpes du Sud","Pyr\\u00e9n\\u00e9es","Vosges","Jura","Massif Central"].forEach(m=>{if(!out.massif && hitAny("massif",m)) out.massif=m;});
    ["neige","ambiance","nature","domaine"].forEach(k=>{if(hitAny("priorite",k)) out.priorite.push(k);});
    ["restaurants","spa","shopping"].forEach(k=>{if(hitAny("horsSki",k)) out.horsSki.push(k);});
    return out;
  }

  function scoreStation(s, c, n){
    let sc = (s.score||0)*15;
    const reasons = [];
    if(c.budget==="eco"){if(s.forfait<=25){sc+=40;reasons.push("forfait "+s.forfait+"\\u20ac");}else if(s.forfait<=35) sc+=15; else sc -= (s.forfait-35)*2;}
    if(c.budget==="luxe"){if(s.amb && s.amb.indexOf("luxe")>-1){sc+=35;reasons.push("ambiance luxe");} if(s.forfait>=55) sc+=10;}
    if(n.forfaitMax && s.forfait<=n.forfaitMax) sc+=20;
    else if(n.forfaitMax && s.forfait>n.forfaitMax) sc-=30;
    if(n.altMax && s.alt_min<=n.altMax){sc+=25; reasons.push("village \\u00e0 "+s.alt_min+"m");}
    else if(n.altMax && s.alt_min>n.altMax) sc-=40;
    if(n.altMin && s.alt_max>=n.altMin){sc+=15; reasons.push("sommet "+s.alt_max+"m");}
    if(c.niveau && s.niv && s.niv.indexOf(c.niveau)>-1){sc+=30; reasons.push("niveau "+c.niveau+" OK");}
    if(c.niveau==="debutant" && s.pistes && (s.pistes.v||0)>=8){sc+=20; reasons.push(s.pistes.v+" pistes vertes");}
    if(c.niveau==="expert" && s.tags && s.tags.indexOf("rider")>-1){sc+=25; reasons.push("terrain freeride");}
    if(c.groupe==="famille"){
      if(s.amb && s.amb.indexOf("famille")>-1){sc+=30; reasons.push("ambiance famille");}
      if(s.equip && s.equip.indexOf("garderie")>-1){sc+=20; reasons.push("garderie");}
    }
    if(c.groupe==="amis" && s.amb && s.amb.indexOf("festif")>-1){sc+=25; reasons.push("apr\\u00e8s-ski anim\\u00e9");}
    if(c.groupe==="couple" && s.amb && s.amb.indexOf("village")>-1){sc+=20; reasons.push("village charmant");}
    (c.ambiance||[]).forEach(a=>{
      if(s.amb && s.amb.indexOf(a)>-1) sc+=15;
      if(a==="nature" && s.alt_min<=1500){sc+=10;}
    });
    if(c.massif && s.massif===c.massif){sc+=40; reasons.push(c.massif);}
    else if(c.massif && s.massif!==c.massif) sc-=30;
    (c.priorite||[]).forEach(p=>{
      if(p==="neige" && s.alt_max>=2200) sc+=20;
      if(p==="neige" && s.alt_max>=2700) sc+=10;
      if(p==="domaine" && s.km>=100) sc+=15;
      if(p==="domaine" && s.km>=200){sc+=15; reasons.push(s.km+" km de pistes");}
      if(p==="ambiance" && s.amb && s.amb.indexOf("festif")>-1) sc+=20;
      if(p==="nature" && s.amb && (s.amb.indexOf("nature")>-1 || s.amb.indexOf("village")>-1)) sc+=20;
    });
    if(n.kmMin && s.km>=n.kmMin){sc+=15; reasons.push(s.km+" km");}
    if(n.kmMin && s.km<n.kmMin) sc-=25;
    if(n.kmMax && s.km<=n.kmMax) sc+=10;
    (c.horsSki||[]).forEach(h=>{
      if(s.equip && s.equip.indexOf(h)>-1){sc+=15; reasons.push(h);}
      if(h==="spa" && s.amb && s.amb.indexOf("luxe")>-1) sc+=10;
    });
    return {score: sc, reasons: reasons.slice(0,4)};
  }

  window.iaParseQuery = function(text){return {categories: detectCategories(text), numbers: extractNumbers(text), raw: text};};
  window.iaSearchStations = function(text, opts){
    opts = opts || {}; const limit = opts.limit || 5;
    const source = opts.source || window.DATA || (typeof DATA!=="undefined"?DATA:[]);
    const parsed = window.iaParseQuery(text);
    const scored = source.map(s=>{const r=scoreStation(s,parsed.categories,parsed.numbers); return {station:s, score:r.score, reasons:r.reasons};}).sort((a,b)=>b.score-a.score);
    const c=parsed.categories;
    const hasCriteria = c.budget||c.niveau||c.groupe||c.massif||(c.ambiance&&c.ambiance.length)||(c.priorite&&c.priorite.length)||(c.horsSki&&c.horsSki.length)||parsed.numbers.altMax||parsed.numbers.forfaitMax||parsed.numbers.kmMin;
    return {results: scored.slice(0, limit), parsed: parsed, noCriteria: !hasCriteria};
  };
  window.iaIntroSentence = function(parsed){
    const c=parsed.categories, n=parsed.numbers; const p=[];
    if(c.groupe==="famille") p.push("pour partir en famille");
    else if(c.groupe==="amis") p.push("entre amis");
    else if(c.groupe==="couple") p.push("en couple");
    else if(c.groupe==="solo") p.push("pour partir solo");
    if(c.niveau) p.push("niveau "+c.niveau);
    if(c.budget==="eco") p.push("avec petit budget");
    if(c.budget==="luxe") p.push("haut de gamme");
    if(n.forfaitMax) p.push("forfait sous "+n.forfaitMax+"\\u20ac");
    if(n.altMax) p.push("village sous "+n.altMax+"m");
    if(c.massif) p.push("dans les "+c.massif);
    if((c.priorite||[]).indexOf("domaine")>-1) p.push("grand domaine");
    if((c.priorite||[]).indexOf("nature")>-1) p.push("proche de la nature");
    if((c.horsSki||[]).indexOf("spa")>-1) p.push("avec spa");
    if((c.horsSki||[]).indexOf("restaurants")>-1) p.push("bonne table");
    return p.length ? "Tu cherches : "+p.join(", ")+"." : "";
  };
})();

/* ── UI du conseiller IA ─────────────────────────────────────────────── */
function openIaPanel(){
  document.getElementById("iaPanelOverlay").classList.add("open");
  document.body.style.overflow="hidden";
  setTimeout(()=>{ var t=document.getElementById("iaQuery"); if(t) t.focus(); }, 250);
}
function closeIaPanel(){
  document.getElementById("iaPanelOverlay").classList.remove("open");
  document.body.style.overflow="";
}
document.getElementById("iaPanelOverlay").addEventListener("click", e=>{
  if(e.target===document.getElementById("iaPanelOverlay")) closeIaPanel();
});

// Suggestions cliquables : pré-remplissent et lancent
document.querySelectorAll(".ia-sugg").forEach(btn=>{
  btn.addEventListener("click", ()=>{
    document.getElementById("iaQuery").value = btn.getAttribute("data-q");
    iaSearch();
  });
});

// Enter dans le textarea (sans Shift) = lancer la recherche
document.getElementById("iaQuery").addEventListener("keydown", e=>{
  if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); iaSearch(); }
});

async function iaSearch(){
  var q = (document.getElementById("iaQuery").value||"").trim();
  if(!q){ document.getElementById("iaQuery").focus(); return; }

  document.getElementById("iaInputWrap").style.display = "none";
  document.getElementById("iaIntro").style.display = "none";
  document.getElementById("iaResults").classList.remove("show");
  document.getElementById("iaLoading").classList.add("show");
  document.getElementById("iaPanel").scrollTop = 0;

  await new Promise(r=>setTimeout(r, 800)); // micro-loader UX

  var search = window.iaSearchStations(q, {limit: 5});
  var resHtml = "";

  if(search.noCriteria){
    resHtml += '<div class="ia-results-warn">🤔 Je n\\'ai pas réussi à identifier de critère précis dans ta demande. Essaie d\\'évoquer un budget, un niveau, un massif, une ambiance, ou clique sur une inspiration ci-dessous.</div>';
  }

  var intro = window.iaIntroSentence(search.parsed);
  if(intro && !search.noCriteria){
    resHtml += '<div class="ia-results-header"><div class="ia-results-intro">Voici tes 5 stations idéales</div><div class="ia-results-sub">'+intro+'</div></div>';
  } else if(!search.noCriteria){
    resHtml += '<div class="ia-results-header"><div class="ia-results-intro">Voici tes 5 stations idéales</div></div>';
  }

  search.results.forEach((r, i)=>{
    var s = r.station;
    var reasonsHtml = (r.reasons||[]).map(x=>'<span class="ia-result-reason">'+x+'</span>').join("");
    resHtml += '<div class="ia-result-card" onclick="iaGoStation('+s.id+')">' +
      '<div class="ia-result-rank">'+(i+1)+'</div>' +
      '<div class="ia-result-body">' +
        '<div class="ia-result-name">'+s.name+'</div>' +
        '<div class="ia-result-meta">'+(s.massif||'')+' · '+(s.region||'')+'</div>' +
        (reasonsHtml ? '<div class="ia-result-reasons">'+reasonsHtml+'</div>' : '') +
        '<div class="ia-result-stats">'+
          '<span>🏔️ '+s.alt_min+'-'+s.alt_max+'m</span>'+
          '<span>📏 '+s.km+' km</span>'+
          '<span>🎫 '+s.forfait+'€</span>'+
          '<span>⭐ '+s.score+'</span>'+
        '</div>'+
      '</div>'+
    '</div>';
  });

  resHtml += '<div class="ia-result-foot">' +
    '<button class="ia-foot-btn" onclick="iaReset()">↻ Nouvelle recherche</button>' +
    '<button class="ia-foot-btn primary" onclick="closeIaPanel()">Voir tout le grid</button>' +
    '</div>';

  document.getElementById("iaLoading").classList.remove("show");
  document.getElementById("iaResults").innerHTML = resHtml;
  document.getElementById("iaResults").classList.add("show");
  document.getElementById("iaPanel").scrollTop = 0;
}

function iaReset(){
  document.getElementById("iaQuery").value = "";
  document.getElementById("iaResults").classList.remove("show");
  document.getElementById("iaResults").innerHTML = "";
  document.getElementById("iaInputWrap").style.display = "";
  document.getElementById("iaIntro").style.display = "";
  document.getElementById("iaPanel").scrollTop = 0;
  setTimeout(()=>{ document.getElementById("iaQuery").focus(); }, 50);
}

function iaGoStation(id){
  closeIaPanel();
  window.location.href = "recherche.html?station=" + id;
}'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    fp = root / "recherche.html"
    if not fp.exists():
        print(f"❌ {fp} introuvable")
        return

    content = fp.read_text(encoding="utf-8")
    original_size = len(content)

    # 1. Remplacer le panneau HTML
    panel_idx = content.find('iaPanelOverlay')
    panel_start = content.rfind('<div class="ia-panel-overlay"', 0, panel_idx)
    if panel_start < 0:
        print("❌ Panneau IA introuvable")
        return
    depth = 0
    i = panel_start
    while i < len(content):
        if content[i:i+4] == '<div':
            depth += 1; i += 4
        elif content[i:i+6] == '</div>':
            depth -= 1; i += 6
            if depth == 0: break
        else: i += 1
    panel_end = i

    content = content[:panel_start] + NEW_PANEL_HTML + content[panel_end:]
    print(f"✓ Panneau HTML remplacé ({panel_end - panel_start} → {len(NEW_PANEL_HTML)} chars)")

    # 2. Injecter le CSS supplémentaire à la fin du <style> principal
    # On cherche la première occurrence de "</style>" après le début
    style_end = content.find('</style>')
    if style_end > 0 and EXTRA_CSS not in content:
        content = content[:style_end] + EXTRA_CSS + content[style_end:]
        print(f"✓ CSS supplémentaire injecté ({len(EXTRA_CSS)} chars)")

    # 3. Remplacer le JS du conseiller IA
    # Localiser le début : après "// ══ CONSEILLER IA COMPLET ══" et après IA_STATIONS = [...];\n
    js_start = content.find('var iaAns = {}, iaStep = 0;')
    if js_start < 0:
        print("❌ JS conseiller IA introuvable")
        return
    # Le JS finit avant le prochain </script>
    js_end = content.find('</script>', js_start)

    content = content[:js_start] + NEW_JS + '\n' + content[js_end:]
    print(f"✓ JS conseiller IA remplacé ({js_end - js_start} → {len(NEW_JS)} chars)")

    fp.write_text(content, encoding="utf-8")
    new_size = len(content)
    print(f"\n📄 {fp.name} : {original_size:,} → {new_size:,} octets ({new_size-original_size:+,})")


if __name__ == "__main__":
    main()
