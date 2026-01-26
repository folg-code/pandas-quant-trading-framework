# Python Trading Research & Execution Framework

A **modular, end-to-end quantitative research and execution framework** written in Python.

This repository is **not focused on trading performance**, but on **software architecture, data pipelines, backtesting infrastructure, and live system design**.
It is intended for **Python Developer / Engineer** and **Data / Quant Analyst** roles.

---

## What This Project Showcases

### Software Engineering
- clean, layered architecture
- modular and extensible design
- separation of research, execution, and infrastructure concerns
- deterministic and reproducible pipelines
- multiprocessing & performance optimization
- stateful systems with crash-safe persistence

### Data & Quant Engineering
- vectorized time-series processing (`pandas`, `numpy`)
- multi-timeframe data handling
- bias-aware backtesting design
- realistic execution simulation
- statistical analysis and reporting
- visual diagnostics (charts & plots)

---

## Technology Stack

- **Python 3.10+**
- **pandas** – time-series data processing
- **numpy** – numerical computation
- **numba** – JIT-compiled performance-critical paths
- **matplotlib** – charting & visualization
- **rich** – structured console reporting
- **multiprocessing** – parallel backtests & strategy runs
- **MetaTrader5 API** – optional live execution backend

---

## High-Level Capabilities

This framework supports the **entire lifecycle** of a quantitative trading system:

1. **Historical data ingestion**
2. **Multi-timeframe feature computation**
3. **Strategy research & signal generation**
4. **Backtesting with realistic execution logic**
5. **Statistical analysis & reporting**
6. **Visual diagnostics (charts)**
7. **Dry-run simulation**
8. **Live trading with persistent state**

Each stage is implemented as a **decoupled module**, allowing independent testing and extension.

---

## System Architecture (Conceptual)

```
Data Providers
  ├── Historical (Dukascopy, cached)
  └── Live (MT5)
        ↓
Market Structure / Feature Engine
        ↓
Strategy Layer (multi-timeframe)
        ↓
Execution Engines
  ├── Backtesting Engine
  ├── Dry-Run Engine
  └── Live Trading Engine
        ↓
Reporting & Visualization
```

---

## Core Modules

### 1. Data Layer

Responsible for **data acquisition and caching**:

- historical OHLCV download
- pluggable backends (e.g. Dukascopy, MT5)
- unified interface for backtest & live data
- local cache for reproducibility and speed

The rest of the system never depends on a concrete data source.

---

### 2. Feature / Market Structure Engine

A **deterministic, dependency-aware computation engine**:

- batch-based processing (no DataFrame mutation)
- explicit feature dependencies
- vectorized time-series operations

Used to generate reusable features for:
- research
- backtesting
- live trading

This module demonstrates **complex data pipelines built on pandas**.

---

### 3. Strategy Layer

Strategies are implemented as **pure data transformations**:

- consume DataFrames
- produce signals & execution plans
- no knowledge of execution or portfolio state

Supports:
- multi-timeframe strategies
- reusability between backtest, dry-run, and live trading
- deterministic behavior

---

### 4. Backtesting Engine

Designed for **correctness and realism**, not shortcuts:

- candle-based execution using high/low simulation
- partial exits
- break-even logic
- slippage modeling
- trade de-duplication per signal tag
- multiprocessing across symbols

Performance-critical exit simulation is implemented with **Numba JIT**.

---

### 5. Reporting & Analytics

The reporting layer provides:

- equity curve computation
- drawdown analysis
- expectancy & profit factor
- per-symbol and per-signal statistics
- stability analysis across backtest windows

Reports are available as:
- rich console tables
- text files
- data structures for further analysis

---

### 6. Visualization

Charting utilities support:

- price charts
- signal overlays
- trade entry / exit visualization
- diagnostic plots for research validation

Plots are generated automatically during backtests.

---

### 7. Dry-Run Mode

A full **execution simulation without broker interaction**:

- uses the same execution pipeline as live trading
- validates logic, risk management, and state transitions
- safe environment for end-to-end testing

---

### 8. Live Trading Engine

A production-style orchestration layer:

- candle-based strategy execution
- tick-based position management
- risk-based position sizing
- partial closes and stop updates
- broker abstraction via adapter

Live trading uses a **persistent state repository** to ensure restart safety.

---

### 9. Persistence Layer

State management is implemented via a lightweight repository:

- JSON-based storage
- atomic writes
- crash-safe design
- single source of truth for live positions

Demonstrates **robust state handling in long-running systems**.

---

## What This Repository Is (and Is Not)

**This is:**
- a systems design project
- a data engineering & quantitative research framework
- a demonstration of Python engineering skills

**This is not:**
- a commercial trading bot
- a black-box ML system
- a promise of trading profitability

---

## Intended Audience

- Python Developers / Engineers
- Data Engineers
- Quantitative / Research Engineers
- Recruiters evaluating real-world system design

---

## Disclaimer

This project is provided for **demonstration and educational purposes only**.
Any use in live markets is at the user's own risk.

---

## Roadmap / TODO

The following items are **explicitly planned** and included to transparently communicate the project’s direction and technical depth:

- **Full refactor of Technical Analysis modules**  
  Focus on architecture cleanup and consistency, including:
  - `PriceStructureZones`
  - `Sessions`
  
  Goal: clearer module boundaries, improved testability, and removal of legacy coupling.  
  **Status:** work in progress.

- **Extended plotting and reporting layer**  
  Planned improvements include:
  - richer diagnostic charts
  - deeper per-strategy and per-feature analytics
  - exportable report formats (research-oriented, not marketing)

- **Machine Learning–ready strategy framework**  
  Preparation of the framework for ML-based strategies, with a focus on:
  - tree-based models (e.g. decision trees, ensembles)
  - strict separation between feature generation and model inference
  - reuse of the same backtesting and execution pipeline

These items are intentionally listed to highlight **forward-looking system design** rather than unfinished work.

---

## Author Note

The primary goal of this project is to demonstrate how I design and build:
- modular Python systems
- data-intensive pipelines
- reproducible research environments
- production-style execution engines

