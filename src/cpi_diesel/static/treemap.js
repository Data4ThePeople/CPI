/* CPI diesel-exposure treemap.

   Vanilla canvas, no libraries and no external requests -- the house pattern
   from NFP_Treemap. The payload is inlined by build.py as window.PAYLOAD.

   Two nested squarified treemaps: the eight major CPI groups fill the canvas,
   then each group's categories fill its rectangle. Area is relative
   importance, so every pixel is a consistent share of the index. */
(function () {
  "use strict";

  var P = window.PAYLOAD;
  var REC = P.records, SUM = P.summary;

  var TIER_COLOR = {
    light_freight: "#cfe0e8",
    freight_dependent_service: "#a8c6d4",
    heavy_freight: "#7aa7bd",
    cold_chain: "#4d84a3",
    diesel_service: "#2e6485",
    direct_diesel: "#17455f",
    gasoline_direct: "#712b13",
    other_fuel: "#b9a06a",
    none: "#e2dac4"
  };
  // Ramp order, palest to deepest, for the legend.
  var TIER_ORDER = [
    "direct_diesel", "diesel_service", "cold_chain", "heavy_freight",
    "freight_dependent_service", "light_freight",
    "gasoline_direct", "other_fuel", "none"
  ];
  var DIM = "#ece4cd", INK = "#2b2317", GRID = "#cdbb96", PANEL = "#f4ead2";

  var MODES = {
    all: {
      label: "Everything",
      shortLabel: "All",
      lit: function () { return true; },
      note: "All " + SUM.categories + " mutually exclusive CPI categories, " +
            "sized by their published relative importance. Together they are " +
            "the whole index."
    },
    gasoline: {
      label: "What gasoline touches",
      shortLabel: "Gasoline",
      lit: function (r) { return r.tier === "gasoline_direct"; },
      note: "<b>Gasoline is " + SUM.gasoline_direct + "% of the index</b> — " +
            "one box. Households buy it directly, and that direct purchase is " +
            "essentially its entire role in the CPI. It is not an input cost " +
            "hidden inside anything else here."
    },
    diesel: {
      label: "What diesel touches",
      shortLabel: "Diesel",
      lit: function (r) { return r.diesel_exposed; },
      note: "<b>Diesel reaches " + SUM.exposed_share + "% of the index</b>, " +
            "across " + SUM.exposed_count + " of " + SUM.categories +
            " categories — " + SUM.reach_ratio + "× gasoline's direct " +
            "weight. Households buy almost none of it: direct diesel is just " +
            SUM.diesel_direct + "%. It arrives inside the price of everything " +
            "that had to be moved."
    }
  };

  /* A framed page is sized by its parent, so it drops the masthead and the
     notes and gives the chart the room instead. Auto-detected, with
     `#embed=0` / `#embed=1` overriding -- a host that wants the full layout
     inside a frame (or the compact one standalone) can say so in the URL.

     window.CPI_STANDALONE is set by the artifact template, whose host frames
     the page but supplies its own document chrome; there the full layout is
     the right one. */
  var EMBEDDED = (function () {
    var flag = null;
    try {
      flag = new URLSearchParams(location.hash.slice(1)).get("embed");
    } catch (e) { /* no URLSearchParams: fall through to detection */ }
    if (flag === "0") return false;
    if (flag === "1") return true;
    if (window.CPI_STANDALONE) return false;
    try { return window.self !== window.top; } catch (e) { return true; }
  })();
  if (EMBEDDED) document.documentElement.classList.add("embed");

  /* Narrow is a property of the space the frame was given, not of the device.
     Measured, for the same reason the CSS uses container queries. */
  function isNarrow() {
    var wrap = document.querySelector(".wrap");
    return ((wrap && wrap.getBoundingClientRect().width) || window.innerWidth) < 620;
  }

  var mode = "all";
  var tiles = [];
  var canvas = document.getElementById("tm");
  var ctx = canvas.getContext("2d");
  var tip = document.getElementById("tip");
  var box = document.getElementById("chartbox");

  /* ---- data shaping ----------------------------------------------------- */

  // Pool the sub-threshold residuals into one tile per group. They stay in the
  // data for the sum invariant; this is presentation only.
  function grouped() {
    var out = [];
    P.major_order.forEach(function (g) {
      var mine = REC.filter(function (r) { return r.major_group === g; });
      var big = mine.filter(function (r) { return r.weight >= P.sliver_threshold; });
      var small = mine.filter(function (r) { return r.weight < P.sliver_threshold; });
      var items = big.slice();
      if (small.length) {
        var w = small.reduce(function (a, r) { return a + r.weight; }, 0);
        items.push({
          display_name: "Other small items",
          item_name: "Other small items",
          major_group: g,
          weight: Math.round(w * 1000) / 1000,
          tier: small[0].tier,
          tier_label: small[0].tier_label,
          diesel_exposed: small.every(function (r) { return r.diesel_exposed; }),
          narrative: small.length + " residual BLS lines too small to draw " +
            "separately, pooled here: " +
            small.map(function (r) { return r.display_name; }).join(", ") + ".",
          pooled: true
        });
      }
      items.sort(function (a, b) { return b.weight - a.weight; });
      out.push({
        name: g,
        weight: mine.reduce(function (a, r) { return a + r.weight; }, 0),
        items: items
      });
    });
    return out;
  }

  /* ---- squarified treemap ----------------------------------------------- */

  function worst(row, side, scale) {
    var s = 0, mn = Infinity, mx = 0;
    for (var i = 0; i < row.length; i++) {
      var v = row[i].weight * scale;
      s += v; if (v < mn) mn = v; if (v > mx) mx = v;
    }
    var s2 = s * s, side2 = side * side;
    return Math.max(side2 * mx / s2, s2 / (side2 * mn));
  }

  // Standard squarify (Bruls, Huizing, van Wijk). Returns [{node, x,y,w,h}].
  function squarify(nodes, x, y, w, h) {
    var out = [];
    var items = nodes.slice().sort(function (a, b) { return b.weight - a.weight; });
    var total = items.reduce(function (a, n) { return a + n.weight; }, 0);
    if (total <= 0 || w <= 0 || h <= 0) return out;
    var scale = (w * h) / total;

    var i = 0;
    while (i < items.length) {
      var side = Math.min(w, h);
      var row = [items[i]];
      i++;
      while (i < items.length &&
             worst(row.concat([items[i]]), side, scale) <= worst(row, side, scale)) {
        row.push(items[i]); i++;
      }
      var rowArea = row.reduce(function (a, n) { return a + n.weight * scale; }, 0);
      var thick = rowArea / side;
      var off = 0;
      for (var j = 0; j < row.length; j++) {
        var len = (row[j].weight * scale) / thick;
        if (w >= h) {
          out.push({ node: row[j], x: x, y: y + off, w: thick, h: len });
        } else {
          out.push({ node: row[j], x: x + off, y: y, w: len, h: thick });
        }
        off += len;
      }
      if (w >= h) { x += thick; w -= thick; } else { y += thick; h -= thick; }
    }
    return out;
  }

  /* ---- rendering -------------------------------------------------------- */

  var HEADER = 21;   // group label strip
  var GAP = 3;

  function layout(width, height) {
    tiles = [];
    squarify(grouped(), 0, 0, width, height).forEach(function (cell) {
      var gx = cell.x + GAP, gy = cell.y + GAP;
      var gw = Math.max(0, cell.w - GAP * 2), gh = Math.max(0, cell.h - GAP * 2);
      cell.label = { x: gx, y: gy, w: gw, h: Math.min(HEADER, gh) };
      var iy = gy + Math.min(HEADER, gh);
      var ih = Math.max(0, gh - Math.min(HEADER, gh));
      squarify(cell.node.items, gx, iy, gw, ih).forEach(function (t) {
        t.group = cell.node.name;
        tiles.push(t);
      });
      tiles.groups = tiles.groups || [];
      tiles.groups.push(cell);
    });
  }

  function fits(text, px, maxW) {
    ctx.font = px + "px Georgia, serif";
    return ctx.measureText(text).width <= maxW;
  }

  // Greedy word wrap. Returns null when the text will not fit in maxLines.
  function wrap(text, px, maxW, maxLines) {
    var words = text.split(" "), lines = [], cur = "";
    for (var i = 0; i < words.length; i++) {
      var trial = cur ? cur + " " + words[i] : words[i];
      if (fits(trial, px, maxW) || !cur) {
        cur = trial;
      } else {
        lines.push(cur);
        cur = words[i];
        if (lines.length === maxLines) return null;
      }
    }
    if (cur) lines.push(cur);
    if (lines.length > maxLines) return null;
    for (var j = 0; j < lines.length; j++) {
      if (!fits(lines[j], px, maxW)) return null;
    }
    return lines;
  }

  /* Measure the element, not the window. Inside the Prismic oEmbed the
     viewport does not describe the space the page is actually given. */
  function chartSize() {
    var wrap = document.querySelector(".wrap");
    var width = Math.round(
      (box && box.getBoundingClientRect().width) ||
      (wrap && wrap.getBoundingClientRect().width) ||
      window.innerWidth || 900
    );
    if (!EMBEDDED) {
      return { w: width, h: Math.round(Math.min(760, Math.max(460, width * 0.66))) };
    }
    /* Embedded, the height is whatever the flex column has left over after the
       fixed rows -- the parent frame's height is the budget, and the chart
       absorbs all of the slack. 220 is a floor for a very short frame. */
    var avail = Math.round(box.getBoundingClientRect().height);
    return { w: width, h: Math.max(220, avail) };
  }

  function draw() {
    var dpr = window.devicePixelRatio || 1;
    var size = chartSize();
    var width = size.w, height = size.h;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    layout(width, height);

    ctx.fillStyle = PANEL;
    ctx.fillRect(0, 0, width, height);

    var lit = MODES[mode].lit;

    tiles.forEach(function (t) {
      var on = lit(t.node);
      ctx.fillStyle = on ? TIER_COLOR[t.node.tier] : DIM;
      ctx.fillRect(t.x, t.y, Math.max(0, t.w - 1), Math.max(0, t.h - 1));

      // The gasoline tile is small and is the whole point of the comparison,
      // so it gets an outline that survives at any size.
      if (t.node.tier === "gasoline_direct" && mode !== "diesel") {
        ctx.strokeStyle = INK; ctx.lineWidth = 1.5;
        ctx.strokeRect(t.x + 0.75, t.y + 0.75, Math.max(0, t.w - 2.5), Math.max(0, t.h - 2.5));
      }
      if (!on || t.w < 38 || t.h < 20) return;

      var pad = 5, availW = t.w - pad * 2, availH = t.h - pad * 2;
      var sizes = [13, 12, 11, 10, 9, 8], lines = null, px = 0;
      for (var si = 0; si < sizes.length; si++) {
        var room = Math.floor(availH / (sizes[si] + 2));
        if (room < 1) continue;
        lines = wrap(t.node.display_name, sizes[si], availW, Math.min(3, room));
        if (lines) { px = sizes[si]; break; }
      }
      if (!lines) return;

      // Deep fills need light type; the pale end of the ramp needs dark.
      var deep = ["direct_diesel", "diesel_service", "cold_chain", "gasoline_direct"];
      ctx.fillStyle = deep.indexOf(t.node.tier) >= 0 ? "#faf3df" : INK;
      ctx.textBaseline = "top";
      var ty = t.y + pad;
      for (var li = 0; li < lines.length; li++) {
        ctx.font = px + "px Georgia, serif";
        ctx.fillText(lines[li], t.x + pad, ty);
        ty += px + 2;
      }
      // The share only earns its place once the label already fits.
      if (ty + px <= t.y + t.h - 2) {
        ctx.font = (px - 1) + "px Georgia, serif";
        ctx.globalAlpha = 0.75;
        ctx.fillText(t.node.weight.toFixed(2) + "%", t.x + pad, ty);
        ctx.globalAlpha = 1;
      }
    });

    (tiles.groups || []).forEach(function (cell) {
      var L = cell.label;
      if (L.h < 12) return;
      ctx.fillStyle = INK;
      ctx.font = "bold 13px Georgia, serif";
      ctx.textBaseline = "middle";
      var name = cell.node.name;
      if (ctx.measureText(name).width > L.w - 56) {
        ctx.font = "bold 11px Georgia, serif";
      }
      // A narrow group still must not bleed into its neighbour, so clip once
      // the smaller face is still too wide.
      if (ctx.measureText(name).width > L.w - 4) {
        while (name.length > 1 && ctx.measureText(name + "\u2026").width > L.w - 4) {
          name = name.slice(0, -1);
        }
        name += "\u2026";
      }
      var nameW = ctx.measureText(name).width;
      ctx.fillText(name, L.x + 1, L.y + L.h / 2);
      ctx.font = "11px Georgia, serif";
      ctx.fillStyle = "#6b5d3f";
      var pct = cell.node.weight.toFixed(1) + "%";
      var pw = ctx.measureText(pct).width;
      // Drop the share rather than collide with a long group name.
      if (nameW + pw + 14 <= L.w) ctx.fillText(pct, L.x + L.w - pw - 1, L.y + L.h / 2);
      ctx.strokeStyle = GRID; ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(L.x, L.y + L.h - 2); ctx.lineTo(L.x + L.w, L.y + L.h - 2);
      ctx.stroke();
    });
    ctx.textBaseline = "alphabetic";
  }

  /* ---- interaction ------------------------------------------------------ */

  function hit(mx, my) {
    for (var i = 0; i < tiles.length; i++) {
      var t = tiles[i];
      if (mx >= t.x && mx <= t.x + t.w && my >= t.y && my <= t.y + t.h) return t;
    }
    return null;
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  canvas.addEventListener("mousemove", function (e) {
    var r = canvas.getBoundingClientRect();
    var t = hit(e.clientX - r.left, e.clientY - r.top);
    if (!t) { tip.className = "tip"; return; }
    var n = t.node;
    tip.innerHTML =
      '<span class="tname">' + esc(n.display_name) + "</span>" +
      '<span class="tmeta">' + n.weight.toFixed(3) + "% of the CPI · " +
      esc(t.group) + " · " + esc(n.tier_label) + "</span>" +
      esc(n.narrative);
    tip.className = "tip on";
    var bw = box.clientWidth;
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var x = e.clientX - r.left + 16, y = e.clientY - r.top + 16;
    if (x + tw > bw) x = e.clientX - r.left - tw - 16;
    if (y + th > canvas.clientHeight) y = e.clientY - r.top - th - 16;
    tip.style.left = Math.max(0, x) + "px";
    tip.style.top = Math.max(0, y) + "px";
  });
  canvas.addEventListener("mouseleave", function () { tip.className = "tip"; });

  /* ---- chrome ----------------------------------------------------------- */

  function setMode(next) {
    mode = next;
    Array.prototype.forEach.call(
      document.querySelectorAll(".controls button"), function (b) {
        b.setAttribute("aria-pressed", String(b.dataset.mode === next));
      });
    document.getElementById("readout").innerHTML = MODES[next].note;
    draw();
  }

  function relabelControls() {
    var narrow = isNarrow();
    Array.prototype.forEach.call(
      document.querySelectorAll(".controls button"), function (b) {
        var m = MODES[b.dataset.mode];
        b.textContent = narrow ? m.shortLabel : m.label;
      });
  }

  function buildControls() {
    var host = document.getElementById("controls");
    ["all", "gasoline", "diesel"].forEach(function (key) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = MODES[key].label;
      b.dataset.mode = key;
      b.setAttribute("aria-pressed", String(key === mode));
      b.addEventListener("click", function () { setMode(key); });
      host.appendChild(b);
    });
  }

  function buildLegend() {
    var host = document.getElementById("legend");
    var byTier = SUM.by_tier;
    P.tiers.slice().sort(function (a, b) {
      return TIER_ORDER.indexOf(a.key) - TIER_ORDER.indexOf(b.key);
    }).forEach(function (t) {
      var s = byTier[t.key];
      var row = document.createElement("div");
      row.className = "row";
      row.innerHTML =
        '<span class="sw" style="background:' + TIER_COLOR[t.key] + '"></span>' +
        "<span><span class=\"lname\">" + esc(t.label) + "</span> " +
        '<span class="lwt">— ' + (s ? s.weight.toFixed(2) : "0.00") +
        '%<span class="lsuffix"> of the index</span></span><br>' +
        '<span class="blurb">' + esc(t.blurb) + "</span></span>";
      host.appendChild(row);
    });
  }

  buildControls();
  buildLegend();
  relabelControls();
  setMode("all");

  var pending;
  function refit() {
    clearTimeout(pending);
    pending = setTimeout(function () {
      relabelControls();
      draw();
    }, 120);
  }
  window.addEventListener("resize", refit);
  /* The frame can be resized without the window firing anything -- a responsive
     article column, or Prismic settling the oEmbed after load. Watch the box
     itself where the browser allows it. */
  if (window.ResizeObserver) {
    new ResizeObserver(refit).observe(box);
  }
})();
