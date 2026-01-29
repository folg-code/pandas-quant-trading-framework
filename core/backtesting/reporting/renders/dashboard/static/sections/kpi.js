function renderKPI(report) {
  const core = report["Core Performance Metrics"] || {};
  const kpiGrid = document.getElementById("kpi-grid");
  if (!kpiGrid) return;

  const kpis = [
    ["Total return (%)", "%"],
    ["CAGR (%)", "%"],
    ["Expectancy (USD)", ""],
    ["Max drawdown (%)", "%"],
  ];

  kpis.forEach(([key, suffix]) => {
    const v = core[key] ?? "-";

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3>${key}</h3>
      <div class="kpi-value">${v}${suffix}</div>
    `;

    kpiGrid.appendChild(card);
  });
}