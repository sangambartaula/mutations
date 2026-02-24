export type CoinsPerMutationInput = {
  fortune: number;
  baseItems: number;
  itemPrice: number;
};

export type ProfitHrASAPInput = {
  plots: number;
  slotsPerPlot: number;
  mutationChance: number;
  stageDurationHours: number;
  fortune: number;
  baseItems: number;
  itemPrice: number;
  buffCostPerHour?: number;
  setupCost?: number;
  setupAmortizeHours?: number;
};

export type ProfitHrAFKInput = {
  plots: number;
  slotsPerPlot: number;
  mutationChance: number;
  stageDurationHours: number;
  harvestStages: number;
  fortune: number;
  baseItems: number;
  itemPrice: number;
  setupCost?: number;
  buffCostPerHarvest?: number;
};

export type ProfitHrASAPResult = {
  expectedMutationsPerStage: number;
  revenuePerStage: number;
  revenuePerHour: number;
  costsPerHour: number;
  netProfitPerHour: number;
};

export type ProfitHrAFKResult = {
  expectedMutationsByHarvest: number;
  harvestTimeHours: number;
  revenueByHarvest: number;
  costsByHarvest: number;
  netProfitByHarvest: number;
  netProfitPerHour: number;
  spawnProbabilityByHarvest: number;
};

export type PerMutationBatchValueInput = {
  totalRevenueAtReferenceFortune: number;
  mutationUnitPrice: number;
  mutationsAtHarvest: number;
  referenceFortune: number;
  modeFortune: number;
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const nonNegative = (value: number) => (Number.isFinite(value) ? Math.max(0, value) : 0);

export function deriveHarvestStagesFromHours(hours: number, stageDurationHours: number): number {
  const safeHours = nonNegative(hours);
  const safeStageDuration = nonNegative(stageDurationHours);
  if (safeStageDuration <= 0) return 0;
  return Math.floor(safeHours / safeStageDuration);
}

export function computeCoinsPerMutation(fortune: number, baseItems: number, itemPrice: number): number {
  const safeFortune = nonNegative(fortune);
  const safeBaseItems = nonNegative(baseItems);
  const safeItemPrice = nonNegative(itemPrice);
  const expectedItemsPerMutation = safeBaseItems * (1 + safeFortune / 100);
  return expectedItemsPerMutation * safeItemPrice;
}

export function computeProfitHrASAP(params: ProfitHrASAPInput): ProfitHrASAPResult {
  const plots = nonNegative(params.plots);
  const slotsPerPlot = nonNegative(params.slotsPerPlot);
  const mutationChance = clamp(nonNegative(params.mutationChance), 0, 1);
  const stageDurationHours = nonNegative(params.stageDurationHours);
  const buffCostPerHour = nonNegative(params.buffCostPerHour ?? 0);
  const setupCost = nonNegative(params.setupCost ?? 0);
  const setupAmortizeHours = nonNegative(params.setupAmortizeHours ?? 0);

  if (stageDurationHours <= 0) {
    return {
      expectedMutationsPerStage: 0,
      revenuePerStage: 0,
      revenuePerHour: 0,
      costsPerHour: 0,
      netProfitPerHour: 0,
    };
  }

  const valuePerMutation = computeCoinsPerMutation(params.fortune, params.baseItems, params.itemPrice);
  const expectedMutationsPerStage = plots * slotsPerPlot * mutationChance;
  const revenuePerStage = expectedMutationsPerStage * valuePerMutation;
  const revenuePerHour = revenuePerStage / stageDurationHours;
  const setupCostPerHour = setupAmortizeHours > 0 ? (setupCost / setupAmortizeHours) : 0;
  const costsPerHour = buffCostPerHour + setupCostPerHour;

  return {
    expectedMutationsPerStage,
    revenuePerStage,
    revenuePerHour,
    costsPerHour,
    netProfitPerHour: revenuePerHour - costsPerHour,
  };
}

export function computeProfitHrAFK(params: ProfitHrAFKInput): ProfitHrAFKResult {
  const plots = nonNegative(params.plots);
  const slotsPerPlot = nonNegative(params.slotsPerPlot);
  const mutationChance = clamp(nonNegative(params.mutationChance), 0, 1);
  const stageDurationHours = nonNegative(params.stageDurationHours);
  const harvestStages = Math.floor(nonNegative(params.harvestStages));
  const setupCost = nonNegative(params.setupCost ?? 0);
  const buffCostPerHarvest = nonNegative(params.buffCostPerHarvest ?? 0);

  if (stageDurationHours <= 0 || harvestStages <= 0) {
    return {
      expectedMutationsByHarvest: 0,
      harvestTimeHours: 0,
      revenueByHarvest: 0,
      costsByHarvest: setupCost + buffCostPerHarvest,
      netProfitByHarvest: -(setupCost + buffCostPerHarvest),
      netProfitPerHour: 0,
      spawnProbabilityByHarvest: 0,
    };
  }

  const valuePerMutation = computeCoinsPerMutation(params.fortune, params.baseItems, params.itemPrice);
  const spawnProbabilityByHarvest = 1 - Math.pow(1 - mutationChance, harvestStages);
  const expectedMutationsByHarvest = plots * slotsPerPlot * spawnProbabilityByHarvest;
  const harvestTimeHours = harvestStages * stageDurationHours;
  const revenueByHarvest = expectedMutationsByHarvest * valuePerMutation;
  const costsByHarvest = setupCost + buffCostPerHarvest;
  const netProfitByHarvest = revenueByHarvest - costsByHarvest;

  return {
    expectedMutationsByHarvest,
    harvestTimeHours,
    revenueByHarvest,
    costsByHarvest,
    netProfitByHarvest,
    netProfitPerHour: harvestTimeHours > 0 ? (netProfitByHarvest / harvestTimeHours) : 0,
    spawnProbabilityByHarvest,
  };
}

export function deriveCoinsPerMutationFromBatch(input: PerMutationBatchValueInput): number {
  const totalRevenue = nonNegative(input.totalRevenueAtReferenceFortune);
  const mutationUnitPrice = nonNegative(input.mutationUnitPrice);
  const mutationsAtHarvest = nonNegative(input.mutationsAtHarvest);
  const referenceFortune = nonNegative(input.referenceFortune);
  const modeFortune = nonNegative(input.modeFortune);

  if (mutationsAtHarvest <= 0) return mutationUnitPrice;

  const mutationRevenue = mutationUnitPrice * mutationsAtHarvest;
  const cropRevenue = Math.max(0, totalRevenue - mutationRevenue);

  const cropPerMutationAtReference = cropRevenue / mutationsAtHarvest;
  const referenceFortuneMult = 1 + (referenceFortune / 100);
  const modeFortuneMult = 1 + (modeFortune / 100);

  const cropPerMutationAtBase = referenceFortuneMult > 0
    ? cropPerMutationAtReference / referenceFortuneMult
    : 0;

  const cropPerMutationAtMode = cropPerMutationAtBase * modeFortuneMult;
  return mutationUnitPrice + cropPerMutationAtMode;
}
