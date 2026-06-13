/** Load gantt_data.json and render the chart. */

const DATA_URL = "gantt_data.json";

const LINK_ANCHORS = {
  FS: { from: "finish", to: "start" },
  SS: { from: "start", to: "start" },
  FF: { from: "finish", to: "finish" },
  SF: { from: "start", to: "finish" },
};

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

function barEdgePct(metrics, edge) {
  if (metrics.kind === "milestone") {
    return metrics.leftPct;
  }
  return edge === "start" ? metrics.leftPct : metrics.leftPct + metrics.widthPct;
}

function rowCenterY(rowEl) {
  return rowEl.offsetTop + rowEl.offsetHeight / 2;
}

function elbowPath(x1, y1, x2, y2) {
  const gap = 8;
  if (Math.abs(y1 - y2) < 1) {
    return `M ${x1} ${y1} H ${x2}`;
  }
  const bendX = Math.max(x1, x2) + gap;
  return `M ${x1} ${y1} H ${bendX} V ${y2} H ${x2}`;
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
  const timelineWidth = timeline.offsetWidth;
  const containerHeight = container.offsetHeight;
  if (!timelineWidth || !containerHeight) {
    return;
  }

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "dependency-lines");
  svg.setAttribute("width", String(timelineWidth));
  svg.setAttribute("height", String(containerHeight));
  svg.setAttribute("viewBox", `0 0 ${timelineWidth} ${containerHeight}`);

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
      const x1 = (barEdgePct(predEntry.metrics, anchors.from) / 100) * timelineWidth;
      const x2 = (barEdgePct(succEntry.metrics, anchors.to) / 100) * timelineWidth;
      const y1 = rowCenterY(predEntry.row);
      const y2 = rowCenterY(succEntry.row);

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", elbowPath(x1, y1, x2, y2));
      if (predEntry.item.is_critical && succEntry.item.is_critical) {
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
