(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createEditorTableModule = function createEditorTableModule(ctx) {
    let initialized = false;
    const disposers = [];

    function on(element, eventName, handler) {
      if (!element) return;
      element.addEventListener(eventName, handler);
      disposers.push(() => element.removeEventListener(eventName, handler));
    }

    function getProcessedRows() {
      const term = ctx.normalize(ctx.state.searchText);
      let mapped = ctx.state.rows.map((row, sourceIndex) => ({ row, sourceIndex }));

      if (term) {
        mapped = mapped.filter((entry) => entry.row.some((cell) => ctx.normalize(cell).includes(term)));
      }

      if (ctx.state.sort.col !== null) {
        const { col, dir } = ctx.state.sort;
        mapped.sort((left, right) => {
          const result = ctx.compareValues(left.row[col] ?? "", right.row[col] ?? "");
          return dir === "asc" ? result : -result;
        });
      }
      return mapped;
    }

    function renderMeta(filteredCount) {
      if (!ctx.elements.metaInfo) return;
      const base = `Archivo: ${ctx.state.file} | Filas: ${ctx.state.rows.length} | Mostradas: ${filteredCount} | Columnas: ${ctx.state.headers.length}`;
      const family = ctx.state.datasetFamily || "-";
      const details = ` | Familia: ${family} | Encoding: ${ctx.state.encoding} | Delimitador: ${ctx.state.delimiter === "\t" ? "\\t" : ctx.state.delimiter}`;
      ctx.elements.metaInfo.textContent = base + details;
    }

    function renderFileSelect() {
      if (!ctx.elements.fileSelect) return;
      ctx.elements.fileSelect.innerHTML = "";
      const infos = ctx.state.fileInfos.length
        ? ctx.state.fileInfos
        : ctx.state.files.map((name) => ({ name, family: "" }));
      infos.forEach((info) => {
        const option = document.createElement("option");
        option.value = info.name;
        option.textContent = info.family ? `${info.name} | Familia ${info.family}` : info.name;
        option.selected = info.name === ctx.state.file;
        ctx.elements.fileSelect.appendChild(option);
      });
    }

    async function renameHeader(colIndex) {
      const modColIndex = ctx.getModDateColIndex();
      if (colIndex === modColIndex) {
        ctx.setStatus("La columna FECHA_MODIF es automatica y no se puede renombrar.", "warn");
        return;
      }
      const currentHeader = ctx.state.headers[colIndex] ?? "";
      const parsed = ctx.splitHeaderName(currentHeader);
      const newName = await ctx.uiPrompt("Nombre de la columna", parsed.name || currentHeader, {
        title: "Editar encabezado",
        confirmText: "Continuar",
      });
      if (newName === null) return;
      if (!newName.trim()) {
        ctx.setStatus("El nombre de la columna no puede quedar vacio.", "warn");
        return;
      }
      const newType = await ctx.uiPrompt(
        "Tipo (opcional). Si lo llenas se guardara como: Nombre (Tipo)",
        parsed.type,
        {
          title: "Tipo de columna",
          confirmText: "Aplicar",
        }
      );
      if (newType === null) return;
      ctx.state.headers[colIndex] = newType.trim() ? `${newName.trim()} (${newType.trim()})` : newName.trim();
      ctx.setDirty(true);
      ctx.refreshConsulta();
      ctx.setStatus(`Encabezado actualizado: ${ctx.state.headers[colIndex]}`, "ok");
      render();
    }

    function buildHeader() {
      if (!ctx.elements.tableHead) return;
      ctx.elements.tableHead.innerHTML = "";

      const tr = document.createElement("tr");
      const selTh = document.createElement("th");
      const allCheck = document.createElement("input");
      allCheck.type = "checkbox";
      allCheck.title = "Seleccionar filas visibles";
      allCheck.addEventListener("change", (event) => {
        const visibleRows = getProcessedRows().map((entry) => entry.sourceIndex);
        if (event.target.checked) visibleRows.forEach((idx) => ctx.state.selected.add(idx));
        else visibleRows.forEach((idx) => ctx.state.selected.delete(idx));
        renderBody();
      });
      selTh.appendChild(allCheck);
      tr.appendChild(selTh);

      const modColIndex = ctx.getModDateColIndex();
      ctx.state.headers.forEach((header, index) => {
        const th = document.createElement("th");
        const wrap = document.createElement("div");
        wrap.className = "th-wrap";

        const button = document.createElement("button");
        button.className = "th-btn";
        button.textContent = header === "" ? `Columna ${index + 1}` : header;
        if (ctx.state.sort.col === index) button.dataset.dir = ctx.state.sort.dir;
        button.addEventListener("click", () => {
          if (ctx.state.sort.col === index) ctx.state.sort.dir = ctx.state.sort.dir === "asc" ? "desc" : "asc";
          else ctx.state.sort = { col: index, dir: "asc" };
          render();
        });

        const editButton = document.createElement("button");
        editButton.className = "th-edit";
        editButton.textContent = "Editar";
        editButton.title = "Editar nombre de columna";
        editButton.addEventListener("click", async (event) => {
          event.preventDefault();
          event.stopPropagation();
          await renameHeader(index);
        });
        if (index === modColIndex) {
          editButton.disabled = true;
          editButton.title = "Columna automatica";
        }

        wrap.appendChild(button);
        wrap.appendChild(editButton);
        th.appendChild(wrap);
        tr.appendChild(th);
      });

      ctx.elements.tableHead.appendChild(tr);
    }

    function renderBody() {
      if (!ctx.elements.tableBody) return;
      ctx.elements.tableBody.innerHTML = "";
      const rows = getProcessedRows();
      renderMeta(rows.length);

      if (!rows.length) {
        const tr = document.createElement("tr");
        tr.className = "empty-row";
        const td = document.createElement("td");
        td.colSpan = ctx.state.headers.length + 1;
        td.textContent = "No hay filas para mostrar con el filtro actual.";
        tr.appendChild(td);
        ctx.elements.tableBody.appendChild(tr);
        return;
      }

      const modColIndex = ctx.getModDateColIndex();
      rows.forEach((entry) => {
        const tr = document.createElement("tr");
        const selectTd = document.createElement("td");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = ctx.state.selected.has(entry.sourceIndex);
        checkbox.addEventListener("change", (event) => {
          if (event.target.checked) ctx.state.selected.add(entry.sourceIndex);
          else ctx.state.selected.delete(entry.sourceIndex);
        });
        selectTd.appendChild(checkbox);
        tr.appendChild(selectTd);

        ctx.state.headers.forEach((_, colIndex) => {
          const td = document.createElement("td");
          td.className = "cell";
          const isModDate = colIndex === modColIndex;
          td.contentEditable = isModDate ? "false" : "true";
          if (isModDate) td.classList.add("cell-readonly");
          td.spellcheck = false;
          td.textContent = entry.row[colIndex] ?? "";
          td.dataset.row = String(entry.sourceIndex);
          td.dataset.col = String(colIndex);
          if (!isModDate) {
            td.addEventListener("input", (event) => {
              const cell = event.currentTarget;
              const rowIndex = Number(cell.dataset.row);
              const fieldIndex = Number(cell.dataset.col);
              ctx.state.rows[rowIndex][fieldIndex] = cell.textContent ?? "";
              ctx.setRowModifiedDate(rowIndex);
              ctx.setDirty(true);
              const rowTr = cell.parentElement;
              const dateCell = rowTr && rowTr.children[modColIndex + 1];
              if (dateCell) {
                dateCell.textContent = ctx.state.rows[rowIndex][modColIndex] ?? "";
              }
            });
          }
          tr.appendChild(td);
        });

        ctx.elements.tableBody.appendChild(tr);
      });
    }

    function render() {
      buildHeader();
      renderBody();
    }

    function addRow() {
      const modColIndex = ctx.ensureModDateColumn();
      const row = Array(ctx.state.headers.length).fill("");
      row[modColIndex] = ctx.nowStamp();
      ctx.state.rows.push(row);
      ctx.setDirty(true);
      ctx.setStatus("Fila agregada.", "ok");
      renderBody();
      ctx.refreshConsulta();
    }

    function deleteSelectedRows() {
      if (!ctx.state.selected.size) {
        ctx.setStatus("Selecciona al menos una fila para eliminar.", "warn");
        return;
      }
      const indexes = [...ctx.state.selected].sort((left, right) => right - left);
      indexes.forEach((index) => ctx.state.rows.splice(index, 1));
      ctx.state.selected.clear();
      ctx.setDirty(true);
      ctx.setStatus(`Se eliminaron ${indexes.length} fila(s).`, "ok");
      renderBody();
      ctx.refreshConsulta();
    }

    function handleSearchInput(event) {
      ctx.state.searchText = event.target.value;
      renderBody();
    }

    function load() {
      render();
      renderFileSelect();
    }

    function init() {
      if (initialized) return;
      initialized = true;

      on(ctx.elements.searchInput, "input", handleSearchInput);
      on(ctx.elements.addBtn, "click", addRow);
      on(ctx.elements.deleteBtn, "click", deleteSelectedRows);
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
      unmount,
      getProcessedRows,
      renderMeta,
      renderFileSelect,
      renameHeader,
      buildHeader,
      renderBody,
      render,
      addRow,
      deleteSelectedRows,
    };
  };
})();
