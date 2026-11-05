(function () {
  const cfg = window.AG_CELEBRATION || {};
  const force = new URLSearchParams(location.search).has('rain');
  const onHome = location.pathname === '/' || location.pathname === '/index.html';
  if (!force && !onHome) return;
  if (!force) {
    if (!cfg.enabled) return;
    const now = Date.now();
    if (cfg.start && now < Date.parse(cfg.start)) return;
    if (cfg.end && now > Date.parse(cfg.end)) return;
  }
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches && !force;

  let container = null;
  if (!reducedMotion) {
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

  const banner = document.createElement('div');
  banner.id = 'ag-banner';
  banner.innerHTML =
    'Llegamos a los 100.000 visitantes subterráneos, muchas gracias a todes quienes forman parte de este terrario' +
    '<button type="button" id="ag-banner-close">Oki</button>';
  document.body.appendChild(banner);

  document.getElementById('ag-banner-close').addEventListener('click', () => {
    banner.remove();
    if (container) container.remove();
  });
})();
