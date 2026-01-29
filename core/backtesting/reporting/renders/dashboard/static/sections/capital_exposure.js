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

  function renderTableLikeDrawdown(rows) {
    const wrapper = document.createElement("div");
    wrapper.className = "diag-section";

    const body = document.createElement("div");
    body.className = "diag-body";
    body.style.display = "block";

    const tableWrap = document.createElement("div");
    tableWrap.className = "diag-table";

    if (!rows || !rows.length) {
      tableWrap.textContent = "No data";
      body.appendChild(tableWrap);
      wrapper.appendChild(body);
      return wrapper;
    }

    const table = document.createElement("table");
    const cols = Object.keys(rows[0]);

    table.innerHTML = `
      <thead>
        <tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr>${cols.map(c => `<td>${window.displayValue(r[c])}</td>`).join("")}</tr>
        `).join("")}
      </tbody>
    `;

    tableWrap.appendChild(table);
    body.appendChild(tableWrap);
    wrapper.appendChild(body);
    return wrapper;
  }

  function renderBarChart(container, title, x, y, yLabel, colorScale = "RdBu") {
    container.innerHTML = "";

    const h = document.createElement("h4");
    h.textContent = title;

    const div = document.createElement("div");
    container.appendChild(h);
    container.appendChild(div);

    const safeX = x.map(v => window.displayValue(v));
    const safeY = y.map(v => Number(v) || 0);

    const maxAbs = Math.max(1e-9, ...safeY.map(v => Math.abs(v)));

    Plotly.newPlot(
      div,
      [{
        type: "bar",
        x: safeX,
        y: safeY,
        marker: {
          color: safeY,
          colorscale: colorScale,
          cmin: -maxAbs,
          cmax: maxAbs,
        },
      }],
      {
        height: 260,
        margin: { t: 20, l: 50, r: 20, b: 60 },
        paper_bgcolor: "#161b22",
        plot_bgcolor: "#161b22",
        font: { color: "#e6edf3" },
        yaxis: { title: yLabel },
        xaxis: {
          type: "category",
          categoryorder: "array",
          categoryarray: safeX,
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
    summaryRoot.appendChild(renderTableLikeDrawdown([section.Summary]));
  }

  const over = section["Overtrading diagnostics"];
  if (!over || !over.rows || !over.rows.length) return;

  tableRoot.appendChild(renderTableLikeDrawdown(over.rows));

  // ==================================================
  // ROW 2 – CHARTS
  // ==================================================

  const buckets = over.rows.map(r => r["Trades/day"]);

  const avgPnL = over.rows.map(r => window.rawValue(r["Avg PnL"]));
  const worstDD = over.rows.map(r => -Math.abs(Number(window.rawValue(r["Worst DD"])) || 0));

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