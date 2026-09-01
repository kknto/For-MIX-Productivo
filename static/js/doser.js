(function () {
  window.FormixModules = window.FormixModules || {};

  window.FormixModules.createDoserModule = function createDoserModule(ctx) {
    const reportsModule = window.FormixModules.createDoserReportsModule(ctx);
    const renderModule = window.FormixModules.createDoserRenderModule({ ...ctx, reportsModule });
    const searchModule = window.FormixModules.createDoserSearchModule({ ...ctx, renderModule });

    async function load() {
      if (ctx.elements.remisionDateInput && !ctx.elements.remisionDateInput.value) {
        ctx.elements.remisionDateInput.value = ctx.getTodayCancun();
      }
      if (ctx.elements.remisionFilterDate && !ctx.elements.remisionFilterDate.value) {
        ctx.elements.remisionFilterDate.value = ctx.getTodayCancun();
      }
      renderModule.render();
      await reportsModule.loadRemisiones();
      await searchModule.loadGlobalRecipes();
    }

    function init() {
      searchModule.init();
      reportsModule.init();
      renderModule.init();
    }

    function unmount() {
      renderModule.unmount();
      reportsModule.unmount();
      searchModule.unmount();
    }

    return {
      init,
      load,
      unmount,
      clearFilters: searchModule.clearFilters,
      rerender: renderModule.rerender,
      runSearch: searchModule.runSearch,
      loadGlobalRecipes: searchModule.loadGlobalRecipes,
      fillDoserSelectorsGlobal: searchModule.fillDoserSelectorsGlobal,
      fillDoserSelectors: searchModule.fillDoserSelectors,
      renderResults: searchModule.renderResults,
      selectRecipe: searchModule.selectRecipe,
      computeTheoreticalLoads: renderModule.computeTheoreticalLoads,
      render: renderModule.render,
      buildReportSnapshot: reportsModule.buildReportSnapshot,
      normalizeReportSnapshot: reportsModule.normalizeReportSnapshot,
      buildReportHtml: reportsModule.buildReportHtml,
      openReportWindow: reportsModule.openReportWindow,
      exportReport: reportsModule.exportReport,
      openRemisionReport: reportsModule.openRemisionReport,
      renderRemisionList: reportsModule.renderRemisionList,
      loadRemisiones: reportsModule.loadRemisiones,
      deleteRemision: reportsModule.deleteRemision,
      saveRemision: reportsModule.saveRemision,
    };
  };
})();
