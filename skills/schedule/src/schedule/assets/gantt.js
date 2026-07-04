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
const collapsedIds = new Set();
let contextLocked = false;
let contextCollapsed = false;

/** IDs of groups that have at least one child. */
function collapsibleIds(items) {
  const withChildren = new Set();
  for (const item of items) {
    if (item.parent_id != null) {
      withChildren.add(item.parent_id);
    }
  }
  return withChildren;
}

/** True if any ancestor of item is collapsed. */
function isHidden(item, byId) {
  let parentId = item.parent_id;
  while (parentId != null) {
    if (collapsedIds.has(parentId)) {
      return true;
    }
    const parent = byId.get(parentId);
    if (!parent) {
      break;
    }
    parentId = parent.parent_id;
  }
  return false;
}

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

function formatDate(iso) {
  const [year, month, day] = iso.split("-");
  return `${month}/${day}/${year}`;
}

function dateRangeLabel(start, finish) {
  return `${formatDate(start)}-${formatDate(finish)}`;
}

/** Multi-line hover-tooltip text for a schedule item; null if unplaced. */
function itemTooltip(item) {
  if (!item.start || !item.finish) {
    return null;
  }
  if (item.kind === "milestone") {
    return `${item.name}\n${formatDate(item.start)}`;
  }
  return [
    item.name,
    `${item.working_days} working days`,
    `${item.calendar_days} calendar days`,
  ].join("\n");
}

function bandSegments(...bands) {
  return bands.flat().flatMap((entry) => entry.segments || []);
}

function dateRange(items, ...bands) {
  const segments = bandSegments(...bands);
  const starts = [
    ...items.filter((item) => item.start).map((item) => parseDate(item.start)),
    ...segments.map((segment) => parseDate(segment.start)),
  ];
  const finishes = [
    ...items.filter((item) => item.finish).map((item) => parseDate(item.finish)),
    ...segments.map((segment) => parseDate(segment.finish)),
  ];
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

/**
 * Master grid: the rendered header day columns are the single source of truth
 * for horizontal position. Return the left edge (px, relative to the timeline
 * origin) of every day plus the right edge of the final day, so any bar can be
 * placed by day index and land exactly on its column — for any column width,
 * including fractional widths from a future horizontal zoom.
 */
function dayColumnEdges(headerTimelineEl) {
  const cells = headerTimelineEl.querySelectorAll(
    ".timeline-header .day-cell",
  );
  if (!cells.length) {
    return [];
  }
  const originLeft = headerTimelineEl.getBoundingClientRect().left;
  const edges = [];
  for (const cell of cells) {
    edges.push(cell.getBoundingClientRect().left - originLeft);
  }
  const last = cells[cells.length - 1].getBoundingClientRect();
  edges.push(last.right - originLeft);
  return edges;
}

function remPx() {
  return parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
}

function cssLengthPx(name) {
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
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

function timelineGutterPx() {
  return cssLengthPx("--timeline-gutter");
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
    today: token("today"),
  };
}

function todayColumnOffset(rangeStart, rangeEnd) {
  // Today is a property of *when the chart is viewed*, computed here rather than
  // baked into the data at compute time. Returns null when today falls outside
  // the schedule range — the range is never stretched to include it.
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (today < rangeStart || today > rangeEnd) {
    return null;
  }
  return Math.round((today - rangeStart) / (1000 * 60 * 60 * 24));
}

function spanMetrics(startValue, finishValue, rangeStart, totalDays) {
  if (!startValue || !finishValue || totalDays <= 0) {
    return null;
  }
  const start = parseDate(startValue);
  const finish = parseDate(finishValue);
  const offsetDays = Math.round((start - rangeStart) / (1000 * 60 * 60 * 24));
  const spanDays = Math.max(
    Math.round((finish - start) / (1000 * 60 * 60 * 24)) + 1,
    1,
  );
  return { offsetDays, spanDays };
}

function itemMetrics(item, rangeStart, totalDays) {
  const metrics = spanMetrics(item.start, item.finish, rangeStart, totalDays);
  if (!metrics) {
    return null;
  }
  return { ...metrics, kind: item.kind };
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

function barGeometry(entry, box, edges) {
  const { metrics, item } = entry;
  if (!metrics) {
    return null;
  }
  const rem = remPx();
  const lastEdge = edges.length - 1;
  const startIdx = Math.min(metrics.offsetDays, lastEdge);
  const endIdx = Math.min(metrics.offsetDays + metrics.spanDays, lastEdge);
  const left = edges[startIdx];
  const width = Math.max(edges[endIdx] - left, 2);

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

function appendFinishFlag(layer, x, cy) {
  // Small checkered flag marking the project-finish milestone. Self-contained
  // SVG (no external asset) so it survives the viewer CSP and prints faithfully.
  const cell = 3;
  const cols = 3;
  const rows = 2;
  const flagW = cols * cell;
  const flagH = rows * cell;
  const poleTop = cy - 9;
  const poleBottom = cy + 8;

  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.setAttribute("class", "finish-flag");

  const pole = document.createElementNS("http://www.w3.org/2000/svg", "line");
  pole.setAttribute("x1", String(x));
  pole.setAttribute("x2", String(x));
  pole.setAttribute("y1", String(poleTop));
  pole.setAttribute("y2", String(poleBottom));
  pole.setAttribute("class", "finish-flag-pole");
  g.appendChild(pole);

  const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  bg.setAttribute("x", String(x));
  bg.setAttribute("y", String(poleTop));
  bg.setAttribute("width", String(flagW));
  bg.setAttribute("height", String(flagH));
  bg.setAttribute("class", "finish-flag-bg");
  g.appendChild(bg);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if ((r + c) % 2 !== 0) {
        continue;
      }
      const sq = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      sq.setAttribute("x", String(x + c * cell));
      sq.setAttribute("y", String(poleTop + r * cell));
      sq.setAttribute("width", String(cell));
      sq.setAttribute("height", String(cell));
      sq.setAttribute("class", "finish-flag-square");
      g.appendChild(sq);
    }
  }

  layer.appendChild(g);
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
    if (item.type === "project_finish") {
      appendFinishFlag(layer, geom.cx + geom.r + 3, geom.cy);
    }
    layer.appendChild(circle);
    return circle;
  }

  if (geom.kind === "group") {
    const { x, y, width, legH } = geom;
    // Transparent hit target: the bracket outline is too thin to hover
    // reliably, so a full-span rect behind it carries the tooltip.
    const hit = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    hit.setAttribute("class", "bar group-hit");
    hit.setAttribute("x", String(x));
    hit.setAttribute("y", String(y));
    hit.setAttribute("width", String(width));
    hit.setAttribute("height", String(legH));
    hit.setAttribute("fill", "transparent");
    layer.appendChild(hit);

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute(
      "d",
      `M ${x} ${y + legH} L ${x} ${y} L ${x + width} ${y} L ${x + width} ${y + legH}`,
    );
    path.setAttribute("class", `group${critical ? " critical" : ""}`);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", critical ? colors.critical : colors.group);
    path.setAttribute("stroke-width", "3");
    layer.appendChild(path);
    return hit;
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
  return rect;
}

function renderTimelineSvg(items, rowEntries, container, edges, range) {
  const drawable = rowEntries.filter((entry) => entry.metrics);
  if (!drawable.length) {
    return;
  }

  const containerRect = container.getBoundingClientRect();
  const timelineWidth = edges.length ? edges[edges.length - 1] : 0;
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
    const geom = barGeometry(entry, box, edges);
    if (!geom) {
      continue;
    }
    geometryById.set(entry.item.id, geom);
    const shape = appendBarShape(barLayer, geom, colors);
    const tip = itemTooltip(entry.item);
    if (tip) {
      shape.dataset.tip = tip;
    }
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

function renderTodayOverlay(container, range, edges, colors) {
  // The today line lives in its own overlay SVG (not the timeline SVG) so it
  // can sit above every row — including a locked context band — rather than
  // being painted over. It spans from the gutter bottom down through the plot.
  const offsetDays = todayColumnOffset(range.start, range.end);
  if (offsetDays == null || !edges.length) {
    return;
  }
  const containerRect = container.getBoundingClientRect();
  const timelineWidth = edges[edges.length - 1];
  const containerHeight = containerRect.height;
  if (!timelineWidth || !containerHeight) {
    return;
  }

  const gutterRow = container.querySelector(".row.gutter");
  const gutterBottom = gutterRow
    ? gutterRow.getBoundingClientRect().bottom - containerRect.top
    : 0;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "today-overlay");
  svg.setAttribute("width", String(timelineWidth));
  svg.setAttribute("height", String(containerHeight));
  svg.setAttribute("viewBox", `0 0 ${timelineWidth} ${containerHeight}`);
  svg.setAttribute("preserveAspectRatio", "none");

  const x = edges[Math.min(offsetDays, edges.length - 1)];
  const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
  line.setAttribute("class", "today-line");
  line.setAttribute("x1", String(x));
  line.setAttribute("x2", String(x));
  line.setAttribute("y1", String(gutterBottom));
  line.setAttribute("y2", String(containerHeight));
  line.setAttribute("stroke", colors.today);
  svg.appendChild(line);
  container.appendChild(svg);
}

function renderTodayTag(gutterTimeline, range, edges) {
  const offsetDays = todayColumnOffset(range.start, range.end);
  if (offsetDays == null || !edges.length) {
    return;
  }
  const x = edges[Math.min(offsetDays, edges.length - 1)];

  // Centered over the line's x: the line does not enter the gutter, so the tag
  // is not offset to one side.
  const tag = document.createElement("div");
  tag.className = "today-tag";
  tag.textContent = "Today";
  tag.style.left = `${x}px`;
  gutterTimeline.appendChild(tag);
}

function renderRow(item, byId, rangeStart, totalDays, collapsible) {
  const depth = itemDepth(item, byId);
  const row = document.createElement("div");
  row.className = `row ${item.kind}`;

  const label = document.createElement("div");
  label.className = `label ${item.kind}`;
  label.title = `${item.kind}: ${item.name}`;
  const indentRem = 0.75 + depth * 1.25;
  label.style.setProperty("--label-indent", `${indentRem}rem`);

  const canCollapse = collapsible.has(item.id);
  if (canCollapse) {
    const collapsed = collapsedIds.has(item.id);
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "row-toggle";
    toggle.textContent = collapsed ? "▶" : "▼";
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.setAttribute(
      "aria-label",
      `${collapsed ? "Expand" : "Collapse"} ${item.name}`,
    );
    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      if (collapsedIds.has(item.id)) {
        collapsedIds.delete(item.id);
      } else {
        collapsedIds.add(item.id);
      }
      if (chartData) {
        renderGantt(chartData);
      }
    });
    label.appendChild(toggle);
  }

  const text = document.createElement("div");
  text.className = "label-text";
  const name = document.createElement("span");
  name.className = "item-name";
  name.textContent = item.name;
  const dates = document.createElement("div");
  dates.className = "dates";
  dates.textContent = dateLabel(item);

  text.append(name, dates);
  label.appendChild(text);

  const timeline = document.createElement("div");
  timeline.className = "timeline";
  const barArea = document.createElement("div");
  barArea.className = "bar-area";
  timeline.appendChild(barArea);
  row.append(label, timeline);

  const metrics = itemMetrics(item, rangeStart, totalDays);
  return { row, metrics, item };
}

function renderContextSegment(segment, entryName, type, rangeStart, totalDays, edges) {
  const metrics = spanMetrics(segment.start, segment.finish, rangeStart, totalDays);
  if (!metrics) {
    return null;
  }
  const gutter = timelineGutterPx();
  const lastEdge = edges.length - 1;
  const startIdx = Math.min(metrics.offsetDays, lastEdge);
  const endIdx = Math.min(metrics.offsetDays + metrics.spanDays, lastEdge);
  const box = document.createElement("div");
  box.className = `context-segment ${type}`;
  box.style.left = `${edges[startIdx] - gutter}px`;
  box.style.width = `${edges[endIdx] - edges[startIdx]}px`;
  box.textContent = segment.label;
  box.dataset.tip = [
    entryName,
    segment.label,
    dateRangeLabel(segment.start, segment.finish),
  ].join("\n");
  return box;
}

function renderContextRow(entry, type, rangeStart, totalDays, edges) {
  const row = document.createElement("div");
  row.className = `row context ${type}`;

  const label = document.createElement("div");
  label.className = `label context ${type}`;
  label.title = `${type}: ${entry.name}`;
  label.style.setProperty("--label-indent", "0.75rem");
  const name = document.createElement("span");
  name.className = "item-name";
  name.textContent = entry.name;
  label.appendChild(name);

  const timeline = document.createElement("div");
  timeline.className = "timeline";
  const track = document.createElement("div");
  track.className = "context-track";
  for (const segment of entry.segments || []) {
    const box = renderContextSegment(segment, entry.name, type, rangeStart, totalDays, edges);
    if (box) {
      track.appendChild(box);
    }
  }
  timeline.appendChild(track);
  row.append(label, timeline);
  return row;
}

function contextLockToggle() {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "context-lock";
  button.textContent = contextLocked ? "🔒" : "🔓";
  button.title = contextLocked
    ? "People and events pinned below the header — click to unlock"
    : "Lock people and events below the header while scrolling";
  button.setAttribute("aria-pressed", String(contextLocked));
  button.setAttribute("aria-label", "Lock people and events bands");
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    contextLocked = !contextLocked;
    if (chartData) {
      renderGantt(chartData);
    }
  });
  return button;
}

function contextCollapseToggle() {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "row-toggle";
  button.textContent = contextCollapsed ? "▶" : "▼";
  button.setAttribute("aria-expanded", String(!contextCollapsed));
  button.setAttribute(
    "aria-label",
    contextCollapsed ? "Expand people and events" : "Collapse people and events",
  );
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    contextCollapsed = !contextCollapsed;
    if (chartData) {
      renderGantt(chartData);
    }
  });
  return button;
}

/** Populate the gutter's label cell with the Context section controls. */
function renderContextControls(gutterLabel) {
  gutterLabel.classList.add("context-controls");
  gutterLabel.appendChild(contextCollapseToggle());
  const name = document.createElement("span");
  name.className = "context-title";
  name.textContent = "Context";
  gutterLabel.appendChild(name);
  if (!contextCollapsed) {
    gutterLabel.appendChild(contextLockToggle());
  }
}

/**
 * Render the context section. Its collapse/lock controls live in the gutter's
 * label cell (always visible, since the gutter is pinned under the header); when
 * expanded, people rows and events rows follow below.
 */
function renderContextBand(people, events, gutterLabel, root, rangeStart, totalDays, edges) {
  const hasBands = (people && people.length) || (events && events.length);
  if (!hasBands) {
    return;
  }

  renderContextControls(gutterLabel);
  if (contextCollapsed) {
    return;
  }

  const bands = [
    ["people", people || []],
    ["events", events || []],
  ];
  const rows = [];
  for (const [type, entries] of bands) {
    for (const entry of entries) {
      const row = renderContextRow(entry, type, rangeStart, totalDays, edges);
      if (contextLocked) {
        row.classList.add("context-locked");
      }
      root.appendChild(row);
      rows.push(row);
    }
  }
  rows[rows.length - 1].classList.add("context-last");
  if (contextLocked) {
    stickContextRows(rows);
  }
}

/** Pin locked context rows in a stack below the sticky header and gutter lane. */
function stickContextRows(rows) {
  const header = document.querySelector(".row.header");
  const gutter = document.querySelector(".row.gutter");
  let offset = header ? header.getBoundingClientRect().height : 0;
  offset += gutter ? gutter.getBoundingClientRect().height : 0;
  for (const row of rows) {
    row.style.top = `${offset}px`;
    offset += row.getBoundingClientRect().height;
  }
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
  const people = data.people || [];
  const events = data.events || [];
  const range = dateRange(items, people, events);
  if (!range) {
    root.textContent = "No scheduled items to display.";
    return;
  }

  const totalDays =
    Math.round((range.end - range.start) / (1000 * 60 * 60 * 24)) + 1;
  document.documentElement.style.setProperty("--day-count", String(totalDays));
  const byId = new Map(items.map((item) => [item.id, item]));
  const collapsible = collapsibleIds(items);
  const visibleItems = items.filter((item) => !isHidden(item, byId));

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

  // Thin annotation lane under the date header — a reserved strip where
  // timeline labels (the "Today" tag now, others later) can sit without
  // overlapping the first content row.
  const gutter = document.createElement("div");
  gutter.className = "row gutter";
  const gutterLabel = document.createElement("div");
  gutterLabel.className = "label";
  const gutterTimeline = document.createElement("div");
  gutterTimeline.className = "timeline";
  gutter.append(gutterLabel, gutterTimeline);
  root.appendChild(gutter);

  const headerHeight = header.getBoundingClientRect().height;
  gutter.style.top = `${headerHeight}px`;

  const edges = dayColumnEdges(headerTimeline);

  renderTodayTag(gutterTimeline, range, edges);

  renderContextBand(people, events, gutterLabel, root, range.start, totalDays, edges);

  const rowEntries = [];
  visibleItems.forEach((item) => {
    const entry = renderRow(item, byId, range.start, totalDays, collapsible);
    root.appendChild(entry.row);
    rowEntries.push(entry);
  });

  updateCollapseAllButton(collapsible);
  renderTimelineSvg(visibleItems, rowEntries, root, edges, range);
  renderTodayOverlay(root, range, edges, chartColors());
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

/** Reflect state on the Collapse/Expand-all button, or hide it if nothing collapses. */
function updateCollapseAllButton(collapsible) {
  const button = document.getElementById("collapse-all");
  if (!button) {
    return;
  }
  button.hidden = false;
  if (!collapsible.size) {
    // Nothing to collapse (no groups) — keep the button visible but inert.
    button.disabled = true;
    button.textContent = "Collapse all";
    button.dataset.action = "collapse";
    return;
  }
  button.disabled = false;
  const allCollapsed = [...collapsible].every((id) => collapsedIds.has(id));
  button.textContent = allCollapsed ? "Expand all" : "Collapse all";
  button.dataset.action = allCollapsed ? "expand" : "collapse";
}

function bindCollapseAllButton() {
  const button = document.getElementById("collapse-all");
  if (!button) {
    return;
  }
  button.addEventListener("click", () => {
    if (!chartData) {
      return;
    }
    const collapsible = collapsibleIds(chartData.items || []);
    if (button.dataset.action === "expand") {
      collapsedIds.clear();
    } else {
      collapsible.forEach((id) => collapsedIds.add(id));
    }
    renderGantt(chartData);
  });
}

function showError(message) {
  const error = document.getElementById("error");
  error.hidden = false;
  error.textContent = message;
}

/**
 * One floating tooltip, shown for any element carrying a `data-tip` attribute
 * (multi-line via newlines). Bound once on the document so it survives the
 * full re-render on resize/collapse; positioned near the cursor and kept on
 * screen.
 */
function setupTooltip() {
  const tip = document.createElement("div");
  tip.className = "gantt-tooltip";
  tip.hidden = true;
  document.body.appendChild(tip);

  const position = (event) => {
    const pad = 12;
    const rect = tip.getBoundingClientRect();
    let x = event.clientX + pad;
    let y = event.clientY + pad;
    if (x + rect.width > window.innerWidth) {
      x = event.clientX - pad - rect.width;
    }
    if (y + rect.height > window.innerHeight) {
      y = event.clientY - pad - rect.height;
    }
    tip.style.left = `${Math.max(x, 0)}px`;
    tip.style.top = `${Math.max(y, 0)}px`;
  };

  document.addEventListener("mouseover", (event) => {
    const target = event.target.closest("[data-tip]");
    if (!target) {
      return;
    }
    tip.textContent = target.dataset.tip;
    tip.hidden = false;
    position(event);
  });

  document.addEventListener("mousemove", (event) => {
    if (!tip.hidden && event.target.closest("[data-tip]")) {
      position(event);
    }
  });

  document.addEventListener("mouseout", (event) => {
    if (event.target.closest("[data-tip]")) {
      tip.hidden = true;
    }
  });
}

/**
 * A subtle full-height vertical line that tracks the cursor across the plot
 * area (like a stock chart), so the user can line a bar up with the date
 * header. Fixed-position and driven by clientX, so it needs no scroll math;
 * hidden over the sticky label column and whenever the cursor leaves the plot.
 */
function setupCrosshair() {
  const gantt = document.querySelector(".gantt");
  if (!gantt) {
    return;
  }
  const line = document.createElement("div");
  line.className = "gantt-crosshair";
  line.hidden = true;
  document.body.appendChild(line);

  const update = (event) => {
    const rect = gantt.getBoundingClientRect();
    const labelWidth = cssLengthPx("--label-width");
    const inPlot =
      event.clientX >= rect.left + labelWidth &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom;
    if (!inPlot) {
      line.hidden = true;
      return;
    }
    line.style.left = `${event.clientX}px`;
    line.style.top = `${rect.top}px`;
    line.style.height = `${rect.height}px`;
    line.hidden = false;
  };

  gantt.addEventListener("mousemove", update);
  gantt.addEventListener("mouseleave", () => {
    line.hidden = true;
  });
}

async function init() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) {
      throw new Error(`Could not load ${DATA_URL} (${response.status})`);
    }
    chartData = await response.json();
    setupTooltip();
    setupCrosshair();
    bindCollapseAllButton();
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
