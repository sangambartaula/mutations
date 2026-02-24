"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { ModeToggle } from "@/components/mode-toggle";
import { Coins, Sprout, Clock, Calculator, Loader2, ArrowUpRight, AlertTriangle, X, Info } from "lucide-react";
import Image from "next/image";

type OptimizationMode = "profit" | "smart" | "target";
type SetupMode = "buy_order" | "insta_buy";
type SellMode = "sell_offer" | "insta_sell";
type SortKey = "rank" | "mutation" | "value" | "cycle_profit" | "cycles" | "setup";
type SortDirection = "asc" | "desc";

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
    profit_per_hour_selected?: number | null;
    g?: number | null;
    warnings?: string[];
  };
  breakdown: MutationBreakdown;
};

type LeaderboardResponse = {
  leaderboard: LeaderboardItem[];
  metadata: {
    cycle_time_hours: number;
    missing_crops?: string[];
    fortune_breakdown?: {
      base_fortune: number;
      effective_fortune: number;
      bonus_total: number;
      harvest_harbinger: boolean;
      infini_vacuum: boolean;
      dark_cacao: boolean;
      hypercharge_level: number;
      affected_multiplier: number;
    };
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
const toMutationLabel = (mutation: string) => {
  if (mutation === "TURTLELLINI") return "Turtlellini";
  if (mutation === "Plant Boy Advance") return "PlantBoy Advance";
  return mutation;
};
const toMutationIconPath = (mutationName: string) =>
  `/icons/mutations/${mutationName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")}.png`;
const netProfitPerCycleTooltipLines = [
  "Setup-amortized net profit per global growth tick.",
  "Computed as: Net Profit / Harvest divided by expected cycles per harvest.",
  "Expected cycles per harvest = (1 / p) + g.",
  "This keeps cycle sign aligned with overall per-harvest profitability.",
  "Profit / Hour = Net Profit / Cycle / tau.",
];

export default function Home() {
  const [plots, setPlots] = useState(3);
  const [fortune, setFortune] = useState(2500);
  const [useImprovedHarvestBoost, setUseImprovedHarvestBoost] = useState(true);
  const [useHarvestHarbinger, setUseHarvestHarbinger] = useState(false);
  const [useInfiniVacuum, setUseInfiniVacuum] = useState(false);
  const [useDarkCacao, setUseDarkCacao] = useState(false);
  const [hyperchargeLevel, setHyperchargeLevel] = useState(0);
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
  const activeLeaderboardRequestRef = useRef(0);

  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const maxedCropsQuery = useMemo(() => maxedCrops.join(","), [maxedCrops]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("mutations:maxed-crops");
      if (saved) {
        const parsed: unknown = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          setMaxedCrops(parsed.filter((v): v is string => typeof v === "string"));
        }
      }
    } catch {
      // Ignore malformed local storage data.
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("mutations:maxed-crops", JSON.stringify(maxedCrops));
    } catch {
      // Ignore local storage write failures.
    }
  }, [maxedCrops]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("mutations:settings");
      if (saved) {
        const parsed = JSON.parse(saved) as Record<string, unknown>;
        if (typeof parsed.plots === "number") setPlots(Math.max(1, Math.min(3, parsed.plots)));
        if (typeof parsed.fortune === "number") setFortune(Math.max(0, Math.min(4000, parsed.fortune)));
        if (typeof parsed.useImprovedHarvestBoost === "boolean") setUseImprovedHarvestBoost(parsed.useImprovedHarvestBoost);
        if (typeof parsed.useHarvestHarbinger === "boolean") setUseHarvestHarbinger(parsed.useHarvestHarbinger);
        if (typeof parsed.useInfiniVacuum === "boolean") setUseInfiniVacuum(parsed.useInfiniVacuum);
        if (typeof parsed.useDarkCacao === "boolean") setUseDarkCacao(parsed.useDarkCacao);
        if (typeof parsed.hyperchargeLevel === "number") setHyperchargeLevel(Math.max(0, Math.min(20, parsed.hyperchargeLevel)));
        if (typeof parsed.ghUpgrade === "number") setGhUpgrade(Math.max(0, Math.min(9, parsed.ghUpgrade)));
        if (typeof parsed.uniqueCrops === "number") setUniqueCrops(Math.max(0, Math.min(12, parsed.uniqueCrops)));
        if (parsed.setupMode === "buy_order" || parsed.setupMode === "insta_buy") setSetupMode(parsed.setupMode);
        if (parsed.sellMode === "sell_offer" || parsed.sellMode === "insta_sell") setSellMode(parsed.sellMode);
      }
    } catch {
      // Ignore malformed local storage data.
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("mutations:settings", JSON.stringify({
        plots,
        fortune,
        useImprovedHarvestBoost,
        useHarvestHarbinger,
        useInfiniVacuum,
        useDarkCacao,
        hyperchargeLevel,
        ghUpgrade,
        uniqueCrops,
        setupMode,
        sellMode,
      }));
    } catch {
      // Ignore local storage write failures.
    }
  }, [
    plots,
    fortune,
    useImprovedHarvestBoost,
    useHarvestHarbinger,
    useInfiniVacuum,
    useDarkCacao,
    hyperchargeLevel,
    ghUpgrade,
    uniqueCrops,
    setupMode,
    sellMode,
  ]);

  useEffect(() => {
    const controller = new AbortController();
    const requestId = activeLeaderboardRequestRef.current + 1;
    activeLeaderboardRequestRef.current = requestId;
    const timeoutHandle = window.setTimeout(() => controller.abort(), 15000);

    const query = new URLSearchParams({
      plots: plots.toString(),
      fortune: fortune.toString(),
      improved_harvest_boost: useImprovedHarvestBoost ? "true" : "false",
      harvest_harbinger: useHarvestHarbinger ? "true" : "false",
      infini_vacuum: useInfiniVacuum ? "true" : "false",
      dark_cacao: useDarkCacao ? "true" : "false",
      hypercharge_level: hyperchargeLevel.toString(),
      gh_upgrade: ghUpgrade.toString(),
      unique_crops: uniqueCrops.toString(),
      mode: mode,
      setup_mode: setupMode,
      sell_mode: sellMode,
      maxed_crops: maxedCropsQuery,
      ...(mode === "target" && { target_crop: targetCrop })
    });
    const queryString = query.toString();

    setLoading(true);
    setError("");

    (async () => {
      try {
        const res = await fetch(`/api/leaderboard?${queryString}&t=${Date.now()}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!res.ok) throw new Error("Failed to fetch leaderboard data.");
        const json: LeaderboardResponse = await res.json();
        if (requestId !== activeLeaderboardRequestRef.current) return;
        setData(json);
      } catch (err: unknown) {
        if (requestId !== activeLeaderboardRequestRef.current) return;
        if ((err as Error)?.name === "AbortError") {
          setError("Leaderboard request timed out. Check backend connectivity.");
          return;
        }
        setError(err instanceof Error ? err.message : "Unexpected error while fetching leaderboard data.");
      } finally {
        window.clearTimeout(timeoutHandle);
        if (requestId === activeLeaderboardRequestRef.current) {
          setLoading(false);
        }
      }
    })();

    return () => {
      controller.abort();
      window.clearTimeout(timeoutHandle);
    };
  }, [
    plots,
    fortune,
    useImprovedHarvestBoost,
    useHarvestHarbinger,
    useInfiniVacuum,
    useDarkCacao,
    hyperchargeLevel,
    ghUpgrade,
    uniqueCrops,
    mode,
    setupMode,
    sellMode,
    targetCrop,
    maxedCropsQuery,
  ]);

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

  const getGrowthCyclesLabel = (item: LeaderboardItem) => {
    const g = item.hourly?.g;
    if (typeof g === "number") {
      if (g === 0) return "Instant";
      return `${g} Cycles`;
    }
    const fallback = item.breakdown.growth_stages;
    if (fallback === 0) return "Instant";
    return `${fallback} Cycles`;
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
    if (key === "cycle_profit") return mode === "profit" ? item.profit_per_cycle : item.score;
    if (key === "cycles") return item.hourly?.g ?? item.breakdown.growth_stages;
    if (key === "setup") return item.opt_cost;
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
              {data?.metadata.fortune_breakdown && (
                <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300">
                  Effective Fortune: {Math.round(data.metadata.fortune_breakdown.effective_fortune)} (+{Math.round(data.metadata.fortune_breakdown.bonus_total)})
                </p>
              )}
            </div>

            <div className="mb-6 rounded-xl border border-neutral-200 dark:border-neutral-800 p-3 space-y-3">
              <p className="text-sm font-medium">Fortune Buffs</p>

              <label className="flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 text-xs">
                  Improved Harvest Boost (+30% crop yield)
                </span>
                <input type="checkbox" checked={useImprovedHarvestBoost} onChange={(e) => setUseImprovedHarvestBoost(e.target.checked)} className="accent-emerald-500" />
              </label>

              <label className="flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 text-xs">
                  <Image src="/icons/buffs/harvest-harbinger-potion.png" alt="Harvest Harbinger Potion" width={20} height={20} className="w-5 h-5 rounded-sm" />
                  Harvest Harbinger (+50, unaffected)
                </span>
                <input type="checkbox" checked={useHarvestHarbinger} onChange={(e) => setUseHarvestHarbinger(e.target.checked)} className="accent-emerald-500" />
              </label>

              <label className="flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 text-xs">
                  <Image src="/icons/buffs/infini-vacuum-hooverius.png" alt="InfiniVacuum Hooverius" width={20} height={20} className="w-5 h-5 rounded-sm" />
                  Pest Buff (+200)
                </span>
                <input type="checkbox" checked={useInfiniVacuum} onChange={(e) => setUseInfiniVacuum(e.target.checked)} className="accent-emerald-500" />
              </label>

              <label className="flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 text-xs">
                  <Image src="/icons/buffs/refined-dark-cacao-truffle.png" alt="Refined Dark Cacao Truffle" width={20} height={20} className="w-5 h-5 rounded-sm" />
                  Refined Dark Cacao Truffle (+30, affected)
                </span>
                <input type="checkbox" checked={useDarkCacao} onChange={(e) => setUseDarkCacao(e.target.checked)} className="accent-emerald-500" />
              </label>

              <div>
                <label className="flex items-center justify-between text-xs mb-1">
                  <span className="inline-flex items-center gap-2">
                    <Image src="/icons/buffs/hypercharge-chip.png" alt="Hypercharge Chip" width={20} height={20} className="w-5 h-5 rounded-sm" />
                    Hypercharge Chip Level (0-20)
                  </span>
                  <span className="text-emerald-600 dark:text-emerald-400">{hyperchargeLevel}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="20"
                  step="1"
                  value={hyperchargeLevel}
                  onChange={(e) => setHyperchargeLevel(Number(e.target.value))}
                  className="w-full accent-emerald-500"
                />
                <p className="text-[11px] text-neutral-500 mt-1">Hypercharge only scales affected buffs (Vacuum + Dark Cacao), up to +100% at level 20.</p>
              </div>
            </div>

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
              ) : loading && !data ? (
                <div className="p-12 text-center text-neutral-500 flex flex-col items-center gap-3">
                  <Loader2 className="w-8 h-8 animate-spin text-neutral-300 dark:text-neutral-700" />
                  <p>Calculating leaderboard data...</p>
                </div>
              ) : !data ? (
                <div className="p-8 text-center text-neutral-500">
                  No leaderboard data yet. Try refreshing.
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
                      {mode === "profit" && (
                        <th className="px-6 py-4 font-semibold text-right text-sky-600 dark:text-sky-400 hidden lg:table-cell">
                          <div className="inline-flex items-center justify-end gap-2">
                            <button type="button" onClick={() => toggleSort("cycle_profit")} className="inline-flex items-center gap-1">
                              Net Profit / Cycle <span aria-hidden="true">{sortIndicator("cycle_profit")}</span>
                            </button>
                            <div className="group relative">
                              <button
                                type="button"
                                tabIndex={0}
                                aria-label="Net profit per cycle info"
                                className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-sky-500/50 text-[10px] leading-none cursor-help"
                              >
                                <Info className="h-3 w-3" />
                              </button>
                              <div className="absolute left-1/2 top-full z-20 mt-2 w-80 -translate-x-1/2 rounded bg-neutral-900 px-3 py-2 text-left text-[11px] font-normal normal-case tracking-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                                {netProfitPerCycleTooltipLines.map((line) => (
                                  <p key={line} className="leading-snug">
                                    {line}
                                  </p>
                                ))}
                              </div>
                            </div>
                          </div>
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
                            <Image
                              src={toMutationIconPath(item.mutationName)}
                              alt={`${item.mutationName} icon`}
                              width={20}
                              height={20}
                              className="w-5 h-5 object-contain"
                              onError={(e) => {
                                const target = e.currentTarget;
                                target.style.display = "none";
                                target.parentElement?.classList.add("icon-fallback");
                              }}
                            />
                            <Sprout className="w-4 h-4 text-emerald-500 icon-fallback-glyph hidden" />
                          </div>
                          <div>
                            <span className="hover:text-amber-500 transition-colors">{toMutationLabel(item.mutationName)}</span>
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
                              {item.mutationName === "Devourer" && (
                                <div className="group relative">
                                  <AlertTriangle className="w-4 h-4 text-red-500 hover:text-red-400" />
                                  <div className="absolute bottom-full right-0 mb-2 w-64 p-2 bg-neutral-900 text-xs text-white rounded opacity-0 group-hover:opacity-100 transition-opacity z-10 text-left font-sans tracking-wide">
                                    This crop destroys surrounding crops over time. You must remove adjacent blocks to prevent spread. It is not advised to try and grow all 16 at once but it is possible.
                                  </div>
                                </div>
                              )}
                              {formatCoins(mode === "target" ? item.score : item.profit)}
                            </div>
                          </td>
                        )}
                        {mode === "profit" && (
                          <td className="px-6 py-4 text-right font-mono font-bold text-sky-600 dark:text-sky-400 hidden lg:table-cell">
                            {formatCoins(item.profit_per_cycle)}
                          </td>
                        )}
                        <td className="px-6 py-4 text-right font-mono text-neutral-500 hidden md:table-cell">
                          {getGrowthCyclesLabel(item)}
                        </td>
                        <td className="px-6 py-4 text-right font-mono text-neutral-500 hidden lg:table-cell">
                          {formatDuration(item.breakdown.estimated_time_hours)}
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
            Results are based on community-tested assumptions; verify key values in-game before large orders.
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
                  <Image
                    src={toMutationIconPath(selectedMutation.mutationName)}
                    alt={`${selectedMutation.mutationName} icon`}
                    width={28}
                    height={28}
                    className="w-7 h-7 object-contain"
                    onError={(e) => {
                      const target = e.currentTarget;
                      target.style.display = "none";
                      target.parentElement?.classList.add("icon-fallback");
                    }}
                  />
                  <Sprout className="w-6 h-6 text-emerald-600 dark:text-emerald-400 icon-fallback-glyph hidden" />
                </div>
                <div>
                  <h3 className="text-xl font-bold">{toMutationLabel(selectedMutation.mutationName)} Breakdown</h3>
                  <p className="text-sm text-neutral-500">For {plots} Placed Plot{plots > 1 ? 's' : ''}</p>
                </div>
              </div>
              <button className="text-neutral-400 hover:text-neutral-600 transition-colors p-1" onClick={() => setSelectedMutation(null)}>
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar">
              <div className="bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30 rounded-xl p-4 text-sm text-emerald-800 dark:text-emerald-200">
                You can plant <span className="font-bold">{selectedMutation.breakdown.base_limit}x {toMutationLabel(selectedMutation.mutationName)}</span> in 1 Plot.
                <br />With {plots} plot(s) total ({selectedMutation.limit}x {toMutationLabel(selectedMutation.mutationName)}), {selectedMutation.breakdown.ingredients.length === 0 ? "this requires no ingredients!" : "this requires:"}
              </div>
              {selectedMutation.mutationName === "Devourer" && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 text-sm text-red-800 dark:text-red-200">
                  This crop destroys surrounding crops over time. You must remove adjacent blocks to prevent spread. It is not advised to try and grow all 16 at once but it is possible.
                </div>
              )}

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
                    <span className="bg-blue-600 text-white px-3 py-1 rounded-lg text-xs font-black">
                      {selectedMutation.hourly?.g === 0 ? "Instant" : `${selectedMutation.hourly?.g ?? selectedMutation.breakdown.growth_stages} Cycles`}
                    </span>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-blue-500/20">
                    <span className="text-xs font-medium text-blue-600 dark:text-blue-400">Estimated Lifecycle Time:</span>
                    <span className="text-sm font-black text-blue-700 dark:text-blue-300">{formatDuration(selectedMutation.breakdown.estimated_time_hours)}</span>
                  </div>
                </div>

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
        .icon-fallback .icon-fallback-glyph {
          display: block;
        }
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

