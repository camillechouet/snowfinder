/* ── sidebar.js ── Chargement et gestion du menu latéral SnowFinder ── */

(function () {

  // ── 1. Injection du HTML ──────────────────────────────────────────
  var placeholder = document.getElementById('sidebar-placeholder');
  if (!placeholder) return;

  fetch('sidebar.html')
    .then(function (r) { return r.text(); })
    .then(function (html) {
      placeholder.outerHTML = html;
      initSidebar();
    })
    .catch(function (e) {
      console.warn('sidebar.html non trouvé', e);
    });

  // ── 2. Initialisation après injection ────────────────────────────
  function initSidebar() {

    // Lien actif : on compare le nom du fichier courant
    var currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.sb-link[data-page]').forEach(function (a) {
      if (a.getAttribute('data-page') === currentPage) {
        a.classList.add('active');
      }
    });

    // Toggle saison
    var saison = localStorage.getItem('snowfinder_saison') || 'hiver';
    applySaison(saison);

    var toggle = document.getElementById('saisonToggle');
    if (toggle) {
      toggle.addEventListener('click', function () {
        var current = localStorage.getItem('snowfinder_saison') || 'hiver';
        var next = current === 'hiver' ? 'ete' : 'hiver';
        localStorage.setItem('snowfinder_saison', next);
        applySaison(next);
        // Notifier la page si elle veut réagir
        document.dispatchEvent(new CustomEvent('saisonChange', { detail: next }));
      });
    }

    // Hamburger
    window.toggleSidebar = function () {
      ['sidebar', 'sbHamburger', 'sbOverlay'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.classList.toggle('open');
      });
    };
    window.closeSidebar = function () {
      ['sidebar', 'sbHamburger', 'sbOverlay'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.classList.remove('open');
      });
    };

    // Stubs pour les boutons si non définis par la page
    if (typeof window.openHebModal === 'undefined') {
      window.openHebModal = function () { window.location.href = 'recherche.html'; };
    }
    if (typeof window.openContact === 'undefined') {
      window.openContact = function () { window.location.href = 'index.html#contact'; };
    }
  }

  // ── 3. Applique la saison visuellement ───────────────────────────
  function applySaison(saison) {
    var btnH = document.getElementById('btnHiver');
    var btnE = document.getElementById('btnEte');
    if (!btnH || !btnE) return;
    if (saison === 'ete') {
      btnH.className = 'saison-btn';
      btnE.className = 'saison-btn active-ete';
      document.body.classList.add('ete');
      document.body.classList.remove('hiver');
    } else {
      btnH.className = 'saison-btn active-hiver';
      btnE.className = 'saison-btn';
      document.body.classList.add('hiver');
      document.body.classList.remove('ete');
    }
  }

})();
