"use strict";

// Report data lives at the root of testmap_output/; the report assets live in
// report/, so each data file is one level up (PRD 8.1). Files that may be absent
// (report_content on a fresh run) resolve to null instead of failing.
const DATA_FILES = {
  index: "../index.json",
  triage: "../triage.json",
  analysis: "../analysis.json",
  metrics: "../metrics.json",
  meta: "../meta.json",
  reportContent: "../report_content.json",
};

const OPTIONAL = new Set(["reportContent"]);

async function loadData() {
  const entries = await Promise.all(
    Object.entries(DATA_FILES).map(async ([key, path]) => [key, await fetchJson(path, OPTIONAL.has(key))])
  );
  return Object.fromEntries(entries);
}

async function fetchJson(path, optional) {
  let response;
  try {
    response = await fetch(path);
  } catch (err) {
    if (optional) return null;
    throw err;
  }
  if (!response.ok) {
    if (optional) return null;
    throw new Error(`failed to load ${path}: ${response.status}`);
  }
  return response.json();
}

// ---- DOM helpers ----
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child == null) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

function section(title, ...children) {
  return el("section", {}, [el("h2", {}, title), ...children]);
}

// Build a table from a header list and rows of cell values (strings or nodes).
function table(headers, rows, opts = {}) {
  const head = el("thead", {}, el("tr", {}, headers.map((h) => el("th", {}, h))));
  const body = el("tbody", {}, rows.map((cells, i) =>
    el("tr", opts.rowClass ? { class: opts.rowClass(i) } : {}, cells.map((c) => el("td", {}, c)))
  ));
  return el("table", { class: "data" }, [head, body]);
}

function badge(text, kind) {
  return el("span", { class: `badge badge-${kind}` }, text);
}

function emptyNote(text) {
  return el("p", { class: "empty prose" }, text);
}

function pct(value) {
  return `${Math.round(value * 100)}%`;
}

// ---- Aggregation (derived client-side from analysis + triage + index) ----
function cellCounts(matrix) {
  const counts = { covered: 0, gap: 0, unspecified: 0, total: matrix.length };
  for (const cell of matrix) counts[cell.status] += 1;
  return counts;
}

function coverageOf(counts) {
  const denominator = counts.total - counts.unspecified;
  return denominator > 0 ? counts.covered / denominator : 0;
}

// One row per analyzed symbol with its file, priority, risk, coverage, and counts.
function symbolRows(data) {
  return Object.entries(data.analysis || {}).map(([id, entry]) => {
    const counts = cellCounts(entry.behavior_matrix || []);
    const triage = (data.triage || {})[id] || {};
    const index = (data.index || {})[id] || {};
    return {
      id,
      name: index.qualified_name || id,
      file: index.file_path || "(unknown)",
      priority: triage.priority || "low",
      risk: triage.score ?? 0,
      coverage: coverageOf(counts),
      counts,
      difficulty: entry.test_difficulty?.rating,
      hasErrorPaths: !!index.has_error_paths,
      spec: entry.spec,
      entry,
    };
  });
}

// Aggregate symbol rows by file.
function fileRows(rows) {
  const byFile = new Map();
  for (const row of rows) {
    const agg = byFile.get(row.file) || {
      file: row.file, covered: 0, gap: 0, unspecified: 0, total: 0, symbols: 0, topRisk: 0, topSymbol: "",
    };
    agg.covered += row.counts.covered;
    agg.gap += row.counts.gap;
    agg.unspecified += row.counts.unspecified;
    agg.total += row.counts.total;
    agg.symbols += 1;
    if (row.risk >= agg.topRisk) { agg.topRisk = row.risk; agg.topSymbol = row.name; }
    byFile.set(row.file, agg);
  }
  for (const agg of byFile.values()) {
    agg.coverage = coverageOf(agg);
  }
  return [...byFile.values()];
}

// Interpolate gap-red -> unspecified-amber -> covered-green across 0..1 coverage.
function coverageColor(coverage) {
  const stops = [
    [0.0, [201, 72, 47]],
    [0.5, [184, 134, 11]],
    [1.0, [47, 143, 91]],
  ];
  let [lo, hi] = [stops[0], stops[stops.length - 1]];
  for (let i = 0; i < stops.length - 1; i++) {
    if (coverage >= stops[i][0] && coverage <= stops[i + 1][0]) { lo = stops[i]; hi = stops[i + 1]; }
  }
  const span = hi[0] - lo[0] || 1;
  const t = (coverage - lo[0]) / span;
  const rgb = lo[1].map((c, i) => Math.round(c + (hi[1][i] - c) * t));
  return `rgb(${rgb.join(",")})`;
}

// ---- Sections ----
function renderHero(data) {
  const m = data.metrics || {};
  const grade = m.grade || "";
  const verdict = el("div", { class: "verdict" }, [
    el("div", { class: "score" }, [
      el("span", {}, String(m.composite_score ?? "—")),
      el("span", { class: "out-of" }, " / 100"),
    ]),
    el("div", { class: `grade grade-${grade.toLowerCase()}` }, grade),
  ]);
  const summary = el("div", { class: "summary" }, [
    el("div", { class: "title" }, "Behavioral coverage audit"),
    el("div", { class: "coverage" }, `${pct(m.coverage_pct ?? 0)} behavioral coverage`),
    el("div", { class: "target" }, data.meta?.target_dir ?? ""),
  ]);
  const hero = el("section", { class: "hero" }, [verdict, summary]);

  const narrative = data.reportContent?.narrative_summary;
  if (narrative && window.marked) {
    hero.appendChild(el("div", { class: "prose narrative", html: window.marked.parse(narrative) }));
  }
  return hero;
}

function renderKpis(data) {
  const m = data.metrics || {};
  const items = [
    ["Behavioral coverage", pct(m.coverage_pct ?? 0), false],
    ["Gaps", m.gap_cells ?? 0, (m.gap_cells ?? 0) > 0],
    ["Symbols analyzed", m.symbols_analyzed ?? 0, false],
    ["High-priority w/ gaps", m.high_priority_with_gaps ?? 0, (m.high_priority_with_gaps ?? 0) > 0],
    ["Brittle tests", m.brittle_test_count ?? 0, (m.brittle_test_count ?? 0) > 0],
    ["Unspecified cells", m.unspecified_cells ?? 0, (m.unspecified_cells ?? 0) > 0],
  ];
  const strip = el("div", { class: "kpis" },
    items.map(([label, value, flag]) =>
      el("div", { class: `kpi${flag ? " flag" : ""}` }, [
        el("div", { class: "value" }, String(value)),
        el("div", { class: "label" }, label),
      ])
    )
  );
  return section("Key metrics", strip);
}

function renderHeatmap(rows) {
  const files = fileRows(rows).sort((a, b) => a.coverage - b.coverage);
  const grid = el("div", { class: "heatmap" },
    files.map((f) => {
      const tile = el("div", {
        class: "tile",
        style: `background:${coverageColor(f.coverage)}`,
        title: `${f.file} — ${pct(f.coverage)} covered, ${f.gap} gaps`,
      }, [
        el("div", { class: "tile-pct" }, pct(f.coverage)),
        el("div", { class: "tile-file" }, f.file),
      ]);
      return tile;
    })
  );
  return section("Coverage heatmap", grid);
}

function renderScatter(rows) {
  const canvas = el("canvas", { id: "scatter", height: "320" });
  const wrap = el("div", { class: "chart-wrap" }, canvas);
  const sec = section("Risk vs. coverage", wrap);
  // Chart.js draws after the canvas is in the DOM; defer to the next frame.
  requestAnimationFrame(() => drawScatter(canvas, rows));
  return sec;
}

function drawScatter(canvas, rows) {
  if (!window.Chart) return;
  const color = { high: "#c9482f", medium: "#b8860b", low: "#6b6f76" };
  const byPriority = ["high", "medium", "low"].map((priority) => ({
    label: priority,
    data: rows.filter((r) => r.priority === priority).map((r) => ({ x: r.risk, y: r.coverage * 100, name: r.name })),
    backgroundColor: color[priority],
    pointRadius: 5,
    pointHoverRadius: 7,
  }));
  new window.Chart(canvas, {
    type: "scatter",
    data: { datasets: byPriority },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: "risk score" }, min: 0, max: 1 },
        y: { title: { display: true, text: "coverage %" }, min: 0, max: 100 },
      },
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.raw.name}: risk ${ctx.raw.x.toFixed(2)}, ${Math.round(ctx.raw.y)}% covered`,
          },
        },
      },
    },
  });
}

function renderFilesNeedingAttention(rows) {
  const files = fileRows(rows).filter((f) => f.gap > 0).sort((a, b) => b.gap - a.gap);
  if (!files.length) return section("Files needing attention", emptyNote("No gaps — every analyzed file is fully covered."));
  const body = files.map((f) => [f.file, String(f.gap), pct(f.coverage), f.topSymbol]);
  return section("Files needing attention",
    table(["File", "Gaps", "Coverage", "Highest-risk symbol"], body));
}

function renderBrittleDistribution(rows) {
  const byFile = new Map();
  for (const row of rows) {
    let brittle = 0;
    for (const cell of row.entry.behavior_matrix || []) {
      for (const t of cell.covering_tests || []) if (t.brittle) brittle += 1;
    }
    if (brittle) byFile.set(row.file, (byFile.get(row.file) || 0) + brittle);
  }
  const files = [...byFile.entries()].sort((a, b) => b[1] - a[1]);
  if (!files.length) return section("Brittle test distribution", emptyNote("No brittle tests detected."));
  return section("Brittle test distribution",
    table(["File", "Brittle tests"], files.map(([f, n]) => [f, String(n)])));
}

function renderDifficultyDistribution(rows) {
  const counts = { high: 0, medium: 0, low: 0 };
  for (const row of rows) if (row.difficulty in counts) counts[row.difficulty] += 1;
  const order = [["high", "Hard to test"], ["medium", "Moderate"], ["low", "Easy to test"]];
  const bars = el("div", { class: "dist" },
    order.map(([key, label]) => {
      const n = counts[key];
      const width = rows.length ? (n / rows.length) * 100 : 0;
      return el("div", { class: "dist-row" }, [
        el("div", { class: "dist-label" }, `${label} (${n})`),
        el("div", { class: "dist-track" }, el("div", { class: `dist-fill diff-${key}`, style: `width:${width}%` })),
      ]);
    })
  );
  return section("Test difficulty distribution", bars);
}

function renderFindings(rows) {
  const ranked = rows
    .map((r) => ({ ...r, impact: r.risk * r.counts.gap }))
    .filter((r) => r.counts.gap > 0)
    .sort((a, b) => b.impact - a.impact);
  if (!ranked.length) return section("Findings — what to fix", emptyNote("No gaps to fix."));
  const items = ranked.map((r) => {
    const prescriptions = (r.entry.behavior_matrix || [])
      .filter((c) => c.status === "gap" && c.test_prescription)
      .map((c) => el("li", {}, c.test_prescription));
    return el("div", { class: "finding" }, [
      el("div", { class: "finding-head" }, [
        el("span", { class: "finding-name" }, r.name),
        badge(r.priority, r.priority),
        el("span", { class: "finding-meta" }, `${r.counts.gap} gaps`),
      ]),
      el("ul", { class: "prose" }, prescriptions),
    ]);
  });
  return section("Findings — what to fix", ...items);
}

function renderUnspecified(rows) {
  const out = [];
  for (const row of rows) {
    for (const cell of row.entry.behavior_matrix || []) {
      if (cell.status === "unspecified") out.push([row.name, cell.input_class, cell.unspecified_reason || ""]);
    }
  }
  if (!out.length) return section("Unspecified behaviors — needs human decision", emptyNote("No unspecified behaviors."));
  return section("Unspecified behaviors — needs human decision",
    table(["Symbol", "Input class", "Why unspecified"], out));
}

function renderPrescriptions(rows) {
  const out = [];
  for (const row of rows) {
    for (const cell of row.entry.behavior_matrix || []) {
      if (cell.status === "gap") {
        out.push([row.name, badge(row.priority, row.priority), cell.input_class, cell.expected_behavior, cell.test_prescription || ""]);
      }
    }
  }
  if (!out.length) return section("Test prescriptions", emptyNote("No gaps — nothing to prescribe."));
  return section("Test prescriptions",
    table(["Symbol", "Priority", "Input class", "Expected behavior", "Prescription"], out));
}

function coverageBar(coverage) {
  return el("div", { class: "cov-bar" },
    el("div", { class: "cov-fill", style: `width:${coverage * 100}%;background:${coverageColor(coverage)}` }));
}

function renderCell(cell) {
  const detail = el("div", { class: "cell-detail" });
  if (cell.status === "covered") {
    for (const t of cell.covering_tests || []) {
      detail.appendChild(el("div", { class: `cov-test${t.brittle ? " brittle" : ""}` },
        t.brittle ? `${t.test_name} — brittle: ${t.brittle_reason || "implementation-coupled"}` : t.test_name));
    }
  } else if (cell.status === "gap") {
    if (cell.gap_note) detail.appendChild(el("div", { class: "cell-note" }, cell.gap_note));
    if (cell.test_prescription) detail.appendChild(el("div", { class: "cell-rx" }, `Rx: ${cell.test_prescription}`));
  } else if (cell.unspecified_reason) {
    detail.appendChild(el("div", { class: "cell-note" }, cell.unspecified_reason));
  }
  return el("div", { class: `cell status-${cell.status}`, "data-status": cell.status }, [
    el("div", { class: "cell-row" }, [
      el("span", { class: `dot dot-${cell.status}` }, ""),
      el("span", { class: "cell-input" }, cell.input_class),
      el("span", { class: "cell-behavior" }, cell.expected_behavior),
    ]),
    detail,
  ]);
}

function renderSymbol(row) {
  const c = row.counts;
  const head = el("summary", { class: "sym-head" }, [
    el("span", { class: "sym-name" }, row.name),
    badge(row.priority, row.priority),
    el("span", { class: "sym-counts" }, `${c.covered}/${c.gap}/${c.unspecified}`),
    coverageBar(row.coverage),
    el("span", { class: "sym-pct" }, pct(row.coverage)),
  ]);
  const meta = el("div", { class: "sym-meta prose" }, [
    row.spec ? el("p", { class: "sym-spec" }, row.spec) : null,
    row.difficulty ? el("p", { class: "sym-diff" },
      `Test difficulty: ${row.difficulty} — ${row.entry.test_difficulty?.signals_note || ""}`) : null,
  ]);
  const cells = el("div", { class: "cells" }, (row.entry.behavior_matrix || []).map(renderCell));
  return el("details", {
    class: "sym",
    "data-priority": row.priority,
    "data-haserror": String(row.hasErrorPaths),
    "data-hasgaps": String(c.gap > 0),
    "data-search": `${row.name} ${row.file} ${row.spec || ""}`.toLowerCase(),
  }, [head, meta, cells]);
}

function renderModule(file, rows) {
  const agg = fileRows(rows).find((f) => f.file === file);
  const head = el("summary", { class: "mod-head" }, [
    el("span", { class: "mod-name" }, file),
    coverageBar(agg.coverage),
    el("span", { class: "mod-pct" }, pct(agg.coverage)),
    el("span", { class: "mod-summary" },
      `${rows.length} symbols · ${agg.covered} cov / ${agg.gap} gap / ${agg.unspecified} unspec`),
  ]);
  const syms = el("div", { class: "syms" }, rows.map(renderSymbol));
  return el("details", { class: "mod", open: "", "data-file": file }, [head, syms]);
}

function renderMatrix(data, rows) {
  const byFile = new Map();
  for (const row of rows) {
    if (!byFile.has(row.file)) byFile.set(row.file, []);
    byFile.get(row.file).push(row);
  }
  const modules = [...byFile.keys()].sort().map((file) => renderModule(file, byFile.get(file)));
  const sec = section("Symbol coverage matrix",
    matrixControls(),
    matrixLegend(),
    el("div", { class: "matrix" }, modules),
    deferredStubs(data, rows));
  wireMatrixControls(sec);
  return sec;
}

function matrixControls() {
  const search = el("input", { class: "matrix-search", type: "search", placeholder: "Search symbol / file / spec…" });
  const chips = ["all", "has gaps", "fully covered", "high priority", "error paths"].map((label, i) =>
    el("button", { class: `chip${i === 0 ? " active" : ""}`, "data-filter": label }, label));
  const expand = el("button", { class: "chip ghost", "data-action": "expand" }, "Expand all");
  const collapse = el("button", { class: "chip ghost", "data-action": "collapse" }, "Collapse all");
  return el("div", { class: "matrix-controls" }, [search, el("div", { class: "chips" }, [...chips, expand, collapse])]);
}

function matrixLegend() {
  return el("div", { class: "legend prose" }, [
    el("span", {}, [el("span", { class: "dot dot-covered" }, ""), " covered — a test pins this behavior"]),
    el("span", {}, [el("span", { class: "dot dot-gap" }, ""), " gap — no meaningful test"]),
    el("span", {}, [el("span", { class: "dot dot-unspecified" }, ""), " unspecified — behavior ambiguous, needs a human decision"]),
    el("span", { class: "legend-formula" }, "coverage % = covered / (total − unspecified)"),
  ]);
}

function deferredStubs(data, rows) {
  const analyzedIds = new Set(rows.map((r) => r.id));
  const stubs = Object.entries(data.index || {})
    .filter(([id]) => !analyzedIds.has(id))
    .map(([, s]) => `${s.file_path}::${s.qualified_name}`)
    .sort();
  if (!stubs.length) return null;
  return el("details", { class: "deferred" }, [
    el("summary", {}, `Not yet analyzed (${stubs.length})`),
    el("div", { class: "stub-list prose" }, stubs.map((s) => el("div", { class: "stub" }, s))),
  ]);
}

function wireMatrixControls(sec) {
  const search = sec.querySelector(".matrix-search");
  const chips = [...sec.querySelectorAll(".chip[data-filter]")];
  const syms = [...sec.querySelectorAll(".sym")];
  let activeFilter = "all";

  function apply() {
    const q = search.value.trim().toLowerCase();
    for (const sym of syms) {
      const matchesSearch = !q || sym.dataset.search.includes(q);
      const matchesFilter =
        activeFilter === "all" ||
        (activeFilter === "has gaps" && sym.dataset.hasgaps === "true") ||
        (activeFilter === "fully covered" && sym.dataset.hasgaps === "false") ||
        (activeFilter === "high priority" && sym.dataset.priority === "high") ||
        (activeFilter === "error paths" && sym.dataset.haserror === "true");
      sym.style.display = matchesSearch && matchesFilter ? "" : "none";
    }
    // Hide modules with no visible symbols.
    for (const mod of sec.querySelectorAll(".mod")) {
      const visible = [...mod.querySelectorAll(".sym")].some((s) => s.style.display !== "none");
      mod.style.display = visible ? "" : "none";
    }
  }

  search.addEventListener("input", apply);
  for (const chip of chips) {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      activeFilter = chip.dataset.filter;
      apply();
    });
  }
  sec.querySelector('[data-action="expand"]').addEventListener("click", () =>
    syms.filter((s) => s.style.display !== "none").forEach((s) => (s.open = true)));
  sec.querySelector('[data-action="collapse"]').addEventListener("click", () =>
    syms.forEach((s) => (s.open = false)));
}

function render(data) {
  const root = document.getElementById("report");
  root.innerHTML = "";
  const rows = symbolRows(data);
  root.appendChild(renderHero(data));
  root.appendChild(renderKpis(data));
  root.appendChild(renderHeatmap(rows));
  root.appendChild(renderScatter(rows));
  root.appendChild(renderFilesNeedingAttention(rows));
  root.appendChild(renderBrittleDistribution(rows));
  root.appendChild(renderDifficultyDistribution(rows));
  root.appendChild(renderFindings(rows));
  root.appendChild(renderUnspecified(rows));
  root.appendChild(renderPrescriptions(rows));
  root.appendChild(renderMatrix(data, rows));
}

function renderError(message) {
  document.getElementById("report").innerHTML = `<p class="error">Could not render report: ${message}</p>`;
}

loadData().then(render).catch((err) => renderError(err.message));
