#!/usr/bin/env python3
"""BacktestMaster 批量扫描调度器 — 事件驱动双节点

支持两种目录结构:
  扁平: sweep_dir/Z08_2020/v4.0_Z08_2020.py  (--flat)
  嵌套: sweep_dir/R03/2025/R03_2025.py        (默认)

用法:
  # 嵌套结构 (variant/year/file.py)
  python batch_sweep.py /path/to/sweep_dir --prefix v4.1_

  # 扁平结构 (varname_year/file.py)
  python batch_sweep.py /path/to/sweep_dir --flat --prefix v4.0_

  # 自定义节点数和轮询间隔
  python batch_sweep.py /path/to/sweep_dir --flat --nodes 2 --poll 60
"""
import subprocess, sys, os, time, json, glob, re, argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(SCRIPT_DIR, "run_workflow.py")
GET_RESULTS = os.path.join(SCRIPT_DIR, "get_results.py")

sys.path.insert(0, SCRIPT_DIR)
from qc_api.client import QCApiClient
from qc_api.config import get_default_project_id


def get_qc_status(client, project_id):
    for attempt in range(3):
        try:
            bt_list = client.list_backtests(project_id)
            break
        except Exception:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
            else:
                raise
    running, completed = [], {}
    for bt in bt_list.get("backtests", []):
        name = bt.get("name", "")
        status = bt.get("status", "")
        bid = bt.get("backtestId", "")
        if any(k in status for k in ["Running", "InQueue", "Building", "In Progress", "Initializing"]):
            running.append(name)
        elif "Completed" in status:
            completed[name] = bid
    return running, completed


def has_valid_result(result_dir):
    for f in glob.glob(os.path.join(result_dir, "*_result.json")):
        try:
            d = json.load(open(f))
            stats = d.get("backtest", {}).get("statistics", {})
            if stats and stats.get("Total Orders", "0") != "0":
                return True
        except (json.JSONDecodeError, KeyError):
            continue
    return False


def submit_one(main_file, name):
    cmd = [sys.executable, RUNNER, "--main-file", main_file,
           "--name", name, "--skip-monitor", "--timeout", "14400"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        print(f"  ✓ {name} 已提交", flush=True)
        return True
    print(f"  ✗ {name} 提交失败: {(result.stderr or result.stdout)[-200:]}", flush=True)
    return False


def download_result(name, result_dir, backtest_id):
    dl_cmd = [sys.executable, GET_RESULTS, backtest_id, "--output-dir", result_dir]
    dl = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=60)
    for line in dl.stdout.split("\n"):
        if any(k in line for k in ["Net Profit", "Sharpe", "Drawdown"]):
            print(f"    {line.strip()}")
    if dl.returncode == 0:
        print(f"  💾 {name} 已保存", flush=True)
        return True
    print(f"  ⚠ {name} 下载失败", flush=True)
    return False


def build_queue_nested(sweep_dir, prefix):
    """嵌套结构: sweep_dir/variant/year/prefix_variant_year.py"""
    queue = []
    for var_dir in sorted(os.listdir(sweep_dir)):
        var_path = os.path.join(sweep_dir, var_dir)
        if not os.path.isdir(var_path) or var_dir.startswith('.') or var_dir == '__pycache__':
            continue
        for year in sorted(os.listdir(var_path)):
            year_path = os.path.join(var_path, year)
            if not os.path.isdir(year_path):
                continue
            if has_valid_result(year_path):
                continue
            name = f"{var_dir}_{year}"
            py_file = os.path.join(year_path, f"{prefix}{name}.py")
            if not os.path.exists(py_file):
                # try without prefix
                py_file = os.path.join(year_path, f"{name}.py")
            if os.path.exists(py_file):
                queue.append((name, py_file, year_path))
    return queue


def build_queue_flat(sweep_dir, prefix):
    """扁平结构: sweep_dir/Z08_2020/prefix_Z08_2020.py"""
    queue = []
    pattern = re.compile(r'^[A-Za-z]\w+_\d{4}$')
    for d in sorted(os.listdir(sweep_dir)):
        d_path = os.path.join(sweep_dir, d)
        if not os.path.isdir(d_path) or not pattern.match(d):
            continue
        if has_valid_result(d_path):
            continue
        py_file = os.path.join(d_path, f"{prefix}{d}.py")
        if not os.path.exists(py_file):
            py_file = os.path.join(d_path, f"{d}.py")
        if os.path.exists(py_file):
            queue.append((d, py_file, d_path))
    return queue


def run_sweep(sweep_dir, flat, prefix, max_nodes, poll_interval, project_id):
    client = QCApiClient()

    if flat:
        queue = build_queue_flat(sweep_dir, prefix)
    else:
        queue = build_queue_nested(sweep_dir, prefix)

    print(f"批量扫描: {len(queue)} 个回测 (事件驱动, {max_nodes}节点)")
    print(f"目录: {sweep_dir}")
    print(f"模式: {'扁平' if flat else '嵌套'} | 前缀: '{prefix}'")
    for i, (name, py_file, _) in enumerate(queue):
        print(f"  {i+1}. {name}")
    print(f"{'='*60}\n", flush=True)

    completed, failed = [], []
    # name -> (py_file, result_dir, submit_time, miss_count)
    in_flight = {}
    qi = 0
    GRACE_PERIOD = 120
    MISS_THRESHOLD = 5

    # Startup: adopt running, download completed
    running_names, completed_map = get_qc_status(client, project_id)
    new_queue = []
    for name, py_file, result_dir in queue:
        if name in running_names:
            in_flight[name] = (py_file, result_dir, 0, 0)
            print(f"  ⏩ 接管已运行: {name}", flush=True)
        elif name in completed_map:
            print(f"  ⏬ 下载已完成: {name}", flush=True)
            if download_result(name, result_dir, completed_map[name]):
                completed.append(name)
            else:
                failed.append(name)
        else:
            new_queue.append((name, py_file, result_dir))
    queue = new_queue
    print(f"实际待提交: {len(queue)} 个, 已在运行: {len(in_flight)} 个\n", flush=True)

    while qi < len(queue) or in_flight:
        running_names, completed_map = get_qc_status(client, project_id)
        now = time.time()

        # Check in-flight completions
        done_names = []
        for name, (pf, rd, t, mc) in list(in_flight.items()):
            if t > 0 and (now - t) < GRACE_PERIOD:
                continue
            if name in running_names:
                in_flight[name] = (pf, rd, t, 0)
                continue
            if name in completed_map:
                done_names.append(name)
                continue
            new_mc = mc + 1
            if new_mc >= MISS_THRESHOLD:
                done_names.append(name)
            else:
                in_flight[name] = (pf, rd, t, new_mc)

        for name in done_names:
            _, result_dir, _, _ = in_flight.pop(name)
            if name in completed_map:
                if download_result(name, result_dir, completed_map[name]):
                    completed.append(name)
                else:
                    failed.append(name)
            else:
                failed.append(name)
            print(f"  进度: {len(completed)}完成, {len(in_flight)}运行中, {len(queue)-qi}待提交", flush=True)

        # Submit new jobs
        actual_running = len(running_names)
        free_slots = max_nodes - max(actual_running, len(in_flight))

        while qi < len(queue) and free_slots > 0:
            name, py_file, result_dir = queue[qi]
            qi += 1
            if has_valid_result(result_dir):
                completed.append(name)
                continue
            if name in running_names:
                in_flight[name] = (py_file, result_dir, 0, 0)
                free_slots -= 1
                continue
            if name in completed_map:
                if download_result(name, result_dir, completed_map[name]):
                    completed.append(name)
                continue

            running_names_now, _ = get_qc_status(client, project_id)
            if len(running_names_now) >= max_nodes:
                qi -= 1
                break

            print(f"\n[{qi}/{len(queue)}] 提交: {name} (空闲节点: {free_slots})", flush=True)
            if submit_one(py_file, name):
                in_flight[name] = (py_file, result_dir, time.time(), 0)
                free_slots -= 1
                time.sleep(3)
            else:
                qi -= 1
                break

        if in_flight:
            status = ", ".join(in_flight.keys())
            print(f"  ⏳ 运行中({len(in_flight)}): {status}", flush=True)
            time.sleep(poll_interval)
        elif qi >= len(queue):
            break

    print(f"\n{'='*60}")
    print(f"✅ 完成: {len(completed)} | ❌ 失败: {len(failed)}")
    if failed:
        print(f"失败列表: {failed}")
    return completed, failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BacktestMaster 批量扫描调度器")
    parser.add_argument("sweep_dir", help="扫描目录路径")
    parser.add_argument("--flat", action="store_true", help="扁平目录结构 (varname_year/file.py)")
    parser.add_argument("--prefix", default="", help="策略文件前缀 (如 'v4.0_')")
    parser.add_argument("--nodes", type=int, default=2, help="最大并行节点数 (默认2)")
    parser.add_argument("--poll", type=int, default=60, help="轮询间隔秒数 (默认60)")
    parser.add_argument("--project-id", type=int, default=get_default_project_id(), help="QC项目ID")
    args = parser.parse_args()

    run_sweep(
        sweep_dir=os.path.abspath(args.sweep_dir),
        flat=args.flat,
        prefix=args.prefix,
        max_nodes=args.nodes,
        poll_interval=args.poll,
        project_id=args.project_id,
    )
