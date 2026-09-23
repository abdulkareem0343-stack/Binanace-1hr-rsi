import ccxt
import pandas as pd
import pandas_ta as ta
import time

# Binance API Setup (Public Data / No API Key Required)
exchange = ccxt.binance({
    'enableRateLimit': True,
})

def fetch_and_scan():
    print("Binance Markets load ho rahe hain...")
    markets = exchange.load_markets()
    
    # Sirf USDT Spot Pairs filter karein (e.g., BTC/USDT)
    usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT') and markets[symbol]['spot']]
    
    print(f"Total {len(usdt_pairs)} USDT pairs milay. Scanning shuru ho rahi hai...\n")
    print(f"{'Coin':<12} | {'Current Price':<12} | {'RSI (1H)':<8}")
    print("-" * 40)

    for symbol in usdt_pairs:
        try:
            # 1-Hour Timeframe ka Candle Data (OHLCV) fetch karein
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            
            if not ohlcv or len(ohlcv) < 50:
                continue

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # RSI Calculate karein (Period = 14)
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            # Sub se latest closed candle ki RSI
            latest_rsi = df['rsi'].iloc[-1]
            latest_price = df['close'].iloc[-1]

            # Requirement: RSI 45 se 60 ke darmiyan ho
            if 45 <= latest_rsi <= 60:
                print(f"{symbol:<12} | ${latest_price:<11.4f} | {latest_rsi:.2f}")

        except Exception as e:
            # Agar kisi pair par API limit ya error aaye toh ignore karein
            continue

if __name__ == '__main__':
    fetch_and_scan()
  
