# SSA Gourmet - Intelligent Battery Optimization

### AED × UPC Sostenible Datathon 2026

**Predicting energy. Optimizing decisions. Building a more sustainable campus.**

An intelligent energy management system developed for the **AED × UPC Sostenible Datathon 2026**, focused on optimizing battery storage operations at UPC's Campus Nord in Barcelona.

Our solution combines **Model Predictive Control (MPC), mathematical optimization, probabilistic forecasting, and real-time adaptation** to reduce electricity costs and carbon emissions while respecting the physical constraints of an industrial battery.

---

## The Challenge

How can we make a university campus more energy-efficient using artificial intelligence and optimization?

Electricity demand, photovoltaic production, electricity prices, and grid carbon intensity constantly fluctuate. A battery can help balance these variations, but deciding **when to charge, when to discharge, and how much energy to store** is a complex sequential decision-making problem.

The objective is to develop an autonomous controller that:

- Minimizes CO₂ emissions associated with electricity consumption.
- Reduces electricity costs.
- Maximizes the use of locally generated solar energy.
- Optimizes battery charging and discharging decisions.
- Respects battery capacity, power limits, and operational safety.
- Generalizes to unseen future data without accessing future observations.

The controller receives a new observation every hour and must return a single battery power setpoint.

**Positive power = charging | Negative power = discharging**

## Two Optimization Modes

The competition introduces two operational environments.

| Parameter | Standard Mode | Hard Mode |
|---|---|---|
| Battery capacity | 2,000 kWh | 6,000 kWh |
| Maximum power | ±500 kW | ±1,500 kW |
| Solar generation | Original PV | 12× PV |
| Available market forecast | 24 hours | 3 hours |
| Main challenge | Energy arbitrage | Forecasting and uncertainty |

### Why Hard Mode Is Harder

Hard Mode fundamentally changes the problem.

With twelve times more photovoltaic generation, the campus can produce more electricity than it consumes during sunny hours. Excess solar energy can be stored instead of wasted.

However, the controller receives only three hours of market information, making accurate forecasting essential for planning the full daily battery cycle.

The challenge is no longer simply identifying cheap and expensive hours. It is about **anticipating demand, solar availability, electricity prices, and emissions under uncertainty**.

---

## Our Solution

We developed a forecasting-driven, rolling-horizon battery controller built around five components.

### 1. Data-Driven Forecasting

Historical campus data is used to learn recurring patterns in:

- Electricity consumption
- Photovoltaic generation
- Electricity market prices
- Grid carbon intensity

The forecasting system incorporates seasonal patterns, calendar effects, and learned relationships between observed and future market conditions.

It also uses recent observations to update predictions during execution.

### 2. Real-Time Adaptive Forecasting

Static forecasts are not sufficient for a dynamic energy system.

Our controller continuously adapts its predictions using recent information:

- Demand forecast residuals
- Recent solar production
- Estimated solar clarity
- Calendar-based demand patterns
- Observed forecasting errors

This allows the controller to react to changing campus activity and weather conditions rather than relying exclusively on historical averages.

### 3. Model Predictive Control (MPC)

At every decision step, the controller solves an optimization problem over a rolling horizon of up to 24 hours.

The optimization accounts for:

- Expected future demand and photovoltaic generation
- Forecast electricity prices and CO₂ intensity
- Battery energy capacity and charging power
- Charging and discharging efficiency
- Expected future grid imports
- Operational constraints

Only the **first optimized action** is executed.

At the following hour, new observations arrive, forecasts are updated, and the optimization is solved again.

This rolling-horizon approach allows the system to continuously adapt its decisions.

### 4. Scenario-Based Uncertainty Modeling

Future electricity demand and solar generation are uncertain.

Instead of relying on a single deterministic prediction, our optimization considers multiple possible net-demand scenarios.

The current implementation uses five weighted scenarios around the central forecast, representing different levels of forecasting uncertainty.

The controller minimizes expected weighted grid-import costs across these scenarios, making decisions less dependent on one potentially inaccurate forecast.

### 5. Battery Safety and Physical Constraints

All decisions must respect the battery's physical limitations.

The controller models:

- State of charge (SOC)
- Battery capacity
- Maximum charging and discharging power
- Charging and discharging efficiency
- Feasible energy transitions

A final safety clamp restricts the requested power to the physically feasible range before returning the action.

---

## Mathematical Formulation

The competition evaluates performance using a weighted combination of relative carbon and cost savings:

$$
\text{Score}=\max(0,\ 0.70\Delta CO_2 + 0.30\Delta Cost - 0.20N_{\text{violations}})
$$

where savings are expressed in percentage points.

Our controller uses a surrogate objective that combines expected carbon intensity and electricity prices:

$$
w_t = c_t + \lambda_t p_t
$$

where:

- \(c_t\): predicted grid carbon intensity
- \(p_t\): predicted electricity price
- \(\lambda_t\): adaptive relative cost weight

The optimization minimizes expected weighted grid imports across demand scenarios:

$$
\min \sum_{s \in S} P_s \sum_{t=1}^{H} w_t g_{s,t}^{+}
$$

subject to battery energy and power constraints.

The battery dynamics are modeled as:

$$
SOC_{t+1}=SOC_t+\eta P_t^{charge}-\frac{P_t^{discharge}}{\eta}
$$

with:

$$
\eta=\sqrt{0.90}
$$

The optimization is implemented using **SciPy's HiGHS linear programming solver**.

---

## Architecture

The final submission contains two files:

```text
submission_v7/
├── agent.py       # Forecasting, MPC, adaptation and safety
└── params.json    # Parameters learned from training data
```

### `agent.py`

The main controller implements the competition interface:

```python
class BatteryAgent:
    def __init__(self):
        ...

    def act(self, obs: dict) -> float:
        ...
```

It manages the complete decision-making process, including forecasting, optimization, observation history, and battery safety.

### `params.json`

Contains the learned forecasting parameters, including demand profiles, solar reference profiles, market predictions, uncertainty estimates, and correction coefficients.

The submission is self-contained and does not require access to the training CSV files during evaluation.

---

## Decision-Making Pipeline

```text
           NEW HOURLY OBSERVATION
                     |
                     v
          Read battery state,
          market and telemetry
                     |
                     v
          Update online history
          and forecast residuals
                     |
                     v
          Forecast next 24 hours
          ----------------------
          | Demand             |
          | Solar production   |
          | Electricity prices |
          | Carbon intensity   |
          ----------------------
                     |
                     v
          Generate uncertainty
                scenarios
                     |
                     v
          Solve MPC optimization
                     |
                     v
          Apply battery safety
                constraints
                     |
                     v
          Return charging or
          discharging setpoint
                     |
                     v
              NEXT HOUR
                 REPEAT
```

---

## Evaluation and Generalization

The objective is not to maximize performance on historical data alone.

A strong battery controller must perform reliably on **unseen demand patterns, weather conditions, and electricity market behavior**.

Our development methodology emphasizes:

- Chronological backtesting
- Comparison of competing strategies over identical time windows
- Separate tuning and validation periods
- Monitoring both cost and carbon performance
- Checking battery constraint violations
- Measuring execution time
- Avoiding access to future test data

### Competition Results

The team competed in the independent Standard and Hard Mode leaderboards.

A recorded Hard Mode public evaluation achieved:

| Metric | Recorded result |
|---|---:|
| Public score | **23.01 points** |
| CO₂ avoided | **13,237.8 kg** |
| CO₂ reduction | **21.97%** |
| Electricity savings | **€24,161.84** |
| Cost reduction | **25.44%** |
| Constraint violations | **0** |

*These figures are from a recorded team submission and should not be interpreted as independently verified results of the included v7 controller.*

---

## Technology Stack

**Language:** Python

**Numerical computing:** NumPy

**Data processing:** pandas

**Optimization:** SciPy (`linprog`, HiGHS)

**Model representation:** JSON-based learned parameters

**Methods:** Model Predictive Control, time-series forecasting, linear programming, scenario-based optimization, and online residual correction.

---

## Running the Agent

Install the required Python dependencies:

```bash
pip install numpy pandas scipy
```

Ensure `agent.py` and `params.json` are in the same directory.

The controller can then be instantiated as follows:

```python
from agent import BatteryAgent

agent = BatteryAgent()

# obs is provided by the competition environment.
action_kw = agent.act(obs)
```

For competition submission, package both files at the root of a ZIP archive:

```text
submission.zip
├── agent.py
└── params.json
```

The official evaluation environment calls `BatteryAgent.act()` once per simulation step.

---

## Key Engineering Principles

**Causal by design.** The controller uses available observations and learned parameters rather than future test information.

**Forecast-aware.** Decisions account for future electricity demand, solar production, prices, and emissions.

**Adaptive.** Forecast corrections and objective weights evolve as new information becomes available.

**Safety-conscious.** Battery feasibility is checked before executing each action.

**Computationally practical.** Linear programming makes repeated rolling-horizon optimization feasible within the competition environment.

**Generalization-oriented.** Chronological evaluation is used to assess performance beyond the data used for tuning.

---

## Team — SSA Gourmet

Developed by:

- **Mar Becerra i Vilardaga**
- **Jan Monné Parera**
- **Clara Ruiz Dichos**
- **Arnau Roca Puig**

**Universitat Politècnica de Catalunya (UPC)**

AED × UPC Sostenible Datathon 2026

---

## What We Learned

This project demonstrates that energy optimization is not simply about charging a battery when electricity is cheap and discharging when it is expensive.

Real-world decisions require balancing competing objectives, imperfect forecasts, physical constraints, and uncertainty.

By combining forecasting with mathematical optimization and continuous adaptation, we explored how intelligent energy storage can contribute to a more efficient and sustainable university campus.

**Better predictions. Smarter decisions. Lower emissions.**

---

*Built for the AED × UPC Sostenible Datathon 2026 — Barcelona, Spain.*
