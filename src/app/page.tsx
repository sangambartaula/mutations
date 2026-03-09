"use client";

import { Fragment, useState, useEffect, useMemo, useRef } from "react";
import { ModeToggle } from "@/components/mode-toggle";
import { Coins, Sprout, Clock, Calculator, Loader2, ArrowUpRight, AlertTriangle, X, Info, Sparkles, ChevronDown } from "lucide-react";
import Image from "next/image";

type OptimizationMode = "profit" | "smart" | "target";
type SetupMode = "buy_order" | "insta_buy";
type SellMode = "sell_offer" | "insta_sell";
type SortKey = "mutation" | "value" | "growth_cycle_profit" | "profit_per_hour" | "cycles" | "time" | "setup";
type SortDirection = "asc" | "desc";
type ChipRarity = "rare" | "epic" | "legendary";

type YieldMath = {
  base: number;
  limit: number;
  evergreen_buff?: number;
  gh_buff: number;
  unique_buff: number;
  harvest_boost?: number;
  wart_buff?: number;
  fortune: number;
  overdrive_bonus?: number;
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

type CalculationTone = "neutral" | "plots" | "garden" | "unique" | "evergreen" | "harvest" | "fortune" | "special";

type CalculationStep = {
  label: string;
  value: string;
  tone: CalculationTone;
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
  profit_per_growth_cycle?: number | null;
  profit_per_hour: number;
  opt_cost: number;
  revenue: number;
  warning: boolean;
  warning_messages?: string[];
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
      hypercharge_rarity: ChipRarity;
      affected_multiplier: number;
    };
    yield_breakdown?: {
      base_multiplier: number;
      evergreen_chip_level: number;
      evergreen_chip_rarity: ChipRarity;
      evergreen_bonus: number;
      greenhouse_yield_upgrade: number;
      greenhouse_yield_bonus: number;
      unique_crops: number;
      unique_crop_bonus: number;
      harvest_boost?: boolean;
      improved_harvest_boost?: boolean;
      harvest_boost_multiplier?: number;
      wart_multiplier?: number;
      overdrive_chip_level: number;
      overdrive_chip_rarity: ChipRarity;
      overdrive_crop?: string | null;
      overdrive_bonus: number;
    };
    speed_breakdown?: {
      greenhouse_speed_upgrade: number;
      greenhouse_speed_reduction: number;
      unique_speed_reduction: number;
    };
  };
};

const optimizationModes: { id: OptimizationMode; label: string }[] = [
  { id: "profit", label: "Pure Profit" },
  { id: "smart", label: "Smart (Milestones)" },
  { id: "target", label: "Focus One Crop" },
];
const chipRarityOrder: ChipRarity[] = ["rare", "epic", "legendary"];
const chipRarityConfig: Record<ChipRarity, { label: string; maxLevel: number; hyperchargeRate: number; evergreenRate: number; overdriveBonus: number }> = {
  rare: { label: "Rare", maxLevel: 10, hyperchargeRate: 0.03, evergreenRate: 0.02, overdriveBonus: 5 },
  epic: { label: "Epic", maxLevel: 15, hyperchargeRate: 0.04, evergreenRate: 0.025, overdriveBonus: 6 },
  legendary: { label: "Legendary", maxLevel: 20, hyperchargeRate: 0.05, evergreenRate: 0.03, overdriveBonus: 7 },
};
const asChipRarity = (value: unknown, fallback: ChipRarity = "legendary"): ChipRarity =>
  value === "rare" || value === "epic" || value === "legendary" ? value : fallback;
const clampChipLevelByRarity = (value: number, rarity: ChipRarity) =>
  Math.max(0, Math.min(chipRarityConfig[rarity].maxLevel, value));

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
const setupCostNote = "Some mutations decay after a few days, so setup cost may recur.";
const lonelilyHarvestWarning = {
  label: "LONELILY WARNING",
  lines: [
    "Lonelily has an extremely low spawn probability. Profit per harvest assumes that all planted mutations eventually spawn and grow, which may take a very long time in practice.",
    "For realistic profitability, refer to Profit per Growth Cycle or Profit per Hour instead.",
  ],
};
const getLeaderboardWarningTone = (item: LeaderboardItem) => {
  const hasMechanicalWarning = item.warning_messages?.some((message) => !message.startsWith("Market spreads")) ?? false;

  if (item.mutationName === "Devourer") {
    return {
      label: "Devourer warning",
      icon: "text-red-500 hover:text-red-400",
      panel: "border-red-500/30 bg-red-950/95 text-red-50",
      heading: "text-red-200",
      body: "text-red-100/90",
    };
  }

  if (hasMechanicalWarning) {
    return {
      label: "Mutation warning",
      icon: "text-red-500 hover:text-red-400",
      panel: "border-red-500/30 bg-red-950/95 text-red-50",
      heading: "text-red-200",
      body: "text-red-100/90",
    };
  }

  return {
    label: "Market warning",
    icon: "text-yellow-500 hover:text-yellow-400",
    panel: "border-amber-500/30 bg-neutral-900 text-white",
    heading: "text-amber-200",
    body: "text-white/90",
  };
};
const faqItems = [
  {
    question: "How are profits calculated?",
    answer: [
      "Profit per Harvest is the profit from one full planted batch once everything is grown.",
      "Profit per Growth Cycle adds expected spawn time to the mutation's growth stages. Most mutations use a 25 percent spawn chance per garden growth cycle, so their expected spawn wait is 1 / 0.25 = 4 cycles.",
      "Lonelily uses its own rarer spawn estimate instead. Profit per Hour then converts those expected cycles into real time using the current garden cycle duration.",
      "The Growth Cycles column only shows post-spawn growth stages. If a mutation has 0 growth stages, it will display as 0 Cycles and Instant while the timing metrics still include expected spawn wait.",
    ],
  },
  {
    question: "Why do some crops have warning icons?",
    answer: [
      "Warning icons highlight mutations that have unusual mechanics or conditions that may affect profitability calculations.",
      "These warnings help explain when normal assumptions may not fully reflect in-game behavior.",
      "Some warnings come from special mutation behavior, while others reflect wide Bazaar spreads that can distort pricing.",
    ],
  },
  {
    question: "Why does Devourer have a warning?",
    answer: [
      "Devourer spreads to nearby crops and can destroy surrounding plants over time.",
      "Although it is technically possible to grow many at once, doing so reliably is extremely difficult and generally not recommended. The mutation spreads to nearby crops and can destroy them over time, making large-scale setups inconsistent and risky.",
    ],
  },
  {
    question: "Why does Lonelily behave differently?",
    answer: [
      "Lonelily has a much lower spawn probability than other mutations.",
      "Most mutations assume roughly a 25% spawn chance per valid farmland slot each growth cycle.",
      "Lonelily instead spawns at an estimated rate of roughly 0.45% per slot per cycle.",
      "Because of this extremely low spawn rate, the time required for a full harvest can be very long.",
      "Profit per Harvest therefore represents the theoretical value of a completed harvest, but Profit per Growth Cycle and Profit per Hour provide a more realistic estimate of actual profitability.",
    ],
  },
  {
    question: "Why does Magic Jellybean show very large profits?",
    answer: [
      "Magic Jellybean grows through many stages and increases its multiplier over time.",
      "When allowed to grow to the full 120 stages, it can reach a 10x multiplier, producing extremely large harvest values.",
      "However this also means the mutation takes a very long time to mature.",
    ],
  },
  {
    question: "Why is All-in Aloe calculated differently?",
    answer: [
      "All-in Aloe has a unique mechanic where its multiplier increases over time but can randomly reset each cycle.",
      "Because reaching the maximum multiplier would take an unrealistic amount of time in practice, the calculator assumes harvesting around stage 13-14, which is considered the most efficient point for most setups.",
    ],
  },
] as const;

export default function Home() {
  const [plots, setPlots] = useState(3);
  const [fortune, setFortune] = useState(2500);
  const [useHarvestBoost, setUseHarvestBoost] = useState(false);
  const [useImprovedHarvestBoost, setUseImprovedHarvestBoost] = useState(true);
  const [useHarvestHarbinger, setUseHarvestHarbinger] = useState(false);
  const [useInfiniVacuum, setUseInfiniVacuum] = useState(false);
  const [useDarkCacao, setUseDarkCacao] = useState(false);
  const [hyperchargeLevel, setHyperchargeLevel] = useState(0);
  const [hyperchargeRarity, setHyperchargeRarity] = useState<ChipRarity>("legendary");
  const [ghYieldUpgrade, setGhYieldUpgrade] = useState(9);
  const [ghSpeedUpgrade, setGhSpeedUpgrade] = useState(9);
  const [uniqueCrops, setUniqueCrops] = useState(12);
  const [evergreenChipLevel, setEvergreenChipLevel] = useState(20);
  const [evergreenChipRarity, setEvergreenChipRarity] = useState<ChipRarity>("legendary");
  const [overdriveChipLevel, setOverdriveChipLevel] = useState(0);
  const [overdriveChipRarity, setOverdriveChipRarity] = useState<ChipRarity>("legendary");
  const [overdriveCrop, setOverdriveCrop] = useState("");

  const [mode, setMode] = useState<OptimizationMode>("profit");
  const [targetCrop, setTargetCrop] = useState("Wheat");
  const [maxedCrops, setMaxedCrops] = useState<string[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>("value");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // New Toggles
  const [setupMode, setSetupMode] = useState<SetupMode>("buy_order");
  const [sellMode, setSellMode] = useState<SellMode>("sell_offer");

  // Modal State
  const [selectedMutation, setSelectedMutation] = useState<LeaderboardItem | null>(null);
  const [openFaqQuestion, setOpenFaqQuestion] = useState<string | null>(faqItems[0].question);

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
        if (typeof parsed.useHarvestBoost === "boolean") setUseHarvestBoost(parsed.useHarvestBoost);
        if (typeof parsed.useImprovedHarvestBoost === "boolean") setUseImprovedHarvestBoost(parsed.useImprovedHarvestBoost);
        if (typeof parsed.useHarvestHarbinger === "boolean") setUseHarvestHarbinger(parsed.useHarvestHarbinger);
        if (typeof parsed.useInfiniVacuum === "boolean") setUseInfiniVacuum(parsed.useInfiniVacuum);
        if (typeof parsed.useDarkCacao === "boolean") setUseDarkCacao(parsed.useDarkCacao);
        const parsedHyperchargeRarity = asChipRarity(parsed.hyperchargeRarity);
        setHyperchargeRarity(parsedHyperchargeRarity);
        if (typeof parsed.hyperchargeLevel === "number") {
          setHyperchargeLevel(clampChipLevelByRarity(parsed.hyperchargeLevel, parsedHyperchargeRarity));
        }
        const legacyGhUpgrade = typeof parsed.ghUpgrade === "number"
          ? Math.max(0, Math.min(9, parsed.ghUpgrade))
          : 9;
        if (typeof parsed.ghYieldUpgrade === "number") setGhYieldUpgrade(Math.max(0, Math.min(9, parsed.ghYieldUpgrade)));
        else setGhYieldUpgrade(legacyGhUpgrade);
        if (typeof parsed.ghSpeedUpgrade === "number") setGhSpeedUpgrade(Math.max(0, Math.min(9, parsed.ghSpeedUpgrade)));
        else setGhSpeedUpgrade(legacyGhUpgrade);
        if (typeof parsed.uniqueCrops === "number") setUniqueCrops(Math.max(0, Math.min(12, parsed.uniqueCrops)));
        const parsedEvergreenRarity = asChipRarity(parsed.evergreenChipRarity);
        setEvergreenChipRarity(parsedEvergreenRarity);
        if (typeof parsed.evergreenChipLevel === "number") {
          setEvergreenChipLevel(clampChipLevelByRarity(parsed.evergreenChipLevel, parsedEvergreenRarity));
        }
        const parsedOverdriveRarity = asChipRarity(parsed.overdriveChipRarity);
        setOverdriveChipRarity(parsedOverdriveRarity);
        if (typeof parsed.overdriveChipLevel === "number") {
          setOverdriveChipLevel(clampChipLevelByRarity(parsed.overdriveChipLevel, parsedOverdriveRarity));
        }
        if (typeof parsed.overdriveCrop === "string") setOverdriveCrop(parsed.overdriveCrop);
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
        useHarvestBoost,
        useImprovedHarvestBoost,
        useHarvestHarbinger,
        useInfiniVacuum,
        useDarkCacao,
        hyperchargeLevel,
        hyperchargeRarity,
        ghYieldUpgrade,
        ghSpeedUpgrade,
        uniqueCrops,
        evergreenChipLevel,
        evergreenChipRarity,
        overdriveChipLevel,
        overdriveChipRarity,
        overdriveCrop,
        setupMode,
        sellMode,
      }));
    } catch {
      // Ignore local storage write failures.
    }
  }, [
    plots,
    fortune,
    useHarvestBoost,
    useImprovedHarvestBoost,
    useHarvestHarbinger,
    useInfiniVacuum,
    useDarkCacao,
    hyperchargeLevel,
    hyperchargeRarity,
    ghYieldUpgrade,
    ghSpeedUpgrade,
    uniqueCrops,
    evergreenChipLevel,
    evergreenChipRarity,
    overdriveChipLevel,
    overdriveChipRarity,
    overdriveCrop,
    setupMode,
    sellMode,
  ]);

  useEffect(() => {
    setHyperchargeLevel((current) => clampChipLevelByRarity(current, hyperchargeRarity));
  }, [hyperchargeRarity]);

  useEffect(() => {
    setEvergreenChipLevel((current) => clampChipLevelByRarity(current, evergreenChipRarity));
  }, [evergreenChipRarity]);

  useEffect(() => {
    setOverdriveChipLevel((current) => clampChipLevelByRarity(current, overdriveChipRarity));
  }, [overdriveChipRarity]);

  useEffect(() => {
    if (useHarvestBoost && useImprovedHarvestBoost) {
      setUseHarvestBoost(false);
    }
  }, [useHarvestBoost, useImprovedHarvestBoost]);

  useEffect(() => {
    if (mode !== "profit" && (sortKey === "growth_cycle_profit" || sortKey === "profit_per_hour")) {
      setSortKey("value");
      setSortDirection("desc");
    }
  }, [mode, sortKey]);

  useEffect(() => {
    const controller = new AbortController();
    const requestId = activeLeaderboardRequestRef.current + 1;
    activeLeaderboardRequestRef.current = requestId;
    const timeoutHandle = window.setTimeout(() => controller.abort(), 15000);

    const query = new URLSearchParams({
      plots: plots.toString(),
      fortune: fortune.toString(),
      harvest_boost: useHarvestBoost ? "true" : "false",
      improved_harvest_boost: useImprovedHarvestBoost ? "true" : "false",
      harvest_harbinger: useHarvestHarbinger ? "true" : "false",
      infini_vacuum: useInfiniVacuum ? "true" : "false",
      dark_cacao: useDarkCacao ? "true" : "false",
      hypercharge_level: hyperchargeLevel.toString(),
      hypercharge_rarity: hyperchargeRarity,
      gh_yield_upgrade: ghYieldUpgrade.toString(),
      gh_speed_upgrade: ghSpeedUpgrade.toString(),
      unique_crops: uniqueCrops.toString(),
      evergreen_chip_level: evergreenChipLevel.toString(),
      evergreen_chip_rarity: evergreenChipRarity,
      overdrive_chip_level: overdriveChipLevel.toString(),
      overdrive_chip_rarity: overdriveChipRarity,
      mode: mode,
      setup_mode: setupMode,
      sell_mode: sellMode,
      maxed_crops: maxedCropsQuery,
      ...(overdriveCrop && { overdrive_crop: overdriveCrop }),
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
    useHarvestBoost,
    useImprovedHarvestBoost,
    useHarvestHarbinger,
    useInfiniVacuum,
    useDarkCacao,
    hyperchargeLevel,
    hyperchargeRarity,
    ghYieldUpgrade,
    ghSpeedUpgrade,
    uniqueCrops,
    evergreenChipLevel,
    evergreenChipRarity,
    overdriveChipLevel,
    overdriveChipRarity,
    overdriveCrop,
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

  const markAllMissingAsCompleted = () => {
    setMaxedCrops((prev) => {
      const next = new Set(prev);
      for (const crop of displayCrops) {
        next.add(crop.key);
      }
      return displayCrops.map((crop) => crop.key).filter((crop) => next.has(crop));
    });
  };

  const markAllAsMissing = () => {
    setMaxedCrops([]);
  };

  const handleHarvestBoostToggle = (checked: boolean) => {
    setUseHarvestBoost(checked);
    if (checked) {
      setUseImprovedHarvestBoost(false);
    }
  };

  const handleImprovedHarvestBoostToggle = (checked: boolean) => {
    setUseImprovedHarvestBoost(checked);
    if (checked) {
      setUseHarvestBoost(false);
    }
  };

  const formatCoins = (num: number) => {
    const safe = Number.isFinite(num) ? num : 0;
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(safe);
  };

  const formatSignedCoins = (num: number) => {
    const safe = Number.isFinite(num) ? num : 0;
    return `${safe >= 0 ? "+" : "-"}${formatCoins(Math.abs(safe))}`;
  };

  const formatGrowthCycleProfit = (num: number | null | undefined) => {
    if (typeof num !== "number" || !Number.isFinite(num)) return "N/A";
    return formatCoins(num);
  };

  const formatPreciseValue = (num: number, digits = 2) =>
    num.toLocaleString("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });

  const formatDuration = (hours: number) => {
    const safeHours = Number.isFinite(hours) ? hours : 0;
    const totalMinutes = Math.max(0, Math.round(safeHours * 60));
    const hrs = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;

    if (hrs === 0) return `${mins}m`;
    if (mins === 0) return `${hrs}h`;
    return `${hrs}h ${mins}m`;
  };

  const formatGrowthCyclesDisplay = (cycles: number) => {
    if (!Number.isFinite(cycles) || cycles <= 0) return "0 Cycles";
    if (cycles === 1) return "1 Cycle";
    return `${cycles} Cycles`;
  };

  const formatLifecycleDisplay = (hours: number, growthStages: number) => {
    if (growthStages <= 0) return "Instant";
    return formatDuration(hours);
  };

  const getGrowthCyclesLabel = (item: LeaderboardItem) => {
    const g = item.hourly?.g;
    if (typeof g === "number") {
      return formatGrowthCyclesDisplay(g);
    }
    const fallback = item.breakdown.growth_stages;
    return formatGrowthCyclesDisplay(fallback);
  };

  const getCalculationToneClasses = (tone: CalculationTone) => {
    const tones: Record<CalculationTone, string> = {
      neutral: "border-neutral-700/80 bg-neutral-900/80 text-neutral-100",
      plots: "border-emerald-500/30 bg-emerald-500/10 text-emerald-100",
      garden: "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-100",
      unique: "border-sky-500/30 bg-sky-500/10 text-sky-100",
      evergreen: "border-teal-500/30 bg-teal-500/10 text-teal-100",
      harvest: "border-red-500/30 bg-red-500/10 text-red-100",
      fortune: "border-amber-500/30 bg-amber-500/10 text-amber-100",
      special: "border-cyan-500/30 bg-cyan-500/10 text-cyan-100",
    };
    return tones[tone];
  };

  const getYieldCalculationSteps = (yld: YieldItem): CalculationStep[] => {
    if (!yld.math || !selectedMutation) return [];

    const math = yld.math;
    const spotsPerPlot = selectedMutation.breakdown.base_limit;
    const totalSpots = spotsPerPlot * plots;
    const spawnFactor = totalSpots > 0 ? math.limit / totalSpots : 1;
    const evergreenBuff = math.evergreen_buff ?? 0;
    const harvestBoostMultiplier = math.harvest_boost ?? math.wart_buff ?? 1;
    const isPlainMutationMath =
      math.base === 1 &&
      evergreenBuff === 0 &&
      math.gh_buff === 0 &&
      math.unique_buff === 0 &&
      harvestBoostMultiplier === 1 &&
      math.fortune === 1 &&
      math.special === 1;
    const steps: CalculationStep[] = [
      { label: "Base Drop", value: formatCoins(math.base), tone: "neutral" },
      { label: "Spots per Plot", value: formatCoins(spotsPerPlot), tone: "neutral" },
      { label: "Plots", value: formatCoins(plots), tone: "plots" },
    ];

    if (Number.isFinite(spawnFactor) && Math.abs(spawnFactor - 1) > 1e-6) {
      steps.push({ label: "Spawn Factor", value: formatPreciseValue(spawnFactor), tone: "special" });
    }

    if (!isPlainMutationMath) {
      steps.push({ label: "Base Yield", value: formatPreciseValue(1.0), tone: "neutral" });
      if (evergreenBuff !== 0) {
        steps.push({ label: "Evergreen Chip", value: `+${formatPreciseValue(evergreenBuff)}`, tone: "evergreen" });
      }
      if (math.gh_buff !== 0) {
        steps.push({ label: "Greenhouse Yield", value: `+${formatPreciseValue(math.gh_buff)}`, tone: "garden" });
      }
      if (math.unique_buff !== 0) {
        steps.push({ label: "Unique Crops", value: `+${formatPreciseValue(math.unique_buff)}`, tone: "unique" });
      }
      steps.push({ label: "Harvest Boost", value: formatPreciseValue(harvestBoostMultiplier), tone: "harvest" });
      if ((math.overdrive_bonus ?? 0) > 0) {
        steps.push({ label: "Overdrive Fortune", value: `+${formatCoins(math.overdrive_bonus ?? 0)}`, tone: "fortune" });
      }
      steps.push({ label: "Fortune Multiplier", value: formatPreciseValue(math.fortune), tone: "fortune" });
    }

    steps.push({
      label: selectedMutation.mutationName === "All-in Aloe" ? "Expected Special Multiplier" : "Special Multiplier",
      value: formatPreciseValue(math.special),
      tone: "special"
    });
    steps.push({ label: "Market Price", value: formatCoins(yld.unit_price), tone: "neutral" });
    return steps;
  };

  const showsAdditiveGardenBreakdown = (math?: YieldMath) =>
    Boolean(math && ((math.evergreen_buff ?? 0) !== 0 || math.gh_buff !== 0 || math.unique_buff !== 0));

  const missingCrops = mode === "smart" ? (data?.metadata.missing_crops ?? []) : [];
  const visibleSmartCrops = mode === "smart" ? missingCrops : [];

  const visibleLeaderboard = useMemo(() => {
    if (!(mode === "smart" && data)) return data?.leaderboard ?? [];
    return data.leaderboard.filter((item) => {
      const progress = item.smart_progress ?? {};
      return Object.keys(progress).length > 0;
    });
  }, [mode, data]);

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
    if (key === "growth_cycle_profit") return item.profit_per_growth_cycle ?? null;
    if (key === "profit_per_hour") return item.profit_per_hour;
    if (key === "cycles") return item.hourly?.g ?? item.breakdown.growth_stages;
    if (key === "time") return item.breakdown.estimated_time_hours;
    if (key === "setup") return item.opt_cost;
    if (key === "value") {
      if (mode === "smart") {
        return item.score;
      }
      return mode === "target" ? item.score : item.profit;
    }
    return item.score;
  };

  const sortedLeaderboard = [...visibleLeaderboard].sort((a, b) => {
    const av = sortValue(a, sortKey);
    const bv = sortValue(b, sortKey);
    const aMissing = av === null || av === undefined || (typeof av === "number" && !Number.isFinite(av));
    const bMissing = bv === null || bv === undefined || (typeof bv === "number" && !Number.isFinite(bv));
    if (aMissing || bMissing) {
      if (aMissing && bMissing) return 0;
      return aMissing ? 1 : -1;
    }
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

  const selectedMutationNetProfit = selectedMutation
    ? selectedMutation.breakdown.total_revenue - selectedMutation.breakdown.total_setup_cost
    : 0;
  const selectedMutationGrowthCycles = selectedMutation
    ? formatGrowthCyclesDisplay(selectedMutation.hourly?.g ?? selectedMutation.breakdown.growth_stages)
    : "0 Cycles";
  const selectedMutationLifecycle = selectedMutation
    ? formatLifecycleDisplay(selectedMutation.breakdown.estimated_time_hours, selectedMutation.breakdown.growth_stages)
    : "Instant";



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

            <div className="space-y-4">
              <div className="rounded-2xl border border-emerald-200/80 bg-emerald-50/50 p-4 dark:border-emerald-900/40 dark:bg-emerald-950/15">
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

              <div className="rounded-2xl border border-rose-200/80 bg-rose-50/40 p-4 space-y-4 dark:border-rose-900/40 dark:bg-rose-950/10">
                <div>
                  <label className="flex justify-between text-sm font-medium mb-2">
                    <span>Greenhouse Yield Upgrade</span>
                    <span className="text-fuchsia-600 dark:text-fuchsia-400">{ghYieldUpgrade}/9</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="9"
                    value={ghYieldUpgrade}
                    onChange={(e) => setGhYieldUpgrade(Number(e.target.value))}
                    className="w-full accent-fuchsia-500"
                  />
                  <p className="mt-2 text-[11px] text-neutral-500 dark:text-neutral-400">
                    Adds up to +20% greenhouse yield at 9/9.
                  </p>
                </div>

                <div>
                  <label className="flex justify-between items-center text-sm font-medium mb-2">
                    <span className="inline-flex items-center gap-2">
                      <Image src="/icons/buffs/seeds.png" alt="Seeds" width={20} height={20} className="w-5 h-5 rounded-md object-contain pixelated" />
                      Unique Crops Placed
                    </span>
                    <span className="text-sky-600 dark:text-sky-400">{uniqueCrops}/12</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="12"
                    value={uniqueCrops}
                    onChange={(e) => setUniqueCrops(Number(e.target.value))}
                    className="w-full accent-sky-500"
                  />
                </div>

                <div className="grid gap-3">
                  <div className="rounded-xl border border-neutral-200/80 bg-white/80 p-3 dark:border-neutral-800 dark:bg-neutral-900/70">
                    <label className="flex items-start justify-between gap-3">
                      <span className="min-w-0">
                        <span className="inline-flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-100">
                          <Image src="/icons/buffs/wheat.png" alt="Harvest Boost icon" width={20} height={20} className="w-5 h-5 rounded-md object-contain pixelated" />
                          Harvest Boost (Increases Yield by +20%)
                          <span className="group relative inline-flex">
                            <button
                              type="button"
                              tabIndex={0}
                              aria-label="Harvest Boost info"
                              onClick={(e) => e.preventDefault()}
                              className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-neutral-300 text-[10px] leading-none text-neutral-500 dark:border-neutral-700 dark:text-neutral-400"
                            >
                              <Info className="h-3 w-3" />
                            </button>
                            <span className="absolute left-1/2 top-full z-20 mt-2 w-56 -translate-x-1/2 rounded bg-neutral-900 px-3 py-2 text-left text-[11px] font-normal normal-case tracking-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                              Apply this boost if your mutations will have a Harvest Boost.
                            </span>
                          </span>
                        </span>
                        <span className="mt-1 block text-[11px] text-neutral-500 dark:text-neutral-400">
                          Current boost: {useHarvestBoost ? "1.20x" : "1.00x"}
                        </span>
                      </span>
                      <input
                        type="checkbox"
                        checked={useHarvestBoost}
                        onChange={(e) => handleHarvestBoostToggle(e.target.checked)}
                        className="mt-0.5 accent-emerald-500"
                      />
                    </label>
                  </div>

                  <div className="rounded-xl border border-neutral-200/80 bg-white/80 p-3 dark:border-neutral-800 dark:bg-neutral-900/70">
                    <label className="flex items-start justify-between gap-3">
                      <span className="min-w-0">
                        <span className="inline-flex items-center gap-2 text-sm font-medium text-neutral-800 dark:text-neutral-100">
                          <Image src="/icons/buffs/wart.png" alt="Improved Harvest Boost icon" width={20} height={20} className="w-5 h-5 rounded-md object-contain pixelated" />
                          Improved Harvest Boost (Increases Yield by +30%)
                          <span className="group relative inline-flex">
                            <button
                              type="button"
                              tabIndex={0}
                              aria-label="Improved Harvest Boost info"
                              onClick={(e) => e.preventDefault()}
                              className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-neutral-300 text-[10px] leading-none text-neutral-500 dark:border-neutral-700 dark:text-neutral-400"
                            >
                              <Info className="h-3 w-3" />
                            </button>
                            <span className="absolute left-1/2 top-full z-20 mt-2 w-56 -translate-x-1/2 rounded bg-neutral-900 px-3 py-2 text-left text-[11px] font-normal normal-case tracking-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                              Apply this boost if your mutations will have an Increased Harvest Boost.
                            </span>
                          </span>
                        </span>
                        <span className="mt-1 block text-[11px] text-neutral-500 dark:text-neutral-400">
                          Current boost: {useImprovedHarvestBoost ? "1.30x" : "1.00x"}
                        </span>
                      </span>
                      <input
                        type="checkbox"
                        checked={useImprovedHarvestBoost}
                        onChange={(e) => handleImprovedHarvestBoostToggle(e.target.checked)}
                        className="mt-0.5 accent-emerald-500"
                      />
                    </label>
                  </div>
                </div>

                <div>
                  <label className="flex justify-between items-center text-sm font-medium mb-2">
                    <span className="inline-flex items-center gap-2">
                      <Image src="/icons/buffs/evergreen.webp" alt="Evergreen Chip" width={20} height={20} className="w-5 h-5 rounded-md object-contain pixelated" />
                      Evergreen Chip Level
                    </span>
                    <span className="text-teal-600 dark:text-teal-400">{evergreenChipLevel}/{chipRarityConfig[evergreenChipRarity].maxLevel}</span>
                  </label>
                  <div className="mb-3 grid grid-cols-3 gap-2">
                    {chipRarityOrder.map((rarity) => (
                      <button
                        key={`evergreen-${rarity}`}
                        type="button"
                        onClick={() => setEvergreenChipRarity(rarity)}
                        className={`rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors ${evergreenChipRarity === rarity
                          ? "border-teal-500 bg-teal-500 text-white"
                          : "border-neutral-200 bg-white text-neutral-600 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300"}`}
                      >
                        {chipRarityConfig[rarity].label}
                      </button>
                    ))}
                  </div>
                  <input
                    type="range"
                    min="0"
                    max={chipRarityConfig[evergreenChipRarity].maxLevel}
                    step="1"
                    value={evergreenChipLevel}
                    onChange={(e) => setEvergreenChipLevel(Number(e.target.value))}
                    className="w-full accent-teal-500"
                  />
                  <p className="mt-2 text-[11px] text-neutral-500 dark:text-neutral-400">
                    {chipRarityConfig[evergreenChipRarity].label}: +{(chipRarityConfig[evergreenChipRarity].evergreenRate * 100).toFixed(1).replace(".0", "")}% base crops per level.
                    Current bonus: +{(evergreenChipLevel * chipRarityConfig[evergreenChipRarity].evergreenRate * 100).toFixed(1).replace(".0", "")}%.
                  </p>
                </div>
              </div>

              <div className="rounded-2xl border border-amber-200/80 bg-amber-50/40 p-4 space-y-4 dark:border-amber-900/40 dark:bg-amber-950/10">
                <div>
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
                      className="w-24 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-2 py-1 text-right text-amber-600 dark:text-amber-400"
                    />
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="4000"
                    step="50"
                    value={fortune}
                    onChange={(e) => setFortune(Number(e.target.value))}
                    className="w-full accent-amber-500"
                  />
                  {data?.metadata.fortune_breakdown && (
                    <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
                      Effective Fortune: {Math.round(data.metadata.fortune_breakdown.effective_fortune)} (+{Math.round(data.metadata.fortune_breakdown.bonus_total)})
                    </p>
                  )}
                </div>

                <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-3 space-y-3 bg-white/70 dark:bg-neutral-900/60">
                  <p className="text-sm font-medium">Fortune Buffs</p>

                  <label className="flex items-center justify-between gap-3">
                    <span className="inline-flex items-center gap-2 text-xs">
                      <Image src="/icons/buffs/harvest-harbinger-potion.png" alt="Harvest Harbinger Potion" width={20} height={20} className="w-5 h-5 rounded-sm" />
                      Harvest Harbinger (+50, unaffected)
                    </span>
                    <input type="checkbox" checked={useHarvestHarbinger} onChange={(e) => setUseHarvestHarbinger(e.target.checked)} className="accent-amber-500" />
                  </label>

                  <label className="flex items-center justify-between gap-3">
                    <span className="inline-flex items-center gap-2 text-xs">
                      <Image src="/icons/buffs/infini-vacuum-hooverius.png" alt="InfiniVacuum Hooverius" width={20} height={20} className="w-5 h-5 rounded-sm" />
                      Pest Buff (+200)
                    </span>
                    <input type="checkbox" checked={useInfiniVacuum} onChange={(e) => setUseInfiniVacuum(e.target.checked)} className="accent-amber-500" />
                  </label>

                  <label className="flex items-center justify-between gap-3">
                    <span className="inline-flex items-center gap-2 text-xs">
                      <Image src="/icons/buffs/refined-dark-cacao-truffle.png" alt="Refined Dark Cacao Truffle" width={20} height={20} className="w-5 h-5 rounded-sm" />
                      Refined Dark Cacao Truffle (+30, affected)
                    </span>
                    <input type="checkbox" checked={useDarkCacao} onChange={(e) => setUseDarkCacao(e.target.checked)} className="accent-amber-500" />
                  </label>

                  <div>
                    <label className="flex items-center justify-between text-xs mb-1">
                      <span className="inline-flex items-center gap-2">
                        <Image src="/icons/buffs/hypercharge-chip.png" alt="Hypercharge Chip" width={20} height={20} className="w-5 h-5 rounded-sm" />
                        Hypercharge Chip Level
                      </span>
                      <span className="text-amber-600 dark:text-amber-400">{hyperchargeLevel}/{chipRarityConfig[hyperchargeRarity].maxLevel}</span>
                    </label>
                    <div className="mb-3 grid grid-cols-3 gap-2">
                      {chipRarityOrder.map((rarity) => (
                        <button
                          key={`hypercharge-${rarity}`}
                          type="button"
                          onClick={() => setHyperchargeRarity(rarity)}
                          className={`rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors ${hyperchargeRarity === rarity
                            ? "border-amber-500 bg-amber-500 text-white"
                            : "border-neutral-200 bg-white text-neutral-600 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300"}`}
                        >
                          {chipRarityConfig[rarity].label}
                        </button>
                      ))}
                    </div>
                    <input
                      type="range"
                      min="0"
                      max={chipRarityConfig[hyperchargeRarity].maxLevel}
                      step="1"
                      value={hyperchargeLevel}
                      onChange={(e) => setHyperchargeLevel(Number(e.target.value))}
                      className="w-full accent-amber-500"
                    />
                    <p className="text-[11px] text-neutral-500 mt-1">
                      {chipRarityConfig[hyperchargeRarity].label}: +{(chipRarityConfig[hyperchargeRarity].hyperchargeRate * 100).toFixed(0)}% affected buff strength per level.
                      Current bonus: +{(hyperchargeLevel * chipRarityConfig[hyperchargeRarity].hyperchargeRate * 100).toFixed(0)}%.
                    </p>
                  </div>

                  <div className="rounded-xl border border-neutral-200/80 bg-neutral-50/80 p-3 dark:border-neutral-800 dark:bg-neutral-950/40">
                    <label className="flex items-center justify-between text-xs mb-1">
                      <span className="inline-flex items-center gap-2">
                        <Image src="/icons/buffs/overdrive.webp" alt="Overdrive Chip" width={20} height={20} className="w-5 h-5 rounded-sm object-contain pixelated" />
                        Overdrive Chip Level
                      </span>
                      <span className="text-orange-600 dark:text-orange-400">{overdriveChipLevel}/{chipRarityConfig[overdriveChipRarity].maxLevel}</span>
                    </label>
                    <div className="mb-3 grid grid-cols-3 gap-2">
                      {chipRarityOrder.map((rarity) => (
                        <button
                          key={`overdrive-${rarity}`}
                          type="button"
                          onClick={() => setOverdriveChipRarity(rarity)}
                          className={`rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors ${overdriveChipRarity === rarity
                            ? "border-orange-500 bg-orange-500 text-white"
                            : "border-neutral-200 bg-white text-neutral-600 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300"}`}
                        >
                          {chipRarityConfig[rarity].label}
                        </button>
                      ))}
                    </div>
                    <input
                      type="range"
                      min="0"
                      max={chipRarityConfig[overdriveChipRarity].maxLevel}
                      step="1"
                      value={overdriveChipLevel}
                      onChange={(e) => setOverdriveChipLevel(Number(e.target.value))}
                      className="w-full accent-orange-500"
                    />
                    <div className="mt-3">
                      <label className="mb-1 block text-[11px] font-medium text-neutral-600 dark:text-neutral-300">Contest Crop</label>
                      <select
                        value={overdriveCrop}
                        onChange={(e) => setOverdriveCrop(e.target.value)}
                        className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-700 outline-none transition-colors focus:border-orange-400 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200"
                      >
                        <option value="">No contest crop</option>
                        {displayCrops.map((crop) => (
                          <option key={`overdrive-crop-${crop.key}`} value={crop.key}>
                            {crop.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <p className="text-[11px] text-neutral-500 mt-2">
                      {chipRarityConfig[overdriveChipRarity].label}: +{chipRarityConfig[overdriveChipRarity].overdriveBonus} crop fortune per level.
                      {overdriveCrop
                        ? ` Current bonus: +${formatCoins(overdriveChipLevel * chipRarityConfig[overdriveChipRarity].overdriveBonus)} to ${toCropLabel(overdriveCrop)}.`
                        : " Select a contest crop to apply it."}
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-sky-200/80 bg-sky-50/40 p-4 space-y-4 dark:border-sky-900/40 dark:bg-sky-950/10">
                <div>
                  <label className="flex justify-between text-sm font-medium mb-2">
                    <span>Greenhouse Speed Upgrade</span>
                    <span className="text-sky-600 dark:text-sky-400">{ghSpeedUpgrade}/9</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="9"
                    value={ghSpeedUpgrade}
                    onChange={(e) => setGhSpeedUpgrade(Number(e.target.value))}
                    className="w-full accent-sky-500"
                  />
                  <p className="mt-2 text-[11px] text-neutral-500 dark:text-neutral-400">
                    Controls the greenhouse cycle-time bonus used for lifecycle estimates.
                  </p>
                </div>

                {data && (
                  <div className="rounded-xl border border-white/80 bg-white/75 px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900/70">
                    <p className="text-sm text-neutral-500 dark:text-neutral-400">Cycle Time</p>
                    <div className="mt-1 flex items-center gap-2 font-mono text-lg font-medium text-sky-700 dark:text-sky-300">
                      <Clock className="w-5 h-5" />
                      {formatDuration(data.metadata.cycle_time_hours)}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </aside>

        {/* MAIN CONTENT: LEADERBOARD */}
        <main className="flex-1 min-w-0 space-y-8">

          {/* CROP MILESTONES SECTION */}
          {mode === "smart" && (
            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
              <div className="mb-5 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={markAllMissingAsCompleted}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-emerald-500 bg-emerald-500 text-white transition-colors hover:bg-emerald-400 hover:border-emerald-400"
                >
                  Mark All Missing as Completed
                </button>
                <button
                  type="button"
                  onClick={markAllAsMissing}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-neutral-300 bg-neutral-50 text-neutral-700 transition-colors hover:bg-neutral-100 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-200 dark:hover:bg-neutral-700"
                >
                  Mark All as Missing
                </button>
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
                      <th className="px-6 py-4 font-semibold w-16 text-center">Rank</th>
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
                        <th className="px-6 py-4 font-semibold text-right text-cyan-600 dark:text-cyan-400 hidden lg:table-cell">
                          <div className="inline-flex items-center justify-end gap-2">
                            <button type="button" onClick={() => toggleSort("profit_per_hour")} className="inline-flex items-center gap-1">
                              Profit / Hour <span aria-hidden="true">{sortIndicator("profit_per_hour")}</span>
                            </button>
                            <div className="group relative">
                              <button
                                type="button"
                                tabIndex={0}
                                aria-label="Profit per hour help"
                                className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-neutral-500/50 text-[10px] leading-none cursor-help"
                              >
                                <Info className="h-3 w-3" />
                              </button>
                              <div className="absolute left-1/2 top-full z-20 mt-2 w-72 -translate-x-1/2 rounded bg-neutral-900 px-3 py-2 text-left text-[11px] font-normal normal-case tracking-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                                <p className="leading-snug">Uses expected spawn wait plus growth stages, then converts that full cycle into real hours with the current garden cycle time.</p>
                              </div>
                            </div>
                          </div>
                        </th>
                      )}
                      {mode === "profit" && (
                        <th className="px-6 py-4 font-semibold text-right text-sky-600 dark:text-sky-400 hidden lg:table-cell">
                          <button type="button" onClick={() => toggleSort("growth_cycle_profit")} className="inline-flex items-center gap-1">
                            Profit / Growth Cycle <span aria-hidden="true">{sortIndicator("growth_cycle_profit")}</span>
                          </button>
                        </th>
                      )}
                      <th className="px-6 py-4 font-semibold text-right hidden md:table-cell">
                        <div className="inline-flex items-center justify-end gap-2">
                          <button type="button" onClick={() => toggleSort("cycles")} className="inline-flex items-center gap-1">
                            Growth Cycles <span aria-hidden="true">{sortIndicator("cycles")}</span>
                          </button>
                          <div className="group relative">
                            <button
                              type="button"
                              tabIndex={0}
                              aria-label="Growth cycles help"
                              className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-neutral-500/50 text-[10px] leading-none cursor-help"
                            >
                              <Info className="h-3 w-3" />
                            </button>
                            <div className="absolute left-1/2 top-full z-20 mt-2 w-72 -translate-x-1/2 rounded bg-neutral-900 px-3 py-2 text-left text-[11px] font-normal normal-case tracking-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                              <p className="leading-snug">Shows only the mutation&apos;s post-spawn growth stages. Expected spawn wait is already included in Profit / Growth Cycle and Profit / Hour.</p>
                            </div>
                          </div>
                        </div>
                      </th>
                      <th className="px-6 py-4 font-semibold text-right hidden lg:table-cell">
                        <div className="inline-flex items-center justify-end gap-2">
                          <button type="button" onClick={() => toggleSort("time")} className="inline-flex items-center gap-1">
                            Time <span aria-hidden="true">{sortIndicator("time")}</span>
                          </button>
                          <div className="group relative">
                            <button
                              type="button"
                              tabIndex={0}
                              aria-label="Lifecycle time help"
                              className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-neutral-500/50 text-[10px] leading-none cursor-help"
                            >
                              <Info className="h-3 w-3" />
                            </button>
                            <div className="absolute left-1/2 top-full z-20 mt-2 w-64 -translate-x-1/2 rounded bg-neutral-900 px-3 py-2 text-left text-[11px] font-normal normal-case tracking-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                              <p className="leading-snug">Lifecycle time is the post-spawn growth window only. Instant mutations show as Instant here.</p>
                            </div>
                          </div>
                        </div>
                      </th>
                      <th className="px-6 py-4 font-semibold text-right hidden sm:table-cell">
                        <div className="inline-flex items-center justify-end gap-2">
                          <button type="button" onClick={() => toggleSort("setup")} className="inline-flex items-center gap-1">
                            Setup Cost <span aria-hidden="true">{sortIndicator("setup")}</span>
                          </button>
                          <div className="group relative">
                            <button
                              type="button"
                              tabIndex={0}
                              aria-label="Setup cost note"
                              className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-neutral-500/50 text-[10px] leading-none cursor-help"
                            >
                              <Info className="h-3 w-3" />
                            </button>
                            <div className="absolute left-1/2 top-full z-20 mt-2 w-72 -translate-x-1/2 rounded bg-neutral-900 px-3 py-2 text-left text-[11px] font-normal normal-case tracking-normal text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                              <p className="leading-snug">{setupCostNote}</p>
                            </div>
                          </div>
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedLeaderboard.map((item, idx) => (
                      <tr
                        key={item.mutationName}
                        onClick={() => setSelectedMutation(item)}
                        title="Click to view mutation breakdown"
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
                              {mode === "profit" && item.mutationName === "Lonelily" && (
                                <div className="group/lonelily relative">
                                  <button
                                    type="button"
                                    aria-label={`${lonelilyHarvestWarning.label}: ${lonelilyHarvestWarning.lines.join(" ")}`}
                                    className="inline-flex items-center"
                                  >
                                    <AlertTriangle className="h-4 w-4 text-amber-500 hover:text-amber-400" />
                                  </button>
                                  <div className="pointer-events-none absolute right-full top-1/2 z-10 mr-3 hidden w-80 -translate-y-1/2 rounded-xl border border-amber-500/30 bg-neutral-900 p-3 text-left text-xs tracking-wide text-white opacity-0 shadow-lg transition-opacity group-hover/lonelily:opacity-100 group-focus-within/lonelily:opacity-100 lg:block">
                                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-200">
                                      {lonelilyHarvestWarning.label}
                                    </p>
                                    <div className="text-white/90">
                                      {lonelilyHarvestWarning.lines.map((line) => (
                                        <p key={line} className="mb-2 leading-relaxed last:mb-0">
                                          {line}
                                        </p>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                              {item.warning_messages && item.warning_messages.length > 0 && (
                                <div className="group/warn relative">
                                  {(() => {
                                    const tone = getLeaderboardWarningTone(item);
                                    return (
                                      <>
                                        <button
                                          type="button"
                                          aria-label={`${tone.label}: ${item.warning_messages.join(" ")}`}
                                          className="inline-flex items-center"
                                        >
                                          <AlertTriangle className={`w-4 h-4 ${tone.icon}`} />
                                        </button>
                                        <div className={`pointer-events-none absolute right-full top-1/2 z-10 mr-3 hidden w-72 -translate-y-1/2 rounded-xl border p-3 text-left text-xs tracking-wide opacity-0 shadow-lg transition-opacity group-hover/warn:opacity-100 group-focus-within/warn:opacity-100 lg:block ${tone.panel}`}>
                                          <p className={`mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${tone.heading}`}>
                                            {tone.label}
                                          </p>
                                          <div className={tone.body}>
                                            {item.warning_messages.map((message) => (
                                              <p key={message} className="mb-2 leading-relaxed last:mb-0">
                                                {message}
                                              </p>
                                            ))}
                                          </div>
                                        </div>
                                      </>
                                    );
                                  })()}
                                </div>
                              )}
                              {formatCoins(mode === "target" ? item.score : item.profit)}
                            </div>
                          </td>
                        )}
                        {mode === "profit" && (
                          <td className="px-6 py-4 text-right font-mono font-bold text-cyan-600 dark:text-cyan-400 hidden lg:table-cell">
                            {formatGrowthCycleProfit(item.profit_per_hour)}
                          </td>
                        )}
                        {mode === "profit" && (
                          <td className="px-6 py-4 text-right font-mono font-bold text-sky-600 dark:text-sky-400 hidden lg:table-cell">
                            {formatGrowthCycleProfit(item.profit_per_growth_cycle)}
                          </td>
                        )}
                        <td className="px-6 py-4 text-right font-mono text-neutral-500 hidden md:table-cell">
                          {getGrowthCyclesLabel(item)}
                        </td>
                        <td className="px-6 py-4 text-right font-mono text-neutral-500 hidden lg:table-cell">
                          {formatLifecycleDisplay(item.breakdown.estimated_time_hours, item.breakdown.growth_stages)}
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

          <div className="rounded-2xl border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
            <div className="border-b border-neutral-200 px-5 py-4 dark:border-neutral-800 sm:px-6">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 rounded-xl bg-sky-100 p-2 text-sky-600 dark:bg-sky-900/30 dark:text-sky-300">
                  <Info className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-neutral-950 dark:text-white">Frequently Asked Questions (FAQ)</h3>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">Open each question for the current profit, spawn, and warning rules used by the calculator.</p>
                </div>
              </div>
            </div>
            <div className="px-5 py-4 sm:px-6">
              <div className="space-y-3">
                {faqItems.map((item) => (
                  <div key={item.question} className="rounded-2xl border border-neutral-200/80 bg-neutral-50/80 dark:border-neutral-800 dark:bg-neutral-950/60">
                    <button
                      type="button"
                      onClick={() => setOpenFaqQuestion((current) => current === item.question ? null : item.question)}
                      className="flex w-full items-center justify-between gap-4 px-4 py-4 text-left"
                      aria-expanded={openFaqQuestion === item.question}
                    >
                      <span className="text-sm font-bold text-neutral-950 dark:text-white">{item.question}</span>
                      <ChevronDown className={`h-4 w-4 shrink-0 text-neutral-400 transition-transform ${openFaqQuestion === item.question ? "rotate-180" : ""}`} />
                    </button>
                    {openFaqQuestion === item.question && (
                      <div className="border-t border-neutral-200 px-4 py-4 dark:border-neutral-800">
                        {item.answer.map((paragraph) => (
                          <p key={paragraph} className="text-sm leading-6 text-neutral-600 dark:text-neutral-300">
                            {paragraph}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Modal Overlay */}
      {selectedMutation && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-3 md:p-5 animate-in fade-in duration-200" onClick={() => setSelectedMutation(null)}>
          <div className="relative flex max-h-[96vh] w-full max-w-[min(96vw,1520px)] flex-col overflow-hidden rounded-[32px] border border-neutral-200/80 bg-white/95 shadow-2xl shadow-neutral-950/20 backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/95" onClick={e => e.stopPropagation()}>
            <div className="pointer-events-none absolute inset-x-0 top-0 h-56 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.22),transparent_55%),radial-gradient(circle_at_top_right,_rgba(59,130,246,0.16),transparent_45%)] dark:bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.28),transparent_55%),radial-gradient(circle_at_top_right,_rgba(59,130,246,0.24),transparent_45%)]" />
            <div className="relative border-b border-neutral-200/70 bg-white/70 px-6 py-6 backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/70 sm:px-8 lg:px-10">
              <div className="flex items-start justify-between gap-4">
                <div className="flex min-w-0 items-start gap-4 lg:gap-5">
                  <div className="relative flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-emerald-200/70 bg-gradient-to-br from-emerald-100 via-white to-emerald-50 text-2xl shadow-sm dark:border-emerald-800/80 dark:from-emerald-950/70 dark:via-neutral-900 dark:to-emerald-900/30">
                    <div className="absolute h-10 w-10 rounded-full bg-emerald-500/10 blur-xl dark:bg-emerald-400/10" aria-hidden="true" />
                    <div className="relative flex h-full w-full items-center justify-center">
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
                  </div>
                  <div className="min-w-0 space-y-4">
                    <div>
                      <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-emerald-600/80 dark:text-emerald-300/75">Mutation Breakdown</p>
                      <h3 className="mt-2 text-2xl font-black tracking-tight text-neutral-950 dark:text-white">{toMutationLabel(selectedMutation.mutationName)}</h3>
                      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                        Harvest snapshot, setup cost, and expected value for {plots} placed plot{plots > 1 ? "s" : ""}.
                      </p>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-2xl border border-emerald-200/70 bg-emerald-50/80 px-4 py-3 dark:border-emerald-900/50 dark:bg-emerald-950/25">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">Total Placed</p>
                        <p className="mt-1 text-lg font-black text-neutral-950 dark:text-white">{selectedMutation.limit}</p>
                      </div>
                      <div className="rounded-2xl border border-sky-200/70 bg-sky-50/80 px-4 py-3 dark:border-sky-900/50 dark:bg-sky-950/25">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-700 dark:text-sky-300">Growth Cycles</p>
                        <p className="mt-1 text-lg font-black text-neutral-950 dark:text-white">{selectedMutationGrowthCycles}</p>
                      </div>
                      <div className="rounded-2xl border border-cyan-200/70 bg-cyan-50/80 px-4 py-3 dark:border-cyan-900/50 dark:bg-cyan-950/25">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-700 dark:text-cyan-300">Lifecycle</p>
                        <p className="mt-1 text-lg font-black text-neutral-950 dark:text-white">{selectedMutationLifecycle}</p>
                      </div>
                      <div className="rounded-2xl border border-amber-200/70 bg-amber-50/80 px-4 py-3 dark:border-amber-900/50 dark:bg-amber-950/25">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700 dark:text-amber-300">Setup Cost</p>
                        <p className="mt-1 text-base font-black font-mono text-neutral-950 dark:text-white">{formatCoins(selectedMutation.breakdown.total_setup_cost)}</p>
                      </div>
                    </div>
                  </div>
                </div>
                <button className="rounded-full border border-neutral-200/80 bg-white/80 p-2 text-neutral-400 transition-colors hover:text-neutral-700 dark:border-neutral-700 dark:bg-neutral-900/70 dark:hover:text-neutral-200" onClick={() => setSelectedMutation(null)}>
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="relative overflow-y-auto px-6 py-5 custom-scrollbar sm:px-8 lg:px-10">
              <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)] 2xl:grid-cols-[360px_minmax(0,1fr)]">
                <section className="space-y-4">
                  {selectedMutation.mutationName === "Devourer" && (
                    <div className="rounded-3xl border border-red-200/80 bg-gradient-to-br from-red-50 via-white to-red-50/50 p-5 shadow-sm dark:border-red-900/40 dark:from-red-950/30 dark:via-neutral-900 dark:to-neutral-900">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
                        <div>
                          <p className="text-sm font-bold text-red-700 dark:text-red-300">Devourer placement warning</p>
                          <p className="mt-1 text-sm leading-6 text-red-700/90 dark:text-red-200/90">
                            This crop destroys surrounding crops over time. Remove adjacent blocks to prevent spread. Growing all 16 at once is possible, but not advised.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="rounded-3xl border border-neutral-200/80 bg-neutral-50/80 p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900/70">
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <div>
                        <h4 className="text-lg font-bold text-neutral-950 dark:text-white">Setup Ingredients</h4>
                        <p className="text-sm text-neutral-500 dark:text-neutral-400">Everything needed to plant the full batch.</p>
                      </div>
                      <span className="rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs font-semibold text-neutral-600 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300">
                        {selectedMutation.breakdown.ingredients.length} item{selectedMutation.breakdown.ingredients.length === 1 ? "" : "s"}
                      </span>
                    </div>

                    {selectedMutation.breakdown.ingredients.length > 0 ? (
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                        {selectedMutation.breakdown.ingredients.map((ing) => (
                          <div key={ing.name} className="rounded-2xl border border-neutral-200/70 bg-white/85 p-4 shadow-sm dark:border-neutral-800 dark:bg-neutral-950/70">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-neutral-400">Ingredient</p>
                                <p className="mt-2 text-base font-bold text-neutral-900 dark:text-white">
                                  {ing.amount}x <span className="text-emerald-700 dark:text-emerald-300">{toCropLabel(ing.name)}</span>
                                </p>
                              </div>
                              <div className="rounded-xl border border-amber-200/70 bg-amber-50 px-3 py-2 text-right dark:border-amber-900/40 dark:bg-amber-950/20">
                                <div className="font-mono text-sm font-black text-amber-600 dark:text-amber-300">{formatCoins(ing.total_cost)}</div>
                                <div className="mt-0.5 text-[10px] font-mono text-neutral-500 dark:text-neutral-400">{formatCoins(ing.unit_price)} each</div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-2xl border border-dashed border-emerald-300/70 bg-emerald-50/70 px-4 py-5 text-sm text-emerald-700 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300">
                        No setup ingredients are needed for this mutation.
                      </div>
                    )}
                  </div>
                </section>

                <section className="space-y-4">
                  <div className="rounded-3xl border border-neutral-200/80 bg-neutral-50/70 p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900/70">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-sky-700 dark:text-sky-300">
                          <Sparkles className="h-4 w-4" />
                          Harvest Yields
                        </div>
                        <h4 className="mt-2 text-lg font-bold text-neutral-950 dark:text-white">Yield Breakdown</h4>
                        <p className="text-sm text-neutral-500 dark:text-neutral-400">Amounts, value, and the exact formula used for each drop.</p>
                      </div>
                    </div>

                    {(selectedMutation.mutationName === "Magic Jellybean" || selectedMutation.mutationName === "All-in Aloe") && (
                      <div className="mb-3 rounded-2xl border border-sky-400/20 bg-white/70 p-3 dark:border-sky-500/20 dark:bg-sky-950/20">
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-sky-600 dark:text-sky-300" />
                          <p className="text-sm leading-6 text-sky-800 dark:text-sky-200">
                            {selectedMutation.mutationName === "Magic Jellybean"
                              ? "Magic Jellybean has 120 growth stages. It is best to harvest when its fully grown so you waste less time waiting for spawns."
                              : "All-in Aloe is evaluated at Stage 14 because that is the best expected harvest window. The raw stage multiplier there is 60x, but the calculator uses the reset-adjusted expected multiplier of 9.37x."}
                          </p>
                        </div>
                      </div>
                    )}

                    {selectedMutation.breakdown.yields && selectedMutation.breakdown.yields.length > 0 ? (
                      <div className="space-y-3">
                        {selectedMutation.breakdown.yields.map((yld) => (
                          <div key={yld.name} className="rounded-2xl border border-neutral-200/70 bg-gradient-to-br from-white via-white to-neutral-50 p-3 shadow-sm dark:border-neutral-800 dark:from-neutral-950 dark:via-neutral-950 dark:to-neutral-900">
                            <div className="grid gap-3 lg:grid-cols-[minmax(0,0.65fr)_minmax(0,1.45fr)_170px] lg:items-center">
                              <div className="min-w-0">
                                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-neutral-400">
                                  <Sparkles className="h-3.5 w-3.5" />
                                  Expected yield
                                </div>
                                <div className="mt-1.5 flex flex-wrap items-baseline gap-x-2 gap-y-1">
                                  <span className="text-xl font-black tracking-tight text-neutral-950 dark:text-white">{formatCoins(yld.amount)}x</span>
                                  <span className="text-lg font-semibold text-emerald-700 dark:text-emerald-300">{toCropLabel(yld.name)}</span>
                                </div>
                              </div>
                              {yld.math && (
                                <div className="rounded-2xl border border-neutral-200/80 bg-neutral-950 px-3 py-2.5 text-[11px] shadow-inner dark:border-neutral-700">
                                  <div className="flex flex-wrap items-center justify-between gap-1.5">
                                    <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-neutral-400">
                                      Calculation Breakdown
                                    </div>
                                    {showsAdditiveGardenBreakdown(yld.math) && (
                                      <p className="text-[10px] text-neutral-500">
                                        Yield bonuses stack before harvest boost, fortune, and special
                                      </p>
                                    )}
                                  </div>
                                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                                      {getYieldCalculationSteps(yld).map((step, index) => (
                                        <Fragment key={`${yld.name}-${step.label}`}>
                                          {index > 0 && <span className="text-xs font-black text-neutral-500">×</span>}
                                          <div className={`rounded-lg border px-2 py-1.5 ${getCalculationToneClasses(step.tone)}`}>
                                            <div className="flex flex-wrap items-center gap-1 whitespace-normal">
                                              <p className="text-[9px] font-semibold uppercase tracking-[0.12em] opacity-70">{step.label}</p>
                                              <p className="font-mono text-[11px] font-black">{step.value}</p>
                                            </div>
                                          </div>
                                        </Fragment>
                                      ))}
                                  </div>
                                </div>
                              )}
                              <div className="shrink-0 rounded-2xl border border-emerald-300/20 bg-emerald-500/10 px-3 py-2.5 text-right dark:border-emerald-500/20 dark:bg-emerald-500/10">
                                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">Value</div>
                                <div className="mt-1 text-xl font-black font-mono text-emerald-600 dark:text-emerald-300">{formatCoins(yld.total_value)}</div>
                                <div className="mt-0.5 text-[10px] font-mono text-neutral-500 dark:text-neutral-400">{formatCoins(yld.unit_price)} each</div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-2xl border border-dashed border-neutral-300 bg-white/80 px-4 py-6 text-sm italic text-neutral-500 dark:border-neutral-700 dark:bg-neutral-950/70 dark:text-neutral-400">
                        No direct harvest yields.
                      </div>
                    )}

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div className="rounded-2xl border border-emerald-300/20 bg-emerald-500/10 p-4">
                        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">
                          <Coins className="h-4 w-4" />
                          Total Batch Revenue
                        </div>
                        <div className="mt-2 text-3xl font-black font-mono text-emerald-600 dark:text-emerald-300">
                          +{formatCoins(selectedMutation.breakdown.total_revenue)}
                        </div>
                      </div>
                      <div className={`rounded-2xl p-4 shadow-lg ${selectedMutationNetProfit >= 0
                        ? "bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-emerald-500/20"
                        : "bg-gradient-to-r from-red-500 to-rose-500 text-white shadow-red-500/20"
                        }`}>
                        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-white/80">
                          <ArrowUpRight className="h-4 w-4" />
                          Expected Net Profit
                        </div>
                        <div className="mt-2 text-3xl font-black font-mono">
                          {formatSignedCoins(selectedMutationNetProfit)}
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </div>
        </div>
      )}

      <style jsx global>{`
        .pixelated {
          image-rendering: pixelated;
          image-rendering: crisp-edges;
        }
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

