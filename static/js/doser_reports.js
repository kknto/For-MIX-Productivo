(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createDoserReportsModule = function createDoserReportsModule(ctx) {
    let initialized = false;
    const disposers = [];

    function on(element, eventName, handler) {
      if (!element) return;
      element.addEventListener(eventName, handler);
      disposers.push(() => element.removeEventListener(eventName, handler));
    }

    function normalizeRemisionInput() {
      if (!ctx.elements.remisionNoInput) return;
      ctx.elements.remisionNoInput.value = ctx.elements.remisionNoInput.value.toUpperCase();
    }

    function readRemisionDate() {
      return ((ctx.elements.remisionDateInput?.value || "").toString().trim());
    }

    function buildReportSnapshot() {
      ctx.state.doser.tolerances.cemento = ctx.toNumber(ctx.elements.tolCementoInput.value || "1");
      ctx.state.doser.tolerances.agregados = ctx.toNumber(ctx.elements.tolAgregadosInput.value || "3");
      ctx.state.doser.tolerances.agua = ctx.toNumber(ctx.elements.tolAguaInput.value || "2");
      ctx.state.doser.tolerances.aditivo = ctx.toNumber(ctx.elements.tolAditivoInput.value || "1");
      const dose = Math.max(0, ctx.toNumber(ctx.elements.doseM3Input.value));
      ctx.state.doser.params = ctx.readParamsFromInputs();
      ctx.state.doser.dosageM3 = dose;

      const entry = ctx.state.doser.selectedEntry;
      const selectedRow = entry ? entry.row : null;
      if (!selectedRow) return null;

      const isGlobal = !Array.isArray(selectedRow);
      const getV = (key) => isGlobal ? (selectedRow[key] || "") : ctx.valueByKey(selectedRow, key);

      const recipeItems = ctx.normalizeDoserRecipeItems(ctx.extractRecipe(selectedRow));
      const detailed = ctx.computeDoserDetailedLoads(recipeItems, dose, ctx.state.doser.params);
      const recipe = detailed.rows.map((row) => {
        let displayUnit = row.unit;
        if (["Reductor", "Retardante"].includes(row.name)) displayUnit = "Lts/m3";
        else if (["Fibra", "Imper"].includes(row.name)) displayUnit = "kg/m3";
        return { name: row.name, qty: row.designA, unit: displayUnit };
      });
      const recipeWeight = recipe.reduce((acc, item) => acc + (item.qty * ctx.componentWeightFactor(item)), 0);
      const theoretical = detailed.rows.map((row) => ({
        name: row.name,
        unit: row.trialUnit || row.unit,
        qty: row.trialLoad,
      }));
      const theoreticalWeight = detailed.totals.theoreticalWeight;

      let realWeight = 0;
      const realRows = theoretical.map((item) => {
        if (typeof ctx.state.doser.realLoads[item.name] !== "number") {
          ctx.state.doser.realLoads[item.name] = item.qty;
        }
        const real = ctx.toNumber(ctx.state.doser.realLoads[item.name]);
        const diff = real - item.qty;
        const tol = ctx.toleranceFor(item.name);
        const lim = item.qty * (tol / 100);
        const ok = Math.abs(diff) <= lim;
        realWeight += real * ctx.componentWeightFactor(item);
        return {
          name: item.name,
          material_id: ctx.state.doser.selectedMaterials[item.name] || null,
          material_name: ctx.state.doser.selectedMaterials[item.name]
            ? ((ctx.state.doser.invMaterials || []).find((m) => String(m.id) === String(ctx.state.doser.selectedMaterials[item.name]))?.name || "-- Sin descontar --")
            : "-- Sin descontar --",
          unit: item.unit,
          theoretical: item.qty,
          real,
          diff,
          status: ok ? "OK" : "FUERA",
          tolerance: tol,
        };
      });

      const formula = getV("formula") || "-";
      const fc = getV("fc") || "-";
      const tipo = getV("cod") || "-";
      const coloc = getV("tipo") || "-";
      const tma = getV("tma") || "-";
      const rev = getV("rev") || "-";
      const comp = getV("comp") || "-";
      const modDate = (isGlobal ? selectedRow._updated : ctx.getRowModDate(selectedRow)) || "-";
      const remisionNo = ((ctx.elements.remisionNoInput?.value || "").toString().trim().toUpperCase()) || "-";
      const cliente = ((ctx.elements.clienteInput?.value || "").toString().trim().toUpperCase()) || "-";
      const ubicacion = ((ctx.elements.ubicacionInput?.value || "").toString().trim().toUpperCase()) || "-";

      return {
        remisionNo,
        cliente,
        ubicacion,
        file: ctx.state.file || "",
        qcUpdatedAt: ctx.state.qcUpdatedAt || "",
        formula,
        fc,
        tipo,
        coloc,
        tma,
        rev,
        comp,
        modDate,
        recipe,
        recipeWeight,
        theoretical,
        theoreticalWeight,
        theoreticalDetailed: detailed.rows,
        calcTotals: detailed.totals,
        realRows,
        realWeight,
        dose,
        qc: ctx.state.doser.quality,
        doserParams: ctx.state.doser.params,
        tolerances: { ...ctx.state.doser.tolerances },
      };
    }

    function normalizeReportSnapshot(raw, fallback = {}) {
      const snap = raw && typeof raw === "object" ? raw : {};
      const defaultTol = { cemento: 0, agregados: 0, agua: 0, aditivo: 0 };
      const tolerances = snap.tolerances && typeof snap.tolerances === "object" ? snap.tolerances : defaultTol;
      const qcValues = snap.qc && typeof snap.qc === "object" ? snap.qc : ctx.createDefaultQuality();

      return {
        remisionNo: (snap.remisionNo || snap.remision_no || fallback.remisionNo || "-").toString(),
        file: snap.file || fallback.file || "-",
        qcUpdatedAt: snap.qcUpdatedAt || fallback.qcUpdatedAt || "-",
        formula: snap.formula || "-",
        cliente: snap.cliente || "-",
        ubicacion: snap.ubicacion || "-",
        fc: snap.fc || "-",
        tipo: snap.tipo || "-",
        coloc: snap.coloc || "-",
        tma: snap.tma || "-",
        rev: snap.rev || "-",
        comp: snap.comp || "-",
        modDate: snap.modDate || "-",
        dose: ctx.toNumber(snap.dose || snap.dosificacion_m3 || 0),
        recipe: Array.isArray(snap.recipe) ? snap.recipe : [],
        recipeWeight: ctx.toNumber(snap.recipeWeight || snap.peso_receta || 0),
        theoretical: Array.isArray(snap.theoretical) ? snap.theoretical : [],
        theoreticalDetailed: Array.isArray(snap.theoreticalDetailed) ? snap.theoreticalDetailed : [],
        calcTotals: snap.calcTotals && typeof snap.calcTotals === "object" ? snap.calcTotals : {},
        theoreticalWeight: ctx.toNumber(snap.theoreticalWeight || snap.peso_teorico_total || 0),
        realRows: Array.isArray(snap.realRows) ? snap.realRows : [],
        realWeight: ctx.toNumber(snap.realWeight || snap.peso_real_total || 0),
        doserParams: ctx.normalizeDoserParams(snap.doserParams),
        tolerances: {
          cemento: ctx.toNumber(tolerances.cemento || 0),
          agregados: ctx.toNumber(tolerances.agregados || 0),
          agua: ctx.toNumber(tolerances.agua || 0),
          aditivo: ctx.toNumber(tolerances.aditivo || 0),
        },
        qc: qcValues,
      };
    }

    function buildReportHtml(rawSnapshot, reportDate) {
      const snap = normalizeReportSnapshot(rawSnapshot, {
        file: ctx.state.file || "-",
        qcUpdatedAt: ctx.state.qcUpdatedAt || "-",
      });

      const qcRowsHtml = ctx.qcAggregates.map((agg) => {
        const q = snap.qc[agg] || {};
        return `
      <tr>
        <td>${ctx.escapeHtml(agg)}</td>
        <td class="num">${ctx.escapeHtml(ctx.formatNum(q.pvs || 0))}</td>
        <td class="num">${ctx.escapeHtml(ctx.formatNum(q.pvc || 0))}</td>
        <td class="num">${ctx.escapeHtml(ctx.formatNum(q.densidad || 0))}</td>
        <td class="num">${ctx.escapeHtml(ctx.formatNum(q.absorcion || 0))}</td>
        <td class="num">${ctx.escapeHtml(ctx.formatNum(q.humedad || 0))}</td>
      </tr>
    `;
      }).join("");

      const tolRowsHtml = `
    <tr><td>Cemento</td><td class="num">${ctx.escapeHtml(ctx.formatNum(snap.tolerances.cemento))}%</td></tr>
    <tr><td>Agregados</td><td class="num">${ctx.escapeHtml(ctx.formatNum(snap.tolerances.agregados))}%</td></tr>
    <tr><td>Agua</td><td class="num">${ctx.escapeHtml(ctx.formatNum(snap.tolerances.agua))}%</td></tr>
    <tr><td>Aditivo</td><td class="num">${ctx.escapeHtml(ctx.formatNum(snap.tolerances.aditivo))}%</td></tr>
  `;

      const paramsRowsHtml = `
    <tr><td>Peso esp. cemento</td><td class="num">${ctx.escapeHtml(ctx.formatNum(snap.doserParams.cemento_pesp || 0))}</td></tr>
    <tr><td>Aire (%)</td><td class="num">${ctx.escapeHtml(ctx.formatNum(snap.doserParams.aire_pct || 0))}</td></tr>
    <tr><td>Pasa malla 200 (%)</td><td class="num">${ctx.escapeHtml(ctx.formatNum(snap.doserParams.pasa_malla_200_pct || 0))}</td></tr>
    <tr><td>PxL pond. (%)</td><td class="num">${ctx.escapeHtml(ctx.formatNum(snap.doserParams.pxl_pond_pct || 0))}</td></tr>
    <tr><td>Densidad agg fallback</td><td class="num">${ctx.escapeHtml(ctx.formatNum(snap.doserParams.densidad_agregado_fallback || 0))}</td></tr>
  `;

      const recipeRowsHtml = snap.recipe.map((item) => `
        <tr>
          <td>${ctx.escapeHtml(item.name)}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.qty))}</td>
          <td>${ctx.escapeHtml(item.unit)}</td>
        </tr>
      `).join("");

      const theoreticalDetailedRowsHtml = (snap.theoreticalDetailed || []).map((item) => `
        <tr>
          <td>${ctx.escapeHtml(item.name)}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.designA || 0))}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.designSss || 0))}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.freeWater || 0))}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.absVolume || 0))}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.designReal || 0))}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.trialLoad || 0))}</td>
          <td>${ctx.escapeHtml(item.trialUnit || item.unit || "-")}</td>
          <td>${ctx.escapeHtml(item.note || "-")}</td>
        </tr>
      `).join("");

      const theoreticalRowsHtml = theoreticalDetailedRowsHtml || snap.theoretical.map((item) => `
        <tr>
          <td>${ctx.escapeHtml(item.name)}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.qty || 0))}</td>
          <td class="num">-</td>
          <td class="num">-</td>
          <td class="num">-</td>
          <td class="num">-</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.qty || 0))}</td>
          <td>${ctx.escapeHtml(item.unit || "-")}</td>
          <td>-</td>
        </tr>
      `).join("");

      const realRowsHtml = snap.realRows.map((item) => `
        <tr>
          <td>${ctx.escapeHtml(item.name)}</td>
          <td>${ctx.escapeHtml(item.material_name || "-- Sin descontar --")}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.theoretical))}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.real))}</td>
          <td class="num">${item.diff >= 0 ? "+" : ""}${ctx.escapeHtml(ctx.formatNum(item.diff))}</td>
          <td class="num">${ctx.escapeHtml(ctx.formatNum(item.tolerance))}%</td>
          <td class="${item.status === "OK" ? "ok" : "bad"}">${ctx.escapeHtml(item.status)}</td>
        </tr>
      `).join("");

      return `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Reporte Dosificador - ${ctx.escapeHtml(snap.formula)}</title>
  <style>
    @page { size: A4 landscape; margin: 0; }
    html, body { width: 297mm; height: 210mm; }
    * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    body { font-family: "Segoe UI", Tahoma, Arial, sans-serif; margin: 0; color: #1a2c3f; font-size: 11px; line-height: 1.2; }
    .sheet { width: 100%; min-height: 100%; padding: 3mm 4mm; }
    .head { border-bottom: 1px solid #0b4f8a; margin-bottom: 6px; padding-bottom: 4px; display: flex; justify-content: space-between; align-items: center; gap: 10px; }
    .head-brand { display: inline-flex; align-items: center; gap: 8px; }
    .head-logo { width: 44px; height: 44px; object-fit: contain; border: 1px solid #d5e1ee; border-radius: 8px; background: #fff; padding: 4px; }
    .head h1 { margin: 0; font-size: 16px; color: #0d3762; }
    .head .brand { margin: 2px 0 0; color: #39546e; font-size: 10px; font-weight: 600; }
    .head .sub { margin: 0; color: #39546e; font-size: 10.5px; text-align: right; }
    .meta-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 6px; }
    .meta-table th, .meta-table td { border: 1px solid #dce5ef; padding: 3px 5px; }
    .meta-table th { background: #edf4fb; text-align: left; width: 9%; font-weight: 600; }
    .meta-table td { width: 16%; font-weight: 600; color: #153958; }
    .grid-2 { display: grid; grid-template-columns: 1.45fr 1fr; gap: 6px; margin-bottom: 6px; }
    .grid-2.equal { grid-template-columns: 1fr 1fr; }
    .panel { border: 1px solid #dce5ef; border-radius: 6px; padding: 4px; break-inside: avoid; }
    .panel h2 { margin: 0 0 4px; font-size: 12px; color: #0d3762; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th, td { border: 1px solid #dce5ef; padding: 3px 5px; vertical-align: middle; }
    th { background: #edf4fb; text-align: left; font-size: 10.5px; font-weight: 700; }
    td { font-size: 10.5px; }
    td.num, th.num { text-align: right; }
    .total-line { margin-top: 3px; padding-top: 3px; border-top: 1px dashed #ccd8e6; text-align: right; font-weight: 700; color: #123b66; }
    .ok { color: #1f7a42; font-weight: 700; }
    .bad { color: #b9362d; font-weight: 700; }
    .sign { margin-top: 8px; border-top: 1px solid #d3dfec; padding-top: 5px; text-align: center; color: #264767; font-weight: 600; font-size: 10.5px; }
    .nowrap { white-space: nowrap; }
    @media print {
      html, body { margin: 0 !important; padding: 0 !important; }
      .sheet { break-inside: avoid; page-break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="sheet">
    <div class="head">
      <div class="head-brand">
        <img class="head-logo" src="${ctx.escapeHtml(ctx.brandLogoUrl)}" alt="${ctx.escapeHtml(ctx.brandName || "ForMIX")}">
        <div>
          <h1>Reporte de Dosificador</h1>
          <p class="brand">${ctx.escapeHtml(ctx.brandName || "ForMIX")}</p>
        </div>
      </div>
      <p class="sub">Generado: ${ctx.escapeHtml(reportDate)} | Archivo: ${ctx.escapeHtml(snap.file)}</p>
    </div>

    <table class="meta-table">
      <tbody>
        <tr>
          <th>Remision</th><td>${ctx.escapeHtml(snap.remisionNo)}</td>
          <th>Cliente</th><td>${ctx.escapeHtml(snap.cliente)}</td>
          <th>Ubicacion</th><td>${ctx.escapeHtml(snap.ubicacion)}</td>
          <th>Formula</th><td>${ctx.escapeHtml(snap.formula)}</td>
        </tr>
        <tr>
          <th>f'c</th><td>${ctx.escapeHtml(snap.fc)}</td>
          <th>Tipo</th><td>${ctx.escapeHtml(snap.tipo)}</td>
          <th>Colocacion</th><td>${ctx.escapeHtml(snap.coloc)}</td>
          <th>T.M.A.</th><td>${ctx.escapeHtml(snap.tma)}</td>
          <th>Rev</th><td>${ctx.escapeHtml(snap.rev)}</td>
          <th>Comp</th><td>${ctx.escapeHtml(snap.comp)}</td>
        </tr>
        <tr>
          <th>Fecha Modif</th><td>${ctx.escapeHtml(snap.modDate)}</td>
          <th>Dosificacion</th><td class="nowrap">${ctx.escapeHtml(ctx.formatNum(snap.dose))} m<sup>3</sup></td>
          <th>QC</th><td>${ctx.escapeHtml(snap.qcUpdatedAt)}</td>
          <th></th><td></td>
        </tr>
      </tbody>
    </table>

    <div class="grid-2">
      <section class="panel">
        <h2>Datos de Control de Calidad</h2>
        <table>
          <thead>
            <tr>
              <th style="width:22%;">Agregado</th>
              <th class="num" style="width:15%;">PVS</th>
              <th class="num" style="width:15%;">PVC</th>
              <th class="num" style="width:16%;">Densidad</th>
              <th class="num" style="width:16%;">Absorcion</th>
              <th class="num" style="width:16%;">Humedad</th>
            </tr>
          </thead>
          <tbody>${qcRowsHtml}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>Tolerancias de Carga</h2>
        <table>
          <thead><tr><th>Material</th><th class="num">Tolerancia</th></tr></thead>
          <tbody>${tolRowsHtml}</tbody>
        </table>
        <h2 style="margin-top:6px;">Parametros de Calculo</h2>
        <table>
          <thead><tr><th>Parametro</th><th class="num">Valor</th></tr></thead>
          <tbody>${paramsRowsHtml}</tbody>
        </table>
      </section>
    </div>

    <div class="grid-2 equal">
      <section class="panel">
        <h2>Receta</h2>
        <table>
          <thead><tr><th style="width:50%;">Componente</th><th class="num" style="width:30%;">Cantidad</th><th style="width:20%;">Unidad</th></tr></thead>
          <tbody>${recipeRowsHtml}</tbody>
        </table>
        <div class="total-line">Peso aprox por m<sup>3</sup>: ${ctx.escapeHtml(ctx.formatNum(snap.recipeWeight))}</div>
      </section>
      <section class="panel">
        <h2>Carga Teorica Detallada</h2>
        <table>
          <thead>
            <tr>
              <th style="width:17%;">Componente</th>
              <th class="num" style="width:9%;">Diseño A</th>
              <th class="num" style="width:9%;">Diseño SSS</th>
              <th class="num" style="width:10%;">Agua libre H.R.</th>
              <th class="num" style="width:9%;">Vol. Abs.</th>
              <th class="num" style="width:9%;">Diseño H.R.</th>
              <th class="num" style="width:10%;">Mezcla Prueba</th>
              <th style="width:8%;">U.M.</th>
              <th style="width:19%;">Obs.</th>
            </tr>
          </thead>
          <tbody>${theoreticalRowsHtml}</tbody>
        </table>
        <div class="total-line">Peso teorico total: ${ctx.escapeHtml(ctx.formatNum(snap.theoreticalWeight))}</div>
        <div class="total-line">Rel. A/C: ${ctx.escapeHtml(ctx.formatNum(ctx.toNumber(snap.calcTotals.relAc || 0)))} | Vol. Abs. + Aire: ${ctx.escapeHtml(ctx.formatNum(ctx.toNumber(snap.calcTotals.absVolumeTotal || 0)))}</div>
      </section>
    </div>

    <section class="panel">
      <h2>Carga Real y Diferencial</h2>
      <table>
        <thead>
          <tr>
            <th style="width:18%;">Componente</th>
            <th style="width:20%;">Material</th>
            <th class="num" style="width:14%;">Teorica</th>
            <th class="num" style="width:14%;">Real</th>
            <th class="num" style="width:12%;">Diferencia</th>
            <th class="num" style="width:10%;">Tol. %</th>
            <th style="width:12%;">Estatus</th>
          </tr>
        </thead>
        <tbody>${realRowsHtml}</tbody>
      </table>
      <div class="total-line">Peso real total: ${ctx.escapeHtml(ctx.formatNum(snap.realWeight))}</div>
    </section>

    <div class="sign">${ctx.escapeHtml(ctx.brandTagline || "ForMIX Pilot")} - Disena-Dosifica-Calcula</div>
  </div>
</body>
</html>`;
    }

    function openReportWindow(html, successMessage) {
      const win = window.open("", "_blank");
      if (!win) {
        ctx.setStatus("El navegador bloqueo la ventana del reporte. Habilita pop-ups e intenta de nuevo.", "warn");
        return false;
      }
      win.document.open();
      win.document.write(html);
      win.document.close();
      if (successMessage) ctx.setStatus(successMessage, "ok");
      return true;
    }

    function exportReport() {
      const snap = buildReportSnapshot();
      if (!snap) {
        ctx.setStatus("Selecciona una mezcla en Dosificador para exportar el reporte.", "warn");
        return;
      }
      const html = buildReportHtml(snap, ctx.nowStamp());
      openReportWindow(html, "Reporte de dosificador generado. Usa Imprimir para guardarlo en PDF.");
    }

    async function openRemisionReport(remisionId) {
      try {
        const id = Number(remisionId);
        if (!Number.isFinite(id) || id <= 0) return ctx.setStatus("ID invalido.", "warn");
        const response = await ctx.apiFetch(`/api/remisiones/${encodeURIComponent(id)}`);
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo cargar la remision.");
        }
        const snap = payload.snapshot && typeof payload.snapshot === "object" ? payload.snapshot : null;
        if (!snap) throw new Error("La remision no tiene snapshot de reporte.");
        const remisionNo = snap.remisionNo || snap.remision_no || payload.remision_no || "-";
        const normalized = normalizeReportSnapshot(snap, {
          remisionNo,
          file: payload.file || ctx.state.file || "-",
          qcUpdatedAt: ctx.state.qcUpdatedAt || "-",
        });
        const html = buildReportHtml(normalized, ctx.nowStamp());
        openReportWindow(html);
        ctx.setStatus(`Reporte de remision ${remisionNo} generado. Usa Imprimir para guardarlo en PDF.`, "ok");
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    function renderRemisionList() {
      if (!ctx.elements.doserRemisionBody) return;
      ctx.elements.doserRemisionBody.innerHTML = "";
      const items = Array.isArray(ctx.state.doser.remisiones) ? ctx.state.doser.remisiones : [];
      if (!items.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="11">Sin remisiones guardadas para esta fecha.</td>`;
        ctx.elements.doserRemisionBody.appendChild(tr);
        if (ctx.elements.remisionMeta) ctx.elements.remisionMeta.textContent = "Remisiones: 0";
        return;
      }

      items.forEach((item) => {
        const snap = item.snapshot || {};
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${ctx.escapeHtml(item.remision_no || "-")}</td>
          <td><span class="remision-cell remision-cell--formula" title="${ctx.escapeHtml(item.formula || "-")}">${ctx.escapeHtml(item.formula || "-")}</span></td>
          <td>${ctx.escapeHtml(item.fc || "-")}</td>
          <td>${ctx.escapeHtml(item.tma || "-")}</td>
          <td>${ctx.formatNum(item.dosificacion_m3 || 0)}</td>
          <td><span class="remision-cell remision-cell--client" title="${ctx.escapeHtml(snap.cliente || "-")}">${ctx.escapeHtml(snap.cliente || "-")}</span></td>
          <td><span class="remision-cell remision-cell--location" title="${ctx.escapeHtml(snap.ubicacion || "-")}">${ctx.escapeHtml(snap.ubicacion || "-")}</span></td>
          <td>${ctx.formatNum(item.peso_real_total || 0)}</td>
          <td><span class="remision-cell remision-cell--date" title="${ctx.escapeHtml(item.created_at || "-")}">${ctx.escapeHtml(item.created_at || "-")}</span></td>
          <td class="remision-actions" title="Archivo: ${ctx.escapeHtml(item.source_file || "-")} | Usuario: ${ctx.escapeHtml(item.created_by || "-")}">
            <button type="button" class="btn btn--secondary btn--small remision-report-btn">Reporte</button>
            ${ctx.state.auth.role === "administrador" ? '<button type="button" class="btn btn--muted btn--small remision-edit-btn">Editar</button>' : ""}
            <button type="button" class="btn btn--danger btn--small remision-delete-btn">Eliminar</button>
          </td>
        `;
        const reportBtn = tr.querySelector(".remision-report-btn");
        if (reportBtn) reportBtn.addEventListener("click", () => openRemisionReport(item.id));
        const deleteBtn = tr.querySelector(".remision-delete-btn");
        if (deleteBtn) deleteBtn.addEventListener("click", () => deleteRemision(item.id, item.remision_no));
        const editBtn = tr.querySelector(".remision-edit-btn");
        if (editBtn) editBtn.addEventListener("click", () => {
          if (typeof window.openEditRemisionModal === "function") window.openEditRemisionModal(item);
        });
        ctx.elements.doserRemisionBody.appendChild(tr);
      });

      if (ctx.elements.remisionMeta) ctx.elements.remisionMeta.textContent = `Remisiones: ${items.length}`;
    }

    async function loadRemisiones() {
      if (!ctx.canAccessView("dosificador")) return;
      const filterDate = (ctx.elements.remisionFilterDate && ctx.elements.remisionFilterDate.value) ? ctx.elements.remisionFilterDate.value : "";
      try {
        if (ctx.elements.remisionMeta) ctx.elements.remisionMeta.textContent = "Cargando remisiones...";
        const url = `/api/remisiones?limit=150${filterDate ? `&date=${filterDate}` : ""}`;
        const response = await ctx.apiFetch(url);
        const payload = await response.json();
        if (!response.ok || !payload.ok) throw new Error(payload.error || "No se pudo cargar remisiones.");
        ctx.state.doser.remisiones = Array.isArray(payload.items) ? payload.items : [];
      } catch (error) {
        ctx.state.doser.remisiones = [];
        console.error("loadRemisiones error:", error);
      }
      renderRemisionList();
    }

    async function deleteRemision(remisionId, remisionNo) {
      try {
        const id = Number(remisionId);
        if (!Number.isFinite(id) || id <= 0) throw new Error("ID de remision invalido.");
        const code = (remisionNo || "-").toString().trim() || "-";
        const confirmed = await ctx.uiConfirm(
          `Se eliminara la remision ${code}. Esta accion no se puede deshacer. Continuar?`,
          {
            title: "Eliminar remision",
            confirmText: "Eliminar",
            tone: "err",
          }
        );
        if (!confirmed) return;
        const response = await ctx.apiFetch(`/api/remisiones/${encodeURIComponent(id)}`, {
          method: "DELETE",
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo eliminar la remision.");
        }
        await loadRemisiones();
        ctx.setStatus(`Remision eliminada: ${payload.remision_no || code}`, "ok");
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function saveRemision() {
      try {
        const remisionNo = ((ctx.elements.remisionNoInput?.value || "").toString().trim().toUpperCase());
        if (!remisionNo) {
          ctx.setStatus("Ingresa el numero de remision.", "warn");
          return;
        }
        const remisionDate = readRemisionDate();
        const snap = buildReportSnapshot();
        if (!snap) {
          ctx.setStatus("Selecciona una mezcla para guardar la remision.", "warn");
          return;
        }
        const response = await ctx.apiFetch("/api/remisiones/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            file: ctx.state.file,
            remision_no: remisionNo,
            remision_date: remisionDate || undefined,
            snapshot: snap,
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo guardar la remision.");
        }
        if (ctx.elements.remisionNoInput) ctx.elements.remisionNoInput.value = "";
        if (ctx.elements.clienteInput) ctx.elements.clienteInput.value = "";
        if (ctx.elements.ubicacionInput) ctx.elements.ubicacionInput.value = "";
        if (ctx.elements.remisionFilterDate && remisionDate) {
          ctx.elements.remisionFilterDate.value = remisionDate;
        }
        await loadRemisiones();
        ctx.setStatus(`Remision guardada: ${payload.remision_no}`, "ok");
        ctx.pushToast(`Remision guardada con exito: ${payload.remision_no}`, "ok");
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    function init() {
      if (initialized) return;
      initialized = true;

      on(ctx.elements.exportReportBtn, "click", exportReport);
      on(ctx.elements.saveRemisionBtn, "click", saveRemision);
      on(ctx.elements.refreshRemisionBtn, "click", loadRemisiones);
      on(ctx.elements.remisionFilterDate, "change", loadRemisiones);
      on(ctx.elements.remisionNoInput, "input", normalizeRemisionInput);
      on(ctx.elements.remisionNoInput, "keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        saveRemision();
      });
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
      normalizeRemisionInput,
      buildReportSnapshot,
      normalizeReportSnapshot,
      buildReportHtml,
      openReportWindow,
      exportReport,
      openRemisionReport,
      renderRemisionList,
      loadRemisiones,
      deleteRemision,
      saveRemision,
    };
  };
})();
