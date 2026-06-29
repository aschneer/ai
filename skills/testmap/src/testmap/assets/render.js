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

function pct(value) {
  return `${Math.round(value * 100)}%`;
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

function render(data) {
  const root = document.getElementById("report");
  root.innerHTML = "";
  root.appendChild(renderHero(data));
  root.appendChild(renderKpis(data));
}

function renderError(message) {
  document.getElementById("report").innerHTML = `<p class="error">Could not render report: ${message}</p>`;
}

loadData().then(render).catch((err) => renderError(err.message));
