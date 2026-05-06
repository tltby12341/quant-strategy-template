import yfinance as yf
import pandas as pd

# Let's take APP in 2024, PLTR in 2024, VRT in 2023, NVDA in 2023, NVDA in 2024
# and see if our M0 filters (which we want to keep/modify) would have caught them.

# M0 core logic:
# 1. Is in Top 500 turnover today.
# 2. Is closing near 60-day high (within 3%).
# 3. Is up on the day (Close > Open).
# 4. Optional N3 logic: Intraday return > 1.5%.

tickers = ['APP', 'PLTR', 'NVDA', 'CVNA', 'ASTS', 'SYM', 'HOOD', 'VRT']

data = yf.download(tickers, start="2023-01-01", end="2026-01-31", progress=False)

print("Analyzing top performers for M0 / N3 logic feasibility...")

for ticker in tickers:
    df_close = data['Close'][ticker]
    df_open = data['Open'][ticker]
    df_vol = data['Volume'][ticker]
    
    # Needs to drop NaN
    df_close = df_close.dropna()
    df_open = df_open.loc[df_close.index]
    df_vol = df_vol.loc[df_close.index]
    
    if df_close.empty: continue
    
    # Calculate rolling 60 day high
    h60 = df_close.rolling(window=60).max().shift(1) # yesterday's 60 day high
    
    close_open_pct = (df_close - df_open) / df_open
    
    is_near_high = df_close > (h60 * 0.97)
    is_up_today = close_open_pct > 0.0
    is_strong_today = close_open_pct > 0.015
    
    # We would need a volume approximation to know if they make the top 500 turnover.
    # Top 500 turnover usually requires >$200M/day.
    turnover = df_close * df_vol
    is_high_turnover = turnover > 200_000_000
    
    # Count trigger days per year
    df = pd.DataFrame({
        'close': df_close,
        'turnover': turnover,
        'is_near_high': is_near_high,
        'is_up_today': is_up_today,
        'is_strong_today': is_strong_today,
        'is_high_turnover': is_high_turnover
    }).dropna()
    
    df['year'] = df.index.year
    
    for year in sorted(df['year'].unique()):
        year_df = df[df['year'] == year]
        
        # Original M0: Near high + Up today + Top 500 turnover
        m0_triggers = year_df[year_df['is_high_turnover'] & year_df['is_near_high'] & year_df['is_up_today']]
        
        # N3 version: Near high + Strong today (>1.5%) + Top 500
        n3_triggers = year_df[year_df['is_high_turnover'] & year_df['is_near_high'] & year_df['is_strong_today']]
        
        # App Hunter version: M0 logic but relaxed turnover (Top 1000 roughly > $50M/day)
        hunter_triggers = year_df[(year_df['turnover'] > 50_000_000) & year_df['is_near_high'] & year_df['is_up_today']]
        
        roi = 0
        if not year_df.empty:
            roi = (year_df['close'].iloc[-1] / year_df['close'].iloc[0]) - 1
        
        if roi > 0.5: # Only show big years
            print(f"\n[{ticker} - {year}] Return: {roi*100:.0f}% | Avg Daily DlrVol: ${year_df['turnover'].mean()/1e6:.0f}M")
            print(f"  M0 Triggers (Strict 500): {len(m0_triggers)} days")
            print(f"  N3 Triggers (1.5% Intr):  {len(n3_triggers)} days")
            print(f"  AppHunter Triggers (1000):{len(hunter_triggers)} days")
