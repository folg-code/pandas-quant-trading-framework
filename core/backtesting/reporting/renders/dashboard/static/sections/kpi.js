function renderKPI(report) {
  const root = document.getElementById("kpi-grid");
  if (!root) return;

  // section name from python
  const payload = report["Core Performance Metrics"];
  if (!payload) return;

  // pick KPIs (keys must match what your section emits)
  const kpis = [
    { label: "Total return (%)", key: "Total return (%)" },
    { label: "CAGR (%)", key: "CAGR (%)" },
    { label: "Expectancy (USD)", key: "Expectancy (USD)" },
    { label: "Max drawdown (%)", key: "Max drawdown (%)" },
  ];

  root.innerHTML = "";

  kpis.forEach(({ label, key }) => {
    const card = document.createElement("div");
    card.className = "card";

    const h3 = document.createElement("h3");
    h3.textContent = label;

    const v = document.createElement("div");
    v.className = "kpi-value";

    v.textContent = window.displayValue(payload[key]);

    card.appendChild(h3);
    card.appendChild(v);
    root.appendChild(card);
  });
}