function renderDiagnostics(report) {
  const root = document.getElementById("diagnostics");
  if (!root) return;

  root.innerHTML = "";

  // ------------------------------
  // Helpers
  // ------------------------------

  function renderTable(rows) {
    const table = document.createElement("table");
    const cols = Object.keys(rows[0] || {});

    table.innerHTML = `
      <thead><tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr></thead>
      <tbody>
        ${rows.map(r => `
          <tr>${cols.map(c => `<td>${window.displayValue(r[c])}</td>`).join("")}</tr>
        `).join("")}
      </tbody>
    `;
    return table;
  }

  function makePanel(title) {
    const panel = document.createElement("div");
    panel.className = "diag-section";

    const header = document.createElement("div");
    header.className = "diag-header";
    header.innerHTML = `<div>${title}</div><span>click to collapse</span>`;

    const body = document.createElement("div");
    body.className = "diag-body";
    body.style.display = "block";

    header.onclick = () => {
      body.style.display = body.style.display === "none" ? "block" : "none";
    };

    panel.appendChild(header);
    panel.appendChild(body);
    root.appendChild(panel);

    return body;
  }
  function renderSignedContribution100(container, title, labels, rawValues, yLabel = "Share of |total| (%)") {
    const tile = document.createElement("div");
    tile.className = "tile";

    const h = document.createElement("h4");
    h.textContent = title;

    const div = document.createElement("div");
    tile.appendChild(h);
    tile.appendChild(div);
    container.appendChild(tile);

    const vals = rawValues.map(v => Number(v) || 0);
    const denom = vals.reduce((acc, v) => acc + Math.abs(v), 0) || 1;

    const pos = vals.map(v => (v > 0 ? (v / denom) * 100 : 0));
    const neg = vals.map(v => (v < 0 ? (-v / denom) * 100 : 0));

    Plotly.newPlot(
      div,
      [
        {
          type: "bar",
          x: labels,
          y: pos,
          name: "Positive",
          hovertemplate: "%{x}<br>+%{y:.2f}%<extra></extra>",
        },
        {
          type: "bar",
          x: labels,
          y: neg,
          name: "Negative",
          hovertemplate: "%{x}<br>-%{y:.2f}%<extra></extra>",
        },
      ],
      {
        barmode: "stack",
        height: 260,
        margin: { t: 10, l: 50, r: 10, b: 80 },
        paper_bgcolor: "#0d1117",
        plot_bgcolor: "#0d1117",
        font: { color: "#e6edf3" },
        yaxis: { title: yLabel, range: [0, 100] },
        xaxis: { automargin: true, tickangle: -25 },
        legend: { orientation: "h", y: -0.25 },
      },
      { displayModeBar: false, responsive: true }
    );

    setTimeout(() => Plotly.Plots.resize(div), 0);
  }

  function renderPie(container, title, labels, values) {
    const tile = document.createElement("div");
    tile.className = "tile";

    const h = document.createElement("h4");
    h.textContent = title;

    const div = document.createElement("div");
    tile.appendChild(h);
    tile.appendChild(div);
    container.appendChild(tile);

    const safeVals = values.map(v => Math.abs(Number(v) || 0));
    Plotly.newPlot(
      div,
      [{
        type: "pie",
        labels,
        values: safeVals,
        hole: 0.4,
        textinfo: "label+percent",
      }],
      {
        height: 260,
        margin: { t: 10, b: 10, l: 10, r: 10 },
        paper_bgcolor: "#0d1117",
        font: { color: "#e6edf3" },
        showlegend: false,
      },
      { displayModeBar: false, responsive: true }
    );

    setTimeout(() => Plotly.Plots.resize(div), 0);
  }

  function renderBar(container, title, x, y, yLabel) {
    const tile = document.createElement("div");
    tile.className = "tile";

    const h = document.createElement("h4");
    h.textContent = title;

    const div = document.createElement("div");
    tile.appendChild(h);
    tile.appendChild(div);
    container.appendChild(tile);

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
          colorscale: "RdBu",
          cmin: -maxAbs,
          cmax: maxAbs,
        },
        hovertemplate: "%{x}<br>%{y}<extra></extra>",
      }],
      {
        height: 260,
        margin: { t: 10, l: 45, r: 10, b: 60 },
        paper_bgcolor: "#0d1117",
        plot_bgcolor: "#0d1117",
        font: { color: "#e6edf3" },
        yaxis: { title: yLabel },
        xaxis: { automargin: true, tickangle: -25 },
      },
      { displayModeBar: false, responsive: true }
    );

    setTimeout(() => Plotly.Plots.resize(div), 0);
  }

  function renderBarDuration(container, title, labels, durationVals) {
    const tile = document.createElement("div");
    tile.className = "tile";

    const h = document.createElement("h4");
    h.textContent = title;

    const div = document.createElement("div");
    tile.appendChild(h);
    tile.appendChild(div);
    container.appendChild(tile);

    const seconds = durationVals.map(v => Number(window.rawValue(v)) || 0);
    const hours = seconds.map(s => s / 3600);

    const hoverText = durationVals.map(v => window.displayValue(v));

    Plotly.newPlot(
      div,
      [{
        type: "bar",
        x: labels,
        y: hours,
        text: hoverText,
        hovertemplate: "%{x}<br>%{text}<extra></extra>",
      }],
      {
        height: 260,
        margin: { t: 10, l: 45, r: 10, b: 60 },
        paper_bgcolor: "#0d1117",
        plot_bgcolor: "#0d1117",
        font: { color: "#e6edf3" },
        yaxis: { title: "Avg duration (hours)" },
        xaxis: { automargin: true, tickangle: -25 },
      },
      { displayModeBar: false, responsive: true }
    );

    setTimeout(() => Plotly.Plots.resize(div), 0);
  }

  function renderTagBlock(title, rows, tagKey) {
    if (!rows || !rows.length) return;

    const body = makePanel(title);

    const row1 = document.createElement("div");
    row1.className = "grid-3-1";

    const tableTile = document.createElement("div");
    tableTile.className = "tile";
    tableTile.appendChild(renderTable(rows));

    const shareTile = document.createElement("div");
    shareTile.className = "tile";

    row1.appendChild(tableTile);
    row1.appendChild(shareTile);
    body.appendChild(row1);

    const labels = rows.map(r => window.displayValue(r[tagKey]));
    const share = rows.map(r => window.rawValue(r["Share (%)"]) ?? 0);
    renderPie(shareTile, "Share of occurrences", labels, share);

    const row2 = document.createElement("div");
    row2.className = "grid-4";
    body.appendChild(row2);

    const expectancy = rows.map(r => window.rawValue(r["Expectancy (USD)"]) ?? 0);
    renderBar(row2, "Expectancy by tag", labels, expectancy, "Expectancy (USD)");

    const avgDur = rows.map(r => window.rawValue(r["Avg duration"]) ?? 0);
    renderBarDuration(row2, "Avg duration by tag", labels, rows.map(r => r["Avg duration"]));

    const pnlRaw = rows.map(r => window.rawValue(r["Total PnL"]) ?? 0);
    renderSignedContribution100(row2, "PnL contribution (100% of |total|)", labels, pnlRaw, "Share of |Total PnL| (%)");

    const ddRaw = rows.map(r => window.rawValue(r["Max drawdown contribution (USD)"]) ?? 0);
    renderSignedContribution100(row2, "DD contribution (100% of |total|)", labels, ddRaw, "Share of |DD contribution| (%)");
  }

  // ------------------------------
  // Entry tag block
  // ------------------------------

  const entry = report["Performance by Entry Tag"];
  if (entry && entry.rows) {
    renderTagBlock("ENTRY TAG", entry.rows, "Entry tag");
  }

  // ------------------------------
  // Exit tag block
  // ------------------------------

  const exit = report["Exit Logic Diagnostics"];
  if (exit && exit.rows) {
    renderTagBlock("EXIT TAG", exit.rows, "Exit tag");
  }
}