(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createDoserSearchModule = function createDoserSearchModule(ctx) {
    let initialized = false;
    const disposers = [];

    function on(element, eventName, handler) {
      if (!element) return;
      element.addEventListener(eventName, handler);
      disposers.push(() => element.removeEventListener(eventName, handler));
    }

    function sameEntry(left, right) {
      if (!left || !right) return false;
      if (left.isGlobal !== right.isGlobal) return false;
      if (left.isGlobal) {
        return left.row.formula === right.row.formula && left.row.no === right.row.no;
      }
      return left.sourceIndex === right.sourceIndex;
    }

    function applyFilter(entry, filters) {
      const row = entry.row;
      const isGlobal = !!entry.isGlobal;
      const getV = (key) => isGlobal ? (row[key] || "") : ctx.valueByKey(row, key);
      const family = isGlobal ? (row.family || "") : ctx.deriveFamily(row);
      const formula = getV("formula");
      const no = getV("no");
      const cod = getV("cod");

      if (filters.family) {
        const term = ctx.normalize(filters.family);
        const haystack = `${family} ${formula} ${no} ${cod}`;
        if (!ctx.normalize(haystack).includes(term)) return false;
      }
      if (filters.fc && ctx.normalize(getV("fc")) !== ctx.normalize(filters.fc)) return false;
      if (filters.edad && ctx.normalize(getV("edad")) !== ctx.normalize(filters.edad)) return false;
      if (filters.tipo && ctx.normalize(getV("tipo")) !== ctx.normalize(filters.tipo)) return false;
      if (filters.tma && ctx.normalize(getV("tma")) !== ctx.normalize(filters.tma)) return false;
      if (filters.rev && ctx.normalize(getV("rev")) !== ctx.normalize(filters.rev)) return false;
      if (filters.comp && ctx.normalize(getV("comp")) !== ctx.normalize(filters.comp)) return false;
      return true;
    }

    function fillDoserSelectors() {
      ctx.fillSelect(ctx.doserFields.family, ctx.getUniqueValues("family"));
      ctx.fillSelect(ctx.doserFields.fc, ctx.getUniqueValues("fc"));
      ctx.fillSelect(ctx.doserFields.edad, ctx.getUniqueValues("edad"));
      ctx.fillSelect(ctx.doserFields.tipo, ctx.getUniqueValues("tipo"));
      ctx.fillSelect(ctx.doserFields.tma, ctx.getUniqueValues("tma"));
      ctx.fillSelect(ctx.doserFields.rev, ctx.getUniqueValues("rev"));
      ctx.fillSelect(ctx.doserFields.comp, ctx.getUniqueValues("comp"));
    }

    function fillDoserSelectorsGlobal() {
      if (!ctx.state.doser.globalRecipes.length) {
        fillDoserSelectors();
        return;
      }

      const getUnique = (key) => {
        const values = new Set();
        ctx.state.doser.globalRecipes.forEach((recipe) => {
          if (recipe[key]) values.add(String(recipe[key]).trim());
        });
        return Array.from(values).sort();
      };

      ctx.fillSelect(ctx.doserFields.family, getUnique("family"));
      ctx.fillSelect(ctx.doserFields.fc, getUnique("fc"));
      ctx.fillSelect(ctx.doserFields.edad, getUnique("edad"));
      ctx.fillSelect(ctx.doserFields.tipo, getUnique("tipo"));
      ctx.fillSelect(ctx.doserFields.tma, getUnique("tma"));
      ctx.fillSelect(ctx.doserFields.rev, getUnique("rev"));
      ctx.fillSelect(ctx.doserFields.comp, getUnique("comp"));
    }

    function renderResults() {
      const queryBody = ctx.elements.queryBody;
      if (!queryBody) return;

      queryBody.innerHTML = "";
      if (!ctx.state.doser.results.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="9">Sin resultados para los filtros del dosificador.</td>`;
        queryBody.appendChild(tr);
        return;
      }

      ctx.state.doser.results.forEach((entry) => {
        const row = entry.row;
        const tr = document.createElement("tr");
        if (sameEntry(ctx.state.doser.selectedEntry, entry)) tr.classList.add("is-selected");

        const displayVal = (key) => ctx.escapeHtml(
          entry.isGlobal ? (row[key] || "-") : (ctx.valueByKey(row, key) || "-")
        );

        tr.innerHTML = `
          <td>${ctx.escapeHtml(entry.isGlobal ? (row.family || "") : ctx.deriveFamily(row))}</td>
          <td>${displayVal("formula")}</td>
          <td>${displayVal("fc")}</td>
          <td>${displayVal("edad")}</td>
          <td>${displayVal("tipo")}</td>
          <td>${displayVal("tma")}</td>
          <td>${displayVal("rev")}</td>
          <td>${displayVal("comp")}</td>
          <td>${ctx.escapeHtml((entry.isGlobal ? row._updated : ctx.getRowModDate(row)) || "-")}</td>
        `;
        tr.addEventListener("click", () => {
          selectRecipe(entry);
        });
        queryBody.appendChild(tr);
      });
    }

    async function selectRecipe(entry) {
      ctx.state.doser.selectedEntry = entry;

      if (entry.isGlobal && entry.row._source !== ctx.state.file) {
        ctx.setStatus(`Cambiando al archivo ${entry.row._source}...`, "info");
        try {
          const resp = await ctx.apiFetch("/api/select", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file: entry.row._source }),
          });
          const res = await resp.json();
          if (!res.ok) {
            ctx.setStatus(`Error al cambiar de archivo: ${res.error}`, "err");
            return;
          }
          ctx.state.file = res.file;
          ctx.state.headers = res.headers || [];
          ctx.state.rows = res.rows || [];
          ctx.state.datasetFamily = res.family || "";
          ctx.state.version = res.version;
          await Promise.all([ctx.loadQcData(), ctx.loadDoserParams()]);
        } catch (error) {
          ctx.setStatus(`Error de red al cambiar archivo: ${error.message}`, "err");
          return;
        }
      }

      ctx.state.doser.realLoads = {};
      renderResults();
      ctx.renderModule.render();
    }

    function runSearch() {
      const filters = {
        family: ctx.doserFields.family.value.trim(),
        fc: ctx.doserFields.fc.value,
        edad: ctx.doserFields.edad.value,
        tipo: ctx.doserFields.tipo.value,
        tma: ctx.doserFields.tma.value,
        rev: ctx.doserFields.rev.value,
        comp: ctx.doserFields.comp.value,
      };

      let pool = [];
      if (ctx.state.doser.globalRecipes.length > 0) {
        pool = ctx.state.doser.globalRecipes.map((recipe, index) => ({
          row: recipe,
          sourceIndex: index,
          isGlobal: true,
        }));
      } else {
        pool = ctx.state.rows.map((row, sourceIndex) => ({
          row,
          sourceIndex,
          isGlobal: false,
        }));
      }

      ctx.state.doser.results = pool.filter((entry) => applyFilter(entry, filters));

      const current = ctx.state.doser.selectedEntry;
      const stillInResults = current && ctx.state.doser.results.some((entry) => sameEntry(entry, current));
      if (!stillInResults) {
        ctx.state.doser.selectedEntry = ctx.state.doser.results.length ? ctx.state.doser.results[0] : null;
        ctx.state.doser.realLoads = {};
      }

      renderResults();
      ctx.renderModule.render();
    }

    async function loadGlobalRecipes() {
      try {
        const resp = await ctx.apiFetch("/api/doser/recipes_global");
        const data = await resp.json();
        if (data.ok) {
          ctx.state.doser.globalRecipes = data.recipes || [];
          fillDoserSelectorsGlobal();
          runSearch();
          return;
        }
      } catch (error) {
        console.warn("No se pudieron cargar recetas globales:", error);
      }
      fillDoserSelectors();
      runSearch();
    }

    function clearFilters() {
      ctx.doserFields.family.value = "";
      ctx.doserFields.fc.value = "";
      ctx.doserFields.edad.value = "";
      ctx.doserFields.tipo.value = "";
      ctx.doserFields.tma.value = "";
      ctx.doserFields.rev.value = "";
      ctx.doserFields.comp.value = "";
      runSearch();
    }

    function init() {
      if (initialized) return;
      initialized = true;
      on(ctx.elements.searchBtn, "click", runSearch);
      on(ctx.elements.clearBtn, "click", clearFilters);
    }

    function unmount() {
      while (disposers.length) {
        const dispose = disposers.pop();
        dispose();
      }
      initialized = false;
    }

    return {
      init,
      unmount,
      sameEntry,
      clearFilters,
      fillDoserSelectors,
      fillDoserSelectorsGlobal,
      renderResults,
      selectRecipe,
      runSearch,
      loadGlobalRecipes,
    };
  };
})();
