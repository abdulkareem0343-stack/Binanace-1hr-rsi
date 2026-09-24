import ccxt
import pandas as pd
import time

# --- CONFIGURATION ---
EXCHANGES = ['binance', 'bybit', 'okx', 'kucoin', 'mexc'] 
TIMEFRAME = '5m'
EMA_FAST = 14
EMA_SLOW = 100
GAP_THRESHOLD_PERCENT = 0.3  # 0.3% gap threshold
TOP_N_PAIRS = 15             # Top 15 USDT pairs per exchange

def get_exchange_instance(exchange_id):
    """CCXT Exchange Instance with Rate-Limiting Enabled"""
    try:
        exchange_class = getattr(ccxt, exchange_id)
        return exchange_class({
            'enableRateLimit': True,
            'timeout': 10000
        })
    except Exception as e:
        print(f"Error initializing {exchange_id}: {e}")
        return None

def fetch_top_usdt_pairs(exchange, limit=15):
    """Fetch Top Volume USDT Spot Pairs"""
    try:
        tickers = exchange.fetch_tickers()
        usdt_pairs = []
        for symbol, ticker in tickers.items():
            if symbol.endswith('/USDT') and 'quoteVolume' in ticker and ticker['quoteVolume']:
                usdt_pairs.append((symbol, ticker['quoteVolume']))
        
        usdt_pairs.sort(key=lambda x: x[1], reverse=True)
        return [pair[0] for pair in usdt_pairs[:limit]]
    except Exception as e:
        print(f"[{exchange.id.upper()}] Error fetching pairs: {e}")
        return []

def analyze_symbol(exchange, symbol):
    """Fetch 5m OHLCV and Calculate EMA Crossover & Gap using Pure Pandas"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=150)
        if not ohlcv or len(ohlcv) < 100:
            return

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Pure Pandas se EMA Calculation (Streamlit Crash Safe)
        df['ema_fast'] = df['close'].ewm(span=EMA_FAST, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=EMA_SLOW, adjust=False).mean()
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        ema_fast_curr, ema_slow_curr = last_row['ema_fast'], last_row['ema_slow']
        ema_fast_prev, ema_slow_prev = prev_row['ema_fast'], prev_row['ema_slow']
        
        # Signals Check
        bullish_cross = (ema_fast_prev <= ema_slow_prev) and (ema_fast_curr > ema_slow_curr)
        bearish_cross = (ema_fast_prev >= ema_slow_prev) and (ema_fast_curr < ema_slow_curr)
        
        gap_percent = abs(ema_fast_curr - ema_slow_curr) / ema_slow_curr * 100
        close_gap = gap_percent <= GAP_THRESHOLD_PERCENT
        
        ex_name = exchange.id.upper()
        price = last_row['close']

        if bullish_cross:
            print(f"🚀 [BUY CROSS]  | {ex_name:<8} | {symbol:<10} | Price: {price} | EMA14 crossed ABOVE EMA100")
        elif bearish_cross:
            print(f"🔻 [SELL CROSS] | {ex_name:<8} | {symbol:<10} | Price: {price} | EMA14 crossed BELOW EMA100")
        elif close_gap:
            print(f"⚠️  [GAP ALERT]  | {ex_name:<8} | {symbol:<10} | Price: {price} | Gap: {gap_percent:.2f}% (EMA14: {ema_fast_curr:.4f}, EMA100: {ema_slow_curr:.4f})")

    except Exception:
        pass

def main():
    print("=" * 70)
    print(" MULTI-EXCHANGE 5m EMA 14/100 SCANNER INITIALIZED")
    print("=" * 70)
    
    active_exchanges = {}
    for ex_id in EXCHANGES:
        inst = get_exchange_instance(ex_id)
        if inst:
            print(f"Fetching top pairs for {ex_id.upper()}...")
            pairs = fetch_top_usdt_pairs(inst, limit=TOP_N_PAIRS)
            if pairs:
                active_exchanges[inst] = pairs
                print(f"✓ Loaded {len(pairs)} pairs for {ex_id.upper()}")
    
    print("\nStarting Scanning Loop... Press Ctrl+C to Stop.\n")
    
    while True:
        for exchange, pairs in active_exchanges.items():
            for symbol in pairs:
                analyze_symbol(exchange, symbol)
                time.sleep(0.15)
        
        print("\n--- Scan Loop Complete. Refreshing in 30 seconds --- \n")
        time.sleep(30)

if __name__ == '__main__':
    main()
