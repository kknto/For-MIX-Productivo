(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createConsultaCostsModule = function createConsultaCostsModule(ctx) {
    function syncQuoteModeButton() {
      const button = ctx.elements.toggleQuoteModeBtn;
      if (!button) return;
      button.textContent = ctx.state.quoteMode ? "Salir Cotizacion" : "Modo Cotizacion";
      button.classList.toggle("btn--active", ctx.state.quoteMode);
      button.classList.toggle("btn--muted", !ctx.state.quoteMode);
    }

    function getAggregateLabel(componentName) {
      if (!ctx.isAggregateComponent(componentName)) return "";
      const aggregateMap = ctx.buildAggregateColumnMap();
      const raw = (aggregateMap && aggregateMap[componentName]) || [];
      const details = [...new Set(raw.map((h) => ctx.splitHeaderName(h).name || h).map((s) => (s || "").trim()).filter(Boolean))];
      return details.length ? details.join(" + ") : "";
    }

    function effectiveQty(item) {
      if (ctx.state.quoteMode) {
        const override = ctx.state.quoteOverrides[item.name];
        if (override && typeof override.qty === "number") return override.qty;
      }
      return item.qty;
    }

    function effectivePV(componentName) {
      if (ctx.state.quoteMode) {
        const override = ctx.state.quoteOverrides[componentName];
        if (override && typeof override.pv === "number" && override.pv > 0) return override.pv;
      }
      return ctx.averagePV(componentName);
    }

    function volumeM3ForCost(item) {
      if (!ctx.isAggregateComponent(item.name)) return 0;
      const pv = ctx.isAggregateComponent(item.name)
        ? (ctx.averagePV(item.name) || ctx.densityFor(item.name, "kg"))
        : ctx.densityFor(item.name, item.unit);
      return pv > 0 ? item.qty / pv : 0;
    }

    function materialSubtotalForCost(item) {
      const unitCost = ctx.state.unitCosts[item.name] || 0;
      if (!ctx.isAggregateComponent(item.name)) return unitCost * item.qty;
      const m3 = volumeM3ForCost(item);
      return m3 * unitCost;
    }

    function haulSubtotalForCost(item) {
      if (!ctx.isAggregateComponent(item.name)) return 0;
      const haulCost = ctx.state.haulCosts[item.name] || 0;
      const m3 = volumeM3ForCost(item);
      return m3 * haulCost;
    }

    function subtotalForCost(item) {
      const unitCost = ctx.state.unitCosts[item.name] || 0;
      if (!ctx.isAggregateComponent(item.name)) return unitCost * item.qty;
      const haulCost = ctx.state.haulCosts[item.name] || 0;
      const m3 = volumeM3ForCost(item);
      return m3 * (unitCost + haulCost);
    }

    function updateCostTotals(recipeItems) {
      const haulTotal = recipeItems.reduce((acc, item) => acc + haulSubtotalForCost(item), 0);
      const materialTotal = recipeItems.reduce((acc, item) => acc + materialSubtotalForCost(item), 0);
      const total = materialTotal + haulTotal;
      if (ctx.elements.costHaulTotal) ctx.elements.costHaulTotal.textContent = ctx.formatMoney(haulTotal);
      if (ctx.elements.costMaterialTotal) ctx.elements.costMaterialTotal.textContent = ctx.formatMoney(materialTotal);
      ctx.elements.costTotal.textContent = ctx.formatMoney(total);
    }

    function renderCostTable(recipeItems) {
      const { costBody } = ctx.elements;
      costBody.innerHTML = "";
      recipeItems.forEach((item) => {
        const tr = document.createElement("tr");
        const isAgg = ctx.isAggregateComponent(item.name);
        const override = ctx.state.quoteMode ? (ctx.state.quoteOverrides[item.name] || {}) : {};
        const qty = effectiveQty(item);
        const unitCost = ctx.state.unitCosts[item.name] || 0;
        const haulCost = ctx.state.haulCosts[item.name] || 0;
        const pvValue = isAgg ? (effectivePV(item.name) || ctx.densityFor(item.name, "kg")) : ctx.densityFor(item.name, item.unit);
        const m3 = isAgg && pvValue > 0 ? qty / pvValue : 0;
        const subtotal = isAgg ? m3 * (unitCost + haulCost) : unitCost * qty;
        const materialLabel = isAgg ? (override.material || getAggregateLabel(item.name) || "-") : "-";
        const materialCell = ctx.state.quoteMode && isAgg
          ? `<input class="quote-input quote-material" type="text" value="${ctx.escapeHtml(materialLabel)}" placeholder="Nombre material">`
          : ctx.escapeHtml(materialLabel);
        const qtyCell = ctx.state.quoteMode
          ? `<input class="quote-input quote-qty" type="number" min="0" step="0.01" value="${qty.toFixed(2)}">`
          : ctx.escapeHtml(ctx.formatNum(qty));
        const pvDisplay = isAgg ? pvValue.toFixed(0) : "-";
        const pvCell = ctx.state.quoteMode && isAgg
          ? `<input class="quote-input quote-pv" type="number" min="0" step="1" value="${pvValue.toFixed(0)}" placeholder="PV">`
          : pvDisplay;
        const m3Text = isAgg ? ctx.formatVol(m3) : "-";
        const haulCell = isAgg
          ? `<div class="money-field"><span class="money-field__symbol">$</span><input class="haul-input" type="number" min="0" step="0.01" value="${haulCost.toFixed(2)}" title="Costo de transporte por m3 del agregado" aria-label="Acarreo por m3"></div>`
          : "-";

        tr.innerHTML = `
          <td>${ctx.escapeHtml(item.name)}</td>
          <td>${materialCell}</td>
          <td>${qtyCell}</td>
          <td class="num">${pvCell}</td>
          <td>${ctx.escapeHtml(m3Text)}</td>
          <td>${ctx.escapeHtml(item.unit)}</td>
          <td>${haulCell}</td>
          <td><div class="money-field"><span class="money-field__symbol">$</span><input class="cost-input" type="number" min="0" step="0.01" value="${unitCost.toFixed(2)}"></div></td>
          <td class="cost-sub">${ctx.escapeHtml(ctx.formatMoney(subtotal))}</td>
        `;

        const costInput = tr.querySelector(".cost-input");
        const haulInput = tr.querySelector(".haul-input");
        const subCell = tr.querySelector(".cost-sub");

        const recalcRow = () => {
          const currentQty = effectiveQty(item);
          const currentPv = isAgg ? (effectivePV(item.name) || ctx.densityFor(item.name, "kg")) : ctx.densityFor(item.name, item.unit);
          const currentUnitCost = ctx.state.unitCosts[item.name] || 0;
          const currentHaulCost = ctx.state.haulCosts[item.name] || 0;
          const currentM3 = isAgg && currentPv > 0 ? currentQty / currentPv : 0;
          const currentSubtotal = isAgg ? currentM3 * (currentUnitCost + currentHaulCost) : currentUnitCost * currentQty;
          const pvTd = tr.querySelector(".num");
          const m3Td = tr.children[4];
          if (pvTd && !ctx.state.quoteMode) pvTd.textContent = isAgg ? currentPv.toFixed(0) : "-";
          if (m3Td) m3Td.textContent = isAgg ? ctx.formatVol(currentM3) : "-";
          subCell.textContent = ctx.formatMoney(currentSubtotal);
          updateCostTotals(recipeItems);
        };

        costInput.addEventListener("input", () => {
          ctx.state.unitCosts[item.name] = ctx.toNumber(costInput.value);
          recalcRow();
        });

        if (haulInput) {
          haulInput.addEventListener("input", () => {
            ctx.state.haulCosts[item.name] = ctx.toNumber(haulInput.value);
            recalcRow();
          });
        } else {
          ctx.state.haulCosts[item.name] = 0;
        }

        if (ctx.state.quoteMode) {
          const materialInput = tr.querySelector(".quote-material");
          const qtyInput = tr.querySelector(".quote-qty");
          const pvInput = tr.querySelector(".quote-pv");
          if (materialInput) {
            materialInput.addEventListener("input", () => {
              if (!ctx.state.quoteOverrides[item.name]) ctx.state.quoteOverrides[item.name] = {};
              ctx.state.quoteOverrides[item.name].material = materialInput.value;
            });
          }
          if (qtyInput) {
            qtyInput.addEventListener("input", () => {
              if (!ctx.state.quoteOverrides[item.name]) ctx.state.quoteOverrides[item.name] = {};
              ctx.state.quoteOverrides[item.name].qty = ctx.toNumber(qtyInput.value);
              recalcRow();
            });
          }
          if (pvInput) {
            pvInput.addEventListener("input", () => {
              if (!ctx.state.quoteOverrides[item.name]) ctx.state.quoteOverrides[item.name] = {};
              ctx.state.quoteOverrides[item.name].pv = ctx.toNumber(pvInput.value);
              recalcRow();
            });
          }
        }

        costBody.appendChild(tr);
      });

      updateCostTotals(recipeItems);
    }

    function renderRecipeAndCosts(row) {
      const { recipeMeta, recipeBody, recipeWeight, costBody, costTotal } = ctx.elements;
      if (!row) {
        recipeMeta.textContent = "Selecciona una formula de la tabla de resultados.";
        recipeBody.innerHTML = "";
        recipeWeight.textContent = "0.00";
        costBody.innerHTML = "";
        if (ctx.elements.costHaulTotal) ctx.elements.costHaulTotal.textContent = "$0.00";
        if (ctx.elements.costMaterialTotal) ctx.elements.costMaterialTotal.textContent = "$0.00";
        costTotal.textContent = "$0.00";
        return;
      }

      const formula = ctx.valueByKey(row, "formula");
      const fc = ctx.valueByKey(row, "fc");
      const edad = ctx.valueByKey(row, "edad");
      const tipo = ctx.valueByKey(row, "tipo");
      const tma = ctx.valueByKey(row, "tma");
      const rev = ctx.valueByKey(row, "rev");
      const comp = ctx.valueByKey(row, "comp");
      const modDate = ctx.getRowModDate(row);
      const qcDate = ctx.state.qcUpdatedAt || "-";

      recipeMeta.textContent = `Formula: ${formula || "-"} | f'c: ${fc || "-"} | Edad: ${edad || "-"} | Tipo: ${tipo || "-"} | TMA: ${tma || "-"} | Rev: ${rev || "-"} | Comp: ${comp || "-"} | Fecha Modif: ${modDate || "-"} | QC: ${qcDate}`;

      const recipeItems = ctx.normalizeConsultaRecipeItems(ctx.extractRecipe(row));
      recipeBody.innerHTML = "";
      let totalWeight = 0;

      recipeItems.forEach((item) => {
        totalWeight += item.qty;
        const volText = ctx.isAggregateComponent(item.name) ? ctx.formatVol(item.volume) : "-";
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${ctx.escapeHtml(item.name)}</td>
          <td>${ctx.escapeHtml(ctx.formatNum(item.qty))}</td>
          <td>${ctx.escapeHtml(item.unit)}</td>
          <td>${ctx.escapeHtml(volText)}</td>
        `;
        recipeBody.appendChild(tr);
      });

      recipeWeight.textContent = ctx.formatNum(totalWeight);
      const adjustedForCost = ctx.adjustRecipeByQuality(recipeItems, 1);
      renderCostTable(adjustedForCost);
    }

    function toggleQuoteMode() {
      ctx.state.quoteMode = !ctx.state.quoteMode;
      if (!ctx.state.quoteMode) ctx.state.quoteOverrides = {};
      syncQuoteModeButton();
      const selectedIndex = ctx.state.selectedQueryRow;
      const row = typeof selectedIndex === "number" ? ctx.state.rows[selectedIndex] : null;
      if (row) {
        const recipeItems = ctx.normalizeConsultaRecipeItems(ctx.extractRecipe(row));
        const adjustedForCost = ctx.adjustRecipeByQuality(recipeItems, 1);
        renderCostTable(adjustedForCost);
      }
    }

    return {
      syncQuoteModeButton,
      effectiveQty,
      volumeM3ForCost,
      materialSubtotalForCost,
      haulSubtotalForCost,
      subtotalForCost,
      renderCostTable,
      renderRecipeAndCosts,
      toggleQuoteMode,
    };
  };
})();
