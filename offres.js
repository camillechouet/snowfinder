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
      offers: "Offers & deals", deals: "Hot deals", pick: "Right now · picked by SnowFinder"
    } : {
      book: "Réserver votre séjour", hotelsIn: "Hôtels à ", booking: "Booking", expedia: "Expedia",
      aff: "Liens affiliés — prix identiques pour vous, sans frais supplémentaires.", partner: "Partenaire",
      see: "Voir l'offre", offers: "Offres & bons plans", deals: "Bons plans 🔥", pick: "Offres du moment · sélection SnowFinder"
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
      ".sfo-box{background:#fff;border:2px solid #ff7a1a;border-radius:20px;overflow:hidden;margin-bottom:14px;box-shadow:0 12px 34px rgba(255,90,20,.28)}" +
      ".sfo-box-hd{display:flex;align-items:center;gap:11px;padding:15px 16px;color:#fff;background:linear-gradient(135deg,#ff8a1f 0%,#ff4d3d 60%,#e8265f 100%)}" +
      ".sfo-box-fire{flex:0 0 40px;height:40px;border-radius:50%;background:rgba(255,255,255,.25);display:flex;align-items:center;justify-content:center;font-size:1.4rem}" +
      ".sfo-box-t{font-family:'DM Serif Display',serif;font-size:1.45rem;line-height:1.05;display:block;text-shadow:0 1px 4px rgba(0,0,0,.25)}" +
      ".sfo-box-s{display:block;font-size:.72rem;font-weight:600;letter-spacing:.03em;opacity:.95;margin-top:3px}" +
      ".sfo-deal{display:flex;gap:13px;align-items:flex-start;padding:15px 16px;text-decoration:none!important;color:inherit!important;border-top:1px solid #ffe2cc;border-left:5px solid #ff7a1a;transition:background .2s}" +
      ".sfo-box-hd+.sfo-deal{border-top:0;background:#fff4e8}" +
      ".sfo-box-hd+.sfo-deal+.sfo-deal{background:#fffbe3;border-left-color:#ffb800}" +
      ".sfo-deal:hover{filter:brightness(.97)}" +
      ".sfo-thumb{flex:0 0 74px;height:74px;border-radius:14px;position:relative;background:linear-gradient(135deg,#d3e8f8,#8fbfe3) center/cover no-repeat;box-shadow:0 4px 12px rgba(13,34,64,.18)}" +
      ".sfo-ico{position:absolute;right:-7px;bottom:-7px;width:30px;height:30px;border-radius:50%;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.22);display:flex;align-items:center;justify-content:center;font-size:.95rem}" +
      ".sfo-dbody{min-width:0;display:flex;flex-direction:column;gap:4px}" +
      ".sfo-tag{align-self:flex-start;font-size:.58rem;font-weight:800;letter-spacing:.07em;text-transform:uppercase;color:#fff;background:linear-gradient(90deg,#ff8a2b,#ff4d4d);border-radius:20px;padding:2px 9px}" +
      ".sfo-dh{font-weight:800;font-size:.95rem;line-height:1.25;color:#7a1d00}" +
      ".sfo-dp{font-size:.77rem;line-height:1.42;color:#5a6b7b}" +
      ".sfo-by{font-size:.68rem;color:#8a97a3}" +
      ".sfo-go{align-self:flex-start;margin-top:5px;font-size:.8rem;font-weight:800;color:#fff;background:linear-gradient(90deg,#ff7a1a,#ff3d3d);padding:7px 14px;border-radius:22px;box-shadow:0 4px 12px rgba(255,70,30,.35)}" +
      ".sfo-deal:hover .sfo-go{filter:brightness(1.08)}" +
      ".sfo-stay{background:#f6faff;border-top:1px solid #eef2f6;padding:13px 16px}" +
      ".sfo-stay-h{font-weight:800;font-size:.86rem;margin:0 0 8px;color:#0d2240}" +
      ".sfo-row{margin:0 0 9px}.sfo-row:last-child{margin-bottom:0}" +
      ".sfo-row-n{font-size:.78rem;font-weight:700;margin:0 0 5px}" +
      ".sfo-pill{display:inline-block;font-size:.76rem;font-weight:800;text-decoration:none!important;padding:6px 12px;border-radius:20px;margin-right:6px}" +
      ".sfo-pill.bk{background:#003d96;color:#fff!important}.sfo-pill.ex{background:#ffcc00;color:#1a2060!important}" +
      ".sfo-aff{font-size:.64rem;color:#8a97a3;text-align:center;padding:9px 14px;line-height:1.35;background:#faf9f7;border-top:1px solid #eef2f6}" +
      ".sfb{position:fixed;right:20px;bottom:20px;width:400px;max-width:calc(100vw - 24px);z-index:60;color:#fff;border-radius:22px;box-shadow:0 18px 50px rgba(120,20,0,.45),0 0 0 3px rgba(255,255,255,.9);overflow:hidden;font-family:'DM Sans',-apple-system,sans-serif;background:linear-gradient(135deg,#ff8a1f 0%,#ff4d3d 55%,#e8265f 100%);transform:translateY(40px) scale(.96);opacity:0;transition:transform .5s cubic-bezier(.2,.9,.3,1.2),opacity .4s ease}" +
      ".sfb.on{transform:none;opacity:1}" +
      ".sfb-in{padding:16px 18px 14px}" +
      ".sfb-top{display:flex;align-items:center;gap:8px;font-size:.7rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;margin-bottom:10px;padding-right:26px}" +
      ".sfb-live{display:inline-block;width:9px;height:9px;border-radius:50%;background:#fff;animation:sfbpulse 1.2s infinite}" +
      "@keyframes sfbpulse{0%{box-shadow:0 0 0 0 rgba(255,255,255,.8)}100%{box-shadow:0 0 0 10px rgba(255,255,255,0)}}" +
      ".sfb-main{display:flex;align-items:center;gap:14px}" +
      ".sfb-big{flex:0 0 auto;min-width:104px;text-align:center;background:#fff176;color:#c4171a;border-radius:16px;padding:8px 10px 6px;transform:rotate(-3deg);box-shadow:0 6px 16px rgba(0,0,0,.25)}" +
      ".sfb-big b{display:block;font-family:'DM Serif Display',serif;font-weight:400;font-size:2.5rem;line-height:1}" +
      ".sfb-big span{display:block;font-size:.62rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#7a1d00;margin-top:2px}" +
      ".sfb-t{font-family:'DM Serif Display',serif;font-size:1.3rem;line-height:1.15}" +
      ".sfb-p{font-size:.8rem;line-height:1.35;opacity:.95;margin-top:3px}" +
      ".sfb-chips{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 4px}" +
      ".sfb-chip{background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.45);border-radius:20px;padding:4px 10px;font-size:.7rem;font-weight:700}" +
      ".sfb-btns{display:flex;gap:8px;margin-top:12px}" +
      ".sfb-btn{flex:1;text-align:center;text-decoration:none!important;font-weight:800;font-size:.84rem;padding:11px 10px;border-radius:26px;line-height:1.15}" +
      ".sfb-btn.a{background:#fff;color:#d0291d!important;animation:sfbpop 1.8s ease-in-out infinite}" +
      ".sfb-btn.b{background:#ffe03a;color:#6b1a00!important}" +
      "@keyframes sfbpop{0%,100%{transform:scale(1)}50%{transform:scale(1.04)}}" +
      ".sfb-urg{font-size:.7rem;font-weight:700;margin-top:10px;text-align:center;opacity:.97}" +
      ".sfb-aff{font-size:.58rem;opacity:.75;text-align:center;margin-top:5px}" +
      ".sfb-x{position:absolute;top:8px;right:10px;width:30px;height:30px;border:0;border-radius:50%;background:rgba(0,0,0,.22);color:#fff;font-size:1.25rem;line-height:1;cursor:pointer}" +
      "@media(max-width:700px){.sfb{left:10px;right:10px;width:auto;bottom:calc(74px + env(safe-area-inset-bottom,0px))}.sfb-in{padding:13px 14px 12px}.sfb-big{min-width:86px}.sfb-big b{font-size:2rem}.sfb-t{font-size:1.1rem}.sfb-chips{display:none}.sfb-btn{font-size:.78rem;padding:10px 6px}}" +
      "@media print{.sfb{display:none!important}}" +
      ".sfx{width:100%;position:relative;z-index:5;background:linear-gradient(90deg,#f97316,#ea580c);box-shadow:0 4px 14px rgba(234,88,12,.30);font-family:'DM Sans',-apple-system,sans-serif;color:#fff}" +
      ".sfx-in{max-width:1100px;margin:0 auto;padding:0 12px}" +
      ".sfx-bar{display:flex;align-items:center;gap:12px;width:100%;border:0;background:transparent;color:#fff;cursor:pointer;text-align:left;padding:13px 6px;font:inherit;position:relative;overflow:hidden}" +
      ".sfx-bar::after{display:none}" +
      "@keyframes sfxshine{0%{left:-120px}55%,100%{left:110%}}" +
      ".sfx-fire{flex:0 0 36px;height:36px;border-radius:8px;background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;font-size:1.2rem}" +
      ".sfx-txt{flex:1;min-width:0}" +
      ".sfx-txt b{display:block;font-family:'DM Sans',-apple-system,sans-serif;font-weight:700;font-size:1.05rem;line-height:1.2;letter-spacing:.005em}" +
      ".sfx-txt small{display:block;font-size:.82rem;font-weight:500;opacity:.95;margin-top:2px}" +
      ".sfx-count{flex:0 0 auto;border:1px solid rgba(255,255,255,.7);color:#fff;font-weight:600;font-size:.76rem;border-radius:6px;padding:4px 10px}" +
      ".sfx-go{flex:0 0 auto;background:#fff;color:#c2410c;font-weight:700;font-size:.84rem;border-radius:8px;padding:9px 16px;white-space:nowrap}" +
      ".sfx-chev{display:inline-block;transition:transform .3s}" +
      ".sfx.open .sfx-chev{transform:rotate(180deg)}" +
      ".sfx-panel{display:none;padding:4px 0 16px}" +
      ".sfx.open .sfx-panel{display:block}" +
      ".sfx-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px}" +
      ".sfx-card{display:flex;gap:13px;align-items:flex-start;background:#fff;color:#22303e;border-radius:12px;padding:13px;text-decoration:none!important;box-shadow:0 6px 18px rgba(80,30,0,.22)}" +
      ".sfx-card .sfo-thumb{flex:0 0 78px;height:78px}" +
      ".sfx-card .sfo-dh{font-size:.98rem}" +
      ".sfx-note{font-size:.66rem;opacity:.85;text-align:center;margin-top:10px}" +
      "@media(max-width:700px){.sfx-txt b{font-size:1.08rem}.sfx-txt small{font-size:.72rem}.sfx-count{display:none}.sfx-go{padding:8px 11px;font-size:.76rem}.sfx-fire{flex-basis:34px;height:34px;font-size:1.2rem}}" +
      "@media print{.sfx{display:none!important}}" +
      ".sfo-rail{position:fixed;top:84px;width:270px;max-height:calc(100vh - 160px);overflow-y:auto;overflow-x:hidden;scrollbar-width:thin;z-index:20}" +
      ".sfo-inline{max-width:640px;margin:22px auto}" +
      "@media print{#sfo-root{display:none!important}}";
    document.head.appendChild(css);


    // ── Habillage des fiches stations : onglets bien visibles + fil d'Ariane ──
    if (kind === "station") {
      var st = document.createElement("style");
      st.textContent =
        ".tab-nav-wrap{background:#f3f7fb!important;border-bottom:2px solid #12365a!important;padding-top:10px;box-shadow:none!important}" +
        ".tab-nav{gap:4px!important;padding:0 10px!important;align-items:flex-end}" +
        ".tab-btn{font-size:.92rem!important;font-weight:600!important;letter-spacing:.01em;padding:12px 22px 11px!important;min-width:0!important;color:#3b5068!important;background:#e4ecf4!important;border:1px solid #d3dfeb!important;border-bottom:0!important;border-radius:8px 8px 0 0!important;box-shadow:none!important;transition:background .15s,color .15s}" +
        ".tab-btn:hover:not(.active){background:#d6e3f0!important;color:#12365a!important}" +
        ".tab-btn.active{color:#fff!important;background:#12365a!important;border-color:#12365a!important;font-weight:700!important;margin-bottom:-2px;padding-bottom:13px!important}" +
        ".breadcrumb{display:inline-flex!important;max-width:100%;background:#fff;border:1px solid #d3dfeb;border-radius:8px;padding:8px 14px;box-shadow:none;font-size:.86rem!important;font-weight:600;color:#12365a!important;gap:8px!important}" +
        ".breadcrumb a{font-weight:500!important;color:#2b6a9e!important;text-decoration:none}" +
        ".breadcrumb a:hover{text-decoration:underline}" +
        "@media(max-width:700px){.tab-btn{font-size:.8rem!important;padding:11px 13px 10px!important}.tab-btn.active{padding-bottom:12px!important}.breadcrumb{font-size:.78rem!important;padding:7px 11px}}";
      document.head.appendChild(st);
      var stripEmoji = function () {
        [].forEach.call(document.querySelectorAll(".tab-nav .tab-btn"), function (b) {
          var t = b.textContent || "", c = t.replace(/^[^A-Za-zÀ-ÿ0-9]+/, "");
          if (c && c !== t) b.textContent = c;
        });
      };
      stripEmoji(); setTimeout(stripEmoji, 1500);
    }

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
        var thumb = safeUrl(o.image) || (/^\//.test(o.image || "") ? o.image : "");
        html += '<a class="sfo-deal" href="' + esc(lien) + '" target="_blank" rel="sponsored nofollow noopener">' +
          '<span class="sfo-thumb"' + (thumb ? ' style="background-image:url(\'' + esc(thumb) + '\')"' : "") + '><span class="sfo-ico">' + icon + "</span></span>" +
          '<span class="sfo-dbody"><span class="sfo-tag">' + esc(label) + "</span>" +
          '<span class="sfo-dh">' + esc(titre) + "</span>" +
          (texte ? '<span class="sfo-dp">' + esc(texte) + "</span>" : "") +
          (o.partenaire ? '<span class="sfo-by">' + esc(o.partenaire) + "</span>" : "") +
          '<span class="sfo-go">' + esc(cta) + " →</span></span></a>";
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
      root.innerHTML = '<div class="sfo-box"><div class="sfo-box-hd"><span class="sfo-box-fire">🎿</span><span><span class="sfo-box-t">' + T.deals + '</span><span class="sfo-box-s">' + T.pick + "</span></span></div>" +
        html + (hasAff ? '<div class="sfo-aff">' + T.aff + "</div>" : "") + "</div>";
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
        var bkA = sb.querySelector("a[href*='tkqlhce.com']");
        var bkBlock = bkA && bkA.parentNode && bkA.parentNode !== sb ? bkA.parentNode : null;
        if (bkBlock && bkBlock.parentNode === sb) { sb.insertBefore(root, bkBlock); return; }
        var ref = sb.children[1] || sb.lastElementChild;
        if (ref && ref.nextSibling) sb.insertBefore(root, ref.nextSibling); else sb.appendChild(root);
        return;
      }
      layout();
      var t; window.addEventListener("resize", function () { clearTimeout(t); t = setTimeout(layout, 150); });
    }

    // ── Données ────────────────────────────────────────────────────────────
    function pick(data, nmax) {
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
      return list.slice(0, nmax || 2);
    }


    // ── Bulle « offres du moment » (temporaire, fermable) ──────────────────
    function bulle(b) {
      try {
        if (!b || b.actif === false || !safeUrl(b.lien)) return;
        var today = new Date(); today.setHours(0, 0, 0, 0);
        var iso = today.getFullYear() + "-" + ("0" + (today.getMonth() + 1)).slice(-2) + "-" + ("0" + today.getDate()).slice(-2);
        if (b.debut && iso < b.debut) return;
        if (b.fin && iso > b.fin) return;
        var key = "sfb_" + (b.id || "x"), days = (b.masquer_jours == null ? 3 : b.masquer_jours);
        try { var last = parseInt(localStorage.getItem(key) || "0", 10); if (last && Date.now() - last < days * 86400000) return; } catch (e) { }
        var e = (EN && b.en) || {};
        var g = function (k) { return e[k] != null ? e[k] : b[k]; };
        var titre = g("titre"); if (!titre) return;
        var urg = g("urgence") || "";
        if (b.fin) {
          var d = new Date(b.fin + "T00:00:00");
          urg = (EN ? "⏳ Offer valid until " : "⏳ Offre valable jusqu'au ") + d.toLocaleDateString(EN ? "en-GB" : "fr-FR", { day: "numeric", month: "long" }) + (urg ? " — " + urg : "");
        }
        var chips = g("puces") || [];
        var el = document.createElement("div");
        el.className = "sfb"; el.setAttribute("role", "complementary");
        var h = '<div class="sfb-in"><div class="sfb-top"><span class="sfb-live"></span>' + esc(g("tag") || (EN ? "Ski deals right now" : "Bons plans ski en ce moment")) + "</div>" +
          '<div class="sfb-main">' + (g("gros") ? '<div class="sfb-big"><b>' + esc(g("gros")) + "</b><span>" + esc(g("gros_legende") || "") + "</span></div>" : "") +
          "<div><div class=\"sfb-t\">" + esc(titre) + "</div>" + (g("texte") ? '<div class="sfb-p">' + esc(g("texte")) + "</div>" : "") + "</div></div>";
        if (chips.length) { h += '<div class="sfb-chips">'; chips.forEach(function (c) { h += '<span class="sfb-chip">' + esc(c) + "</span>"; }); h += "</div>"; }
        h += '<div class="sfb-btns"><a class="sfb-btn a" href="' + esc(b.lien) + '" target="_blank" rel="sponsored nofollow noopener">' + esc(g("cta") || T.see) + "</a>" +
          (safeUrl(b.lien2) ? '<a class="sfb-btn b" href="' + esc(b.lien2) + '" target="_blank" rel="sponsored nofollow noopener">' + esc(g("cta2") || T.see) + "</a>" : "") + "</div>" +
          (urg ? '<div class="sfb-urg">' + esc(urg) + "</div>" : "") +
          '<div class="sfb-aff">' + esc(T.aff) + "</div></div>" +
          '<button class="sfb-x" type="button" aria-label="' + (EN ? "Close" : "Fermer") + '">×</button>';
        el.innerHTML = h;
        el.querySelector(".sfb-x").addEventListener("click", function () {
          try { localStorage.setItem(key, String(Date.now())); } catch (e) { }
          el.classList.remove("on"); setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 500);
        });
        setTimeout(function () { document.body.appendChild(el); setTimeout(function () { el.classList.add("on"); }, 30); }, Math.max(0, (b.delai == null ? 12 : b.delai)) * 1000);
      } catch (e) { }
    }

    // ── Bandeau « bons plans » déroulant (fiches stations, entre la photo et le menu) ──
    function bandeau(data) {
      try {
        if (kind !== "station") return;
        var b = data && data.bandeau;
        if (!b || b.actif === false) return;
        var today = new Date(); today.setHours(0, 0, 0, 0);
        var iso = today.getFullYear() + "-" + ("0" + (today.getMonth() + 1)).slice(-2) + "-" + ("0" + today.getDate()).slice(-2);
        if (b.debut && iso < b.debut) return;
        if (b.fin && iso > b.fin) return;
        var anchor = document.getElementById("tabNavWrap");
        if (!anchor || document.getElementById("sfx")) return;
        var offers = pick(data, 4);
        var cards = "";
        offers.forEach(function (o) {
          var e = (EN && o.en) || {};
          var titre = e.titre || o.titre, texte = e.texte || o.texte, cta = e.cta || o.cta || T.see, lien = safeUrl(o.lien);
          if (!titre || !lien) return;
          var label = o.label || T.partner;
          if (EN) label = ({ "Partenaire": "Partner", "Bon plan": "Deal", "Publicité": "Ad" })[label] || label;
          var thumb = safeUrl(o.image) || (/^\//.test(o.image || "") ? o.image : "");
          cards += '<a class="sfx-card" href="' + esc(lien) + '" target="_blank" rel="sponsored nofollow noopener">' +
            '<span class="sfo-thumb"' + (thumb ? ' style="background-image:url(\'' + esc(thumb) + '\')"' : "") + '><span class="sfo-ico">' + (ICONS[o.type] || "⭐") + "</span></span>" +
            '<span class="sfo-dbody"><span class="sfo-tag">' + esc(label) + "</span>" +
            '<span class="sfo-dh">' + esc(titre) + "</span>" + (texte ? '<span class="sfo-dp">' + esc(texte) + "</span>" : "") +
            '<span class="sfo-go">' + esc(cta) + " →</span></span></a>";
        });
        if (!cards) return;
        var e2 = (EN && b.en) || {};
        var titreB = e2.titre || b.titre || T.deals, resume = e2.resume || b.resume || "";
        if (b.fin) {
          var d = new Date(b.fin + "T00:00:00");
          resume = (EN ? "Until " : "Jusqu'au ") + d.toLocaleDateString(EN ? "en-GB" : "fr-FR", { day: "numeric", month: "long" }) + " · " + resume;
        }
        var n = offers.length;
        var el = document.createElement("div");
        el.id = "sfx"; el.className = "sfx";
        el.innerHTML = '<div class="sfx-in"><button type="button" class="sfx-bar" aria-expanded="false" aria-controls="sfx-panel">' +
          '<span class="sfx-fire">🔥</span><span class="sfx-txt"><b>' + esc(titreB) + "</b><small>" + esc(resume) + "</small></span>" +
          '<span class="sfx-count">' + n + (EN ? (n > 1 ? " deals" : " deal") : (n > 1 ? " offres" : " offre")) + '</span>' +
          '<span class="sfx-go">' + (EN ? "See deals" : "Voir les offres") + ' <span class="sfx-chev">▾</span></span></button>' +
          '<div class="sfx-panel" id="sfx-panel"><div class="sfx-grid">' + cards + "</div>" +
          '<div class="sfx-note">' + esc(T.aff) + "</div></div></div>";
        el.querySelector(".sfx-bar").addEventListener("click", function () {
          var open = el.classList.toggle("open");
          this.setAttribute("aria-expanded", open ? "true" : "false");
        });
        anchor.parentNode.insertBefore(el, anchor);
      } catch (e) { }
    }

    var started = false;
    function go(offers) {
      if (started) return; started = true;
      if (kind === "station") return; // fiches stations : le bandeau déroulant remplace l'encart de droite
      if (render(offers)) mount();
    }
    var v = Math.floor(Date.now() / 3600000);
    fetch("/partenaires.json?v=" + v, { credentials: "omit" })
      .then(function (r) { return r.ok ? r.json() : { offres: [] }; })
      .catch(function () { return { offres: [] }; })
      .then(function (d) { go(pick(d)); bandeau(d); bulle(d && d.bulle); });
  } catch (e) { /* un encart ne doit jamais casser une page */ }
})();
