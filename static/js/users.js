(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createUsersModule = function createUsersModule(ctx) {
    const { escapeHtml, uiConfirm, uiToastHost, uiDialogHost } = ctx;
    const usersTbody = document.getElementById("usersTbody");
    const btnNewUser = document.getElementById("btnNewUser");
    let initialized = false;
    let userList = [];
    const disposers = [];

    function on(element, eventName, handler) {
      if (!element) return;
      element.addEventListener(eventName, handler);
      disposers.push(() => element.removeEventListener(eventName, handler));
    }

    function setUsersStatus(msg, tone = "ok") {
      if (!uiToastHost) return;
      const toast = document.createElement("div");
      toast.className = `ui-toast ui-toast--${tone === "err" ? "error" : tone === "warn" ? "warning" : "success"} fade-in`;
      toast.textContent = msg;
      uiToastHost.appendChild(toast);
      setTimeout(() => {
        toast.classList.replace("fade-in", "fade-out");
        setTimeout(() => toast.remove(), 300);
      }, 3000);
    }

    async function userFetch(url, options = {}) {
      const csrfToken = ctx.state.auth.csrfToken || "";
      const headers = { ...(options.headers || {}) };
      if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
      }
      let opts = { ...options };
      if (opts.method && opts.method.toUpperCase() !== "GET") {
        if (opts.body && typeof opts.body === "string") {
          try {
            const parsed = JSON.parse(opts.body);
            parsed._csrf_token = csrfToken;
            opts.body = JSON.stringify(parsed);
          } catch (error) {
            // Keep body as-is if it is not JSON.
          }
        } else if (!opts.body) {
          opts = { ...opts, body: JSON.stringify({ _csrf_token: csrfToken }) };
        }
      }
      const res = await window.fetch(url, { ...opts, headers, credentials: "same-origin" });
      return res.json();
    }

    async function load() {
      try {
        const res = await userFetch("/api/users");
        if (!res.ok) throw new Error(res.error || "Error al cargar la lista de usuarios.");
        userList = res.users || [];
        render();
      } catch (err) {
        setUsersStatus(err.message, "err");
      }
    }

    function render() {
      if (!usersTbody) return;
      usersTbody.innerHTML = "";

      if (userList.length === 0) {
        usersTbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No hay usuarios registrados.</td></tr>`;
        return;
      }

      userList.forEach((user) => {
        const tr = document.createElement("tr");
        const statusClass = user.is_active ? "status--ok" : "status--error";
        const statusText = user.is_active ? "Activo" : "Inactivo";

        tr.innerHTML = `
          <td><strong>${escapeHtml(user.username)}</strong></td>
          <td><span class="ui-dialog__chip">${escapeHtml(user.role)}</span></td>
          <td style="text-align:center;"><span class="status ${statusClass}">${statusText}</span></td>
          <td style="text-align:center;">${escapeHtml(user.last_login_at || "Nunca")}</td>
          <td style="text-align:center;">${escapeHtml(user.created_at || "-")}</td>
          <td style="text-align:center;">
            <div style="display: flex; gap: 8px; justify-content: center;">
              <button class="btn btn--muted btn--small edit-user-btn" style="padding: 2px 8px;" title="Editar">Editar</button>
              <button class="btn btn--muted btn--small reset-pass-btn" style="padding: 2px 8px;" title="Resetear Contraseña">Reset</button>
              <button class="btn btn--danger btn--small del-user-btn" style="padding: 2px 8px;" title="Eliminar">Eliminar</button>
            </div>
          </td>
        `;

        tr.querySelector(".edit-user-btn").addEventListener("click", () => showUserFormDialog(user));
        tr.querySelector(".reset-pass-btn").addEventListener("click", () => showPasswordResetDialog(user));
        tr.querySelector(".del-user-btn").addEventListener("click", () => deleteUser(user));

        usersTbody.appendChild(tr);
      });
    }

    function showDialog(innerHtml, tone = "info") {
      if (!uiDialogHost) return null;
      const dialog = document.createElement("div");
      dialog.className = "ui-dialog";
      dialog.setAttribute("data-tone", tone);
      dialog.innerHTML = innerHtml;
      uiDialogHost.innerHTML = "";
      uiDialogHost.appendChild(dialog);
      uiDialogHost.classList.remove("is-hidden");
      return dialog;
    }

    function closeDialog() {
      if (uiDialogHost) uiDialogHost.classList.add("is-hidden");
    }

    async function showUserFormDialog(user = null) {
      const isEdit = !!user;
      showDialog(`
        <header class="ui-dialog__head">
          <h3 class="ui-dialog__title">${isEdit ? "Editar Usuario" : "Nuevo Usuario"}</h3>
        </header>
        <div class="ui-dialog__body">
          <form id="userForm">
            <div class="form-group" style="margin-bottom: 1rem;">
              <label style="color:var(--text-soft); font-size:0.85rem;">Nombre de Usuario</label>
              <input type="text" id="usrName" class="ui-dialog__input" required autocomplete="off" ${isEdit ? "disabled" : ""} value="${isEdit ? escapeHtml(user.username) : ""}">
            </div>
            ${!isEdit ? `
            <div class="form-group" style="margin-bottom: 1rem;">
              <label style="color:var(--text-soft); font-size:0.85rem;">Contraseña Temporal</label>
              <input type="password" id="usrPassword" class="ui-dialog__input" required autocomplete="new-password">
              <small style="color: var(--text-muted); font-size: 0.75rem;">Debe incluir al menos 10 caracteres, una mayúscula, una minúscula, un número y un símbolo especial.</small>
            </div>` : ""}
            <div class="form-group" style="margin-bottom: 1rem; display: flex; gap: 1rem;">
              <div style="flex: 1;">
                <label style="color:var(--text-soft); font-size:0.85rem;">Rol</label>
                <select id="usrRole" class="ui-dialog__input" required>
                  <option value="operador" ${isEdit && user.role === "operador" ? "selected" : ""}>Operador</option>
                  <option value="laboratorista" ${isEdit && user.role === "laboratorista" ? "selected" : ""}>Laboratorista</option>
                  <option value="presupuestador" ${isEdit && user.role === "presupuestador" ? "selected" : ""}>Presupuestador</option>
                  <option value="dosificador" ${isEdit && user.role === "dosificador" ? "selected" : ""}>Dosificador</option>
                  <option value="jefe-de-planta" ${isEdit && user.role === "jefe-de-planta" ? "selected" : ""}>Jefe de Planta</option>
                  <option value="administrador" ${isEdit && user.role === "administrador" ? "selected" : ""}>Administrador</option>
                </select>
              </div>
              <div style="flex: 1;">
                <label style="color:var(--text-soft); font-size:0.85rem;">Estado</label>
                <select id="usrStatus" class="ui-dialog__input" required>
                  <option value="1" ${isEdit && user.is_active === 1 ? "selected" : (!isEdit ? "selected" : "")}>Activo</option>
                  <option value="0" ${isEdit && user.is_active === 0 ? "selected" : ""}>Inactivo</option>
                </select>
              </div>
            </div>
          </form>
        </div>
        <footer class="ui-dialog__actions">
          <button id="cancelUserBtn" class="btn btn--muted btn--small">Cancelar</button>
          <button id="saveUserBtn" class="btn btn--primary btn--small">Guardar</button>
        </footer>
      `);

      document.getElementById("cancelUserBtn").addEventListener("click", closeDialog);
      document.getElementById("saveUserBtn").addEventListener("click", async () => {
        const payload = {
          id: isEdit ? user.id : null,
          username: document.getElementById("usrName").value.trim(),
          role: document.getElementById("usrRole").value,
          is_active: parseInt(document.getElementById("usrStatus").value, 10),
        };
        if (!isEdit) payload.password = document.getElementById("usrPassword").value;
        if (!payload.username) {
          window.alert("El usuario es requerido.");
          return;
        }
        if (!isEdit && !payload.password) {
          window.alert("La contraseña es requerida.");
          return;
        }

        try {
          const res = await userFetch("/api/users", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          if (!res.ok) throw new Error(res.error || "Error al guardar usuario");
          closeDialog();
          setUsersStatus("Usuario guardado correctamente.", "ok");
          await load();
        } catch (error) {
          window.alert(error.message);
        }
      });
    }

    async function showPasswordResetDialog(user) {
      showDialog(`
        <header class="ui-dialog__head">
          <h3 class="ui-dialog__title">Resetear Contraseña a ${escapeHtml(user.username)}</h3>
        </header>
        <div class="ui-dialog__body">
          <p class="ui-dialog__message" style="margin-bottom:1rem;">Genera una nueva contraseña temporal para este usuario. Se le pedirá que la cambie cuando inicie sesión.</p>
          <input type="password" id="resetPassInput" class="ui-dialog__input" placeholder="Nueva Contraseña" autocomplete="new-password">
        </div>
        <footer class="ui-dialog__actions">
          <button id="cancelResetBtn" class="btn btn--muted btn--small">Cancelar</button>
          <button id="confirmResetBtn" class="btn btn--danger btn--small">Resetear</button>
        </footer>
      `, "warn");

      document.getElementById("cancelResetBtn").addEventListener("click", closeDialog);
      document.getElementById("confirmResetBtn").addEventListener("click", async () => {
        const newPassword = document.getElementById("resetPassInput").value;
        if (!newPassword) {
          window.alert("Ingresa una contraseña");
          return;
        }

        try {
          const res = await userFetch(`/api/users/${user.id}/reset_password`, {
            method: "POST",
            body: JSON.stringify({ new_password: newPassword }),
          });
          if (!res.ok) throw new Error(res.error || "Error al resetear contraseña");
          closeDialog();
          setUsersStatus("Contraseña actualizada correctamente.", "ok");
        } catch (error) {
          window.alert(error.message);
        }
      });
    }

    async function deleteUser(user) {
      const confirmed = await uiConfirm(
        `¿Estás seguro de ELIMINAR al usuario "${user.username}"? Esta acción no se puede deshacer de forma segura. Si el usuario tiene registros, es mejor ponerlo en estado Inactivo.`,
        { title: "Eliminar Usuario", tone: "err", confirmText: "Sí, Eliminar" }
      );
      if (!confirmed) return;

      try {
        const res = await userFetch(`/api/users/${user.id}`, { method: "DELETE" });
        if (!res.ok) throw new Error(res.error || "Error al eliminar usuario.");
        setUsersStatus(`Usuario ${user.username} eliminado.`, "ok");
        await load();
      } catch (error) {
        window.alert(error.message);
      }
    }

    function init() {
      if (initialized) return;
      initialized = true;
      on(btnNewUser, "click", () => showUserFormDialog(null));
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
      load,
    };
  };
})();
