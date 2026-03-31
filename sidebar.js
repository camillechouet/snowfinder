(function() {
  var ph = document.getElementById('sidebar-placeholder');
  if (!ph) return;

  fetch('sidebar.html')
    .then(function(r){ return r.text(); })
    .then(function(html){
      ph.innerHTML = html;
      // Set active link
      var page = window.location.pathname.split('/').pop() || 'index.html';
      var links = document.querySelectorAll('.sb-link[data-page]');
      links.forEach(function(l){
        if(l.getAttribute('data-page') === page) l.classList.add('active');
      });
      // Saison toggle sync
      var saison = localStorage.getItem('snowfinder_saison') || 'hiver';
      var btnH = document.getElementById('sbBtnHiver');
      var btnE = document.getElementById('sbBtnEte');
      if(btnH && btnE){
        btnH.className = 'saison-btn' + (saison==='hiver' ? ' active-hiver' : '');
        btnE.className = 'saison-btn' + (saison==='ete' ? ' active-ete' : '');
      }
    })
    .catch(function(){
      // Fallback si fetch échoue (file://)
      ph.innerHTML = '';
    });
})();
