function renderEquityDrawdown(report) {
  const root = document.getElementById("equity-drawdown-chart");
  if (!root) return;

  const data = report["__equity__"];
  if (!data) {
    root.innerHTML = "<em>No equity data</em>";
    return;
  }

  const time = data.time;
  const equity = data.equity;
  const drawdown = data.drawdown.map(v => -Math.abs(v));

  Plotly.newPlot(
    root,
    [
      {
        x: time,
        y: equity,
        type: "scatter",
        mode: "lines",
        name: "Equity",
        line: { color: "#58a6ff", width: 2 },
        yaxis: "y1",
      },

      {
        x: time,
        y: drawdown,
        type: "scatter",
        fill: "tozeroy",
        mode: "lines",
        name: "Drawdown",
        line: { color: "#f85149", width: 1 },
        yaxis: "y2",
        opacity: 0.6,
      },
    ],
    {
      height: 320,
      margin: { t: 20, l: 60, r: 60, b: 40 },
      paper_bgcolor: "#161b22",
      plot_bgcolor: "#161b22",
      font: { color: "#e6edf3" },

      xaxis: {
        title: "Time",
        showgrid: false,
      },

      yaxis: {
        title: "Equity",
        side: "left",
        showgrid: true,
        gridcolor: "#30363d",
      },

      yaxis2: {
        title: "Drawdown",
        side: "right",
        overlaying: "y",
        showgrid: false,
        zeroline: true,
        zerolinecolor: "#30363d",
      },

      legend: {
        orientation: "h",
        y: -0.25,
      },
    },
    {
      displayModeBar: true,
      displaylogo: false,
    }
  );
}