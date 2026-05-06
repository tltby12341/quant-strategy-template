import sys
import subprocess
import os
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qc_api.config import get_default_project_id

# Monitor exit codes (mirrors monitor_backtest.py)
EXIT_MONITOR_SUCCESS    = 0
EXIT_MONITOR_ERROR      = 1
EXIT_MONITOR_TIMEOUT    = 2
EXIT_MONITOR_EARLY_STOP = 3


def run_script(script_path, args):
    """
    Runs a python script and streams output line-by-line.
    Returns: (returncode, full_output_lines, captured_id)
    """
    python_cmd = sys.executable
    cmd = [python_cmd, script_path] + args

    print(f"\n🚀 Running: {os.path.basename(script_path)} {' '.join(args)}")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        captured_id = None
        full_output = []

        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                stripped = line.strip()
                print(stripped)
                full_output.append(stripped)

                if "OUTPUT_BACKTEST_ID:" in stripped:
                    captured_id = stripped.split("OUTPUT_BACKTEST_ID:")[1].strip()

        returncode = process.poll()
        return returncode, full_output, captured_id

    except Exception as e:
        print(f"Failed to run script: {e}")
        return -1, [], None


def main():
    parser = argparse.ArgumentParser(description="Full Workflow: Submit -> Monitor -> Get Results")
    parser.add_argument("--main-file", required=True, help="Path to the main strategy .py file")
    parser.add_argument("--project-id", type=str, default=str(get_default_project_id()), help="QuantConnect Project ID (defaults to QC_PROJECT_ID env var)")
    parser.add_argument("--name", help="Backtest Name")
    parser.add_argument("--timeout", type=int, default=None, help="Monitor timeout in seconds")

    # ── Early-stop thresholds ────────────────────────────────────────────────
    parser.add_argument("--max-dd", type=float, default=None,
                        help="Early-stop if DD exceeds this %%. Example: --max-dd 65")
    parser.add_argument("--check-after-progress", type=float, default=0.07,
                        help="Start DD/peak-drop checks after this progress (default 0.07)")
    parser.add_argument("--max-peak-drop", type=float, default=None,
                        help="Early-stop if equity drops this %% from peak. Example: --max-peak-drop 60")

    # ── Baseline comparison ──────────────────────────────────────────────────
    parser.add_argument("--baseline", type=str, default=None,
                        help="Baseline JSON file or name (e.g. 'M0'). Stops if underperforming.")
    parser.add_argument("--baseline-tolerance", type=float, default=0.5,
                        help="Stop if equity < this fraction of baseline (default 0.5 = 50%%)")
    parser.add_argument("--baseline-fail-count", type=int, default=3,
                        help="Consecutive fails before stopping (default 3)")
    parser.add_argument("--baseline-check-after", type=float, default=0.15,
                        help="Start baseline checks after this progress (default 0.15)")

    # ── Capture mode ─────────────────────────────────────────────────────────
    parser.add_argument("--capture-baseline", type=str, default=None,
                        help="Capture equity curve to baseline file. Example: --capture-baseline M0")

    # ── Skip monitor (browser monitoring instead) ──────────────────────────
    parser.add_argument("--skip-monitor", action="store_true",
                        help="Only submit, skip code monitoring. Use browser to monitor.")

    args = parser.parse_args()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # ── 1. Submit ────────────────────────────────────────────────────────────
    submit_script = os.path.join(base_dir, "submit_backtest.py")
    submit_args = ["--main-file", args.main_file, "--project-id", args.project_id]
    if args.name:
        submit_args.extend(["--name", args.name])

    rc, _, backtest_id = run_script(submit_script, submit_args)
    if rc != 0 or not backtest_id:
        print("❌ Submission failed or Backtest ID not found.")
        sys.exit(1)

    print(f"\n✅ Backtest ID Captured: {backtest_id}")

    if args.skip_monitor:
        print(f"\n⏭️  Skipping code monitor. Monitor in browser.")
        print(f"   To stop: python3 -c \"import sys; sys.path.insert(0,'strategy_research/skills/BacktestMaster'); from qc_api.client import QCApiClient; QCApiClient().delete_backtest({args.project_id}, '{backtest_id}')\"")
        sys.exit(0)

    time.sleep(2)

    # ── 2. Monitor ───────────────────────────────────────────────────────────
    monitor_script = os.path.join(base_dir, "monitor_backtest.py")
    monitor_args = [backtest_id, "--project-id", args.project_id]

    if args.timeout is not None:
        monitor_args.extend(["--timeout", str(args.timeout)])
    if args.max_dd is not None:
        monitor_args.extend(["--max-dd", str(args.max_dd)])
    monitor_args.extend(["--check-after-progress", str(args.check_after_progress)])
    if args.max_peak_drop is not None:
        monitor_args.extend(["--max-peak-drop", str(args.max_peak_drop)])
    if args.baseline:
        monitor_args.extend(["--baseline", args.baseline])
        monitor_args.extend(["--baseline-tolerance", str(args.baseline_tolerance)])
        monitor_args.extend(["--baseline-fail-count", str(args.baseline_fail_count)])
        monitor_args.extend(["--baseline-check-after", str(args.baseline_check_after)])
    if args.capture_baseline:
        monitor_args.extend(["--capture-baseline", args.capture_baseline])

    rc, _, _ = run_script(monitor_script, monitor_args)

    if rc == EXIT_MONITOR_ERROR:
        print("❌ Backtest ended with a runtime error. Skipping result download.")
        sys.exit(1)

    if rc == EXIT_MONITOR_TIMEOUT:
        print("⏰ Monitoring timed out. Skipping result download.")
        sys.exit(2)

    if rc == EXIT_MONITOR_EARLY_STOP:
        print(f"\n⛔ Workflow stopped early: threshold exceeded.")
        print("   Backtest has been deleted from QC. No results to download.")
        print("   → Adjust strategy and resubmit.")
        sys.exit(3)

    # ── 3. Get Results — 下载到策略文件所在目录 ─────────────────────────────
    get_results_script = os.path.join(base_dir, "get_results.py")
    strategy_dir = os.path.dirname(os.path.abspath(args.main_file))
    get_results_args = [backtest_id, "--project-id", args.project_id, "--output-dir", strategy_dir]

    rc, _, _ = run_script(get_results_script, get_results_args)
    if rc == 0:
        print("\n🎉 Workflow Completed Successfully!")
    else:
        print("\n❌ Failed to retrieve results.")


if __name__ == "__main__":
    main()
