---
name: DeepForensics
description: A tool to execute a deep forensic analysis and attribution on completed QuantConnect backtest outputs.
---

# DeepForensics Skill

This skill allows you to conduct a detailed "deep forensic" analysis on the trading data extracted from any QuantConnect backtest. 

The `download_and_analyze.py` script automatically downloads the Orders CSV for the designated strategy execution run, fetches the corresponding historical ticker data from `yfinance`, extracts and restructures 10-15 granular market factors (e.g. RSI, moving average deviations, gap openings, volume surges), splits trades into pure winners (profit > 0) and losers (profit < 0), and identifies statistical correlations that define successful options entries.

## How to execute

Run the script from the application root path as follows:
```bash
python3 download_and_analyze.py <backtest_id> <optional_output_directory>
```
If you do not manually specify `<optional_output_directory>`, the results will be stored dynamically in the path `results/auto_<backtest_id_short>/`.

### Output
The process will generate:
- A `[hash]_orders_features.csv` broad analytical table.
- A `diagnosis.txt` plain text diagnostic report dissecting the "What-If" implications of altering strategy variables, summarizing the statistical deltas and outlining absolute toxic filter indicators vs absolute safe filter identifiers.

*Always read the `diagnosis.txt` after backtest completions to fine-tune iterative models.*
