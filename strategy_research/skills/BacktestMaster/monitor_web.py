#!/usr/bin/env python3
"""
Monitor backtest via QC web UI using Playwright (Chrome session).
Reads real-time equity/return from the terminal page.

Usage:
    python monitor_web.py <backtest_id> --baseline M0
"""
import sys
import os
import json
import time
import argparse
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qc_api.config import get_default_project_id

BASELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselines")
START_EQUITY = 10000
PROJECT_ID = get_default_project_id()

EXIT_SUCCESS   = 0
EXIT_ERROR     = 1
EXIT_TIMEOUT   = 2
EXIT_EARLY_STOP = 3


def _load_baseline(name_or_path):
    if os.path.exists(name_or_path):
        path = name_or_path
    else:
        path = os.path.join(BASELINE_DIR, f"{name_or_path}.json")
    if not os.path.exists(path):
        print(f"   ⚠️  Baseline not found: {path}")
        return None
    with open(path) as f:
        data = json.load(f)
    print(f"   Baseline: {len(data.get('checkpoints', []))} checkpoints from {os.path.basename(path)}")
    return data


def _get_baseline_equity_at(baseline, progress):
    cps = baseline["checkpoints"]
    if not cps:
        return None
    prev, nxt = None, None
    for cp in cps:
        if cp["progress"] <= progress:
            prev = cp
        else:
            nxt = cp
            break
    if prev is None:
        return cps[0].get("equity")
    if nxt is None:
        return prev.get("equity")
    r = nxt["progress"] - prev["progress"]
    if r <= 0:
        return prev.get("equity")
    t = (progress - prev["progress"]) / r
    return prev.get("equity", 0) + t * (nxt.get("equity", 0) - prev.get("equity", 0))


def _parse_value(text):
    """Parse '$5,871.05' or '-$2,524.95' or '38.31 %' → float."""
    if not text:
        return None
    s = text.strip().replace(',', '').replace('$', '').replace('%', '').replace('\xa0', '')
    # Handle negative: '-$2,524.95' → '-2524.95'
    s = s.replace('−', '-')  # unicode minus
    try:
        return float(s)
    except ValueError:
        return None


def scrape_backtest_data(page):
    """Scrape equity, return, net profit from the QC terminal page header."""
    data = {}
    try:
        # The header stats are in specific elements
        # Look for the stats bar with Equity, Fees, Holdings, Net Profit, PSR, Return
        stats_text = page.inner_text('.backtest-results-header, .panel-header, #statistics-bar', timeout=2000)
        if not stats_text:
            return data
    except Exception:
        pass

    # Alternative: read individual stat elements
    try:
        selectors = [
            ('.stat-equity .value, [data-stat="equity"] .value', 'equity'),
            ('.stat-return .value, [data-stat="return"] .value', 'return_pct'),
            ('.stat-net-profit .value, [data-stat="netProfit"] .value', 'net_profit'),
        ]
        for sel, key in selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    data[key] = _parse_value(el.inner_text())
            except Exception:
                pass
    except Exception:
        pass

    # Fallback: grab all visible text from the header area and parse
    if not data:
        try:
            # Get the entire page header text
            header = page.evaluate("""() => {
                // Try to find the backtest stats header
                const els = document.querySelectorAll('.backtest-toolbar .toolbar-item, .qc-col');
                const result = {};
                for (const el of els) {
                    const text = el.innerText.trim();
                    if (text.includes('Equity') && !text.includes('Strategy')) {
                        const val = text.replace('Equity', '').trim();
                        result.equity = val;
                    }
                    if (text.includes('Return') && !text.includes('Compounding')) {
                        const val = text.replace('Return', '').trim();
                        result.return_pct = val;
                    }
                    if (text.includes('Net Profit')) {
                        const val = text.replace('Net Profit', '').trim();
                        result.net_profit = val;
                    }
                }
                return result;
            }""")
            if header:
                for k, v in header.items():
                    parsed = _parse_value(v)
                    if parsed is not None:
                        data[k] = parsed
        except Exception:
            pass

    # Final fallback: just grab all text and regex parse
    if not data:
        try:
            all_text = page.inner_text('body', timeout=3000)
            # Look for patterns like "$5,871.05\nEquity"
            eq_match = re.search(r'([\-\$\d,\.]+)\s*\n?\s*Equity', all_text)
            ret_match = re.search(r'([\-\d\.]+\s*%)\s*\n?\s*Return', all_text)
            np_match = re.search(r'([\-\$\d,\.]+)\s*\n?\s*Net Profit', all_text)
            if eq_match:
                data['equity'] = _parse_value(eq_match.group(1))
            if ret_match:
                data['return_pct'] = _parse_value(ret_match.group(1))
            if np_match:
                data['net_profit'] = _parse_value(np_match.group(1))
        except Exception:
            pass

    return data


def check_backtest_running(page):
    """Check if backtest is still running by looking for progress indicators."""
    try:
        text = page.inner_text('body', timeout=3000)
        # Look for "Completed" status
        if 'Completed' in text and 'Up Time' in text:
            # Check server stats - if "Up Time" exists, it's still running
            uptime_match = re.search(r'Up Time\s*\n?\s*([\dd:hms ]+)', text)
            if uptime_match:
                return True  # still running
        # Check for progress indicator
        if 'Progress' in text:
            return True
        return False
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Monitor backtest via QC web UI")
    parser.add_argument("backtest_id")
    parser.add_argument("--project-id", type=int, default=PROJECT_ID)
    parser.add_argument("--timeout", type=int, default=14400)
    parser.add_argument("--poll-interval", type=int, default=30, help="Seconds between checks (default 30)")
    parser.add_argument("--max-dd", type=float, default=None)
    parser.add_argument("--check-after-progress", type=float, default=0.08)
    parser.add_argument("--baseline", type=str, default=None)
    parser.add_argument("--baseline-tolerance", type=float, default=0.5)
    parser.add_argument("--baseline-fail-count", type=int, default=3)
    parser.add_argument("--baseline-check-after", type=float, default=0.08)
    parser.add_argument("--baseline-check-interval", type=float, default=0.05)

    args = parser.parse_args()

    baseline = _load_baseline(args.baseline) if args.baseline else None

    print(f"🌐 Web Monitor: Backtest {args.backtest_id}")
    if baseline:
        print(f"   Baseline: stop if equity < {args.baseline_tolerance*100:.0f}% of M0 "
              f"for {args.baseline_fail_count} consecutive checks")

    # Launch Playwright with Chrome session
    from playwright.sync_api import sync_playwright

    chrome_profile = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default")
    url = f"https://www.quantconnect.com/terminal/{args.project_id}#open/{args.backtest_id}"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=chrome_profile,
            headless=True,
            channel="chrome",
        )
        page = context.new_page()
        print(f"   Opening: {url}")
        page.goto(url, timeout=30000)
        page.wait_for_timeout(5000)  # wait for page to load

        start_time = time.time()
        baseline_fails = 0
        last_baseline_progress = -1.0
        last_equity = None
        peak_equity = 0.0
        check_count = 0

        while True:
            elapsed = time.time() - start_time
            if elapsed > args.timeout:
                print(f"\n⏰ Timeout after {args.timeout}s")
                break

            # Refresh to get latest data
            if check_count > 0:
                page.reload(timeout=15000)
                page.wait_for_timeout(3000)

            check_count += 1
            data = scrape_backtest_data(page)
            equity = data.get('equity')
            return_pct = data.get('return_pct')
            net_profit = data.get('net_profit')

            if equity is not None:
                last_equity = equity
                if equity > peak_equity:
                    peak_equity = equity

            # Estimate progress from return (rough: compare to M0's timeline)
            progress = None
            if baseline and equity is not None:
                # Binary search for approximate progress
                for cp in baseline.get('checkpoints', []):
                    if cp.get('equity', 0) >= equity:
                        progress = cp['progress']
                        break

            ts = time.strftime("%H:%M:%S")
            eq_str = f"${equity:,.0f}" if equity else "N/A"
            ret_str = f"{return_pct:.1f}%" if return_pct is not None else "N/A"
            print(f"[{ts}] Equity: {eq_str}  Return: {ret_str}  Net Profit: ${net_profit:,.0f}" if net_profit else
                  f"[{ts}] Equity: {eq_str}  Return: {ret_str}")

            # Check if completed
            if not check_backtest_running(page):
                print("✅ Backtest appears completed.")
                break

            # ── Baseline check ──────────────────────────────
            if baseline and equity is not None and progress is not None:
                if progress >= args.baseline_check_after:
                    if progress - last_baseline_progress >= args.baseline_check_interval:
                        last_baseline_progress = progress
                        bl_eq = _get_baseline_equity_at(baseline, progress)
                        if bl_eq and bl_eq > 0:
                            threshold = bl_eq * args.baseline_tolerance
                            if equity < threshold:
                                baseline_fails += 1
                                print(f"   ⚠️  Baseline FAIL [{baseline_fails}/{args.baseline_fail_count}]: "
                                      f"${equity:,.0f} < {args.baseline_tolerance*100:.0f}% of ${bl_eq:,.0f}")
                                if baseline_fails >= args.baseline_fail_count:
                                    print(f"\n⛔ Stopping: underperforming baseline for "
                                          f"{args.baseline_fail_count} consecutive checks")
                                    # Delete via API
                                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                                    from qc_api.client import QCApiClient
                                    try:
                                        QCApiClient().delete_backtest(args.project_id, args.backtest_id)
                                        print("   ✅ Backtest deleted.")
                                    except Exception as e:
                                        print(f"   ⚠️  Delete failed: {e}")
                                    context.close()
                                    sys.exit(EXIT_EARLY_STOP)
                            else:
                                baseline_fails = 0

            time.sleep(args.poll_interval)

        context.close()


if __name__ == "__main__":
    main()
