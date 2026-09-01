(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createQcSyncModule = function createQcSyncModule(ctx) {
    let initialized = false;
    const disposers = [];
    let isSavingQcData = false;
    let isSavingQcHumidity = false;

    function on(element, eventName, handler) {
      if (!element) return;
      element.addEventListener(eventName, handler);
      disposers.push(() => element.removeEventListener(eventName, handler));
    }

    function syncStamps() {
      const stamp = ctx.state.qcUpdatedAt || "-";
      const suffix = ctx.state.qcError ? ` | Error: ${ctx.state.qcError}` : "";
      if (ctx.elements.editorQcMeta) {
        ctx.elements.editorQcMeta.textContent = `Archivo: ${ctx.state.file || "-"} | Fecha QC: ${stamp}${suffix}`;
      }
      if (ctx.elements.qcLinkedStamp) {
        ctx.elements.qcLinkedStamp.textContent = `Sincronizado con Editor CSV | Fecha QC: ${stamp}`;
      }
    }

    function rerenderDependents() {
      ctx.renderDoser();
      if (ctx.state.selectedQueryRow !== null) {
        ctx.renderRecipeAndCosts(ctx.state.rows[ctx.state.selectedQueryRow]);
      }
    }

    function onFieldChange(aggName, field, rawValue, source = "editor") {
      if (source === "editor" && field === "humedad") return;
      if (source === "dosificador" && field !== "humedad") return;
      if (!ctx.state.doser.quality[aggName]) ctx.state.doser.quality[aggName] = {};
      ctx.state.doser.quality[aggName][field] = ctx.toNumber(rawValue);
      ctx.setQcDirty(true);
      syncStamps();
      if (ctx.state.view === "dosificador") ctx.renderDoser();
      if (ctx.state.selectedQueryRow !== null) {
        ctx.renderRecipeAndCosts(ctx.state.rows[ctx.state.selectedQueryRow]);
      }
    }

    function renderEditorTable() {
      const { editorQcBody } = ctx.elements;
      if (!editorQcBody) return;
      editorQcBody.innerHTML = "";
      ctx.QC_AGGREGATES.forEach((aggName) => {
        const tr = document.createElement("tr");
        const tdName = document.createElement("td");
        tdName.textContent = aggName;
        tr.appendChild(tdName);
        ctx.QC_FIELDS.forEach((field) => {
          const td = document.createElement("td");
          const input = document.createElement("input");
          input.className = "qc-input";
          input.type = "number";
          input.min = "0";
          input.step = "0.01";
          input.value = (ctx.state.doser.quality[aggName]?.[field] ?? 0).toString();
          const editable = ctx.state.auth.canEdit && field !== "humedad";
          input.disabled = !editable;
          if (!editable) input.classList.add("qc-input--readonly");
          if (editable) {
            input.addEventListener("input", () => onFieldChange(aggName, field, input.value, "editor"));
          }
          td.appendChild(input);
          tr.appendChild(td);
        });
        editorQcBody.appendChild(tr);
      });
      syncStamps();
    }

    function renderTable() {
      const { qcBody } = ctx.elements;
      if (!qcBody) return;
      qcBody.innerHTML = "";
      ctx.QC_AGGREGATES.forEach((aggName) => {
        const tr = document.createElement("tr");
        const tdName = document.createElement("td");
        tdName.textContent = aggName;
        tr.appendChild(tdName);
        ctx.QC_FIELDS.forEach((field) => {
          const td = document.createElement("td");
          const input = document.createElement("input");
          input.className = "qc-input";
          input.type = "number";
          input.min = "0";
          input.step = "0.01";
          input.value = (ctx.state.doser.quality[aggName]?.[field] ?? 0).toString();
          const editable = ctx.state.auth.canEditQcHumidity && field === "humedad";
          input.disabled = !editable;
          if (!editable) input.classList.add("qc-input--readonly");
          if (editable) {
            input.addEventListener("change", () => onFieldChange(aggName, field, input.value, "dosificador"));
          }
          td.appendChild(input);
          tr.appendChild(td);
        });
        qcBody.appendChild(tr);
      });
      syncStamps();
    }

    async function load(fileName = ctx.state.file) {
      ctx.state.qcError = "";
      try {
        const response = await ctx.apiFetch(`/api/qc?file=${encodeURIComponent(fileName || "")}`);
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo cargar Control de Calidad.");
        }
        ctx.state.qcVersion = Number.isFinite(Number(payload.version)) ? Number(payload.version) : 0;
        ctx.state.qcUpdatedAt = payload.updated_at || "";
        ctx.state.doser.quality = ctx.normalizeQualityValues(payload.values);
        ctx.setQcDirty(false);
      } catch (error) {
        ctx.state.qcVersion = 0;
        ctx.state.qcUpdatedAt = "";
        ctx.state.doser.quality = ctx.createDefaultQuality();
        ctx.state.qcError = String(error);
        ctx.setQcDirty(false);
      }
      renderEditorTable();
    }

    async function save() {
      if (isSavingQcData) return;
      isSavingQcData = true;
      if (ctx.elements.saveQcBtn) ctx.elements.saveQcBtn.disabled = true;

      try {
        const response = await ctx.apiFetch("/api/qc/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            file: ctx.state.file,
            version: ctx.state.qcVersion,
            values: ctx.state.doser.quality,
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          if (response.status === 409) {
            throw new Error("Conflicto de version en Control de Calidad. Recarga y vuelve a intentar.");
          }
          throw new Error(payload.error || "No se pudo guardar Control de Calidad.");
        }
        ctx.state.qcVersion = Number(payload.version || 0);
        ctx.state.qcUpdatedAt = payload.updated_at || "";
        ctx.state.doser.quality = ctx.normalizeQualityValues(payload.values);
        ctx.state.qcError = "";
        ctx.setQcDirty(false);
        renderEditorTable();
        rerenderDependents();
        ctx.setStatus("Control de Calidad guardado.", "ok");
      } catch (error) {
        ctx.setStatus(String(error), "err");
      } finally {
        isSavingQcData = false;
        if (ctx.elements.saveQcBtn) ctx.elements.saveQcBtn.disabled = false;
      }
    }

    async function saveHumidity() {
      if (isSavingQcHumidity) return;
      isSavingQcHumidity = true;
      if (ctx.elements.saveQcHumidityBtn) ctx.elements.saveQcHumidityBtn.disabled = true;

      if (!ctx.state.auth.canEditQcHumidity) {
        ctx.setStatus("No tienes permisos para guardar humedad.", "warn");
        return;
      }
      try {
        const humidityValues = {};
        ctx.QC_AGGREGATES.forEach((agg) => {
          humidityValues[agg] = {
            humedad: ctx.toNumber(ctx.state.doser.quality[agg]?.humedad ?? 0),
          };
        });
        const response = await ctx.apiFetch("/api/qc/humidity/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            file: ctx.state.file,
            version: ctx.state.qcVersion,
            values: humidityValues,
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          if (response.status === 409) {
            throw new Error("Conflicto de version en humedad. Recarga y vuelve a intentar.");
          }
          throw new Error(payload.error || "No se pudo guardar la humedad.");
        }
        ctx.state.qcVersion = Number(payload.version || 0);
        ctx.state.qcUpdatedAt = payload.updated_at || "";
        ctx.state.doser.quality = ctx.normalizeQualityValues(payload.values);
        ctx.state.qcError = "";
        ctx.setQcDirty(false);
        renderEditorTable();
        rerenderDependents();
        ctx.setStatus("Humedad guardada correctamente.", "ok");
      } catch (error) {
        ctx.setStatus(String(error), "err");
      } finally {
        isSavingQcHumidity = false;
        if (ctx.elements.saveQcHumidityBtn) ctx.elements.saveQcHumidityBtn.disabled = false;
      }
    }

    function init() {
      if (initialized) return;
      initialized = true;
      on(ctx.elements.saveQcBtn, "click", save);
      on(ctx.elements.saveQcHumidityBtn, "click", saveHumidity);
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
      syncStamps,
      onFieldChange,
      renderEditorTable,
      renderTable,
      load,
      save,
      saveHumidity,
    };
  };
})();
