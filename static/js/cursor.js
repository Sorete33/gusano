(function () {
  if (window.matchMedia("(pointer: coarse)").matches) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var cursor = document.createElement("div");
  cursor.className = "custom-cursor";
  document.body.appendChild(cursor);
  document.body.classList.add("hide-cursor");

  var visible = false;
  var rafId = null;
  var pendingX = 0;
  var pendingY = 0;

  document.addEventListener("mousemove", function (e) {
    pendingX = e.clientX;
    pendingY = e.clientY;
    if (rafId) return;
    rafId = requestAnimationFrame(function () {
      rafId = null;
      if (!visible) {
        visible = true;
        cursor.style.opacity = "1";
      }
      cursor.style.transform =
        "translate(" + (pendingX - 4) + "px, " + (pendingY - 4) + "px)";
    });
  });

  document.addEventListener("mousedown", function () {
    cursor.classList.add("clicking");
  });

  document.addEventListener("mouseup", function () {
    cursor.classList.remove("clicking");
  });

  document.addEventListener("mouseleave", function () {
    visible = false;
    cursor.style.opacity = "0";
  });

  document.addEventListener("mouseenter", function () {
    visible = true;
    cursor.style.opacity = "1";
  });
})();
