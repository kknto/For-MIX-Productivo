(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createConsultaFlowModule = function createConsultaFlowModule(ctx) {
    let initialized = false;
    const disposers = [];

    function on(element, eventName, handler) {
      if (!element) return;
      element.addEventListener(eventName, handler);
      disposers.push(() => element.removeEventListener(eventName, handler));
    }

    function setStep(step) {
      const slides = ctx.elements.consultaSlides || [];
      if (!slides.length) return;
      const maxStep = slides.length - 1;
      const normalizedStep = Math.max(0, Math.min(maxStep, Number(step) || 0));
      ctx.state.consultaStep = normalizedStep;

      slides.forEach((slide, index) => {
        slide.classList.toggle("is-active", index === normalizedStep);
      });

      if (ctx.elements.consultaStepLabel) {
        ctx.elements.consultaStepLabel.textContent = `Paso ${normalizedStep + 1} de ${maxStep + 1}`;
      }
      if (ctx.elements.consultaPrevBtn) ctx.elements.consultaPrevBtn.disabled = normalizedStep === 0;
      if (ctx.elements.consultaNextBtn) ctx.elements.consultaNextBtn.disabled = normalizedStep === maxStep;
    }

    function applyQueryFilter(entry, filters) {
      const { row } = entry;
      const family = ctx.deriveFamily(row);
      const formula = ctx.valueByKey(row, "formula");
      const no = ctx.valueByKey(row, "no");
      const cod = ctx.valueByKey(row, "cod");

      if (filters.family) {
        const term = ctx.normalize(filters.family);
        const haystack = `${family} ${formula} ${no} ${cod}`;
        if (!ctx.normalize(haystack).includes(term)) return false;
      }
      if (filters.fc && ctx.normalize(ctx.valueByKey(row, "fc")) !== ctx.normalize(filters.fc)) return false;
      if (filters.edad && ctx.normalize(ctx.valueByKey(row, "edad")) !== ctx.normalize(filters.edad)) return false;
      if (filters.tipo && ctx.normalize(ctx.valueByKey(row, "tipo")) !== ctx.normalize(filters.tipo)) return false;
      if (filters.tma && ctx.normalize(ctx.valueByKey(row, "tma")) !== ctx.normalize(filters.tma)) return false;
      if (filters.rev && ctx.normalize(ctx.valueByKey(row, "rev")) !== ctx.normalize(filters.rev)) return false;
      if (filters.comp && ctx.normalize(ctx.valueByKey(row, "comp")) !== ctx.normalize(filters.comp)) return false;
      return true;
    }

    function adjustQueryVisibleRows(rowsToShow = 5) {
      const { queryTable, queryResultShell, queryBody } = ctx.elements;
      if (!queryTable || !queryResultShell) return;
      const headerHeight = queryTable.tHead ? queryTable.tHead.offsetHeight : 0;
      const firstRow = queryBody.querySelector("tr");
      const rowHeight = firstRow ? firstRow.offsetHeight : 34;
      const shellHeight = Math.round(headerHeight + (rowHeight * rowsToShow) + 2);
      queryResultShell.style.maxHeight = `${shellHeight}px`;
      queryResultShell.style.minHeight = "0";
      queryResultShell.style.flex = "0 0 auto";
      queryResultShell.style.overflow = "auto";
    }

    function renderQueryResults() {
      const { queryBody, querySummary } = ctx.elements;
      queryBody.innerHTML = "";
      if (ctx.state.queryResults.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="9">No se encontraron resultados con esos filtros.</td>`;
        queryBody.appendChild(tr);
        querySummary.textContent = "Resultados: 0";
        ctx.costsModule.renderRecipeAndCosts(null);
        setStep(0);
        adjustQueryVisibleRows(5);
        return;
      }

      ctx.state.queryResults.forEach((entry) => {
        const row = entry.row;
        const tr = document.createElement("tr");
        if (entry.sourceIndex === ctx.state.selectedQueryRow) tr.classList.add("is-selected");
        tr.innerHTML = `
          <td>${ctx.escapeHtml(ctx.deriveFamily(row))}</td>
          <td>${ctx.escapeHtml(ctx.valueByKey(row, "formula") || "-")}</td>
          <td>${ctx.escapeHtml(ctx.valueByKey(row, "fc") || "-")}</td>
          <td>${ctx.escapeHtml(ctx.valueByKey(row, "edad") || "-")}</td>
          <td>${ctx.escapeHtml(ctx.valueByKey(row, "tipo") || "-")}</td>
          <td>${ctx.escapeHtml(ctx.valueByKey(row, "tma") || "-")}</td>
          <td>${ctx.escapeHtml(ctx.valueByKey(row, "rev") || "-")}</td>
          <td>${ctx.escapeHtml(ctx.valueByKey(row, "comp") || "-")}</td>
          <td>${ctx.escapeHtml(ctx.getRowModDate(row) || "-")}</td>
        `;
        tr.addEventListener("click", () => {
          ctx.state.selectedQueryRow = entry.sourceIndex;
          renderQueryResults();
          ctx.costsModule.renderRecipeAndCosts(ctx.state.rows[entry.sourceIndex]);
          setStep(1);
        });
        queryBody.appendChild(tr);
      });

      querySummary.textContent = `Resultados: ${ctx.state.queryResults.length} (clic en una fila para ver receta)`;
      if (!ctx.state.queryResults.some((item) => item.sourceIndex === ctx.state.selectedQueryRow)) {
        ctx.state.selectedQueryRow = ctx.state.queryResults[0].sourceIndex;
      }
      ctx.costsModule.renderRecipeAndCosts(ctx.state.rows[ctx.state.selectedQueryRow]);
      adjustQueryVisibleRows(5);
    }

    function runQuery() {
      const filters = {
        family: ctx.queryFields.family.value.trim(),
        fc: ctx.queryFields.fc.value,
        edad: ctx.queryFields.edad.value,
        tipo: ctx.queryFields.tipo.value,
        tma: ctx.queryFields.tma.value,
        rev: ctx.queryFields.rev.value,
        comp: ctx.queryFields.comp.value,
      };

      const mapped = ctx.state.rows.map((row, sourceIndex) => ({ row, sourceIndex }));
      ctx.state.queryResults = mapped.filter((entry) => applyQueryFilter(entry, filters));
      renderQueryResults();
    }

    function populateQuerySelectors() {
      ctx.fillSelect(ctx.queryFields.fc, ctx.getUniqueValues("fc"));
      ctx.fillSelect(ctx.queryFields.edad, ctx.getUniqueValues("edad"));
      ctx.fillSelect(ctx.queryFields.tipo, ctx.getUniqueValues("tipo"));
      ctx.fillSelect(ctx.queryFields.tma, ctx.getUniqueValues("tma"));
      ctx.fillSelect(ctx.queryFields.rev, ctx.getUniqueValues("rev"));
      ctx.fillSelect(ctx.queryFields.comp, ctx.getUniqueValues("comp"));
    }

    function refresh() {
      ctx.buildHeaderIndex();
      populateQuerySelectors();
      ctx.renderFamiliesBoard();
      runQuery();
    }

    function clearFilters() {
      ctx.queryFields.family.value = "";
      if (ctx.doserFields.family) ctx.doserFields.family.value = "";
      ctx.queryFields.fc.value = "";
      ctx.queryFields.edad.value = "";
      ctx.queryFields.tipo.value = "";
      ctx.queryFields.tma.value = "";
      ctx.queryFields.rev.value = "";
      ctx.queryFields.comp.value = "";
      runQuery();
    }

    function load() {
      setStep(ctx.state.consultaStep);
      return Promise.resolve(ctx.fetchFamiliesSummary())
        .then(() => {
          ctx.renderFamiliesBoard();
          runQuery();
        })
        .catch(() => {
          runQuery();
        });
    }

    function init() {
      if (initialized) return;
      initialized = true;
      ctx.costsModule.syncQuoteModeButton();
      on(ctx.elements.consultaPrevBtn, "click", () => setStep(ctx.state.consultaStep - 1));
      on(ctx.elements.consultaNextBtn, "click", () => setStep(ctx.state.consultaStep + 1));
      on(ctx.elements.runQueryBtn, "click", runQuery);
      on(ctx.elements.exportReportBtn, "click", ctx.reportModule.exportReport);
      on(ctx.elements.toggleQuoteModeBtn, "click", ctx.costsModule.toggleQuoteMode);
      on(ctx.elements.clearQueryBtn, "click", clearFilters);
      Object.values(ctx.queryFields).forEach((el) => on(el, "change", runQuery));
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
      load,
      unmount,
      setStep,
      runQuery,
      refresh,
    };
  };
})();
