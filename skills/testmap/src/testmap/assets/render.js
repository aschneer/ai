"use strict";

// Report data lives at the root of testmap_output/; the report assets live in
// report/, so each data file is one level up (PRD 8.1). Files that may be absent
// (mutation, report_content on a fresh run) resolve to null instead of failing.
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
  const response = await fetch(path);
  if (!response.ok) {
    if (optional) return null;
    throw new Error(`failed to load ${path}: ${response.status}`);
  }
  return response.json();
}

function render(data) {
  const root = document.getElementById("report");
  root.innerHTML = "";
  root.appendChild(renderHero(data));
}

// Placeholder hero — full section rendering is built incrementally (PRD 8.2).
function renderHero(data) {
  const section = document.createElement("section");
  section.className = "hero";
  const metrics = data.metrics || {};
  section.innerHTML = `
    <h1>Testmap Report</h1>
    <p class="score">${metrics.composite_score ?? "—"} <span>${metrics.grade ?? ""}</span></p>
    <p class="meta">${data.meta?.target_dir ?? ""}</p>
  `;
  return section;
}

function renderError(message) {
  const root = document.getElementById("report");
  root.innerHTML = `<p class="error">Could not render report: ${message}</p>`;
}

loadData().then(render).catch((err) => renderError(err.message));
