function renderKPI(report) {
  const root = document.getElementById("kpi-table");
  if (!root) return;

  const payload = report["Core Performance Metrics"];
  if (!payload) return;

  root.innerHTML = "";

  const kpis = [
    "Backtesting from",
    "Backtesting to",
    "Total trades",
    "Trades/day (avg)",

    "Starting balance",
    "Final balance",
    "Absolute profit",
    "Total return (%)",
    "CAGR (%)",

    "Profit factor",
    "Expectancy (USD)",
    "Win rate (%)",
    "Avg win",
    "Avg loss",
    "Avg win/loss",

    "Max drawdown ($)",
    "Max drawdown (%)",
    "Max daily loss ($)",
    "Max daily loss (%)",
    "Max consecutive wins",
    "Max consecutive losses",
  ];

  const rows = kpis
    .filter(key => payload[key] !== undefined)
    .map(key => ({
      Metric: key,
      Value: window.displayValue(payload[key]),
    }));

  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr>
        <th>Metric</th>
        <th style="text-align:right;">Value</th>
      </tr>
    </thead>
    <tbody>
      ${rows.map(r => `
        <tr>
          <td>${r.Metric}</td>
          <td style="text-align:right;">${r.Value}</td>
        </tr>
      `).join("")}
    </tbody>
  `;

  const wrap = document.createElement("div");
  wrap.className = "kpi-table";
  wrap.appendChild(table);
  root.appendChild(wrap);
}