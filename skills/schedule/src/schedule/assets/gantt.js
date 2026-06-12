/** Load gantt-data.json and render the chart. */

const DATA_URL = "gantt-data.json";

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

function renderRow(item, byId, rangeStart, totalDays) {
  const row = document.createElement("div");
  row.className = "row";

  const depth = itemDepth(item, byId);
  const label = document.createElement("div");
  label.className = "label";
  label.title = item.name;

  const kind = document.createElement("span");
  kind.className = "kind";
  kind.textContent = item.kind;

  const name = document.createTextNode(`${"  ".repeat(depth)}${item.name}`);
  const dates = document.createElement("div");
  dates.className = "dates";
  dates.textContent = dateLabel(item);

  label.append(kind, name, dates);

  const timeline = document.createElement("div");
  timeline.className = "timeline";
  const barArea = document.createElement("div");
  barArea.className = "bar-area";

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
    bar.style.left = `${leftPct.toFixed(2)}%`;
    if (item.kind === "milestone") {
      bar.classList.add("milestone");
    } else {
      bar.style.width = `${widthPct.toFixed(2)}%`;
    }
    barArea.appendChild(bar);
  }

  timeline.appendChild(barArea);
  row.append(label, timeline);
  return row;
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

  items.forEach((item) => {
    root.appendChild(renderRow(item, byId, range.start, totalDays));
  });
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
