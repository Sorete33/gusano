(function () {
  if (window.matchMedia("(pointer: coarse)").matches) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  function a11yLargeCursor() {
    try {
      var s = JSON.parse(localStorage.getItem("a11ySettings") || "{}");
      return !!(s && s.largeCursor);
    } catch (e) {
      return false;
    }
  }

  var STORAGE_KEY = "ag-cursor";
  var cursor = null;
  var rafId = null;
  var pendingX = 0;
  var pendingY = 0;
  var visible = false;

  var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  var lowEnd =
    (navigator.deviceMemory && navigator.deviceMemory <= 2) ||
    (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) ||
    (conn && conn.saveData);

  var enabled = true;
  try {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "0") enabled = false;
    if (saved === "1") enabled = true;
    if (saved === null && lowEnd) enabled = false;
    if (a11yLargeCursor()) enabled = false;
  } catch (e) {
    if (lowEnd) enabled = false;
  }

  function createCursor() {
    if (cursor) return;
    cursor = document.createElement("div");
    cursor.className = "custom-cursor";
    document.body.appendChild(cursor);
    document.documentElement.classList.add("hide-cursor");
    document.body.classList.add("hide-cursor");
    visible = false;
  }

  function destroyCursor() {
    if (cursor) {
      cursor.remove();
      cursor = null;
    }
    document.documentElement.classList.remove("hide-cursor");
    document.body.classList.remove("hide-cursor");
    visible = false;
  }

  function updateButtons() {
    document.querySelectorAll("[data-cursor-toggle]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", enabled ? "true" : "false");
    });
  }

  function setEnabled(next) {
    if (a11yLargeCursor()) {
      enabled = false;
      try { localStorage.setItem(STORAGE_KEY, "0"); } catch (e) {}
      destroyCursor();
      updateButtons();
      return;
    }
    enabled = !!next;
    try {
      localStorage.setItem(STORAGE_KEY, enabled ? "1" : "0");
    } catch (e) {}
    if (enabled) createCursor();
    else destroyCursor();
    updateButtons();
  }

  function toggle() {
    setEnabled(!enabled);
  }

  window.AGCursor = {
    isOn: function () { return enabled; },
    start: function () { setEnabled(true); },
    stop: function () { setEnabled(false); },
    toggle: toggle,
    setEnabled: setEnabled
  };

  document.addEventListener("mousemove", function (e) {
    if (!cursor) return;
    pendingX = e.clientX;
    pendingY = e.clientY;
    if (rafId) return;
    rafId = requestAnimationFrame(function () {
      rafId = null;
      if (!cursor) return;
      if (!visible) {
        visible = true;
        cursor.style.opacity = "1";
      }
      cursor.style.transform =
        "translate(" + (pendingX - 4) + "px, " + (pendingY - 4) + "px)";
    });
  });

  document.addEventListener("mousedown", function () {
    if (cursor) cursor.classList.add("clicking");
  });

  document.addEventListener("mouseup", function () {
    if (cursor) cursor.classList.remove("clicking");
  });

  document.addEventListener("mouseleave", function () {
    if (!cursor) return;
    visible = false;
    cursor.style.opacity = "0";
  });

  document.addEventListener("mouseenter", function () {
    if (!cursor) return;
    visible = true;
    cursor.style.opacity = "1";
  });

  function wireButtons() {
    document.querySelectorAll("[data-cursor-toggle]").forEach(function (btn) {
      if (btn.dataset.cursorBound) return;
      btn.dataset.cursorBound = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        toggle();
      });
    });
    updateButtons();
  }

  function init() {
    if (a11yLargeCursor()) {
      enabled = false;
      destroyCursor();
      wireButtons();
      updateButtons();
      document.querySelectorAll("[data-cursor-toggle]").forEach(function (btn) {
        btn.disabled = true;
        btn.title = "Cursor desactivado (cursor grande de accesibilidad)";
      });
      return;
    }
    if (enabled) createCursor();
    else destroyCursor();
    wireButtons();
    updateButtons();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();