"use client";

import { useState, useEffect } from "react";
import { ModeToggle } from "@/components/mode-toggle";
import { Coins, Sprout, Clock, Calculator, Loader2, ArrowUpRight, AlertTriangle, X } from "lucide-react";

type OptimizationMode = "profit" | "smart" | "target";
type SetupMode = "buy_order" | "insta_buy";
type SellMode = "sell_offer" | "insta_sell";

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
  opt_cost: number;
  revenue: number;
  warning: boolean;
  mut_price: number;
  limit: number;
  breakdown: MutationBreakdown;
};

type LeaderboardResponse = {
  leaderboard: LeaderboardItem[];
  metadata: {
    cycle_time_hours: number;
  };
};

const optimizationModes: { id: OptimizationMode; label: string; icon: string }[] = [
  { id: "profit", label: "Pure Profit", icon: "💰" },
  { id: "smart", label: "Smart (Milestones)", icon: "🧠" },
  { id: "target", label: "Focus One Crop", icon: "🎯" },
];

export default function Home() {
  const [plots, setPlots] = useState(3);
  const [fortune, setFortune] = useState(2500);
  const [ghUpgrade, setGhUpgrade] = useState(9);
  const [uniqueCrops, setUniqueCrops] = useState(12);

  const [mode, setMode] = useState<OptimizationMode>("profit");
  const [targetCrop, setTargetCrop] = useState("Wheat");
  const [maxedCrops, setMaxedCrops] = useState<string[]>([]);

  // New Toggles
  const [setupMode, setSetupMode] = useState<SetupMode>("buy_order");
  const [sellMode, setSellMode] = useState<SellMode>("sell_offer");

  // Modal State
  const [selectedMutation, setSelectedMutation] = useState<LeaderboardItem | null>(null);

  const displayCrops = [
    "Wheat", "Carrot", "Potato", "Pumpkin", "Sugar cane", "Melon", "Cactus",
    "Coco Bean", "Nether Wart", "Sunflower", "Moonflower", "Wild Rose", "Mushroom"
  ];

  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(num);
  };

  const formatDuration = (hours: number) => {
    const totalMinutes = Math.max(0, Math.round(hours * 60));
    const hrs = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;

    if (hrs === 0) return `${mins}m`;
    if (mins === 0) return `${hrs}h`;
    return `${hrs}h ${mins}m`;
  };

  const formatYieldCalculation = (math: YieldMath, unitPrice: number) => {
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col md:flex-row gap-8">

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
                    <span>{m.icon}</span>
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
                    <option key={c} value={c}>{c}</option>
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
              <label className="flex justify-between text-sm font-medium mb-2">
                <span>Farming Fortune</span>
                <span className="text-emerald-600 dark:text-emerald-400">{fortune}</span>
              </label>
              <input
                type="range"
                min="0"
                max="3000"
                step="50"
                value={fortune}
                onChange={(e) => setFortune(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
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
          <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <div className="p-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg">
                <ArrowUpRight className="w-4 h-4" />
              </div>
              Crop Milestones
            </h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
              Toggle: <span className="text-emerald-600 font-bold">Maxed</span> vs <span className="text-blue-500 font-bold">Needed</span>.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              {displayCrops.map(crop => (
                <button
                  key={crop}
                  onClick={() => toggleMaxedCrop(crop)}
                  className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${maxedCrops.includes(crop)
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-800 dark:text-emerald-400'
                    : 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-400'
                    }`}
                >
                  <span className="truncate">{crop}</span>
                  <span className="shrink-0">{maxedCrops.includes(crop) ? '✅' : '⚡'}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white dark:bg-neutral-900 rounded-2xl shadow-sm border border-neutral-200 dark:border-neutral-800 overflow-hidden">
            <div className="px-6 py-5 border-b border-neutral-200 dark:border-neutral-800 flex justify-between items-center bg-neutral-50/50 dark:bg-neutral-900/50">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Coins className="w-5 h-5 text-amber-500" />
                {mode === "profit" ? "Profit Leaderboard" : mode === "smart" ? "Smart Value Ranking" : `${targetCrop} Optimization`}
              </h2>
              {loading && <Loader2 className="w-5 h-5 animate-spin text-emerald-500" />}
            </div>

            <div className="overflow-x-auto">
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
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-neutral-100 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400 border-b border-neutral-200 dark:border-neutral-800">
                    <tr>
                      <th className="px-6 py-4 font-semibold w-16 text-center">Rank</th>
                      <th className="px-6 py-4 font-semibold">Mutation Profile</th>
                      <th className="px-6 py-4 font-semibold text-right text-emerald-600 dark:text-emerald-400">
                        {mode === "profit" ? "Profit / Harvest" : mode === "target" ? `${targetCrop} Yield` : "Smart Score"}
                      </th>
                      <th className="px-6 py-4 font-semibold text-right hidden md:table-cell">Grow Time</th>
                      <th className="px-6 py-4 font-semibold text-right hidden sm:table-cell">Setup Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.leaderboard.map((item, idx) => (
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
                            🌱
                          </div>
                          <div>
                            <span className="hover:text-amber-500 transition-colors">{item.mutationName}</span>
                            {idx === 0 && <span className="ml-2 text-[10px] uppercase tracking-wider font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/30 px-2 py-0.5 rounded-full inline-block mt-1">Top Pick</span>}
                          </div>
                        </td>
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
                            {mode === "smart" ? item.score.toFixed(2) : formatCoins(mode === "target" ? item.score : item.profit)}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right font-mono text-neutral-500 hidden md:table-cell">
                          {formatDuration(item.breakdown.estimated_time_hours)}
                        </td>
                        <td className="px-6 py-4 text-right font-mono opacity-[0.65] hidden sm:table-cell">
                          {formatCoins(item.opt_cost)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
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
                  🌱
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
                        <span className="font-medium">{ing.amount}x <span className="text-emerald-700 dark:text-emerald-300">{ing.name}</span></span>
                      </div>
                      <div className="text-right">
                        <div className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">{formatCoins(ing.total_cost)} 🪙</div>
                        <div className="text-[10px] text-neutral-400 font-mono mt-0.5">{formatCoins(ing.unit_price)} each</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex justify-between items-center pt-4 border-t border-neutral-200 dark:border-neutral-800">
                <span className="font-medium">Total Setup Cost</span>
                <span className="font-mono text-lg font-bold text-amber-500">{formatCoins(selectedMutation.breakdown.total_setup_cost)} 🪙</span>
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
                      Target Growth Stage:
                    </div>
                    <span className="bg-blue-600 text-white px-3 py-1 rounded-lg text-xs font-black">{selectedMutation.breakdown.growth_stages} Stages</span>
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
                            <span className="font-medium">{formatCoins(yld.amount)}x <span className="text-emerald-700 dark:text-emerald-300">{yld.name}</span></span>
                          </div>
                          <div className="text-right">
                            <div className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">{formatCoins(yld.total_value)} 🪙</div>
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
                  <span className="text-2xl font-mono font-black text-emerald-600 dark:text-emerald-400">+{formatCoins(selectedMutation.breakdown.total_revenue)} 🪙</span>
                </div>

                <div className="flex justify-between items-center p-6 bg-emerald-500 rounded-2xl shadow-xl shadow-emerald-500/20 text-white">
                  <span className="font-black uppercase tracking-wider text-sm">Expected Net Profit</span>
                  <span className="text-2xl font-mono font-black">
                    {formatCoins(selectedMutation.breakdown.total_revenue - selectedMutation.breakdown.total_setup_cost)} 🪙
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
