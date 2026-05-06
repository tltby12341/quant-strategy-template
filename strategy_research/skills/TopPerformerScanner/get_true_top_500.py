import pandas as pd
import yfinance as yf
import urllib.request
import io
import warnings

warnings.filterwarnings('ignore')

print("1. Downloading all US traded symbols from NASDAQ FTP...")
url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqtraded.txt"
try:
    response = urllib.request.urlopen(url)
    data = response.read().decode("utf-8")
    df_sym = pd.read_csv(io.StringIO(data), sep="|")
except Exception as e:
    print("Failed to download or parse NASDAQ directory:", e)
    exit(1)

# Exclude ETFs and Test Issues
if 'ETF' in df_sym.columns and 'Test Issue' in df_sym.columns:
    df_sym = df_sym[(df_sym['ETF'] == 'N') & (df_sym['Test Issue'] == 'N')]

# Filter for clean tickers (e.g., AAPL)
tickers = df_sym['Symbol'].dropna().unique().tolist()
tickers = [t for t in tickers if type(t) == str and len(t) <= 4 and t.isalpha()]

print(f"2. Found {len(tickers)} potential US equities. Downloading historical data (2019-2026)... This will take 1-2 minutes.")

# Download historical data
data = yf.download(tickers, start="2019-12-20", end="2026-02-28", progress=False, threads=True)

df_close = data['Close']
df_vol = data['Volume']

years = [2020, 2021, 2022, 2023, 2024, 2025]
results = []

print("3. Processing Top 500 liquidity filtering and calculating returns...")

for year in years:
    try:
        start_date = f"{year-1}-12-25"
        end_date = f"{year}-12-31"
        
        y_close = df_close.loc[start_date:end_date]
        y_vol = df_vol.loc[start_date:end_date]
        
        if y_close.empty or len(y_close) < 2: continue
        
        # Calculate average daily dollar volume to find the Top 500 most liquid stocks of that year
        dollar_vol = (y_close * y_vol).mean()
        
        # Drop NaNs
        dollar_vol = dollar_vol.dropna()
        
        # Get top 500 most traded stocks of the year
        top_500_tickers = dollar_vol.sort_values(ascending=False).head(500).index
        
        # Now find returns for these top 500
        y_close_top = y_close[top_500_tickers]
        
        # Find first valid price of the year
        start_prices = y_close_top.bfill().iloc[0]
        # Find last valid price of the year
        end_prices = y_close_top.ffill().iloc[-1]
        
        returns = (end_prices - start_prices) / start_prices
        
        # Filter price >= $5 to avoid extreme penny stock math anomalies
        # But allow spin-offs that might have started trading mid-year
        valid_mask = (start_prices >= 5.0) & start_prices.notna() & end_prices.notna()
        returns = returns[valid_mask]
        
        top_15 = returns.sort_values(ascending=False).head(15)
        
        print(f"\n================ TOP 15 PERFORMERS OF {year} (Among NASDAQ Top 500 Liquidity) ================")
        rank = 1
        for t, r in top_15.items():
            print(f"{rank:2d}. {t:5s} : {r*100:6.1f}% (Avg Daily Vol: ${dollar_vol[t]/1e6:.0f}M)")
            results.append({'year': year, 'rank': rank, 'ticker': t, 'return': r, 'avg_daily_vol_m': dollar_vol[t]/1e6})
            rank += 1
            
    except Exception as e:
        print(f"Error processing {year}: {e}")

pd.DataFrame(results).to_csv('nasdaq_top500_performers.csv', index=False)
print("\nDone. Saved comprehensive list to nasdaq_top500_performers.csv")
