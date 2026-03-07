# Skyblock Mutation Optimizer

A full-stack web application that models crop mutation mechanics and calculates optimal farming strategies using probabilistic spawn models.

Live app: [skyblockmutations.vercel.app](https://skyblockmutations.vercel.app/)

## Tech Stack

- Next.js (TypeScript)
- FastAPI (Python)
- TailwindCSS
- Vercel deployment

## Overview

Skyblock Mutation Optimizer is a probability-driven farming calculator for Garden mutations in Hypixel SkyBlock. It combines live market data, mutation growth rules, setup costs, and expected spawn timing to rank strategies in a way that is actually useful for players.

Instead of only showing the biggest final harvest, the app answers harder questions:

- Which mutation gives the highest raw harvest value?
- Which one is actually efficient once time is considered?
- Which mutation helps specific crop milestones the fastest?
- Which setups look strong on paper but break down because of low spawn chance or special mechanics?

The result is a full-stack tool that turns a messy in-game system into something measurable and explorable.

## Core Features

- Sortable leaderboard for:
  - Profit / Harvest
  - Profit / Growth Cycle
  - Profit / Hour
  - Setup Cost
  - Growth Cycles
  - Lifecycle Time
- Expanded mutation breakdowns with setup ingredients, yield math, and warning states
- Smart milestone mode for missing crop progress
- Target-crop mode for optimizing specific output types
- Live Bazaar-aware pricing with NPC fallbacks
- Special-case handling for mutations that do not fit the default model

## How The Calculator Works

### Profit / Harvest

Profit per Harvest represents one full mature batch after the mutation has spawned and finished growing.

```text
profit_per_harvest = total_revenue - setup_cost
```

Where:

- `setup_cost` is the total cost of all ingredients needed to place the mutation batch
- `total_revenue` includes:
  - mutated crop drops
  - mutation value itself

This is the theoretical completed-harvest value. It is useful, but not always realistic on its own.

### Profit / Growth Cycle

Profit per Growth Cycle adjusts that full-harvest value by the expected number of cycles required for the mutation to spawn and mature.

```text
expected_spawn_cycles = 1 / spawn_chance
expected_cycles = expected_spawn_cycles + growth_stages
profit_per_growth_cycle = profit_per_harvest / expected_cycles
```

This prevents low-spawn or long-growth mutations from looking deceptively strong just because their final harvest is large.

### Profit / Hour

Profit per Hour converts the same expected cycle model into real-world time using the current garden cycle duration.

```text
expected_hours = expected_cycles * cycle_time_hours
profit_per_hour = profit_per_harvest / expected_hours
```

In practice, this is usually the most realistic comparison metric when two mutations have very different spawn or growth behavior.

## Spawn Assumptions

Most mutations use the standard model:

```text
spawn_chance = 0.25
```

Lonelily is treated separately:

```text
spawn_chance = 0.0045
```

That difference matters a lot. Lonelily can still show a strong theoretical Profit / Harvest, but the expected time to assemble a full mature batch is much longer, so time-based metrics are intentionally harsher.

## Yield Model

Expected drop values are built from the full harvest stack, including:

- base drop amount
- spots per plot
- plot count
- greenhouse yield upgrades
- unique crop bonus
- Evergreen Chip bonus
- wart boost
- farming fortune multiplier
- Overdrive Chip bonus when relevant
- mutation-specific special multiplier
- market price per drop

The UI exposes this breakdown directly so the user can inspect how each number was built instead of trusting an opaque final total.

## Special Cases

### Lonelily

Lonelily has an extremely low spawn rate compared to standard mutations. The app therefore separates its theoretical harvest value from its realistic time-based profitability.

### Devourer

Devourer can spread and destroy nearby crops, which makes large-scale setups inconsistent. The tool marks this explicitly with warnings instead of pretending the layout risk does not exist.

### Magic Jellybean

Magic Jellybean grows through 120 stages and ramps into a 10x multiplier when fully grown. It can produce huge harvest values, but it also takes dramatically longer than standard mutations to mature.

### All-in Aloe

All-in Aloe has a reset-based multiplier mechanic. Rather than assuming an unrealistic perfect high-roll scenario, the calculator uses an efficient expected-value harvest window around stages 13-14.

## Architecture

### Frontend

- Next.js App Router
- TypeScript
- TailwindCSS
- Interactive controls, sortable tables, accordions, tooltips, and expanded mutation panels

### Backend

- FastAPI calculation API
- Cached Bazaar data fetches
- Precomputed mutation metadata for faster leaderboard generation
- Validation, rate limiting, and security headers for public API use

### Data Layer

Mutation behavior is built from a mix of:

- local JSON metadata
- crop drop tables
- live Bazaar quick-status pricing
- NPC fallback prices

That combination lets the app react to real market conditions while still encoding game-specific mechanics that the Bazaar API alone cannot describe.

## Local Development

Install dependencies:

```bash
npm install
pip install -r requirements.txt
```

Run the full app:

```bash
npm run dev
```

This starts:

- Next.js frontend on `localhost:3000`
- FastAPI backend on `localhost:8000`

You can also run them separately:

```bash
npm run dev:frontend
npm run dev:backend
```

## Verification

Useful checks:

```bash
npm run lint
npm run build
python -m pytest tests/test_leaderboard.py tests/test_leaderboard_integration.py tests/test_mut_calc.py
```

## Why This Project Belongs On a Resume

This project demonstrates more than just UI work or scripting. It combines:

- full-stack application development across TypeScript and Python
- probability-based modeling and expected-value calculations
- live external data integration
- domain-specific edge-case handling
- explainable UI for complex calculations
- backend performance and public API hardening

It is a good example of building a polished product around ambiguous real-world rules, then making the assumptions visible enough that users can trust the result.
