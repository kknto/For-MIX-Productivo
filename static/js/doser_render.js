(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createDoserRenderModule = function createDoserRenderModule(ctx) {
    let initialized = false;
    const disposers = [];

    function on(element, eventName, handler) {
      if (!element) return;
      element.addEventListener(eventName, handler);
      disposers.push(() => element.removeEventListener(eventName, handler));
    }

    function computeTheoreticalLoads(recipeItems) {
      const dose = Math.max(0, ctx.toNumber(ctx.elements.doseM3Input.value));
      ctx.state.doser.dosageM3 = dose;
      const calc = ctx.computeDoserDetailedLoads(recipeItems, dose, ctx.state.doser.params);
      return calc.rows.map((item) => ({
        name: item.name,
        unit: item.trialUnit || item.unit,
        qty: item.trialLoad,
      }));
    }

    function render() {
      ctx.renderQcTable();
      ctx.reportsModule.renderRemisionList();

      ctx.state.doser.tolerances.cemento = ctx.toNumber(ctx.elements.tolCementoInput.value || "1");
      ctx.state.doser.tolerances.agregados = ctx.toNumber(ctx.elements.tolAgregadosInput.value || "3");
      ctx.state.doser.tolerances.agua = ctx.toNumber(ctx.elements.tolAguaInput.value || "2");
      ctx.state.doser.tolerances.aditivo = ctx.toNumber(ctx.elements.tolAditivoInput.value || "1");
      ctx.state.doser.params = ctx.readParamsFromInputs();
      const dose = Math.max(0, ctx.toNumber(ctx.elements.doseM3Input.value));
      ctx.state.doser.dosageM3 = dose;

      const entry = ctx.state.doser.selectedEntry;
      const selectedRow = entry ? entry.row : null;
      const baseSummary = `Dosificacion actual: ${ctx.formatNum(dose)} m<sup>3</sup>`;
      if (ctx.elements.summary) ctx.elements.summary.innerHTML = baseSummary;
      if (ctx.elements.paramsMeta) {
        const stamp = ctx.state.doser.paramsUpdatedAt ? ctx.state.doser.paramsUpdatedAt : "sin guardar";
        const lockLabel = ctx.canEditTolerances() ? "" : " | solo lectura";
        ctx.elements.paramsMeta.textContent = `Parametros activos (${stamp})${lockLabel}`;
      }

      if (ctx.elements.recipeBody) ctx.elements.recipeBody.innerHTML = "";
      if (ctx.elements.theoreticalBody) ctx.elements.theoreticalBody.innerHTML = "";
      if (ctx.elements.realBody) ctx.elements.realBody.innerHTML = "";
      if (ctx.elements.recipeWeight) ctx.elements.recipeWeight.textContent = "0.00";
      if (ctx.elements.theoreticalWeight) ctx.elements.theoreticalWeight.textContent = "0.00";
      if (ctx.elements.realWeight) ctx.elements.realWeight.textContent = "0.00";

      if (!selectedRow) {
        if (ctx.elements.selectedMeta) {
          ctx.elements.selectedMeta.textContent = "Selecciona una mezcla para dosificar";
        }
        return;
      }

      const isGlobal = !Array.isArray(selectedRow);
      const getV = (key) => isGlobal ? (selectedRow[key] || "") : ctx.valueByKey(selectedRow, key);

      if (ctx.elements.selectedMeta) {
        ctx.elements.selectedMeta.textContent = `Formula: ${getV("formula") || "-"} | f'c: ${getV("fc") || "-"} | Edad: ${getV("edad") || "-"} | Tipo: ${getV("tipo") || "-"} | T.M.A.: ${getV("tma") || "-"} | Rev: ${getV("rev") || "-"} | Comp: ${getV("comp") || "-"}`;
      }

      const recipeItems = ctx.normalizeDoserRecipeItems(ctx.extractRecipe(selectedRow));
      const detailed = ctx.computeDoserDetailedLoads(recipeItems, dose, ctx.state.doser.params);

      let recipeTotal = 0;
      detailed.rows.forEach((item) => {
        let displayUnit = item.unit;
        if (["Reductor", "Retardante"].includes(item.name)) displayUnit = "Lts/m3";
        else if (["Fibra", "Imper"].includes(item.name)) displayUnit = "kg/m3";

        const qty = item.designA;
        recipeTotal += qty * ctx.componentWeightFactor({ unit: item.unit });
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${ctx.escapeHtml(item.name)}</td>
          <td>${ctx.escapeHtml(ctx.formatNum(qty))} <span class="recipe-inline-unit">${ctx.escapeHtml(displayUnit)}</span></td>
        `;
        if (ctx.elements.recipeBody) ctx.elements.recipeBody.appendChild(tr);
      });
      if (ctx.elements.recipeWeight) ctx.elements.recipeWeight.textContent = ctx.formatNum(recipeTotal);

      let theoreticalTotal = 0;
      detailed.rows.forEach((item) => {
        theoreticalTotal += item.trialLoad * ctx.componentWeightFactor({ unit: item.trialUnit || item.unit });
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${ctx.escapeHtml(item.name)}</td>
          <td>${ctx.escapeHtml(ctx.formatVol(item.designA))}</td>
          <td>${ctx.escapeHtml(ctx.formatVol(item.designSss))}</td>
          <td>${ctx.escapeHtml(ctx.formatVol(item.freeWater))}</td>
          <td>${ctx.escapeHtml(item.includeAbsVolume ? ctx.formatVol(item.absVolume) : "-")}</td>
          <td>${ctx.escapeHtml(ctx.formatVol(item.designReal))}</td>
          <td>${ctx.escapeHtml(ctx.formatVol(item.trialLoad))}</td>
          <td>${ctx.escapeHtml(item.trialUnit || item.unit)}</td>
          <td>${ctx.escapeHtml(item.note || "-")}</td>
        `;
        if (ctx.elements.theoreticalBody) ctx.elements.theoreticalBody.appendChild(tr);
      });
      if (ctx.elements.theoreticalWeight) {
        ctx.elements.theoreticalWeight.textContent = ctx.formatNum(theoreticalTotal);
      }
      if (ctx.elements.summary) {
        ctx.elements.summary.innerHTML = `${baseSummary} | Rel. A/C: ${ctx.formatNum(detailed.totals.relAc || 0)} | Vol. Abs. + Aire: ${ctx.formatNum(detailed.totals.absVolumeTotal || 0)}`;
      }

      let realTotal = 0;
      detailed.rows.forEach((item) => {
        if (typeof ctx.state.doser.realLoads[item.name] !== "number") {
          ctx.state.doser.realLoads[item.name] = item.trialLoad;
        }
        const real = ctx.state.doser.realLoads[item.name];
        realTotal += real * ctx.componentWeightFactor({ unit: item.trialUnit || item.unit });
        const diff = real - item.trialLoad;
        const tol = ctx.toleranceFor(item.name);
        const lim = item.trialLoad * (tol / 100);
        const ok = Math.abs(diff) <= lim;

        const alias = item.name;
        const options = (ctx.state.doser.invMaterials || []).filter((material) => material.doser_alias === alias);
        if (options.length === 1 && !ctx.state.doser.selectedMaterials[alias]) {
          ctx.state.doser.selectedMaterials[alias] = options[0].id;
        }
        const currentSelectedId = ctx.state.doser.selectedMaterials[alias];

        let materialSelectHtml = `<select class="doser-mat-select"><option value="">-- Sin Descontar --</option>`;
        options.forEach((material) => {
          const selected = Number(currentSelectedId) === material.id ? "selected" : "";
          materialSelectHtml += `<option value="${material.id}" ${selected}>${ctx.escapeHtml(material.name)}</option>`;
        });
        materialSelectHtml += "</select>";

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${ctx.escapeHtml(item.name)}</td>
          <td>${materialSelectHtml}</td>
          <td>${ctx.escapeHtml(ctx.formatNum(item.trialLoad))}</td>
          <td><input class="doser-real-input" type="number" min="0" step="0.01" value="${real.toFixed(2)}"></td>
          <td>${ctx.escapeHtml(`${diff >= 0 ? "+" : ""}${ctx.formatNum(diff)}`)}</td>
          <td class="${ok ? "status-ok" : "status-bad"}">${ctx.escapeHtml(ok ? "OK" : "FUERA")}</td>
        `;

        const input = tr.querySelector(".doser-real-input");
        let lastCommitted = ctx.toNumber(input.value);
        const commitRealValue = () => {
          const next = ctx.toNumber(input.value);
          if (next === lastCommitted) return;
          lastCommitted = next;
          ctx.state.doser.realLoads[item.name] = next;
          render();
        };
        input.addEventListener("change", commitRealValue);
        input.addEventListener("blur", commitRealValue);
        input.addEventListener("keydown", (event) => {
          if (event.key !== "Enter") return;
          event.preventDefault();
          commitRealValue();
          input.blur();
        });

        const select = tr.querySelector(".doser-mat-select");
        select.addEventListener("change", () => {
          ctx.state.doser.selectedMaterials[alias] = select.value ? Number(select.value) : null;
        });

        if (ctx.elements.realBody) ctx.elements.realBody.appendChild(tr);
      });
      if (ctx.elements.realWeight) ctx.elements.realWeight.textContent = ctx.formatNum(realTotal);
    }

    function rerender() {
      render();
    }

    function init() {
      if (initialized) return;
      initialized = true;
      on(ctx.elements.saveParamsBtn, "click", ctx.saveParams);
      [
        ctx.elements.doseM3Input,
        ctx.elements.tolCementoInput,
        ctx.elements.tolAgregadosInput,
        ctx.elements.tolAguaInput,
        ctx.elements.tolAditivoInput,
        ctx.elements.paramCementoPespInput,
        ctx.elements.paramAirePctInput,
        ctx.elements.paramPasa200PctInput,
        ctx.elements.paramPxlPctInput,
        ctx.elements.paramDensidadAggInput,
      ].forEach((element) => on(element, "input", rerender));
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
      rerender,
      computeTheoreticalLoads,
      render,
    };
  };
})();
