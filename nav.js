/* Highlights the current section in the "On this page" list and keeps it in view on small screens. */
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  if (!links.length || !("IntersectionObserver" in window)) { return; }
  var map = {};
  links.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
  var visible = {};
  function update() {
    var best = null;
    links.forEach(function (a) { var id = a.getAttribute("href").slice(1); if (visible[id] && !best) { best = a; } });
    if (!best) { return; }
    links.forEach(function (a) { a.classList.toggle("active", a === best); if (a === best) { a.setAttribute("aria-current", "true"); } else { a.removeAttribute("aria-current"); } });
    var bar = best.closest(".toc");
    if (bar && bar.scrollWidth > bar.clientWidth) {
      bar.scrollTo({left: best.offsetLeft - 16, behavior: "smooth"});
    }
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });
    update();
  }, {rootMargin: "-120px 0px -55% 0px"});
  Object.keys(map).forEach(function (id) { var s = document.getElementById(id); if (s) { io.observe(s); } });
})();
