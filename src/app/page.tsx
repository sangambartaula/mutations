"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { ModeToggle } from "@/components/mode-toggle";
import { Coins, Sprout, Clock, Calculator, Loader2, ArrowUpRight, AlertTriangle, X } from "lucide-react";
import {
  computeProfitHrAFK,
  computeProfitHrASAP,
  deriveCoinsPerMutationFromBatch,
  deriveHarvestStagesFromHours,
} from "@/lib/mutation-profit-calculator";
import { applyFortuneChange, syncFortunesOnToggle } from "@/lib/fortune-link";

type OptimizationMode = "profit" | "smart" | "target";
type SetupMode = "buy_order" | "insta_buy";
type SellMode = "sell_offer" | "insta_sell";
type SortKey = "rank" | "mutation" | "value" | "profitCycle" | "profitHour" | "cycles" | "setup";
type SortDirection = "asc" | "desc";
type HarvestMode = "afk" | "asap";
type AfkInputMode = "stages" | "hours";

type YieldMath = {
  base: number;
  limit: number;
  gh_buff: number;
  unique_buff: number;
  wart_buff: number;
  fortune: number;
  special: number;
};

type Ingredient = {
  name: string;
  amount: number;
  unit_price: number;
  total_cost: number;
};

type YieldItem = {
  name: string;
  amount: number;
  unit_price: number;
  total_value: number;
  math?: YieldMath;
};

type MutationBreakdown = {
  base_limit: number;
  ingredients: Ingredient[];
  yields: YieldItem[];
  total_setup_cost: number;
  total_revenue: number;
  growth_stages: number;
  estimated_time_hours: number;
};

type LeaderboardItem = {
  mutationName: string;
  score: number;
  profit: number;
  profit_per_cycle: number;
  profit_per_hour: number;
  opt_cost: number;
  revenue: number;
  warning: boolean;
  mut_price: number;
  limit: number;
  smart_progress?: Record<string, number>;
  hourly?: {
    mutation_chance?: number;
  };
  breakdown: MutationBreakdown;
};

type LeaderboardResponse = {
  leaderboard: LeaderboardItem[];
  metadata: {
    cycle_time_hours: number;
    missing_crops?: string[];
  };
};

const optimizationModes: { id: OptimizationMode; label: string }[] = [
  { id: "profit", label: "Pure Profit" },
  { id: "smart", label: "Smart (Milestones)" },
  { id: "target", label: "Focus One Crop" },
];

const cropLabelMap: Record<string, string> = {
  "Coco Bean": "Cocoa Beans",
  "Sugar cane": "Sugar Cane",
};

const toCropLabel = (crop: string) => cropLabelMap[crop] ?? crop;

export default function Home() {
  const [plots, setPlots] = useState(3);
  const [fortune, setFortune] = useState(2500);
  const [harvestMode, setHarvestMode] = useState<HarvestMode>("afk");
  const [afkInputMode, setAfkInputMode] = useState<AfkInputMode>("stages");
  const [afkStages, setAfkStages] = useState(0);
  const [afkHours, setAfkHours] = useState(0);
  const [fortuneAfk, setFortuneAfk] = useState(2500);
  const [fortuneAsap, setFortuneAsap] = useState(2500);
  const [useSameFortune, setUseSameFortune] = useState(true);
  const [buffCostAfkPerHarvest, setBuffCostAfkPerHarvest] = useState(0);
  const [buffCostAsapPerHour, setBuffCostAsapPerHour] = useState(0);
  const [extraSetupCost, setExtraSetupCost] = useState(0);
  const [asapSetupAmortizeHours, setAsapSetupAmortizeHours] = useState(24);
  const [ghUpgrade, setGhUpgrade] = useState(9);
  const [uniqueCrops, setUniqueCrops] = useState(12);

  const [mode, setMode] = useState<OptimizationMode>("profit");
  const [targetCrop, setTargetCrop] = useState("Wheat");
  const [maxedCrops, setMaxedCrops] = useState<string[]>([]);
  const [smartTab, setSmartTab] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // New Toggles
  const [setupMode, setSetupMode] = useState<SetupMode>("buy_order");
  const [sellMode, setSellMode] = useState<SellMode>("sell_offer");

  // Modal State
  const [selectedMutation, setSelectedMutation] = useState<LeaderboardItem | null>(null);

  const displayCrops = [
    { key: "Wheat", label: "Wheat" },
    { key: "Carrot", label: "Carrot" },
    { key: "Potato", label: "Potato" },
    { key: "Pumpkin", label: "Pumpkin" },
    { key: "Sugar cane", label: "Sugar Cane" },
    { key: "Melon", label: "Melon" },
    { key: "Cactus", label: "Cactus" },
    { key: "Coco Bean", label: "Cocoa Beans" },
    { key: "Nether Wart", label: "Nether Wart" },
    { key: "Sunflower", label: "Sunflower" },
    { key: "Moonflower", label: "Moonflower" },
    { key: "Wild Rose", label: "Wild Rose" },
    { key: "Mushroom", label: "Mushroom" },
  ];
  const tableScrollRef = useRef<HTMLDivElement | null>(null);

  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("mutations:maxed-crops");
    if (!saved) return;
    try {
      const parsed: unknown = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        setMaxedCrops(parsed.filter((v): v is string => typeof v === "string"));
      }
    } catch {
      // Ignore malformed local storage data.
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("mutations:maxed-crops", JSON.stringify(maxedCrops));
  }, [maxedCrops]);

  useEffect(() => {
    const synced = syncFortunesOnToggle(useSameFortune, { fortuneAfk, fortuneAsap });
    if (synced.fortuneAfk !== fortuneAfk) setFortuneAfk(synced.fortuneAfk);
    if (synced.fortuneAsap !== fortuneAsap) setFortuneAsap(synced.fortuneAsap);
  }, [useSameFortune, fortuneAfk, fortuneAsap]);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError("");
      try {
        const query = new URLSearchParams({
          plots: plots.toString(),
          fortune: fortune.toString(),
          gh_upgrade: ghUpgrade.toString(),
          unique_crops: uniqueCrops.toString(),
          mode: mode,
          setup_mode: setupMode,
          sell_mode: sellMode,
          maxed_crops: maxedCrops.join(","),
          ...(mode === "target" && { target_crop: targetCrop })
        });
        const res = await fetch(`/api/leaderboard?${query.toString()}`);
        if (!res.ok) throw new Error("Failed to fetch leaderboard data.");
        const json: LeaderboardResponse = await res.json();
        setData(json);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Unexpected error while fetching leaderboard data.");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [plots, fortune, ghUpgrade, uniqueCrops, mode, setupMode, sellMode, targetCrop, maxedCrops]);

  const toggleMaxedCrop = (crop: string) => {
    setMaxedCrops(prev =>
      prev.includes(crop) ? prev.filter(c => c !== crop) : [...prev, crop]
    );
  };

  const formatCoins = (num: number) => {
    const safe = Number.isFinite(num) ? num : 0;
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(safe);
  };

  const formatDuration = (hours: number) => {
    const safeHours = Number.isFinite(hours) ? hours : 0;
    const totalMinutes = Math.max(0, Math.round(safeHours * 60));
    const hrs = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;

    if (hrs === 0) return `${mins}m`;
    if (mins === 0) return `${hrs}h`;
    return `${hrs}h ${mins}m`;
  };

  const formatYieldCalculation = (math: YieldMath, unitPrice: number) => {
    const isPlainMutationMath =
      math.base === 1 &&
      math.gh_buff === 0 &&
      math.unique_buff === 0 &&
      math.wart_buff === 1 &&
      math.fortune === 1 &&
      math.special === 1;

    if (isPlainMutationMath) {
      return `1 base × ${math.limit} total across plots × ${formatCoins(unitPrice)} price`;
    }

    const factors = [
      `${math.base} base`,
      `${math.limit} limit`,
      `(+${math.gh_buff.toFixed(2)} GH)`,
      `(+${math.unique_buff.toFixed(2)} Unique)`,
      `${math.wart_buff} wart buff`,
      `${math.fortune.toFixed(2)} fortune`,
    ];

    if (math.special !== 1) {
      factors.push(`${math.special} special buff`);
    }

    factors.push(`${formatCoins(unitPrice)} price`);
    return factors.join(" × ");
  };

  const missingCrops = mode === "smart" ? (data?.metadata.missing_crops ?? []) : [];
  const activeSmartTab = missingCrops.includes(smartTab) ? smartTab : "all";

  const visibleSmartCrops = mode === "smart"
    ? (activeSmartTab === "all" ? missingCrops : [activeSmartTab])
    : [];

  const visibleLeaderboard = useMemo(() => {
    if (!(mode === "smart" && data)) return data?.leaderboard ?? [];
    return data.leaderboard.filter((item) => {
      const progress = item.smart_progress ?? {};
      if (activeSmartTab === "all") return Object.keys(progress).length > 0;
      return (progress[activeSmartTab] ?? 0) > 0;
    });
  }, [mode, data, activeSmartTab]);

  const mutationProfitByName = useMemo(() => {
    const cycleTime = data?.metadata.cycle_time_hours ?? 0;
    const map: Record<string, {
      expectedMutations: number;
      revenue: number;
      costs: number;
      net: number;
      profitHr: number;
      harvestHours: number;
      stages: number;
    }> = {};

    for (const item of visibleLeaderboard) {
      const chance = item.hourly?.mutation_chance ?? 0.25;
      const slotsPerPlot = Math.max(0, item.breakdown.base_limit);
      const setupCost = Math.max(0, item.opt_cost + extraSetupCost);
      const afkStagesDerived = afkInputMode === "stages"
        ? Math.max(0, Math.floor(afkStages))
        : deriveHarvestStagesFromHours(afkHours, cycleTime);
      const afkStagesForItem = afkStagesDerived > 0 ? afkStagesDerived : item.breakdown.growth_stages;
      const mutationYield = item.breakdown.yields.find((y) => y.name === item.mutationName)?.amount ?? 0;
      const modeFortune = harvestMode === "asap" ? fortuneAsap : fortuneAfk;
      const itemPrice = deriveCoinsPerMutationFromBatch({
        totalRevenueAtReferenceFortune: Math.max(0, item.revenue),
        mutationUnitPrice: Math.max(0, item.mut_price),
        mutationsAtHarvest: mutationYield,
        referenceFortune: fortune,
        modeFortune,
      });
      const baseItems = 1;

      if (harvestMode === "asap") {
        const asap = computeProfitHrASAP({
          plots,
          slotsPerPlot,
          mutationChance: chance,
          stageDurationHours: cycleTime,
          fortune: 0,
          baseItems,
          itemPrice,
          buffCostPerHour: buffCostAsapPerHour,
          setupCost,
          setupAmortizeHours: asapSetupAmortizeHours,
        });
        map[item.mutationName] = {
          expectedMutations: asap.expectedMutationsPerStage,
          revenue: asap.revenuePerHour,
          costs: asap.costsPerHour,
          net: asap.netProfitPerHour,
          profitHr: asap.netProfitPerHour,
          harvestHours: cycleTime,
          stages: 1,
        };
      } else {
        const afk = computeProfitHrAFK({
          plots,
          slotsPerPlot,
          mutationChance: chance,
          stageDurationHours: cycleTime,
          harvestStages: afkStagesForItem,
          fortune: 0,
          baseItems,
          itemPrice,
          setupCost,
          buffCostPerHarvest: buffCostAfkPerHarvest,
        });
        map[item.mutationName] = {
          expectedMutations: afk.expectedMutationsByHarvest,
          revenue: afk.revenueByHarvest,
          costs: afk.costsByHarvest,
          net: afk.netProfitByHarvest,
          profitHr: afk.netProfitPerHour,
          harvestHours: afk.harvestTimeHours,
          stages: afkStagesForItem,
        };
      }
    }
    return map;
  }, [
    data?.metadata.cycle_time_hours,
    visibleLeaderboard,
    harvestMode,
    plots,
    fortuneAfk,
    fortuneAsap,
    buffCostAfkPerHarvest,
    buffCostAsapPerHour,
    extraSetupCost,
    asapSetupAmortizeHours,
    afkInputMode,
    afkStages,
    afkHours,
    fortune,
  ]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === "desc" ? "asc" : "desc"));
      return;
    }
    setSortKey(key);
    setSortDirection(key === "mutation" ? "asc" : "desc");
  };

  const sortValue = (item: LeaderboardItem, key: SortKey) => {
    if (key === "mutation") return item.mutationName.toLowerCase();
    if (key === "cycles") {
      if (mode === "profit") return mutationProfitByName[item.mutationName]?.stages ?? item.breakdown.growth_stages;
      return item.breakdown.growth_stages;
    }
    if (key === "setup") return item.opt_cost;
    if (key === "profitCycle") return item.profit_per_cycle ?? 0;
    if (key === "profitHour") {
      if (mode === "profit") return mutationProfitByName[item.mutationName]?.profitHr ?? 0;
      return item.profit_per_hour ?? 0;
    }
    if (key === "value") {
      if (mode === "smart") {
        if (activeSmartTab !== "all") return item.smart_progress?.[activeSmartTab] ?? 0;
        return item.score;
      }
      return mode === "target" ? item.score : item.profit;
    }
    if (mode === "smart" && activeSmartTab !== "all") {
      return item.smart_progress?.[activeSmartTab] ?? 0;
    }
    return item.score;
  };

  const sortedLeaderboard = [...visibleLeaderboard].sort((a, b) => {
    const av = sortValue(a, sortKey);
    const bv = sortValue(b, sortKey);
    let cmp = 0;
    if (typeof av === "string" && typeof bv === "string") cmp = av.localeCompare(bv);
    else cmp = Number(av) - Number(bv);
    return sortDirection === "asc" ? cmp : -cmp;
  });

  const sortIndicator = (key: SortKey) => {
    if (sortKey !== key) return "↕";
    return sortDirection === "asc" ? "↑" : "↓";
  };

  const scrollLeaderboardBy = (pixels: number) => {
    if (!tableScrollRef.current) return;
    tableScrollRef.current.scrollBy({ left: pixels, behavior: "smooth" });
  };

  const selectedMutationModel = selectedMutation ? mutationProfitByName[selectedMutation.mutationName] : null;



  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950 font-sans text-neutral-900 dark:text-neutral-100 transition-colors duration-200">

      {/* TOP NAVIGATION */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-md border-b border-neutral-200 dark:border-neutral-800">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-500 text-white p-2 rounded-lg shadow-sm">
            <Sprout className="w-5 h-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">Skyblock Mutations</h1>
        </div>
        <div className="flex items-center gap-4">
          <ModeToggle />
        </div>
      </nav>

      {/* DASHBOARD LAYOUT */}
      <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col md:flex-row gap-8">

        {/* SIDEBAR: SETTINGS */}
        <aside className="w-full md:w-80 shrink-0 space-y-6">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-6 text-emerald-600 dark:text-emerald-400">
              <Calculator className="w-5 h-5" />
              Optimization Settings
            </h2>

            {/* Optimization Mode */}
            <div className="mb-6">
              <label className="text-sm font-medium mb-2 block">Optimization Mode</label>
              <div className="grid grid-cols-1 gap-2">
                {optimizationModes.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setMode(m.id)}
                    className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium border transition-all ${mode === m.id
                      ? 'bg-emerald-500 border-emerald-500 text-white shadow-md shadow-emerald-500/20'
                      : 'border-neutral-200 dark:border-neutral-800 hover:border-emerald-500/50 hover:bg-emerald-50 dark:hover:bg-emerald-900/10'
                      }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Target Crop (Conditional) */}
            {mode === "target" && (
              <div className="mb-6 animate-in fade-in slide-in-from-top-2 duration-300">
                <label className="text-sm font-medium mb-2 block text-emerald-600 dark:text-emerald-400">Target Crop</label>
                <select
                  value={targetCrop}
                  onChange={(e) => setTargetCrop(e.target.value)}
                  className="w-full bg-neutral-100 dark:bg-neutral-800 border-transparent rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                >
                  {displayCrops.map(c => (
                    <option key={c.key} value={c.key}>{c.label}</option>
                  ))}
                </select>
              </div>
            )}


            <hr className="my-6 border-neutral-100 dark:border-neutral-800" />

            {/* Market Strategies */}
            <div className="mb-6 space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Setup Purchase Strategy</label>
                <div className="flex bg-neutral-100 dark:bg-neutral-800 rounded-xl p-1">
                  <button
                    onClick={() => setSetupMode("buy_order")}
                    className={`flex-1 text-xs py-1.5 rounded-lg transition-colors ${setupMode === "buy_order" ? "bg-white dark:bg-neutral-700 shadow-sm font-medium" : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"}`}
                  >Buy Order</button>
                  <button
                    onClick={() => setSetupMode("insta_buy")}
                    className={`flex-1 text-xs py-1.5 rounded-lg transition-colors ${setupMode === "insta_buy" ? "bg-white dark:bg-neutral-700 shadow-sm font-medium" : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"}`}
                  >Insta-Buy</button>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Crop Selling Strategy</label>
                <div className="flex bg-neutral-100 dark:bg-neutral-800 rounded-xl p-1">
                  <button
                    onClick={() => setSellMode("sell_offer")}
                    className={`flex-1 text-xs py-1.5 rounded-lg transition-colors ${sellMode === "sell_offer" ? "bg-emerald-500 text-white shadow-sm font-medium" : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"}`}
                  >Sell Offer</button>
                  <button
                    onClick={() => setSellMode("insta_sell")}
                    className={`flex-1 text-xs py-1.5 rounded-lg transition-colors ${sellMode === "insta_sell" ? "bg-emerald-500 text-white shadow-sm font-medium" : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"}`}
                  >Insta-Sell</button>
                </div>
              </div>
            </div>

            <hr className="my-6 border-neutral-100 dark:border-neutral-800" />

            {/* Plots Slider */}
            <div className="mb-6">
              <label className="flex justify-between text-sm font-medium mb-2">
                <span>Number of Plots</span>
                <span className="text-emerald-600 dark:text-emerald-400">{plots}</span>
              </label>
              <input
                type="range"
                min="1"
                max="3"
                value={plots}
                onChange={(e) => setPlots(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
            </div>

            {/* Farming Fortune Slider */}
            <div className="mb-6">
              <label className="flex justify-between items-center text-sm font-medium mb-2">
                <span>Farming Fortune</span>
                <input
                  type="number"
                  min="0"
                  max="4000"
                  value={fortune}
                  onChange={(e) => {
                    const next = Number(e.target.value);
                    setFortune(Math.max(0, Math.min(4000, Number.isFinite(next) ? next : 0)));
                  }}
                  className="w-24 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-2 py-1 text-right text-emerald-600 dark:text-emerald-400"
                />
              </label>
              <input
                type="range"
                min="0"
                max="4000"
                step="50"
                value={fortune}
                onChange={(e) => setFortune(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
            </div>

            {mode === "profit" && (
              <div className="mb-6 rounded-xl border border-blue-200 dark:border-blue-900/40 bg-blue-50/60 dark:bg-blue-950/20 p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-blue-700 dark:text-blue-300">Mutation Profit / Hour</p>
                  <div className="flex rounded-lg border border-blue-300 dark:border-blue-700 overflow-hidden text-xs">
                    <button
                      type="button"
                      onClick={() => setHarvestMode("afk")}
                      className={`px-2 py-1 ${harvestMode === "afk" ? "bg-blue-600 text-white" : "bg-transparent text-blue-700 dark:text-blue-300"}`}
                    >
                      AFK
                    </button>
                    <button
                      type="button"
                      onClick={() => setHarvestMode("asap")}
                      className={`px-2 py-1 ${harvestMode === "asap" ? "bg-blue-600 text-white" : "bg-transparent text-blue-700 dark:text-blue-300"}`}
                    >
                      ASAP
                    </button>
                  </div>
                </div>

                <p className="text-[11px] text-blue-800/80 dark:text-blue-200/80">
                  AFK uses setup cost once per harvest window. ASAP amortizes setup cost over the hours below.
                </p>

                {harvestMode === "afk" ? (
                  <div className="space-y-2">
                    <label className="text-xs font-medium block">AFK Harvest Input</label>
                    <div className="flex bg-white/70 dark:bg-neutral-900/50 rounded-lg p-1 border border-blue-200 dark:border-blue-900/40 text-xs">
                      <button
                        type="button"
                        onClick={() => setAfkInputMode("stages")}
                        className={`flex-1 rounded-md py-1 ${afkInputMode === "stages" ? "bg-blue-600 text-white" : "text-blue-700 dark:text-blue-300"}`}
                      >
                        After N Stages
                      </button>
                      <button
                        type="button"
                        onClick={() => setAfkInputMode("hours")}
                        className={`flex-1 rounded-md py-1 ${afkInputMode === "hours" ? "bg-blue-600 text-white" : "text-blue-700 dark:text-blue-300"}`}
                      >
                        After T Hours
                      </button>
                    </div>
                    {afkInputMode === "stages" ? (
                      <>
                        <input
                          type="number"
                          min="0"
                          value={afkStages}
                          onChange={(e) => setAfkStages(Math.max(0, Math.floor(Number(e.target.value) || 0)))}
                          className="w-full bg-white dark:bg-neutral-800 border border-blue-200 dark:border-blue-900/40 rounded-lg px-3 py-1.5 text-sm"
                        />
                        <p className="text-[11px] text-blue-800/80 dark:text-blue-200/80">
                          Set to 0 to use each mutation&apos;s default growth cycles.
                        </p>
                      </>
                    ) : (
                      <>
                        <input
                          type="number"
                          min="0"
                          value={afkHours}
                          onChange={(e) => setAfkHours(Math.max(0, Number(e.target.value) || 0))}
                          className="w-full bg-white dark:bg-neutral-800 border border-blue-200 dark:border-blue-900/40 rounded-lg px-3 py-1.5 text-sm"
                        />
                        <p className="text-[11px] text-blue-800/80 dark:text-blue-200/80">
                          Derived stages are computed from hours and cycle time (0 hours uses each mutation default).
                        </p>
                      </>
                    )}
                  </div>
                ) : null}

                <div className="space-y-2">
                  <label className="inline-flex items-center gap-2 text-xs font-medium">
                    <input
                      type="checkbox"
                      checked={useSameFortune}
                      onChange={(e) => setUseSameFortune(e.target.checked)}
                      className="accent-blue-600"
                    />
                    Use same fortune for both
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="number"
                      min="0"
                      max="4000"
                      value={fortuneAfk}
                      onChange={(e) => {
                        const next = applyFortuneChange("afk", Number(e.target.value), useSameFortune, { fortuneAfk, fortuneAsap });
                        setFortuneAfk(next.fortuneAfk);
                        setFortuneAsap(next.fortuneAsap);
                      }}
                      className="w-full bg-white dark:bg-neutral-800 border border-blue-200 dark:border-blue-900/40 rounded-lg px-3 py-1.5 text-sm"
                      aria-label="Fortune AFK"
                    />
                    <input
                      type="number"
                      min="0"
                      max="4000"
                      value={fortuneAsap}
                      onChange={(e) => {
                        const next = applyFortuneChange("asap", Number(e.target.value), useSameFortune, { fortuneAfk, fortuneAsap });
                        setFortuneAfk(next.fortuneAfk);
                        setFortuneAsap(next.fortuneAsap);
                      }}
                      className="w-full bg-white dark:bg-neutral-800 border border-blue-200 dark:border-blue-900/40 rounded-lg px-3 py-1.5 text-sm"
                      aria-label="Fortune ASAP"
                      disabled={useSameFortune}
                    />
                  </div>
                  <p className="text-[11px] text-blue-800/80 dark:text-blue-200/80">Left: Fortune (AFK), Right: Fortune (ASAP)</p>
                </div>

                <div className="grid grid-cols-1 gap-2">
                  <label className="text-xs font-medium">Buff Cost (AFK, per harvest)</label>
                  <input
                    type="number"
                    min="0"
                    value={buffCostAfkPerHarvest}
                    onChange={(e) => setBuffCostAfkPerHarvest(Math.max(0, Number(e.target.value) || 0))}
                    className="w-full bg-white dark:bg-neutral-800 border border-blue-200 dark:border-blue-900/40 rounded-lg px-3 py-1.5 text-sm"
                  />

                  <label className="text-xs font-medium">Buff Cost (ASAP, per hour)</label>
                  <input
                    type="number"
                    min="0"
                    value={buffCostAsapPerHour}
                    onChange={(e) => setBuffCostAsapPerHour(Math.max(0, Number(e.target.value) || 0))}
                    className="w-full bg-white dark:bg-neutral-800 border border-blue-200 dark:border-blue-900/40 rounded-lg px-3 py-1.5 text-sm"
                  />

                  <label className="text-xs font-medium">Extra Setup Cost (coins)</label>
                  <input
                    type="number"
                    min="0"
                    value={extraSetupCost}
                    onChange={(e) => setExtraSetupCost(Math.max(0, Number(e.target.value) || 0))}
                    className="w-full bg-white dark:bg-neutral-800 border border-blue-200 dark:border-blue-900/40 rounded-lg px-3 py-1.5 text-sm"
                  />
                  <label className="text-xs font-medium">ASAP Setup Amortize Hours</label>
                  <input
                    type="number"
                    min="0"
                    value={asapSetupAmortizeHours}
                    onChange={(e) => setAsapSetupAmortizeHours(Math.max(0, Number(e.target.value) || 0))}
                    className="w-full bg-white dark:bg-neutral-800 border border-blue-200 dark:border-blue-900/40 rounded-lg px-3 py-1.5 text-sm"
                  />
                </div>
              </div>
            )}

            {/* Greenhouse Upgrade Slider */}
            <div className="mb-6">
              <label className="flex justify-between text-sm font-medium mb-2">
                <span>Greenhouse Upgrades</span>
                <span className="text-emerald-600 dark:text-emerald-400">{ghUpgrade}/9</span>
              </label>
              <input
                type="range"
                min="0"
                max="9"
                value={ghUpgrade}
                onChange={(e) => setGhUpgrade(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
            </div>

            {/* Unique Crops Slider */}
            <div className="mb-4">
              <label className="flex justify-between text-sm font-medium mb-2">
                <span>Unique Crops Placed</span>
                <span className="text-emerald-600 dark:text-emerald-400">{uniqueCrops}/12</span>
              </label>
              <input
                type="range"
                min="0"
                max="12"
                value={uniqueCrops}
                onChange={(e) => setUniqueCrops(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
            </div>

            {data && (
              <div className="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-800">
                <p className="text-sm text-neutral-500 dark:text-neutral-400">Cycle Time</p>
                <div className="flex items-center gap-2 mt-1 font-mono text-lg font-medium text-amber-600 dark:text-amber-400">
                  <Clock className="w-5 h-5" />
                  {formatDuration(data.metadata.cycle_time_hours)}
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* MAIN CONTENT: LEADERBOARD */}
        <main className="flex-1 min-w-0 space-y-8">

          {/* CROP MILESTONES SECTION */}
          {mode === "smart" && (
            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
              <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                <div className="p-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg">
                  <ArrowUpRight className="w-4 h-4" />
                </div>
                Smart Milestones
              </h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
                Missing milestone tabs and per-harvest progress. Maxed selections are saved locally.
              </p>

              <div className="flex flex-wrap gap-2 mb-5" role="tablist" aria-label="Missing milestones">
                <button
                  role="tab"
                  aria-selected={activeSmartTab === "all"}
                  onClick={() => setSmartTab("all")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${activeSmartTab === "all"
                    ? "bg-emerald-500 text-white border-emerald-500"
                    : "bg-neutral-50 text-neutral-600 border-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700"}`}
                >
                  All Missing
                </button>
                {missingCrops.map((crop) => (
                  <button
                    key={crop}
                    role="tab"
                    aria-selected={activeSmartTab === crop}
                    onClick={() => setSmartTab(crop)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${activeSmartTab === crop
                      ? "bg-blue-500 text-white border-blue-500"
                      : "bg-neutral-50 text-neutral-600 border-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700"}`}
                  >
                    {toCropLabel(crop)}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                {displayCrops.map(crop => (
                  <button
                    key={crop.key}
                    onClick={() => toggleMaxedCrop(crop.key)}
                    className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${maxedCrops.includes(crop.key)
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-800 dark:text-emerald-400'
                      : 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-400'
                      }`}
                    aria-label={`${crop.label} milestone ${maxedCrops.includes(crop.key) ? "maxed" : "needed"}`}
                  >
                    <span className="truncate">{crop.label}</span>
                    <span
                      className={`shrink-0 inline-flex items-center justify-center w-4 h-4 rounded-sm border text-[10px] leading-none ${
                        maxedCrops.includes(crop.key)
                          ? "bg-emerald-500 border-emerald-500 text-white"
                          : "border-blue-500/60 bg-transparent text-transparent"
                      }`}
                      aria-hidden="true"
                    >
                      ✓
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="bg-white dark:bg-neutral-900 rounded-2xl shadow-sm border border-neutral-200 dark:border-neutral-800 overflow-hidden">
            <div className="px-6 py-5 border-b border-neutral-200 dark:border-neutral-800 flex justify-between items-center bg-neutral-50/50 dark:bg-neutral-900/50">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Coins className="w-5 h-5 text-amber-500" />
                {mode === "profit"
                  ? "Profit Leaderboard"
                  : mode === "smart"
                    ? "Smart Milestone Progress"
                    : `${targetCrop} Optimization`}
              </h2>
              <div className="flex items-center gap-2">
                {mode === "smart" && visibleSmartCrops.length > 6 && (
                  <>
                    <button type="button" onClick={() => scrollLeaderboardBy(-420)} className="px-2 py-1 text-xs rounded border border-neutral-300 dark:border-neutral-700">←</button>
                    <button type="button" onClick={() => scrollLeaderboardBy(420)} className="px-2 py-1 text-xs rounded border border-neutral-300 dark:border-neutral-700">→</button>
                  </>
                )}
                {loading && <Loader2 className="w-5 h-5 animate-spin text-emerald-500" />}
              </div>
            </div>

            <div className="overflow-x-auto" ref={tableScrollRef}>
              {error ? (
                <div className="p-8 text-center text-red-500 bg-red-50 dark:bg-red-950/20 m-4 rounded-xl">
                  {error}
                </div>
              ) : !data ? (
                <div className="p-12 text-center text-neutral-500 flex flex-col items-center gap-3">
                  <Loader2 className="w-8 h-8 animate-spin text-neutral-300 dark:text-neutral-700" />
                  <p>Calculating leaderboard data...</p>
                </div>
              ) : (
                mode === "smart" && missingCrops.length === 0 ? (
                  <div className="p-10 text-center text-neutral-500 dark:text-neutral-400">
                    All milestone crops are marked as maxed.
                  </div>
                ) : (
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-neutral-100 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400 border-b border-neutral-200 dark:border-neutral-800">
                    <tr>
                      <th className="px-6 py-4 font-semibold w-16 text-center">
                        <button type="button" onClick={() => toggleSort("rank")} className="inline-flex items-center gap-1">
                          Rank <span aria-hidden="true">{sortIndicator("rank")}</span>
                        </button>
                      </th>
                      <th className="px-6 py-4 font-semibold">
                        <button type="button" onClick={() => toggleSort("mutation")} className="inline-flex items-center gap-1">
                          Mutation <span aria-hidden="true">{sortIndicator("mutation")}</span>
                        </button>
                      </th>
                      {mode === "smart" ? (
                        visibleSmartCrops.map((crop) => (
                          <th key={crop} className="px-6 py-4 font-semibold text-right text-blue-600 dark:text-blue-400">
                            {toCropLabel(crop)}
                          </th>
                        ))
                      ) : (
                        <th className="px-6 py-4 font-semibold text-right text-emerald-600 dark:text-emerald-400">
                          <button type="button" onClick={() => toggleSort("value")} className="inline-flex items-center gap-1">
                            {mode === "profit" ? "Profit / Harvest" : `${targetCrop} Yield`} <span aria-hidden="true">{sortIndicator("value")}</span>
                          </button>
                        </th>
                      )}
                      <th className="px-6 py-4 font-semibold text-right hidden lg:table-cell text-emerald-600 dark:text-emerald-400">
                        <button type="button" onClick={() => toggleSort("profitCycle")} className="inline-flex items-center gap-1">
                          Profit / Cycle <span aria-hidden="true">{sortIndicator("profitCycle")}</span>
                        </button>
                      </th>
                      {mode === "profit" && (
                        <th className="px-6 py-4 font-semibold text-right hidden xl:table-cell text-emerald-600 dark:text-emerald-400">
                          <button type="button" onClick={() => toggleSort("profitHour")} className="inline-flex items-center gap-1">
                            Mutation Profit / Hour <span aria-hidden="true">{sortIndicator("profitHour")}</span>
                          </button>
                        </th>
                      )}
                      <th className="px-6 py-4 font-semibold text-right hidden md:table-cell">
                        <button type="button" onClick={() => toggleSort("cycles")} className="inline-flex items-center gap-1">
                          Growth Cycles <span aria-hidden="true">{sortIndicator("cycles")}</span>
                        </button>
                      </th>
                      <th className="px-6 py-4 font-semibold text-right hidden lg:table-cell">
                        Time
                      </th>
                      <th className="px-6 py-4 font-semibold text-right hidden sm:table-cell">
                        <button type="button" onClick={() => toggleSort("setup")} className="inline-flex items-center gap-1">
                          Setup Cost <span aria-hidden="true">{sortIndicator("setup")}</span>
                        </button>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedLeaderboard.map((item, idx) => (
                      <tr
                        key={item.mutationName}
                        onClick={() => setSelectedMutation(item)}
                        title="Click to view setup requirements!"
                        className={`cursor-pointer border-b border-neutral-100 dark:border-neutral-800 last:border-0 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors ${idx === 0 ? 'bg-amber-50/50 dark:bg-amber-900/10' : ''}`}
                      >
                        <td className="px-6 py-4 text-center">
                          {idx === 0 ? (
                            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400 font-bold text-xs ring-1 ring-amber-500/20">
                              {idx + 1}
                            </span>
                          ) : (
                            <span className="text-neutral-400 font-mono">{idx + 1}</span>
                          )}
                        </td>
                        <td className="px-6 py-4 font-medium flex items-center gap-3">
                          <div className="w-8 h-8 shrink-0 flex items-center justify-center bg-neutral-100 dark:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700 text-lg">
                            <Sprout className="w-4 h-4 text-emerald-500" />
                          </div>
                          <div>
                            <span className="hover:text-amber-500 transition-colors">{item.mutationName}</span>
                            {idx === 0 && <span className="ml-2 text-[10px] uppercase tracking-wider font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/30 px-2 py-0.5 rounded-full inline-block mt-1">Top Pick</span>}
                          </div>
                        </td>
                        {mode === "smart" ? (
                          visibleSmartCrops.map((crop) => (
                            <td key={`${item.mutationName}-${crop}`} className="px-6 py-4 text-right font-mono font-bold text-blue-600 dark:text-blue-400">
                              {(item.smart_progress?.[crop] ?? 0).toFixed(1)}%
                            </td>
                          ))
                        ) : (
                          <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                            <div className="flex items-center justify-end gap-2">
                              {item.warning && (
                                <div className="group relative">
                                  <AlertTriangle className="w-4 h-4 text-yellow-500 hover:text-yellow-600" />
                                  <div className="absolute bottom-full right-0 mb-2 w-48 p-2 bg-neutral-900 text-xs text-white rounded opacity-0 group-hover:opacity-100 transition-opacity z-10 text-center font-sans tracking-wide">
                                    Warning: Spreads are wide. Double check orders!
                                  </div>
                                </div>
                              )}
                              {formatCoins(mode === "target" ? item.score : item.profit)}
                            </div>
                          </td>
                        )}
                        <td className="px-6 py-4 text-right font-mono hidden lg:table-cell text-emerald-600 dark:text-emerald-400">
                          {formatCoins(item.profit_per_cycle)}
                        </td>
                        {mode === "profit" && (
                          <td className="px-6 py-4 text-right font-mono hidden xl:table-cell text-emerald-600 dark:text-emerald-400">
                            {formatCoins(mutationProfitByName[item.mutationName]?.profitHr ?? 0)}
                          </td>
                        )}
                        <td className="px-6 py-4 text-right font-mono text-neutral-500 hidden md:table-cell">
                          {mode === "profit"
                            ? `${mutationProfitByName[item.mutationName]?.stages ?? item.breakdown.growth_stages} Cycles`
                            : `${item.breakdown.growth_stages} Cycles`}
                        </td>
                        <td className="px-6 py-4 text-right font-mono text-neutral-500 hidden lg:table-cell">
                          {mode === "profit"
                            ? formatDuration(mutationProfitByName[item.mutationName]?.harvestHours ?? item.breakdown.estimated_time_hours)
                            : formatDuration(item.breakdown.estimated_time_hours)}
                        </td>
                        <td className="px-6 py-4 text-right font-mono opacity-[0.65] hidden sm:table-cell">
                          {formatCoins(item.opt_cost)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                )
              )}
            </div>
          </div>

          <div className="rounded-xl border border-amber-200/70 bg-amber-50/80 px-4 py-3 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
            Results are based on community-tested assumptions, and some crop behaviors may still be uncertain. Verify key values in-game before placing large orders.
          </div>
        </main>
      </div>

      {/* Modal Overlay */}
      {selectedMutation && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200" onClick={() => setSelectedMutation(null)}>
          <div className="bg-white dark:bg-neutral-900 rounded-2xl w-full max-w-lg max-h-[90vh] shadow-2xl border border-neutral-200 dark:border-neutral-800 overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between bg-neutral-50/50 dark:bg-neutral-900/50">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 shrink-0 flex items-center justify-center bg-emerald-100 dark:bg-emerald-900/30 rounded-xl border border-emerald-200 dark:border-emerald-800 text-2xl shadow-sm">
                  <Sprout className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-xl font-bold">{selectedMutation.mutationName} Breakdown</h3>
                  <p className="text-sm text-neutral-500">For {plots} Placed Plot{plots > 1 ? 's' : ''}</p>
                </div>
              </div>
              <button className="text-neutral-400 hover:text-neutral-600 transition-colors p-1" onClick={() => setSelectedMutation(null)}>
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar">
              <div className="bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30 rounded-xl p-4 text-sm text-emerald-800 dark:text-emerald-200">
                You can plant <span className="font-bold">{selectedMutation.breakdown.base_limit}x {selectedMutation.mutationName}</span> in 1 Plot.
                <br />With {plots} plot(s) total ({selectedMutation.limit}x {selectedMutation.mutationName}), {selectedMutation.breakdown.ingredients.length === 0 ? "this requires no ingredients!" : "this requires:"}
              </div>

              {selectedMutation.breakdown.ingredients.length > 0 && (
                <div className="space-y-3">
                  {selectedMutation.breakdown.ingredients.map((ing) => (
                    <div key={ing.name} className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg border border-neutral-100 dark:border-neutral-800">
                      <div className="flex items-center gap-3">
                        <span className="font-medium">{ing.amount}x <span className="text-emerald-700 dark:text-emerald-300">{toCropLabel(ing.name)}</span></span>
                      </div>
                      <div className="text-right">
                        <div className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">{formatCoins(ing.total_cost)} coins</div>
                        <div className="text-[10px] text-neutral-400 font-mono mt-0.5">{formatCoins(ing.unit_price)} each</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex justify-between items-center pt-4 border-t border-neutral-200 dark:border-neutral-800">
                <span className="font-medium">Total Setup Cost</span>
                <span className="font-mono text-lg font-bold text-amber-500">{formatCoins(selectedMutation.breakdown.total_setup_cost)} coins</span>
              </div>

              <div className="pt-6">
                <h4 className="font-bold mb-3 flex items-center justify-between text-emerald-700 dark:text-emerald-400">
                  <span>Expected Harvest Yields</span>
                  <span className="text-sm font-normal text-neutral-500 dark:text-neutral-400">~{data ? formatDuration(data.metadata.cycle_time_hours) : "0m"} Cycle</span>
                </h4>

                <div className="p-5 bg-blue-500/10 rounded-2xl border border-blue-500/20 space-y-4">
                  {(selectedMutation.mutationName === "Magic Jellybean" || selectedMutation.mutationName === "All-in Aloe") && (
                    <div className="p-3 bg-blue-500/10 rounded-xl border border-blue-500/20 mb-4">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                        <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed font-medium">
                          {selectedMutation.mutationName === "Magic Jellybean"
                            ? "Magic Jellybean is exceptionally rare and has 120 growth stages! It will take significantly longer to reach full maturity than standard crops."
                            : "For All-in Aloe, the optimal harvest stage is Stage 14 to avoid the maturity reset mechanic."}
                        </p>
                      </div>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-bold text-blue-700 dark:text-blue-400">
                      <Clock className="w-4 h-4" />
                      Growth Cycles:
                    </div>
                    <span className="bg-blue-600 text-white px-3 py-1 rounded-lg text-xs font-black">{selectedMutation.breakdown.growth_stages} Cycles</span>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-blue-500/20">
                    <span className="text-xs font-medium text-blue-600 dark:text-blue-400">Estimated Lifecycle Time:</span>
                    <span className="text-sm font-black text-blue-700 dark:text-blue-300">{formatDuration(selectedMutation.breakdown.estimated_time_hours)}</span>
                  </div>
                </div>

                {mode === "profit" && selectedMutationModel && (
                  <div className="mt-4 p-4 bg-emerald-500/10 rounded-2xl border border-emerald-500/20 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-emerald-700 dark:text-emerald-300">Harvest Mode</span>
                      <span className="font-mono text-emerald-700 dark:text-emerald-300">
                        {harvestMode === "afk" ? "AFK (harvest all at once)" : "ASAP (harvest when ready)"}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono text-emerald-800 dark:text-emerald-200">
                      <div className="rounded-lg bg-emerald-500/10 px-2 py-1">
                        {harvestMode === "afk" ? "Expected Mutations / Harvest" : "Expected Mutations / Stage"}: {selectedMutationModel.expectedMutations.toFixed(2)}
                      </div>
                      <div className="rounded-lg bg-emerald-500/10 px-2 py-1">
                        {harvestMode === "afk" ? "Window Time" : "Stage Time"}: {formatDuration(selectedMutationModel.harvestHours)}
                      </div>
                      <div className="rounded-lg bg-emerald-500/10 px-2 py-1">
                        Revenue: {formatCoins(selectedMutationModel.revenue)}
                      </div>
                      <div className="rounded-lg bg-emerald-500/10 px-2 py-1">
                        Costs: {formatCoins(selectedMutationModel.costs)}
                      </div>
                      <div className="rounded-lg bg-emerald-500/10 px-2 py-1">
                        Net: {formatCoins(selectedMutationModel.net)}
                      </div>
                      <div className="rounded-lg bg-emerald-600/20 px-2 py-1 font-bold">
                        Profit / Hour: {formatCoins(selectedMutationModel.profitHr)}
                      </div>
                    </div>
                  </div>
                )}

                {selectedMutation.breakdown.yields && selectedMutation.breakdown.yields.length > 0 ? (
                  <div className="space-y-3">
                    {selectedMutation.breakdown.yields.map((yld) => (
                      <div key={yld.name} className="flex flex-col p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg border border-neutral-100 dark:border-neutral-800">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-3">
                            <span className="font-medium">{formatCoins(yld.amount)}x <span className="text-emerald-700 dark:text-emerald-300">{toCropLabel(yld.name)}</span></span>
                          </div>
                          <div className="text-right">
                            <div className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">{formatCoins(yld.total_value)} coins</div>
                            <div className="text-[10px] text-neutral-400 font-mono mt-0.5">{formatCoins(yld.unit_price)} each</div>
                          </div>
                        </div>
                        {yld.math && (
                          <div className="text-[10px] text-neutral-400 font-mono bg-neutral-100 dark:bg-neutral-800 px-2 py-1 rounded w-fit border border-neutral-200 dark:border-neutral-700/50">
                            Calculation: {formatYieldCalculation(yld.math, yld.unit_price)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-neutral-500 italic">No direct harvest yields.</p>
                )}

                <div className="flex justify-between items-center p-6 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
                  <span className="font-bold text-emerald-700 dark:text-emerald-400">Total Batch Revenue</span>
                  <span className="text-2xl font-mono font-black text-emerald-600 dark:text-emerald-400">+{formatCoins(selectedMutation.breakdown.total_revenue)} coins</span>
                </div>

                <div className="flex justify-between items-center p-6 bg-emerald-500 rounded-2xl shadow-xl shadow-emerald-500/20 text-white">
                  <span className="font-black uppercase tracking-wider text-sm">Expected Net Profit</span>
                  <span className="text-2xl font-mono font-black">
                    {formatCoins(selectedMutation.breakdown.total_revenue - selectedMutation.breakdown.total_setup_cost)} coins
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(16, 185, 129, 0.2);
          border-radius: 20px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(16, 185, 129, 0.4);
        }
      `}</style>
    </div>
  );
}

