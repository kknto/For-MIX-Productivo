(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createConsultaReportModule = function createConsultaReportModule(ctx) {
    function buildCostRowsForReport(recipeItems) {
      return recipeItems.map((item) => {
        const isAgg = ctx.isAggregateComponent(item.name);
        const m3 = isAgg ? ctx.costsModule.volumeM3ForCost(item) : null;
        const unitCost = ctx.state.unitCosts[item.name] || 0;
        const haulCost = isAgg ? ctx.state.haulCosts[item.name] || 0 : 0;
        const subtotal = ctx.costsModule.subtotalForCost(item);
        return {
          name: item.name,
          qty: item.qty,
          m3,
          unit: item.unit,
          haul: isAgg ? haulCost : null,
          haulSubtotal: isAgg && m3 !== null ? m3 * haulCost : 0,
          unitCost,
          subtotal,
        };
      });
    }

    function exportReport() {
      const selectedIndex = ctx.state.selectedQueryRow;
      const row = typeof selectedIndex === "number" ? ctx.state.rows[selectedIndex] : null;
      if (!row) {
        ctx.setStatus("Selecciona una mezcla en Consulta Mix para exportar el reporte.", "warn");
        return;
      }

      const formula = ctx.valueByKey(row, "formula") || "-";
      const fc = ctx.valueByKey(row, "fc") || "-";
      const edad = ctx.valueByKey(row, "edad") || "-";
      const tipo = ctx.valueByKey(row, "tipo") || "-";
      const tma = ctx.valueByKey(row, "tma") || "-";
      const rev = ctx.valueByKey(row, "rev") || "-";
      const comp = ctx.valueByKey(row, "comp") || "-";
      const modDate = ctx.getRowModDate(row) || "-";
      const qcDate = ctx.state.qcUpdatedAt || "-";
      const reportDate = ctx.nowStamp();
      const recipeItems = ctx.normalizeConsultaRecipeItems(ctx.extractRecipe(row));
      const recipeTotal = recipeItems.reduce((acc, item) => acc + item.qty, 0);
      const adjustedForCost = ctx.adjustRecipeByQuality(recipeItems, 1);
      const costRows = buildCostRowsForReport(adjustedForCost);
      const totalMaterials = adjustedForCost.reduce((acc, item) => acc + ctx.costsModule.materialSubtotalForCost(item), 0);
      const totalHaul = costRows.reduce((acc, item) => acc + (item.haulSubtotal || 0), 0);
      const totalCost = totalMaterials + totalHaul;
      const aggregateMap = ctx.buildAggregateColumnMap();

      const recipeRowsHtml = recipeItems.map((item) => {
        const componentLabel = ctx.reportComponentLabel(item.name, aggregateMap);
        const volText = ctx.isAggregateComponent(item.name) ? ctx.formatVol(item.volume) : "-";
        return `
        <tr>
          <td>${ctx.escapeHtml(componentLabel)}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.qty))}</td>
          <td>${ctx.escapeHtml(item.unit)}</td>
          <td class="num">${ctx.escapeHtml(volText)}</td>
        </tr>
      `;
      }).join("");

      const costRowsHtml = costRows.map((item) => {
        const componentLabel = ctx.reportComponentLabel(item.name, aggregateMap);
        const m3Text = item.m3 === null ? "-" : ctx.formatVol(item.m3);
        return `
        <tr>
          <td>${ctx.escapeHtml(componentLabel)}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.qty))}</td>
          <td class="num">${ctx.escapeHtml(m3Text)}</td>
          <td>${ctx.escapeHtml(item.unit)}</td>
          <td class="num">${item.haul === null ? "-" : ctx.escapeHtml(ctx.formatNum(item.haul))}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.unitCost))}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatMoney(item.subtotal))}</td>
        </tr>
      `;
      }).join("");

      const html = `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Reporte Mix - ${ctx.escapeHtml(formula)}</title>
  <style>
    @page { size: letter landscape; margin: 8mm; }
    body { font-family: "Segoe UI", Tahoma, Arial, sans-serif; margin: 0; color: #1a2c3f; font-size: 11px; }
    .page { min-height: 100%; }
    .head { border-bottom: 2px solid #0b4f8a; padding-bottom: 6px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
    .head-brand { display: inline-flex; align-items: center; gap: 8px; }
    .head-logo { width: 46px; height: 46px; object-fit: contain; border: 1px solid #d5e1ee; border-radius: 8px; background: #fff; padding: 4px; }
    .head h1 { margin: 0; font-size: 18px; line-height: 1.1; }
    .head .brand { margin: 3px 0 0; color: #3b5572; font-size: 10.5px; font-weight: 600; }
    .head .head-meta { margin: 0; color: #3b5572; font-size: 11px; text-align: right; }
    .meta { display: grid; grid-template-columns: repeat(5, minmax(95px, 1fr)); gap: 5px; margin-bottom: 8px; }
    .meta .item { border: 1px solid #d6e0eb; border-radius: 6px; padding: 5px 6px; background: #f8fbff; }
    .meta .k { font-size: 9px; color: #4d667f; text-transform: uppercase; line-height: 1; }
    .meta .v { font-size: 11px; font-weight: 700; margin-top: 2px; line-height: 1.2; }
    .main-grid { display: grid; grid-template-columns: 36% 64%; gap: 8px; align-items: start; }
    .section { margin-top: 0; }
    .section h2 { margin: 0 0 6px; font-size: 13px; color: #0d3762; line-height: 1.1; }
    table { width: 100%; border-collapse: collapse; margin-top: 0; table-layout: fixed; }
    th, td { border: 1px solid #dce5ef; padding: 4px 5px; font-size: 10px; line-height: 1.2; }
    th { background: #edf4fb; text-align: left; }
    td.num { text-align: right; }
    .cost-table th:nth-child(1), .cost-table td:nth-child(1) { width: 22%; }
    .cost-table th:nth-child(2), .cost-table td:nth-child(2) { width: 13%; }
    .cost-table th:nth-child(3), .cost-table td:nth-child(3) { width: 10%; }
    .cost-table th:nth-child(4), .cost-table td:nth-child(4) { width: 10%; }
    .cost-table th:nth-child(5), .cost-table td:nth-child(5) { width: 12%; }
    .cost-table th:nth-child(6), .cost-table td:nth-child(6) { width: 14%; }
    .cost-table th:nth-child(7), .cost-table td:nth-child(7) { width: 19%; }
    .totals { margin-top: 6px; text-align: right; font-size: 13px; font-weight: 800; color: #123b66; }
    .totals-sub { margin-top: 4px; text-align: right; font-size: 12px; font-weight: 700; color: #1f4e7b; }
    .sign { margin-top: 10px; border-top: 1px solid #d3dfec; padding-top: 6px; text-align: center; color: #264767; font-weight: 700; font-size: 11px; }
    @media print {
      html, body { width: 100%; height: 100%; }
      * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .page { break-inside: avoid; }
      .section { break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="head">
      <div class="head-brand">
        <img class="head-logo" src="${ctx.escapeHtml(ctx.brandLogoUrl)}" alt="${ctx.escapeHtml(ctx.brandName || "ForMIX")}">
        <div>
          <h1>Reporte de Consulta Mix</h1>
          <p class="brand">${ctx.escapeHtml(ctx.brandName || "ForMIX")}</p>
        </div>
      </div>
      <p class="head-meta">Generado: ${ctx.escapeHtml(reportDate)} | Archivo: ${ctx.escapeHtml(ctx.state.file || "-")}</p>
    </div>

    <div class="meta">
      <div class="item"><div class="k">Formula</div><div class="v">${ctx.escapeHtml(formula)}</div></div>
      <div class="item"><div class="k">f'c</div><div class="v">${ctx.escapeHtml(fc)}</div></div>
      <div class="item"><div class="k">Edad</div><div class="v">${ctx.escapeHtml(edad)}</div></div>
      <div class="item"><div class="k">Tipo</div><div class="v">${ctx.escapeHtml(tipo)}</div></div>
      <div class="item"><div class="k">TMA</div><div class="v">${ctx.escapeHtml(tma)}</div></div>
      <div class="item"><div class="k">Rev</div><div class="v">${ctx.escapeHtml(rev)}</div></div>
      <div class="item"><div class="k">Comp</div><div class="v">${ctx.escapeHtml(comp)}</div></div>
      <div class="item"><div class="k">Fecha Modif</div><div class="v">${ctx.escapeHtml(modDate)}</div></div>
      <div class="item"><div class="k">QC</div><div class="v">${ctx.escapeHtml(qcDate)}</div></div>
      <div class="item"><div class="k">Sub-Total Acarreo m3</div><div class="v">${ctx.escapeHtml(ctx.formatMoney(totalHaul))}</div></div>
      <div class="item"><div class="k">Sub-Total Materiales m3</div><div class="v">${ctx.escapeHtml(ctx.formatMoney(totalMaterials))}</div></div>
      <div class="item"><div class="k">Total por m3</div><div class="v">${ctx.escapeHtml(ctx.formatMoney(totalCost))}</div></div>
    </div>

    <section class="main-grid">
      <article class="section">
        <h2>Receta</h2>
        <table>
          <thead>
            <tr>
              <th>Componente</th>
              <th>Cantidad</th>
              <th>Unidad</th>
              <th>Vol. Est. m3</th>
            </tr>
          </thead>
          <tbody>${recipeRowsHtml}</tbody>
        </table>
        <div class="totals">Peso por m3: ${ctx.escapeHtml(ctx.formatNum(recipeTotal))}</div>
      </article>

      <article class="section">
        <h2>Costos por m3</h2>
        <table class="cost-table">
          <thead>
            <tr>
              <th>Componente</th>
              <th>Cant. Final</th>
              <th>m3</th>
              <th>U.M.</th>
              <th>Acarreo ($)</th>
              <th>Costo Unit. ($)</th>
              <th>Subtotal</th>
            </tr>
          </thead>
          <tbody>${costRowsHtml}</tbody>
        </table>
        <div class="totals-sub">Sub-Total acarreo m3: ${ctx.escapeHtml(ctx.formatMoney(totalHaul))}</div>
        <div class="totals-sub">Sub-Total materiales m3: ${ctx.escapeHtml(ctx.formatMoney(totalMaterials))}</div>
        <div class="totals">Total por m3: ${ctx.escapeHtml(ctx.formatMoney(totalCost))}</div>
      </article>
    </section>

    <div class="sign">${ctx.escapeHtml(ctx.brandTagline || "ForMIX Pilot")} - Disena-Dosifica-Calcula</div>
  </div>
</body>
</html>`;

      const win = window.open("", "_blank");
      if (!win) {
        ctx.setStatus("El navegador bloqueo la ventana del reporte. Habilita pop-ups e intenta de nuevo.", "warn");
        return;
      }
      win.document.open();
      win.document.write(html);
      win.document.close();
      ctx.setStatus("Reporte generado. Usa Imprimir para guardarlo en PDF.", "ok");
    }

    return {
      exportReport,
    };
  };
})();
