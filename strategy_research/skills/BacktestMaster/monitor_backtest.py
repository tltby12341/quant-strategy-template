import sys
import os
import json
import time
import argparse
from qc_api.client import QCApiClient
from qc_api.config import get_default_project_id

TIMEOUT_SECONDS = 3600
BASELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselines")
START_EQUITY = 10000

EXIT_SUCCESS   = 0
EXIT_ERROR     = 1
EXIT_TIMEOUT   = 2
EXIT_EARLY_STOP = 3


def _parse_pct(raw):
    if raw is None:
        return None
    s = str(raw).strip().rstrip('%')
    try:
        val = float(s)
        return val / 100.0 if val > 1.0 else val
    except ValueError:
        return None


def _parse_equity(raw):
    if raw is None:
        return None
    s = str(raw).strip().replace(',', '').replace('$', '')
    try:
        return float(s)
    except ValueError:
        return None


def _load_baseline(baseline_path):
    if not os.path.exists(baseline_path):
        print(f"   ⚠️  Baseline file not found: {baseline_path}")
        return None
    with open(baseline_path) as f:
        data = json.load(f)
    checkpoints = data.get("checkpoints", [])
    if not checkpoints:
        return None
    print(f"   Baseline loaded: {len(checkpoints)} checkpoints from {os.path.basename(baseline_path)}")
    return data


def _get_baseline_equity_at(baseline_data, progress):
    checkpoints = baseline_data["checkpoints"]
    if not checkpoints:
        return None
    prev, next_cp = None, None
    for cp in checkpoints:
        if cp["progress"] <= progress:
            prev = cp
        else:
            next_cp = cp
            break
    if prev is None:
        return checkpoints[0].get("equity")
    if next_cp is None:
        return prev.get("equity")
    p_range = next_cp["progress"] - prev["progress"]
    if p_range <= 0:
        return prev.get("equity")
    t = (progress - prev["progress"]) / p_range
    return prev.get("equity", 0) + t * (next_cp.get("equity", 0) - prev.get("equity", 0))


def _delete_and_exit(client, project_id, backtest_id, reason, output_key, output_val):
    print(f"\n⛔ {reason}")
    print(f"   Deleting backtest {backtest_id} via API...")
    try:
        client.delete_backtest(project_id, backtest_id)
        print("   ✅ Backtest deleted.")
    except Exception as e:
        print(f"   ⚠️  Delete failed: {e}")
    print(f"OUTPUT_EARLY_STOP_{output_key}:{output_val}")
    sys.exit(EXIT_EARLY_STOP)


def _find_backtest_in_list(client, project_id, backtest_id):
    """Use list_backtests to get reliable progress/stats for a running backtest."""
    try:
        resp = client.list_backtests(project_id)
        for bt in resp.get('backtests', []):
            if bt.get('backtestId') == backtest_id:
                return bt
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="Monitor backtest with early-stop")
    parser.add_argument("backtest_id")
    parser.add_argument("--project-id", type=int, default=get_default_project_id())
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SECONDS)
    parser.add_argument("--max-dd", type=float, default=None,
                        help="Early-stop if DD exceeds this %%. Example: --max-dd 75")
    parser.add_argument("--check-after-progress", type=float, default=0.08,
                        help="Start checks after this progress (default 0.08 = ~3 months)")
    parser.add_argument("--max-peak-drop", type=float, default=None,
                        help="Early-stop if equity drops this %% from peak")
    parser.add_argument("--baseline", type=str, default=None,
                        help="Baseline JSON or name (e.g. 'M0')")
    parser.add_argument("--baseline-tolerance", type=float, default=0.5,
                        help="Stop if equity < this fraction of baseline (default 0.5)")
    parser.add_argument("--baseline-fail-count", type=int, default=3,
                        help="Consecutive fails before stopping (default 3)")
    parser.add_argument("--baseline-check-after", type=float, default=0.08,
                        help="Start baseline checks after this progress (default 0.08)")
    parser.add_argument("--baseline-check-interval", type=float, default=0.05,
                        help="Check every N progress (default 0.05)")
    parser.add_argument("--capture-baseline", type=str, default=None,
                        help="Capture equity curve to baseline file")

    args = parser.parse_args()

    max_dd = args.max_dd
    if max_dd is not None and max_dd > 1.0:
        max_dd /= 100.0
    max_peak_drop = args.max_peak_drop
    if max_peak_drop is not None and max_peak_drop > 1.0:
        max_peak_drop /= 100.0

    baseline_data = None
    if args.baseline:
        bp = args.baseline if os.path.exists(args.baseline) else os.path.join(BASELINE_DIR, f"{args.baseline}.json")
        baseline_data = _load_baseline(bp)

    capture_checkpoints = []
    capture_file = None
    if args.capture_baseline:
        os.makedirs(BASELINE_DIR, exist_ok=True)
        capture_file = args.capture_baseline if args.capture_baseline.endswith('.json') else os.path.join(BASELINE_DIR, f"{args.capture_baseline}.json")

    client = QCApiClient()
    print(f"🔍 Monitoring Backtest {args.backtest_id}...")
    if max_dd is not None:
        print(f"   Early-stop: DD > {max_dd*100:.0f}% (after {args.check_after_progress*100:.0f}% progress)")
    if max_peak_drop is not None:
        print(f"   Early-stop: Peak drop > {max_peak_drop*100:.0f}% (after {args.check_after_progress*100:.0f}% progress)")
    if baseline_data:
        print(f"   Baseline: stop if equity < {args.baseline_tolerance*100:.0f}% of M0 for "
              f"{args.baseline_fail_count} consecutive checks (after {args.baseline_check_after*100:.0f}%)")
    if capture_file:
        print(f"   📸 Capture mode → {capture_file}")

    start_time = time.time()
    had_error = False
    peak_equity = 0.0
    last_captured_progress = -1.0
    baseline_consecutive_fails = 0
    last_baseline_check_progress = -1.0
    last_progress = -1.0

    while True:
        if time.time() - start_time > args.timeout:
            print(f"\n⏰ Timeout after {args.timeout}s.")
            if capture_file and capture_checkpoints:
                _save_capture(capture_file, capture_checkpoints, completed=False)
            sys.exit(EXIT_TIMEOUT)

        try:
            # ── Primary: use list_backtests for reliable progress/stats ──
            list_bt = _find_backtest_in_list(client, args.project_id, args.backtest_id)

            # Fallback: read_backtest for error detection and runtimeStatistics
            resp = client.read_backtest(args.project_id, args.backtest_id)
            read_bt = resp.get('backtest', resp)

            # Merge: prefer list_backtests progress (more reliable during running)
            if list_bt:
                state = list_bt.get('progress', 0) or 0
                completed = list_bt.get('completed', False)
                list_net_profit = list_bt.get('netProfit')  # e.g. 0.3831 = 38.31%
                list_dd = list_bt.get('drawdown')  # e.g. 0.656 = 65.6%
            else:
                state = read_bt.get('progress', 0) or 0
                completed = read_bt.get('completed', False)
                list_net_profit = None
                list_dd = None

            # Calculate equity from net profit
            current_equity = None
            runtime_stats = read_bt.get('runtimeStatistics', {})
            # Try runtimeStatistics first (most accurate when available)
            rt_equity = _parse_equity(runtime_stats.get('Equity'))
            if rt_equity and rt_equity > 0:
                current_equity = rt_equity
            # Fallback: calculate from list_backtests netProfit
            elif list_net_profit is not None:
                current_equity = START_EQUITY * (1 + list_net_profit)

            # Progress bar
            bar_length = 30
            filled = int(bar_length * state)
            bar = '█' * filled + '-' * (bar_length - filled)
            eq_str = f" ${current_equity:,.0f}" if current_equity else ""
            # Only print when progress changes
            if state != last_progress:
                print(f"\rProgress: |{bar}| {state*100:.1f}%{eq_str}")
                last_progress = state

            # Error check
            error = read_bt.get('error') or (list_bt.get('error') if list_bt else None)
            if error:
                print(f"\n❌ Runtime Error:\n{error}")
                had_error = True
                break

            # Completion
            if completed or state >= 1.0:
                print(f"\n✅ Backtest Completed!{eq_str}")
                break

            # Track peak equity
            if current_equity is not None and current_equity > peak_equity:
                peak_equity = current_equity

            # ── Capture ─────────────────────────────────────────────────
            if capture_file and current_equity is not None and state - last_captured_progress >= 0.01:
                capture_checkpoints.append({
                    "progress": round(state, 4),
                    "equity": round(current_equity, 2),
                    "net_profit_pct": round((current_equity - START_EQUITY) / START_EQUITY * 100, 2),
                })
                last_captured_progress = state

            # ── DD check ────────────────────────────────────────────────
            if max_dd is not None and state >= args.check_after_progress:
                dd = list_dd  # from list_backtests, most reliable
                if dd is not None and dd > max_dd:
                    _delete_and_exit(client, args.project_id, args.backtest_id,
                        f"Early Stop at {state*100:.1f}%: DD {dd*100:.1f}% > {max_dd*100:.0f}%",
                        "DD", f"{dd*100:.2f}")

            # ── Peak-drop check ─────────────────────────────────────────
            if max_peak_drop is not None and state >= args.check_after_progress:
                if peak_equity > 0 and current_equity is not None:
                    drop = (peak_equity - current_equity) / peak_equity
                    if drop > max_peak_drop:
                        _delete_and_exit(client, args.project_id, args.backtest_id,
                            f"Early Stop at {state*100:.1f}%: Equity dropped {drop*100:.1f}% from peak "
                            f"(${peak_equity:,.0f}→${current_equity:,.0f}) > {max_peak_drop*100:.0f}%",
                            "PEAK_DROP", f"{drop*100:.2f}")

            # ── Baseline comparison ─────────────────────────────────────
            if baseline_data and state >= args.baseline_check_after and current_equity is not None:
                if state - last_baseline_check_progress >= args.baseline_check_interval:
                    last_baseline_check_progress = state
                    baseline_eq = _get_baseline_equity_at(baseline_data, state)
                    if baseline_eq is not None and baseline_eq > 0:
                        threshold_eq = baseline_eq * args.baseline_tolerance
                        if current_equity < threshold_eq:
                            baseline_consecutive_fails += 1
                            print(f"\n   ⚠️  Baseline fail at {state*100:.0f}%: "
                                  f"${current_equity:,.0f} < {args.baseline_tolerance*100:.0f}% of "
                                  f"${baseline_eq:,.0f} [{baseline_consecutive_fails}/{args.baseline_fail_count}]")
                            if baseline_consecutive_fails >= args.baseline_fail_count:
                                _delete_and_exit(client, args.project_id, args.backtest_id,
                                    f"Early Stop at {state*100:.1f}%: Underperforming baseline "
                                    f"for {args.baseline_fail_count} consecutive checks. "
                                    f"${current_equity:,.0f} vs baseline ${baseline_eq:,.0f}",
                                    "BASELINE", f"{current_equity:.0f}_vs_{baseline_eq:.0f}")
                        else:
                            if baseline_consecutive_fails > 0:
                                print(f"\n   ✓ Baseline pass at {state*100:.0f}%: "
                                      f"${current_equity:,.0f} >= ${threshold_eq:,.0f} [reset]")
                            baseline_consecutive_fails = 0

        except Exception as e:
            print(f"\n⚠️ Error: {e}")
            time.sleep(5)

        time.sleep(10)  # poll every 10s (list_backtests is heavier)

    if capture_file and capture_checkpoints:
        if current_equity is not None:
            capture_checkpoints.append({
                "progress": 1.0,
                "equity": round(current_equity, 2),
                "net_profit_pct": round((current_equity - START_EQUITY) / START_EQUITY * 100, 2),
            })
        _save_capture(capture_file, capture_checkpoints, completed=True)

    if had_error:
        sys.exit(EXIT_ERROR)


def _save_capture(filepath, checkpoints, completed=False):
    data = {
        "description": "Baseline equity checkpoints captured from live backtest",
        "completed": completed,
        "capture_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "checkpoints": checkpoints,
    }
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n   📸 Baseline saved: {len(checkpoints)} checkpoints → {filepath}")


if __name__ == "__main__":
    main()
