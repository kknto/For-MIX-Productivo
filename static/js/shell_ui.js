(function () {
  window.FormixShared = window.FormixShared || {};

  function getToneMeta(tone = "ok") {
    if (tone === "err") return { label: "Error", buttonClass: "btn--danger" };
    if (tone === "warn") return { label: "Advertencia", buttonClass: "btn--warn" };
    if (tone === "info") return { label: "Informacion", buttonClass: "btn--secondary" };
    return { label: "Correcto", buttonClass: "btn--success" };
  }

  function toneIconSvg(tone = "ok", cssClass = "ui-tone-icon", escapeHtml = (v) => String(v ?? "")) {
    const cls = escapeHtml(cssClass);
    if (tone === "err") {
      return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="10"></circle><path d="M8 8l8 8M16 8l-8 8"></path></svg>`;
    }
    if (tone === "warn") {
      return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 3l10 18H2L12 3z"></path><path d="M12 9v5m0 3h.01"></path></svg>`;
    }
    if (tone === "info") {
      return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="10"></circle><path d="M12 10v7m0-10h.01"></path></svg>`;
    }
    return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="10"></circle><path d="M7 12l3 3 7-7"></path></svg>`;
  }

  function createUiHelpers(options = {}) {
    const uiToastHost = options.uiToastHost || null;
    const uiDialogHost = options.uiDialogHost || null;
    const escapeHtml = options.escapeHtml || ((value) => String(value ?? ""));

    function pushToast(message, tone = "ok", timeoutMs = 3200) {
      if (!uiToastHost || !message) return;
      const toneMeta = getToneMeta(tone);
      const toast = document.createElement("div");
      toast.className = "ui-toast";
      toast.setAttribute("data-tone", tone);
      toast.innerHTML = `
        <div class="ui-toast__head">
          ${toneIconSvg(tone, "ui-tone-icon ui-tone-icon--toast", escapeHtml)}
          <p class="ui-toast__title">${escapeHtml(toneMeta.label)}</p>
        </div>
        <p class="ui-toast__text">${escapeHtml(message)}</p>
      `;
      uiToastHost.appendChild(toast);
      window.setTimeout(() => {
        toast.classList.add("is-out");
        window.setTimeout(() => toast.remove(), 180);
      }, timeoutMs);
    }

    function uiDialog(options = {}) {
      const {
        mode = "confirm",
        title = "Confirmacion",
        message = "",
        defaultValue = "",
        confirmText = "Aceptar",
        cancelText = "Cancelar",
        tone = "ok",
      } = options;

      if (!uiDialogHost) {
        if (mode === "prompt") return Promise.resolve(window.prompt(message, defaultValue));
        return Promise.resolve(window.confirm(message));
      }

      const toneMeta = getToneMeta(tone);

      return new Promise((resolve) => {
        uiDialogHost.classList.remove("is-hidden");
        uiDialogHost.setAttribute("aria-hidden", "false");
        uiDialogHost.innerHTML = `
          <div class="ui-dialog" data-tone="${escapeHtml(tone)}" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}" tabindex="-1">
            <header class="ui-dialog__head">
              <div class="ui-dialog__title-wrap">
                ${toneIconSvg(tone, "ui-tone-icon ui-tone-icon--dialog", escapeHtml)}
                <h3 class="ui-dialog__title">${escapeHtml(title)}</h3>
              </div>
              <span class="ui-dialog__chip">${escapeHtml(toneMeta.label)}</span>
            </header>
            <div class="ui-dialog__body">
              <p class="ui-dialog__message">${escapeHtml(message)}</p>
              ${mode === "prompt"
                ? `<input class="ui-dialog__input" type="text" value="${escapeHtml(defaultValue)}" autocomplete="off">`
                : ""}
            </div>
            <footer class="ui-dialog__actions">
              <button type="button" class="btn btn--muted btn--small ui-dialog-cancel">${escapeHtml(cancelText)}</button>
              <button type="button" class="btn ${escapeHtml(toneMeta.buttonClass)} btn--small ui-dialog-confirm">${escapeHtml(confirmText)}</button>
            </footer>
          </div>
        `;

        const dialog = uiDialogHost.querySelector(".ui-dialog");
        const input = uiDialogHost.querySelector(".ui-dialog__input");
        const cancelBtn = uiDialogHost.querySelector(".ui-dialog-cancel");
        const confirmBtn = uiDialogHost.querySelector(".ui-dialog-confirm");

        const onBackdropClick = (event) => {
          if (event.target === uiDialogHost) close(mode === "prompt" ? null : false);
        };

        const close = (value) => {
          document.removeEventListener("keydown", onKeyDown);
          uiDialogHost.removeEventListener("click", onBackdropClick);
          uiDialogHost.classList.add("is-hidden");
          uiDialogHost.setAttribute("aria-hidden", "true");
          uiDialogHost.innerHTML = "";
          resolve(value);
        };

        const onKeyDown = (event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            close(mode === "prompt" ? null : false);
            return;
          }
          if (event.key === "Enter") {
            const targetTag = (event.target?.tagName || "").toLowerCase();
            if (targetTag === "textarea") return;
            event.preventDefault();
            close(mode === "prompt" ? (input ? input.value : "") : true);
          }
        };

        document.addEventListener("keydown", onKeyDown);
        if (cancelBtn) cancelBtn.addEventListener("click", () => close(mode === "prompt" ? null : false));
        if (confirmBtn) confirmBtn.addEventListener("click", () => close(mode === "prompt" ? (input ? input.value : "") : true));
        uiDialogHost.addEventListener("click", onBackdropClick);

        if (input) {
          input.focus();
          input.select();
        } else if (dialog) {
          dialog.focus();
        }
      });
    }

    function uiConfirm(message, options = {}) {
      return uiDialog({
        mode: "confirm",
        title: options.title || "Confirmacion",
        message,
        confirmText: options.confirmText || "Aceptar",
        cancelText: options.cancelText || "Cancelar",
        tone: options.tone || "warn",
      });
    }

    function uiPrompt(message, defaultValue = "", options = {}) {
      return uiDialog({
        mode: "prompt",
        title: options.title || "Captura de datos",
        message,
        defaultValue,
        confirmText: options.confirmText || "Guardar",
        cancelText: options.cancelText || "Cancelar",
        tone: options.tone || "ok",
      });
    }

    return {
      getToneMeta,
      toneIconSvg,
      pushToast,
      uiDialog,
      uiConfirm,
      uiPrompt,
    };
  }

  window.FormixShared.ui = {
    getToneMeta,
    toneIconSvg,
    createUiHelpers,
  };
})();
