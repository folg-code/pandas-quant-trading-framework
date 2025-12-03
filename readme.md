# PandasQuantLab

PandasQuantLab is a modular framework for quantitative trading in Python.  
It integrates backtesting, strategy development, technical analysis, and live trading into a single, extensible structure. The project is designed for traders and developers who want to build, test, and deploy algorithmic strategies using a clean and scalable architecture.

---

## 🚀 Key Features

### **Backtesting Engine**
- Vectorized backtests based on Pandas.
- Trade tracking, performance metrics, and statistics.
- Automated report generation.
- Plotting utilities for equity curves, drawdowns, signals, and more.

### **Live Trading Module**
- File-based or API-driven signal management.
- Position manager for tracking open and closed trades.
- Order execution module (exchange/broker integration ready).
- Telegram sender for notifications and alerts.

### **Strategies**
- Plug-and-play strategy architecture.
- Easy to extend with custom trading logic.
- Compatible with historical and live data flows.

### **Technical Analysis Toolkit**
Contains multiple submodules:
- **Indicators** – classic technical indicators and custom tools.
- **SMC Components** – Points of Interest (POI), sessions, structure tools.
- **Price Action & Fibonacci Tools** – swing detection, levels, confluence zones.


---

## ⚙️ Goals of the Project
- Provide a clean, understandable, and modern framework for quantitative research.
- Allow fast iteration from strategy idea → backtest → live deployment.
- Support both traditional technical analysis and SMC/price-action-based systems.
- Enable modular expansion without breaking existing workflows.

---

## 📊 Project Summary – Completed & Planned Work

### ✅ What’s Already Implemented

#### **Backtesting Engine**
- Fully functional, vectorized backtesting system.
- Stable trade lifecycle, portfolio tracking, and reporting.
- Plotting tools for performance visualization.

#### **Live Trading**
- Operational live trading pipeline.
- Position Manager for real-time trade handling.
- Telegram notifications integrated.
- Trade executor ready for multi-broker support.

#### **Strategies**
- Working strategy framework.
- Strategies run in both backtest and live environments.
- Technical analysis and SMC/PA modules fully integrated.

#### **Technical Analysis**
- Indicators, SMC utilities, Fibonacci/PA tools.
- All modules are stable and used across strategies.

---

### 🔧 Planned / In Progress

#### **Strategy Development**
- Ongoing work on new algorithmic strategies.
- Expansion of SMC, momentum, and multi-factor models.

#### **Exchange & Platform Support**
- Binance / Bybit API connectors (planned).
- Additional trading platforms beyond MT5 are planned.
- Unified interface for REST and WebSocket feeds.

#### **Web UI Module**
- A browser-based dashboard is planned.
- Live charts, trade monitoring, strategy metrics, and configuration panels.

#### **Dockerization & DevOps**
- Full Docker environment planned for easy deployment.
- Local development containers + production images.

#### **AWS Infrastructure**
- Preparing architecture for AWS deployment:
  - Lambda task runners
  - S3 data storage
  - Event-driven strategy execution
  - CloudWatch monitoring and alerts

#### **Portfolio & Multi-Asset Support**
- Multi-symbol backtesting.
- Portfolio-level metrics.
- Dynamic allocation and risk models.

#### **Optimization & Research Tools**
- Parameter optimization engine.
- Walk-forward testing.
- Robustness and validation tools.

#### **Risk Management Module**
- Position sizing models.
- Volatility filters.
- Built-in risk constraints.

#### **Documentation & Tutorials**
- Strategy templates.
- Indicator and SMC usage examples.
- End-to-end workflow guides.

---

## 🛠️ Requirements
- Python 3.10+
- pandas, numpy
- matplotlib / plotly
- requests
- python-telegram-bot (optional for Telegram)
- Additional libraries depending on runtime environment
