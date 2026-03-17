# bollinger-bands-trading-system
Automated Trading System Using Bollinger Bands and n8n Workflow Automation
# 📈 Automated Trading System Using Bollinger Bands & n8n

> **ICETCI 2026 Conference Paper**  
> Department of AI and Data Science, Anantrao Pawar College of Engineering, Pune

<img width="1172" height="768" alt="Screenshot 2026-03-17 at 5 30 22 PM" src="https://github.com/user-attachments/assets/33d278c2-a486-4648-8a35-a0f4628fbf86" />

<img width="1468" height="801" alt="Screenshot 2026-03-17 at 6 10 29 PM" src="https://github.com/user-attachments/assets/9e2ccf10-729f-4654-b5fe-263c303553b4" />

<img width="1276" height="661" alt="Screenshot 2026-03-17 at 6 14 54 PM" src="https://github.com/user-attachments/assets/2df2d21b-f0dd-4ff4-89e5-c21fa6a34dca" />




---

## 📋 Overview

This project implements a fully automated stock trading system for **IDBI Bank (NSE: IDBI)** using **Bollinger Bands** as the core technical indicator. The system is integrated with **n8n workflow automation** for scheduling, **Angel One SmartAPI** for order execution, and **Telegram** for real-time alerts.

### 🏆 Results

| Period | Trades | Win Rate | Return | Profit Factor |
|--------|--------|----------|--------|---------------|
| 5 Days (Live) | 9 | **78%** | Rs 13.3 | 6.0 |
| 1 Month (Backtest) | 8 | **62.5%** | 0.1% | 0.69 |
| 1 Year (Backtest) | 11 | **45.5%** | 1.02% | 1.68 |

---

## 🏗️ System Architecture

```
n8n Schedule Trigger (every 30 min)
        ↓
Execute Command Node
        ↓
Python Script:
  1. Login → Angel One SmartAPI
  2. Fetch → Yahoo Finance (IDBI.NS)
  3. Calculate → Bollinger Bands
  4. Generate → Buy/Sell Signals
  5. Execute → Orders via Angel One
  6. Track → Capital & Balance
  7. Output → JSON for n8n
        ↓
IF Buy/Sell Signal
  ├── Telegram Alert
  └── Google Sheets Log
```

---

## 📐 Strategy — Bollinger Bands

### Equations

| Equation | Formula | Description |
|----------|---------|-------------|
| (1) | SMAₜ = (1/n) Σ Pₜ₋ᵢ | Simple Moving Average |
| (2) | σₜ = √[(1/n) Σ (Pₜ₋ᵢ - SMAₜ)²] | Standard Deviation |
| (3) | UBₜ = SMAₜ + k·σₜ | Upper Band |
| (4) | LBₜ = SMAₜ - k·σₜ | Lower Band |
| (5) | Pₜ < LBₜ AND Pₜ₋₁ ≥ LBₜ₋₁ | Buy Signal |
| (6) | Pₜ > UBₜ AND Pₜ₋₁ ≤ UBₜ₋₁ | Sell Signal |
| (7) | Pₜ ≥ SMAₜ (Long) | Mean-Reversion Exit |
| (8) | Pₜ ≤ SMAₜ (Short) | Mean-Reversion Exit |
| (9) | Entry × 0.98 | Long Stop-Loss |
| (10) | Entry × 1.02 | Short Stop-Loss |

### Parameters
- **SMA Period (n):** 20 candles
- **Std Dev Multiplier (k):** 2
- **Stop Loss:** 2%
- **Timeframe:** 30 minutes
- **Risk per Trade:** 10% of balance

---

## 📁 Repository Structure

```
bollinger-bands-trading-system/
│
├── bollinger_trading_system_angelone.py  # Main live trading script
├── bollinger_backtest.py                 # Backtesting script
├── bollinger_tradingview.pine            # TradingView Pine Script
├── bollinger_n8n_workflow.json           # n8n workflow (import directly)
├── backtest_report.html                  # Visual backtest report
├── config.py.example                     # Credentials template
└── README.md                             # This file
```

---

## 🚀 Quick Start

### Prerequisites
```bash
pip install smartapi-python pyotp yfinance pandas numpy logzero
```

### Setup
1. Clone the repository:
```bash
git clone https://github.com/Prajwal02531/bollinger-bands-trading-system.git
cd bollinger-bands-trading-system
```

2. Create `config.py` with your Angel One credentials:
```python
API_KEY      = "your_api_key"
CLIENT_ID    = "your_client_id"
PASSWORD     = "your_4digit_mpin"
TOTP_SECRET  = "your_totp_secret"
```

3. Run the live trading script:
```bash
python bollinger_trading_system_angelone.py
```

4. Run the backtest:
```bash
python bollinger_backtest.py
```

---

## ⚙️ Configuration

Edit the top of `bollinger_trading_system_angelone.py`:

```python
SYMBOL          = "IDBI.NS"     # Stock symbol
PERIOD          = "5d"          # Data period
INTERVAL        = "30m"         # Candle interval
SMA_PERIOD      = 20            # Bollinger Band period
STD_MULT        = 2             # Standard deviation multiplier
STOP_LOSS_PCT   = 0.02          # 2% stop loss
INITIAL_CAPITAL = 10000.00      # Starting capital in Rs
RISK_PER_TRADE  = 0.10          # 10% risk per trade
MODE            = "DEMO"        # "DEMO" or "LIVE"
```

---

## 🤖 n8n Workflow Setup

1. Install n8n:
```bash
npm install n8n -g
n8n start
```

2. Open `http://localhost:5678`

3. Import `bollinger_n8n_workflow.json`:
   - Click **⋯ menu → Import from file**
   - Select the JSON file

4. Configure nodes:
   - **Execute Command:** Set path to your Python script
   - **Telegram:** Add your bot token and chat ID
   - **Google Sheets:** Connect your Google account

5. Activate the workflow ✅

---

## 📊 Backtest Results

### 1 Month (30-min candles)

| # | Signal | Entry | Exit | Qty | P&L | Result |
|---|--------|-------|------|-----|-----|--------|
| 1 | Buy | 110.58 | 113.80 | 9 | +28.98 | ✅ WIN |
| 2 | Sell | 114.99 | 113.45 | 8 | +12.32 | ✅ WIN |
| 3 | Sell | 114.47 | 113.51 | 8 | +7.68 | ✅ WIN |
| 4 | Sell | 116.37 | 113.94 | 8 | +19.44 | ✅ WIN |
| 5 | Buy | 110.19 | 111.19 | 9 | +9.00 | ✅ WIN |
| 6 | Buy | 101.89 | 99.29 | 9 | -23.40 | ❌ LOSS |
| 7 | Buy | 96.17 | 93.97 | 10 | -22.00 | ❌ LOSS |
| 8 | Buy | 79.61 | 77.75 | 12 | -22.32 | ❌ LOSS |

**Win Rate: 62.5% | Return: 0.1% | Max Drawdown: 0.67%**

---

## 🔔 Telegram Alert Format

```
🚨 Trading Signal!

Symbol: IDBI.NS
Signal: Buy
Price: Rs 96.17
SMA: Rs 95.98
Quantity: 10
Balance: Rs 9978
Time: 2026-03-13 09:30
```

---

## ⚠️ Disclaimer

> This project is for **educational and research purposes only**.  
> It was developed as part of a conference paper submission to ICETCI 2026.  
> Do NOT use this system for real trading without proper understanding of financial risks.  
> The authors are not responsible for any financial losses.

---

## 👥 Authors

| Name | Role |
|------|------|
| Prajwal Chidrewar | Lead Developer |
| Vedant Ghare | Co-Author |
| Pandurang Melgave | Co-Author |
| Madhumita Khanvilkar | Co-Author |
| Vishakha Ovhal | Co-Author |
| Jitendra Musale | Guide |

**Institution:** Department of AI and Data Science  
Anantrao Pawar College of Engineering, Pune, India

---

## 📄 Paper

**Title:** Automated Trading System Using Bollinger Bands and n8n Workflow Automation  
**Conference:** ICETCI 2026  
**Stock Tested:** IDBI Bank NSE (IDBI.NS)

---
