import datetime
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# App Configuration
st.set_page_config(
    page_title="QQQ VWAP Discipline & Signal Dashboard", layout="wide"
)

st.title("📈 QQQ VWAP Pullback System Dashboard")
st.markdown(
    "*Enforcing a strict 1% risk model, 1:2 risk-to-reward ratio, and VWAP institutional baseline.*"
)

# Sidebar for Account Parameters & Risk Management
st.sidebar.header("1. Risk Parameters")
account_balance = st.sidebar.number_input(
    "Total Account Balance ($)", min_value=100.0, value=10000.0, step=100.0
)
risk_pct = st.sidebar.slider(
    "Risk Percentage per Trade (%)", min_value=0.5, max_value=3.0, value=1.0
)

st.sidebar.header("2. Daily Discipline")
trades_taken_today = st.sidebar.number_input(
    "Trades Taken Today", min_value=0, max_value=5, value=0, step=1
)
consecutive_losses = st.sidebar.number_input(
    "Consecutive Losses Today", min_value=0, max_value=3, value=0, step=1
)

# Hard Rules Enforcer Check
max_trades_allowed = 3
max_losses_allowed = 2

lockout_triggered = False
lockout_reason = ""

if trades_taken_today >= max_trades_allowed:
    lockout_triggered = True
    lockout_reason = (
        "🛑 DAILY CAP REACHED: Maximum of 3 trades completed for today."
    )
elif consecutive_losses >= max_losses_allowed:
    lockout_triggered = True
    lockout_reason = (
        "🛑 CIRCUIT BREAKER TRIGGERED: 2 consecutive losses hit. Walk away."
    )

if lockout_triggered:
    st.error(
        f"### SYSTEM LOCKED OUT\n{lockout_reason}\n*Close your laptop/phone and protect your capital.*"
    )
else:
    st.success(
        "🟢 SYSTEM ACTIVE: Discipline rules validated. Ready to scan market data."
    )

    # Fetching Live QQQ Intraday Data
    @st.cache_data(ttl=300)  # Refresh cache every 5 minutes
    def load_qqq_data():
        ticker = yf.Ticker("QQQ")
        # Fetching 5-minute interval data for the past 5 days
        df = ticker.history(period="5d", interval="5m")
        return df


    data_load_state = st.text("Fetching live QQQ market data...")
    df = load_qqq_data()
    data_load_state.text("Data loaded successfully!")


    # Calculate Intraday VWAP
    def calculate_vwap(dataframe):
        # Reset VWAP each trading day based on date changes
        dataframe["Date"] = dataframe.index.date
        q = dataframe["Close"]
        v = dataframe["Volume"]
        # Cumulative Typical Price * Volume / Cumulative Volume per day
        dataframe["Typical_Price"] = (
            dataframe["High"] + dataframe["Low"] + dataframe["Close"]
        ) / 3
        dataframe["TPV"] = dataframe["Typical_Price"] * dataframe["Volume"]

        dataframe["Cum_TPV"] = dataframe.groupby("Date")["TPV"].cumsum()
        dataframe["Cum_Vol"] = dataframe.groupby("Date")["Volume"].cumsum()
        dataframe["VWAP"] = dataframe["Cum_TPV"] / dataframe["Cum_Vol"]
        return dataframe


    df = calculate_vwap(df)

    # Get the latest candle data
    latest_row = df.iloc[-1]
    current_price = latest_row["Close"]
    current_vwap = latest_row["VWAP"]
    prev_price = df.iloc[-2]["Close"]
    prev_vwap = df.iloc[-2]["VWAP"]

    # Display Current Market Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("QQQ Current Price", f"${current_price:.2f}")
    col2.metric("Intraday VWAP", f"${current_vwap:.2f}")

    # Strategy Evaluation Logic (VWAP Trend Pullback)
    # Rule: Price was below or near VWAP and crosses back above, or bounces off VWAP cleanly
    price_to_vwap_diff_pct = ((current_price - current_vwap) / current_vwap) * 100

    st.markdown("---")
    st.subheader("📊 Strategy Signal Analysis")

    # Interactive Checklist Validation
    st.markdown("### Manual Confluence Checklist:")
    c1 = st.checkbox(
        "1. Trend Alignment: Is QQQ making higher lows on the broader intraday chart?"
    )
    c2 = st.checkbox(
        "2. Pullback Confirmation: Did price cleanly test or dip near the VWAP line?"
    )
    c3 = st.checkbox(
        "3. Risk Parameter Set: Am I risking exactly 1% of my total account balance?"
    )

    # Signal Assessment
    signal_is_green = False
    if current_price > current_vwap and price_to_vwap_diff_pct < 0.4:
        st.info(
            "ℹ️ Market State: Price is sitting right at or slightly above the institutional VWAP line."
        )
        if c1 and c2 and c3:
            signal_is_green = True
    else:
        st.warning(
            "⚠️ Market State: Price is extended too far away from VWAP or trading below it. No setup triggered."
        )

    st.markdown("---")
    if signal_is_green:
        st.markdown(
            "# 🟢 GREEN LIGHT SIGNAL DETECTED: EXECUTE LONG POSITION"
        )

        # Risk Math Calculations
        dollar_risk_amount = account_balance * (risk_pct / 100.0)
        # Assume a tight technical stop-loss distance of 0.5% below current price
        stop_loss_price = current_price * 0.995
        risk_per_share = current_price - stop_loss_price

        # Position Sizing
        shares_to_buy = int(dollar_risk_amount / risk_per_share)
        take_profit_price = current_price + (
            risk_per_share * 2.0
        )  # 1:2 Reward Ratio

        st.markdown("### 📋 Trade Execution Plan:")
        st.markdown(f"* **Asset:** QQQ (ETF)")
        st.markdown(f"* **Action:** BUY (LONG)")
        st.markdown(f"* **Suggested Entry Price:** ~${current_price:.2f}")
        st.markdown(
            f"* **Stop Loss (Risking {risk_pct}%):** ${stop_loss_price:.2f}"
        )
        st.markdown(
            f"* **Take Profit Target (1:2 Ratio):** ${take_profit_price:.2f}"
        )
        st.markdown(
            f"* **Position Size:** **{shares_to_buy} shares** (Total Capital risked: ${dollar_risk_amount:.2f})"
        )
    else:
        st.markdown("# 🔴 RED LIGHT / STANDBY")
        st.markdown(
            "Conditions are not fully met. Do not open a trade. Wait for a textbook VWAP pullback setup and check all boxes."
        )

    # Display Recent Chart Data Table for review
    with st.expander("View Recent 5-Minute QQQ Data & VWAP Table"):
        st.dataframe(
            df[["Close", "Volume", "VWAP"]].tail(10), use_container_width=True
        )
