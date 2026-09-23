import streamlit as st
import ccxt
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Binance RSI Scanner", layout="wide")
st.title("📊 Binance 1-Hour RSI Scanner (45 - 60)")

# Custom RSI Function (No pandas_ta required)
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=300)  # 5 minute tak cache rakhega taake fast load ho
def scan_markets():
    exchange = ccxt.binance({'enableRateLimit': True})
    markets = exchange.load_markets()
    
    # Top 50 USDT Pairs (Scanning fast karne ke liye limit ki hai)
    usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT') and markets[symbol]['spot']][:50]
    
    results = []
    
    progress_bar = st.progress(0)
    for idx, symbol in enumerate(usdt_pairs):
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
            if ohlcv and len(ohlcv) >= 20:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df = calculate_rsi(df)
                
                latest_rsi = df['rsi'].iloc[-1]
                latest_price = df['close'].iloc[-1]

                if 45 <= latest_rsi <= 60:
                    results.append({
                        'Coin': symbol,
                        'Price ($)': round(latest_price, 4),
                        'RSI (1H)': round(latest_rsi, 2)
                    })
        except Exception:
            continue
            
        progress_bar.progress((idx + 1) / len(usdt_pairs))
        
    return pd.DataFrame(results)

if st.button('🚀 Start Scan'):
    with st.spinner('Binance Data Scan ho raha hai...'):
        df_results = scan_markets()
        
        if not df_results.empty:
            st.success(f"{len(df_results)} Coins milay hain!")
            st.dataframe(df_results, use_container_width=True)
        else:
            st.warning("Koi coin 45-60 RSI range me nahi mila.")
else:
    st.info("Scan shuru karne ke liye 'Start Scan' button par click karein.")
