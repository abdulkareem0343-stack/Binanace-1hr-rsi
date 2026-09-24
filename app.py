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

# Custom CSS for Mobile Responsive Cards Grid
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #0083B0;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px;
    }
    .crypto-card {
        border: 1px solid #333;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
        background-color: #1E1E1E;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #444;
        padding-bottom: 5px;
        margin-bottom: 8px;
    }
    .symbol-title {
        font-weight: bold;
        font-size: 1.1em;
        color: #FFFFFF;
    }
    .badge-buy { background-color: #28a745; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    .badge-sell { background-color: #dc3545; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    .badge-gap { background-color: #ffc107; color: black; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    .card-body { font-size: 0.85em; color: #BBB; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

st.title("📈 Multi-Exchange EMA Scanner")

# Sidebar Filters
st.sidebar.header("⚙️ Scanner Filters")

EXCHANGES = st.sidebar.multiselect(
    "Select Exchanges",
    ['binance', 'bybit', 'okx', 'kucoin', 'mexc'],
    default=['binance']
)

# Timeframe Selection Added
TIMEFRAME = st.sidebar.selectbox(
    "Select Timeframe",
    ['5m', '15m', '30m', '1h', '4h', '1d'],
    index=0
)

TOP_N_PAIRS = st.sidebar.number_input(
    "Number of Coins per Exchange", 
    min_value=10, 
    max_value=1000, 
    value=50, 
    step=10
)

GAP_THRESHOLD = st.sidebar.number_input("Gap Threshold (%)", value=0.3, step=0.1)

EMA_FAST = 14
EMA_SLOW = 100

@st.cache_resource
def get_exchange_instance(exchange_id):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        return exchange_class({'enableRateLimit': True, 'timeout': 10000})
    except Exception:
        return None

def fetch_top_usdt_pairs(exchange, limit=50):
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
    
    for ex_id in EXCHANGES:
        exchange = get_exchange_instance(ex_id)
        if not exchange:
            continue
            
        status_text.text(f"Fetching top pairs for {ex_id.upper()}...")
        pairs = fetch_top_usdt_pairs(exchange, limit=TOP_N_PAIRS)
        total_pairs = len(pairs)

        for idx, symbol in enumerate(pairs):
            progress_bar.progress(min((idx + 1) / total_pairs, 1.0))
            status_text.text(f"Scanning [{TIMEFRAME}] {ex_id.upper()} ({idx + 1}/{total_pairs}) -> {symbol}")

            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=150)
                if not ohlcv or len(ohlcv) < 100:
                    continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # EMA Calculation
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
                badge_class = ""
                
                if bullish_cross:
                    status = "🚀 Bullish Cross"
                    badge_class = "badge-buy"
                elif bearish_cross:
                    status = "🔻 Bearish Cross"
                    badge_class = "badge-sell"
                elif close_gap:
                    status = f"⚠️ Gap {gap_percent:.2f}%"
                    badge_class = "badge-gap"

                if status:
                    alerts.append({
                        "Exchange": ex_id.upper(),
                        "Symbol": symbol,
                        "Price": last_row['close'],
                        "Signal": status,
                        "Badge": badge_class,
                        "Gap": round(gap_percent, 2),
                        "EMA14": round(ema_fast_curr, 4),
                        "EMA100": round(ema_slow_curr, 4),
                        "Timeframe": TIMEFRAME
                    })

                time.sleep(0.04)
            except Exception:
                continue

    progress_bar.empty()
    status_text.empty()
    return alerts

# Button Press Control (Auto-scan disabled)
start_scan = st.button("🚀 Start Scanning")

if start_scan:
    with st.spinner("Scanning markets... Please wait."):
        results = scan_markets()
        st.session_state['scan_results'] = results

# Displaying Results in 3-Column Mobile Card Layout
if 'scan_results' in st.session_state:
    results = st.session_state['scan_results']
    if results:
        st.success(f"Found {len(results)} signals on {TIMEFRAME} timeframe!")
        
        # 3 Columns per row setup
        cols = st.columns(3)
        for idx, item in enumerate(results):
            col = cols[idx % 3]  # Distribute cards in 3 columns
            with col:
                st.markdown(f"""
                <div class="crypto-card">
                    <div class="card-header">
                        <span class="symbol-title">{item['Symbol']}</span>
                        <span class="{item['Badge']}">{item['Signal']}</span>
                    </div>
                    <div class="card-body">
                        <b>Ex:</b> {item['Exchange']} | <b>TF:</b> {item['Timeframe']}<br>
                        <b>Price:</b> ${item['Price']}<br>
                        <b>Gap:</b> {item['Gap']}%<br>
                        <b>EMA14:</b> {item['EMA14']}<br>
                        <b>EMA100:</b> {item['EMA100']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No signals found in the current scan.")
else:
    st.info("👈 Select options from sidebar and click 'Start Scanning' to run.")
