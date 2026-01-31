function hoursToHM(h) {
  const x = Number(h) || 0;
  const hours = Math.floor(x);
  const minutes = Math.round((x - hours) * 60);
  return `${hours}h ${minutes}m`;
}

function renderTradeDistribution(report) {
  const section = report["Trade Distribution & Payoff Geometry"];
  if (!section) return;

  const block = section["R-multiple distribution"];
  if (!block || !block.rows) return;

  const rows = block.rows;

  const countRoot = document.getElementById("trade-r-count");
  const shareRoot = document.getElementById("trade-r-share");
  const durRoot = document.getElementById("trade-r-duration");

  if (!countRoot || !shareRoot || !durRoot) return;

  countRoot.innerHTML = "";
  shareRoot.innerHTML = "";
  durRoot.innerHTML = "";

  const buckets = rows.map(r => r["Bucket"]);

  const trades = rows.map(r => Number(window.rawValue(r["Trades"])) || 0);

  const shares = rows.map(r => Number(window.rawValue(r["Share (%)"])) || 0);

  const durations = rows.map(r => Number(window.rawValue(r["Avg duration"])) || 0);

  // ==================================================
  // 1️⃣ R DISTRIBUTION (BAR)
  // ==================================================

  Plotly.newPlot(
    countRoot,
    [{
      type: "bar",
      x: buckets,
      y: trades,
      marker: { color: "#58a6ff" },
    }],
    {
      title: "Trades by R bucket",
      margin: { t: 40, l: 50, r: 20, b: 40 },
      paper_bgcolor: "#161b22",
      plot_bgcolor: "#161b22",
      font: { color: "#e6edf3" },
      xaxis: {
        type: "category",
        categoryorder: "array",
        categoryarray: buckets,
      },
      yaxis: { title: "Trades" },
    },
    { displayModeBar: false, responsive: true }
  );

  // ==================================================
  // 2️⃣ SHARE % (PIE)
  // ==================================================

  Plotly.newPlot(
    shareRoot,
    [{
      type: "pie",
      labels: buckets,
      values: shares,
      hole: 0.4,
      textinfo: "label+percent",
    }],
    {
      title: "Share (%) by R bucket",
      paper_bgcolor: "#161b22",
      font: { color: "#e6edf3" },
      margin: { t: 40, b: 20 },
      showlegend: false,
    },
    { displayModeBar: false, responsive: true }
  );

  // ==================================================
  // 3️⃣ AVG DURATION (BAR)
  // ==================================================

  Plotly.newPlot(
    durRoot,
    [{
      type: "bar",
      x: buckets,
      y: durations,
      text: durations.map(hoursToHM),
      hovertemplate: "%{text}<extra></extra>",
      marker: { color: "#8b949e" },
    }],
    {
      title: "Avg trade duration by R",
      margin: { t: 40, l: 50, r: 20, b: 40 },
      paper_bgcolor: "#161b22",
      plot_bgcolor: "#161b22",
      font: { color: "#e6edf3" },
      xaxis: {
        type: "category",
        categoryorder: "array",
        categoryarray: buckets,
      },
      yaxis: { title: "Duration (hours)" },
    },
    { displayModeBar: false, responsive: true }
  );

  [countRoot, shareRoot, durRoot].forEach(div =>
    setTimeout(() => Plotly.Plots.resize(div), 0)
  );
}