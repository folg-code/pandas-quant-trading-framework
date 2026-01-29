function rawValue(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "object" && v.raw !== undefined) return v.raw;
  return v;
}
window.rawValue = rawValue;

function renderConditionalExpectancy(report) {
  const section = report["Conditional Expectancy Analysis"];
  if (!section) return;

  function renderBar(containerId, title, categories, values, height = 220) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <h3>${title}</h3>
      <div></div>
    `;

    const chartDiv = container.querySelector("div");

    const safe = values.map(v => Number(v) || 0);
    const maxAbs = Math.max(1e-9, ...safe.map(v => Math.abs(v)));

    Plotly.newPlot(
      chartDiv,
      [
        {
          type: "bar",
          x: categories,
          y: safe,
          marker: {
            color: safe,
            colorscale: "RdBu",
            cmin: -maxAbs,
            cmax: maxAbs,
          },
        },
      ],
      {
        height,
        margin: { t: 20, l: 50, r: 20 },
        paper_bgcolor: "#161b22",
        plot_bgcolor: "#161b22",
        font: { color: "#e6edf3" },
        yaxis: { title: "Expectancy (USD)" },
      },
      { displayModeBar: false }
    );
  }

  if (section["By hour of day"]?.rows) {
    const HOURS = Array.from({ length: 24 }, (_, i) => String(i));
    const map = {};

    section["By hour of day"].rows.forEach(r => {
      map[r["hour"]] = window.rawValue(r["Expectancy (USD)"]);
    });

    const values = HOURS.map(h => map[h] ?? 0);
    renderBar("cond-hour", "By hour of day", HOURS, values, 260);
  }

  if (section["By day of week"]?.rows) {
    const ORDER = [
      "Monday", "Tuesday", "Wednesday",
      "Thursday", "Friday", "Saturday", "Sunday",
    ];

    const map = {};
    section["By day of week"].rows.forEach(r => {
      map[r["weekday"]] = window.rawValue(r["Expectancy (USD)"]);
    });

    const values = ORDER.map(d => map[d] ?? 0);
    renderBar("cond-weekday", "By day of week", ORDER, values, 260);
  }

  const contextRoot = document.getElementById("cond-context-grid");
  if (!contextRoot) return;

  Object.entries(section).forEach(([key, block]) => {
    if (!key.startsWith("By context:")) return;
    if (!block.rows || block.rows.length === 0) return;

    const container = document.createElement("div");
    contextRoot.appendChild(container);

    const categories = block.rows.map(r => {
      const k = Object.keys(r)[0];
      return r[k];
    });

    const values = block.rows.map(r => window.rawValue(r["Expectancy (USD)"]) ?? 0);

    const id = "ctx-" + Math.random().toString(36).slice(2);
    container.id = id;

    renderBar(id, key, categories, values, 220);
  });
}