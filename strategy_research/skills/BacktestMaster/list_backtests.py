import argparse
from qc_api.client import QCApiClient
from qc_api.config import get_default_project_id

STATUS_ICON = {
    "Completed.": "✅",
    "Runtime Error": "❌",
    "In Queue...": "⏳",
    "Running...": "🔄",
}

def main():
    parser = argparse.ArgumentParser(description="List backtests for a project")
    parser.add_argument("--project-id", type=int, default=get_default_project_id(), help="QuantConnect Project ID")
    parser.add_argument("--limit", type=int, default=10, help="Number of backtests to show")
    args = parser.parse_args()

    client = QCApiClient()
    resp = client.list_backtests(args.project_id)
    backtests = resp.get('backtests', [])

    if not backtests:
        print("No backtests found.")
        return

    print(f"\n{'#':<4} {'Status':<18} {'Name':<35} {'Created':<22} {'ID'}")
    print("-" * 105)
    for i, bt in enumerate(backtests[:args.limit], 1):
        status = bt.get('status', '')
        icon = STATUS_ICON.get(status, '❓')
        print(f"{i:<4} {icon} {status:<15} {bt.get('name', ''):<35} {bt.get('created', ''):<22} {bt.get('backtestId', '')}")

    print(f"\nShowing {min(args.limit, len(backtests))} of {len(backtests)} backtests.")

if __name__ == "__main__":
    main()
