import streamlit as st
import ccxt
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Binance RSI Scanner", layout="wide")
st.title("📊 Binance 1-Hour RSI Scanner (45 - 60)")

# Custom RSI Function
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=300)
def scan_markets():
    # Streamlit Cloud IP restriction fix
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'urls': {
            'api': {
                'public': 'https://api1.binance.com/api/v3',
            }
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
    })
    
    try:
        markets = exchange.load_markets()
    except Exception as e:
        st.error(f"Binance connection failed: {e}")
        return pd.DataFrame()
    
    # Top 40 USDT Pairs scan karein
    usdt_pairs = [symbol for symbol in markets if symbol.endswith('/USDT') and markets[symbol]['spot']][:40]
    
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
    with st.spinner('Fetching data from Binance...'):
        df_results = scan_markets()
        
        if not df_results.empty:
            st.success(f"{len(df_results)} Coins found in 45-60 RSI range!")
            st.dataframe(df_results, use_container_width=True)
        else:
            st.warning("No coins found matching the RSI range right now.")
else:
    st.info("Click 'Start Scan' to begin scanning.")
