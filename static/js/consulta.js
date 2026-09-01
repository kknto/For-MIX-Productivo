(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createConsultaModule = function createConsultaModule(ctx) {
    const costsModule = window.FormixModules.createConsultaCostsModule(ctx);
    const reportModule = window.FormixModules.createConsultaReportModule({
      ...ctx,
      costsModule,
    });
    const flowModule = window.FormixModules.createConsultaFlowModule({
      ...ctx,
      costsModule,
      reportModule,
    });

    return {
      init: flowModule.init,
      load: flowModule.load,
      unmount: flowModule.unmount,
      setStep: flowModule.setStep,
      runQuery: flowModule.runQuery,
      refresh: flowModule.refresh,
      renderRecipeAndCosts: costsModule.renderRecipeAndCosts,
      renderCostTable: costsModule.renderCostTable,
      exportReport: reportModule.exportReport,
      toggleQuoteMode: costsModule.toggleQuoteMode,
    };
  };
})();
