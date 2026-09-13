(function () {
  var key = "sendtomac-theme";
  function night() {
    return document.documentElement.dataset.theme === "night";
  }
  function paint() {
    var on = night();
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", on ? "#141311" : "#efece6");
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.setAttribute("aria-label", on ? "Switch to day" : "Night mode");
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (night()) document.documentElement.removeAttribute("data-theme");
      else document.documentElement.dataset.theme = "night";
      try { localStorage.setItem(key, night() ? "night" : "day"); } catch (e) {}
      paint();
    });
  });
  paint();
})();
