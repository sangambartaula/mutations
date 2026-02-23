import { describe, expect, it } from "vitest";
import {
  computeCoinsPerMutation,
  computeProfitHrAFK,
  computeProfitHrASAP,
  deriveHarvestStagesFromHours,
} from "@/lib/mutation-profit-calculator";

describe("mutation-profit-calculator", () => {
  it("returns deterministic coins per mutation", () => {
    expect(computeCoinsPerMutation(0, 1, 100)).toBe(100);
    expect(computeCoinsPerMutation(100, 1, 100)).toBe(200);
  });

  it("ASAP with p=0 yields no mutations and only costs", () => {
    const result = computeProfitHrASAP({
      plots: 3,
      slotsPerPlot: 16,
      mutationChance: 0,
      stageDurationHours: 1,
      fortune: 2500,
      baseItems: 1,
      itemPrice: 100,
      buffCostPerHour: 20,
      setupCost: 40,
      setupAmortizeHours: 4,
    });

    expect(result.expectedMutationsPerStage).toBe(0);
    expect(result.revenuePerHour).toBe(0);
    expect(result.netProfitPerHour).toBe(-30);
  });

  it("p=1 yields full slots immediately for ASAP and AFK(1 stage)", () => {
    const asap = computeProfitHrASAP({
      plots: 2,
      slotsPerPlot: 10,
      mutationChance: 1,
      stageDurationHours: 2,
      fortune: 0,
      baseItems: 1,
      itemPrice: 50,
    });

    const afk = computeProfitHrAFK({
      plots: 2,
      slotsPerPlot: 10,
      mutationChance: 1,
      stageDurationHours: 2,
      harvestStages: 1,
      fortune: 0,
      baseItems: 1,
      itemPrice: 50,
    });

    expect(asap.expectedMutationsPerStage).toBe(20);
    expect(afk.expectedMutationsByHarvest).toBe(20);
    expect(afk.spawnProbabilityByHarvest).toBe(1);
  });

  it("higher fortune increases profit for both modes", () => {
    const lowAsap = computeProfitHrASAP({
      plots: 3,
      slotsPerPlot: 16,
      mutationChance: 0.25,
      stageDurationHours: 1,
      fortune: 0,
      baseItems: 1,
      itemPrice: 100,
    });
    const highAsap = computeProfitHrASAP({
      plots: 3,
      slotsPerPlot: 16,
      mutationChance: 0.25,
      stageDurationHours: 1,
      fortune: 1000,
      baseItems: 1,
      itemPrice: 100,
    });

    const lowAfk = computeProfitHrAFK({
      plots: 3,
      slotsPerPlot: 16,
      mutationChance: 0.25,
      stageDurationHours: 1,
      harvestStages: 4,
      fortune: 0,
      baseItems: 1,
      itemPrice: 100,
    });
    const highAfk = computeProfitHrAFK({
      plots: 3,
      slotsPerPlot: 16,
      mutationChance: 0.25,
      stageDurationHours: 1,
      harvestStages: 4,
      fortune: 1000,
      baseItems: 1,
      itemPrice: 100,
    });

    expect(highAsap.netProfitPerHour).toBeGreaterThan(lowAsap.netProfitPerHour);
    expect(highAfk.netProfitPerHour).toBeGreaterThan(lowAfk.netProfitPerHour);
  });

  it("AFK with N=0 is safe and returns 0 profit/hour", () => {
    const afk = computeProfitHrAFK({
      plots: 3,
      slotsPerPlot: 16,
      mutationChance: 0.25,
      stageDurationHours: 1,
      harvestStages: 0,
      fortune: 0,
      baseItems: 1,
      itemPrice: 100,
      setupCost: 200,
      buffCostPerHarvest: 50,
    });

    expect(afk.expectedMutationsByHarvest).toBe(0);
    expect(afk.netProfitPerHour).toBe(0);
    expect(afk.netProfitByHarvest).toBe(-250);
  });

  it("converts AFK hours to stages using floor", () => {
    expect(deriveHarvestStagesFromHours(5.9, 2)).toBe(2);
    expect(deriveHarvestStagesFromHours(0.9, 1)).toBe(0);
  });
});