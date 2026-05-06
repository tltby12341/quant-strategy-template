import sys
import os

sys.path.append(os.path.abspath('.'))
from phoenix_agent.qc_runner import QCBacktestRunner
from phoenix_agent.deep_forensics import FeatureForensics

if len(sys.argv) < 2:
    print("Usage: python download_and_analyze.py <bt_id> [output_dir]")
    sys.exit(1)

bt_id = sys.argv[1]
output_dir = sys.argv[2] if len(sys.argv) > 2 else f"results/auto_{bt_id[:8]}"

print(f"Downloading results for {bt_id} into {output_dir}...")
runner = QCBacktestRunner()
res = runner.get_results(bt_id, output_dir=output_dir)

orders_csv = res.get('orders_csv')
if not orders_csv or not os.path.exists(orders_csv):
    print("Could not download orders CSV.")
    sys.exit(1)

print(f"Running deep forensics on {orders_csv}...")
forensics = FeatureForensics(orders_csv)
report = forensics.analyze()

diag_path = os.path.join(output_dir, 'diagnosis.txt')
with open(diag_path, 'w') as f:
    f.write(report)

print(f"Done! Diagnosis saved to {diag_path}")
