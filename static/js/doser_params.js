(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createDoserParamsModule = function createDoserParamsModule(ctx) {
    let isSaving = false;

    function syncInputs() {
      const p = ctx.state.doser.params || ctx.defaultDoserParams();
      if (ctx.elements.paramCementoPespInput) ctx.elements.paramCementoPespInput.value = (p.cemento_pesp ?? 0).toString();
      if (ctx.elements.paramAirePctInput) ctx.elements.paramAirePctInput.value = (p.aire_pct ?? 0).toString();
      if (ctx.elements.paramPasa200PctInput) ctx.elements.paramPasa200PctInput.value = (p.pasa_malla_200_pct ?? 0).toString();
      if (ctx.elements.paramPxlPctInput) ctx.elements.paramPxlPctInput.value = (p.pxl_pond_pct ?? 0).toString();
      if (ctx.elements.paramDensidadAggInput) ctx.elements.paramDensidadAggInput.value = (p.densidad_agregado_fallback ?? 0).toString();
    }

    function readFromInputs() {
      return ctx.normalizeDoserParams({
        cemento_pesp: ctx.elements.paramCementoPespInput?.value,
        aire_pct: ctx.elements.paramAirePctInput?.value,
        pasa_malla_200_pct: ctx.elements.paramPasa200PctInput?.value,
        pxl_pond_pct: ctx.elements.paramPxlPctInput?.value,
        densidad_agregado_fallback: ctx.elements.paramDensidadAggInput?.value,
      });
    }

    async function load(fileName = ctx.state.file) {
      try {
        const response = await ctx.apiFetch(`/api/doser/params?file=${encodeURIComponent(fileName || "")}`);
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudieron cargar parametros de dosificacion.");
        }
        ctx.state.doser.paramsVersion = Number.isFinite(Number(payload.version)) ? Number(payload.version) : 0;
        ctx.state.doser.paramsUpdatedAt = payload.updated_at || "";
        ctx.state.doser.params = ctx.normalizeDoserParams(payload.values);
      } catch (error) {
        ctx.state.doser.paramsVersion = 0;
        ctx.state.doser.paramsUpdatedAt = "";
        ctx.state.doser.params = ctx.defaultDoserParams();
        ctx.setStatus(String(error), "warn");
      }
      syncInputs();
    }

    async function save() {
      if (isSaving) return;
      isSaving = true;
      if (ctx.elements.saveDoserParamsBtn) ctx.elements.saveDoserParamsBtn.disabled = true;

      if (!ctx.canEditTolerances()) {
        ctx.setStatus("Solo administrador y jefe-de-planta pueden guardar parametros de dosificacion.", "warn");
        return;
      }
      try {
        const values = readFromInputs();
        const response = await ctx.apiFetch("/api/doser/params/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            file: ctx.state.file,
            version: ctx.state.doser.paramsVersion,
            values,
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          if (response.status === 409) {
            throw new Error("Conflicto de version en parametros de dosificacion. Recarga y vuelve a intentar.");
          }
          throw new Error(payload.error || "No se pudieron guardar parametros de dosificacion.");
        }
        ctx.state.doser.paramsVersion = Number(payload.version || 0);
        ctx.state.doser.paramsUpdatedAt = payload.updated_at || "";
        ctx.state.doser.params = ctx.normalizeDoserParams(payload.values);
        syncInputs();
        ctx.renderDoser();
        ctx.setStatus("Parametros de dosificacion guardados.", "ok");
      } catch (error) {
        ctx.setStatus(String(error), "err");
      } finally {
        isSaving = false;
        if (ctx.elements.saveDoserParamsBtn) ctx.elements.saveDoserParamsBtn.disabled = false;
      }
    }

    return {
      syncInputs,
      readFromInputs,
      load,
      save,
    };
  };
})();
