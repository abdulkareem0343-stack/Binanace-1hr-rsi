import streamlit as st
import ccxt
import pandas as pd
import time

# Page Configuration
st.set_page_config(
    page_title="Crypto EMA Scanner",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Multi-Exchange EMA 14 / 100 Scanner")
st.caption("5-Minute Timeframe Scanner for Crossovers and ≤ 0.3% Gap Thresholds")

# Sidebar Configuration
st.sidebar.header("Scanner Settings")
EXCHANGES = st.sidebar.multiselect(
    "Select Exchanges",
    ['binance', 'bybit', 'okx', 'kucoin', 'mexc'],
    default=['binance', 'bybit', 'okx']
)
TOP_N_PAIRS = st.sidebar.slider("Top Pairs per Exchange", min_value=5, max_value=30, value=10)
GAP_THRESHOLD = st.sidebar.number_input("Gap Threshold (%)", value=0.3, step=0.1)
AUTO_REFRESH = st.sidebar.checkbox("Auto Refresh (Every 30s)", value=True)

EMA_FAST = 14
EMA_SLOW = 100
TIMEFRAME = '5m'

@st.cache_resource
def get_exchange_instance(exchange_id):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        return exchange_class({'enableRateLimit': True, 'timeout': 10000})
    except Exception:
        return None

def fetch_top_usdt_pairs(exchange, limit=10):
    try:
        tickers = exchange.fetch_tickers()
        usdt_pairs = []
        for symbol, ticker in tickers.items():
            if symbol.endswith('/USDT') and 'quoteVolume' in ticker and ticker['quoteVolume']:
                usdt_pairs.append((symbol, ticker['quoteVolume']))
        usdt_pairs.sort(key=lambda x: x[1], reverse=True)
        return [pair[0] for pair in usdt_pairs[:limit]]
    except Exception:
        return []

def scan_markets():
    alerts = []
    
    if not EXCHANGES:
        st.warning("Please select at least one exchange from the sidebar.")
        return alerts

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_steps = len(EXCHANGES) * TOP_N_PAIRS
    current_step = 0

    for ex_id in EXCHANGES:
        exchange = get_exchange_instance(ex_id)
        if not exchange:
            continue
            
        status_text.text(f"Fetching top pairs for {ex_id.upper()}...")
        pairs = fetch_top_usdt_pairs(exchange, limit=TOP_N_PAIRS)

        for symbol in pairs:
            current_step += 1
            progress_bar.progress(min(current_step / total_steps, 1.0))
            status_text.text(f"Scanning {ex_id.upper()} -> {symbol}")

            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=150)
                if not ohlcv or len(ohlcv) < 100:
                    continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Pure Pandas EMA Calculations
                df['ema_fast'] = df['close'].ewm(span=EMA_FAST, adjust=False).mean()
                df['ema_slow'] = df['close'].ewm(span=EMA_SLOW, adjust=False).mean()

                last_row = df.iloc[-1]
                prev_row = df.iloc[-2]

                ema_fast_curr, ema_slow_curr = last_row['ema_fast'], last_row['ema_slow']
                ema_fast_prev, ema_slow_prev = prev_row['ema_fast'], prev_row['ema_slow']

                bullish_cross = (ema_fast_prev <= ema_slow_prev) and (ema_fast_curr > ema_slow_curr)
                bearish_cross = (ema_fast_prev >= ema_slow_prev) and (ema_fast_curr < ema_slow_curr)

                gap_percent = abs(ema_fast_curr - ema_slow_curr) / ema_slow_curr * 100
                close_gap = gap_percent <= GAP_THRESHOLD

                status = None
                if bullish_cross:
                    status = "🚀 Bullish Crossover"
                elif bearish_cross:
                    status = "🔻 Bearish Crossover"
                elif close_gap:
                    status = "⚠️ Gap Alert"

                if status:
                    alerts.append({
                        "Exchange": ex_id.upper(),
                        "Symbol": symbol,
                        "Price": last_row['close'],
                        "Signal": status,
                        "Gap (%)": round(gap_percent, 2),
                        "EMA 14": round(ema_fast_curr, 4),
                        "EMA 100": round(ema_slow_curr, 4)
                    })

                time.sleep(0.1)  # Avoid rate limits
            except Exception:
                continue

    progress_bar.empty()
    status_text.empty()
    return alerts

# Execution
if st.button("Manual Scan Now") or 'initial' not in st.session_state:
    st.session_state['initial'] = True

with st.spinner("Scanning markets... Please wait."):
    results = scan_markets()

if results:
    st.success(f"Found {len(results)} active signals!")
    df_results = pd.DataFrame(results)
    st.dataframe(df_results, use_container_width=True)
else:
    st.info("No crossover or narrow gap detected in current scan cycle.")

if AUTO_REFRESH:
    time.sleep(30)
    st.rerun()
