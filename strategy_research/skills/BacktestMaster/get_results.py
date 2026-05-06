import sys
import json
import csv
import argparse
import os
from qc_api.client import QCApiClient
from qc_api.config import get_default_project_id

ORDER_TYPE = {0: "Market", 1: "Limit", 2: "StopMarket", 3: "StopLimit", 4: "MarketOnOpen", 5: "MarketOnClose"}
ORDER_STATUS = {0: "New", 1: "Submitted", 2: "PartiallyFilled", 3: "Filled", 4: "Cancelled", 5: "Invalid"}

def main():
    parser = argparse.ArgumentParser(description="Get results of a completed backtest")
    parser.add_argument("backtest_id", help="Backtest ID")
    parser.add_argument("--project-id", type=int, default=get_default_project_id(), help="QuantConnect Project ID (defaults to QC_PROJECT_ID env var)")
    parser.add_argument("--output-dir", default=".", help="Directory to save results")

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    client = QCApiClient()

    print(f"📥 Fetching results for Backtest {args.backtest_id}...")

    try:
        # 1. Get main backtest object
        resp = client.read_backtest(args.project_id, args.backtest_id)
        result = resp.get('backtest', resp)

        # Save full stats JSON
        json_path = os.path.join(args.output_dir, f"{args.backtest_id}_result.json")
        with open(json_path, 'w') as f:
            json.dump(resp, f, indent=2)
        print(f"📄 Full result saved to {json_path}")

        # Check for runtime error
        if result.get('error'):
            print(f"\n❌ Backtest ended with error: {result['error']}")

        # 2. Key Statistics
        stats = result.get('statistics', {})
        if stats:
            print("\n📊 Key Statistics:")
            for k in ["Total Orders", "Net Profit", "Sharpe Ratio", "Drawdown", "Win Rate", "Total Fees"]:
                if k in stats:
                    print(f"  - {k}: {stats[k]}")

        # 3. Orders via dedicated endpoint
        # 3. Orders via dedicated endpoint
        all_orders = []
        start_idx = 0
        limit = 100
        while True:
            orders_resp = client.read_backtest_orders(args.project_id, args.backtest_id, start=start_idx, end=start_idx + limit)
            batch = orders_resp.get('orders', [])
            if not batch:
                break
            all_orders.extend(batch)
            # Some APIs might return exactly 'limit' items on the final page, 
            # but usually it's safe to break if less than limit. Let's be safe.
            if len(batch) < limit:
                break
            start_idx += limit

        if all_orders:
            csv_path = os.path.join(args.output_dir, f"{args.backtest_id}_orders.csv")
            rows = []
            for o in all_orders:
                symbol = o.get('symbol', {}).get('value', '')
                fill_event = next((e for e in o.get('events', []) if e.get('status') == 'filled'), None)
                rows.append({
                    'orderId':     o.get('id'),
                    'symbol':      symbol,
                    'type':        ORDER_TYPE.get(o.get('type'), o.get('type')),
                    'direction':   'buy' if o.get('direction') == 0 else 'sell',
                    'quantity':    o.get('quantity'),
                    'fillPrice':   fill_event['fillPrice'] if fill_event else '',
                    'fillQty':     fill_event['fillQuantity'] if fill_event else '',
                    'fee':         fill_event.get('orderFeeAmount', '') if fill_event else '',
                    'status':      ORDER_STATUS.get(o.get('status'), o.get('status')),
                    'submitTime':  o.get('time'),
                    'fillTime':    o.get('lastFillTime'),
                    'tag':         o.get('tag'),
                })
            with open(csv_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            print(f"📝 Orders ({len(rows)}) saved to {csv_path}")
        else:
            print("ℹ️  No orders in this backtest.")

        # 4. Trades (closed round-trips) via dedicated endpoint
        all_trades = []
        start_idx = 0
        limit = 100
        while True:
            trades_resp = client.read_backtest_trades(args.project_id, args.backtest_id, start=start_idx, end=start_idx + limit)
            batch = trades_resp.get('trades', [])
            if not batch:
                break
            all_trades.extend(batch)
            if len(batch) < limit:
                break
            start_idx += limit

        if all_trades:
            csv_path = os.path.join(args.output_dir, f"{args.backtest_id}_trades.csv")
            rows = []
            for t in all_trades:
                symbols = t.get('symbols', [])
                sym_str = symbols[0].get('value', '') if symbols else ''
                ticker = sym_str.split()[0] if sym_str else ''
                rows.append({
                    'entryTime':   t.get('entryTime', ''),
                    'exitTime':    t.get('exitTime', ''),
                    'symbol':      sym_str,
                    'ticker':      ticker,
                    'direction':   'buy' if t.get('direction') == 0 else 'sell',
                    'entryPrice':  t.get('entryPrice', ''),
                    'exitPrice':   t.get('exitPrice', ''),
                    'quantity':    t.get('quantity', ''),
                    'pnl':         t.get('profitLoss', ''),
                    'fees':        t.get('totalFees', ''),
                    'mae':         t.get('mae', ''),
                    'mfe':         t.get('mfe', ''),
                    'drawdown':    t.get('endTradeDrawdown', ''),
                    'isWin':       t.get('isWin', ''),
                })
            with open(csv_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            print(f"📊 Trades ({len(rows)}) saved to {csv_path}")
        else:
            print("ℹ️  No trades in this backtest.")

        # 5. Logs via paginated API
        all_logs = []
        log_start = 0
        log_page = 200
        while True:
            log_resp = client.read_backtest_logs(args.project_id, args.backtest_id, start=log_start, end=log_start + log_page)
            lines = log_resp.get('logs', [])
            if not lines:
                break
            all_logs.extend(lines)
            if len(lines) < log_page:
                break
            log_start += log_page

        if all_logs:
            log_path = os.path.join(args.output_dir, f"{args.backtest_id}_logs.txt")
            with open(log_path, 'w') as f:
                for line in all_logs:
                    f.write(line + '\n')
            print(f"📋 Logs ({len(all_logs)} lines) saved to {log_path}")
        else:
            print("ℹ️  No logs in this backtest.")

    except Exception as e:
        print(f"❌ Failed to fetch results: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
