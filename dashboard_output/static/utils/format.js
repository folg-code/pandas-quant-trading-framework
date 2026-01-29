function displayValue(v) {
  if (v === null || v === undefined) return "-";
  if (typeof v === "object" && v.display !== undefined) return v.display;
  return String(v);
}

function rawValue(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "object" && v.raw !== undefined) return v.raw;
  return v;
}

window.displayValue = displayValue;
window.rawValue = rawValue;