"""
Automated Trading System Using Bollinger Bands
With Angel One SmartAPI Integration + n8n Workflow Support

Paper: Automated Trading System Using Bollinger Bands and n8n Workflow Automation
Authors: Prajwal Chidrewar, Vedant Ghare, Pandurang Melgave,
         Madhumita Khanvilkar, Vishakha Ovhal, Jitendra Musale
Institution: Department of AI and Data Science,
             Anantrao Pawar College of Engineering, Pune

HOW TO RUN:
  1. pip install smartapi-python pyotp yfinance pandas numpy
  2. Fill in config.py with your Angel One credentials
  3. python bollinger_trading_system_angelone.py
  4. OR let n8n Execute Command Node run it automatically
"""

import pandas as pd
import numpy as np
import yfinance as yf
import pyotp
import json
import sys
import time
from datetime import datetime

# ── Try importing Angel One SDK ───────────────
try:
    from SmartApi import SmartConnect
    ANGEL_ONE_AVAILABLE = True
except ImportError:
    ANGEL_ONE_AVAILABLE = False
    print("[WARNING] SmartApi not installed. Running in simulation mode.")
    print("[WARNING] Run: pip install smartapi-python")

# ── Try importing credentials ─────────────────
try:
    from config import API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET
    CREDENTIALS_AVAILABLE = True
except ImportError:
    CREDENTIALS_AVAILABLE = False
    API_KEY      = ""
    CLIENT_ID    = ""
    PASSWORD     = ""
    TOTP_SECRET  = ""
    print("[WARNING] config.py not found. Running in simulation mode.")


# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
SYMBOL           = "IDBI.NS"    # Yahoo Finance symbol (for price data)
ANGEL_SYMBOL     = "IDBI-EQ"    # Angel One symbol
ANGEL_TOKEN      = "1301"       # Angel One token for IDBI Bank NSE
EXCHANGE         = "NSE"        # Exchange

PERIOD           = "5d"         # 5 trading days of data
INTERVAL         = "30m"        # 30-minute timeframe
SMA_PERIOD       = 20           # Lookback period (n = 20)
STD_MULT         = 2            # Standard deviation multiplier (k = 2)
STOP_LOSS_PCT    = 0.02         # 2% stop-loss from entry price

# ── Capital and Position Sizing ───────────────
INITIAL_CAPITAL  = 10000.00     # Starting virtual money in Rs
RISK_PER_TRADE   = 0.10         # Use 10% of current balance per trade

# ── Mode ──────────────────────────────────────
# DEMO  = simulate trades, no real orders placed (safe for testing)
# LIVE  = place real orders via Angel One API
MODE = "LIVE"                   # Change to "LIVE" only when fully ready


# ─────────────────────────────────────────────
# STEP 1 — ANGEL ONE LOGIN
# ─────────────────────────────────────────────
def login_angel_one():
    """
    Login to Angel One SmartAPI using credentials from config.py.
    Uses TOTP (Time-based One Time Password) for 2FA authentication.
    Returns the SmartConnect object if successful, None if failed.
    """
    if not ANGEL_ONE_AVAILABLE or not CREDENTIALS_AVAILABLE:
        print("[DEMO MODE] Skipping Angel One login.")
        return None

    print(f"[{datetime.now()}] Logging into Angel One...")
    try:
        obj  = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()   # Generate 6-digit TOTP code

        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)

        if data['status']:
            print(f"[{datetime.now()}] Login successful. Client: {CLIENT_ID}")
            return obj
        else:
            print(f"[{datetime.now()}] Login failed: {data['message']}")
            return None

    except Exception as e:
        print(f"[{datetime.now()}] Login error: {e}")
        return None


# ─────────────────────────────────────────────
# STEP 2 — FETCH MARKET DATA
# ─────────────────────────────────────────────
def fetch_data(symbol, period, interval):
    """
    Fetch historical OHLCV data from Yahoo Finance.
    Retries up to 3 times with exponential backoff.
    """
    print(f"[{datetime.now()}] Fetching market data for {symbol}...")

    for attempt in range(3):
        try:
            ticker = yf.Ticker(symbol)
            df     = ticker.history(period=period, interval=interval)

            if df.empty:
                raise ValueError("No data returned.")

            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df.index = pd.to_datetime(df.index)
            print(f"[{datetime.now()}] Data fetched. Rows: {len(df)}")
            return df

        except Exception as e:
            wait = 2 ** attempt
            print(f"[{datetime.now()}] Attempt {attempt+1} failed: {e}. Retry in {wait}s...")
            time.sleep(wait)

    print("[ERROR] Could not fetch data after 3 attempts.")
    sys.exit(1)


# ─────────────────────────────────────────────
# STEP 3 — PREPROCESSING
# ─────────────────────────────────────────────
def preprocess_data(df):
    """
    Clean, remove duplicates, sort by time.
    """
    print(f"[{datetime.now()}] Preprocessing data...")
    df = df.dropna()
    df = df[~df.index.duplicated(keep='first')]
    df = df.sort_index()
    print(f"[{datetime.now()}] Preprocessing done. Clean rows: {len(df)}")
    return df


# ─────────────────────────────────────────────
# STEP 4 — BOLLINGER BAND CALCULATION
# ─────────────────────────────────────────────
def calculate_bollinger_bands(df, period=SMA_PERIOD, multiplier=STD_MULT):
    """
    SMAₜ = (1/n) Σ Pₜ₋ᵢ                  -- Equation (1)
    σₜ   = sqrt[(1/n) Σ (Pₜ₋ᵢ - SMAₜ)²]  -- Equation (2)
    UBₜ  = SMAₜ + k*σₜ                    -- Equation (3)
    LBₜ  = SMAₜ - k*σₜ                    -- Equation (4)
    """
    print(f"[{datetime.now()}] Calculating Bollinger Bands...")
    df['SMA']       = df['Close'].rolling(window=period).mean()
    df['STD']       = df['Close'].rolling(window=period).std()
    df['UpperBand'] = df['SMA'] + (multiplier * df['STD'])
    df['LowerBand'] = df['SMA'] - (multiplier * df['STD'])
    df = df.dropna(subset=['SMA', 'UpperBand', 'LowerBand'])
    print(f"[{datetime.now()}] Bands calculated. Rows: {len(df)}")
    return df


# ─────────────────────────────────────────────
# STEP 5 — SIGNAL GENERATION
# ─────────────────────────────────────────────
def generate_signals(df):
    """
    Buy Signal:  Pₜ < LBₜ AND Pₜ₋₁ >= LBₜ₋₁   -- Equation (5)
    Sell Signal: Pₜ > UBₜ AND Pₜ₋₁ <= UBₜ₋₁   -- Equation (6)
    """
    print(f"[{datetime.now()}] Generating signals...")
    df['Signal'] = 'No-Action'

    for i in range(1, len(df)):
        curr_price = df['Close'].iloc[i]
        prev_price = df['Close'].iloc[i - 1]
        curr_lb    = df['LowerBand'].iloc[i]
        prev_lb    = df['LowerBand'].iloc[i - 1]
        curr_ub    = df['UpperBand'].iloc[i]
        prev_ub    = df['UpperBand'].iloc[i - 1]

        if curr_price < curr_lb and prev_price >= prev_lb:
            df.iloc[i, df.columns.get_loc('Signal')] = 'Buy'
        elif curr_price > curr_ub and prev_price <= prev_ub:
            df.iloc[i, df.columns.get_loc('Signal')] = 'Sell'

    buys  = (df['Signal'] == 'Buy').sum()
    sells = (df['Signal'] == 'Sell').sum()
    print(f"[{datetime.now()}] Signals — Buy: {buys}, Sell: {sells}")
    return df


# ─────────────────────────────────────────────
# STEP 6 — PLACE ORDER VIA ANGEL ONE
# ─────────────────────────────────────────────
def place_order(angel_obj, signal, quantity):
    """
    Place a real order via Angel One SmartAPI.
    Only called when MODE = "LIVE" and angel_obj is available.

    Parameters:
        angel_obj : SmartConnect object (logged in)
        signal    : "Buy" or "Sell"
        quantity  : Number of shares to trade
    """
    if MODE == "DEMO" or angel_obj is None:
        print(f"  [DEMO] Would place {signal} order for {quantity} shares of {ANGEL_SYMBOL}")
        return {"status": True, "demo": True, "orderid": "DEMO_ORDER"}

    try:
        transaction = "BUY" if signal == "Buy" else "SELL"

        order_params = {
            "variety"          : "NORMAL",
            "tradingsymbol"    : ANGEL_SYMBOL,
            "symboltoken"      : ANGEL_TOKEN,
            "transactiontype"  : transaction,
            "exchange"         : EXCHANGE,
            "ordertype"        : "MARKET",        # Market order - executes immediately
            "producttype"      : "INTRADAY",       # Intraday trade (closed same day)
            "duration"         : "DAY",
            "quantity"         : str(quantity)
        }

        response = angel_obj.placeOrder(order_params)
        print(f"  [ORDER PLACED] {transaction} {quantity} shares | Order ID: {response}")
        return response

    except Exception as e:
        print(f"  [ORDER FAILED] {e}")
        return {"status": False, "error": str(e)}


# ─────────────────────────────────────────────
# STEP 7 — EXIT STRATEGY, RISK MANAGEMENT
#           AND CAPITAL TRACKING
# ─────────────────────────────────────────────
def apply_exit_strategy(df, angel_obj, stop_loss_pct=STOP_LOSS_PCT):
    """
    Mean-Reversion Exit:
      Long:  Pₜ >= SMAₜ              -- Equation (7)
      Short: Pₜ <= SMAₜ              -- Equation (8)

    Stop-Loss:
      Long:  Entry Price x 0.98      -- Equation (9)
      Short: Entry Price x 1.02      -- Equation (10)

    Capital Tracking:
      trade_amount = balance x RISK_PER_TRADE
      quantity     = int(trade_amount / entry_price)
      profit_rs    = price_diff x quantity
      balance      = balance + profit_rs
    """
    print(f"[{datetime.now()}] Running trade execution ({MODE} MODE)...")
    print(f"[{datetime.now()}] Starting capital : Rs {INITIAL_CAPITAL:.2f}")
    print(f"[{datetime.now()}] Risk per trade   : {int(RISK_PER_TRADE*100)}%")

    trades      = []
    position    = None
    entry_price = None
    entry_time  = None
    quantity    = 0
    balance     = INITIAL_CAPITAL
    order_id    = None

    for i in range(len(df)):
        row           = df.iloc[i]
        current_price = row['Close']
        current_sma   = row['SMA']
        current_time  = df.index[i]
        signal        = row['Signal']

        # ── Check exit conditions ─────────────────
        if position == 'Long':
            stop_loss_price = entry_price * (1 - stop_loss_pct)
            exit_reason     = None
            exit_price      = None

            if current_price >= current_sma:           # Equation (7)
                exit_reason = 'Mean-Reversion'
                exit_price  = current_price
            elif current_price <= stop_loss_price:     # Equation (9)
                exit_reason = 'Stop-Loss'
                exit_price  = current_price

            if exit_reason:
                # Place exit order (Sell to close Long)
                place_order(angel_obj, "Sell", quantity)

                price_diff  = round(exit_price - entry_price, 2)
                profit_rs   = round(price_diff * quantity, 2)
                balance     = round(balance + profit_rs, 2)

                trades.append({
                    'TradeNo'       : len(trades) + 1,
                    'Signal'        : 'Buy',
                    'EntryPrice'    : round(entry_price, 2),
                    'ExitPrice'     : round(exit_price, 2),
                    'Quantity'      : quantity,
                    'PriceDiff'     : price_diff,
                    'ProfitLoss_Rs' : profit_rs,
                    'BalanceAfter'  : balance,
                    'EntryTime'     : str(entry_time),
                    'ExitTime'      : str(current_time),
                    'ExitReason'    : exit_reason,
                    'Mode'          : MODE
                })
                print(f"  [EXIT]  {exit_reason} | Price: Rs {exit_price:.2f} | "
                      f"P&L: Rs {profit_rs:+.2f} | Balance: Rs {balance:.2f}")
                position = None

        elif position == 'Short':
            stop_loss_price = entry_price * (1 + stop_loss_pct)
            exit_reason     = None
            exit_price      = None

            if current_price <= current_sma:           # Equation (8)
                exit_reason = 'Mean-Reversion'
                exit_price  = current_price
            elif current_price >= stop_loss_price:     # Equation (10)
                exit_reason = 'Stop-Loss'
                exit_price  = current_price

            if exit_reason:
                # Place exit order (Buy to close Short)
                place_order(angel_obj, "Buy", quantity)

                price_diff  = round(entry_price - exit_price, 2)
                profit_rs   = round(price_diff * quantity, 2)
                balance     = round(balance + profit_rs, 2)

                trades.append({
                    'TradeNo'       : len(trades) + 1,
                    'Signal'        : 'Sell',
                    'EntryPrice'    : round(entry_price, 2),
                    'ExitPrice'     : round(exit_price, 2),
                    'Quantity'      : quantity,
                    'PriceDiff'     : price_diff,
                    'ProfitLoss_Rs' : profit_rs,
                    'BalanceAfter'  : balance,
                    'EntryTime'     : str(entry_time),
                    'ExitTime'      : str(current_time),
                    'ExitReason'    : exit_reason,
                    'Mode'          : MODE
                })
                print(f"  [EXIT]  {exit_reason} | Price: Rs {exit_price:.2f} | "
                      f"P&L: Rs {profit_rs:+.2f} | Balance: Rs {balance:.2f}")
                position = None

        # ── Enter new position ────────────────────
        if position is None and signal in ('Buy', 'Sell'):
            trade_amount = balance * RISK_PER_TRADE
            quantity     = int(trade_amount / current_price)

            if quantity > 0:
                # Place entry order via Angel One
                order_response = place_order(angel_obj, signal, quantity)
                order_id       = order_response.get('orderid', 'N/A')

                position    = 'Long' if signal == 'Buy' else 'Short'
                entry_price = current_price
                entry_time  = current_time

                print(f"  [ENTRY] {signal} | Price: Rs {current_price:.2f} | "
                      f"Qty: {quantity} | Amount: Rs {trade_amount:.2f} | "
                      f"Order ID: {order_id}")

    print(f"[{datetime.now()}] Execution complete. Total trades: {len(trades)}")
    return trades, balance


# ─────────────────────────────────────────────
# STEP 8 — PERFORMANCE SUMMARY
# ─────────────────────────────────────────────
def calculate_performance(trades, final_balance):
    """
    Print full performance report with capital tracking.
    """
    if not trades:
        print("No trades executed.")
        return {}

    total_trades  = len(trades)
    winning       = [t for t in trades if t['ProfitLoss_Rs'] > 0]
    losing        = [t for t in trades if t['ProfitLoss_Rs'] <= 0]
    total_profit  = round(sum(t['ProfitLoss_Rs'] for t in trades), 2)
    win_rate      = round((len(winning) / total_trades) * 100, 1)
    avg_win       = round(np.mean([t['ProfitLoss_Rs'] for t in winning]), 2) if winning else 0
    avg_loss      = round(abs(np.mean([t['ProfitLoss_Rs'] for t in losing])), 2) if losing else 0
    profit_factor = round(avg_win / avg_loss, 2) if avg_loss > 0 else float('inf')
    total_return  = round(((final_balance - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100, 2)

    print("\n" + "="*70)
    print("              TRADING PERFORMANCE SUMMARY")
    print("="*70)
    print(f"  Mode                : {MODE}")
    print(f"  Symbol              : {SYMBOL}")
    print(f"  Initial Capital     : Rs {INITIAL_CAPITAL:.2f}")
    print(f"  Final Balance       : Rs {final_balance:.2f}")
    print(f"  Total Profit/Loss   : Rs {total_profit:.2f}")
    print(f"  Total Return        : {total_return}%")
    print(f"  Total Trades        : {total_trades}")
    print(f"  Winning Trades      : {len(winning)}")
    print(f"  Losing Trades       : {len(losing)}")
    print(f"  Win Rate            : {win_rate}%")
    print(f"  Avg Win             : Rs {avg_win:.2f}")
    print(f"  Avg Loss            : Rs {avg_loss:.2f}")
    print(f"  Profit Factor       : {profit_factor}")
    print("="*70)

    print(f"\n  {'No':<4} {'Sig':<5} {'Entry':>8} {'Exit':>8} {'Qty':>5} "
          f"{'P&L(Rs)':>10} {'Balance':>10} {'Reason'}")
    print("  " + "-"*65)
    for t in trades:
        print(f"  {t['TradeNo']:<4} {t['Signal']:<5} {t['EntryPrice']:>8.2f} "
              f"{t['ExitPrice']:>8.2f} {t['Quantity']:>5} "
              f"{t['ProfitLoss_Rs']:>+10.2f} {t['BalanceAfter']:>10.2f}  {t['ExitReason']}")
    print("="*70)

    return {
        'initial_capital'  : INITIAL_CAPITAL,
        'final_balance'    : final_balance,
        'total_profit'     : total_profit,
        'total_return_pct' : total_return,
        'total_trades'     : total_trades,
        'win_rate'         : win_rate,
        'profit_factor'    : profit_factor
    }


# ─────────────────────────────────────────────
# STEP 9 — OUTPUT JSON FOR n8n
# ─────────────────────────────────────────────
def prepare_output_for_n8n(trades, df, final_balance):
    """
    Print JSON output that n8n Execute Command Node captures.
    n8n then routes this to:
      - Google Sheets Node  → logs every trade
      - Email/Telegram Node → sends alert on Buy/Sell signal
    """
    latest_signal = df[df['Signal'] != 'No-Action'].tail(1)
    current_price = round(df['Close'].iloc[-1], 2)

    # Calculate quantity for the latest signal
    trade_amount   = final_balance * RISK_PER_TRADE
    latest_qty     = int(trade_amount / current_price) if current_price > 0 else 0

    output = {
        'timestamp'        : str(datetime.now()),
        'mode'             : MODE,
        'symbol'           : SYMBOL,
        'angel_symbol'     : ANGEL_SYMBOL,
        'initial_capital'  : INITIAL_CAPITAL,
        'final_balance'    : final_balance,
        'latest_close'     : current_price,
        'latest_sma'       : round(df['SMA'].iloc[-1], 2),
        'upper_band'       : round(df['UpperBand'].iloc[-1], 2),
        'lower_band'       : round(df['LowerBand'].iloc[-1], 2),
        'signal'           : latest_signal['Signal'].values[0] if not latest_signal.empty else 'No-Action',
        'suggested_qty'    : latest_qty,
        'trade_amount_rs'  : round(trade_amount, 2),
        'total_trades'     : len(trades),
        'trade_log'        : trades
    }

    # n8n reads everything between these markers
    print("\n[N8N_OUTPUT_START]")
    print(json.dumps(output, indent=2))
    print("[N8N_OUTPUT_END]")

    return output


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────
def main():
    print("\n" + "="*70)
    print("       BOLLINGER BANDS AUTOMATED TRADING SYSTEM")
    print(f"       Mode: {MODE} | Symbol: {SYMBOL}")
    print("="*70 + "\n")

    # Step 1: Login to Angel One
    angel_obj = login_angel_one()

    # Step 2: Fetch market data
    df = fetch_data(SYMBOL, PERIOD, INTERVAL)

    # Step 3: Preprocess
    df = preprocess_data(df)

    # Step 4: Calculate Bollinger Bands
    df = calculate_bollinger_bands(df)

    # Step 5: Generate signals
    df = generate_signals(df)

    # Step 6: Execute trades (DEMO or LIVE)
    trades, balance = apply_exit_strategy(df, angel_obj)

    # Step 7: Performance summary
    calculate_performance(trades, balance)

    # Step 8: Output JSON for n8n → Google Sheets
    prepare_output_for_n8n(trades, df, balance)


if __name__ == "__main__":
    main()