#!/usr/bin/env python3
"""
patch_tinder_quiz.py
====================
Ajoute le questionnaire 6 étapes (ancien conseiller IA) en amont du
swipe dans tinder.html.

Flow nouveau :
  1. Arrivée sur la page → écran questionnaire (6 questions)
  2. Réponses → calcul des top 8 stations selon les critères
  3. Bascule en mode swipe sur ces 8 stations pré-sélectionnées
  4. Le bouton "🔄 Recommencer" relance le questionnaire

Option "Passer le questionnaire" en bas → mode swipe libre (comportement actuel).

Usage :
  python3 patch_tinder_quiz.py [--root .]
"""
import argparse, re
from pathlib import Path

# ── HTML DU QUESTIONNAIRE ──────────────────────────────────────────────
QUIZ_HTML = '''<!-- ════════ QUIZ EN AMONT DU SWIPE ════════ -->
<div id="quizScreen" class="quiz-screen">
  <div class="quiz-wrap">
    <div class="quiz-header">
      <div class="quiz-title">Trouve ta station idéale ✨</div>
      <div class="quiz-sub">6 questions pour pré-sélectionner 8 stations, puis tu swipes pour choisir.</div>
    </div>
    <div class="quiz-progress">
      <div class="qp-dot active" id="qpdot0"></div>
      <div class="qp-dot" id="qpdot1"></div>
      <div class="qp-dot" id="qpdot2"></div>
      <div class="qp-dot" id="qpdot3"></div>
      <div class="qp-dot" id="qpdot4"></div>
      <div class="qp-dot" id="qpdot5"></div>
    </div>

    <div class="quiz-step active" id="qstep0">
      <div class="quiz-num">Question 1 / 6</div>
      <div class="quiz-q">Tu pars avec qui&nbsp;?</div>
      <div class="quiz-choices">
        <div class="quiz-choice" onclick="quizSelect(0,'solo')"><span class="qc-emoji">🧍</span><div class="qc-label">Seul(e)</div></div>
        <div class="quiz-choice" onclick="quizSelect(0,'couple')"><span class="qc-emoji">👫</span><div class="qc-label">En couple</div></div>
        <div class="quiz-choice" onclick="quizSelect(0,'famille')"><span class="qc-emoji">👨‍👩‍👧</span><div class="qc-label">En famille</div></div>
        <div class="quiz-choice" onclick="quizSelect(0,'amis')"><span class="qc-emoji">👯</span><div class="qc-label">Entre amis</div></div>
      </div>
    </div>

    <div class="quiz-step" id="qstep1">
      <div class="quiz-num">Question 2 / 6</div>
      <div class="quiz-q">Ton niveau de ski&nbsp;?</div>
      <div class="quiz-choices">
        <div class="quiz-choice" onclick="quizSelect(1,'debutant')"><span class="qc-emoji">🟢</span><div class="qc-label">Débutant</div></div>
        <div class="quiz-choice" onclick="quizSelect(1,'intermediaire')"><span class="qc-emoji">🔵</span><div class="qc-label">Intermédiaire</div></div>
        <div class="quiz-choice" onclick="quizSelect(1,'avance')"><span class="qc-emoji">🔴</span><div class="qc-label">Avancé</div></div>
        <div class="quiz-choice" onclick="quizSelect(1,'expert')"><span class="qc-emoji">⚫</span><div class="qc-label">Expert</div></div>
      </div>
    </div>

    <div class="quiz-step" id="qstep2">
      <div class="quiz-num">Question 3 / 6</div>
      <div class="quiz-q">Ton budget forfait&nbsp;?</div>
      <div class="quiz-choices">
        <div class="quiz-choice" onclick="quizSelect(2,'eco')"><span class="qc-emoji">💚</span><div class="qc-label">Économique</div><div class="qc-sub">≤ 30€/j</div></div>
        <div class="quiz-choice" onclick="quizSelect(2,'moyen')"><span class="qc-emoji">💛</span><div class="qc-label">Moyen</div><div class="qc-sub">30-50€/j</div></div>
        <div class="quiz-choice" onclick="quizSelect(2,'premium')"><span class="qc-emoji">💎</span><div class="qc-label">Premium</div><div class="qc-sub">50€+/j</div></div>
      </div>
    </div>

    <div class="quiz-step" id="qstep3">
      <div class="quiz-num">Question 4 / 6</div>
      <div class="quiz-q">Quel massif&nbsp;?</div>
      <div class="quiz-choices">
        <div class="quiz-choice" onclick="quizSelect(3,'alpes_nord')"><span class="qc-emoji">🏔️</span><div class="qc-label">Alpes du Nord</div></div>
        <div class="quiz-choice" onclick="quizSelect(3,'alpes_sud')"><span class="qc-emoji">☀️</span><div class="qc-label">Alpes du Sud</div></div>
        <div class="quiz-choice" onclick="quizSelect(3,'pyrenees')"><span class="qc-emoji">🌲</span><div class="qc-label">Pyrénées</div></div>
        <div class="quiz-choice" onclick="quizSelect(3,'autre')"><span class="qc-emoji">🗺️</span><div class="qc-label">Peu importe</div></div>
      </div>
    </div>

    <div class="quiz-step" id="qstep4">
      <div class="quiz-num">Question 5 / 6</div>
      <div class="quiz-q">Ce qui compte le plus pour toi&nbsp;?</div>
      <div class="quiz-choices">
        <div class="quiz-choice" onclick="quizSelect(4,'neige')"><span class="qc-emoji">❄️</span><div class="qc-label">Neige garantie</div><div class="qc-sub">Altitude</div></div>
        <div class="quiz-choice" onclick="quizSelect(4,'ambiance')"><span class="qc-emoji">🎉</span><div class="qc-label">Ambiance</div><div class="qc-sub">Après-ski</div></div>
        <div class="quiz-choice" onclick="quizSelect(4,'nature')"><span class="qc-emoji">🌲</span><div class="qc-label">Nature</div><div class="qc-sub">Tranquillité</div></div>
        <div class="quiz-choice" onclick="quizSelect(4,'domaine')"><span class="qc-emoji">📏</span><div class="qc-label">Grand domaine</div><div class="qc-sub">Beaucoup de km</div></div>
      </div>
    </div>

    <div class="quiz-step" id="qstep5">
      <div class="quiz-num">Question 6 / 6</div>
      <div class="quiz-q">Hors-ski, tu aimes&nbsp;?</div>
      <div class="quiz-choices">
        <div class="quiz-choice" onclick="quizSelect(5,'restaurants')"><span class="qc-emoji">🍽️</span><div class="qc-label">Restaurants</div></div>
        <div class="quiz-choice" onclick="quizSelect(5,'spa')"><span class="qc-emoji">💆</span><div class="qc-label">Spa &amp; bien-être</div></div>
        <div class="quiz-choice" onclick="quizSelect(5,'shopping')"><span class="qc-emoji">🛍️</span><div class="qc-label">Shopping</div></div>
        <div class="quiz-choice" onclick="quizSelect(5,'peu_importe')"><span class="qc-emoji">🤷</span><div class="qc-label">Peu importe</div></div>
      </div>
    </div>

    <div class="quiz-skip">
      <button class="quiz-skip-btn" onclick="quizSkip()">↷ Passer le questionnaire — me laisser surprendre</button>
    </div>
  </div>
</div>

<!-- ════════ FIN QUIZ ════════ -->
'''

# ── CSS POUR LE QUIZ ───────────────────────────────────────────────────
QUIZ_CSS = '''
/* === QUIZ EN AMONT DU SWIPE === */
.quiz-screen{display:none;padding:32px 16px 60px;animation:fadeIn .3s ease}
.quiz-screen.show{display:block}
.quiz-wrap{max-width:520px;margin:0 auto}
.quiz-header{text-align:center;margin-bottom:24px}
.quiz-title{font-family:"DM Serif Display",serif;font-size:1.7rem;color:white;text-shadow:0 2px 8px rgba(0,0,0,.3);margin-bottom:8px;line-height:1.2}
.quiz-sub{font-size:.88rem;color:rgba(255,255,255,.92);max-width:380px;margin:0 auto;line-height:1.5;text-shadow:0 1px 4px rgba(0,0,0,.3)}
.quiz-progress{display:flex;justify-content:center;gap:8px;margin-bottom:24px}
.qp-dot{width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,.4);transition:all .3s}
.qp-dot.active{background:white;width:24px;border-radius:4px}
.qp-dot.done{background:var(--green)}
.quiz-step{display:none;animation:slideIn .3s ease}
.quiz-step.active{display:block}
.quiz-num{font-size:.78rem;color:rgba(255,255,255,.85);text-align:center;margin-bottom:8px;text-transform:uppercase;letter-spacing:.05em;font-weight:600;text-shadow:0 1px 4px rgba(0,0,0,.3)}
.quiz-q{font-family:"DM Serif Display",serif;font-size:1.5rem;color:white;text-align:center;margin-bottom:20px;text-shadow:0 2px 8px rgba(0,0,0,.3);line-height:1.3}
.quiz-choices{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.quiz-choice{background:white;border:2px solid transparent;border-radius:16px;padding:18px 12px;text-align:center;cursor:pointer;transition:all .2s;box-shadow:0 4px 16px rgba(0,0,0,.12);font-family:"DM Sans",sans-serif}
.quiz-choice:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.18);border-color:var(--blue-mid)}
.quiz-choice.selected{border-color:var(--blue-mid);background:var(--blue-light)}
.qc-emoji{font-size:1.8rem;display:block;margin-bottom:6px}
.qc-label{font-family:"DM Sans",sans-serif;font-size:.92rem;font-weight:700;color:var(--text)}
.qc-sub{font-size:.72rem;color:var(--text-light);margin-top:2px;font-weight:500}
.quiz-skip{text-align:center;margin-top:28px}
.quiz-skip-btn{background:transparent;border:1.5px solid rgba(255,255,255,.6);color:white;padding:9px 18px;border-radius:24px;font-family:"DM Sans",sans-serif;font-size:.78rem;cursor:pointer;transition:all .2s;font-weight:500}
.quiz-skip-btn:hover{background:rgba(255,255,255,.15);border-color:white}
@keyframes slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@media(max-width:380px){.quiz-q{font-size:1.25rem}.qc-emoji{font-size:1.5rem}.quiz-choice{padding:14px 10px}}
'''

# ── JS DU QUIZ + INTÉGRATION ────────────────────────────────────────────
QUIZ_JS = '''
/* ══════ QUIZ EN AMONT DU SWIPE ══════ */
var quizAns = {}, quizStep = 0;
var quizPickedDeck = null;  // si quiz rempli : pool pré-sélectionné

function quizSelect(step, val){
  quizAns[step] = val;
  var stepEl = document.getElementById("qstep"+step);
  if(stepEl){
    stepEl.querySelectorAll(".quiz-choice").forEach(c=>c.classList.remove("selected"));
    if(event && event.currentTarget) event.currentTarget.classList.add("selected");
  }
  setTimeout(function(){
    if(step < 5) quizGoStep(step+1);
    else quizFinish();
  }, 280);
}

function quizGoStep(n){
  document.querySelectorAll(".quiz-step").forEach(s=>s.classList.remove("active"));
  var s = document.getElementById("qstep"+n);
  if(s) s.classList.add("active");
  quizStep = n;
  for(var i=0;i<6;i++){
    var d = document.getElementById("qpdot"+i);
    if(d) d.className = "qp-dot" + (i<n?" done":i===n?" active":"");
  }
  window.scrollTo({top:0, behavior:"smooth"});
}

function quizSkip(){
  quizAns = {};
  quizPickedDeck = null;
  showSwipeUI();
  // Mode swipe libre (comportement actuel)
  restart();
}

function quizFinish(){
  // Calcul du score de chaque station selon les réponses
  var groupe = quizAns[0] || "amis";
  var niveau = quizAns[1] || "intermediaire";
  var budget = quizAns[2] || "moyen";
  var massif = quizAns[3] || "autre";
  var priorite = quizAns[4] || "neige";
  var horsSki = quizAns[5] || "peu_importe";

  function score(s){
    var sc = (s.score||0) * 20;
    // Groupe
    if(groupe==="famille" && (s.amb||[]).indexOf("famille")>-1) sc += 25;
    if(groupe==="famille" && (s.equip||[]).indexOf("garderie")>-1) sc += 15;
    if(groupe==="amis"    && (s.amb||[]).indexOf("festif")>-1)    sc += 25;
    if(groupe==="couple"  && (s.amb||[]).indexOf("village")>-1)   sc += 20;
    if(groupe==="couple"  && (s.amb||[]).indexOf("luxe")>-1)      sc += 15;
    if(groupe==="solo"    && (s.tags||[]).indexOf("rider")>-1)    sc += 15;
    // Niveau
    if(s.niv && s.niv.indexOf(niveau)>-1) sc += 25;
    if(niveau==="expert" && (s.tags||[]).indexOf("rider")>-1) sc += 20;
    if(niveau==="debutant" && s.pistes && (s.pistes.v||0)>=8) sc += 15;
    // Budget
    if(budget==="eco"){
      if(s.forfait<=25) sc += 30;
      else sc -= Math.max(0, (s.forfait-25)*2);
    }
    if(budget==="moyen" && s.forfait>=25 && s.forfait<=40) sc += 20;
    if(budget==="premium" && (s.amb||[]).indexOf("luxe")>-1) sc += 30;
    // Massif
    if(massif==="alpes_nord" && s.massif==="Alpes du Nord") sc += 25;
    if(massif==="alpes_sud"  && s.massif==="Alpes du Sud")  sc += 25;
    if(massif==="pyrenees"   && s.massif==="Pyr\\u00e9n\\u00e9es")    sc += 25;
    // Priorité
    if(priorite==="neige" && s.alt_max>=2000) sc += 20;
    if(priorite==="neige" && s.alt_max>=2500) sc += 10;
    if(priorite==="ambiance" && (s.amb||[]).indexOf("festif")>-1) sc += 25;
    if(priorite==="nature"   && (s.amb||[]).indexOf("nature")>-1) sc += 25;
    if(priorite==="domaine"  && s.km>=200) sc += 25;
    if(priorite==="domaine"  && s.km>=100 && s.km<200) sc += 15;
    // Hors-ski
    if(horsSki==="restaurants" && (s.equip||[]).indexOf("restaurants")>-1) sc += 20;
    if(horsSki==="restaurants" && (s.amb||[]).indexOf("luxe")>-1) sc += 10;
    if(horsSki==="spa" && (s.equip||[]).indexOf("spa")>-1) sc += 25;
    if(horsSki==="spa" && (s.amb||[]).indexOf("luxe")>-1) sc += 10;
    if(horsSki==="shopping" && (s.amb||[]).indexOf("luxe")>-1) sc += 20;
    return sc;
  }

  var scored = RAW_DATA.map(s => ({s:s, sc:score(s)})).sort((a,b)=>b.sc-a.sc);
  // Top 8 mais on mélange légèrement les positions 3-8 pour pas que ce soit toujours le même podium
  var top = scored.slice(0, 8).map(x => x.s);
  // Shuffle léger des positions 3-7 pour effet "surprise" tout en gardant le podium
  var head = top.slice(0, 2);
  var tail = top.slice(2).sort(()=>Math.random()-.5);
  quizPickedDeck = head.concat(tail);

  showSwipeUI();
  // restart() utilisera quizPickedDeck via buildDeck()
  restart();
}

function showSwipeUI(){
  document.getElementById("quizScreen").classList.remove("show");
  document.getElementById("mainContent").style.display = "block";
}

function showQuizUI(){
  document.getElementById("quizScreen").classList.add("show");
  document.getElementById("mainContent").style.display = "none";
  document.getElementById("endScreen").classList.remove("show");
  // Reset visuel du questionnaire
  quizAns = {}; quizStep = 0;
  document.querySelectorAll(".quiz-step").forEach(s=>s.classList.remove("active"));
  document.querySelectorAll(".quiz-choice").forEach(c=>c.classList.remove("selected"));
  document.getElementById("qstep0").classList.add("active");
  for(var i=0;i<6;i++){
    var d = document.getElementById("qpdot"+i);
    if(d) d.className = "qp-dot" + (i===0?" active":"");
  }
  window.scrollTo({top:0, behavior:"smooth"});
}
'''

# ── PATCH ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    fp = Path(args.root) / "tinder.html"
    if not fp.exists():
        print(f"❌ {fp} introuvable")
        return
    content = fp.read_text(encoding="utf-8")
    orig_size = len(content)

    if "quizScreen" in content:
        print("⚠️  Le quiz semble déjà présent (id=quizScreen trouvé). Aucune action.")
        return

    # 1. Injecter le HTML du quiz juste avant <div id="mainContent">
    main_content_idx = content.find('id="mainContent"')
    if main_content_idx < 0:
        print("❌ <div id=\"mainContent\"> introuvable")
        return
    # Remonter au <div correspondant
    div_start = content.rfind('<div', 0, main_content_idx)
    content = content[:div_start] + QUIZ_HTML + '\n\n' + content[div_start:]
    print(f"✓ HTML quiz injecté ({len(QUIZ_HTML):,} chars)")

    # 2. Injecter le CSS dans le <style>
    style_end = content.find('</style>')
    content = content[:style_end] + QUIZ_CSS + content[style_end:]
    print(f"✓ CSS quiz injecté ({len(QUIZ_CSS):,} chars)")

    # 3. Injecter le JS du quiz juste après la déclaration de `let allStations = []`
    anchor = "let allStations = [];"
    anchor_idx = content.find(anchor)
    if anchor_idx < 0:
        print("❌ Ancre JS introuvable")
        return
    content = content[:anchor_idx] + anchor + QUIZ_JS + content[anchor_idx+len(anchor):]
    print(f"✓ JS quiz injecté ({len(QUIZ_JS):,} chars)")

    # 4. Modifier buildDeck() pour utiliser quizPickedDeck quand disponible
    old_build = "function buildDeck(){\n  var pool = RAW_DATA.filter(s => s.score >= 3.8 && !profile.seen.includes(s.id));"
    new_build = """function buildDeck(){
  // Si quiz rempli, on swipe sur les 8 stations pré-sélectionnées (filtrant celles déjà vues)
  if(quizPickedDeck && quizPickedDeck.length){
    var picked = quizPickedDeck.filter(s => !profile.seen.includes(s.id));
    if(picked.length >= 2) return picked;
    // Si on a déjà swipé toutes celles du quiz, on bascule sur le mode général
  }
  var pool = RAW_DATA.filter(s => s.score >= 3.8 && !profile.seen.includes(s.id));"""
    if old_build not in content:
        print("❌ buildDeck() introuvable pour patch")
        return
    content = content.replace(old_build, new_build)
    print("✓ buildDeck() patchée pour utiliser quizPickedDeck")

    # 5. Cacher mainContent par défaut au chargement, et lancer showQuizUI
    # On ajoute un display:none initial sur #mainContent via style inline OU via JS
    # Approche : ajouter un onload ou un dernier script qui appelle showQuizUI()
    # Cherchons le DOMContentLoaded existant ou le dernier appel restart()

    # Le plus simple : ajouter à la toute fin du body, avant </body>, un script qui cache mainContent et montre le quiz
    body_close = content.rfind('</body>')
    init_script = '''
<script>
// Affiche le quiz au chargement (cache le swipe par défaut)
(function(){
  var main = document.getElementById("mainContent");
  if(main) main.style.display = "none";
  var quiz = document.getElementById("quizScreen");
  if(quiz) quiz.classList.add("show");
})();
</script>
'''
    content = content[:body_close] + init_script + content[body_close:]
    print(f"✓ Script d'init injecté ({len(init_script)} chars)")

    # 6. Modifier le bouton "🔄 Recommencer" pour relancer le quiz (et pas direct le swipe)
    # On cherche restart-btn et son onclick
    # Le restart() actuel relance directement le swipe
    # On veut que le bouton final lance showQuizUI()
    # Cherchons : <button class="restart-btn" onclick="restart()">
    old_restart_btn = re.search(r'<button class="restart-btn"[^>]*onclick="restart\(\)"[^>]*>([^<]*)</button>', content)
    if old_restart_btn:
        new_btn_html = '<button class="restart-btn" onclick="showQuizUI()">🔄 Refaire le questionnaire</button>'
        content = content.replace(old_restart_btn.group(0), new_btn_html, 1)
        print(f"✓ Bouton 'Recommencer' réorienté vers showQuizUI()")
    else:
        print("⚠️  Bouton 'Recommencer' introuvable (à vérifier manuellement)")

    fp.write_text(content, encoding="utf-8")
    new_size = len(content)
    print(f"\n📄 {fp.name} : {orig_size:,} → {new_size:,} octets ({new_size-orig_size:+,})")


if __name__ == "__main__":
    main()
