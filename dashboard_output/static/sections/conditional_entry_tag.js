function renderConditionalEntryTag(report) {
  const section = report["Conditional Entry Tag Performance"];
  const tagStats = report["Performance by Entry Tag"];
  if (!section || !tagStats) return;

  const select = document.getElementById("conditional-entry-select");
  const summaryRoot = document.getElementById("entry-tag-summary");
  const grid = document.getElementById("conditional-entry-grid");

  const minTradesInput = document.getElementById("min-trades");
  const metricSelect = document.getElementById("metric-select");
  const sortSelect = document.getElementById("sort-select");

  if (
    !select ||
    !summaryRoot ||
    !grid ||
    !minTradesInput ||
    !metricSelect ||
    !sortSelect
  ) return;

  // ==================================================
  // Helpers
  // ==================================================

  function renderSummaryTable(row) {
    const table = document.createElement("table");
    const cols = Object.keys(row);

    table.innerHTML = `
      <thead>
        <tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>
      </thead>
      <tbody>
        <tr>${cols.map(c => `<td>${row[c]}</td>`).join("")}</tr>
      </tbody>
    `;
    return table;
  }

  function renderBarChart(container, title, categories, values, metric) {
    const h = document.createElement("h4");
    h.textContent = title;

    const chartDiv = document.createElement("div");
    chartDiv.style.width = "100%";
    chartDiv.style.maxWidth = "100%";

    container.appendChild(h);
    container.appendChild(chartDiv);

    if (!categories.length) return;

    const maxAbs = Math.max(...values.map(v => Math.abs(v))) || 1;

    Plotly.newPlot(
      chartDiv,
      [{
        type: "bar",
        x: categories,
        y: values,
        marker: {
          color: values,
          colorscale: "RdBu",
          cmin: -maxAbs,
          cmax: maxAbs,
        },
      }],
      {
        margin: { t: 20, l: 40, r: 20, b: 40 },
        paper_bgcolor: "#161b22",
        plot_bgcolor: "#161b22",
        font: { color: "#e6edf3" },
        yaxis: { title: metric },
        xaxis: { automargin: true },
      },
      {
        displayModeBar: false,
        responsive: true,
      }
    );

    // 👇 KLUCZ: wymuś dopasowanie do kolumny grida
    setTimeout(() => {
      Plotly.Plots.resize(chartDiv);
    }, 0);
  }

  // ==================================================
  // Populate selector (WITH DEFAULT VALUE)
  // ==================================================

  select.innerHTML = "";

  tagStats.rows.forEach((r, i) => {
    const opt = document.createElement("option");
    opt.value = r["Entry tag"];
    opt.textContent = r["Entry tag"];
    if (i === 0) opt.selected = true; // ✅ KLUCZ
    select.appendChild(opt);
  });

  // ==================================================
  // Render logic
  // ==================================================

  function render(entryTag) {
    summaryRoot.innerHTML = "";
    grid.innerHTML = "";

    // ---------- SUMMARY (2/3 WIDTH) ----------
    const summaryRow = tagStats.rows.find(
      r => r["Entry tag"] === entryTag
    );
    if (summaryRow) {
      summaryRoot.appendChild(renderSummaryTable(summaryRow));
    }

    const metric = metricSelect.value;
    const minTrades = Number(minTradesInput.value);
    const sortDir = sortSelect.value;

    const timeCharts = [];
    const contextCharts = [];

    Object.entries(section).forEach(([ctxName, block]) => {
      let rows = block.rows.filter(
        r => r["Entry tag"] === entryTag && r["Trades"] >= minTrades
      );
      if (!rows.length) return;

      rows.sort((a, b) => {
        const va = a[metric];
        const vb = b[metric];
        return sortDir === "desc" ? vb - va : va - vb;
      });

      const categories = rows.map(r => r["Context"]);
      const values = rows.map(r => r[metric]);

      if (ctxName.toLowerCase().includes("hour") ||
          ctxName.toLowerCase().includes("weekday")) {
        timeCharts.push({ ctxName, categories, values });
      } else {
        contextCharts.push({ ctxName, categories, values });
      }
    });

    // ---------- NON-TIME CONTEXTS (1/4 EACH) ----------
    contextCharts.forEach(c => {
      const box = document.createElement("div");
      box.className = "context-chart";
      renderBarChart(box, c.ctxName, c.categories, c.values, metric);
      grid.appendChild(box);
    });

    // ---------- TIME CONTEXT (ONCE, AT END, 1/2) ----------
    if (timeCharts.length) {
      const t = timeCharts[0];
      const box = document.createElement("div");
      box.className = "time-chart";
      renderBarChart(box, t.ctxName, t.categories, t.values, metric);
      grid.appendChild(box);
    }
  }

  // ==================================================
  // Events
  // ==================================================

  select.onchange = () => render(select.value);
  [minTradesInput, metricSelect, sortSelect].forEach(el => {
    el.onchange = () => render(select.value);
  });

  // ---------- INITIAL RENDER ----------
  render(select.value);
}