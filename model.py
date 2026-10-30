"""
model.py - Stochastic optimization model for hospital resource allocation.

All numbers are ILLUSTRATIVE ACADEMIC ASSUMPTIONS, not real hospital data.
Benefit values are hypothetical rupee-equivalent scores, not real valuations
of patient health or life. Not suitable for clinical decisions.

Model
-----
Decision variables : B (bed units), S (staff units), integers >= 0
Effective capacity : C = min(B, S)
Per scenario i     : emergency served  = min(E_i, C)
                     general served    = min(G_i, C - emergency served)
                     V_i = benE*emerg_served + benG*gen_served - cB*B - cS*S
Objective          : maximize E[V] = sum_i p_i * V_i   (exact enumeration)
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

TOL = 1e-9


# --------------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Scenario:
    name: str
    probability: float
    general: int
    emergency: int


@dataclass(frozen=True)
class Params:
    benefit_general: float = 1000.0
    benefit_emergency: float = 2500.0
    cost_bed: float = 250.0
    cost_staff: float = 180.0
    max_beds: int = 100
    max_staff: int = 100


def default_scenarios() -> List[Scenario]:
    """Illustrative demand scenarios from the project brief."""
    return [
        Scenario("Low demand", 0.20, 40, 8),
        Scenario("Normal demand", 0.50, 60, 12),
        Scenario("High demand", 0.30, 85, 20),
    ]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def validate_scenarios(scenarios: Sequence[Scenario]) -> None:
    """Raise ValueError if scenarios are not a valid discrete distribution."""
    if len(scenarios) == 0:
        raise ValueError("At least one scenario is required.")
    for s in scenarios:
        if s.probability < 0 or s.probability > 1:
            raise ValueError(f"Probability of '{s.name}' must be in [0, 1].")
        if s.general < 0 or s.emergency < 0:
            raise ValueError(f"Demand of '{s.name}' cannot be negative.")
    total = sum(s.probability for s in scenarios)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Probabilities must sum to 1 (got {total:.6f}).")


def validate_params(params: Params) -> None:
    if params.max_beds < 0 or params.max_staff < 0:
        raise ValueError("Capacity limits must be non-negative.")
    for label, v in [("benefit_general", params.benefit_general),
                     ("benefit_emergency", params.benefit_emergency),
                     ("cost_bed", params.cost_bed),
                     ("cost_staff", params.cost_staff)]:
        if v < 0:
            raise ValueError(f"{label} must be non-negative.")


# --------------------------------------------------------------------------
# Single-scenario evaluation
# --------------------------------------------------------------------------
def effective_capacity(beds: int, staff: int) -> int:
    return min(int(beds), int(staff))


def evaluate_scenario(beds: int, staff: int, scenario: Scenario, params: Params) -> dict:
    """Outcome of one (B, S) allocation under one demand scenario."""
    if beds < 0 or staff < 0:
        raise ValueError("Beds and staff must be non-negative.")
    cap = effective_capacity(beds, staff)
    emerg_served = min(scenario.emergency, cap)           # emergency first
    gen_served = min(scenario.general, cap - emerg_served)  # leftover capacity
    total_demand = scenario.emergency + scenario.general
    benefit = (emerg_served * params.benefit_emergency
               + gen_served * params.benefit_general)
    cost = beds * params.cost_bed + staff * params.cost_staff
    served = emerg_served + gen_served
    return {
        "scenario": scenario.name,
        "probability": scenario.probability,
        "emergency_demand": scenario.emergency,
        "general_demand": scenario.general,
        "effective_capacity": cap,
        "emergency_served": emerg_served,
        "general_served": gen_served,
        "emergency_unserved": scenario.emergency - emerg_served,
        "general_unserved": scenario.general - gen_served,
        "total_served": served,
        "total_unserved": total_demand - served,
        "service_rate": served / total_demand if total_demand > 0 else 1.0,
        "benefit": benefit,
        "cost": cost,
        "net_value": benefit - cost,
    }


def scenario_table(beds: int, staff: int, scenarios: Sequence[Scenario],
                   params: Params) -> pd.DataFrame:
    return pd.DataFrame([evaluate_scenario(beds, staff, s, params) for s in scenarios])


# --------------------------------------------------------------------------
# Expected value
# --------------------------------------------------------------------------
def expected_summary(beds: int, staff: int, scenarios: Sequence[Scenario],
                     params: Params) -> dict:
    """Probability-weighted expectations for one allocation."""
    df = scenario_table(beds, staff, scenarios, params)
    p = df["probability"]
    return {
        "beds": int(beds),
        "staff": int(staff),
        "effective_capacity": effective_capacity(beds, staff),
        "expected_benefit": float((p * df["benefit"]).sum()),
        "resource_cost": float(beds * params.cost_bed + staff * params.cost_staff),
        "expected_net_value": float((p * df["net_value"]).sum()),
        "expected_served": float((p * df["total_served"]).sum()),
        "expected_unserved": float((p * df["total_unserved"]).sum()),
        "expected_emergency_served": float((p * df["emergency_served"]).sum()),
        "expected_general_served": float((p * df["general_served"]).sum()),
    }


def expected_net_value(beds: int, staff: int, scenarios: Sequence[Scenario],
                       params: Params) -> float:
    return expected_summary(beds, staff, scenarios, params)["expected_net_value"]


def expected_demand(scenarios: Sequence[Scenario]) -> dict:
    return {
        "general": sum(s.probability * s.general for s in scenarios),
        "emergency": sum(s.probability * s.emergency for s in scenarios),
        "total": sum(s.probability * (s.general + s.emergency) for s in scenarios),
    }


# --------------------------------------------------------------------------
# Exact enumeration (vectorised with NumPy over the whole B x S grid)
# --------------------------------------------------------------------------
def expected_value_grid(scenarios: Sequence[Scenario], params: Params) -> np.ndarray:
    """Return array EV[b, s] of expected net value for every b in 0..max_beds,
    s in 0..max_staff. Same formulas as evaluate_scenario, computed in bulk."""
    validate_scenarios(scenarios)
    validate_params(params)
    b = np.arange(params.max_beds + 1)[:, None]
    s = np.arange(params.max_staff + 1)[None, :]
    cap = np.minimum(b, s)
    ev = np.zeros((params.max_beds + 1, params.max_staff + 1))
    for sc in scenarios:
        e_served = np.minimum(sc.emergency, cap)
        g_served = np.minimum(sc.general, cap - e_served)
        benefit = e_served * params.benefit_emergency + g_served * params.benefit_general
        ev += sc.probability * benefit
    ev -= b * params.cost_bed + s * params.cost_staff
    return ev


def optimize(scenarios: Sequence[Scenario], params: Params) -> dict:
    """Exact enumeration of all feasible (B, S). Returns the best allocation.

    Ties are broken deterministically: highest EV, then smaller total
    resource cost, then smaller B, then smaller S.
    """
    ev = expected_value_grid(scenarios, params)
    best = ev.max()
    cand = np.argwhere(ev >= best - TOL)
    keyed = sorted(
        ((int(bb), int(ss)) for bb, ss in cand),
        key=lambda t: (t[0] * params.cost_bed + t[1] * params.cost_staff, t[0], t[1]),
    )
    b_opt, s_opt = keyed[0]
    result = expected_summary(b_opt, s_opt, scenarios, params)
    result["n_combinations_checked"] = int(ev.size)
    result["n_tied_optima"] = len(keyed)
    return result


def optimize_bruteforce(scenarios: Sequence[Scenario], params: Params) -> dict:
    """Slow, loop-based enumeration using evaluate_scenario. Used by tests to
    cross-check the vectorised optimizer."""
    validate_scenarios(scenarios)
    validate_params(params)
    best = None
    for b in range(params.max_beds + 1):
        for s in range(params.max_staff + 1):
            val = expected_net_value(b, s, scenarios, params)
            key = (-val, b * params.cost_bed + s * params.cost_staff, b, s)
            if best is None or (key[0] < best[0] - TOL) or (
                    abs(key[0] - best[0]) <= TOL and key[1:] < best[1:]):
                best = key
    return expected_summary(best[2], best[3], scenarios, params)


def ev_vs_capacity_curve(scenarios: Sequence[Scenario], params: Params) -> pd.DataFrame:
    """Expected net value when B = S = c (a 1-D slice used for the main chart),
    plus the best achievable EV for each effective capacity level."""
    ev = expected_value_grid(scenarios, params)
    n = min(params.max_beds, params.max_staff)
    return pd.DataFrame({
        "capacity": np.arange(n + 1),
        "expected_net_value": [ev[c, c] for c in range(n + 1)],
    })


# --------------------------------------------------------------------------
# Monte Carlo simulation
# --------------------------------------------------------------------------
def monte_carlo(beds: int, staff: int, scenarios: Sequence[Scenario], params: Params,
                n_sims: int = 10000, seed: Optional[int] = 42) -> dict:
    """Sample demand scenarios by their probabilities and compute the net value
    of a FIXED allocation (beds, staff) for every draw."""
    validate_scenarios(scenarios)
    if n_sims < 1:
        raise ValueError("n_sims must be at least 1.")
    rng = np.random.default_rng(seed)
    probs = np.array([s.probability for s in scenarios], dtype=float)
    probs = probs / probs.sum()
    idx = rng.choice(len(scenarios), size=int(n_sims), p=probs)
    per_scenario = np.array([evaluate_scenario(beds, staff, s, params)["net_value"]
                             for s in scenarios])
    values = per_scenario[idx]
    counts = np.bincount(idx, minlength=len(scenarios))
    return {
        "values": values,
        "scenario_counts": counts,
        "mean": float(values.mean()),
        "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        "median": float(np.median(values)),
        "p5": float(np.percentile(values, 5)),
        "p95": float(np.percentile(values, 95)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


# --------------------------------------------------------------------------
# Sensitivity analysis
# --------------------------------------------------------------------------
def sensitivity_costs(scenarios: Sequence[Scenario], params: Params,
                      bed_costs: Sequence[float],
                      staff_costs: Sequence[float]) -> pd.DataFrame:
    """Re-optimise for every (bed cost, staff cost) pair."""
    rows = []
    for cb in bed_costs:
        for cs in staff_costs:
            p = replace(params, cost_bed=float(cb), cost_staff=float(cs))
            r = optimize(scenarios, p)
            rows.append({
                "bed_cost": float(cb), "staff_cost": float(cs),
                "opt_beds": r["beds"], "opt_staff": r["staff"],
                "effective_capacity": r["effective_capacity"],
                "expected_net_value": r["expected_net_value"],
                "expected_unserved": r["expected_unserved"],
            })
    return pd.DataFrame(rows)


def default_cost_range(base: float, steps: int = 5, spread: float = 0.5) -> List[float]:
    """Evenly spaced values from base*(1-spread) to base*(1+spread)."""
    return [float(x) for x in np.linspace(base * (1 - spread), base * (1 + spread), steps)]


def sensitivity_one_at_a_time(scenarios: Sequence[Scenario], params: Params,
                              field: str, values: Sequence[float]) -> pd.DataFrame:
    """Vary one Params field (e.g. 'benefit_general') and re-optimise."""
    rows = []
    for v in values:
        p = replace(params, **{field: float(v)})
        r = optimize(scenarios, p)
        rows.append({field: float(v), "opt_beds": r["beds"], "opt_staff": r["staff"],
                     "effective_capacity": r["effective_capacity"],
                     "expected_net_value": r["expected_net_value"]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# CSV helpers
# --------------------------------------------------------------------------
def scenarios_from_dataframe(df: pd.DataFrame) -> List[Scenario]:
    return [Scenario(str(r["scenario"]), float(r["probability"]),
                     int(r["general_patients"]), int(r["emergency_patients"]))
            for _, r in df.iterrows()]


def scenarios_to_dataframe(scenarios: Sequence[Scenario]) -> pd.DataFrame:
    return pd.DataFrame({
        "scenario": [s.name for s in scenarios],
        "probability": [s.probability for s in scenarios],
        "general_patients": [s.general for s in scenarios],
        "emergency_patients": [s.emergency for s in scenarios],
    })
