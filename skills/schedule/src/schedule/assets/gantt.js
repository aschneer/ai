/** Load gantt_data.json and render the chart. */

const DATA_URL = "gantt_data.json";

const LINK_ANCHORS = {
  FS: { from: { edge: "finish", v: "center" }, to: { edge: "start", v: "top" } },
  SS: { from: { edge: "start", v: "top" }, to: { edge: "start", v: "top" } },
  FF: { from: { edge: "finish", v: "bottom" }, to: { edge: "finish", v: "bottom" } },
  SF: { from: { edge: "start", v: "center" }, to: { edge: "finish", v: "bottom" } },
};

const LINK_ARROW_INDENT = 8;

function parseDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function itemDepth(item, byId) {
  let level = 0;
  let parentId = item.parent_id;
  while (parentId != null) {
    level += 1;
    const parent = byId.get(parentId);
    if (!parent) {
      break;
    }
    parentId = parent.parent_id;
  }
  return level;
}

function dateLabel(item) {
  if (!item.start || !item.finish) {
    return "—";
  }
  if (item.kind === "milestone") {
    return item.start;
  }
  if (item.start === item.finish) {
    return item.start;
  }
  return `${item.start} → ${item.finish}`;
}

function dateRange(items) {
  const starts = items.filter((item) => item.start).map((item) => parseDate(item.start));
  const finishes = items.filter((item) => item.finish).map((item) => parseDate(item.finish));
  if (!starts.length || !finishes.length) {
    return null;
  }
  return {
    start: new Date(Math.min(...starts)),
    end: new Date(Math.max(...finishes)),
  };
}

function weekColumns(rangeStart, rangeEnd) {
  const columns = [];
  const current = new Date(rangeStart);
  current.setDate(current.getDate() - current.getDay());
  while (current <= rangeEnd) {
    const label = current.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    const week = document.createElement("div");
    week.className = "week";
    week.textContent = label;
    columns.push(week);
    current.setDate(current.getDate() + 7);
  }
  return columns;
}

function barAnchor(rowEl, edge, vertical, timelineRect, containerRect) {
  const bar = rowEl.querySelector(".bar");
  if (!bar) {
    return null;
  }
  const barRect = bar.getBoundingClientRect();
  let x = (edge === "start" ? barRect.left : barRect.right) - timelineRect.left;
  if (edge === "start") {
    x += LINK_ARROW_INDENT;
  }
  let y = barRect.top;
  if (vertical === "center") {
    y = barRect.top + barRect.height / 2;
  } else if (vertical === "bottom") {
    y = barRect.bottom;
  }
  y -= containerRect.top;
  return { x, y };
}

/** MS Project-style: horizontal to target column, vertical into top/bottom anchor. */
function dependencyPath(x1, y1, x2, y2) {
  if (Math.abs(y1 - y2) < 1) {
    return `M ${x1} ${y1} H ${x2}`;
  }
  return `M ${x1} ${y1} H ${x2} V ${y2}`;
}

function addDependencyArrowMarkers(svg) {
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  for (const [id, fill] of [
    ["dependency-arrow", "#aaa"],
    ["dependency-arrow-critical", "#c0392b"],
  ]) {
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    marker.setAttribute("id", id);
    marker.setAttribute("markerWidth", "8");
    marker.setAttribute("markerHeight", "8");
    marker.setAttribute("refX", "8");
    marker.setAttribute("refY", "4");
    marker.setAttribute("orient", "auto");
    marker.setAttribute("markerUnits", "userSpaceOnUse");
    const head = document.createElementNS("http://www.w3.org/2000/svg", "path");
    head.setAttribute("d", "M0,0 L8,4 L0,8 Z");
    head.setAttribute("fill", fill);
    marker.appendChild(head);
    defs.appendChild(marker);
  }
  svg.appendChild(defs);
}

function renderRow(item, byId, rangeStart, totalDays) {
  const depth = itemDepth(item, byId);
  const row = document.createElement("div");
  row.className = `row ${item.kind}`;

  const label = document.createElement("div");
  label.className = `label ${item.kind}`;
  label.title = `${item.kind}: ${item.name}`;
  label.style.paddingLeft = `${0.75 + depth * 1.25}rem`;

  const name = document.createElement("span");
  name.className = "item-name";
  name.textContent = item.name;
  const dates = document.createElement("div");
  dates.className = "dates";
  dates.textContent = dateLabel(item);

  label.append(name, dates);

  const timeline = document.createElement("div");
  timeline.className = "timeline";
  const barArea = document.createElement("div");
  barArea.className = "bar-area";

  let metrics = null;
  if (item.start && item.finish && totalDays > 0) {
    const start = parseDate(item.start);
    const finish = parseDate(item.finish);
    const offsetDays = Math.round((start - rangeStart) / (1000 * 60 * 60 * 24));
    const spanDays = Math.max(
      Math.round((finish - start) / (1000 * 60 * 60 * 24)) + 1,
      1,
    );
    const leftPct = (offsetDays / totalDays) * 100;
    const widthPct = (spanDays / totalDays) * 100;

    const bar = document.createElement("div");
    bar.className = `bar ${item.kind}`;
    if (item.is_critical) {
      bar.classList.add("critical");
    }
    bar.style.left = `${leftPct.toFixed(2)}%`;
    if (item.kind === "milestone") {
      bar.classList.add("milestone");
    } else {
      bar.style.width = `${widthPct.toFixed(2)}%`;
    }
    barArea.appendChild(bar);
    metrics = { leftPct, widthPct, kind: item.kind };
  }

  timeline.appendChild(barArea);
  row.append(label, timeline);
  return { row, metrics, item };
}

function renderDependencyLines(items, rowEntries, container) {
  const drawable = rowEntries.filter((entry) => entry.metrics);
  if (!drawable.length) {
    return;
  }

  const timeline = drawable[0].row.querySelector(".timeline");
  const timelineRect = timeline.getBoundingClientRect();
  const timelineWidth = timelineRect.width;
  const containerRect = container.getBoundingClientRect();
  const containerHeight = containerRect.height;
  if (!timelineWidth || !containerHeight) {
    return;
  }

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "dependency-lines");
  svg.setAttribute("width", String(timelineWidth));
  svg.setAttribute("height", String(containerHeight));
  svg.setAttribute("viewBox", `0 0 ${timelineWidth} ${containerHeight}`);
  addDependencyArrowMarkers(svg);

  const byId = new Map(drawable.map((entry) => [entry.item.id, entry]));

  for (const item of items) {
    const predecessors = item.predecessors || [];
    const succEntry = byId.get(item.id);
    if (!succEntry) {
      continue;
    }

    for (const pred of predecessors) {
      const predEntry = byId.get(pred.task_id);
      if (!predEntry) {
        continue;
      }

      const anchors = LINK_ANCHORS[pred.link_type] || LINK_ANCHORS.FS;
      const from = barAnchor(
        predEntry.row,
        anchors.from.edge,
        anchors.from.v,
        timelineRect,
        containerRect,
      );
      const to = barAnchor(
        succEntry.row,
        anchors.to.edge,
        anchors.to.v,
        timelineRect,
        containerRect,
      );
      if (!from || !to) {
        continue;
      }

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", dependencyPath(from.x, from.y, to.x, to.y));
      const isCritical =
        predEntry.item.is_critical && succEntry.item.is_critical;
      path.setAttribute(
        "marker-end",
        isCritical ? "url(#dependency-arrow-critical)" : "url(#dependency-arrow)",
      );
      if (isCritical) {
        path.classList.add("critical");
      }
      svg.appendChild(path);
    }
  }

  if (svg.childNodes.length) {
    container.appendChild(svg);
  }
}

function renderGantt(data) {
  document.getElementById("title").textContent = data.title || "Schedule";
  document.getElementById("project-finish").textContent =
    `Project finish: ${data.project_finish || "—"}`;

  const root = document.getElementById("gantt-root");
  root.replaceChildren();

  const items = data.items || [];
  const range = dateRange(items);
  if (!range) {
    root.textContent = "No scheduled items to display.";
    return;
  }

  const totalDays =
    Math.round((range.end - range.start) / (1000 * 60 * 60 * 24)) + 1;
  const byId = new Map(items.map((item) => [item.id, item]));

  const header = document.createElement("div");
  header.className = "row header";
  const headerLabel = document.createElement("div");
  headerLabel.className = "label";
  headerLabel.textContent = "Item";
  const headerTimeline = document.createElement("div");
  headerTimeline.className = "timeline";
  const headerWeeks = document.createElement("div");
  headerWeeks.className = "timeline-header";
  weekColumns(range.start, range.end).forEach((week) => headerWeeks.appendChild(week));
  headerTimeline.appendChild(headerWeeks);
  header.append(headerLabel, headerTimeline);
  root.appendChild(header);

  const rowEntries = [];
  items.forEach((item) => {
    const entry = renderRow(item, byId, range.start, totalDays);
    root.appendChild(entry.row);
    rowEntries.push(entry);
  });

  renderDependencyLines(items, rowEntries, root);
}

function showError(message) {
  const error = document.getElementById("error");
  error.hidden = false;
  error.textContent = message;
}

async function init() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) {
      throw new Error(`Could not load ${DATA_URL} (${response.status})`);
    }
    const data = await response.json();
    renderGantt(data);
  } catch (err) {
    showError(err.message);
  }
}

init();
