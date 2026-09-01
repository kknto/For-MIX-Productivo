(function () {
  window.FormixShared = window.FormixShared || {};

  function createDatasetCore(ctx) {
    const {
      state,
      normalizeHeader,
      splitHeaderName,
      compareValues,
      classifyComponent,
      componentUnit,
      isAggregateComponent,
      averagePV,
      densityFor,
      toNumber,
      getModDateColIndex,
    } = ctx;

    function buildHeaderIndex() {
      const idx = {};
      state.headers.forEach((header, i) => {
        const key = normalizeHeader(splitHeaderName(header).name || header);
        if (key === "no") idx.no = i;
        else if (key === "formula") idx.formula = i;
        else if (key === "cod") idx.cod = i;
        else if (key === "fc") idx.fc = i;
        else if (key === "edad") idx.edad = i;
        else if (key === "coloc" || key === "tipo") idx.tipo = i;
        else if (key === "tma") idx.tma = i;
        else if (key === "rev") idx.rev = i;
        else if (key === "var" || key === "comp" || key === "complemento") idx.comp = i;
        else if (key === "familia" || key === "family" || key.startsWith("familia") || key.startsWith("family")) idx.family = i;
      });
      state.index = idx;
    }

    function valueByKey(row, key) {
      const idx = state.index[key];
      if (typeof idx !== "number") return "";
      return (row[idx] ?? "").toString().trim();
    }

    function getRowModDate(row) {
      const modIdx = getModDateColIndex();
      if (modIdx < 0) return "";
      return (row[modIdx] ?? "").toString().trim();
    }

    function deriveFamily(row) {
      const explicitFamily = valueByKey(row, "family");
      if (explicitFamily) return explicitFamily;
      if (state.datasetFamily) return state.datasetFamily;
      const formula = valueByKey(row, "formula");
      const no = valueByKey(row, "no");
      const cod = valueByKey(row, "cod");
      if (formula) {
        const start = formula.match(/^(\d{2,3})/);
        if (start) return start[1];
        const any = formula.match(/(\d{2,3})/);
        if (any) return any[1];
        const token = formula.split(/[-\s]/)[0];
        if (token) return token;
      }
      return no || cod || "-";
    }

    function getUniqueValues(columnKey) {
      const idx = state.index[columnKey];
      if (typeof idx !== "number") return [];
      const set = new Set();
      state.rows.forEach((row) => {
        const value = (row[idx] ?? "").toString().trim();
        if (value !== "") set.add(value);
      });
      return [...set].sort((a, b) => compareValues(a, b));
    }

    function fillSelect(selectEl, values, keepValue = "") {
      const current = keepValue || selectEl.value || "";
      selectEl.innerHTML = "";
      const all = document.createElement("option");
      all.value = "";
      all.textContent = "Todos";
      selectEl.appendChild(all);
      values.forEach((v) => {
        const op = document.createElement("option");
        op.value = v;
        op.textContent = v;
        if (v === current) op.selected = true;
        selectEl.appendChild(op);
      });
    }

    function getMetaIndexes() {
      const set = new Set(Object.values(state.index).filter((v) => typeof v === "number"));
      const modIndex = getModDateColIndex();
      if (modIndex >= 0) set.add(modIndex);
      return set;
    }

    function buildAggregateColumnMap() {
      const counters = { fino: 0, grueso: 0 };
      const metaIndexes = getMetaIndexes();
      const map = {
        "Fino 1": new Set(),
        "Fino 2": new Set(),
        "Grueso 1": new Set(),
        "Grueso 2": new Set(),
      };

      state.headers.forEach((header, index) => {
        if (metaIndexes.has(index)) return;
        const rawHeader = (header ?? "").toString().trim();
        if (!rawHeader) return;
        const component = classifyComponent(rawHeader, counters);
        if (map[component]) map[component].add(rawHeader);
      });

      return {
        "Fino 1": [...map["Fino 1"]],
        "Fino 2": [...map["Fino 2"]],
        "Grueso 1": [...map["Grueso 1"]],
        "Grueso 2": [...map["Grueso 2"]],
      };
    }

    function extractRecipe(row) {
      const counters = { fino: 0, grueso: 0 };
      const metaIndexes = getMetaIndexes();
      const aggregate = new Map();
      const isGlobal = !Array.isArray(row);

      if (isGlobal) {
        const exclude = ["formula", "no", "cod", "fc", "edad", "tipo", "tma", "rev", "comp", "family", "source", "updated", "id", "dataset_id"];
        Object.keys(row).forEach((header) => {
          if (header.startsWith("_")) return;
          if (exclude.includes(header.toLowerCase())) return;
          const qty = toNumber(row[header]);
          if (qty === 0) return;
          const component = classifyComponent(header, counters);
          aggregate.set(component, (aggregate.get(component) || 0) + qty);
        });
      } else {
        state.headers.forEach((header, index) => {
          if (metaIndexes.has(index)) return;
          const rawHeader = (header ?? "").toString().trim();
          if (!rawHeader) return;
          const qty = toNumber(row[index]);
          if (qty === 0) return;
          const component = classifyComponent(rawHeader, counters);
          aggregate.set(component, (aggregate.get(component) || 0) + qty);
        });
      }

      ["Fino 1", "Fino 2", "Grueso 1", "Grueso 2"].forEach((aggName) => {
        if (!aggregate.has(aggName)) aggregate.set(aggName, 0);
      });

      const priority = [
        "Cemento",
        "Fino 1",
        "Fino 2",
        "Grueso 1",
        "Grueso 2",
        "Agua",
        "Reductor",
        "Retardante",
        "Fibra",
        "Imper",
      ];

      const ordered = [];
      priority.forEach((name) => {
        if (aggregate.has(name)) {
          ordered.push({ name, qty: aggregate.get(name), unit: componentUnit(name) });
          aggregate.delete(name);
        }
      });

      [...aggregate.entries()]
        .sort((a, b) => compareValues(a[0], b[0]))
        .forEach(([name, qty]) => ordered.push({ name, qty, unit: componentUnit(name) }));

      return ordered.map((item) => ({
        ...item,
        volume: isAggregateComponent(item.name) ? item.qty / (averagePV(item.name) || densityFor(item.name, item.unit)) : 0,
      }));
    }

    return {
      buildHeaderIndex,
      valueByKey,
      getRowModDate,
      deriveFamily,
      getUniqueValues,
      fillSelect,
      buildAggregateColumnMap,
      extractRecipe,
    };
  }

  window.FormixShared.datasetCore = {
    createDatasetCore,
  };
})();
