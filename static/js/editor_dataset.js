(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createEditorDatasetModule = function createEditorDatasetModule(ctx) {
    let initialized = false;
    const disposers = [];

    function on(element, eventName, handler) {
      if (!element) return;
      element.addEventListener(eventName, handler);
      disposers.push(() => element.removeEventListener(eventName, handler));
    }

    async function loadData() {
      try {
        const response = await ctx.apiFetch("/api/data");
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "No se pudo cargar el archivo.");

        ctx.state.file = payload.file;
        ctx.state.files = payload.files || [];
        ctx.state.fileInfos = Array.isArray(payload.file_infos)
          ? payload.file_infos
            .map((info) => ({
              name: (info?.name || "").toString(),
              family: (info?.family || "").toString().trim(),
            }))
            .filter((info) => info.name)
          : ctx.state.files.map((name) => ({ name: (name || "").toString(), family: "" }));
        ctx.state.datasetFamily = (payload.family || "").toString().trim();
        ctx.state.version = Number.isFinite(Number(payload.version)) ? Number(payload.version) : null;
        ctx.state.encoding = payload.encoding;
        ctx.state.delimiter = payload.delimiter;
        ctx.state.updatedAt = payload.updated_at || "";
        ctx.state.headers = payload.headers || [];
        ctx.state.rows = payload.rows || [];
        ctx.ensureModDateColumn();
        ctx.state.selected.clear();
        ctx.state.sort = { col: null, dir: "asc" };
        ctx.state.searchText = "";
        if (ctx.elements.searchInput) ctx.elements.searchInput.value = "";
        ctx.setDirty(false);
        await ctx.loadQcData(ctx.state.file);
        await ctx.loadDoserParams(ctx.state.file);
        ctx.table.renderFileSelect();
        if (ctx.elements.datasetFamilyInput) {
          ctx.elements.datasetFamilyInput.value = ctx.state.datasetFamily;
        }
        ctx.table.render();
        ctx.refreshConsulta();
        await ctx.loadRemisiones();
        ctx.setStatus("Archivo cargado correctamente.", "ok");
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function selectActiveFile(fileName) {
      try {
        const response = await ctx.apiFetch("/api/select", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file: fileName }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) throw new Error(payload.error || "No se pudo cambiar el archivo.");
        ctx.setStatus(`Archivo activo: ${payload.file}`, "ok");
        await loadData();
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function saveDatasetFamily() {
      if (!ctx.elements.datasetFamilyInput) return;
      const familyCode = ctx.elements.datasetFamilyInput.value.trim().toUpperCase();
      if (!familyCode) {
        ctx.setStatus("La familia no puede quedar vacia.", "warn");
        return;
      }
      try {
        const response = await ctx.apiFetch("/api/family", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            file: ctx.state.file,
            family_code: familyCode,
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo guardar la familia.");
        }
        ctx.state.datasetFamily = (payload.family || "").toString().trim();
        if (Array.isArray(payload.file_infos)) {
          ctx.state.fileInfos = payload.file_infos
            .map((info) => ({
              name: (info?.name || "").toString(),
              family: (info?.family || "").toString().trim(),
            }))
            .filter((info) => info.name);
          ctx.state.files = ctx.state.fileInfos.map((item) => item.name);
        }
        ctx.elements.datasetFamilyInput.value = ctx.state.datasetFamily;
        ctx.table.renderFileSelect();
        ctx.refreshConsulta();
        ctx.table.renderMeta(ctx.table.getProcessedRows().length);
        ctx.setStatus(`Familia actualizada: ${ctx.state.datasetFamily}`, "ok");
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function chooseImportMode(preview) {
      const duplicateMsg = preview.duplicate_of
        ? `\nDetectado contenido duplicado de: ${preview.duplicate_of}`
        : "";
      const suggested = preview.suggested_mode || "new";
      const answer = await ctx.uiPrompt(
        `Modo de importacion (${preview.allowed_modes.join(" | ")}). Recomendado: ${suggested}.${duplicateMsg}`,
        suggested,
        {
          title: "Importacion de CSV",
          confirmText: "Seleccionar",
        }
      );
      if (answer === null) return null;
      const mode = answer.trim().toLowerCase();
      if (!preview.allowed_modes.includes(mode)) {
        throw new Error("Modo invalido. Usa new, replace o merge.");
      }
      return mode;
    }

    async function chooseFamilyCode(preview, mode) {
      const detected = (preview.family_guess || "").toString().trim().toUpperCase();
      const current = (ctx.state.datasetFamily || "").toString().trim().toUpperCase();
      const defaultValue = mode === "new" ? detected : detected || current;
      const promptText =
        mode === "new"
          ? `Familia detectada: ${detected || "no detectada"}.\nConfirma o escribe la familia del nuevo dataset (ej. 40, 60, 70).`
          : `Familia detectada en CSV: ${detected || "no detectada"}.\nEscribe la familia para el dataset destino o deja vacio para mantener la actual (${current || "-"})`;
      const answer = await ctx.uiPrompt(promptText, defaultValue, {
        title: "Familia del dataset",
        confirmText: "Continuar",
      });
      if (answer === null) return null;
      const family = answer.trim().toUpperCase();
      if (mode === "new" && !family) {
        throw new Error("La familia es requerida para crear un dataset nuevo.");
      }
      return family;
    }

    function describeValidation(preview) {
      const validation = preview.validation || { errors: [], warnings: [], stats: { rows: 0, columns: 0 } };
      const parts = [`Filas: ${validation.stats.rows}`, `Columnas: ${validation.stats.columns}`, `Hash: ${preview.hash}`];
      if (preview.family_guess) parts.push(`Familia detectada: ${preview.family_guess}`);
      if (preview.duplicate_of) parts.push(`Duplicado de: ${preview.duplicate_of}`);
      if (Array.isArray(preview.header_mapping) && preview.header_mapping.length) {
        const sample = preview.header_mapping
          .slice(0, 6)
          .map((item) => `${item.from} -> ${item.to}`)
          .join(" | ");
        parts.push(`Mapeo de columnas: ${sample}${preview.header_mapping.length > 6 ? " | ..." : ""}`);
      }
      if ((validation.warnings || []).length) parts.push(`Advertencias: ${validation.warnings.join(" | ")}`);
      return parts.join(" | ");
    }

    async function uploadNewCsv(file) {
      const form = new FormData();
      form.append("file", file);
      try {
        const previewResp = await ctx.apiFetch("/api/upload/preview", { method: "POST", body: form });
        const preview = await previewResp.json();
        if (!previewResp.ok || !preview.ok) {
          const msg = preview?.validation?.errors?.join(" | ") || preview.error || "No se pudo validar el CSV.";
          throw new Error(msg);
        }

        const mode = await chooseImportMode(preview);
        if (!mode) return;
        const familyCode = await chooseFamilyCode(preview, mode);
        if (familyCode === null) return;
        const targetFile = mode === "new" ? null : ctx.state.file;
        if (mode === "replace") {
          const ok = await ctx.uiConfirm(
            `Vas a REEMPLAZAR el dataset '${targetFile}'. Esta accion conserva historial pero cambia todo el contenido.`,
            {
              title: "Confirmar reemplazo",
              confirmText: "Reemplazar",
              tone: "warn",
            }
          );
          if (!ok) return;
        }

        const commitResp = await ctx.apiFetch("/api/upload/commit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            token: preview.token,
            mode,
            target_file: targetFile,
            family_code: familyCode,
          }),
        });
        const payload = await commitResp.json();
        if (!commitResp.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo confirmar la importacion.");
        }

        const summary =
          mode === "merge"
            ? `Merge listo: insertadas ${payload.inserted || 0}, actualizadas ${payload.updated || 0}.`
            : mode === "replace"
              ? `Dataset reemplazado: ${payload.file}.`
              : `Dataset cargado: ${payload.file}.`;
        ctx.setStatus(`${summary} ${describeValidation(preview)}`, "ok");
        await loadData();
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function deleteCsvFile(fileName) {
      try {
        const response = await ctx.apiFetch("/api/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file: fileName }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) throw new Error(payload.error || "No se pudo eliminar el archivo.");
        ctx.setStatus(`Dataset eliminado: ${payload.deleted}.`, "ok");
        await loadData();
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function restoreRevision(revisionId) {
      const response = await ctx.apiFetch("/api/history/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          revision_id: revisionId,
          file: ctx.state.file,
          version: ctx.state.version,
        }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        if (response.status === 409) {
          throw new Error("Conflicto de version al restaurar. Recarga y vuelve a intentar.");
        }
        throw new Error(payload.error || "No se pudo restaurar revision.");
      }
      ctx.setStatus(`Revision ${revisionId} restaurada.`, "ok");
      await loadData();
    }

    async function openHistoryDialog() {
      try {
        const response = await ctx.apiFetch(`/api/history?file=${encodeURIComponent(ctx.state.file)}`);
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo obtener historial.");
        }
        const revisions = payload.revisions || [];
        if (!revisions.length) {
          ctx.setStatus("No hay revisiones disponibles para restaurar.", "warn");
          return;
        }
        const top = revisions.slice(0, 20);
        const lines = top.map(
          (revision) => `${revision.id} | ${revision.created_at} | filas:${revision.row_count}${revision.note ? ` | ${revision.note}` : ""}`
        );
        const idText = await ctx.uiPrompt(
          `Historial (${payload.file}) v${payload.version}\nIngresa el ID de revision a restaurar:\n\n${lines.join("\n")}`,
          "",
          {
            title: "Restaurar historial",
            confirmText: "Restaurar",
          }
        );
        if (idText === null) return;
        const revisionId = Number(idText);
        if (!Number.isInteger(revisionId) || revisionId <= 0) {
          ctx.setStatus("ID de revision invalido.", "warn");
          return;
        }
        const ok = await ctx.uiConfirm(
          `Vas a restaurar la revision ${revisionId}. Se guardara una revision del estado actual antes de restaurar.`,
          {
            title: "Confirmar restauracion",
            confirmText: "Restaurar",
            tone: "warn",
          }
        );
        if (!ok) return;
        await restoreRevision(revisionId);
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function openAuditDialog() {
      try {
        const response = await ctx.apiFetch(`/api/audit?file=${encodeURIComponent(ctx.state.file || "")}&limit=120`);
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo cargar la bitacora.");
        }
        const items = Array.isArray(payload.items) ? payload.items : [];
        if (!items.length) {
          ctx.setStatus("Bitacora sin eventos para el dataset actual.", "warn");
          return;
        }
        const lines = items.slice(0, 40).map((item) => {
          const detailKeys = Object.keys(item.details || {});
          const detailText = detailKeys.length
            ? detailKeys.slice(0, 3).map((key) => `${key}:${item.details[key]}`).join(", ")
            : "-";
          return `${item.id} | ${item.created_at} | ${item.username || "-"} | ${item.action} | ${detailText}`;
        });
        await ctx.uiDialog({
          mode: "confirm",
          title: "Bitacora de cambios",
          message: lines.join("\n"),
          confirmText: "Cerrar",
          cancelText: "Cerrar",
          tone: "info",
        });
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function createManualBackup() {
      try {
        const reason = await ctx.uiPrompt("Motivo del respaldo (opcional):", "manual", {
          title: "Crear respaldo",
          confirmText: "Crear",
          tone: "info",
        });
        if (reason === null) return;
        const response = await ctx.apiFetch("/api/backups/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo crear el respaldo.");
        }
        const backup = payload.backup || {};
        ctx.setStatus(`Respaldo creado: ${backup.file || "-"}.`, "ok");
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function restoreBackupFromDialog() {
      try {
        const response = await ctx.apiFetch("/api/backups?limit=80");
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || "No se pudo obtener respaldos.");
        }
        const items = Array.isArray(payload.items) ? payload.items : [];
        if (!items.length) {
          ctx.setStatus("No hay respaldos disponibles.", "warn");
          return;
        }
        const previewLines = items
          .slice(0, 20)
          .map((item) => `${item.file} | ${item.created_at} | ${(item.reason || "").replace(/_/g, " ")}`);
        const selected = await ctx.uiPrompt(
          `Escribe el nombre exacto del respaldo a restaurar:\n\n${previewLines.join("\n")}`,
          items[0].file,
          {
            title: "Restaurar respaldo",
            confirmText: "Continuar",
            tone: "warn",
          }
        );
        if (selected === null) return;
        const file = selected.trim();
        if (!file) {
          ctx.setStatus("Debes indicar el nombre del respaldo.", "warn");
          return;
        }
        const ok = await ctx.uiConfirm(
          `Se restaurara el respaldo '${file}'. Se recomienda que no haya usuarios editando durante este proceso.`,
          {
            title: "Confirmar restauracion de respaldo",
            confirmText: "Restaurar",
            tone: "err",
          }
        );
        if (!ok) return;

        const restoreResp = await ctx.apiFetch("/api/backups/restore", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file }),
        });
        const restorePayload = await restoreResp.json();
        if (!restoreResp.ok || !restorePayload.ok) {
          throw new Error(restorePayload.error || "No se pudo restaurar el respaldo.");
        }
        ctx.setStatus(`Respaldo restaurado: ${file}.`, "ok");
        await loadData();
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function saveData() {
      try {
        ctx.ensureModDateColumn();
        const response = await ctx.apiFetch("/api/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            headers: ctx.state.headers,
            rows: ctx.state.rows,
            version: ctx.state.version,
          }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          if (response.status === 409) {
            throw new Error("Conflicto de version: otro cambio ya fue guardado. Recarga y vuelve a intentar.");
          }
          throw new Error(payload.error || "No se pudo guardar.");
        }
        if (Number.isFinite(Number(payload.version))) {
          ctx.state.version = Number(payload.version);
        }
        ctx.setDirty(false);
        ctx.setStatus("Cambios guardados en SQLite.", "ok");
        await loadData();
      } catch (error) {
        ctx.setStatus(String(error), "err");
      }
    }

    async function handleReload() {
      if (ctx.state.dirty || ctx.state.qcDirty) {
        const proceed = await ctx.uiConfirm("Hay cambios sin guardar. Deseas recargar de todos modos?", {
          title: "Recargar datos",
          confirmText: "Recargar",
          tone: "warn",
        });
        if (!proceed) return;
      }
      await loadData();
    }

    async function handleLoadSelected() {
      const selectedFile = ctx.elements.fileSelect?.value || "";
      if (!selectedFile) {
        ctx.setStatus("No hay archivo seleccionado.", "warn");
        return;
      }
      if (ctx.state.dirty || ctx.state.qcDirty) {
        const proceed = await ctx.uiConfirm("Hay cambios sin guardar. Cambiar de archivo puede descartarlos. Continuar?", {
          title: "Cambiar archivo",
          confirmText: "Cambiar",
          tone: "warn",
        });
        if (!proceed) return;
      }
      await selectActiveFile(selectedFile);
    }

    async function handleUploadButton() {
      if (ctx.state.dirty || ctx.state.qcDirty) {
        const proceed = await ctx.uiConfirm("Hay cambios sin guardar. Cargar otro CSV puede descartarlos. Continuar?", {
          title: "Cargar nuevo CSV",
          confirmText: "Continuar",
          tone: "warn",
        });
        if (!proceed) return;
      }
      if (ctx.elements.uploadInput) {
        ctx.elements.uploadInput.value = "";
        ctx.elements.uploadInput.click();
      }
    }

    async function handleDeleteFile() {
      const selectedFile = ctx.elements.fileSelect?.value || "";
      if (!selectedFile) {
        ctx.setStatus("No hay archivo seleccionado para eliminar.", "warn");
        return;
      }
      if (ctx.state.dirty || ctx.state.qcDirty) {
        const proceed = await ctx.uiConfirm("Hay cambios sin guardar. Eliminar un CSV puede descartar estos cambios. Continuar?", {
          title: "Eliminar CSV",
          confirmText: "Continuar",
          tone: "warn",
        });
        if (!proceed) return;
      }
      const confirmDelete = await ctx.uiConfirm(
        `Seguro que quieres eliminar el dataset '${selectedFile}'?`,
        {
          title: "Confirmar eliminacion",
          confirmText: "Eliminar",
          tone: "err",
        }
      );
      if (!confirmDelete) return;
      await deleteCsvFile(selectedFile);
    }

    async function handlePurgeDeleted() {
      const confirmHard = await ctx.uiConfirm(
        "Estas seguro de que deseas eliminar DEFINITIVAMENTE todos los archivos borrados? Esto eliminara tambien todas las REMISIONES vinculadas a ellos.",
        {
          title: "Hard Reset - Purga Definitiva",
          confirmText: "Si, entiendo el riesgo",
          tone: "err",
        }
      );
      if (!confirmHard) return;

      const finalBoss = await ctx.uiConfirm(
        "ADVERTENCIA CRITICA. Esta accion borrara permanentemente el historial de remisiones, transacciones de inventario y perfiles. No se puede deshacer. Deseas purgar todo ahora?",
        {
          title: "Confirmacion Final Irreversible",
          confirmText: "BORRAR TODO DEFINITIVAMENTE",
          tone: "err",
        }
      );
      if (!finalBoss) return;

      ctx.setStatus("Purgando archivos de la base de datos...", "info");
      try {
        const resp = await ctx.apiFetch("/api/purge_deleted", { method: "POST" });
        const res = await resp.json();
        if (!res.ok) {
          ctx.setStatus(`Error al purgar: ${res.error || "Error desconocido"}`, "err");
          return;
        }
        ctx.setStatus(`Purga completada: ${res.purged_count} archivos eliminados fisicamente.`, "ok");
        await loadData();
      } catch (error) {
        ctx.setStatus(`Error de red al purgar: ${error.message}`, "err");
      }
    }

    async function handleUploadChange(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".csv")) {
        ctx.setStatus("Selecciona un archivo con extension .csv", "warn");
        return;
      }
      await uploadNewCsv(file);
    }

    function init() {
      if (initialized) return;
      initialized = true;

      on(ctx.elements.reloadBtn, "click", handleReload);
      on(ctx.elements.saveBtn, "click", saveData);
      on(ctx.elements.historyBtn, "click", openHistoryDialog);
      on(ctx.elements.auditBtn, "click", openAuditDialog);
      on(ctx.elements.backupCreateBtn, "click", createManualBackup);
      on(ctx.elements.backupRestoreBtn, "click", restoreBackupFromDialog);
      on(ctx.elements.loadSelectedBtn, "click", handleLoadSelected);
      on(ctx.elements.uploadBtn, "click", handleUploadButton);
      on(ctx.elements.deleteFileBtn, "click", handleDeleteFile);
      on(ctx.elements.purgeBtn, "click", handlePurgeDeleted);
      on(ctx.elements.uploadInput, "change", handleUploadChange);
      on(ctx.elements.saveFamilyBtn, "click", saveDatasetFamily);
      on(ctx.elements.datasetFamilyInput, "keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        saveDatasetFamily();
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
      loadData,
      selectActiveFile,
      saveDatasetFamily,
      uploadNewCsv,
      deleteCsvFile,
      openHistoryDialog,
      restoreRevision,
      openAuditDialog,
      createManualBackup,
      restoreBackupFromDialog,
      saveData,
    };
  };
})();
