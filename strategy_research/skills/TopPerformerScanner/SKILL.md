---
name: TopPerformerScanner/FeasibilityAnalyzer
description: Analyzes historic top-performing stock traits and assesses whether current filter logic would catch or miss the best performers (like APP, ASTS, CVNA, SNDK) early over past years.
---

# TopPerformerScanner Skill

This skill allows you to:
1. Extract authentic Top-performing stocks. `get_true_top_500.py` scrapes the entire NASDAQ-listed symbol pool and dynamically derives the true top returning components sorted by liquidity segments over designated years (e.g. 2021-2025). This ensures we do not overfit to known mega-caps or lookahead biases.
2. Measure strategy filtration feasibility against these explosive names. `analyze_feasibility.py` loops multiple distinct option scanning configurations (e.g., M0 mega-cap limits vs AppHunter lower-cap expanded thresholds) to pinpoint exactly when and how often the explosive run-ups were captured vs stepped over. 

## Base Executions
### Option A: Find true market leaders
```bash
python3 strategy_research/skills/TopPerformerScanner/get_true_top_500.py
```
This requires internet (`yfinance`, `ftps`) and will construct output CSVs highlighting 1000% annual returns without survivorship bias.

### Option B: Back-test custom filters against leading components
```bash
python3 strategy_research/skills/TopPerformerScanner/analyze_feasibility.py
```
It compares multiple simulated triggers (`M0_logic`, `N3_logic`, `AppHunter_logic`) per leading entity component and returns total days the filter would pass during explosive trajectories comparing tight threshold (like `Top 500 Daily Volume`) vs broad threshold (like `Top 1000 Daily Volume`).

*Use this module to ensure you don't build an air-tight fortress that inadvertently filters out true multibaggers early.*
