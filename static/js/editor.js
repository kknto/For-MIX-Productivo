(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createEditorModule = function createEditorModule(ctx) {
    const table = window.FormixModules.createEditorTableModule(ctx);
    const dataset = window.FormixModules.createEditorDatasetModule({ ...ctx, table });

    function init() {
      table.init();
      dataset.init();
    }

    function load() {
      table.load();
    }

    function unmount() {
      dataset.unmount();
      table.unmount();
    }

    return {
      init,
      load,
      unmount,
      getProcessedRows: table.getProcessedRows,
      renderMeta: table.renderMeta,
      renderFileSelect: table.renderFileSelect,
      renameHeader: table.renameHeader,
      buildHeader: table.buildHeader,
      renderBody: table.renderBody,
      render: table.render,
      loadData: dataset.loadData,
      selectActiveFile: dataset.selectActiveFile,
      saveDatasetFamily: dataset.saveDatasetFamily,
      uploadNewCsv: dataset.uploadNewCsv,
      deleteCsvFile: dataset.deleteCsvFile,
      openHistoryDialog: dataset.openHistoryDialog,
      restoreRevision: dataset.restoreRevision,
      openAuditDialog: dataset.openAuditDialog,
      createManualBackup: dataset.createManualBackup,
      restoreBackupFromDialog: dataset.restoreBackupFromDialog,
      saveData: dataset.saveData,
      addRow: table.addRow,
      deleteSelectedRows: table.deleteSelectedRows,
    };
  };
})();
