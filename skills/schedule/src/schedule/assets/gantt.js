/** Load gantt_data.json and render the chart. */

const DATA_URL = "gantt_data.json";

const LINK_ANCHORS = {
  FS: { from: { edge: "finish", v: "center" }, to: { edge: "start", v: "top" } },
  SS: { from: { edge: "start", v: "top" }, to: { edge: "start", v: "top" } },
  FF: { from: { edge: "finish", v: "bottom" }, to: { edge: "finish", v: "bottom" } },
  SF: { from: { edge: "start", v: "center" }, to: { edge: "finish", v: "bottom" } },
};

const LINK_ARROW_INDENT = 8;
const LABEL_WIDTH_MIN = 120;
const LABEL_WIDTH_MAX = 720;

let chartData = null;

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

function eachDay(rangeStart, rangeEnd) {
  const days = [];
  const current = new Date(rangeStart);
  while (current <= rangeEnd) {
    days.push(new Date(current));
    current.setDate(current.getDate() + 1);
  }
  return days;
}

const WEEKDAY_LETTERS = ["S", "M", "T", "W", "T", "F", "S"];

function headerSpans(days, spanKey, labelFn) {
  const spans = [];
  let index = 0;
  while (index < days.length) {
    const key = spanKey(days[index]);
    let count = 1;
    while (index + count < days.length && spanKey(days[index + count]) === key) {
      count += 1;
    }
    spans.push({ label: labelFn(days[index]), count });
    index += count;
  }
  return spans;
}

function boundaryClass(day, index, days) {
  if (index === 0) {
    return "";
  }
  if (day.getFullYear() !== days[index - 1].getFullYear()) {
    return "year-start";
  }
  if (day.getMonth() !== days[index - 1].getMonth()) {
    return "month-start";
  }
  return "";
}

function appendGridSpan(header, className, gridRow, col, spanCount, label, startDay, previousDay) {
  const cell = document.createElement("div");
  cell.className = className;
  cell.style.gridColumn = `${col} / span ${spanCount}`;
  cell.style.gridRow = String(gridRow);
  cell.textContent = label;
  if (previousDay) {
    const boundary = boundaryClass(startDay, 1, [previousDay, startDay]);
    if (boundary) {
      cell.classList.add(boundary);
    }
  }
  header.appendChild(cell);
}

function appendGridDay(header, className, gridRow, col, day, index, days, valueFn) {
  const cell = document.createElement("div");
  cell.className = className;
  cell.style.gridColumn = String(col);
  cell.style.gridRow = String(gridRow);
  const dayOfWeek = day.getDay();
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    cell.classList.add("weekend");
  }
  const boundary = boundaryClass(day, index, days);
  if (boundary) {
    cell.classList.add(boundary);
  }
  if (index === days.length - 1) {
    cell.classList.add("last-col");
  }
  cell.textContent = valueFn(day);
  header.appendChild(cell);
}

function buildTimelineHeader(rangeStart, rangeEnd) {
  const header = document.createElement("div");
  header.className = "timeline-header";
  const days = eachDay(rangeStart, rangeEnd);
  header.style.setProperty("--day-count", String(days.length));

  let col = 1;
  for (const span of headerSpans(
    days,
    (day) => day.getFullYear(),
    (day) => String(day.getFullYear()),
  )) {
    appendGridSpan(
      header,
      "header-span year-cell",
      1,
      col,
      span.count,
      span.label,
      days[col - 1],
      col > 1 ? days[col - 2] : null,
    );
    col += span.count;
  }

  col = 1;
  for (const span of headerSpans(
    days,
    (day) => `${day.getFullYear()}-${day.getMonth()}`,
    (day) => day.toLocaleDateString(undefined, { month: "long" }),
  )) {
    appendGridSpan(
      header,
      "header-span month-cell",
      2,
      col,
      span.count,
      span.label,
      days[col - 1],
      col > 1 ? days[col - 2] : null,
    );
    col += span.count;
  }

  days.forEach((day, index) => {
    const colNum = index + 1;
    appendGridDay(header, "day-col day-cell", 3, colNum, day, index, days, (d) =>
      String(d.getDate()),
    );
    appendGridDay(
      header,
      "day-col weekday-cell",
      4,
      colNum,
      day,
      index,
      days,
      (d) => WEEKDAY_LETTERS[d.getDay()],
    );
  });

  return header;
}

function remPx() {
  return parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
}

function timelineGutterPx() {
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--timeline-gutter").trim();
  if (!raw) {
    return 0;
  }
  if (raw.endsWith("rem")) {
    return parseFloat(raw) * remPx();
  }
  if (raw.endsWith("px")) {
    return parseFloat(raw);
  }
  return parseFloat(raw) || 0;
}

function chartColors() {
  const styles = getComputedStyle(document.documentElement);
  const token = (name) => styles.getPropertyValue(`--color-${name}`).trim();
  return {
    task: token("task"),
    group: token("group"),
    milestone: token("milestone"),
    critical: token("critical"),
    link: token("link"),
  };
}

function itemMetrics(item, rangeStart, totalDays) {
  if (!item.start || !item.finish || totalDays <= 0) {
    return null;
  }
  const start = parseDate(item.start);
  const finish = parseDate(item.finish);
  const offsetDays = Math.round((start - rangeStart) / (1000 * 60 * 60 * 24));
  const spanDays = Math.max(
    Math.round((finish - start) / (1000 * 60 * 60 * 24)) + 1,
    1,
  );
  return {
    leftPct: (offsetDays / totalDays) * 100,
    widthPct: (spanDays / totalDays) * 100,
    kind: item.kind,
  };
}

function timelineBox(rowEl, containerTop) {
  const timeline = rowEl.querySelector(".timeline");
  const rect = timeline.getBoundingClientRect();
  return {
    top: rect.top - containerTop,
    height: rect.height,
    width: rect.width,
  };
}

function barGeometry(entry, box, timelineWidth) {
  const { metrics, item } = entry;
  if (!metrics) {
    return null;
  }
  const rem = remPx();
  const gutter = timelineGutterPx();
  const plotWidth = Math.max(timelineWidth - gutter, 1);
  const left = gutter + (metrics.leftPct / 100) * plotWidth;
  const width = Math.max((metrics.widthPct / 100) * plotWidth, 2);

  if (item.kind === "milestone") {
    return {
      kind: "milestone",
      cx: left,
      cy: box.top + box.height / 2,
      r: 7,
      item,
    };
  }

  if (item.kind === "group") {
    const y = box.top + 0.3 * rem;
    return {
      kind: "group",
      x: left,
      y,
      width,
      legH: 10,
      item,
    };
  }

  const areaTop = box.top + 0.3 * rem;
  const areaHeight = box.height - 0.6 * rem;
  return {
    kind: "task",
    x: left,
    y: areaTop + 0.25 * rem,
    width,
    height: Math.max(areaHeight - 0.5 * rem, 4),
    item,
  };
}

function anchorFromGeometry(geom, edge, vertical) {
  if (geom.kind === "milestone") {
    return { x: geom.cx, y: geom.cy };
  }

  if (geom.kind === "group") {
    let x = edge === "start" ? geom.x : geom.x + geom.width;
    let y = vertical === "top" ? geom.y : geom.y + geom.legH / 2;
    if (edge === "start") {
      x += LINK_ARROW_INDENT;
    }
    return { x, y };
  }

  let x = edge === "start" ? geom.x : geom.x + geom.width;
  let y = geom.y;
  if (vertical === "center") {
    y = geom.y + geom.height / 2;
  } else if (vertical === "bottom") {
    y = geom.y + geom.height;
  }
  if (edge === "start") {
    x += LINK_ARROW_INDENT;
  }
  return { x, y };
}

/** MS Project-style: horizontal to target column, vertical into top/bottom anchor. */
function dependencyPath(x1, y1, x2, y2) {
  if (Math.abs(y1 - y2) < 1) {
    return `M ${x1} ${y1} H ${x2}`;
  }
  return `M ${x1} ${y1} H ${x2} V ${y2}`;
}

function addDependencyArrowMarkers(defs, colors) {
  for (const [id, fill] of [
    ["dependency-arrow", colors.link],
    ["dependency-arrow-critical", colors.critical],
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
}

function appendBarShape(layer, geom, colors) {
  const { item } = geom;
  const critical = item.is_critical;

  if (geom.kind === "milestone") {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("class", `bar milestone${critical ? " critical" : ""}`);
    circle.setAttribute("cx", String(geom.cx));
    circle.setAttribute("cy", String(geom.cy));
    circle.setAttribute("r", String(geom.r));
    circle.setAttribute("fill", colors.milestone);
    if (critical) {
      circle.setAttribute("stroke", colors.critical);
      circle.setAttribute("stroke-width", "3");
    }
    layer.appendChild(circle);
    return;
  }

  if (geom.kind === "group") {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const { x, y, width, legH } = geom;
    path.setAttribute(
      "d",
      `M ${x} ${y + legH} L ${x} ${y} L ${x + width} ${y} L ${x + width} ${y + legH}`,
    );
    path.setAttribute("class", `bar group${critical ? " critical" : ""}`);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", critical ? colors.critical : colors.group);
    path.setAttribute("stroke-width", "3");
    layer.appendChild(path);
    return;
  }

  const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  rect.setAttribute("class", `bar task${critical ? " critical" : ""}`);
  rect.setAttribute("x", String(geom.x));
  rect.setAttribute("y", String(geom.y));
  rect.setAttribute("width", String(geom.width));
  rect.setAttribute("height", String(geom.height));
  rect.setAttribute("rx", "3");
  rect.setAttribute("fill", colors.task);
  if (critical) {
    rect.setAttribute("stroke", colors.critical);
    rect.setAttribute("stroke-width", "3");
  }
  layer.appendChild(rect);
}

function renderTimelineSvg(items, rowEntries, container) {
  const drawable = rowEntries.filter((entry) => entry.metrics);
  if (!drawable.length) {
    return;
  }

  const containerRect = container.getBoundingClientRect();
  const timelineWidth = timelineBox(drawable[0].row, containerRect.top).width;
  const containerHeight = containerRect.height;
  if (!timelineWidth || !containerHeight) {
    return;
  }

  const colors = chartColors();
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "timeline-svg");
  svg.setAttribute("width", String(timelineWidth));
  svg.setAttribute("height", String(containerHeight));
  svg.setAttribute("viewBox", `0 0 ${timelineWidth} ${containerHeight}`);
  svg.setAttribute("preserveAspectRatio", "none");

  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  addDependencyArrowMarkers(defs, colors);
  svg.appendChild(defs);

  const barLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  barLayer.setAttribute("class", "bars");
  const linkLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
  linkLayer.setAttribute("class", "links");

  const geometryById = new Map();
  for (const entry of drawable) {
    const box = timelineBox(entry.row, containerRect.top);
    const geom = barGeometry(entry, box, timelineWidth);
    if (!geom) {
      continue;
    }
    geometryById.set(entry.item.id, geom);
    appendBarShape(barLayer, geom, colors);
  }

  const byId = new Map(drawable.map((entry) => [entry.item.id, entry]));
  for (const item of items) {
    const predecessors = item.predecessors || [];
    const succGeom = geometryById.get(item.id);
    if (!succGeom) {
      continue;
    }

    for (const pred of predecessors) {
      const predGeom = geometryById.get(pred.task_id);
      if (!predGeom) {
        continue;
      }

      const anchors = LINK_ANCHORS[pred.link_type] || LINK_ANCHORS.FS;
      const from = anchorFromGeometry(predGeom, anchors.from.edge, anchors.from.v);
      const to = anchorFromGeometry(succGeom, anchors.to.edge, anchors.to.v);

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", dependencyPath(from.x, from.y, to.x, to.y));
      const isCritical = predGeom.item.is_critical && succGeom.item.is_critical;
      path.setAttribute(
        "marker-end",
        isCritical ? "url(#dependency-arrow-critical)" : "url(#dependency-arrow)",
      );
      if (isCritical) {
        path.classList.add("critical");
      }
      linkLayer.appendChild(path);
    }
  }

  svg.append(barLayer, linkLayer);
  container.appendChild(svg);
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
  timeline.appendChild(barArea);
  row.append(label, timeline);

  const metrics = itemMetrics(item, rangeStart, totalDays);
  return { row, metrics, item };
}

function renderGantt(data) {
  const ganttScroller = document.querySelector(".gantt");
  const scrollLeft = ganttScroller?.scrollLeft ?? 0;
  const scrollTop = ganttScroller?.scrollTop ?? 0;

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
  document.documentElement.style.setProperty("--timeline-min-width", `${totalDays * 1.15}rem`);
  const byId = new Map(items.map((item) => [item.id, item]));

  const header = document.createElement("div");
  header.className = "row header";
  const headerLabel = document.createElement("div");
  headerLabel.className = "label";
  headerLabel.textContent = "Item";
  const headerTimeline = document.createElement("div");
  headerTimeline.className = "timeline";
  headerTimeline.appendChild(buildTimelineHeader(range.start, range.end));
  header.append(headerLabel, headerTimeline);
  root.appendChild(header);

  const rowEntries = [];
  items.forEach((item) => {
    const entry = renderRow(item, byId, range.start, totalDays);
    root.appendChild(entry.row);
    rowEntries.push(entry);
  });

  renderTimelineSvg(items, rowEntries, root);
  appendLabelColumnResizer(root);

  if (ganttScroller) {
    ganttScroller.scrollLeft = scrollLeft;
    ganttScroller.scrollTop = scrollTop;
  }
  syncLabelResizerPosition();
}

function currentLabelWidthPx(root) {
  const label = root.querySelector(".row:not(.header) .label, .row.header .label");
  return label?.getBoundingClientRect().width ?? 256;
}

function syncLabelResizerPosition() {
  const gantt = document.querySelector(".gantt");
  const root = document.getElementById("gantt-root");
  const resizer = document.querySelector(".label-resizer");
  const label = root?.querySelector(".row.header .label");
  if (!gantt || !resizer || !label) {
    return;
  }
  const ganttRect = gantt.getBoundingClientRect();
  const labelRect = label.getBoundingClientRect();
  resizer.style.left = `${labelRect.right - 3}px`;
  resizer.style.top = `${ganttRect.top}px`;
  resizer.style.height = `${ganttRect.height}px`;
}

function appendLabelColumnResizer(root) {
  const gantt = document.querySelector(".gantt");
  if (!gantt) {
    return;
  }
  document.querySelector(".label-resizer")?.remove();

  const resizer = document.createElement("div");
  resizer.className = "label-resizer";
  resizer.setAttribute("role", "separator");
  resizer.setAttribute("aria-orientation", "vertical");
  resizer.setAttribute("aria-label", "Resize item column");
  resizer.title = "Drag to resize item column";

  let startX = 0;
  let startWidth = 0;

  function stopDragging() {
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", stopDragging);
    resizer.classList.remove("dragging");
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    if (chartData) {
      renderGantt(chartData);
    }
  }

  function onMouseMove(event) {
    const width = Math.min(
      LABEL_WIDTH_MAX,
      Math.max(LABEL_WIDTH_MIN, startWidth + event.clientX - startX),
    );
    document.documentElement.style.setProperty("--label-width", `${width}px`);
    syncLabelResizerPosition();
  }

  resizer.addEventListener("mousedown", (event) => {
    event.preventDefault();
    startX = event.clientX;
    startWidth = currentLabelWidthPx(root);
    resizer.classList.add("dragging");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", stopDragging);
  });

  document.body.appendChild(resizer);
  syncLabelResizerPosition();

  if (!gantt.dataset.resizerScrollBound) {
    gantt.dataset.resizerScrollBound = "true";
    gantt.addEventListener("scroll", syncLabelResizerPosition);
    window.addEventListener("resize", syncLabelResizerPosition);
  }
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
    chartData = await response.json();
    renderGantt(chartData);
    window.addEventListener("resize", () => {
      if (chartData) {
        renderGantt(chartData);
      }
    });
  } catch (err) {
    showError(err.message);
  }
}

init();
