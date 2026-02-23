export type FortuneFields = {
  fortuneAfk: number;
  fortuneAsap: number;
};

const sanitizeFortune = (value: number) => {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(4000, Math.round(value)));
};

export function syncFortunesOnToggle(useSameForBoth: boolean, values: FortuneFields): FortuneFields {
  if (!useSameForBoth) return values;
  return {
    fortuneAfk: sanitizeFortune(values.fortuneAfk),
    fortuneAsap: sanitizeFortune(values.fortuneAfk),
  };
}

export function applyFortuneChange(
  target: "afk" | "asap",
  nextValue: number,
  useSameForBoth: boolean,
  values: FortuneFields
): FortuneFields {
  const normalized = sanitizeFortune(nextValue);

  if (useSameForBoth) {
    return {
      fortuneAfk: normalized,
      fortuneAsap: normalized,
    };
  }

  if (target === "afk") {
    return {
      fortuneAfk: normalized,
      fortuneAsap: values.fortuneAsap,
    };
  }

  return {
    fortuneAfk: values.fortuneAfk,
    fortuneAsap: normalized,
  };
}