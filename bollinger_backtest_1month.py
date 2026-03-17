"""
Bollinger Bands Backtesting Script
Paper: Automated Trading System Using Bollinger Bands and n8n Workflow Automation
Authors: Prajwal Chidrewar et al.
Institution: Anantrao Pawar College of Engineering, Pune
"""

import pandas as pd
import numpy as np
import yfinance as yf
import json
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
SYMBOL           = "IDBI.NS"
PERIOD           = "1mo"          # Change to "1y" for 1 year
INTERVAL         = "30m"          # Change to "1d" for 1 year
SMA_PERIOD       = 20
STD_MULT         = 2
STOP_LOSS_PCT    = 0.02
INITIAL_CAPITAL  = 10000.00
RISK_PER_TRADE   = 0.10


# ─────────────────────────────────────────────
# FETCH DATA
# ─────────────────────────────────────────────
def fetch_data():
    print(f"\n{'='*60}")
    print(f"  BOLLINGER BANDS BACKTESTING REPORT")
    print(f"  Symbol: {SYMBOL} | Period: {PERIOD} | Interval: {INTERVAL}")
    print(f"{'='*60}\n")
    print(f"Fetching historical data for {SYMBOL}...")

    ticker = yf.Ticker(SYMBOL)
    df     = ticker.history(period=PERIOD, interval=INTERVAL)
    df     = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    df     = df.dropna()
    df     = df[~df.index.duplicated(keep='first')]
    df     = df.sort_index()

    print(f"Data fetched. Total candles: {len(df)}")
    print(f"From: {df.index[0].strftime('%Y-%m-%d %H:%M')}")
    print(f"To  : {df.index[-1].strftime('%Y-%m-%d %H:%M')}\n")
    return df


# ─────────────────────────────────────────────
# CALCULATE BOLLINGER BANDS
# ─────────────────────────────────────────────
def calculate_bollinger_bands(df):
    df['SMA']       = df['Close'].rolling(window=SMA_PERIOD).mean()
    df['STD']       = df['Close'].rolling(window=SMA_PERIOD).std()
    df['UpperBand'] = df['SMA'] + (STD_MULT * df['STD'])
    df['LowerBand'] = df['SMA'] - (STD_MULT * df['STD'])
    df = df.dropna(subset=['SMA', 'UpperBand', 'LowerBand'])
    return df


# ─────────────────────────────────────────────
# GENERATE SIGNALS
# ─────────────────────────────────────────────
def generate_signals(df):
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
    return df


# ─────────────────────────────────────────────
# RUN BACKTEST
# ─────────────────────────────────────────────
def run_backtest(df):
    trades       = []
    position     = None
    entry_price  = None
    entry_time   = None
    entry_sma    = None
    entry_ub     = None
    entry_lb     = None
    quantity     = 0
    balance      = INITIAL_CAPITAL
    peak_balance = INITIAL_CAPITAL
    max_drawdown = 0

    for i in range(len(df)):
        row           = df.iloc[i]
        current_price = row['Close']
        current_sma   = row['SMA']
        current_ub    = row['UpperBand']
        current_lb    = row['LowerBand']
        current_time  = df.index[i]
        signal        = row['Signal']

        # Track drawdown
        if balance > peak_balance:
            peak_balance = balance
        drawdown = ((peak_balance - balance) / peak_balance) * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        # Exit conditions
        if position == 'Long':
            stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
            exit_reason = None
            exit_price  = None

            if current_price >= current_sma:
                exit_reason = 'Mean-Reversion'
                exit_price  = current_price
            elif current_price <= stop_loss_price:
                exit_reason = 'Stop-Loss'
                exit_price  = current_price

            if exit_reason:
                price_diff = round(exit_price - entry_price, 2)
                profit_rs  = round(price_diff * quantity, 2)
                balance    = round(balance + profit_rs, 2)

                trades.append({
                    'TradeNo'       : len(trades) + 1,
                    'Timestamp'     : str(entry_time)[:16],
                    'ExitTime'      : str(current_time)[:16],
                    'Signal'        : 'Buy',
                    'EntryPrice'    : round(entry_price, 2),
                    'ExitPrice'     : round(exit_price, 2),
                    'SMA'           : round(entry_sma, 2),
                    'UpperBand'     : round(entry_ub, 2),
                    'LowerBand'     : round(entry_lb, 2),
                    'Quantity'      : quantity,
                    'TradeAmount'   : round(entry_price * quantity, 2),
                    'PriceDiff'     : price_diff,
                    'ProfitLoss_Rs' : profit_rs,
                    'BalanceAfter'  : balance,
                    'ExitReason'    : exit_reason,
                    'Result'        : 'WIN' if profit_rs > 0 else 'LOSS',
                    'Mode'          : 'DEMO'
                })
                position = None

        elif position == 'Short':
            stop_loss_price = entry_price * (1 + STOP_LOSS_PCT)
            exit_reason = None
            exit_price  = None

            if current_price <= current_sma:
                exit_reason = 'Mean-Reversion'
                exit_price  = current_price
            elif current_price >= stop_loss_price:
                exit_reason = 'Stop-Loss'
                exit_price  = current_price

            if exit_reason:
                price_diff = round(entry_price - exit_price, 2)
                profit_rs  = round(price_diff * quantity, 2)
                balance    = round(balance + profit_rs, 2)

                trades.append({
                    'TradeNo'       : len(trades) + 1,
                    'Timestamp'     : str(entry_time)[:16],
                    'ExitTime'      : str(current_time)[:16],
                    'Signal'        : 'Sell',
                    'EntryPrice'    : round(entry_price, 2),
                    'ExitPrice'     : round(exit_price, 2),
                    'SMA'           : round(entry_sma, 2),
                    'UpperBand'     : round(entry_ub, 2),
                    'LowerBand'     : round(entry_lb, 2),
                    'Quantity'      : quantity,
                    'TradeAmount'   : round(entry_price * quantity, 2),
                    'PriceDiff'     : price_diff,
                    'ProfitLoss_Rs' : profit_rs,
                    'BalanceAfter'  : balance,
                    'ExitReason'    : exit_reason,
                    'Result'        : 'WIN' if profit_rs > 0 else 'LOSS',
                    'Mode'          : 'DEMO'
                })
                position = None

        # Enter new position
        if position is None and signal in ('Buy', 'Sell'):
            trade_amount = balance * RISK_PER_TRADE
            quantity     = int(trade_amount / current_price)
            if quantity > 0:
                position    = 'Long' if signal == 'Buy' else 'Short'
                entry_price = current_price
                entry_time  = current_time
                entry_sma   = current_sma
                entry_ub    = current_ub
                entry_lb    = current_lb

    return trades, balance, max_drawdown


# ─────────────────────────────────────────────
# PRINT REPORT
# ─────────────────────────────────────────────
def print_report(trades, final_balance, max_drawdown):
    if not trades:
        print("No trades executed.")
        return

    total_trades  = len(trades)
    winning       = [t for t in trades if t['ProfitLoss_Rs'] > 0]
    losing        = [t for t in trades if t['ProfitLoss_Rs'] <= 0]
    total_profit  = round(sum(t['ProfitLoss_Rs'] for t in trades), 2)
    win_rate      = round((len(winning) / total_trades) * 100, 1)
    avg_win       = round(np.mean([t['ProfitLoss_Rs'] for t in winning]), 2) if winning else 0
    avg_loss      = round(abs(np.mean([t['ProfitLoss_Rs'] for t in losing])), 2) if losing else 0
    profit_factor = round(avg_win / avg_loss, 2) if avg_loss > 0 else float('inf')
    total_return  = round(((final_balance - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100, 2)
    best_trade    = max(trades, key=lambda x: x['ProfitLoss_Rs'])
    worst_trade   = min(trades, key=lambda x: x['ProfitLoss_Rs'])

    print(f"{'='*60}")
    print(f"  BACKTEST PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    print(f"  Symbol              : {SYMBOL}")
    print(f"  Period              : {PERIOD} ({INTERVAL} candles)")
    print(f"  Initial Capital     : Rs {INITIAL_CAPITAL:.2f}")
    print(f"  Final Balance       : Rs {final_balance:.2f}")
    print(f"  Total Profit/Loss   : Rs {total_profit:.2f}")
    print(f"  Total Return        : {total_return}%")
    print(f"  Max Drawdown        : {max_drawdown:.2f}%")
    print(f"  Total Trades        : {total_trades}")
    print(f"  Winning Trades      : {len(winning)}")
    print(f"  Losing Trades       : {len(losing)}")
    print(f"  Win Rate            : {win_rate}%")
    print(f"  Avg Win             : Rs {avg_win:.2f}")
    print(f"  Avg Loss            : Rs {avg_loss:.2f}")
    print(f"  Profit Factor       : {profit_factor}")
    print(f"  Best Trade          : Rs {best_trade['ProfitLoss_Rs']:+.2f}")
    print(f"  Worst Trade         : Rs {worst_trade['ProfitLoss_Rs']:+.2f}")
    print(f"{'='*60}\n")

    print(f"  DETAILED TRADE LOG")
    print(f"{'='*60}")
    print(f"  {'No':<4} {'Sig':<5} {'Entry':>8} {'Exit':>8} {'Qty':>5} "
          f"{'P&L(Rs)':>10} {'Balance':>10} {'Result':<6} {'Reason'}")
    print("  " + "-"*70)
    for t in trades:
        print(f"  {t['TradeNo']:<4} {t['Signal']:<5} {t['EntryPrice']:>8.2f} "
              f"{t['ExitPrice']:>8.2f} {t['Quantity']:>5} "
              f"{t['ProfitLoss_Rs']:>+10.2f} {t['BalanceAfter']:>10.2f}  "
              f"{t['Result']:<6} {t['ExitReason']}")
    print(f"{'='*60}\n")


    print(f"{'='*60}")
    print(f"  Strategy    : Bollinger Bands Mean Reversion")
    print(f"  Stock       : IDBI Bank NSE ({SYMBOL})")
    print(f"  Timeframe   : {INTERVAL} candles")
    print(f"  Test Period : {PERIOD}")
    print(f"  Total Trades: {total_trades}")
    print(f"  Win Rate    : {win_rate}%")
    print(f"  Return      : {total_return}%")
    print(f"  Profit Factor: {profit_factor}")
    print(f"  Max Drawdown: {max_drawdown:.2f}%")
    print(f"{'='*60}\n")


# ─────────────────────────────────────────────
# PRINT JSON OUTPUT FOR n8n / GOOGLE SHEETS
# ─────────────────────────────────────────────
def print_json_output(trades, final_balance):
    if not trades:
        return

    # Format exactly like live script JSON
    output = {
        'timestamp'      : str(datetime.now()),
        'mode'           : 'DEMO',
        'symbol'         : SYMBOL,
        'initial_capital': INITIAL_CAPITAL,
        'final_balance'  : final_balance,
        'total_trades'   : len(trades),
        'trade_log'      : []
    }

    for t in trades:
        output['trade_log'].append({
            'Timestamp'    : t['Timestamp'],
            'ExitTime'     : t['ExitTime'],
            'Symbol'       : SYMBOL,
            'Signal'       : t['Signal'],
            'ClosePrice'   : t['EntryPrice'],
            'SMA'          : t['SMA'],
            'UpperBand'    : t['UpperBand'],
            'LowerBand'    : t['LowerBand'],
            'Quantity'     : t['Quantity'],
            'TradeAmount'  : t['TradeAmount'],
            'ProfitLoss_Rs': t['ProfitLoss_Rs'],
            'FinalBalance' : t['BalanceAfter'],
            'TotalTrades'  : t['TradeNo'],
            'ExitReason'   : t['ExitReason'],
            'Result'       : t['Result'],
            'Mode'         : 'DEMO'
        })

    print("\n[N8N_OUTPUT_START]")
    print(json.dumps(output, indent=2))
    print("[N8N_OUTPUT_END]")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    df                        = fetch_data()
    df                        = calculate_bollinger_bands(df)
    df                        = generate_signals(df)
    trades, balance, drawdown = run_backtest(df)
    print_report(trades, balance, drawdown)
    print_json_output(trades, balance)


if __name__ == "__main__":
    main()