(() => {
  'use strict';
  const storageKey = 'badminton-practice-2026-11-15-v1';
  const topics = [...document.querySelectorAll('[data-topic]')];
  const lessons = [...document.querySelectorAll('[data-panel]')];
  const allowed = new Set(topics.map(button => button.dataset.topic));
  const completeButtons = [...document.querySelectorAll('[data-complete]')];
  const mission = document.getElementById('mission');
  const status = document.getElementById('practice-status');
  let done = new Set();
  let canSave = true;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '[]');
    if (Array.isArray(saved)) done = new Set(saved.filter(key => allowed.has(key)));
  } catch (_) { canSave = false; }
  const renderProgress = () => {
    document.getElementById('progress-count').textContent = `${done.size} / 5`;
    topics.forEach(button => {
      const completed = done.has(button.dataset.topic);
      button.classList.toggle('is-done', completed);
      button.querySelector('.topic-done').hidden = !completed;
    });
    completeButtons.forEach(button => {
      const completed = done.has(button.dataset.complete);
      button.setAttribute('aria-pressed', String(completed));
      button.textContent = completed ? '✓ 這組練過了 · 再按可取消' : '✓ 這組我練過了';
    });
    document.querySelectorAll('.completion-note').forEach(note => {
      note.textContent = canSave ? '標記只記錄試練進度，儲存在這部裝置。' : '這個瀏覽器無法儲存進度，離開頁面後標記可能消失。';
    });
    document.getElementById('reset-progress').hidden = done.size === 0;
  };
  const saveProgress = () => {
    try { localStorage.setItem(storageKey, JSON.stringify([...done])); }
    catch (_) { canSave = false; }
    renderProgress();
  };
  const selectLesson = (key, scroll = false) => {
    if (!allowed.has(key)) return;
    topics.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.topic === key)));
    lessons.forEach(panel => { panel.hidden = panel.dataset.panel !== key; });
    const panel = lessons.find(panel => panel.dataset.panel === key);
    document.getElementById('bottom-topic').textContent = panel.dataset.label;
    document.getElementById('bottom-watch').href = panel.dataset.video;
    document.getElementById('bottom-seconds').textContent = `看 ${panel.dataset.seconds} 秒重點`;
    if (scroll && window.matchMedia('(max-width: 759px)').matches) {
      mission.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
      panel.querySelector('h2').focus({preventScroll:true});
    }
  };
  topics.forEach(button => button.addEventListener('click', () => selectLesson(button.dataset.topic, true)));
  completeButtons.forEach(button => button.addEventListener('click', () => {
    const key = button.dataset.complete;
    if (done.has(key)) done.delete(key); else done.add(key);
    saveProgress();
    status.textContent = done.size === 5 ? '五項都試練過了！下次用同樣條件重測，再挑一項放進回合。' : `已試練 ${done.size} 項。下次用同樣條件再磨細一點。`;
  }));
  document.getElementById('reset-progress').addEventListener('click', () => {
    done.clear(); saveProgress(); status.textContent = '試練標記已清除，可以重新開始。';
  });
  selectLesson('grip');
  renderProgress();
})();
