function renderConditionalExpectancy(report) {
  const section = report["Conditional Expectancy Analysis"];
  if (!section) return;

  // ==========================
  // Helper
  // ==========================

  function renderBar(containerId, title, categories, values, height = 220) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <h3>${title}</h3>
      <div></div>
    `;

    const chartDiv = container.querySelector("div");
    const maxAbs = Math.max(...values.map(v => Math.abs(v)));

    Plotly.newPlot(
      chartDiv,
      [
        {
          type: "bar",
          x: categories,
          y: values,
          marker: {
            color: values,
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

  // ==========================
  // By hour of day (2/3)
  // ==========================

  if (section["By hour of day"]?.rows) {
    const HOURS = Array.from({ length: 24 }, (_, i) => String(i));
    const map = {};

    section["By hour of day"].rows.forEach(r => {
      map[r["hour"]] = r["Expectancy (USD)"];
    });

    const values = HOURS.map(h => map[h] ?? 0);
    renderBar("cond-hour", "By hour of day", HOURS, values, 260);
  }

  // ==========================
  // By day of week (1/3)
  // ==========================

  if (section["By day of week"]?.rows) {
    const ORDER = [
      "Monday", "Tuesday", "Wednesday",
      "Thursday", "Friday", "Saturday", "Sunday",
    ];

    const map = {};
    section["By day of week"].rows.forEach(r => {
      map[r["weekday"]] = r["Expectancy (USD)"];
    });

    const values = ORDER.map(d => map[d] ?? 0);
    renderBar("cond-weekday", "By day of week", ORDER, values, 260);
  }

  // ==========================
  // By context (2 per row)
  // ==========================

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

    const values = block.rows.map(r => r["Expectancy (USD)"]);

    const id = "ctx-" + Math.random().toString(36).slice(2);
    container.id = id;

    renderBar(id, key, categories, values, 220);
  });
}