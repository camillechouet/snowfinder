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


/* SnowFinder — colonnes latérales partenaires (accueil, grands écrans).
   S'affichent à gauche et à droite du contenu, à partir de « À la une » jusqu'au pied de page, et restent
   visibles quand on descend. Masquées automatiquement quand il n'y a pas assez de place (écrans < ~1500 px, téléphones).
   Données : liste « colonnes » de /partenaires.json (voir _aide). Aperçu forcé : ajouter ?colonnes=1 à l'adresse. */
(function () {
  try {
    var EN = String(document.documentElement.getAttribute('lang') || 'fr').toLowerCase().indexOf('en') === 0;
    var forced = /[?&]colonnes=1/.test(location.search);
    var GAP = 14, MIN_W = 128, MAX_W = 300;

    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function safeUrl(u) { return /^https?:\/\//i.test(String(u || '')) ? u : ''; }
    function imgUrl(u) { u = String(u || ''); if (!u) return ''; return /^(https?:)?\//.test(u) ? u : '/' + u.replace(/^\.?\//, ''); }

    // Pages équipées : « key » (pour le champ "pages" de partenaires.json), point d'ancrage du haut des colonnes,
    // bloc de contenu qui sert à mesurer les marges, et largeur imposée éventuelle (recherche).
    var PATH = location.pathname.replace(/^\/en\//, '/').replace(/\/index\.html$/, '/');
    var PAGES = [
      { re: /^\/$/, key: 'accueil' },
      { re: /^\/recherche\.html$/, key: 'recherche', top: '.layout', box: '.layout', fixed: 1240 },
      { re: /^\/comparatifs\/tous-les-comparatifs\.html$/, key: 'duels', top: '.page', box: '.page' },
      { re: /^\/articles\/toutes-les-actus\.html$/, key: 'actus', top: '.wrap', box: '.wrap' },
      { re: /^\/station-du-moment\/toutes-les-stations-du-moment\.html$/, key: 'moment', top: '.wrap', box: '.wrap' },
      { re: /^\/enneigement\.html$/, key: 'meteo', top: '.snow-hero', box: '.snow-hero-inner', fixed: 900 },
      { re: /^\/hebergement\.html$/, key: 'hebergement', top: '.heb-hero', box: '.heb-hero-inner', fixed: 900 },
      { re: /^\/comparateur\.html$/, key: 'comparateur', top: '.hero', box: '.container', fixed: 900 }
    ];
    var PAGE = null;
    PAGES.forEach(function (p) { if (!PAGE && p.re.test(PATH)) PAGE = p; });
    if (!PAGE) return;

    // Séparateur « À la une » (FR) / « Headlines » (EN) : accueil uniquement
    function findSep() {
      if (PAGE.top) return document.querySelector(PAGE.top);
      var els = document.querySelectorAll('div');
      for (var i = 0; i < els.length; i++) {
        if (els[i].children.length === 0) {
          var t = els[i].textContent.trim();
          if (t === 'À la une' || t === 'Headlines') return els[i].parentNode;
        }
      }
      return null;
    }

    function pick(data) {
      var today = new Date(); today.setHours(0, 0, 0, 0);
      var iso = today.getFullYear() + '-' + ('0' + (today.getMonth() + 1)).slice(-2) + '-' + ('0' + today.getDate()).slice(-2);
      var list = (data && data.colonnes || []).filter(function (o) {
        if (!o || o.actif === false) return false;
        if (o.debut && iso < o.debut) return false;
        if (o.fin && iso > o.fin) return false;
        if (o.pages && o.pages.length && o.pages.indexOf(PAGE.key) < 0) return false;
        return !!(o.titre && safeUrl(o.lien));
      });
      list.sort(function (a, b) { return (b.priorite || 0) - (a.priorite || 0); });
      var left = null, right = null, both = [];
      list.forEach(function (o) {
        var c = o.cote || 'les-deux';
        if (c === 'gauche' && !left) left = o;
        else if (c === 'droite' && !right) right = o;
        else if (c === 'les-deux') both.push(o);
      });
      both.forEach(function (o) { if (!left) left = o; else if (!right && o !== left) right = o; });
      if (!right && left && (left.cote || 'les-deux') === 'les-deux') right = left; // une seule offre « les deux côtés » : répétée
      if (!left && right && (right.cote || 'les-deux') === 'les-deux') left = right;
      return { left: left, right: right };
    }

    function cardHtml(o) {
      var e = (EN && o.en) || {};
      var titre = e.titre || o.titre, texte = e.texte || o.texte, cta = e.cta || o.cta || (EN ? 'Discover' : 'Découvrir');
      var label = o.label || (EN ? 'Partner' : 'Partenaire');
      if (EN) label = ({ 'Partenaire': 'Partner', 'Bon plan': 'Deal', 'Publicité': 'Ad' })[label] || label;
      var img = imgUrl(o.image);
      return '<div class="sfc-card"><a class="sfc-link" href="' + esc(safeUrl(o.lien)) + '" target="_blank" rel="sponsored nofollow noopener" data-sfc="' + esc(o.id || o.partenaire || titre) + '">' +
        (img ? '<img class="sfc-img" src="' + esc(img) + '" alt="" loading="lazy">' : '') +
        '<span class="sfc-shade"></span>' +
        '<span class="sfc-badge"><img src="/img/badge-partenaire-mini.svg" alt="">' + esc(label) + '</span>' +
        '<span class="sfc-body">' +
        '<span class="sfc-h">' + esc(titre) + '</span>' +
        (texte ? '<span class="sfc-p">' + esc(texte) + '</span>' : '') +
        (o.partenaire ? '<span class="sfc-by">' + esc(o.partenaire) + '</span>' : '') +
        '<span class="sfc-cta">' + esc(cta) + ' →</span></span></a></div>';
    }

    function mount(sel) {
      var sep = findSep();
      if (!sep || !(sel.left || sel.right)) return;
      if (document.getElementById('sfc-left') || document.getElementById('sfc-right')) return;

      var css = document.createElement('style');
      css.textContent =
        '.sfc-rail{position:absolute;z-index:30;box-sizing:border-box;font-family:"DM Sans",-apple-system,sans-serif;display:none}' +
        '.sfc-rail *{box-sizing:border-box}' +
        '.sfc-card{position:sticky;top:80px;height:calc(100vh - 215px);max-height:min(880px,100%);border-radius:20px;overflow:hidden;background:linear-gradient(160deg,#0B2942 0%,#1a5a8a 100%);box-shadow:0 14px 38px rgba(13,34,64,.28);border:1px solid rgba(255,255,255,.35)}' +
        '.sfc-link{position:relative;display:block;height:100%;text-decoration:none!important;color:#fff}' +
        '.sfc-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:transform .8s ease}' +
        '.sfc-link:hover .sfc-img{transform:scale(1.05)}' +
        '.sfc-shade{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(11,41,66,.55) 0%,rgba(11,41,66,0) 22%,rgba(11,41,66,.12) 45%,rgba(11,41,66,.88) 78%,rgba(11,41,66,.96) 100%)}' +
        '.sfc-badge{position:absolute;top:14px;left:14px;display:inline-flex;align-items:center;gap:6px;font-size:.66rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#0B2942;background:linear-gradient(135deg,#F0D78C,#C9982F);border-radius:20px;padding:5px 11px 5px 7px;box-shadow:0 3px 10px rgba(0,0,0,.3)}' +
        '.sfc-badge img{width:18px;height:18px}' +
        '.sfc-body{position:absolute;left:0;right:0;bottom:0;padding:0 18px 20px;display:block}' +
        '.sfc-h{display:block;font-family:"DM Serif Display",serif;font-size:1.3rem;line-height:1.15;margin:0 0 9px;text-shadow:0 2px 10px rgba(0,0,0,.45)}' +
        '.sfc-p{display:-webkit-box;-webkit-line-clamp:6;-webkit-box-orient:vertical;overflow:hidden;font-size:.84rem;line-height:1.45;margin:0 0 10px;color:rgba(255,255,255,.92)}' +
        '.sfc-by{display:block;font-size:.7rem;letter-spacing:.04em;text-transform:uppercase;color:#F0D78C;margin:0 0 13px;font-weight:700}' +
        '.sfc-cta{display:block;text-align:center;background:linear-gradient(135deg,#F0D78C,#C9982F);color:#0B2942;font-weight:900;font-size:.86rem;padding:11px 8px;border-radius:30px;box-shadow:0 5px 16px rgba(0,0,0,.35)}' +
        '.sfc-link:hover .sfc-cta{filter:brightness(1.08)}' +
        '.sfc-l .sfc-h{font-size:1.75rem;margin-bottom:12px}.sfc-l .sfc-p{font-size:.98rem;margin-bottom:14px}.sfc-l .sfc-body{padding:0 24px 26px}.sfc-l .sfc-cta{font-size:.98rem;padding:13px 10px}.sfc-l .sfc-badge{top:18px;left:18px;font-size:.72rem}' +
        '.sfc-m .sfc-h{font-size:1.45rem}.sfc-m .sfc-p{font-size:.9rem}' +
        '.sfc-s .sfc-h{font-size:1.12rem}.sfc-s .sfc-p{font-size:.78rem;-webkit-line-clamp:5}.sfc-s .sfc-body{padding:0 13px 16px}.sfc-s .sfc-cta{font-size:.78rem;padding:10px 6px}.sfc-s .sfc-badge{top:11px;left:11px;font-size:.58rem}' +
        '.sfc-inl{display:none;position:relative;box-sizing:border-box;margin:14px 14px 18px;border-radius:18px;overflow:hidden;height:210px;background:linear-gradient(160deg,#0B2942,#1a5a8a);box-shadow:0 8px 24px rgba(13,34,64,.25);border:1px solid rgba(255,255,255,.35);font-family:"DM Sans",-apple-system,sans-serif}' +
        '.sfc-inl *{box-sizing:border-box}' +
        '.sfc-inl .sfc-card{position:relative;top:auto;height:100%;max-height:none;border-radius:0;border:0;box-shadow:none}' +
        '.sfc-inl .sfc-h{font-size:1.2rem;margin-bottom:5px}.sfc-inl .sfc-p{font-size:.78rem;-webkit-line-clamp:2;margin-bottom:6px}.sfc-inl .sfc-by{margin-bottom:9px;font-size:.62rem}.sfc-inl .sfc-body{padding:0 16px 14px}.sfc-inl .sfc-cta{font-size:.82rem;padding:9px 8px}.sfc-inl .sfc-badge{top:10px;left:10px;font-size:.58rem}' +
        '.sfc-inl .sfc-shade{background:linear-gradient(to bottom,rgba(11,41,66,.5) 0%,rgba(11,41,66,0) 25%,rgba(11,41,66,.25) 45%,rgba(11,41,66,.92) 85%)}' +
        'html.sfc-on .layout{max-width:1240px!important}html.sfc-on{--filter-w:225px!important}' +
        '@media print{.sfc-rail{display:none!important}}';
      document.head.appendChild(css);

      var L = document.createElement('aside'), R = document.createElement('aside');
      L.id = 'sfc-left'; R.id = 'sfc-right';
      L.className = R.className = 'sfc-rail';
      L.setAttribute('aria-label', EN ? 'Partner' : 'Partenaire'); R.setAttribute('aria-label', EN ? 'Partner' : 'Partenaire');
      if (sel.left) L.innerHTML = cardHtml(sel.left);
      if (sel.right) R.innerHTML = cardHtml(sel.right);
      document.body.appendChild(L); document.body.appendChild(R);
      var I = document.createElement('aside'); I.id = 'sfc-inline'; I.className = 'sfc-inl';
      I.setAttribute('aria-label', EN ? 'Partner' : 'Partenaire');
      var one = sel.left || sel.right; I.innerHTML = cardHtml(one);
      if (sep.parentNode) sep.parentNode.insertBefore(I, sep);

      document.addEventListener('click', function (ev) {
        var a = ev.target && ev.target.closest ? ev.target.closest('.sfc-link') : null;
        if (a && typeof window.gtag === 'function') {
          try { window.gtag('event', 'colonne_partenaire_clic', { partenaire: a.getAttribute('data-sfc') }); } catch (e) { }
        }
      });

      function layout() {
        var vw = document.documentElement.clientWidth;
        var cl = (vw - 1200) / 2, cr = cl + 1200; // repli : contenu de 1200 px centré
        if (PAGE.fixed) { cl = (vw - PAGE.fixed) / 2; cr = cl + PAGE.fixed; }
        else {
          var sec = document.querySelector(PAGE.box || '.section');
          if (sec) { var r = sec.getBoundingClientRect(); if (r.width > 300) { cl = r.left; cr = r.right; } }
        }
        var phone = vw < 760; // téléphone : un encart en ligne à la place des colonnes
        I.style.display = phone ? 'block' : 'none';
        if (phone) { L.style.display = R.style.display = 'none'; document.documentElement.classList.remove('sfc-on'); return; }
        var margin = Math.min(cl, vw - cr);
        var w = Math.min(MAX_W, Math.floor(margin - GAP - 8));
        var sy = window.pageYOffset || 0;
        var top = sep.getBoundingClientRect().top + sy;
        var foot = document.querySelector('footer');
        var end = foot ? foot.getBoundingClientRect().top + sy : document.documentElement.scrollHeight;
        var h = Math.max(0, end - top - 24);
        if (w < MIN_W || h < 320) { L.style.display = R.style.display = 'none'; document.documentElement.classList.remove('sfc-on'); return; }
        if (PAGE.key === 'recherche') document.documentElement.classList.add('sfc-on');
        [[L, sel.left, Math.round(cl - GAP - w)], [R, sel.right, Math.round(cr + GAP)]].forEach(function (p) {
          var el = p[0];
          el.style.display = p[1] ? 'block' : 'none';
          el.style.width = w + 'px';
          el.className = 'sfc-rail ' + (w >= 260 ? 'sfc-l' : (w >= 200 ? 'sfc-m' : 'sfc-s'));
          el.style.left = p[2] + 'px';
          el.style.top = Math.round(top) + 'px';
          el.style.height = Math.round(h) + 'px';
        });
      }
      layout();
      window.addEventListener('load', layout);
      var t; window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(layout, 120); });
      if (window.ResizeObserver) { try { new ResizeObserver(function () { clearTimeout(t); t = setTimeout(layout, 120); }).observe(document.body); } catch (e) { } }
      setTimeout(layout, 1500); setTimeout(layout, 4000);
    }

    function start() {
      if (!findSep()) return; // pas l'accueil
      var v = Math.floor(Date.now() / 3600000);
      fetch('/partenaires.json?v=' + v, { credentials: 'omit' })
        .then(function (r) { return r.ok ? r.json() : { colonnes: [] }; })
        .catch(function () { return { colonnes: [] }; })
        .then(function (d) {
          var sel = pick(d);
          if (!sel.left && !sel.right && forced) {
            var ex = { actif: true, label: EN ? 'Preview' : 'Exemple', titre: EN ? 'Your resort here' : 'Votre station ici', texte: EN ? 'Preview of a partner column.' : 'Aperçu d\'une colonne partenaire.', cta: EN ? 'Discover' : 'Découvrir', lien: 'https://snowfinder.fr/partenaires.html' };
            sel = { left: ex, right: ex };
          }
          mount(sel);
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
  } catch (e) { /* une colonne ne doit jamais casser la page */ }
})();
