(function () {
  window.FormixShared = window.FormixShared || {};

  function createRecipeCore(ctx) {
    const {
      normalize,
      toNumber,
      safeDivide,
      normalizeDoserParams,
      averagePV,
      getQualityFor,
    } = ctx;

    function splitHeaderName(headerText) {
      const raw = (headerText ?? "").toString().trim();
      const match = raw.match(/^(.*?)(?:\s*\(([^()]*)\))?$/);
      if (!match) return { name: raw, type: "" };
      return {
        name: (match[1] || "").trim(),
        type: (match[2] || "").trim(),
      };
    }

    function isAggregateComponent(name) {
      return ["Fino 1", "Fino 2", "Grueso 1", "Grueso 2"].includes(name);
    }

    function reportComponentLabel(componentName, aggregateMap) {
      const displayName =
        componentName === "Grueso 1" ? "Grava 1" : componentName === "Grueso 2" ? "Grava 2" : componentName;
      if (!isAggregateComponent(componentName)) return displayName;
      const raw = (aggregateMap && aggregateMap[componentName]) || [];
      const details = [...new Set(raw.map((h) => splitHeaderName(h).name || h).map((s) => (s || "").trim()).filter(Boolean))];
      if (!details.length) return displayName;
      return `${displayName} (${details.join(" + ")})`;
    }

    function classifyComponent(headerText, counters) {
      const parsed = splitHeaderName(headerText);
      const name = parsed.name || headerText;
      const nName = normalize(name);
      const nType = normalize(parsed.type);

      if (nName.includes("fcpc") || nName.includes("cement")) return "Cemento";
      if (nName.includes("agua")) return "Agua";
      if (nName.includes("reductor")) return "Reductor";
      if (nName.includes("retard")) return "Retardante";
      if (nName.includes("fibra")) return "Fibra";
      if (nName.includes("imper")) return "Imper";

      if (nName === "fino1" || nName === "arena1") return "Fino 1";
      if (nName === "fino2" || nName === "arena2") return "Fino 2";
      if (nName === "grueso1" || nName === "grava1" || nName === "nava20") return "Grueso 1";
      if (nName === "grueso2" || nName === "grava2" || nName === "nava5") return "Grueso 2";

      if (nType.includes("grava 1") || nType.includes("grueso 1")) return "Grueso 1";
      if (nType.includes("grava 2") || nType.includes("grueso 2")) return "Grueso 2";
      if (nType.includes("fino 1") || nType.includes("arena 1")) return "Fino 1";
      if (nType.includes("fino 2") || nType.includes("arena 2")) return "Fino 2";

      if (nType.includes("grava") || nType.includes("grueso")) {
        counters.grueso += 1;
        return counters.grueso === 1 ? "Grueso 1" : "Grueso 2";
      }
      if (nType.includes("fino") || nType.includes("arena")) {
        counters.fino += 1;
        return counters.fino === 1 ? "Fino 1" : "Fino 2";
      }

      if (nName.includes("lavada") || nName.includes("arena")) return "Fino 1";
      return name || "Otro";
    }

    function componentUnit(component) {
      if (["Agua", "Reductor", "Retardante"].includes(component)) return "Lts";
      return "kg";
    }

    function densityFor(component, unit) {
      if (unit === "Lts") return 1000;
      if (component === "Cemento") return 3150;
      if (component === "Fino 1" || component === "Fino 2") return 1600;
      if (component === "Grueso 1" || component === "Grueso 2") return 1500;
      if (component === "Fibra") return 900;
      return 1500;
    }

    function normalizeConsultaRecipeItems(recipeItems) {
      return recipeItems.map((item) => {
        if (!["Reductor", "Retardante", "Fibra", "Imper"].includes(item.name)) return item;
        const isLiquid = ["Reductor", "Retardante"].includes(item.name);
        const qty = item.qty / 1000;
        return {
          ...item,
          qty,
          unit: isLiquid ? "cc/kg-cto" : "kg",
          volume: isLiquid ? qty / 1000 : 0,
        };
      });
    }

    function normalizeDoserRecipeItems(recipeItems) {
      return recipeItems.map((item) => {
        if (!["Reductor", "Retardante", "Fibra", "Imper"].includes(item.name)) return item;
        const isLiquid = ["Reductor", "Retardante"].includes(item.name);
        const qty = item.qty / 1000;
        return {
          ...item,
          qty,
          unit: isLiquid ? "Lts/m3" : "kg",
          volume: isLiquid ? qty / 1000 : 0,
        };
      });
    }

    function componentWeightFactor(item) {
      const unit = (item?.unit || "").toString().toLowerCase();
      if (unit === "cc" || unit === "ml") return 1 / 1000;
      return 1;
    }

    function doserComponentOrder(recipeItems) {
      const priority = [
        "Cemento",
        "Grueso 1",
        "Grueso 2",
        "Fino 1",
        "Fino 2",
        "Agua",
        "Reductor",
        "Retardante",
        "Fibra",
        "Imper",
      ];
      const names = recipeItems.map((item) => item.name);
      const out = [];
      priority.forEach((name) => {
        if (names.includes(name)) out.push(name);
      });
      names.forEach((name) => {
        if (!out.includes(name)) out.push(name);
      });
      return out;
    }

    function resolveAggregateDensityKgPerLt(componentName, params) {
      const avg = averagePV(componentName);
      if (avg && avg > 0) {
        if (avg > 50) return { value: avg / 1000, source: "qc_avg_kg_m3" };
        return { value: avg, source: "qc_avg_kg_l" };
      }
      return {
        value: Math.max(0, toNumber(params.densidad_agregado_fallback)),
        source: "fallback",
      };
    }

    function computeDoserDetailedLoads(recipeItems, dose, params) {
      const safeDose = Math.max(0, toNumber(dose));
      const cleanParams = normalizeDoserParams(params);
      const order = doserComponentOrder(recipeItems);
      const recipeByName = new Map(recipeItems.map((item) => [item.name, item]));

      const rows = [];
      let aggAbsDemand = 0;
      let aggFreeWater = 0;
      let aggIGravel = 0;
      let aggISand = 0;
      const airLiters = (Math.max(0, cleanParams.aire_pct) / 100) * 1000;
      let cementDesignSss = 0;
      let waterDesignSss = 0;
      let aditivo4DesignSss = 0;

      const makeBaseRow = (name) => {
        const base = recipeByName.get(name) || { qty: 0, unit: componentUnit(name) };
        return {
          name,
          unit: base.unit || componentUnit(name),
          designA: Math.max(0, toNumber(base.qty)),
          designSss: 0,
          freeWater: 0,
          absVolume: 0,
          designReal: 0,
          trialLoad: 0,
          trialUnit: base.unit || componentUnit(name),
          note: "",
          includeAbsVolume: false,
          includeWeightTotal: true,
        };
      };

      order.forEach((name) => {
        const row = makeBaseRow(name);
        if (name === "Cemento") {
          row.designSss = row.designA;
          row.designReal = row.designSss;
          const div = safeDivide(row.designSss, cleanParams.cemento_pesp, 0);
          row.absVolume = div.value;
          row.includeAbsVolume = true;
          row.trialLoad = row.designReal * safeDose;
          row.trialUnit = "kg";
          cementDesignSss = row.designSss;
          if (div.fallbackUsed) row.note = "Peso esp. cemento faltante";
        } else if (isAggregateComponent(name)) {
          const q = getQualityFor(name);
          const absPct = Math.max(0, toNumber(q.absorcion));
          const humPct = Math.max(0, toNumber(q.humedad));
          row.designSss = row.designA + ((row.designA * absPct) / 100);
          row.freeWater = ((humPct - absPct) / 100) * row.designSss;
          row.designReal = row.designSss + row.freeWater;
          const dens = resolveAggregateDensityKgPerLt(name, cleanParams);
          const div = safeDivide(row.designSss, dens.value, 0);
          row.absVolume = div.value;
          row.includeAbsVolume = true;
          row.trialLoad = row.designReal * safeDose;
          row.trialUnit = "kg";
          aggAbsDemand += (row.designA * absPct) / 100;
          aggFreeWater += row.freeWater;
          if (name.startsWith("Grueso")) aggIGravel += row.designSss;
          if (name.startsWith("Fino")) aggISand += row.designSss;
          if (dens.source === "fallback" || div.fallbackUsed) row.note = "Dato base faltante";
        } else if (name === "Agua") {
          row.designSss = row.designA - aggAbsDemand;
          row.freeWater = aggFreeWater;
          row.absVolume = row.designSss;
          row.designReal = row.designSss - row.freeWater;
          row.includeAbsVolume = true;
          row.trialLoad = row.designReal * safeDose;
          row.trialUnit = "Lts";
          waterDesignSss = row.designSss;
        } else if (name === "Reductor" || name === "Retardante") {
          row.designSss = row.designA;
          row.absVolume = row.designSss;
          row.designReal = row.designSss;
          row.includeAbsVolume = true;
          row.trialLoad = (safeDose / 1000) * row.designReal * 1000;
          row.trialUnit = "Lts";
          if (name === "Retardante") aditivo4DesignSss = row.designSss;
        } else {
          row.designSss = row.designA;
          row.designReal = row.designSss;
          if (row.unit === "Lts") {
            row.absVolume = row.designSss;
            row.includeAbsVolume = true;
          }
          row.trialLoad = row.designReal * safeDose;
          row.trialUnit = row.unit || "kg";
        }
        rows.push(row);
      });

      const sumBy = (fn) => rows.reduce((acc, r) => acc + fn(r), 0);
      const absTotalBase = sumBy((r) => (r.includeAbsVolume ? r.absVolume : 0));
      const absTotal = absTotalBase + airLiters;
      const relAc = safeDivide(waterDesignSss, cementDesignSss, 0).value;
      const gravelPct = safeDivide(aggIGravel * 100, aggIGravel + aggISand, 0).value;
      const sandPct = safeDivide(aggISand * 100, aggIGravel + aggISand, 0).value;
      const gravelSandRatio = safeDivide(aggIGravel, aggISand, 0).value;
      const fino1 = rows.find((r) => r.name === "Fino 1");
      const fino2 = rows.find((r) => r.name === "Fino 2");
      const finoContent =
        cementDesignSss +
        ((Math.max(0, cleanParams.pxl_pond_pct) * toNumber(fino1?.designSss || 0)) / 100) +
        ((toNumber(fino2?.designSss || 0) * Math.max(0, cleanParams.pasa_malla_200_pct)) / 100) +
        aditivo4DesignSss;
      const recipeWeight = sumBy((r) => {
        const isAditivo = r.name === "Reductor" || r.name === "Retardante";
        const qty = isAditivo ? r.designSss : r.designA;
        const unit = isAditivo ? "Lts" : (r.unit || "kg");
        return qty * componentWeightFactor({ unit });
      });
      const theoreticalWeight = sumBy((r) =>
        r.includeWeightTotal ? r.trialLoad * componentWeightFactor({ unit: r.trialUnit || r.unit }) : 0
      );

      return {
        rows,
        totals: {
          recipeWeight,
          theoreticalWeight,
          absVolumeTotal: absTotal,
          airLiters,
          gravelPct,
          sandPct,
          gravelSandRatio,
          relAc,
          finoContent,
          freeWaterTotal: aggFreeWater,
        },
      };
    }

    return {
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
    };
  }

  window.FormixShared.recipeCore = {
    createRecipeCore,
  };
})();
