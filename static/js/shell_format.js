(function () {
  window.FormixShared = window.FormixShared || {};

  function stripAccents(value) {
    return value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function normalize(value) {
    return stripAccents((value ?? "").toString().toLowerCase().trim());
  }

  function normalizeHeader(value) {
    return normalize(value).replace(/[^a-z0-9]/g, "");
  }

  function toNumber(value) {
    const clean = (value ?? "").toString().replace(",", ".").trim();
    if (clean === "") return 0;
    const parsed = Number(clean);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatNum(value) {
    return Number(value).toLocaleString("es-MX", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function formatVol(value) {
    return Number(value).toLocaleString("es-MX", {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    });
  }

  function formatMoney(value) {
    return `$${formatNum(value)}`;
  }

  function escapeHtml(value) {
    return (value ?? "")
      .toString()
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function nowStamp() {
    const dt = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const y = dt.getFullYear();
    const m = pad(dt.getMonth() + 1);
    const d = pad(dt.getDate());
    const hh = pad(dt.getHours());
    const mm = pad(dt.getMinutes());
    return `${y}-${m}-${d} ${hh}:${mm}`;
  }

  window.FormixShared.format = {
    stripAccents,
    normalize,
    normalizeHeader,
    toNumber,
    formatNum,
    formatVol,
    formatMoney,
    escapeHtml,
    nowStamp,
  };
})();
