import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Configure Mobile-Friendly Page View
st.set_page_config(
    page_title="Mobile Stock Tracker", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# Inject custom CSS to look like a native Android App
st.markdown("""
    <style>
    .reportview-container .main .block-container { max-width: 100%; padding: 1rem; }
    div[data-testid="stMetricValue"] { font-size: 2rem; font-weight: bold; color: #26a69a; }
    h1, h2, h3 { margin-bottom: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# 2. Main Title and Dynamic Input for ANY NYSE Ticker
st.title("📊 Mobile Stock Dashboard")
ticker_input = st.text_input("Enter NYSE Ticker Symbol:", value="AAPL").upper().strip()

if ticker_input:
    try:
        # 3. Background Real-Time Price Fetch
        ticker_data = yf.Ticker(ticker_input)
        
        # Get live price data using history to avoid fast_info cloud server bugs
        todays_data = ticker_data.history(period="1d", interval="30m")
        if not todays_data.empty:
            current_price = float(todays_data['Close'].iloc[-1])
            open_price = float(todays_data['Open'].iloc[0])
            price_change = current_price - open_price
            st.metric(
                label=f"Current Price ({ticker_input}) — Updates Every 30m", 
                value=f"${current_price:.2f}", 
                delta=f"${price_change:.2f}"
            )
        else:
            # Fallback historical data fetch if market is fully closed
            fallback_data = ticker_data.history(period="1d")
            current_price = float(fallback_data['Close'].iloc[-1])
            st.metric(label=f"Last Close ({ticker_input})", value=f"${current_price:.2f}")

        # 4. Fetch Historical Daily Data for MAs & RSI
        hist_df = ticker_data.history(period="2y", interval="1d")
        
        if len(hist_df) >= 200:
            # Calculate technical parameters using explicit rolling calculations
            hist_df['MA20'] = hist_df['Close'].rolling(window=20).mean()
            hist_df['MA50'] = hist_df['Close'].rolling(window=50).mean()
            hist_df['MA200'] = hist_df['Close'].rolling(window=200).mean()
            
            # Pure mathematical RSI Calculation
            delta = hist_df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            hist_df['RSI'] = 100 - (100 / (1 + rs))
            
            # Filter layout to show the most recent 90 days for mobile visibility
            plot_df = hist_df.tail(90)
            
            # Determine colors for Candlesticks & Volume Bars
            bar_colors = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in plot_df.iterrows()]

            # 5. Build the Triple-Stacked Visual Layout (Sharing X-Axis)
            fig = make_subplots(
                rows=3, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.05, 
                row_heights=[0.5, 0.15, 0.35]
            )

            # --- Panel A: Candlestick + MA Overlay ---
            fig.add_trace(go.Candlestick(
                x=plot_df.index, open=plot_df['Open'], high=plot_df['High'],
                low=plot_df['Low'], close=plot_df['Close'], name="Price",
                increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA20'], name='MA 20', line=dict(color='orange', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA50'], name='MA 50', line=dict(color='blue', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MA200'], name='MA 200', line=dict(color='magenta', width=1.5)), row=1, col=1)

            # --- Panel B: Daily Volume Bars ---
            fig.add_trace(go.Bar(
                x=plot_df.index, y=plot_df['Volume'], name="Volume",
                marker_color=bar_colors, opacity=0.8
            ), row=2, col=1)

            # --- Panel C: RSI (14) Momentum Line ---
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI'], name='RSI(14)', line=dict(color='purple', width=1.5)), row=3, col=1)
            
            # Add static thresholds
            fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", row=3, col=1, opacity=0.5)
            fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", row=3, col=1, opacity=0.5)

            # 6. Optimize UI Controls for Touchscreens
            fig.update_layout(
                height=650,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_rangeslider_visible=False,
                template="plotly_dark"
            )
            
            fig.update_yaxes(title_text="Price ($)", row=1, col=1)
            fig.update_yaxes(title_text="Vol", row=2, col=1, showticklabels=False)
            fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100])

            # Render the chart
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Not enough historical data available for this asset symbol.")
    except Exception as e:
        st.error(f"Ticker symbol not recognized or API issue. Error Details: {e}")
