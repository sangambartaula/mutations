"use client";

import { useState, useEffect } from "react";
import { ModeToggle } from "@/components/mode-toggle";
import { Coins, Sprout, Clock, Calculator, Loader2, ArrowUpRight } from "lucide-react";

export default function Home() {
  const [plots, setPlots] = useState(1);
  const [fortune, setFortune] = useState(2500);
  const [ghUpgrade, setGhUpgrade] = useState(9);
  const [uniqueCrops, setUniqueCrops] = useState(12);

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(
          `/api/leaderboard?plots=${plots}&fortune=${fortune}&gh_upgrade=${ghUpgrade}&unique_crops=${uniqueCrops}`
        );
        if (!res.ok) throw new Error("Failed to fetch leaderboard data.");
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [plots, fortune, ghUpgrade, uniqueCrops]);

  const formatCoins = (num: number) => {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(num);
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
                  {Math.floor(data.cycle_time_hours)}h {Math.round((data.cycle_time_hours - Math.floor(data.cycle_time_hours)) * 60)}m
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* MAIN CONTENT: LEADERBOARD */}
        <main className="flex-1 min-w-0">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl shadow-sm border border-neutral-200 dark:border-neutral-800 overflow-hidden">
            <div className="px-6 py-5 border-b border-neutral-200 dark:border-neutral-800 flex justify-between items-center bg-neutral-50/50 dark:bg-neutral-900/50">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Coins className="w-5 h-5 text-amber-500" />
                Profit Leaderboard
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
                  <p>Calculating 30+ layout geometries...</p>
                </div>
              ) : (
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-neutral-100 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400 border-b border-neutral-200 dark:border-neutral-800">
                    <tr>
                      <th className="px-6 py-4 font-semibold">Rank</th>
                      <th className="px-6 py-4 font-semibold">Mutation Name</th>
                      <th className="px-6 py-4 font-semibold text-right text-emerald-600 dark:text-emerald-400">Profit / Harvest</th>
                      <th className="px-6 py-4 font-semibold text-right">Profit / Hour</th>
                      <th className="px-6 py-4 font-semibold text-right">Setup Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.leaderboard.map((item: any, idx: number) => (
                      <tr
                        key={item.mutation}
                        className={`border-b border-neutral-100 dark:border-neutral-800 last:border-0 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors ${idx === 0 ? 'bg-amber-50/50 dark:bg-amber-900/10' : ''}`}
                      >
                        <td className="px-6 py-4 text-center w-16">
                          {idx === 0 ? (
                            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400 font-bold text-xs ring-1 ring-amber-500/20">
                              !
                            </span>
                          ) : (
                            <span className="text-neutral-400 font-mono">{idx + 1}</span>
                          )}
                        </td>
                        <td className="px-6 py-4 font-medium">
                          {item.mutation}
                          {idx === 0 && <span className="ml-2 text-[10px] uppercase tracking-wider font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/30 px-2 py-0.5 rounded-full">Top Pick</span>}
                          {item.mutation === 'Magic Jellybean' && (
                            <div className="text-[10px] text-neutral-400 mt-1">Requires 120 cycles (10x drops max)</div>
                          )}
                          {item.mutation === 'All-in Aloe' && (
                            <div className="text-[10px] text-neutral-400 mt-1">Stops at Stage 13-14 optimally</div>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                          {formatCoins(item.profit_per_batch)}
                        </td>
                        <td className="px-6 py-4 text-right font-mono opacity-80">
                          {formatCoins(item.profit_per_hour)}
                        </td>
                        <td className="px-6 py-4 text-right font-mono opacity-[0.65]">
                          {formatCoins(item.setup_cost)}
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
    </div>
  );
}
