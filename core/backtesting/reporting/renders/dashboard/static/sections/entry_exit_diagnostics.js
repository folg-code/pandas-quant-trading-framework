function renderDiagnostics(report) {
  const root = document.getElementById("diagnostics");
  if (!root) return;

  // ==================================================
  // Helper: render table
  // ==================================================

  function renderTable(rows) {
    const table = document.createElement("table");
    const columns = Object.keys(rows[0]);

    table.innerHTML = `
      <thead>
        <tr>
          ${columns.map(c => `<th>${c}</th>`).join("")}
        </tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr>
            ${columns.map(c => `<td>${window.displayValue(r[c])}</td>`).join("")}
          </tr>
        `).join("")}
      </tbody>
    `;

    return table;
  }

  // ==================================================
  // Helper: render bar chart (DOM-safe)
  // ==================================================

  function renderBarChart(container, title, categories, values) {
    const titleEl = document.createElement("h4");
    titleEl.textContent = title;

    const chartDiv = document.createElement("div");

    container.appendChild(titleEl);
    container.appendChild(chartDiv);

    // ✅ values may contain objects -> force numeric raw
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
        height: 260,
        margin: { t: 20, l: 50, r: 20 },
        paper_bgcolor: "#161b22",
        plot_bgcolor: "#161b22",
        font: { color: "#e6edf3" },
        yaxis: { title: "Value" },
      },
      { displayModeBar: false }
    );
  }

  // ==================================================
  // Helper: collapsible section (OPEN BY DEFAULT)
  // ==================================================

  function renderSection(title, payload) {
    if (!payload || !payload.rows || payload.rows.length === 0) return;

    const wrapper = document.createElement("div");
    wrapper.className = "diag-section";

    const header = document.createElement("div");
    header.className = "diag-header";
    header.innerHTML = `
      <div>${title}</div>
      <span>click to collapse</span>
    `;

    const body = document.createElement("div");
    body.className = "diag-body";
    body.style.display = "block";

    const grid = document.createElement("div");
    grid.className = "diag-grid";

    const tableWrap = document.createElement("div");
    tableWrap.className = "diag-table";

    const chartWrap = document.createElement("div");
    chartWrap.className = "diag-chart";

    // ---- TABLE ----
    tableWrap.appendChild(renderTable(payload.rows));

    // ---- CHARTS ----
    if (title === "Performance by Entry Tag") {
      const tags = payload.rows.map(r => window.displayValue(r["Entry tag"]));
      const expectancy = payload.rows.map(r =>
        window.rawValue(r["EXP"] ?? r["Expectancy (USD)"]) ?? 0
      );

      renderBarChart(chartWrap, "Expectancy by Entry Tag", tags, expectancy);
    }

    if (title === "Exit Logic Diagnostics") {
      const tags = payload.rows.map(r => window.displayValue(r["Exit tag"]));
      const pnl = payload.rows.map(r => window.rawValue(r["PnL"]) ?? 0);

      renderBarChart(chartWrap, "Total PnL by Exit Tag", tags, pnl);
    }

    grid.appendChild(tableWrap);
    grid.appendChild(chartWrap);

    body.appendChild(grid);

    header.onclick = () => {
      body.style.display = body.style.display === "none" ? "block" : "none";
    };

    wrapper.appendChild(header);
    wrapper.appendChild(body);
    root.appendChild(wrapper);
  }

  // ==================================================
  // Sections
  // ==================================================

  Object.entries(report).forEach(([key, payload]) => {
    if (key === "Performance by Entry Tag" || key === "Exit Logic Diagnostics") {
      renderSection(key, payload);
    }
  });
}