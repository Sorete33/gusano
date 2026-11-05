window.A11yPanel = (() => {
  const FEATURES = {
    highContrast: {
      default: false,
      apply: (enabled) => {
        document.documentElement.classList.toggle("a11y-high-contrast", enabled);
      },
    },

    underlineLinks: {
      default: false,
      apply: (enabled) => {
        const existing = document.getElementById("a11y-underline-links");
        if (enabled && !existing) {
          const style = document.createElement("style");
          style.id = "a11y-underline-links";
          style.textContent = `
            a { text-decoration: underline !important; }
            .group-hover-card-title { text-decoration: underline !important; }
            .group-hover-card:hover .group-hover-card-title { text-decoration: underline !important; }`;
          document.head.appendChild(style);
        } else if (!enabled && existing) {
          existing.remove();
        }
      },
    },

    reduceMotion: {
      default: false,
      apply: (enabled) => {
        document.documentElement.classList.toggle("a11y-reduce-motion", enabled);
      },
    },

    dyslexiaFont: {
      default: false,
      apply: (enabled) => {
        document.documentElement.classList.toggle("a11y-dyslexia", enabled);
      },
    },

    textSpacing: {
      default: false,
      apply: (enabled) => {
        document.documentElement.classList.toggle("a11y-text-spacing", enabled);
      },
    },

    largeCursor: {
      default: false,
      reload: true,
      apply: (enabled) => {
        document.documentElement.classList.toggle("a11y-large-cursor", enabled);
        if (enabled) {
          document.querySelectorAll(".custom-cursor").forEach((node) => node.remove());
          document.documentElement.classList.remove("hide-cursor");
          document.body.classList.remove("hide-cursor");
        }
      },
    },

    fontSize: {
      default: "default",
      apply: (size) => {
        document.documentElement.style.fontSize = size === "default" ? "" : size;
      },
    },
  };

  let settings = null;

  const getSettings = () => {
    if (settings) return settings;
    const defaults = Object.fromEntries(Object.entries(FEATURES).map(([key, config]) => [key, config.default]));
    try {
      const saved = localStorage.getItem("a11ySettings");
      settings = { ...defaults, ...JSON.parse(saved || "{}") };
    } catch {
      settings = defaults;
    }
    return settings;
  };

  const updateSetting = (key, value) => {
    const current = getSettings();
    current[key] = value;
    try {
      localStorage.setItem("a11ySettings", JSON.stringify(current));
    } catch (e) {
      console.warn(`a11y.js: can not store settings: ${e}`);
    }
    FEATURES[key]?.apply(value);
    if (FEATURES[key]?.reload) {
      window.location.reload();
    }
  };

  const initPanel = (panelId) => {
    const prefix = panelId.replace("a11y-panel", "");
    const current = getSettings();

    Object.entries(FEATURES).forEach(([key, config]) => {
      const elementId = `${prefix}${key.replace(/([A-Z])/g, "-$1").toLowerCase()}`;
      const element = document.getElementById(elementId) || document.getElementById(`${elementId}-select`);

      if (element) {
        if (element.type === "checkbox") {
          element.checked = current[key];
          element.onchange = (e) => updateSetting(key, e.target.checked);
        } else if (element.tagName === "SELECT") {
          element.value = current[key];
          element.onchange = (e) => updateSetting(key, e.target.value);
        }
      }
    });

    const togglePanel = () => {
      const panel = document.getElementById(panelId);
      const overlay = document.getElementById(`${prefix}a11y-overlay`);
      const toggle = document.getElementById(`${prefix}a11y-toggle`);

      if (!panel || !overlay) return;

      const isHidden = overlay.classList.contains("hidden");
      overlay.classList.toggle("hidden");
      panel.classList.toggle("hidden");

      if (toggle) {
        toggle.setAttribute("aria-pressed", String(isHidden));
        toggle.setAttribute("aria-expanded", String(isHidden));
      }
    };

    const toggle = document.getElementById(`${prefix}a11y-toggle`);
    const close = document.getElementById(`${prefix}a11y-close`);
    const overlay = document.getElementById(`${prefix}a11y-overlay`);

    if (toggle) toggle.onclick = togglePanel;
    if (close) close.onclick = togglePanel;
    if (overlay) overlay.onclick = (e) => e.target === overlay && togglePanel();
  };

  const applyAll = () => {
    const current = getSettings();
    Object.entries(current).forEach(([key, value]) => {
      FEATURES[key]?.apply(value);
    });
  };

  const init = () => {
    applyAll();
    document.querySelectorAll('[id$="a11y-panel"]').forEach((panel) => {
      initPanel(panel.id);
    });
  };

  if (getSettings().largeCursor) {
    new MutationObserver(() => {
      document.querySelectorAll(".custom-cursor").forEach((node) => node.remove());
      document.documentElement.classList.remove("hide-cursor");
      document.body.classList.remove("hide-cursor");
    }).observe(document, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return {
    getSettings,
    updateSetting,
    addFeature: (name, config) => {
      FEATURES[name] = config;
      FEATURES[name].apply(getSettings()[name] || config.default);
    },
  };
})();