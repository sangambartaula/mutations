import { describe, expect, it } from "vitest";
import { applyFortuneChange, syncFortunesOnToggle } from "@/lib/fortune-link";

describe("fortune-link", () => {
  it("links fortunes when checkbox is enabled", () => {
    const linked = syncFortunesOnToggle(true, { fortuneAfk: 1234, fortuneAsap: 2500 });
    expect(linked.fortuneAfk).toBe(1234);
    expect(linked.fortuneAsap).toBe(1234);
  });

  it("keeps fortunes independent when checkbox is disabled", () => {
    const values = syncFortunesOnToggle(false, { fortuneAfk: 1200, fortuneAsap: 900 });
    expect(values.fortuneAfk).toBe(1200);
    expect(values.fortuneAsap).toBe(900);
  });

  it("changing one fortune updates both when linked", () => {
    const values = applyFortuneChange("afk", 2800, true, { fortuneAfk: 1000, fortuneAsap: 1000 });
    expect(values.fortuneAfk).toBe(2800);
    expect(values.fortuneAsap).toBe(2800);
  });

  it("changing one fortune only updates target when unlinked", () => {
    const values = applyFortuneChange("asap", 3000, false, { fortuneAfk: 1000, fortuneAsap: 1000 });
    expect(values.fortuneAfk).toBe(1000);
    expect(values.fortuneAsap).toBe(3000);
  });
});