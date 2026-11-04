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
    '.sfp-row{overflow:hidden;padding:2px 0 4px}' +
    '.sfp-track{display:flex;gap:10px;width:max-content}' +
    '.sfp-row.sfp-scroll .sfp-track{animation:sfpmove var(--sfp-dur,30s) linear infinite}' +
    '.sfp-row.sfp-scroll:hover .sfp-track,.sfp-row.sfp-scroll.sfp-pause .sfp-track{animation-play-state:paused}' +
    '@keyframes sfpmove{from{transform:translateX(0)}to{transform:translateX(calc(-50% - 5px))}}' +
    '@media(prefers-reduced-motion:reduce){.sfp-row.sfp-scroll .sfp-track{animation:none}.sfp-row{overflow-x:auto}}' +
    '.sfp-chip{flex:0 0 auto;box-sizing:border-box;width:236px;height:68px;display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:14px;padding:0 12px 0 8px;text-decoration:none;color:#fff;overflow:hidden}' +
    '.sfp-ph{width:50px;height:50px;border-radius:50%;background-size:cover;background-position:center;border:2px solid #E4C777;flex-shrink:0;background-color:#1a5a8a}' +
    '.sfp-t{min-width:0;display:block}' +
    '.sfp-n{display:block;font-weight:800;font-size:.86rem;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.sfp-r{display:block;font-size:.68rem;line-height:1.3;opacity:.78;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.sfp-pill{display:inline-flex;align-items:center;gap:8px;margin-top:10px;margin-left:8px;padding:8px 16px;background:linear-gradient(135deg,#F0D78C,#C9982F);color:#0B2942;border-radius:30px;font-weight:900;font-size:.8rem;text-decoration:none;box-shadow:0 3px 10px rgba(0,0,0,.25)}' +
    '.sfp-pill img{width:22px;height:22px}';
  document.head.appendChild(css);

  function lines(x) {
    // 3 lignes : nom / grand domaine ou massif / département-région
    var parts = String(x.r || '').split(/\s*,\s*/).filter(Boolean);
    if (parts.length < 2 && x.m && x.m !== parts[0]) parts.unshift(x.m);
    return [parts[0] || '', parts[1] || ''];
  }
  function chips() {
    return D.list.map(function (x) {
      var ph = x.p ? (/^(https?:)?\//.test(x.p) ? x.p : '/' + x.p.replace(/^\.?\//, '')) : '';
      var l = lines(x);
      return '<a class="sfp-chip" href="' + esc(x.u) + '"><span class="sfp-ph" style="background-image:url(\'' + esc(ph) + '\')"></span>' +
        '<span class="sfp-t"><span class="sfp-n">' + esc(x.n) + '</span><span class="sfp-r">' + esc(l[0]) + '</span><span class="sfp-r">' + esc(l[1]) + '</span></span></a>';
    }).join('');
  }
  // Bandeau défilant quand les vignettes dépassent la largeur disponible
  function setupScroll(box) {
    var row = box.querySelector('.sfp-row'), track = box.querySelector('.sfp-track');
    if (!row || !track) return;
    if (track.scrollWidth <= row.clientWidth) return;
    track.innerHTML = track.innerHTML + track.innerHTML;
    row.classList.add('sfp-scroll');
    row.style.setProperty('--sfp-dur', Math.max(18, D.list.length * 6) + 's');
    row.addEventListener('touchstart', function () { row.classList.add('sfp-pause'); }, { passive: true });
    row.addEventListener('touchend', function () { setTimeout(function () { row.classList.remove('sfp-pause'); }, 2500); }, { passive: true });
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
      '<a class="sfp-all" href="/partenaires.html">Voir toutes →</a></div><div class="sfp-row"><div class="sfp-track">' + chips() + '</div></div></div>';
    sep.parentNode.insertBefore(s, sep);
    setupScroll(s);
  }

  function onSearch() {
    var slot = document.getElementById('sfPartnersSlot');
    if (!slot) return;
    slot.innerHTML = '<a class="sfp-pill" href="/partenaires.html"><img src="/img/badge-partenaire-mini.svg" alt="">Stations partenaires</a>';
  }

  function go() { onIndex(); onSearch(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
})();
