function renderCapitalExposure(report) {
  const section = report["Capital & Exposure Analysis"];
  if (!section) return;

  const summaryRoot = document.getElementById("capital-summary");
  const tableRoot = document.getElementById("overtrading-table");
  const chartPnL = document.getElementById("overtrading-chart-pnl");
  const chartDD = document.getElementById("overtrading-chart-dd");

  if (!summaryRoot || !tableRoot || !chartPnL || !chartDD) return;

  summaryRoot.innerHTML = "";
  tableRoot.innerHTML = "";
  chartPnL.innerHTML = "";
  chartDD.innerHTML = "";

  // ==================================================
  // Helpers
  // ==================================================

  function renderTable(rows) {
    const table = document.createElement("table");
    const cols = Object.keys(rows[0]);

    table.innerHTML = `
      <thead>
        <tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr>${cols.map(c => `<td>${r[c]}</td>`).join("")}</tr>
        `).join("")}
      </tbody>
    `;
    return table;
  }

  function renderBarChart(container, title, x, y, yLabel, colorScale = "RdBu") {
    const h = document.createElement("h4");
    h.textContent = title;

    const div = document.createElement("div");
    container.appendChild(h);
    container.appendChild(div);

    const maxAbs = Math.max(...y.map(v => Math.abs(v))) || 1;

    Plotly.newPlot(
      div,
      [{
        type: "bar",
        x: x,
        y: y,
        marker: {
          color: y,
          colorscale: colorScale,
          cmin: -maxAbs,
          cmax: maxAbs,
        },
      }],
      {
        margin: { t: 20, l: 50, r: 20, b: 60 },
        paper_bgcolor: "#161b22",
        plot_bgcolor: "#161b22",
        font: { color: "#e6edf3" },
        yaxis: { title: yLabel },
        xaxis: {
          type: "category",
          categoryorder: "array",
          categoryarray: x,
          automargin: true,
          tickangle: -30,
        },
      },
      {
        displayModeBar: false,
        responsive: true,
      }
    );

    setTimeout(() => Plotly.Plots.resize(div), 0);
  }

  // ==================================================
  // ROW 1
  // ==================================================

  if (section.Summary) {
    summaryRoot.appendChild(renderTable([section.Summary]));
  }

  const over = section["Overtrading diagnostics"];
  if (!over || !over.rows || !over.rows.length) return;

  tableRoot.appendChild(renderTable(over.rows));

  // ==================================================
  // ROW 2 – CHARTS
  // ==================================================

  const buckets = over.rows.map(r => r["Trades/day"]);
  const avgPnL = over.rows.map(r => r["Avg PnL"]);
  const worstDD = over.rows.map(r => -Math.abs(r["Worst DD"]));

  renderBarChart(
    chartPnL,
    "Average PnL by trades/day bucket",
    buckets,
    avgPnL,
    "Avg PnL"
  );

  renderBarChart(
    chartDD,
    "Worst drawdown by trades/day bucket",
    buckets,
    worstDD,
    "Worst DD",
    "Reds"
  );
}