function renderDrawdownStructure(report) {
  const root = document.getElementById("drawdown-structure");
  if (!root) return;

  const payload = report["Drawdown Structure & Failure Modes"];
  const equityData = report["__equity__"];
  if (!payload || !payload["Failure modes"] || !equityData) return;

  // ==================================================
  // Prepare data
  // ==================================================

  const rows = payload["Failure modes"].rows;

  const topDD = [...rows]
    .sort((a, b) => (window.rawValue(b["Depth"]) ?? 0) - (window.rawValue(a["Depth"]) ?? 0))
    .slice(0, 7);

  // ==================================================
  // Flat table
  // ==================================================

  function renderTable(rows) {
    const table = document.createElement("table");
    const cols = Object.keys(rows[0]);

    table.innerHTML = `
      <thead>
        <tr>
          ${cols.map(c => `<th>${c}</th>`).join("")}
        </tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr>
            ${cols.map(c => `<td>${window.displayValue(r[c])}</td>`).join("")}
          </tr>
        `).join("")}
      </tbody>
    `;

    return table;
  }

  // ==================================================
  // Equity + DD markers chart
  // ==================================================

  function renderEquityChart(container, ddRows) {
    const title = document.createElement("h4");
    title.textContent = "Equity curve with drawdown events";

    const chartDiv = document.createElement("div");
    container.appendChild(title);
    container.appendChild(chartDiv);

    const time = equityData.time;
    const equity = equityData.equity;
    const initial = equity[0];

    const ddX = [];
    const ddY = [];
    const ddColor = [];

    ddRows.forEach(dd => {
      const start = window.displayValue(dd["Start"]);
      const idx = time.findIndex(t => t.startsWith(start));
      if (idx === -1) return;

      const eq = equity[idx];
      ddX.push(time[idx]);
      ddY.push(eq);
      ddColor.push(eq >= initial ? "#3fb950" : "#f85149");
    });

    Plotly.newPlot(
      chartDiv,
      [
        {
          type: "scatter",
          x: time,
          y: equity,
          mode: "lines",
          name: "Equity",
          line: { color: "#58a6ff", width: 2 },
        },
        {
          type: "scatter",
          x: ddX,
          y: ddY,
          mode: "markers",
          name: "Drawdown start",
          marker: {
            size: 10,
            color: ddColor,
            symbol: "x",
          },
        },
      ],
      {
        height: 300,
        margin: { t: 20, l: 60, r: 20 },
        paper_bgcolor: "#161b22",
        plot_bgcolor: "#161b22",
        font: { color: "#e6edf3" },
        yaxis: { title: "Equity" },
        xaxis: { title: "Time" },
        legend: { orientation: "h", y: -0.25 },
      },
      { displayModeBar: false }
    );
  }

  // ==================================================
  // Build section (OPEN)
  // ==================================================

  const wrapper = document.createElement("div");
  wrapper.className = "diag-section";

  const body = document.createElement("div");
  body.className = "diag-body";
  body.style.display = "block";

  const grid = document.createElement("div");
  grid.className = "diag-grid";

  const tableWrap = document.createElement("div");
  tableWrap.className = "diag-table";
  tableWrap.appendChild(renderTable(topDD));

  const chartWrap = document.createElement("div");
  chartWrap.className = "diag-chart";
  renderEquityChart(chartWrap, topDD);

  grid.appendChild(tableWrap);
  grid.appendChild(chartWrap);

  body.appendChild(grid);
  wrapper.appendChild(body);
  root.appendChild(wrapper);
}