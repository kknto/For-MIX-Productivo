(function () {
  window.FormixShared = window.FormixShared || {};

  function getCancunDate() {
    const now = new Date();
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Cancun",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    const parts = formatter.formatToParts(now);
    const p = parts.reduce((acc, part) => {
      acc[part.type] = part.value;
      return acc;
    }, {});
    return new Date(`${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}`);
  }

  function getTodayCancun() {
    const d = getCancunDate();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function getFullTodayCancun() {
    const d = getCancunDate();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hrs = String(d.getHours()).padStart(2, "0");
    const min = String(d.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day} ${hrs}:${min}`;
  }

  function updateCancunClock(timeEl, dateEl) {
    if (!timeEl || !dateEl) return;
    const d = getCancunDate();
    const hrs = String(d.getHours()).padStart(2, "0");
    const min = String(d.getMinutes()).padStart(2, "0");
    const sec = String(d.getSeconds()).padStart(2, "0");
    timeEl.textContent = `${hrs}:${min}:${sec}`;
    const options = {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      timeZone: "America/Cancun",
    };
    dateEl.textContent = new Intl.DateTimeFormat("es-MX", options).format(new Date());
  }

  function startCancunClock(elements = {}) {
    const timeEl = elements.timeEl || document.getElementById("clockTime");
    const dateEl = elements.dateEl || document.getElementById("clockDate");
    const tick = () => updateCancunClock(timeEl, dateEl);
    tick();
    window.setInterval(tick, 1000);
    return tick;
  }

  window.FormixShared.time = {
    getCancunDate,
    getTodayCancun,
    getFullTodayCancun,
    updateCancunClock,
    startCancunClock,
  };
})();
