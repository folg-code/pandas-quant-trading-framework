# Python Trading Research & Execution Framework

A **modular, end-to-end quantitative research and execution framework** written in Python.

## What This Project Showcases

### Software Engineering
- clean, layered architecture
- modular and extensible design
- separation of research, execution, and infrastructure concerns
- deterministic and reproducible pipelines
- multiprocessing & performance optimization
- stateful systems with crash-safe persistence

### Data  Engineering
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

## Performance & Profiling (Reference)

This project includes **end-to-end runtime profiling** to track performance
regressions and architectural changes over time.

### Test Context
- Market: **EURUSD**
- Timeframes: **M5 + M30 informatives**
- Timerange : **2019:01:01 - 2025:12:31**
- Dataset size:
  - M5: ~734,000 bars
  - M30: ~123,000 bars
- Mode: single-symbol, single-process
- Strategy: HTS / structure-based strategy

### Signal & Trade Volume (Intentional Stress Test)
- **Generated signals:** ~302,000  
- **Executed trades:** ~49,000  

 The signal and trade counts are **intentionally unrealistically high**.  
 This setup is used as a **performance stress test**, not as a realistic
 trading configuration.

 A higher number of trades directly increases:
 - execution simulation complexity
 - state transitions
 - partial exit calculations
 - reporting and statistics computation

 This makes runtime measurements **more representative for worst-case
 performance scenarios**.

### Runtime Breakdown (Approximate)
- Data loading: ~4.3s  
- Informative timeframes (M30): ~2.5s  
- Feature computation (`populate_indicators`): ~4.6s  
- Entry logic & signal generation: ~3.5s  
- Backtest engine (execution simulation): ~1.8s  
- Reporting & analytics: ~2.7s  

**Total runtime:** ~20 seconds

Most of the runtime is spent on **feature computation and market structure logic**,
which is expected at the current development stage.  
Backtest execution itself is **not a bottleneck**, even with a very large number
of generated signals and trades.

This profiling snapshot serves as a **baseline reference**.
Performance numbers may change as features, execution layers,
or infrastructure evolve.

---

## What This Repository Is (and Is Not)

**This is:**
- a systems design project
- a data engineering &  research framework
- a demonstration of Python engineering skills

**This is not:**
- a commercial trading bot
- a black-box ML system
- a promise of trading profitability

---

## Disclaimer

This project is provided for **demonstration and educational purposes only**.
Any use in live markets is at the user's own risk.

---

## Roadmap / TODO

This roadmap defines the long-term development plan for the project.
The order is intentional and optimized for:
- fast feedback loops
- minimal overengineering
- controlled growth of system complexity
- clear separation between research, analytics, execution, and infrastructure

---

## Phase 0 — Baseline Stabilization
**Goal:** Establish a fixed reference point for all further work.

- Finalize TechnicalAnalysis refactor, focusing on architecture cleanup
- Freeze one strategy, one market, one timeframe
- Define a fixed historical dataset
- Create a baseline backtest result
- Treat this result as the reference benchmark

_No new features, or research in this phase._

---

## Phase 1 — Analytics & Reporting Foundation
**Goal:** Build reusable analytical tools and frameworks that will later
enable systematic, repeatable, and extensible quantitative research.


- Feature expectancy & stability tooling  
  - generic tools for expectancy / winrate vs feature quantiles  
  - rolling performance and feature drift detectors  

- Regime-aware backtesting tooling  
  - reusable regime segmentation (trend / volatility / session)  
  - backtest runners producing regime-split metrics and equity curves 
  
- Walk-forward & time-sliced validation tooling  
  - configurable optimization / validation / test windows  
  - robustness and performance decay scoring utilities 

- R-distribution & trade contribution tooling  
  - standardized R-distribution analytics  
  - tail risk and trade contribution analyzers  

- Backtest vs live (dry-run) consistency tooling  
  - dataset alignment and metric comparison utilities  
  - divergence detection with alerting hooks  

---

## Phase 2 — Feature Engineering (No ML)
**Goal:** Identify informative and stable features.

- Extract contextual features from the core engine:
  - market structure
  - trend regime
  - volatility regime
  - distance to key levels
  - time-based features (session, bar index)
- Analyze feature behavior:
  - expectancy by quantiles
  - stability across time
  - redundancy and correlation
- Remove weak, unstable, or redundant features
- Build a final feature set (approximately 5–20 features)

No machine learning is used in this phase.

---

## Phase 3 — Machine Learning (Decision Trees)
**Goal:** Improve trade selection via probabilistic scoring.

- Define ML targets (e.g. win/loss, R > threshold)
- Train tree-based models:
  - Random Forest
  - XGBoost / LightGBM
- Perform strict out-of-sample and walk-forward validation
- Analyze feature importance and decision boundaries
- Integrate ML as a scoring / filtering layer (not signal generation)
- Discard ML if it does not improve robustness or equity behavior

ML is used to strengthen edge, not to create it.

---

## Phase 4 — Market Research (Iterative)
**Goal:** Systematically explore and validate new market hypotheses.

- Formulate explicit hypotheses about price behavior
- Translate hypotheses into measurable features
- Validate ideas using the analytics layer
- Discard ideas without measurable edge
- Iterate only through data-driven feedback

Research is always subordinate to analytics.

---

## Phase 5 — Execution Layer & Containerization
**Goal:** Production-ready execution independent of Windows.

- Implement execution adapter (cTrader Open API)
- Add  risk and rule guards
- Introduce Docker-based runtime for the engine
- Support live and paper trading modes
- Add execution health checks and fail-safe mechanisms

Execution logic remains thin, deterministic, and broker-agnostic.

---

## Phase 6 — Runtime Control & Telegram Notifications
**Goal:** Safe live operation and real-time supervision.

### Strategy Runtime Control
- Enable / disable strategies at runtime
- Temporary pause / resume trading
- Scheduled trading blackout windows (e.g. high-impact news)
- Strategy reload without full system restart

### Trade Operations
- Manual trade close (full or partial)
- Emergency close-all positions
- Per-strategy and global kill switch

### Telegram Notification System
- Trade lifecycle notifications:
  - trade opened
  - trade closed
  - execution errors
- Risk alerts:
  - daily drawdown thresholds
  - max drawdown proximity
- Strategy state changes:
  - paused
  - resumed
  - disabled
  - reloaded
- Connectivity and execution health alerts
- Configurable notification levels (info / warning / critical)

Runtime control must be deterministic, auditable, and broker-agnostic.

---

## Phase 6.5 — Backtest vs Live Consistency Validation
**Goal:** Detect execution drift and hidden performance degradation.

- Align backtest, dry-run, and live trade datasets
- Compare key metrics:
  - trade count
  - winrate
  - expectancy
  - R distribution
  - drawdown profile
- Detect missing or extra trades in live vs backtest
- Analyze timing and slippage differences
- Define acceptable deviation thresholds
- Trigger Telegram alerts on significant divergence
- Generate consistency comparison reports and plots

This phase acts as an early warning system before scaling live trading.

---

## Phase 7 — Django Control Plane
**Goal:** Operational usability and orchestration.

- Django models:
  - Strategy
  - Backtest
  - Trade
  - Report
  - RuntimeState
- Asynchronous backtest manager
- Dashboard for analytics, reports, and comparisons
- GUI for:
  - starting / stopping strategies
  - pausing / resuming trading
  - manual trade management
  - triggering strategy reloads
- compliance monitoring
- Centralized Telegram notification configuration

Django acts as a control plane, not a computation engine.

---

## Phase 8 — Advanced System Intelligence (Future)
**Goal:** Improve robustness, scalability, and understanding.

- Market regime taxonomy beyond trend/range
- Multi-timeframe contextual intelligence
- Dynamic risk and capital allocation
- Explainability for ML-based decisions
- Strategy A/B testing and experimentation framework
- Strategy-as-configuration (DSL / YAML / JSON)
- Stress testing:
  - latency
  - slippage
  - spread shocks
- Human-in-the-loop supervision workflows
- Knowledge graph linking features, setups, regimes, and outcomes

These enhancements follow only after a stable core is achieved.

---

