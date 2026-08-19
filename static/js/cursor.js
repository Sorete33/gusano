(function () {
  if (window.matchMedia("(pointer: coarse)").matches) return;

  var cursor = document.createElement("div");
  cursor.className = "custom-cursor";
  document.body.appendChild(cursor);
  document.body.classList.add("hide-cursor");

  var visible = false;

  document.addEventListener("mousemove", function (e) {
    if (!visible) {
      visible = true;
      cursor.style.opacity = "1";
    }
    cursor.style.transform =
      "translate(" + (e.clientX - 4) + "px, " + (e.clientY - 4) + "px)";
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
