/* Reads data/pm25.json and fills the readings table (air.html) and the
   snapshot (index.html). Values older than 24 hours are never shown. */
(function () {
  var TZ = "Asia/Karachi", MAX_AGE_H = 24;
  var fmt = new Intl.DateTimeFormat("en-GB", {timeZone: TZ, day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false});
  function when(iso) { return iso ? fmt.format(new Date(iso)) + " PKT" : "unknown"; }
  function ageH(iso) { return iso ? (Date.now() - new Date(iso).getTime()) / 3.6e6 : Infinity; }
  function $(id) { return document.getElementById(id); }
  function el(tag, text, cls) { var e = document.createElement(tag); if (text != null) e.textContent = text; if (cls) e.className = cls; return e; }
  function cell(tr, label, node) { var td = el("td"); td.setAttribute("data-label", label); if (typeof node === "string") td.textContent = node; else if (node) td.appendChild(node); tr.appendChild(td); return td; }
  var COLORS = {good:"#c8e6c9", moderate:"#fff59d", usg:"#ffcc80", unhealthy:"#ef9a9a", very_unhealthy:"#ce93d8", hazardous:"#6d1b2b"};

  if (!$("rows") && !$("snapshot-list") && !$("dist")) { return; }

  fetch("data/pm25.json", {cache: "no-cache"}).then(function (r) { return r.json(); }).then(function (d) {
    var cats = {}; ((d.scale || {}).categories || []).forEach(function (c) { cats[c.key] = c; });
    var dataStale = ageH(d.generated_utc) > MAX_AGE_H;
    var updatedText = d.generated_utc
      ? "Last updated " + when(d.generated_utc) + ". Values are 24-hour averages ending at that time."
      : "No data have been fetched yet.";
    if ($("updated")) { $("updated").textContent = updatedText; }
    if ($("foot-updated")) { $("foot-updated").textContent = when(d.generated_utc); }
    if (dataStale && d.generated_utc && $("stale")) {
      $("stale").hidden = false;
      $("stale").textContent = "The last update is more than 24 hours old, so values are hidden and shown as “no recent data”.";
    }

    var rows = $("rows"), list = $("snapshot-list"), prov = {}, shown = 0, counts = {}, hi = null, lo = null;
    if (rows) { rows.textContent = ""; }
    if (list) { list.textContent = ""; }

    (d.locations || []).forEach(function (loc) {
      var status = loc.status, value = loc.pm25_24h_mean, note = "";
      if (status === "ok" && (dataStale || ageH(loc.latest_hour_end_utc) > MAX_AGE_H)) { status = "no_recent_data"; }
      if (status === "manual_snapshot") { note = "Manual snapshot for the 24 hours ending " + when(loc.snapshot_period_end_utc) + ". This is not current data."; }
      var show = (status === "ok" || status === "manual_snapshot") && value != null;
      var c = show ? cats[loc.category] : null;
      var label = c ? c.label : (status === "insufficient_data" ? "Not enough data" : status === "error" ? "Error" : "No recent data");
      if (show && status === "ok") {
        shown++;
        counts[c.key] = (counts[c.key] || 0) + 1;
        var rec = {v: value, where: (loc.city || "") + ", " + (loc.display_name || "")};
        if (!hi || value > hi.v) { hi = rec; }
        if (!lo || value < lo.v) { lo = rec; }
      }

      if (list) {
        var li = el("li"), sw = el("i");
        sw.style.background = c ? COLORS[c.key] : "#eceff1";
        li.appendChild(sw);
        li.appendChild(el("span", (loc.city || "") + ": " + (show ? value.toFixed(1) + " µg/m³, " + label : label)));
        list.appendChild(li);
      }

      if (rows) {
        var tr = el("tr");
        cell(tr, "City", loc.city || "");
        var a = el("a", loc.display_name || "Location");
        if (loc.openaq_url) { a.href = loc.openaq_url; } else if (loc.source_url) { a.href = loc.source_url; }
        cell(tr, "Location", a);
        cell(tr, "24-hour average (µg/m³)", show ? value.toFixed(1) : "—").className = "num";
        cell(tr, "Category", el("span", label, "cat " + (c ? "c-" + c.key : "c-none")));
        var act = el("div");
        if (c && (c.action_sensitive || c.action_everyone)) {
          if (c.action_sensitive) { act.appendChild(el("div", "Sensitive groups: " + c.action_sensitive)); }
          if (c.action_everyone) { act.appendChild(el("div", "Everyone else: " + c.action_everyone)); }
        } else { act.textContent = "—"; }
        cell(tr, "What to do", act);
        var period = show && status === "ok"
          ? loc.hours_used + " of 24 hourly values; last reading ending " + when(loc.latest_hour_end_utc)
          : (note || loc.message || "No data in the last 24 hours.");
        cell(tr, "Data period", el("span", period, "small"));
        rows.appendChild(tr);
      }

      (loc.licenses || []).forEach(function (l) {
        var k = [loc.provider, l.attribution_name, l.name].join("|");
        prov[k] = (loc.provider || "Unknown provider") + " (owner: " + (l.attribution_name || loc.owner || "not stated") + "), licence " + (l.name || "not stated");
      });
    });

    var total = (d.locations || []).length;
    if ($("kpi-reporting")) { $("kpi-reporting").textContent = shown + " of " + total; }
    if ($("kpi-high")) { $("kpi-high").textContent = hi ? hi.v.toFixed(1) + " µg/m³" : "No current value"; $("kpi-high-where").textContent = hi ? hi.where : ""; }
    if ($("kpi-low")) { $("kpi-low").textContent = lo ? lo.v.toFixed(1) + " µg/m³" : "No current value"; $("kpi-low-where").textContent = lo ? lo.where : ""; }
    if ($("dist")) {
      var bar = $("dist"), leg = $("dist-legend"), parts = [];
      bar.textContent = ""; if (leg) { leg.textContent = ""; }
      ((d.scale || {}).categories || []).forEach(function (c) { if (counts[c.key]) { parts.push({label: c.label, n: counts[c.key], color: COLORS[c.key]}); } });
      if (total - shown > 0) { parts.push({label: "No current value", n: total - shown, color: "#eceff1"}); }
      parts.forEach(function (p) {
        var seg = el("span"); seg.style.width = (100 * p.n / total) + "%"; seg.style.background = p.color; seg.title = p.label + ": " + p.n;
        bar.appendChild(seg);
        if (leg) { var li = el("li"), sw = el("i"); sw.style.background = p.color; li.appendChild(sw); li.appendChild(el("span", p.label + ": " + p.n)); leg.appendChild(li); }
      });
      bar.setAttribute("aria-label", parts.map(function (p) { return p.label + ": " + p.n; }).join(", ") || "No data");
    }
    if ($("snapshot-count")) {
      $("snapshot-count").textContent = shown + " of " + (d.locations || []).length + " locations have a current 24-hour average.";
    }
    if ($("providers")) {
      var pv = Object.keys(prov).map(function (k) { return prov[k]; });
      $("providers").textContent = pv.length ? pv.join("; ") + ", via OpenAQ." : "not available.";
    }
  }).catch(function () {
    if ($("updated")) { $("updated").textContent = "The data file could not be loaded, so no readings are shown. Try again later."; }
    if ($("rows")) { $("rows").innerHTML = "<tr><td colspan='6'>No data available.</td></tr>"; }
    var total = (d.locations || []).length;
    if ($("kpi-reporting")) { $("kpi-reporting").textContent = shown + " of " + total; }
    if ($("kpi-high")) { $("kpi-high").textContent = hi ? hi.v.toFixed(1) + " µg/m³" : "No current value"; $("kpi-high-where").textContent = hi ? hi.where : ""; }
    if ($("kpi-low")) { $("kpi-low").textContent = lo ? lo.v.toFixed(1) + " µg/m³" : "No current value"; $("kpi-low-where").textContent = lo ? lo.where : ""; }
    if ($("dist")) {
      var bar = $("dist"), leg = $("dist-legend"), parts = [];
      bar.textContent = ""; if (leg) { leg.textContent = ""; }
      ((d.scale || {}).categories || []).forEach(function (c) { if (counts[c.key]) { parts.push({label: c.label, n: counts[c.key], color: COLORS[c.key]}); } });
      if (total - shown > 0) { parts.push({label: "No current value", n: total - shown, color: "#eceff1"}); }
      parts.forEach(function (p) {
        var seg = el("span"); seg.style.width = (100 * p.n / total) + "%"; seg.style.background = p.color; seg.title = p.label + ": " + p.n;
        bar.appendChild(seg);
        if (leg) { var li = el("li"), sw = el("i"); sw.style.background = p.color; li.appendChild(sw); li.appendChild(el("span", p.label + ": " + p.n)); leg.appendChild(li); }
      });
      bar.setAttribute("aria-label", parts.map(function (p) { return p.label + ": " + p.n; }).join(", ") || "No data");
    }
    if ($("snapshot-count")) { $("snapshot-count").textContent = "The data file could not be loaded, so no readings are shown."; }
    if ($("kpi-reporting")) { $("kpi-reporting").textContent = "No data"; }
    if ($("dist")) { $("dist").setAttribute("aria-label", "No data"); }
  });
})();
