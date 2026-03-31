(function() {
  var ph = document.getElementById('sidebar-placeholder');
  if (!ph) return;

  fetch('sidebar.html')
    .then(function(r){ return r.text(); })
    .then(function(html){
      ph.innerHTML = html;

      // ── Fonctions sidebar (définies après injection) ──
      window.toggleSidebar = function() {
        var sb = document.getElementById('sidebar');
        var hb = document.getElementById('sbHamburger');
        var ov = document.getElementById('sbOverlay');
        if (!sb) return;
        sb.classList.toggle('open');
        hb && hb.classList.toggle('open');
        ov && ov.classList.toggle('open');
      };
      window.closeSidebar = function() {
        var sb = document.getElementById('sidebar');
        if (!sb) return;
        sb.classList.remove('open');
        var hb = document.getElementById('sbHamburger');
        var ov = document.getElementById('sbOverlay');
        hb && hb.classList.remove('open');
        ov && ov.classList.remove('open');
      };

      // ── Lien actif ──
      var page = window.location.pathname.split('/').pop() || 'index.html';
      var links = document.querySelectorAll('.sb-link[data-page]');
      links.forEach(function(l){
        if (l.getAttribute('data-page') === page) l.classList.add('active');
      });

      // ── Saison toggle sync ──
      var saison = localStorage.getItem('snowfinder_saison') || 'hiver';
      var btnH = document.getElementById('sbBtnHiver');
      var btnE = document.getElementById('sbBtnEte');
      if (btnH && btnE) {
        btnH.className = 'saison-btn' + (saison === 'hiver' ? ' active-hiver' : '');
        btnE.className = 'saison-btn' + (saison === 'ete' ? ' active-ete' : '');
      }
    })
    .catch(function() {
      ph.innerHTML = '';
    });
})();
