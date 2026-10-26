/* Dark-only replacement for the vendored Blowfish appearance.js.

   The theme ships an appearance switcher backed by localStorage. This site
   has a single dark palette, so the class is pinned here and any leftover
   preference from the old switcher is discarded. Loaded in <head>, before the
   body paints, so dark mode never depends on a stored preference or on JS
   running after first paint. */
document.documentElement.classList.add("dark");

try {
  localStorage.removeItem("appearance");
} catch (e) {}

// Keep the browser UI (address bar) in sync with the page background.
var updateMeta = () => {
  var body = document.querySelector("body");
  var meta = document.querySelector('meta[name="theme-color"]');
  if (!body || !meta) return;
  meta.setAttribute("content", getComputedStyle(body).backgroundColor);
};

// Mermaid renders against the active theme; only the dark one exists here.
var updateMermaidTheme = () => {
  if (typeof mermaid === "undefined") return;

  var mermaids = document.querySelectorAll("pre.mermaid");
  mermaids.forEach((e) => {
    if (e.getAttribute("data-processed")) {
      // Already rendered: reset so mermaid can run again.
      e.removeAttribute("data-processed");
      e.innerHTML = e.getAttribute("data-graph");
    } else {
      // First run: remember the source for future renders.
      e.setAttribute("data-graph", e.textContent);
    }
  });

  if (typeof initMermaidDark === "function") initMermaidDark();
  mermaid.run();
};

window.addEventListener("DOMContentLoaded", () => {
  updateMeta();
  updateMermaidTheme();

  const scroller = document.getElementById("top-scroller");
  const footer = document.getElementById("site-footer");
  if (scroller && footer && scroller.getBoundingClientRect().top > footer.getBoundingClientRect().top) {
    scroller.hidden = true;
  }
});
