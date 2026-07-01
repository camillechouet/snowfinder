(function() {
  var ph = document.getElementById('sidebar-placeholder');
  if (!ph) return;

  // Chemin absolu — fonctionne depuis n'importe quelle page du site
  var url = window.location.origin + '/sidebar.html';

  fetch(url)
    .then(function(r){ return r.text(); })
    .then(function(html){
      ph.innerHTML = html;

      // Sidebar fermée par défaut sur mobile
      var sb = document.getElementById('sidebar');
      if(sb && window.innerWidth <= 1024){
        sb.classList.remove('open');
      }

      window.toggleSidebar = function() {
        var sb  = document.getElementById('sidebar');
        var hb  = document.getElementById('sbHamburger');
        var ov  = document.getElementById('sbOverlay');
        if(!sb) return;
        var opening = !sb.classList.contains('open');
        sb.classList.toggle('open');
        if(hb) hb.classList.toggle('open');
        if(ov) ov.classList.toggle('open');
        document.body.style.overflow = opening ? 'hidden' : '';
      };

      window.closeSidebar = function() {
        var sb = document.getElementById('sidebar');
        var hb = document.getElementById('sbHamburger');
        var ov = document.getElementById('sbOverlay');
        if(sb) sb.classList.remove('open');
        if(hb) hb.classList.remove('open');
        if(ov) ov.classList.remove('open');
        document.body.style.overflow = '';
      };

      // Overlay : clic ferme la sidebar
      var ov = document.getElementById('sbOverlay');
      if(ov) ov.addEventListener('click', window.closeSidebar);

      // Lien actif
      var page = window.location.pathname.split('/').pop() || 'index.html';
      document.querySelectorAll('.sb-link[data-page]').forEach(function(l){
        if(l.getAttribute('data-page') === page) l.classList.add('active');
      });

      // Saison toggle sync
      var saison = localStorage.getItem('snowfinder_saison') || 'hiver';
      var btnH = document.getElementById('sbBtnHiver');
      var btnE = document.getElementById('sbBtnEte');
      if(btnH && btnE){
        btnH.className = 'saison-btn' + (saison==='hiver'?' active-hiver':'');
        btnE.className = 'saison-btn' + (saison==='ete'?' active-ete':'');
      }
    })
    .catch(function(){ ph.innerHTML = ''; });
})();
