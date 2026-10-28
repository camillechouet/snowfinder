/* SnowFinder — encarts « Offres & bons plans »
 * Affiché sur : fiches stations (/stations/), articles (/articles/), duels (/comparatifs/), en FR et EN.
 * Contenu : offres partenaires du fichier /partenaires.json + liens Booking / Expedia (affiliation CJ)
 * repris des liens déjà présents dans la page. Rien à régler ici : tout se gère dans partenaires.json.
 */
(function () {
  "use strict";
  try {
    var EN = String(document.documentElement.getAttribute("lang") || "fr").toLowerCase().indexOf("en") === 0;
    var path = location.pathname.replace(/^\/en\//, "/");
    var kind = "";
    if (/^\/stations\/[^\/]+\.html$/.test(path)) kind = "station";
    else if (/^\/articles\/[^\/]+\.html$/.test(path) && !/toutes-les-actus/.test(path)) kind = "article";
    else if (/^\/comparatifs\/[^\/]+\.html$/.test(path) && !/tous-les-comparatifs/.test(path)) kind = "duel";
    if (!kind || document.getElementById("sfo-root")) return;

    var T = EN ? {
      book: "Book your stay", hotelsIn: "Hotels in ", booking: "Booking", expedia: "Expedia",
      aff: "Affiliate links — same price for you, no extra cost.", partner: "Partner", see: "See the offer",
      offers: "Offers & deals"
    } : {
      book: "Réserver votre séjour", hotelsIn: "Hôtels à ", booking: "Booking", expedia: "Expedia",
      aff: "Liens affiliés — prix identiques pour vous, sans frais supplémentaires.", partner: "Partenaire",
      see: "Voir l'offre", offers: "Offres & bons plans"
    };
    var ICONS = { "location-ski": "🎿", "forfait": "🎟️", "hebergement": "🏨", "bon-plan": "🔥", "station": "⛰️" };

    function norm(s) {
      return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
        .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    }
    function esc(s) {
      return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
    }
    function safeUrl(u) { return /^https?:\/\//i.test(String(u || "")) ? u : ""; }

    // ── Stations de la page ────────────────────────────────────────────────
    var slugs = [];
    if (kind === "station") {
      slugs = [path.replace(/^\/stations\//, "").replace(/\.html$/, "")];
    } else {
      var seen = {};
      [].forEach.call(document.querySelectorAll('a[href*="/stations/"]'), function (a) {
        var m = (a.getAttribute("href") || "").match(/\/stations\/([^\/?#]+)\.html/);
        if (m && !seen[m[1]]) { seen[m[1]] = 1; slugs.push(m[1]); }
      });
    }

    // Liens Booking / Expedia déjà présents dans la page (déjà en CJ, déjà en en-gb sur les pages EN).
    function cjLinks(slug, kindLink) {
      var host = kindLink === "bk" ? "tkqlhce.com" : "jdoqocy.com";
      var found = null;
      [].forEach.call(document.querySelectorAll("a[href*='" + host + "']"), function (a) {
        if (found) return;
        var h = a.getAttribute("href") || "";
        var m = h.match(/[?&]sid=([^&]+)/);
        if (m && /^comparatif-/.test(m[1]) && norm(m[1].replace(/^comparatif-/, "")) === slug) found = h;
      });
      if (!found) return "";
      return found.replace(/([?&]sid=)[^&]+/, "$1rail-" + kind + "-" + slug);
    }
    function nameOf(slug) {
      var a = document.querySelector("a[href*='tkqlhce.com'][href*='comparatif-" + slug + "']");
      if (a) {
        try {
          var url = decodeURIComponent((a.getAttribute("href").match(/[?&]url=([^&]+)/) || [])[1] || "");
          var ss = (url.match(/[?&]ss=([^&]+)/) || [])[1];
          if (ss) {
            ss = decodeURIComponent(ss).replace(/\+/g, " ").replace(/ ski (france|espagne|andorre|suisse|italie|allemagne|liechtenstein|autriche|slovenie)$/i, "");
            if (ss) return ss;
          }
        } catch (e) { }
      }
      return slug.split("-").map(function (w) { return w.charAt(0).toUpperCase() + w.slice(1); }).join(" ");
    }

    // ── CSS ────────────────────────────────────────────────────────────────
    var css = document.createElement("style");
    css.textContent =
      "#sfo-root{box-sizing:border-box;font-family:'DM Sans',-apple-system,sans-serif;color:var(--text,#22303e)}" +
      "#sfo-root *{box-sizing:border-box}" +
      ".sfo-title-h{font-size:.72rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--text-light,#8a97a3);margin:0 2px 8px}" +
      ".sfo-card{display:block;background:#fff;border:1px solid var(--border,#e3e9ee);border-radius:14px;overflow:hidden;margin-bottom:12px;box-shadow:0 4px 16px rgba(13,34,64,.09)}" +
      ".sfo-img{display:block;width:100%;height:120px;object-fit:cover}" +
      ".sfo-body{padding:12px 14px 14px}" +
      ".sfo-badge{display:inline-block;font-size:.62rem;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:#7a4a00;background:#ffe9b8;border-radius:20px;padding:3px 9px;margin-bottom:7px}" +
      ".sfo-h{font-family:'DM Serif Display',serif;font-size:1.02rem;line-height:1.25;margin:0 0 5px;color:var(--blue-dark,#1a5a8a)}" +
      ".sfo-p{font-size:.82rem;line-height:1.45;margin:0 0 10px;color:var(--text-mid,#4a5a6a)}" +
      ".sfo-by{font-size:.7rem;color:var(--text-light,#8a97a3);margin:-4px 0 9px}" +
      ".sfo-cta{display:inline-block;background:var(--blue-dark,#1a5a8a);color:#fff!important;text-decoration:none!important;font-weight:800;font-size:.8rem;padding:8px 15px;border-radius:22px}" +
      ".sfo-cta:hover{filter:brightness(1.1)}" +
      ".sfo-stay{background:#fff;border:1px solid var(--border,#e3e9ee);border-radius:14px;padding:12px 14px;margin-bottom:12px;box-shadow:0 4px 16px rgba(13,34,64,.09)}" +
      ".sfo-stay-h{font-weight:800;font-size:.86rem;margin:0 0 8px;color:var(--blue-dark,#1a5a8a)}" +
      ".sfo-row{margin:0 0 9px}.sfo-row:last-child{margin-bottom:0}" +
      ".sfo-row-n{font-size:.78rem;font-weight:700;margin:0 0 5px}" +
      ".sfo-pill{display:inline-block;font-size:.76rem;font-weight:800;text-decoration:none!important;padding:6px 12px;border-radius:20px;margin-right:6px}" +
      ".sfo-pill.bk{background:#003d96;color:#fff!important}.sfo-pill.ex{background:#ffcc00;color:#1a2060!important}" +
      ".sfo-aff{font-size:.64rem;color:var(--text-light,#8a97a3);text-align:center;margin:2px 4px 0;line-height:1.35}" +
      ".sfo-rail{position:fixed;top:84px;width:270px;max-height:calc(100vh - 160px);overflow-y:auto;overflow-x:hidden;scrollbar-width:thin;z-index:20}" +
      ".sfo-inline{max-width:640px;margin:22px auto}" +
      "@media print{#sfo-root{display:none!important}}";
    document.head.appendChild(css);

    // ── Rendu ──────────────────────────────────────────────────────────────
    var root = document.createElement("aside");
    root.id = "sfo-root";
    root.setAttribute("aria-label", T.offers);

    function render(offers) {
      var html = "";
      var hasAff = false;
      offers.forEach(function (o) {
        var e = (EN && o.en) || {};
        var titre = e.titre || o.titre, texte = e.texte || o.texte, cta = e.cta || o.cta || T.see;
        var lien = safeUrl(o.lien);
        if (!titre || !lien) return;
        var label = o.label || T.partner;
        if (EN) label = ({ "Partenaire": "Partner", "Bon plan": "Deal", "Publicité": "Ad" })[label] || label;
        var icon = ICONS[o.type] || "⭐";
        html += '<div class="sfo-card">' +
          (safeUrl(o.image) ? '<img class="sfo-img" src="' + esc(o.image) + '" alt="" loading="lazy">' : "") +
          '<div class="sfo-body"><span class="sfo-badge">' + icon + " " + esc(label) + "</span>" +
          '<div class="sfo-h">' + esc(titre) + "</div>" +
          (texte ? '<p class="sfo-p">' + esc(texte) + "</p>" : "") +
          (o.partenaire ? '<div class="sfo-by">' + esc(o.partenaire) + "</div>" : "") +
          '<a class="sfo-cta" href="' + esc(lien) + '" target="_blank" rel="sponsored nofollow noopener">' + esc(cta) + " →</a></div></div>";
        hasAff = true;
      });
      // Hébergement (Booking / Expedia) : seulement sur articles et duels (déjà présent dans la colonne des fiches stations)
      if (kind !== "station") {
        var rows = "";
        slugs.slice(0, 2).forEach(function (s) {
          var bk = cjLinks(s, "bk"), ex = cjLinks(s, "ex");
          if (!bk && !ex) return;
          rows += '<div class="sfo-row"><div class="sfo-row-n">' + esc(T.hotelsIn + nameOf(s)) + "</div>" +
            (bk ? '<a class="sfo-pill bk" href="' + esc(bk) + '" target="_blank" rel="sponsored nofollow noopener">' + T.booking + "</a>" : "") +
            (ex ? '<a class="sfo-pill ex" href="' + esc(ex) + '" target="_blank" rel="sponsored nofollow noopener">' + T.expedia + "</a>" : "") +
            "</div>";
        });
        if (rows) { html += '<div class="sfo-stay"><div class="sfo-stay-h">🏨 ' + T.book + "</div>" + rows + "</div>"; hasAff = true; }
      }
      if (!html) return false;
      root.innerHTML = '<div class="sfo-title-h">' + T.offers + "</div>" + html + (hasAff ? '<div class="sfo-aff">' + T.aff + "</div>" : "");
      return true;
    }

    // ── Placement ──────────────────────────────────────────────────────────
    var RAIL_W = 270, GAP = 24;
    var wrapper = null, origMax = 0;
    if (kind === "article") { var ar = document.querySelector("article"); wrapper = ar && (ar.closest(".wrap") || ar.parentNode); }
    if (kind === "duel") wrapper = document.querySelector("main.page");

    function placeInline() {
      root.className = "sfo-inline"; root.style.cssText = "";
      var host = null, before = null;
      if (kind === "article") {
        var art = document.querySelector("article");
        var hs = art ? art.querySelectorAll("h2,h3") : [];
        if (hs.length > 1) { before = hs[1]; host = before.parentNode; }
        else if (art) { host = art; }
      } else if (kind === "duel") {
        var main = document.querySelector("main.page") || document.body;
        var h2s = main.querySelectorAll("h2");
        for (var i = 0; i < h2s.length; i++) { if (/verdict/i.test(h2s[i].textContent)) { before = h2s[i]; break; } }
        host = before ? before.parentNode : main;
      }
      if (!host) return;
      host.insertBefore(root, before);
    }
    function layout() {
      if (kind === "station") return;
      var W = window.innerWidth;
      if (!wrapper) { placeInline(); return; }
      if (!origMax) origMax = parseFloat(getComputedStyle(wrapper).maxWidth) || wrapper.getBoundingClientRect().width;
      var avail = W - RAIL_W - GAP - 32;
      var target = Math.min(origMax, avail);
      if (W >= 1100 && target >= 740) {
        wrapper.style.maxWidth = target + "px";
        var left = Math.max(16, (W - target - GAP - RAIL_W) / 2);
        wrapper.style.marginLeft = left + "px"; wrapper.style.marginRight = "0";
        root.className = "sfo-rail"; root.style.cssText = "left:" + (left + target + GAP) + "px";
        if (root.parentNode !== document.body) document.body.appendChild(root);
      } else {
        wrapper.style.maxWidth = ""; wrapper.style.marginLeft = ""; wrapper.style.marginRight = "";
        placeInline();
      }
    }

    function mount() {
      if (kind === "station") {
        var sb = document.querySelector(".sidebar");
        if (!sb) return;
        root.className = ""; root.style.cssText = "margin-top:2px";
        var ref = sb.children[1] || sb.lastElementChild;
        if (ref && ref.nextSibling) sb.insertBefore(root, ref.nextSibling); else sb.appendChild(root);
        return;
      }
      layout();
      var t; window.addEventListener("resize", function () { clearTimeout(t); t = setTimeout(layout, 150); });
    }

    // ── Données ────────────────────────────────────────────────────────────
    function pick(data) {
      var today = new Date(); today.setHours(0, 0, 0, 0);
      var iso = today.getFullYear() + "-" + ("0" + (today.getMonth() + 1)).slice(-2) + "-" + ("0" + today.getDate()).slice(-2);
      var list = (data && data.offres || []).filter(function (o) {
        if (!o || o.actif === false) return false;
        if (o.debut && iso < o.debut) return false;
        if (o.fin && iso > o.fin) return false;
        if (o.pages && o.pages.length && o.pages.indexOf(kind) < 0) return false;
        if (o.stations && o.stations.length) {
          var ok = o.stations.some(function (n) { return slugs.indexOf(norm(n)) >= 0; });
          if (!ok) return false;
        }
        return true;
      });
      list.sort(function (a, b) { return (b.priorite || 0) - (a.priorite || 0); });
      return list.slice(0, 2);
    }

    var started = false;
    function go(offers) {
      if (started) return; started = true;
      if (render(offers)) mount();
    }
    var v = Math.floor(Date.now() / 3600000);
    fetch("/partenaires.json?v=" + v, { credentials: "omit" })
      .then(function (r) { return r.ok ? r.json() : { offres: [] }; })
      .catch(function () { return { offres: [] }; })
      .then(function (d) { go(pick(d)); });
  } catch (e) { /* un encart ne doit jamais casser une page */ }
})();
