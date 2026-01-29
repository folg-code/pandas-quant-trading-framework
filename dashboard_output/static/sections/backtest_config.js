function renderBacktestConfig(report) {
  const section = report["Backtest Configuration & Assumptions"];
  if (!section) return;

  const root = document.getElementById("backtest-config");
  if (!root) return;

  root.innerHTML = "";

  Object.entries(section).forEach(([groupName, params]) => {
    const card = document.createElement("div");
    card.className = "config-card";

    const title = document.createElement("h4");
    title.textContent = groupName;
    card.appendChild(title);

    const list = document.createElement("div");
    list.className = "config-list";

    Object.entries(params).forEach(([k, v]) => {
      const row = document.createElement("div");
      row.className = "config-row";

      row.innerHTML = `
        <div class="config-key">${k}</div>
        <div class="config-value">${v}</div>
      `;

      list.appendChild(row);
    });

    card.appendChild(list);
    root.appendChild(card);
  });
}