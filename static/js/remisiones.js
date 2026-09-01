(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createRemisionesModule = function createRemisionesModule(ctx) {
    let initialized = false;
    const disposers = [];

    function on(element, eventName, handler) {
      if (!element) return;
      element.addEventListener(eventName, handler);
      disposers.push(() => element.removeEventListener(eventName, handler));
    }

    function canEditRemision() {
      return ctx.state.auth.role === "administrador";
    }

    function canDeleteRemision() {
      return ["administrador", "jefe-de-planta", "dosificador"].includes(ctx.state.auth.role);
    }

    function ensureDefaultDates() {
      const today = ctx.getTodayCancun();
      if (!ctx.state.remisiones.filters.date_from) ctx.state.remisiones.filters.date_from = today;
      if (!ctx.state.remisiones.filters.date_to) ctx.state.remisiones.filters.date_to = today;
      syncInputsFromState();
    }

    function syncInputsFromState() {
      const filters = ctx.state.remisiones.filters;
      if (ctx.elements.dateFromInput) ctx.elements.dateFromInput.value = filters.date_from || "";
      if (ctx.elements.dateToInput) ctx.elements.dateToInput.value = filters.date_to || "";
      if (ctx.elements.remisionNoInput) ctx.elements.remisionNoInput.value = filters.remision_no || "";
      if (ctx.elements.clienteInput) ctx.elements.clienteInput.value = filters.cliente || "";
      if (ctx.elements.formulaInput) ctx.elements.formulaInput.value = filters.formula || "";
      if (ctx.elements.sourceFileInput) ctx.elements.sourceFileInput.value = filters.source_file || "";
    }

    function syncStateFromInputs(resetPage = false) {
      ctx.state.remisiones.filters = {
        date_from: (ctx.elements.dateFromInput?.value || "").trim(),
        date_to: (ctx.elements.dateToInput?.value || "").trim(),
        remision_no: (ctx.elements.remisionNoInput?.value || "").trim(),
        cliente: (ctx.elements.clienteInput?.value || "").trim(),
        formula: (ctx.elements.formulaInput?.value || "").trim(),
        source_file: (ctx.elements.sourceFileInput?.value || "").trim(),
      };
      if (resetPage) ctx.state.remisiones.page = 1;
    }

    function buildListUrl() {
      const params = new URLSearchParams();
      const filters = ctx.state.remisiones.filters;
      if (filters.date_from) params.set("date_from", filters.date_from);
      if (filters.date_to) params.set("date_to", filters.date_to);
      if (filters.remision_no) params.set("remision_no", filters.remision_no);
      if (filters.cliente) params.set("cliente", filters.cliente);
      if (filters.formula) params.set("formula", filters.formula);
      if (filters.source_file) params.set("source_file", filters.source_file);
      params.set("page", String(ctx.state.remisiones.page || 1));
      params.set("page_size", String(ctx.state.remisiones.pageSize || 20));
      return `/api/remisiones?${params.toString()}`;
    }

    function renderMeta() {
      if (!ctx.elements.meta) return;
      const total = Number(ctx.state.remisiones.total || 0);
      if (!total) {
        ctx.elements.meta.textContent = "Sin remisiones para los filtros seleccionados.";
        return;
      }
      const page = Number(ctx.state.remisiones.page || 1);
      const pageSize = Number(ctx.state.remisiones.pageSize || 20);
      const start = ((page - 1) * pageSize) + 1;
      const end = Math.min(total, start + ctx.state.remisiones.items.length - 1);
      ctx.elements.meta.textContent = `Mostrando ${start}-${end} de ${total} remisiones.`;
    }

    function renderPager() {
      const page = Number(ctx.state.remisiones.page || 1);
      const totalPages = Number(ctx.state.remisiones.totalPages || 1);
      if (ctx.elements.pageInfo) {
        ctx.elements.pageInfo.textContent = `Pagina ${page} de ${totalPages}`;
      }
      if (ctx.elements.prevBtn) ctx.elements.prevBtn.disabled = page <= 1;
      if (ctx.elements.nextBtn) ctx.elements.nextBtn.disabled = page >= totalPages;
    }

    function renderTable() {
      if (!ctx.elements.body) return;
      ctx.elements.body.innerHTML = "";
      const items = Array.isArray(ctx.state.remisiones.items) ? ctx.state.remisiones.items : [];
      if (!items.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="11">No hay remisiones registradas para los filtros seleccionados.</td>`;
        ctx.elements.body.appendChild(tr);
        renderMeta();
        renderPager();
        return;
      }

      items.forEach((item) => {
        const snapshot = item.snapshot || {};
        const tr = document.createElement("tr");
        const cliente = item.cliente || snapshot.cliente || "-";
        const ubicacion = item.ubicacion || snapshot.ubicacion || "-";
        tr.innerHTML = `
          <td><span class="remision-cell remision-cell--date" title="${ctx.escapeHtml(item.created_at || "-")}">${ctx.escapeHtml(item.created_at || "-")}</span></td>
          <td>${ctx.escapeHtml(item.remision_no || "-")}</td>
          <td><span class="remision-cell remision-cell--client" title="${ctx.escapeHtml(cliente)}">${ctx.escapeHtml(cliente)}</span></td>
          <td><span class="remision-cell remision-cell--location" title="${ctx.escapeHtml(ubicacion)}">${ctx.escapeHtml(ubicacion)}</span></td>
          <td><span class="remision-cell remision-cell--formula" title="${ctx.escapeHtml(item.formula || "-")}">${ctx.escapeHtml(item.formula || "-")}</span></td>
          <td>${ctx.escapeHtml(item.fc || "-")}</td>
          <td>${ctx.escapeHtml(item.tma || "-")}</td>
          <td>${ctx.formatNum(item.dosificacion_m3 || 0)}</td>
          <td><span class="remision-cell" title="${ctx.escapeHtml(item.source_file || "-")}">${ctx.escapeHtml(item.source_file || "-")}</span></td>
          <td><span class="remision-cell" title="${ctx.escapeHtml(item.created_by || "-")}">${ctx.escapeHtml(item.created_by || "-")}</span></td>
          <td class="remision-actions"></td>
        `;

        const actionsCell = tr.querySelector(".remision-actions");
        const reportBtn = document.createElement("button");
        reportBtn.type = "button";
        reportBtn.className = "btn btn--secondary btn--small";
        reportBtn.textContent = "Reporte";
        reportBtn.addEventListener("click", () => ctx.openRemisionReport(item.id));
        actionsCell.appendChild(reportBtn);

        if (canEditRemision()) {
          const editBtn = document.createElement("button");
          editBtn.type = "button";
          editBtn.className = "btn btn--muted btn--small";
          editBtn.textContent = "Editar";
          editBtn.addEventListener("click", () => {
            if (typeof window.openEditRemisionModal === "function") window.openEditRemisionModal(item);
          });
          actionsCell.appendChild(editBtn);
        }

        if (canDeleteRemision()) {
          const deleteBtn = document.createElement("button");
          deleteBtn.type = "button";
          deleteBtn.className = "btn btn--danger btn--small";
          deleteBtn.textContent = "Eliminar";
          deleteBtn.addEventListener("click", () => deleteRemision(item.id, item.remision_no));
          actionsCell.appendChild(deleteBtn);
        }

        ctx.elements.body.appendChild(tr);
      });

      renderMeta();
      renderPager();
    }

    async function load() {
      if (!ctx.canAccessView("remisiones")) return;
      ensureDefaultDates();
      syncStateFromInputs(false);
      try {
        if (ctx.elements.meta) ctx.elements.meta.textContent = "Cargando remisiones...";
        const response = await ctx.apiFetch(buildListUrl());
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo cargar remisiones.");
        }
        ctx.state.remisiones.items = Array.isArray(payload.items) ? payload.items : [];
        ctx.state.remisiones.page = Number(payload.page || 1);
        ctx.state.remisiones.pageSize = Number(payload.page_size || ctx.state.remisiones.pageSize || 20);
        ctx.state.remisiones.total = Number(payload.total || 0);
        ctx.state.remisiones.totalPages = Number(payload.total_pages || 1);
      } catch (error) {
        ctx.state.remisiones.items = [];
        ctx.state.remisiones.total = 0;
        ctx.state.remisiones.totalPages = 1;
        ctx.setStatus(String(error), "err");
      }
      renderTable();
    }

    async function search() {
      syncStateFromInputs(true);
      await load();
    }

    async function clearFilters() {
      const today = ctx.getTodayCancun();
      ctx.state.remisiones.filters = {
        date_from: today,
        date_to: today,
        remision_no: "",
        cliente: "",
        formula: "",
        source_file: "",
      };
      ctx.state.remisiones.page = 1;
      syncInputsFromState();
      await load();
    }

    async function changePage(nextPage) {
      const totalPages = Number(ctx.state.remisiones.totalPages || 1);
      const target = Math.max(1, Math.min(totalPages, Number(nextPage || 1)));
      if (target === Number(ctx.state.remisiones.page || 1)) return;
      ctx.state.remisiones.page = target;
      await load();
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
        ctx.setStatus(`Remision eliminada: ${payload.remision_no || code}`, "ok");
        await load();
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    function maybeSearchOnEnter(event) {
      if (event.key !== "Enter") return;
      event.preventDefault();
      search();
    }

    function init() {
      if (initialized) return;
      initialized = true;
      on(ctx.elements.searchBtn, "click", search);
      on(ctx.elements.clearBtn, "click", clearFilters);
      on(ctx.elements.prevBtn, "click", () => changePage((ctx.state.remisiones.page || 1) - 1));
      on(ctx.elements.nextBtn, "click", () => changePage((ctx.state.remisiones.page || 1) + 1));
      [
        ctx.elements.dateFromInput,
        ctx.elements.dateToInput,
        ctx.elements.remisionNoInput,
        ctx.elements.clienteInput,
        ctx.elements.formulaInput,
        ctx.elements.sourceFileInput,
      ].forEach((input) => on(input, "keydown", maybeSearchOnEnter));
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
      clearFilters,
      unmount,
    };
  };
})();
