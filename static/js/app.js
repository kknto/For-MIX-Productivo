const APP_BOOT = window.APP_BOOT || {};
const INSTANCE_META = window.INSTANCE_META || {};
const ROLE_ALLOWED_VIEWS = {
  "administrador": ["consulta", "dosificador", "remisiones", "editor", "flotilla", "inventario", "laboratorio", "usuarios"],
  "jefe-de-planta": ["consulta", "dosificador", "remisiones", "editor", "flotilla", "inventario", "laboratorio"],
  "dosificador": ["dosificador", "remisiones", "flotilla", "inventario"],
  "presupuestador": ["consulta", "remisiones"],
  "laboratorista": ["laboratorio"],
};

function resolveAllowedViews(appBoot) {
  const bootViews = appBoot && Array.isArray(appBoot.allowed_views) ? appBoot.allowed_views.filter(Boolean) : [];
  if (bootViews.length) return bootViews;
  const role = ((appBoot && appBoot.role) || "").trim();
  return ROLE_ALLOWED_VIEWS[role] ? [...ROLE_ALLOWED_VIEWS[role]] : [];
}

const state = {
  auth: {
    username: APP_BOOT.username || "",
    role: APP_BOOT.role || "",
    mustChangePassword: Boolean(APP_BOOT.must_change_password),
    allowedViews: resolveAllowedViews(APP_BOOT),
    canEdit: Boolean(APP_BOOT.can_edit),
    canEditQcHumidity: Boolean(APP_BOOT.can_edit_qc_humidity),
    csrfToken: APP_BOOT.csrf_token || "",
  },
  instanceMeta: INSTANCE_META,
  file: "",
  files: [],
  fileInfos: [],
  datasetFamily: "",
  version: null,
  qcVersion: 0,
  qcUpdatedAt: "",
  qcDirty: false,
  qcError: "",
  encoding: "",
  delimiter: "",
  updatedAt: "",
  headers: [],
  rows: [],
  dirty: false,
  selected: new Set(),
  searchText: "",
  sort: { col: null, dir: "asc" },
  view: "editor",
  consultaStep: 0,
  index: {},
  queryResults: [],
  selectedQueryRow: null,
  unitCosts: {},
  haulCosts: {},
  quoteMode: false,
  quoteOverrides: {},
  remisiones: {
    items: [],
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 1,
    filters: {
      date_from: "",
      date_to: "",
      remision_no: "",
      cliente: "",
      formula: "",
      source_file: "",
    },
  },
  doser: {
    dosageM3: 7.0,
    paramsVersion: 0,
    paramsUpdatedAt: "",
    results: [],
    remisiones: [],
    quality: {
      "Fino 1": { pvs: 0, pvc: 0, densidad: 0, absorcion: 0, humedad: 0 },
      "Fino 2": { pvs: 0, pvc: 0, densidad: 0, absorcion: 0, humedad: 0 },
      "Grueso 1": { pvs: 0, pvc: 0, densidad: 0, absorcion: 0, humedad: 0 },
      "Grueso 2": { pvs: 0, pvc: 0, densidad: 0, absorcion: 0, humedad: 0 },
    },
    params: {
      cemento_pesp: 3.1,
      aire_pct: 2.0,
      pasa_malla_200_pct: 19.0,
      pxl_pond_pct: 6.4,
      densidad_agregado_fallback: 2.2,
    },
    tolerances: { cemento: 1, agregados: 3, agua: 2, aditivo: 1 },
    realLoads: {},
    selectedMaterials: {},
    invMaterials: [],
    familiesSummary: [],
    globalRecipes: [],
    selectedEntry: null,
  },
};
const MOD_DATE_HEADER = "FECHA_MODIF";
const QC_AGGREGATES = ["Fino 1", "Fino 2", "Grueso 1", "Grueso 2"];
const QC_FIELDS = ["pvs", "pvc", "densidad", "absorcion", "humedad"];
const BRAND_NAME = INSTANCE_META.brand_name || "ForMIX";
const BRAND_TAGLINE = INSTANCE_META.brand_tagline || "ForMIX Pilot";
const PLANT_NAME = INSTANCE_META.plant_name || "";
const BRAND_LOGO_URL = INSTANCE_META.logo_url
  || (INSTANCE_META.logo_path ? `${window.location.origin}/static/${INSTANCE_META.logo_path}` : `${window.location.origin}/static/img/logo_formix.svg`);
const MUTATING_HTTP_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

const tableHead = document.querySelector("#csvTable thead");
const tableBody = document.querySelector("#csvTable tbody");
const metaInfo = document.getElementById("metaInfo");
const statusBar = document.getElementById("statusBar");
const uiToastHost = document.getElementById("uiToastHost");
const uiDialogHost = document.getElementById("uiDialogHost");
const saveState = document.getElementById("saveState");
const searchInput = document.getElementById("searchInput");
const fileSelect = document.getElementById("fileSelect");
const datasetFamilyInput = document.getElementById("datasetFamilyInput");
const saveFamilyBtn = document.getElementById("saveFamilyBtn");
const uploadInput = document.getElementById("uploadInput");
const editorView = document.getElementById("editorView");
const consultaView = document.getElementById("consultaView");
const dosificadorView = document.getElementById("dosificadorView");
const remisionesView = document.getElementById("remisionesView");
const tabEditor = document.getElementById("tabEditor");
const tabConsulta = document.getElementById("tabConsulta");
const tabDosificador = document.getElementById("tabDosificador");
const tabRemisiones = document.getElementById("tabRemisiones");
const tabFlotilla = document.getElementById("tabFlotilla");
const tabInventario = document.getElementById("tabInventario");
const tabLaboratorio = document.getElementById("tabLaboratorio");
const tabUsuarios = document.getElementById("tabUsuarios");
const flotillaView = document.getElementById("flotillaView");
const inventarioView = document.getElementById("inventarioView");
const laboratorioView = document.getElementById("laboratorioView");
const usuariosView = document.getElementById("usuariosView");
const vehiclesBody = document.getElementById("vehiclesBody");
const fuelBody = document.getElementById("fuelBody");
const fuelVehicleSelect = document.getElementById("fuelVehicleSelect");
const fleetSummaryBody = document.getElementById("fleetSummaryBody");
const familiasBoard = document.getElementById("familiasBoard");
const updatedStamp = document.getElementById("updatedStamp");
const queryTable = document.getElementById("queryTable");
const queryBody = document.getElementById("queryBody");
const querySummary = document.getElementById("querySummary");
const recipeMeta = document.getElementById("recipeMeta");
const recipeBody = document.getElementById("recipeBody");
const recipeWeight = document.getElementById("recipeWeight");
const exportReportBtn = document.getElementById("exportReportBtn");
const toggleQuoteModeBtn = document.getElementById("toggleQuoteMode");
const costBody = document.getElementById("costBody");
const costHaulTotal = document.getElementById("costHaulTotal");
const costMaterialTotal = document.getElementById("costMaterialTotal");
const costTotal = document.getElementById("costTotal");
const qcBody = document.getElementById("qcBody");
const editorQcBody = document.getElementById("editorQcBody");
const editorQcMeta = document.getElementById("editorQcMeta");
const qcLinkedStamp = document.getElementById("qcLinkedStamp");
const saveQcBtn = document.getElementById("saveQcBtn");
const saveQcHumidityBtn = document.getElementById("saveQcHumidityBtn");
const tolAccessNote = document.getElementById("tolAccessNote");
const doserSummary = document.getElementById("doserSummary");
const doserSelectedMeta = document.getElementById("doserSelectedMeta");
const doserQueryBody = document.getElementById("doserQueryBody");
const doserRecipeBody = document.getElementById("doserRecipeBody");
const doserRecipeWeight = document.getElementById("doserRecipeWeight");
const doserTheoreticalBody = document.getElementById("doserTheoreticalBody");
const doserTheoreticalWeight = document.getElementById("doserTheoreticalWeight");
const doserRealBody = document.getElementById("doserRealBody");
const doserRealWeight = document.getElementById("doserRealWeight");
const doserExportReportBtn = document.getElementById("dExportReportBtn");
const doseM3Input = document.getElementById("doseM3");
const clienteInput = document.getElementById("dCliente");
const ubicacionInput = document.getElementById("dUbicacion");
const remisionNoInput = document.getElementById("dRemisionNo");
const remisionDateInput = document.getElementById("dRemisionDate");
const saveRemisionBtn = document.getElementById("dSaveRemisionBtn");
const refreshRemisionBtn = document.getElementById("dRefreshRemisionBtn");
const remisionFilterDate = document.getElementById("dRemisionFilterDate");
const remisionMeta = document.getElementById("dRemisionMeta");
const doserRemisionBody = document.getElementById("doserRemisionBody");
const remisionesMeta = document.getElementById("remisionesMeta");
const remisionesBody = document.getElementById("remisionesBody");
const remisionesPageInfo = document.getElementById("remisionesPageInfo");
const remisionesDateFromInput = document.getElementById("rDateFrom");
const remisionesDateToInput = document.getElementById("rDateTo");
const remisionesNoInput = document.getElementById("rRemisionNo");
const remisionesClienteInput = document.getElementById("rCliente");
const remisionesFormulaInput = document.getElementById("rFormula");
const remisionesSourceFileInput = document.getElementById("rSourceFile");
const remisionesSearchBtn = document.getElementById("rSearchBtn");
const remisionesClearBtn = document.getElementById("rClearBtn");
const remisionesPrevBtn = document.getElementById("rPrevBtn");
const remisionesNextBtn = document.getElementById("rNextBtn");
const tolCementoInput = document.getElementById("tolCemento");
const tolAgregadosInput = document.getElementById("tolAgregados");
const tolAguaInput = document.getElementById("tolAgua");
const tolAditivoInput = document.getElementById("tolAditivo");
const paramCementoPespInput = document.getElementById("paramCementoPesp");
const paramAirePctInput = document.getElementById("paramAirePct");
const paramPasa200PctInput = document.getElementById("paramPasa200Pct");
const paramPxlPctInput = document.getElementById("paramPxlPct");
const paramDensidadAggInput = document.getElementById("paramDensidadAgg");
const doserParamsMeta = document.getElementById("doserParamsMeta");
const saveDoserParamsBtn = document.getElementById("saveDoserParamsBtn");
const auditBtn = document.getElementById("auditBtn");
const backupCreateBtn = document.getElementById("backupCreateBtn");
const backupRestoreBtn = document.getElementById("backupRestoreBtn");
const {
  getCancunDate,
  getTodayCancun,
  getFullTodayCancun,
  startCancunClock,
} = window.FormixShared.time;
const {
  stripAccents,
  normalize,
  normalizeHeader,
  toNumber,
  formatNum,
  formatVol,
  formatMoney,
  escapeHtml,
  nowStamp,
} = window.FormixShared.format;
const {
  getToneMeta,
  toneIconSvg,
  pushToast,
  uiDialog,
  uiConfirm,
  uiPrompt,
} = window.FormixShared.ui.createUiHelpers({
  uiToastHost,
  uiDialogHost,
  escapeHtml,
});

startCancunClock({
  timeEl: document.getElementById("clockTime"),
  dateEl: document.getElementById("clockDate"),
});

function canEditDoserTolerances() {
  return state.auth.role === "jefe-de-planta" || state.auth.role === "administrador";
}

function withCsrf(options = {}) {
  const out = { ...options };
  const method = (out.method || "GET").toUpperCase();
  if (!MUTATING_HTTP_METHODS.has(method)) return out;
  const headers = { ...(out.headers || {}) };
  if (state.auth.csrfToken) headers["X-CSRF-Token"] = state.auth.csrfToken;
  out.headers = headers;
  return out;
}

function apiFetch(input, options = {}) {
  return window.fetch(input, withCsrf(options));
}

const doserFields = {
  family: document.getElementById("dFamily"),
  fc: document.getElementById("dFc"),
  edad: document.getElementById("dEdad"),
  tipo: document.getElementById("dTipo"),
  tma: document.getElementById("dTma"),
  rev: document.getElementById("dRev"),
  comp: document.getElementById("dComp"),
};

const queryFields = {
  family: document.getElementById("qFamily"),
  fc: document.getElementById("qFc"),
  edad: document.getElementById("qEdad"),
  tipo: document.getElementById("qTipo"),
  tma: document.getElementById("qTma"),
  rev: document.getElementById("qRev"),
  comp: document.getElementById("qComp"),
};

function createDefaultQuality() {
  return {
    "Fino 1": { pvs: 0, pvc: 0, densidad: 0, absorcion: 0, humedad: 0 },
    "Fino 2": { pvs: 0, pvc: 0, densidad: 0, absorcion: 0, humedad: 0 },
    "Grueso 1": { pvs: 0, pvc: 0, densidad: 0, absorcion: 0, humedad: 0 },
    "Grueso 2": { pvs: 0, pvc: 0, densidad: 0, absorcion: 0, humedad: 0 },
  };
}

function normalizeQualityValues(values) {
  const base = createDefaultQuality();
  if (!values || typeof values !== "object") return base;
  QC_AGGREGATES.forEach((agg) => {
    const row = values[agg];
    if (!row || typeof row !== "object") return;
    QC_FIELDS.forEach((field) => {
      base[agg][field] = toNumber(row[field]);
    });
  });
  return base;
}

function defaultDoserParams() {
  return {
    cemento_pesp: 3.1,
    aire_pct: 2.0,
    pasa_malla_200_pct: 19.0,
    pxl_pond_pct: 6.4,
    densidad_agregado_fallback: 2.2,
  };
}

function normalizeDoserParams(values) {
  const base = defaultDoserParams();
  if (!values || typeof values !== "object") return base;
  const out = {};
  Object.keys(base).forEach((key) => {
    const num = toNumber(values[key]);
    out[key] = num >= 0 ? num : base[key];
  });
  return out;
}

function safeDivide(numerator, denominator, fallback = 0) {
  const den = Number(denominator);
  if (!Number.isFinite(den) || Math.abs(den) <= 1e-9) {
    return { value: fallback, fallbackUsed: true };
  }
  return { value: Number(numerator) / den, fallbackUsed: false };
}

const recipeCore = window.FormixShared.recipeCore.createRecipeCore({
  normalize,
  toNumber,
  safeDivide,
  normalizeDoserParams,
  averagePV,
  getQualityFor,
});
const {
  splitHeaderName,
  isAggregateComponent,
  reportComponentLabel,
  classifyComponent,
  componentUnit,
  densityFor,
  normalizeConsultaRecipeItems,
  normalizeDoserRecipeItems,
  componentWeightFactor,
  computeDoserDetailedLoads,
} = recipeCore;
const datasetCore = window.FormixShared.datasetCore.createDatasetCore({
  state,
  normalizeHeader,
  splitHeaderName,
  compareValues,
  classifyComponent,
  componentUnit,
  isAggregateComponent,
  averagePV,
  densityFor,
  toNumber,
  getModDateColIndex,
});
const {
  buildHeaderIndex,
  valueByKey,
  getRowModDate,
  deriveFamily,
  getUniqueValues,
  fillSelect,
  buildAggregateColumnMap,
  extractRecipe,
} = datasetCore;

const queryResultShell = queryTable ? queryTable.closest(".result-shell") : null;
const consultaSlides = Array.from(document.querySelectorAll("#consultaView .consulta-slide"));
const consultaStepLabel = document.getElementById("consultaStepLabel");
const consultaPrevBtn = document.getElementById("consultaPrevBtn");
const consultaNextBtn = document.getElementById("consultaNextBtn");
const editorModule = window.FormixModules && typeof window.FormixModules.createEditorModule === "function"
  ? window.FormixModules.createEditorModule({
    state,
    elements: {
      tableHead,
      tableBody,
      metaInfo,
      fileSelect,
      datasetFamilyInput,
      searchInput,
      uploadInput,
      reloadBtn: document.getElementById("reloadBtn"),
      addBtn: document.getElementById("addBtn"),
      deleteBtn: document.getElementById("deleteBtn"),
      saveBtn: document.getElementById("saveBtn"),
      historyBtn: document.getElementById("historyBtn"),
      auditBtn,
      backupCreateBtn,
      backupRestoreBtn,
      loadSelectedBtn: document.getElementById("loadSelectedBtn"),
      uploadBtn: document.getElementById("uploadBtn"),
      deleteFileBtn: document.getElementById("deleteFileBtn"),
      purgeBtn: document.getElementById("purgeDeletedBtn"),
      saveFamilyBtn,
    },
    apiFetch,
    normalize,
    compareValues,
    uiPrompt,
    uiConfirm,
    uiDialog,
    setStatus,
    setDirty,
    refreshConsulta,
    ensureModDateColumn,
    getModDateColIndex,
    setRowModifiedDate,
    nowStamp,
    loadQcData,
    loadDoserParams,
    loadRemisiones,
  })
  : null;
const consultaModule = window.FormixModules && typeof window.FormixModules.createConsultaModule === "function"
  ? window.FormixModules.createConsultaModule({
    state,
    queryFields,
    doserFields,
    elements: {
      queryTable,
      queryBody,
      querySummary,
      queryResultShell,
      consultaSlides,
      consultaStepLabel,
      consultaPrevBtn,
      consultaNextBtn,
      recipeMeta,
      recipeBody,
      recipeWeight,
      costBody,
      costHaulTotal,
      costMaterialTotal,
      costTotal,
      exportReportBtn,
      toggleQuoteModeBtn,
      runQueryBtn: document.getElementById("runQueryBtn"),
      clearQueryBtn: document.getElementById("clearQueryBtn"),
    },
    normalize,
    toNumber,
    formatNum,
    formatVol,
    formatMoney,
    escapeHtml,
    nowStamp,
    splitHeaderName,
    valueByKey,
    getRowModDate,
    deriveFamily,
    getUniqueValues,
    fillSelect,
    fetchFamiliesSummary,
    renderFamiliesBoard,
    buildAggregateColumnMap,
    densityFor,
    extractRecipe,
    normalizeConsultaRecipeItems,
    reportComponentLabel,
    isAggregateComponent,
    averagePV,
    adjustRecipeByQuality,
    buildHeaderIndex,
    setStatus,
    brandLogoUrl: BRAND_LOGO_URL,
    brandName: BRAND_NAME,
    brandTagline: BRAND_TAGLINE,
  })
  : null;
const doserModule = window.FormixModules && typeof window.FormixModules.createDoserModule === "function"
  ? window.FormixModules.createDoserModule({
    doserFields,
    elements: {
      searchBtn: document.getElementById("dSearchBtn"),
      clearBtn: document.getElementById("dClearBtn"),
      summary: doserSummary,
      selectedMeta: doserSelectedMeta,
      queryBody: doserQueryBody,
      recipeBody: doserRecipeBody,
      recipeWeight: doserRecipeWeight,
      theoreticalBody: doserTheoreticalBody,
      theoreticalWeight: doserTheoreticalWeight,
      realBody: doserRealBody,
      realWeight: doserRealWeight,
      exportReportBtn: doserExportReportBtn,
      saveParamsBtn: saveDoserParamsBtn,
      saveRemisionBtn,
      refreshRemisionBtn,
      remisionDateInput,
      remisionFilterDate,
      remisionNoInput,
      remisionMeta,
      doserRemisionBody,
      clienteInput,
      ubicacionInput,
      doseM3Input,
      tolCementoInput,
      tolAgregadosInput,
      tolAguaInput,
      tolAditivoInput,
      paramCementoPespInput,
      paramAirePctInput,
      paramPasa200PctInput,
      paramPxlPctInput,
      paramDensidadAggInput,
    },
    getTodayCancun,
    apiFetch,
    state,
    toNumber,
    normalize,
    nowStamp,
    escapeHtml,
    formatNum,
    formatVol,
    createDefaultQuality,
    normalizeDoserParams,
    normalizeDoserRecipeItems,
    extractRecipe,
    computeDoserDetailedLoads,
    componentWeightFactor,
    toleranceFor,
    valueByKey,
    getRowModDate,
    deriveFamily,
    getUniqueValues,
    fillSelect,
    readParamsFromInputs: readDoserParamsFromInputs,
    qcAggregates: QC_AGGREGATES,
    brandLogoUrl: BRAND_LOGO_URL,
    brandName: BRAND_NAME,
    brandTagline: BRAND_TAGLINE,
    setStatus,
    canAccessView,
    canEditTolerances: canEditDoserTolerances,
    renderQcTable,
    loadQcData,
    loadDoserParams,
    uiConfirm,
    pushToast,
    saveParams: saveDoserParams,
  })
  : null;
const doserParamsModule = window.FormixModules && typeof window.FormixModules.createDoserParamsModule === "function"
  ? window.FormixModules.createDoserParamsModule({
    state,
    elements: {
      paramCementoPespInput,
      paramAirePctInput,
      paramPasa200PctInput,
      paramPxlPctInput,
      paramDensidadAggInput,
      saveDoserParamsBtn,
    },
    apiFetch,
    normalizeDoserParams,
    defaultDoserParams,
    canEditTolerances: canEditDoserTolerances,
    setStatus,
    renderDoser: renderDosificador,
  })
  : null;
const remisionesModule = window.FormixModules && typeof window.FormixModules.createRemisionesModule === "function"
  ? window.FormixModules.createRemisionesModule({
    state,
    apiFetch,
    canAccessView,
    getTodayCancun,
    escapeHtml,
    formatNum,
    setStatus,
    uiConfirm,
    openRemisionReport,
    elements: {
      view: remisionesView,
      meta: remisionesMeta,
      body: remisionesBody,
      pageInfo: remisionesPageInfo,
      dateFromInput: remisionesDateFromInput,
      dateToInput: remisionesDateToInput,
      remisionNoInput: remisionesNoInput,
      clienteInput: remisionesClienteInput,
      formulaInput: remisionesFormulaInput,
      sourceFileInput: remisionesSourceFileInput,
      searchBtn: remisionesSearchBtn,
      clearBtn: remisionesClearBtn,
      prevBtn: remisionesPrevBtn,
      nextBtn: remisionesNextBtn,
    },
  })
  : null;
const qcModule = window.FormixModules && typeof window.FormixModules.createQcSyncModule === "function"
  ? window.FormixModules.createQcSyncModule({
    state,
    elements: {
      editorQcMeta,
      qcLinkedStamp,
      editorQcBody,
      qcBody,
      saveQcBtn,
      saveQcHumidityBtn,
    },
    QC_AGGREGATES,
    QC_FIELDS,
    apiFetch,
    toNumber,
    setQcDirty,
    setStatus,
    normalizeQualityValues,
    createDefaultQuality,
    renderDoser: renderDosificador,
    renderRecipeAndCosts,
  })
  : null;
const usersModule = window.FormixModules && typeof window.FormixModules.createUsersModule === "function"
  ? window.FormixModules.createUsersModule({
    state,
    escapeHtml,
    uiConfirm,
    uiToastHost,
    uiDialogHost,
  })
  : null;
const inventoryModule = window.FormixModules && typeof window.FormixModules.createInventoryModule === "function"
  ? window.FormixModules.createInventoryModule({
    state,
    escapeHtml,
    formatNum,
    canAccessView,
    switchView,
    tabInventario,
    uiDialogHost,
    brandLogoUrl: BRAND_LOGO_URL,
    brandName: BRAND_NAME,
    brandTagline: BRAND_TAGLINE,
    plantName: PLANT_NAME,
    getTodayCancun,
    getFullTodayCancun,
    renderDoser: renderDosificador,
    uiConfirm,
    pushToast,
  })
  : null;
const fleetModule = window.FormixModules && typeof window.FormixModules.createFleetModule === "function"
  ? window.FormixModules.createFleetModule({
    state,
    escapeHtml,
    formatNum,
    canAccessView,
    switchView,
    vehiclesBody,
    fuelBody,
    fuelVehicleSelect,
    fleetSummaryBody,
    tabFlotilla,
    getTodayCancun,
    getFullTodayCancun,
    pushToast,
  })
  : null;
const qcLabModule = window.FormixModules && typeof window.FormixModules.createQcLabModule === "function"
  ? window.FormixModules.createQcLabModule({
    state,
    apiFetch,
    setStatus,
    getTodayCancun,
  })
  : null;

function getModDateColIndex() {
  const aliases = new Set(["fechamodif", "fechamodificacion", "modificado", "ultimafecha"]);
  for (let i = 0; i < state.headers.length; i += 1) {
    const key = normalizeHeader(splitHeaderName(state.headers[i]).name || state.headers[i]);
    if (aliases.has(key)) return i;
  }
  return -1;
}

function ensureModDateColumn() {
  let idx = getModDateColIndex();
  if (idx < 0) {
    state.headers.push(MOD_DATE_HEADER);
    state.rows.forEach((row) => row.push(""));
    idx = state.headers.length - 1;
  } else {
    state.rows.forEach((row) => {
      if (row.length < state.headers.length) row.push("");
    });
  }
  return idx;
}

function setRowModifiedDate(rowIndex) {
  const colIndex = ensureModDateColumn();
  if (!state.rows[rowIndex]) return;
  state.rows[rowIndex][colIndex] = nowStamp();
}

function setStatus(message, tone = "ok") {
  if (statusBar) {
    statusBar.textContent = message;
    statusBar.setAttribute("data-tone", tone);
  }
  if (tone === "warn" || tone === "err") pushToast(message, tone);
}

function canAccessView(view) {
  return state.auth.allowedViews.includes(view);
}

function defaultView() {
  const preferredOrder = ["dosificador", "consulta", "remisiones", "editor", "inventario", "flotilla", "laboratorio", "usuarios"];
  const preferred = preferredOrder.find((view) => canAccessView(view));
  if (preferred) return preferred;
  return state.auth.allowedViews[0] || "consulta";
}

function applyRoleAccessUi() {
  tabEditor.style.display = canAccessView("editor") ? "" : "none";
  tabConsulta.style.display = canAccessView("consulta") ? "" : "none";
  tabDosificador.style.display = canAccessView("dosificador") ? "" : "none";
  if (tabRemisiones) tabRemisiones.style.display = canAccessView("remisiones") ? "" : "none";
  if (tabFlotilla) tabFlotilla.style.display = canAccessView("flotilla") ? "" : "none";
  if (tabInventario) tabInventario.style.display = canAccessView("inventario") ? "" : "none";
  if (tabLaboratorio) tabLaboratorio.style.display = canAccessView("laboratorio") ? "" : "none";
  if (tabUsuarios) tabUsuarios.style.display = canAccessView("usuarios") ? "" : "none";
  if (auditBtn) auditBtn.style.display = state.auth.canEdit ? "" : "none";
  if (backupCreateBtn) backupCreateBtn.style.display = state.auth.canEdit ? "" : "none";
  if (backupRestoreBtn) backupRestoreBtn.style.display = state.auth.role === "administrador" ? "" : "none";
  const clearKardexBtn = document.getElementById("clearKardexBtn");
  if (clearKardexBtn) clearKardexBtn.style.display = state.auth.role === "administrador" ? "" : "none";
  if (saveQcHumidityBtn) {
    saveQcHumidityBtn.style.display = state.auth.canEditQcHumidity ? "" : "none";
  }
  const toleranceEditable = canEditDoserTolerances();
  [tolCementoInput, tolAgregadosInput, tolAguaInput, tolAditivoInput].forEach((input) => {
    if (!input) return;
    input.disabled = !toleranceEditable;
    input.classList.toggle("is-locked", !toleranceEditable);
  });
  [
    paramCementoPespInput,
    paramAirePctInput,
    paramPasa200PctInput,
    paramPxlPctInput,
    paramDensidadAggInput,
  ].forEach((input) => {
    if (!input) return;
    input.disabled = !toleranceEditable;
    input.classList.toggle("is-locked", !toleranceEditable);
  });
  if (saveDoserParamsBtn) {
    saveDoserParamsBtn.style.display = canAccessView("dosificador") ? "" : "none";
    saveDoserParamsBtn.disabled = !toleranceEditable;
  }
  if (tolAccessNote) {
    tolAccessNote.textContent = toleranceEditable
      ? "Ajustables por tipo de material (editable por administrador y jefe-de-planta)"
      : "Solo administrador y jefe-de-planta pueden editar tolerancias.";
  }
}

function refreshSaveState() {
  const hasChanges = state.dirty || state.qcDirty;
  saveState.textContent = hasChanges ? "Cambios sin guardar" : "Sin cambios";
  saveState.style.color = hasChanges ? "#b67712" : "#4b627a";
}

function setDirty(value) {
  state.dirty = value;
  refreshSaveState();
}

function setQcDirty(value) {
  state.qcDirty = value;
  refreshSaveState();
}

function setConsultaStep(step) {
  if (consultaModule) {
    consultaModule.setStep(step);
  }
}

function switchView(view) {
  if (!canAccessView(view)) {
    setStatus("No tienes permisos para acceder a esta pestaña.", "warn");
    return;
  }
  state.view = view;
  const isEditor = view === "editor";
  const isConsulta = view === "consulta";
  const isDoser = view === "dosificador";
  const isRemisiones = view === "remisiones";
  const isFleet = view === "flotilla";
  const isInv = view === "inventario";
  const isLab = view === "laboratorio";
  const isUsers = view === "usuarios";
  editorView.classList.toggle("is-hidden", !isEditor);
  consultaView.classList.toggle("is-hidden", !isConsulta);
  dosificadorView.classList.toggle("is-hidden", !isDoser);
  if (remisionesView) remisionesView.classList.toggle("is-hidden", !isRemisiones);
  if (flotillaView) flotillaView.classList.toggle("is-hidden", !isFleet);
  if (inventarioView) inventarioView.classList.toggle("is-hidden", !isInv);
  if (laboratorioView) laboratorioView.classList.toggle("is-hidden", !isLab);
  if (usuariosView) usuariosView.classList.toggle("is-hidden", !isUsers);
  tabEditor.classList.toggle("view-tab--active", isEditor);
  tabConsulta.classList.toggle("view-tab--active", isConsulta);
  tabDosificador.classList.toggle("view-tab--active", isDoser);
  if (tabRemisiones) tabRemisiones.classList.toggle("view-tab--active", isRemisiones);
  if (tabFlotilla) tabFlotilla.classList.toggle("view-tab--active", isFleet);
  if (tabInventario) tabInventario.classList.toggle("view-tab--active", isInv);
  if (tabLaboratorio) tabLaboratorio.classList.toggle("view-tab--active", isLab);
  if (tabUsuarios) tabUsuarios.classList.toggle("view-tab--active", isUsers);
  if (isConsulta) {
    if (consultaModule) {
      consultaModule.load();
    }
  }
  if (isEditor) {
    if (editorModule) {
      editorModule.load();
    }
  }
  if (isDoser) {
    if (doserModule) {
      doserModule.load();
    } else {
      renderDosificador();
      loadRemisiones();
      loadGlobalRecipes();
    }
  }
  if (isRemisiones && remisionesModule) remisionesModule.load();
  if (isFleet && fleetModule) fleetModule.load();
  if (isInv && inventoryModule) inventoryModule.load();
  if (isLab && qcLabModule) qcLabModule.load();
  if (isUsers && usersModule) usersModule.load();
}

function compareValues(a, b) {
  const numA = Number(a);
  const numB = Number(b);
  const aIsNum = !Number.isNaN(numA) && normalize(a) !== "";
  const bIsNum = !Number.isNaN(numB) && normalize(b) !== "";
  if (aIsNum && bIsNum) return numA - numB;
  return a.toString().localeCompare(b.toString(), "es", { sensitivity: "base", numeric: true });
}

async function fetchFamiliesSummary() {
  try {
    const resp = await apiFetch("/api/families/summary");
    const res = await resp.json();
    if (res.ok) {
      state.doser.familiesSummary = res.summary || [];
    }
  } catch (err) {
    console.error("Error fetching families summary:", err);
  }
}

function renderFamiliesBoard() {
  const board = document.getElementById("familiasBoard");
  if (!board) return;
  board.innerHTML = "";

  const summary = state.doser.familiesSummary || [];
  if (summary.length === 0) {
    board.textContent = "Cargando familias globalmente...";
    fetchFamiliesSummary().then(() => renderFamiliesBoard());
    return;
  }

  // Agrupar por FAMILIA ahora
  const groups = new Map();
  summary.forEach(item => {
    if (!groups.has(item.family)) groups.set(item.family, []);
    groups.get(item.family).push(item);
  });

  [...groups.entries()]
    .sort((a, b) => compareValues(a[0], b[0]))
    .forEach(([family, tmaItems]) => {
      const card = document.createElement("div");
      card.className = "family-col";
      // Seleccionar el archivo del primer item para esta familia
      const targetFile = tmaItems[0]?.file;

      const h3 = document.createElement("h3");
      h3.textContent = `Familia ${family}`;
      const ul = document.createElement("ul");

      tmaItems.sort((a, b) => compareValues(a.tma, b.tma))
        .forEach(item => {
          const li = document.createElement("li");
          li.innerHTML = `<span class="family-link">T.M.A. ${item.tma}</span> <span class="meta">(${item.count})</span>`;
          ul.appendChild(li);
        });

      card.addEventListener("click", async () => {
        if (!targetFile) return;
        if (state.file !== targetFile) {
          setStatus(`Cargando familia ${family}...`, "info");
          try {
            const resp = await apiFetch("/api/select", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ file: targetFile })
            });
            const res = await resp.json();
            if (res.ok) {
              if (editorModule) await editorModule.loadData();
              const qFamily = document.getElementById("qFamily");
              const qTma = document.getElementById("qTma");
              if (qFamily) qFamily.value = family;
              if (qTma) qTma.value = ""; // No filtrar por TMA
              runQuery();
            }
          } catch (err) {
            setStatus("Error al cargar familia: " + err.message, "err");
          }
        } else {
          const qFamily = document.getElementById("qFamily");
          const qTma = document.getElementById("qTma");
          if (qFamily) qFamily.value = family;
          if (qTma) qTma.value = ""; // No filtrar por TMA
          runQuery();
        }
      });

      card.appendChild(h3);
      card.appendChild(ul);
      board.appendChild(card);
    });
}

function renderRecipeAndCosts(row) {
  if (consultaModule) {
    consultaModule.renderRecipeAndCosts(row);
  }
}

function averagePV(componentName) {
  if (!isAggregateComponent(componentName)) return null;
  const q = getQualityFor(componentName);
  const pvs = toNumber(q.pvs);
  const pvc = toNumber(q.pvc);
  if (pvs > 0 && pvc > 0) return (pvs + pvc) / 2;
  if (pvs > 0) {
    console.warn(`[QC] ${componentName}: PVC es 0, usando solo PVS (${pvs})`);
    return pvs;
  }
  if (pvc > 0) {
    console.warn(`[QC] ${componentName}: PVS es 0, usando solo PVC (${pvc})`);
    return pvc;
  }
  return null;
}

function renderCostTable(recipeItems) {
  if (consultaModule) {
    consultaModule.renderCostTable(recipeItems);
    return;
  }
  costBody.innerHTML = "";
  const aggregateMap = buildAggregateColumnMap();
  recipeItems.forEach((item) => {
    const tr = document.createElement("tr");
    const isAgg = isAggregateComponent(item.name);
    const ov = state.quoteMode ? (state.quoteOverrides[item.name] || {}) : {};
    const qty = effectiveQty(item);
    const unitCost = state.unitCosts[item.name] || 0;
    const haulCost = state.haulCosts[item.name] || 0;
    const pvValue = isAgg ? (effectivePV(item.name) || densityFor(item.name, "kg")) : densityFor(item.name, item.unit);
    const m3 = isAgg && pvValue > 0 ? qty / pvValue : 0;
    const subtotal = isAgg ? m3 * (unitCost + haulCost) : unitCost * qty;

    // Material label
    const materialLabel = isAgg ? (ov.material || getAggregateLabel(item.name) || "-") : "-";
    const materialCell = state.quoteMode && isAgg
      ? `<input class="quote-input quote-material" type="text" value="${escapeHtml(materialLabel)}" placeholder="Nombre material">`
      : escapeHtml(materialLabel);

    // Qty cell
    const qtyCell = state.quoteMode
      ? `<input class="quote-input quote-qty" type="number" min="0" step="0.01" value="${qty.toFixed(2)}">`
      : escapeHtml(formatNum(qty));

    // PV cell
    const pvDisplay = isAgg ? pvValue.toFixed(0) : "-";
    const pvCell = state.quoteMode && isAgg
      ? `<input class="quote-input quote-pv" type="number" min="0" step="1" value="${pvValue.toFixed(0)}" placeholder="PV">`
      : pvDisplay;

    const m3Text = isAgg ? formatVol(m3) : "-";
    const haulCell = isAgg
      ? `<div class="money-field"><span class="money-field__symbol">$</span><input class="haul-input" type="number" min="0" step="0.01" value="${haulCost.toFixed(
        2
      )}" title="Costo de transporte por m³ del agregado (del banco a la planta)" aria-label="Acarreo por m³"></div>`
      : "-";
    tr.innerHTML = `
      <td>${escapeHtml(item.name)}</td>
      <td>${materialCell}</td>
      <td>${qtyCell}</td>
      <td class="num">${pvCell}</td>
      <td>${escapeHtml(m3Text)}</td>
      <td>${escapeHtml(item.unit)}</td>
      <td>${haulCell}</td>
      <td><div class="money-field"><span class="money-field__symbol">$</span><input class="cost-input" type="number" min="0" step="0.01" value="${unitCost.toFixed(2)}"></div></td>
      <td class="cost-sub">${escapeHtml(formatMoney(subtotal))}</td>
    `;

    const costInput = tr.querySelector(".cost-input");
    const haulInput = tr.querySelector(".haul-input");
    const subCell = tr.querySelector(".cost-sub");

    const recalcRow = () => {
      const q = effectiveQty(item);
      const pv = isAgg ? (effectivePV(item.name) || densityFor(item.name, "kg")) : densityFor(item.name, item.unit);
      const uc = state.unitCosts[item.name] || 0;
      const hc = state.haulCosts[item.name] || 0;
      const mv = isAgg && pv > 0 ? q / pv : 0;
      const st = isAgg ? mv * (uc + hc) : uc * q;
      const pvTd = tr.querySelector(".num");
      const m3Td = tr.children[4];
      const qtyTd = tr.children[2];
      if (pvTd && !state.quoteMode) pvTd.textContent = isAgg ? pv.toFixed(0) : "-";
      if (m3Td) m3Td.textContent = isAgg ? formatVol(mv) : "-";
      subCell.textContent = formatMoney(st);
      updateCostTotals(recipeItems);
    };

    costInput.addEventListener("input", () => {
      state.unitCosts[item.name] = toNumber(costInput.value);
      recalcRow();
    });
    if (haulInput) {
      haulInput.addEventListener("input", () => {
        state.haulCosts[item.name] = toNumber(haulInput.value);
        recalcRow();
      });
    } else {
      state.haulCosts[item.name] = 0;
    }

    // Quote mode editable fields
    if (state.quoteMode) {
      const matInput = tr.querySelector(".quote-material");
      const qtyInput = tr.querySelector(".quote-qty");
      const pvInput = tr.querySelector(".quote-pv");
      if (matInput) {
        matInput.addEventListener("input", () => {
          if (!state.quoteOverrides[item.name]) state.quoteOverrides[item.name] = {};
          state.quoteOverrides[item.name].material = matInput.value;
        });
      }
      if (qtyInput) {
        qtyInput.addEventListener("input", () => {
          if (!state.quoteOverrides[item.name]) state.quoteOverrides[item.name] = {};
          state.quoteOverrides[item.name].qty = toNumber(qtyInput.value);
          recalcRow();
        });
      }
      if (pvInput) {
        pvInput.addEventListener("input", () => {
          if (!state.quoteOverrides[item.name]) state.quoteOverrides[item.name] = {};
          state.quoteOverrides[item.name].pv = toNumber(pvInput.value);
          recalcRow();
        });
      }
    }

    costBody.appendChild(tr);
  });
  updateCostTotals(recipeItems);
}

function buildCostRowsForReport(recipeItems) {
  return recipeItems.map((item) => {
    const isAgg = isAggregateComponent(item.name);
    const m3 = isAgg ? volumeM3ForCost(item) : null;
    const unitCost = state.unitCosts[item.name] || 0;
    const haulCost = isAgg ? state.haulCosts[item.name] || 0 : 0;
    const subtotal = subtotalForCost(item);
    return {
      name: item.name,
      qty: item.qty,
      m3,
      unit: item.unit,
      haul: isAgg ? haulCost : null,
      haulSubtotal: isAgg && m3 !== null ? m3 * haulCost : 0,
      unitCost,
      subtotal,
    };
  });
}

function exportConsultaReport() {
  if (consultaModule) {
    consultaModule.exportReport();
    return;
  }
  const selectedIndex = state.selectedQueryRow;
  const row = typeof selectedIndex === "number" ? state.rows[selectedIndex] : null;
  if (!row) {
    setStatus("Selecciona una mezcla en Consulta Mix para exportar el reporte.", "warn");
    return;
  }

  const formula = valueByKey(row, "formula") || "-";
  const fc = valueByKey(row, "fc") || "-";
  const edad = valueByKey(row, "edad") || "-";
  const tipo = valueByKey(row, "tipo") || "-";
  const tma = valueByKey(row, "tma") || "-";
  const rev = valueByKey(row, "rev") || "-";
  const comp = valueByKey(row, "comp") || "-";
  const modDate = getRowModDate(row) || "-";
  const qcDate = state.qcUpdatedAt || "-";
  const reportDate = nowStamp();

  const recipeItems = normalizeConsultaRecipeItems(extractRecipe(row));
  const recipeTotal = recipeItems.reduce((acc, item) => acc + item.qty, 0);
  const adjustedForCost = adjustRecipeByQuality(recipeItems, 1);
  const costRows = buildCostRowsForReport(adjustedForCost);
  const totalMaterials = adjustedForCost.reduce((acc, item) => acc + materialSubtotalForCost(item), 0);
  const totalHaul = costRows.reduce((acc, item) => acc + (item.haulSubtotal || 0), 0);
  const totalCost = totalMaterials + totalHaul;
  const aggregateMap = buildAggregateColumnMap();

  const recipeRowsHtml = recipeItems
    .map(
      (item) => {
        const componentLabel = reportComponentLabel(item.name, aggregateMap);
        const volText = isAggregateComponent(item.name) ? formatVol(item.volume) : "-";
        return `
        <tr>
          <td>${escapeHtml(componentLabel)}</td>
          <td class="num">${escapeHtml(formatNum(item.qty))}</td>
          <td>${escapeHtml(item.unit)}</td>
          <td class="num">${escapeHtml(volText)}</td>
        </tr>
      `;
      }
    )
    .join("");

  const costRowsHtml = costRows
    .map(
      (item) => {
        const componentLabel = reportComponentLabel(item.name, aggregateMap);
        const m3Text = item.m3 === null ? "-" : formatVol(item.m3);
        return `
        <tr>
          <td>${escapeHtml(componentLabel)}</td>
          <td class="num">${escapeHtml(formatNum(item.qty))}</td>
          <td class="num">${escapeHtml(m3Text)}</td>
          <td>${escapeHtml(item.unit)}</td>
          <td class="num">${item.haul === null ? "-" : escapeHtml(formatNum(item.haul))}</td>
          <td class="num">${escapeHtml(formatNum(item.unitCost))}</td>
          <td class="num">${escapeHtml(formatMoney(item.subtotal))}</td>
        </tr>
      `;
      }
    )
    .join("");


  const html = `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Reporte Mix - ${escapeHtml(formula)}</title>
  <style>
    @page { size: letter landscape; margin: 8mm; }
    body { font-family: "Segoe UI", Tahoma, Arial, sans-serif; margin: 0; color: #1a2c3f; font-size: 11px; }
    .page { min-height: 100%; }
    .head { border-bottom: 2px solid #0b4f8a; padding-bottom: 6px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
    .head-brand { display: inline-flex; align-items: center; gap: 8px; }
    .head-logo { width: 46px; height: 46px; object-fit: contain; border: 1px solid #d5e1ee; border-radius: 8px; background: #fff; padding: 4px; }
    .head h1 { margin: 0; font-size: 18px; line-height: 1.1; }
    .head .brand { margin: 3px 0 0; color: #3b5572; font-size: 10.5px; font-weight: 600; }
    .head .head-meta { margin: 0; color: #3b5572; font-size: 11px; text-align: right; }
    .meta { display: grid; grid-template-columns: repeat(5, minmax(95px, 1fr)); gap: 5px; margin-bottom: 8px; }
    .meta .item { border: 1px solid #d6e0eb; border-radius: 6px; padding: 5px 6px; background: #f8fbff; }
    .meta .k { font-size: 9px; color: #4d667f; text-transform: uppercase; line-height: 1; }
    .meta .v { font-size: 11px; font-weight: 700; margin-top: 2px; line-height: 1.2; }
    .main-grid { display: grid; grid-template-columns: 36% 64%; gap: 8px; align-items: start; }
    .section { margin-top: 0; }
    .section h2 { margin: 0 0 6px; font-size: 13px; color: #0d3762; line-height: 1.1; }
    table { width: 100%; border-collapse: collapse; margin-top: 0; table-layout: fixed; }
    th, td { border: 1px solid #dce5ef; padding: 4px 5px; font-size: 10px; line-height: 1.2; }
    th { background: #edf4fb; text-align: left; }
    td.num { text-align: right; }
    .cost-table th:nth-child(1), .cost-table td:nth-child(1) { width: 22%; }
    .cost-table th:nth-child(2), .cost-table td:nth-child(2) { width: 13%; }
    .cost-table th:nth-child(3), .cost-table td:nth-child(3) { width: 10%; }
    .cost-table th:nth-child(4), .cost-table td:nth-child(4) { width: 10%; }
    .cost-table th:nth-child(5), .cost-table td:nth-child(5) { width: 12%; }
    .cost-table th:nth-child(6), .cost-table td:nth-child(6) { width: 14%; }
    .cost-table th:nth-child(7), .cost-table td:nth-child(7) { width: 19%; }
    .totals { margin-top: 6px; text-align: right; font-size: 13px; font-weight: 800; color: #123b66; }
    .totals-sub { margin-top: 4px; text-align: right; font-size: 12px; font-weight: 700; color: #1f4e7b; }
    .sign { margin-top: 10px; border-top: 1px solid #d3dfec; padding-top: 6px; text-align: center; color: #264767; font-weight: 700; font-size: 11px; }
    @media print {
      html, body { width: 100%; height: 100%; }
      * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .page { break-inside: avoid; }
      .section { break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="head">
      <div class="head-brand">
        <img class="head-logo" src="${escapeHtml(BRAND_LOGO_URL)}" alt="${escapeHtml(BRAND_NAME)}">
        <div>
          <h1>Reporte de Consulta Mix</h1>
          <p class="brand">${escapeHtml(BRAND_NAME)}</p>
        </div>
      </div>
      <p class="head-meta">Generado: ${escapeHtml(reportDate)} | Archivo: ${escapeHtml(state.file || "-")}</p>
    </div>

    <div class="meta">
      <div class="item"><div class="k">Formula</div><div class="v">${escapeHtml(formula)}</div></div>
      <div class="item"><div class="k">f'c</div><div class="v">${escapeHtml(fc)}</div></div>
      <div class="item"><div class="k">Edad</div><div class="v">${escapeHtml(edad)}</div></div>
      <div class="item"><div class="k">Tipo</div><div class="v">${escapeHtml(tipo)}</div></div>
      <div class="item"><div class="k">TMA</div><div class="v">${escapeHtml(tma)}</div></div>
      <div class="item"><div class="k">Rev</div><div class="v">${escapeHtml(rev)}</div></div>
      <div class="item"><div class="k">Comp</div><div class="v">${escapeHtml(comp)}</div></div>
      <div class="item"><div class="k">Fecha Modif</div><div class="v">${escapeHtml(modDate)}</div></div>
      <div class="item"><div class="k">QC</div><div class="v">${escapeHtml(qcDate)}</div></div>
      <div class="item"><div class="k">Sub-Total Acarreo m³</div><div class="v">${escapeHtml(formatMoney(totalHaul))}</div></div>
      <div class="item"><div class="k">Sub-Total Materiales m³</div><div class="v">${escapeHtml(formatMoney(totalMaterials))}</div></div>
      <div class="item"><div class="k">Total por m³</div><div class="v">${escapeHtml(formatMoney(totalCost))}</div></div>
    </div>

    <section class="main-grid">
      <article class="section">
        <h2>Receta</h2>
        <table>
          <thead>
            <tr>
              <th>Componente</th>
              <th>Cantidad</th>
              <th>Unidad</th>
              <th>Vol. Est. m³</th>
            </tr>
          </thead>
          <tbody>${recipeRowsHtml}</tbody>
        </table>
        <div class="totals">Peso por m³: ${escapeHtml(formatNum(recipeTotal))}</div>
      </article>

      <article class="section">
        <h2>Costos por m³</h2>
        <table class="cost-table">
          <thead>
            <tr>
              <th>Componente</th>
              <th>Cant. Final</th>
              <th>m³</th>
              <th>U.M.</th>
              <th>Acarreo ($)</th>
              <th>Costo Unit. ($)</th>
              <th>Subtotal</th>
            </tr>
          </thead>
          <tbody>${costRowsHtml}</tbody>
        </table>
        <div class="totals-sub">Sub-Total acarreo m³: ${escapeHtml(formatMoney(totalHaul))}</div>
        <div class="totals-sub">Sub-Total materiales m³: ${escapeHtml(formatMoney(totalMaterials))}</div>
        <div class="totals">Total por m³: ${escapeHtml(formatMoney(totalCost))}</div>
      </article>
    </section>

    <div class="sign">${escapeHtml(BRAND_TAGLINE)} - Disena-Dosifica-Calcula</div>
  </div>
</body>
</html>`;

  const win = window.open("", "_blank");
  if (!win) {
    setStatus("El navegador bloqueo la ventana del reporte. Habilita pop-ups e intenta de nuevo.", "warn");
    return;
  }
  win.document.open();
  win.document.write(html);
  win.document.close();
  setStatus("Reporte generado. Usa Imprimir para guardarlo en PDF.", "ok");
}

function buildDoserReportSnapshot() {
  return doserModule ? doserModule.buildReportSnapshot() : null;
}

function normalizeDoserReportSnapshot(raw, fallback = {}) {
  return doserModule ? doserModule.normalizeReportSnapshot(raw, fallback) : {};
}

function buildDoserReportHtml(rawSnapshot, reportDate) {
  if (doserModule) {
    return doserModule.buildReportHtml(rawSnapshot, reportDate);
  }
  const snap = normalizeDoserReportSnapshot(rawSnapshot, {
    file: state.file || "-",
    qcUpdatedAt: state.qcUpdatedAt || "-",
  });

  const qcRowsHtml = QC_AGGREGATES.map((agg) => {
    const q = snap.qc[agg] || {};
    return `
      <tr>
        <td>${escapeHtml(agg)}</td>
        <td class="num">${escapeHtml(formatNum(q.pvs || 0))}</td>
        <td class="num">${escapeHtml(formatNum(q.pvc || 0))}</td>
        <td class="num">${escapeHtml(formatNum(q.densidad || 0))}</td>
        <td class="num">${escapeHtml(formatNum(q.absorcion || 0))}</td>
        <td class="num">${escapeHtml(formatNum(q.humedad || 0))}</td>
      </tr>
    `;
  }).join("");

  const tolRowsHtml = `
    <tr><td>Cemento</td><td class="num">${escapeHtml(formatNum(snap.tolerances.cemento))}%</td></tr>
    <tr><td>Agregados</td><td class="num">${escapeHtml(formatNum(snap.tolerances.agregados))}%</td></tr>
    <tr><td>Agua</td><td class="num">${escapeHtml(formatNum(snap.tolerances.agua))}%</td></tr>
    <tr><td>Aditivo</td><td class="num">${escapeHtml(formatNum(snap.tolerances.aditivo))}%</td></tr>
  `;

  const paramsRowsHtml = `
    <tr><td>Peso esp. cemento</td><td class="num">${escapeHtml(formatNum(snap.doserParams.cemento_pesp || 0))}</td></tr>
    <tr><td>Aire (%)</td><td class="num">${escapeHtml(formatNum(snap.doserParams.aire_pct || 0))}</td></tr>
    <tr><td>Pasa malla 200 (%)</td><td class="num">${escapeHtml(formatNum(snap.doserParams.pasa_malla_200_pct || 0))}</td></tr>
    <tr><td>PxL pond. (%)</td><td class="num">${escapeHtml(formatNum(snap.doserParams.pxl_pond_pct || 0))}</td></tr>
    <tr><td>Densidad agg fallback</td><td class="num">${escapeHtml(formatNum(snap.doserParams.densidad_agregado_fallback || 0))}</td></tr>
  `;

  const recipeRowsHtml = snap.recipe
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.name)}</td>
          <td class="num">${escapeHtml(formatNum(item.qty))}</td>
          <td>${escapeHtml(item.unit)}</td>
        </tr>
      `
    )
    .join("");

  const theoreticalDetailedRowsHtml = (snap.theoreticalDetailed || [])
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.name)}</td>
          <td class="num">${escapeHtml(formatNum(item.designA || 0))}</td>
          <td class="num">${escapeHtml(formatNum(item.designSss || 0))}</td>
          <td class="num">${escapeHtml(formatNum(item.freeWater || 0))}</td>
          <td class="num">${escapeHtml(formatNum(item.absVolume || 0))}</td>
          <td class="num">${escapeHtml(formatNum(item.designReal || 0))}</td>
          <td class="num">${escapeHtml(formatNum(item.trialLoad || 0))}</td>
          <td>${escapeHtml(item.trialUnit || item.unit || "-")}</td>
          <td>${escapeHtml(item.note || "-")}</td>
        </tr>
      `
    )
    .join("");
  const theoreticalRowsHtml = theoreticalDetailedRowsHtml || snap.theoretical
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.name)}</td>
          <td class="num">${escapeHtml(formatNum(item.qty || 0))}</td>
          <td class="num">-</td>
          <td class="num">-</td>
          <td class="num">-</td>
          <td class="num">-</td>
          <td class="num">${escapeHtml(formatNum(item.qty || 0))}</td>
          <td>${escapeHtml(item.unit || "-")}</td>
          <td>-</td>
        </tr>
      `
    )
    .join("");

  const realRowsHtml = snap.realRows
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.name)}</td>
          <td>${escapeHtml(item.material_name || "-- Sin descontar --")}</td>
          <td class="num">${escapeHtml(formatNum(item.theoretical))}</td>
          <td class="num">${escapeHtml(formatNum(item.real))}</td>
          <td class="num">${item.diff >= 0 ? "+" : ""}${escapeHtml(formatNum(item.diff))}</td>
          <td class="num">${escapeHtml(formatNum(item.tolerance))}%</td>
          <td class="${item.status === "OK" ? "ok" : "bad"}">${escapeHtml(item.status)}</td>
        </tr>
      `
    )
    .join("");

  return `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Reporte Dosificador - ${escapeHtml(snap.formula)}</title>
  <style>
    @page { size: A4 landscape; margin: 0; }
    html, body { width: 297mm; height: 210mm; }
    * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    body { font-family: "Segoe UI", Tahoma, Arial, sans-serif; margin: 0; color: #1a2c3f; font-size: 11px; line-height: 1.2; }
    .sheet { width: 100%; min-height: 100%; padding: 3mm 4mm; }
    .head { border-bottom: 1px solid #0b4f8a; margin-bottom: 6px; padding-bottom: 4px; display: flex; justify-content: space-between; align-items: center; gap: 10px; }
    .head-brand { display: inline-flex; align-items: center; gap: 8px; }
    .head-logo { width: 44px; height: 44px; object-fit: contain; border: 1px solid #d5e1ee; border-radius: 8px; background: #fff; padding: 4px; }
    .head h1 { margin: 0; font-size: 16px; color: #0d3762; }
    .head .brand { margin: 2px 0 0; color: #39546e; font-size: 10px; font-weight: 600; }
    .head .sub { margin: 0; color: #39546e; font-size: 10.5px; text-align: right; }
    .meta-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 6px; }
    .meta-table th, .meta-table td { border: 1px solid #dce5ef; padding: 3px 5px; }
    .meta-table th { background: #edf4fb; text-align: left; width: 9%; font-weight: 600; }
    .meta-table td { width: 16%; font-weight: 600; color: #153958; }
    .grid-2 { display: grid; grid-template-columns: 1.45fr 1fr; gap: 6px; margin-bottom: 6px; }
    .grid-2.equal { grid-template-columns: 1fr 1fr; }
    .panel { border: 1px solid #dce5ef; border-radius: 6px; padding: 4px; break-inside: avoid; }
    .panel h2 { margin: 0 0 4px; font-size: 12px; color: #0d3762; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th, td { border: 1px solid #dce5ef; padding: 3px 5px; vertical-align: middle; }
    th { background: #edf4fb; text-align: left; font-size: 10.5px; font-weight: 700; }
    td { font-size: 10.5px; }
    td.num, th.num { text-align: right; }
    .total-line { margin-top: 3px; padding-top: 3px; border-top: 1px dashed #ccd8e6; text-align: right; font-weight: 700; color: #123b66; }
    .ok { color: #1f7a42; font-weight: 700; }
    .bad { color: #b9362d; font-weight: 700; }
    .sign { margin-top: 8px; border-top: 1px solid #d3dfec; padding-top: 5px; text-align: center; color: #264767; font-weight: 600; font-size: 10.5px; }
    .nowrap { white-space: nowrap; }
    @media print {
      html, body { margin: 0 !important; padding: 0 !important; }
      .sheet { break-inside: avoid; page-break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="sheet">
    <div class="head">
      <div class="head-brand">
        <img class="head-logo" src="${escapeHtml(BRAND_LOGO_URL)}" alt="${escapeHtml(BRAND_NAME)}">
        <div>
          <h1>Reporte de Dosificador</h1>
          <p class="brand">${escapeHtml(BRAND_NAME)}</p>
        </div>
      </div>
      <p class="sub">Generado: ${escapeHtml(reportDate)} | Archivo: ${escapeHtml(snap.file)}</p>
    </div>

    <table class="meta-table">
      <tbody>
        <tr>
          <th>Remision</th><td>${escapeHtml(snap.remisionNo)}</td>
          <th>Cliente</th><td>${escapeHtml(snap.cliente)}</td>
          <th>Ubicación</th><td>${escapeHtml(snap.ubicacion)}</td>
          <th>Formula</th><td>${escapeHtml(snap.formula)}</td>
        </tr>
        <tr>
          <th>f'c</th><td>${escapeHtml(snap.fc)}</td>
          <th>Tipo</th><td>${escapeHtml(snap.tipo)}</td>
          <th>Colocacion</th><td>${escapeHtml(snap.coloc)}</td>
          <th>T.M.A.</th><td>${escapeHtml(snap.tma)}</td>
          <th>Rev</th><td>${escapeHtml(snap.rev)}</td>
          <th>Comp</th><td>${escapeHtml(snap.comp)}</td>
        </tr>
        <tr>
          <th>Fecha Modif</th><td>${escapeHtml(snap.modDate)}</td>
          <th>Dosificacion</th><td class="nowrap">${escapeHtml(formatNum(snap.dose))} m<sup>3</sup></td>
          <th>QC</th><td>${escapeHtml(snap.qcUpdatedAt)}</td>
          <th></th><td></td>
        </tr>
      </tbody>
    </table>

    <div class="grid-2">
      <section class="panel">
        <h2>Datos de Control de Calidad</h2>
        <table>
          <thead>
            <tr>
              <th style="width:22%;">Agregado</th>
              <th class="num" style="width:15%;">PVS</th>
              <th class="num" style="width:15%;">PVC</th>
              <th class="num" style="width:16%;">Densidad</th>
              <th class="num" style="width:16%;">Absorcion</th>
              <th class="num" style="width:16%;">Humedad</th>
            </tr>
          </thead>
          <tbody>${qcRowsHtml}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>Tolerancias de Carga</h2>
        <table>
          <thead><tr><th>Material</th><th class="num">Tolerancia</th></tr></thead>
          <tbody>${tolRowsHtml}</tbody>
        </table>
        <h2 style="margin-top:6px;">Parametros de Calculo</h2>
        <table>
          <thead><tr><th>Parametro</th><th class="num">Valor</th></tr></thead>
          <tbody>${paramsRowsHtml}</tbody>
        </table>
      </section>
    </div>

    <div class="grid-2 equal">
      <section class="panel">
        <h2>Receta</h2>
        <table>
          <thead><tr><th style="width:50%;">Componente</th><th class="num" style="width:30%;">Cantidad</th><th style="width:20%;">Unidad</th></tr></thead>
          <tbody>${recipeRowsHtml}</tbody>
        </table>
        <div class="total-line">Peso aprox por m<sup>3</sup>: ${escapeHtml(formatNum(snap.recipeWeight))}</div>
      </section>
      <section class="panel">
        <h2>Carga Teorica Detallada</h2>
        <table>
          <thead>
            <tr>
              <th style="width:17%;">Componente</th>
              <th class="num" style="width:9%;">Diseño A</th>
              <th class="num" style="width:9%;">Diseño SSS</th>
              <th class="num" style="width:10%;">Agua libre H.R.</th>
              <th class="num" style="width:9%;">Vol. Abs.</th>
              <th class="num" style="width:9%;">Diseño H.R.</th>
              <th class="num" style="width:10%;">Mezcla Prueba</th>
              <th style="width:8%;">U.M.</th>
              <th style="width:19%;">Obs.</th>
            </tr>
          </thead>
          <tbody>${theoreticalRowsHtml}</tbody>
        </table>
        <div class="total-line">Peso teorico total: ${escapeHtml(formatNum(snap.theoreticalWeight))}</div>
        <div class="total-line">Rel. A/C: ${escapeHtml(formatNum(toNumber(snap.calcTotals.relAc || 0)))} | Vol. Abs. + Aire: ${escapeHtml(formatNum(toNumber(snap.calcTotals.absVolumeTotal || 0)))}</div>
      </section>
    </div>

    <section class="panel">
      <h2>Carga Real y Diferencial</h2>
      <table>
        <thead>
          <tr>
            <th style="width:18%;">Componente</th>
            <th style="width:20%;">Material</th>
            <th class="num" style="width:14%;">Teorica</th>
            <th class="num" style="width:14%;">Real</th>
            <th class="num" style="width:12%;">Diferencia</th>
            <th class="num" style="width:10%;">Tol. %</th>
            <th style="width:12%;">Estatus</th>
          </tr>
        </thead>
        <tbody>${realRowsHtml}</tbody>
      </table>
      <div class="total-line">Peso real total: ${escapeHtml(formatNum(snap.realWeight))}</div>
    </section>

    <div class="sign">${escapeHtml(BRAND_TAGLINE)} - Disena-Dosifica-Calcula</div>
  </div>
</body>
</html>`;
}

function openReportWindow(html, successMessage) {
  if (doserModule) {
    return doserModule.openReportWindow(html, successMessage);
  }
  const win = window.open("", "_blank");
  if (!win) {
    setStatus("El navegador bloqueo la ventana del reporte. Habilita pop-ups e intenta de nuevo.", "warn");
    return false;
  }
  win.document.open();
  win.document.write(html);
  win.document.close();
  if (successMessage) setStatus(successMessage, "ok");
  return true;
}

function exportDoserReport() {
  if (doserModule) {
    doserModule.exportReport();
    return;
  }
  const snap = buildDoserReportSnapshot();
  if (!snap) {
    setStatus("Selecciona una mezcla en Dosificador para exportar el reporte.", "warn");
    return;
  }
  const html = buildDoserReportHtml(snap, nowStamp());
  openReportWindow(html, "Reporte de dosificador generado. Usa Imprimir para guardarlo en PDF.");
}

async function openRemisionReport(remisionId) {
  if (doserModule) {
    await doserModule.openRemisionReport(remisionId);
    return;
  }
  try {
    const id = Number(remisionId);
    if (!Number.isFinite(id) || id <= 0) return setStatus("ID invalido.", "warn");
    const response = await apiFetch(`/api/remisiones/${encodeURIComponent(id)}`);
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "No se pudo cargar la remision.");
    }
    const snap = payload.snapshot && typeof payload.snapshot === "object" ? payload.snapshot : null;
    if (!snap) {
      throw new Error("La remision no tiene snapshot de reporte.");
    }
    const remisionNo = snap.remisionNo || snap.remision_no || payload.remision_no || "-";
    const normalized = normalizeDoserReportSnapshot(snap, {
      remisionNo,
      file: payload.file || state.file || "-",
      qcUpdatedAt: state.qcUpdatedAt || "-",
    });
    const html = buildDoserReportHtml(normalized, nowStamp());
    openReportWindow(html);
    setStatus(`Reporte de remision ${remisionNo} generado. Usa Imprimir para guardarlo en PDF.`, "ok");
  } catch (error) {
    setStatus(String(error), "err");
  }
}

function getQualityFor(componentName) {
  return (
    state.doser.quality[componentName] || {
      pvs: 0,
      pvc: 0,
      densidad: 0,
      absorcion: 0,
      humedad: 0,
    }
  );
}

function adjustRecipeByQuality(recipeItems, dose) {
  const safeDose = Math.max(0, toNumber(dose));
  const baseWater = recipeItems.find((item) => item.name === "Agua");
  let freeWaterCorrection = 0;

  const adjusted = recipeItems.map((item) => {
    let qty = item.qty * safeDose;
    if (isAggregateComponent(item.name)) {
      const q = getQualityFor(item.name);
      const abs = (q.absorcion || 0) / 100;
      const hum = (q.humedad || 0) / 100;
      const den = 1 + abs;
      qty = den > 0 ? (qty * (1 + hum)) / den : qty;
      freeWaterCorrection += item.qty * safeDose * ((q.humedad || 0) - (q.absorcion || 0)) / 100;
    }
    return { ...item, qty };
  });

  if (baseWater) {
    const waterItem = adjusted.find((item) => item.name === "Agua");
    if (waterItem) waterItem.qty = Math.max(0, waterItem.qty - freeWaterCorrection);
  }
  return adjusted;
}

function toleranceFor(componentName) {
  if (componentName === "Cemento") return state.doser.tolerances.cemento || 0;
  if (componentName === "Agua") return state.doser.tolerances.agua || 0;
  if (["Fino 1", "Fino 2", "Grueso 1", "Grueso 2"].includes(componentName)) {
    return state.doser.tolerances.agregados || 0;
  }
  return state.doser.tolerances.aditivo || 0;
}

function runDoserSearch() {
  if (!doserModule) return;
  doserModule.runSearch();
}

async function loadGlobalRecipes() {
  if (!doserModule) return;
  await doserModule.loadGlobalRecipes();
}

function fillDoserSelectorsGlobal() {
  if (!doserModule) return;
  doserModule.fillDoserSelectorsGlobal();
}

function fillDoserSelectors() {
  if (!doserModule) return;
  doserModule.fillDoserSelectors();
}

function renderDoserResults() {
  if (!doserModule) return;
  doserModule.renderResults();
}

async function selectDoserRecipe(entry) {
  if (!doserModule) return;
  await doserModule.selectRecipe(entry);
}

function renderRemisionList() {
  if (doserModule) {
    return doserModule.renderRemisionList();
  }
  if (!doserRemisionBody) return;
  doserRemisionBody.innerHTML = "";
  const items = Array.isArray(state.doser.remisiones) ? state.doser.remisiones : [];
  if (!items.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="11">Sin remisiones guardadas para esta fecha.</td>`;
    doserRemisionBody.appendChild(tr);
    if (remisionMeta) remisionMeta.textContent = "Remisiones: 0";
    return;
  }
  items.forEach((item) => {
    const snap = item.snapshot || {};
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(item.remision_no || "-")}</td>
      <td><span class="remision-cell remision-cell--formula" title="${escapeHtml(item.formula || "-")}">${escapeHtml(item.formula || "-")}</span></td>
      <td>${escapeHtml(item.fc || "-")}</td>
      <td>${escapeHtml(item.tma || "-")}</td>
      <td>${formatNum(item.dosificacion_m3 || 0)}</td>
      <td><span class="remision-cell remision-cell--client" title="${escapeHtml(snap.cliente || "-")}">${escapeHtml(snap.cliente || "-")}</span></td>
      <td><span class="remision-cell remision-cell--location" title="${escapeHtml(snap.ubicacion || "-")}">${escapeHtml(snap.ubicacion || "-")}</span></td>
      <td>${formatNum(item.peso_real_total || 0)}</td>
      <td><span class="remision-cell remision-cell--date" title="${escapeHtml(item.created_at || "-")}">${escapeHtml(item.created_at || "-")}</span></td>
      <td class="remision-actions" title="Archivo: ${escapeHtml(item.source_file || "-")} | Usuario: ${escapeHtml(item.created_by || "-")}">
        <button type="button" class="btn btn--secondary btn--small remision-report-btn">Reporte</button>
        ${state.auth.role === 'administrador' ? '<button type="button" class="btn btn--muted btn--small remision-edit-btn">Editar</button>' : ''}
        <button type="button" class="btn btn--danger btn--small remision-delete-btn">Eliminar</button>
      </td>
    `;
    const reportBtn = tr.querySelector(".remision-report-btn");
    if (reportBtn) reportBtn.addEventListener("click", () => openRemisionReport(item.id));
    const deleteBtn = tr.querySelector(".remision-delete-btn");
    if (deleteBtn) deleteBtn.addEventListener("click", () => deleteRemision(item.id, item.remision_no, item.source_file));
    const editBtn = tr.querySelector(".remision-edit-btn");
    if (editBtn) editBtn.addEventListener("click", () => openEditRemisionModal(item));
    doserRemisionBody.appendChild(tr);
  });
  if (remisionMeta) remisionMeta.textContent = `Remisiones: ${items.length}`;
}

async function loadRemisiones() {
  if (doserModule) {
    await doserModule.loadRemisiones();
    return;
  }
  if (!canAccessView("dosificador")) return;
  const filterDate = (remisionFilterDate && remisionFilterDate.value) ? remisionFilterDate.value : "";
  try {
    if (remisionMeta) remisionMeta.textContent = "Cargando remisiones...";
    const url = `/api/remisiones?limit=150${filterDate ? `&date=${filterDate}` : ""}`;
    const response = await apiFetch(url);
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || "No se pudo cargar remisiones.");
    state.doser.remisiones = Array.isArray(payload.items) ? payload.items : [];
  } catch (error) {
    state.doser.remisiones = [];
    console.error("loadRemisiones error:", error);
  }
  renderRemisionList();
}

window.openEditRemisionModal = function (item) {
  if (!item || !item.id) return;
  const modal = document.getElementById("editRemisionModal");
  if (!modal) return;
  document.getElementById("editRemisionId").value = item.id;
  document.getElementById("erNo").value = item.remision_no || "";
  document.getElementById("erFormula").value = item.formula || "";
  document.getElementById("erM3").value = item.dosificacion_m3 || 0;
  document.getElementById("erWeight").value = item.peso_real_total || 0;

  const snap = item.snapshot || {};
  document.getElementById("erCliente").value = snap.cliente || "";
  document.getElementById("erUbicacion").value = snap.ubicacion || "";

  // Formatear fecha para datetime-local (YYYY-MM-DDTHH:mm)
  if (item.created_at) {
    const dt = item.created_at.replace(' ', 'T').substring(0, 16);
    document.getElementById("erDate").value = dt;
  }

  modal.classList.remove("is-hidden");
  modal.setAttribute("aria-hidden", "false");
};

window.closeEditRemisionModal = function () {
  const modal = document.getElementById("editRemisionModal");
  if (modal) {
    modal.classList.add("is-hidden");
    modal.setAttribute("aria-hidden", "true");
  }
};

// Listener para el formulario de edición
document.addEventListener("DOMContentLoaded", () => {
  const editForm = document.getElementById("editRemisionForm");
  if (editForm) {
    editForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = document.getElementById("editRemisionId").value;
      const payload = {
        remision_no: document.getElementById("erNo").value,
        formula: document.getElementById("erFormula").value,
        cliente: document.getElementById("erCliente").value,
        ubicacion: document.getElementById("erUbicacion").value,
        dosificacion_m3: parseFloat(document.getElementById("erM3").value),
        peso_real_total: parseFloat(document.getElementById("erWeight").value),
        created_at: document.getElementById("erDate").value.replace('T', ' ') + ':00'
      };

      try {
        const res = await apiFetch(`/api/remisiones/${id}?file=${encodeURIComponent(state.file || "")}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.ok) {
          setStatus("Remisión actualizada correctamente.", "ok");
          closeEditRemisionModal();
          loadRemisiones();
          if (remisionesModule) remisionesModule.load();
        } else {
          throw new Error(data.error || "Error al actualizar");
        }
      } catch (err) {
        setStatus(`Error: ${err.message}`, "error");
      }
    });
  }
});

async function deleteRemision(remisionId, remisionNo, sourceFile) {
  if (doserModule) {
    await doserModule.deleteRemision(remisionId, remisionNo, sourceFile);
    return;
  }
  try {
    const id = Number(remisionId);
    if (!Number.isFinite(id) || id <= 0) {
      throw new Error("ID de remision invalido.");
    }
    const code = (remisionNo || "-").toString().trim() || "-";
    const confirmed = await uiConfirm(
      `Se eliminara la remision ${code}. Esta accion no se puede deshacer. Continuar?`,
      {
        title: "Eliminar remision",
        confirmText: "Eliminar",
        tone: "err",
      }
    );
    if (!confirmed) return;
    const response = await apiFetch(`/api/remisiones/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "No se pudo eliminar la remision.");
    }
    await loadRemisiones();
    setStatus(`Remision eliminada: ${payload.remision_no || code}`, "ok");
  } catch (error) {
    setStatus(String(error), "err");
  }
}

async function saveRemision() {
  if (doserModule) {
    await doserModule.saveRemision();
    return;
  }
  try {
    const remisionNo = ((remisionNoInput?.value || "").toString().trim().toUpperCase());
    const remisionDate = ((remisionDateInput?.value || "").toString().trim());
    if (!remisionNo) {
      setStatus("Ingresa el numero de remision.", "warn");
      return;
    }
    const snap = buildDoserReportSnapshot();
    if (!snap) {
      setStatus("Selecciona una mezcla para guardar la remision.", "warn");
      return;
    }
    const response = await apiFetch("/api/remisiones/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file: state.file,
        remision_no: remisionNo,
        remision_date: remisionDate || undefined,
        snapshot: snap,
      }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "No se pudo guardar la remision.");
    }
    if (remisionNoInput) remisionNoInput.value = "";
    if (clienteInput) clienteInput.value = "";
    if (ubicacionInput) ubicacionInput.value = "";
    if (remisionFilterDate && remisionDate) remisionFilterDate.value = remisionDate;
    await loadRemisiones();
    setStatus(`Remision guardada: ${payload.remision_no}`, "ok");
    pushToast(`Remisión guardada con éxito: ${payload.remision_no}`, "ok");
  } catch (error) {
    setStatus(String(error), "err");
  }
}

function syncQcStamps() {
  if (qcModule) {
    qcModule.syncStamps();
  }
}

function onQcFieldChange(aggName, field, rawValue, source = "editor") {
  if (qcModule) {
    qcModule.onFieldChange(aggName, field, rawValue, source);
  }
}

function renderEditorQcTable() {
  if (qcModule) {
    qcModule.renderEditorTable();
  }
}

function renderQcTable() {
  if (qcModule) {
    qcModule.renderTable();
  }
}

function computeTheoreticalLoads(recipeItems) {
  if (!doserModule) return [];
  return doserModule.computeTheoreticalLoads(recipeItems);
}

function renderDosificador() {
  if (!doserModule) return;
  doserModule.render();
}
function adjustQueryVisibleRows(rowsToShow = 5) {
  if (!queryTable || !queryResultShell) return;
  const headerHeight = queryTable.tHead ? queryTable.tHead.offsetHeight : 0;
  const firstRow = queryBody.querySelector("tr");
  const rowHeight = firstRow ? firstRow.offsetHeight : 34;
  const shellHeight = Math.round(headerHeight + (rowHeight * rowsToShow) + 2);
  queryResultShell.style.maxHeight = `${shellHeight}px`;
  queryResultShell.style.minHeight = "0";
  queryResultShell.style.flex = "0 0 auto";
  queryResultShell.style.overflow = "auto";
}

function runQuery() {
  if (consultaModule) {
    consultaModule.runQuery();
  }
}

function refreshConsulta() {
  if (consultaModule) {
    consultaModule.refresh();
  }
  fillDoserSelectors();
  runDoserSearch();
}

function syncDoserParamInputs() {
  if (doserParamsModule) {
    doserParamsModule.syncInputs();
  }
}

function readDoserParamsFromInputs() {
  return doserParamsModule ? doserParamsModule.readFromInputs() : normalizeDoserParams({});
}

async function loadQcData(fileName = state.file) {
  if (qcModule) {
    await qcModule.load(fileName);
  }
}

async function loadDoserParams(fileName = state.file) {
  if (doserParamsModule) {
    await doserParamsModule.load(fileName);
  }
}

async function saveDoserParams() {
  if (doserParamsModule) {
    await doserParamsModule.save();
  }
}

async function saveQcData() {
  if (qcModule) {
    await qcModule.save();
  }
}

async function saveQcHumidityData() {
  if (qcModule) {
    await qcModule.saveHumidity();
  }
}

if (qcModule) {
  qcModule.init();
}

// Purga definitiva (Hard Reset) - Solo Admin
const purgeBtn = document.getElementById("purgeDeletedBtn");
if (false && purgeBtn) {
  purgeBtn.addEventListener("click", async () => {
    const confirmHard = await uiConfirm(
      "¿Estás seguro de que deseas eliminar DEFINITIVAMENTE todos los archivos borrados? Esto eliminará también todas las REMISIONES vinculadas a ellos.",
      {
        title: "Hard Reset - Purga Definitiva",
        confirmText: "Si, entiendo el riesgo",
        tone: "err",
      }
    );
    if (!confirmHard) return;

    const finalBoss = await uiConfirm(
      "¡ADVERTENCIA CRÍTICA! Esta acción borrará permanentemente el historial de remisiones, transacciones de inventario y perfiles. No se puede deshacer. ¿Deseas purgar todo ahora?",
      {
        title: "Confirmacion Final Irreversible",
        confirmText: "BORRAR TODO DEFINITIVAMENTE",
        tone: "err",
      }
    );
    if (!finalBoss) return;

    setStatus("Purgando archivos de la base de datos...", "info");
    try {
      const resp = await apiFetch("/api/purge_deleted", { method: "POST" });
      const res = await resp.json();
      if (res.ok) {
        setStatus(`Purga completada: ${res.purged_count} archivos eliminados físicamente.`, "ok");
        await loadFiles();
      } else {
        setStatus("Error al purgar: " + (res.error || "Error desconocido"), "err");
      }
    } catch (err) {
      setStatus("Error de red al purgar: " + err.message, "err");
    }
  });
}

tabEditor.addEventListener("click", () => switchView("editor"));
tabConsulta.addEventListener("click", () => switchView("consulta"));
if (tabDosificador) {
  tabDosificador.addEventListener("click", () => switchView("dosificador"));
}
if (tabRemisiones) {
  tabRemisiones.addEventListener("click", () => switchView("remisiones"));
}
if (editorModule) {
  editorModule.init();
}
if (consultaModule) {
  consultaModule.init();
}
if (usersModule) {
  usersModule.init();
}
if (inventoryModule) {
  inventoryModule.init();
}
if (fleetModule) {
  fleetModule.init();
}
if (qcLabModule) {
  qcLabModule.init();
}

if (false && toggleQuoteModeBtn) {
  toggleQuoteModeBtn.addEventListener("click", () => {
    state.quoteMode = !state.quoteMode;
    if (!state.quoteMode) state.quoteOverrides = {};
    toggleQuoteModeBtn.textContent = state.quoteMode ? "Salir Cotización" : "Modo Cotización";
    toggleQuoteModeBtn.classList.toggle("btn--active", state.quoteMode);
    toggleQuoteModeBtn.classList.toggle("btn--muted", !state.quoteMode);
    // Re-render cost table with current recipe
    const selectedIndex = state.selectedQueryRow;
    const row = typeof selectedIndex === "number" ? state.rows[selectedIndex] : null;
    if (row) {
      const recipeItems = normalizeConsultaRecipeItems(extractRecipe(row));
      const adjustedForCost = adjustRecipeByQuality(recipeItems, 1);
      renderCostTable(adjustedForCost);
    }
  });
}

if (doserModule) {
  doserModule.init();
}
if (remisionesModule) {
  remisionesModule.init();
}

document.addEventListener("keydown", (event) => {
  const ctrlOrCmd = event.ctrlKey || event.metaKey;
  if (ctrlOrCmd && event.key.toLowerCase() === "s") {
    if (!state.auth.canEdit || !canAccessView("editor")) return;
    event.preventDefault();
    if (editorModule) editorModule.saveData();
  }
});

window.addEventListener("beforeunload", (event) => {
  if (!state.dirty && !state.qcDirty) return;
  event.preventDefault();
  event.returnValue = "";
});

window.addEventListener("resize", () => adjustQueryVisibleRows(5));

if (tabLaboratorio) {
  tabLaboratorio.addEventListener("click", () => {
    if (!canAccessView("laboratorio")) return;
    switchView("laboratorio");
  });
}

if (tabUsuarios) {
  tabUsuarios.addEventListener("click", () => switchView("usuarios"));
}

applyRoleAccessUi();
if (remisionDateInput && !remisionDateInput.value) remisionDateInput.value = getTodayCancun();
if (remisionFilterDate && !remisionFilterDate.value) remisionFilterDate.value = getTodayCancun();
switchView(defaultView());
if (editorModule) editorModule.loadData();



