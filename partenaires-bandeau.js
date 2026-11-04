/* SnowFinder — bandeau « Stations partenaires » (accueil) + pastille (recherche).
   Données : /partenaires-data.js (généré par generate_stations.py à partir de PARTNER_STATIONS).
   Affichage : seulement si le nombre de partenaires >= min. Aperçu forcé : ajouter ?partenaires=1 à l'adresse. */
(function () {
  var D = window.SF_PARTNERS;
  if (!D || !D.list) return;
  var forced = /[?&]partenaires=1/.test(location.search);
  if (!forced && D.list.length < D.min) return;
  if (!D.list.length) return;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  var css = document.createElement('style');
  css.textContent =
    '.sfp-strip{max-width:860px;margin:26px auto 4px;padding:0 20px}' +
    '.sfp-box{background:linear-gradient(135deg,#0B2942 0%,#1a5a8a 100%);border-radius:18px;padding:16px 16px 14px;box-shadow:0 8px 28px rgba(13,34,64,.18);color:#fff}' +
    '.sfp-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}' +
    '.sfp-title{display:flex;align-items:center;gap:9px;font-family:"DM Serif Display",serif;font-size:1.08rem}' +
    '.sfp-title img{width:30px;height:30px;flex-shrink:0}' +
    '.sfp-all{font-size:.76rem;font-weight:800;color:#F0D78C;text-decoration:none;white-space:nowrap}' +
    '.sfp-row{display:flex;gap:10px;overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:4px;scrollbar-width:none}' +
    '.sfp-row::-webkit-scrollbar{display:none}' +
    '.sfp-chip{flex:0 0 auto;display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:14px;padding:7px 14px 7px 7px;text-decoration:none;color:#fff}' +
    '.sfp-ph{width:46px;height:46px;border-radius:50%;background-size:cover;background-position:center;border:2px solid #E4C777;flex-shrink:0;background-color:#1a5a8a}' +
    '.sfp-n{font-weight:800;font-size:.86rem;line-height:1.2;white-space:nowrap}' +
    '.sfp-r{font-size:.68rem;opacity:.75;white-space:nowrap}' +
    '.sfp-pill{display:inline-flex;align-items:center;gap:8px;margin-top:10px;margin-left:8px;padding:8px 16px;background:linear-gradient(135deg,#F0D78C,#C9982F);color:#0B2942;border-radius:30px;font-weight:900;font-size:.8rem;text-decoration:none;box-shadow:0 3px 10px rgba(0,0,0,.25)}' +
    '.sfp-pill img{width:22px;height:22px}';
  document.head.appendChild(css);

  function chips() {
    return D.list.map(function (x) {
      var ph = x.p ? (/^(https?:)?\//.test(x.p) ? x.p : '/' + x.p.replace(/^\.?\//, '')) : '';
      return '<a class="sfp-chip" href="' + esc(x.u) + '"><span class="sfp-ph" style="background-image:url(\'' + esc(ph) + '\')"></span>' +
        '<span><span class="sfp-n" style="display:block">' + esc(x.n) + '</span><span class="sfp-r">' + esc(x.r) + '</span></span></a>';
    }).join('');
  }

  function onIndex() {
    // Cherche le séparateur « À la une » et insère le bandeau juste avant (robuste aux mises à jour de la page).
    var els = document.querySelectorAll('div');
    var sep = null;
    for (var i = 0; i < els.length; i++) {
      if (els[i].children.length === 0 && els[i].textContent.trim() === 'À la une') { sep = els[i].parentNode; break; }
    }
    if (!sep || !sep.parentNode) return;
    var s = document.createElement('div');
    s.className = 'sfp-strip';
    s.innerHTML = '<div class="sfp-box"><div class="sfp-head"><div class="sfp-title"><img src="/img/badge-partenaire-mini.svg" alt="">Stations partenaires</div>' +
      '<a class="sfp-all" href="/partenaires.html">Voir toutes →</a></div><div class="sfp-row">' + chips() + '</div></div>';
    sep.parentNode.insertBefore(s, sep);
  }

  function onSearch() {
    var slot = document.getElementById('sfPartnersSlot');
    if (!slot) return;
    slot.innerHTML = '<a class="sfp-pill" href="/partenaires.html"><img src="/img/badge-partenaire-mini.svg" alt="">Stations partenaires</a>';
  }

  function go() { onIndex(); onSearch(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
