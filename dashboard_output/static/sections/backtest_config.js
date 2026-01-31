function renderBacktestConfig(report) {
  const root = document.getElementById("backtest-info-table");
  if (!root) return;

  const section = report["Backtest Configuration & Assumptions"];
  if (!section) return;

  root.innerHTML = "";

  // spłaszcz {"Market & Data": {...}, "Execution Model": {...}} -> [{Section, Key, Value}]
  const rows = [];
  Object.entries(section).forEach(([groupName, groupObj]) => {
    if (!groupObj) return;
    Object.entries(groupObj).forEach(([k, v]) => {
      rows.push({
        Section: groupName,
        Metric: k,
        Value: window.displayValue ? window.displayValue(v) : String(v),
      });
    });
  });

  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr>
        <th>Section</th>
        <th>Metric</th>
        <th style="text-align:right;">Value</th>
      </tr>
    </thead>
    <tbody>
      ${rows.map(r => `
        <tr>
          <td>${r.Section}</td>
          <td>${r.Metric}</td>
          <td style="text-align:right;">${r.Value}</td>
        </tr>
      `).join("")}
    </tbody>
  `;

  const wrap = document.createElement("div");
  wrap.className = "info-table";
  wrap.appendChild(table);
  root.appendChild(wrap);
}