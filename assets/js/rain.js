(function () {
  const STORAGE_KEY = 'ag-rain';
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let container = null;
  let on = false;

  function createRain() {
    if (container) return;
    container = document.createElement('div');
    container.id = 'ag-rain';
    document.body.appendChild(container);

    const count = window.innerWidth < 768 ? 25 : 60;
    for (let i = 0; i < count; i++) {
      const img = document.createElement('img');
      img.src = '/images/lluvia.gif';
      img.alt = '';
      img.className = 'ag-drop';
      const size = 16 + Math.random() * 32;
      img.style.left = (Math.random() * 100) + 'vw';
      img.style.width = size + 'px';
      img.style.height = size + 'px';
      img.style.animationDuration = (3 + Math.random() * 4) + 's';
      img.style.animationDelay = (Math.random() * 5) + 's';
      img.style.setProperty('--drift', ((Math.random() - 0.5) * 120) + 'px');
      img.style.setProperty('--rot', ((Math.random() - 0.5) * 720) + 'deg');
      container.appendChild(img);
    }
  }

  function removeRain() {
    if (container) {
      container.remove();
      container = null;
    }
  }

  function updateButtons() {
    document.querySelectorAll('[data-rain-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function setOn(next) {
    if (REDUCED && next) return; // respect reduced motion
    on = !!next;
    try { localStorage.setItem(STORAGE_KEY, on ? '1' : '0'); } catch (e) {}
    if (on) createRain(); else removeRain();
    updateButtons();
  }

  function toggle() {
    setOn(!on);
  }

  window.AGRain = {
    isOn: function () { return on; },
    start: function () { setOn(true); },
    stop: function () { setOn(false); },
    toggle: toggle,
    setOn: setOn
  };

  // Initial state
  let initial = false;
  try { initial = localStorage.getItem(STORAGE_KEY) === '1'; } catch (e) {}
  if (new URLSearchParams(location.search).has('rain')) initial = true;
  if (REDUCED) initial = false;

  function wireButtons() {
    document.querySelectorAll('[data-rain-toggle]').forEach(function (btn) {
      if (btn.dataset.rainBound) return;
      btn.dataset.rainBound = '1';
      if (REDUCED) {
        btn.setAttribute('aria-disabled', 'true');
        btn.title = 'Lluvia desactivada (movimiento reducido)';
      }
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        if (REDUCED) return;
        toggle();
      });
    });
    updateButtons();
  }

  function init() {
    if (initial) setOn(true);
    else updateButtons();
    wireButtons();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();