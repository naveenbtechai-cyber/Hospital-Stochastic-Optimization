"""
Hospital Resource Allocation under Uncertain Patient Demand
Streamlit dashboard  -  run with:  streamlit run app.py

All data are ILLUSTRATIVE ACADEMIC ASSUMPTIONS. Not for clinical use.
"""
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

import model as m

DATA_FILE = Path(__file__).parent / "data" / "demand_scenarios.csv"
BLUE, ORANGE, GREEN, RED, GREY = "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#7f7f7f"

st.set_page_config(page_title="Hospital Stochastic Optimization", page_icon="🏥",
                   layout="wide")


# ---------------------------------------------------------------- helpers
def rs(x: float) -> str:
    """Format a number as rupees."""
    sign = "-" if x < 0 else ""
    return f"{sign}₹{abs(x):,.0f}"


def to_key(scenarios):
    return tuple((s.name, s.probability, s.general, s.emergency) for s in scenarios)


def from_key(key):
    return [m.Scenario(*k) for k in key]


@st.cache_data(show_spinner=False)
def cached_optimize(skey, pkey):
    return m.optimize(from_key(skey), m.Params(*pkey))


@st.cache_data(show_spinner=False)
def cached_grid(skey, pkey):
    return m.expected_value_grid(from_key(skey), m.Params(*pkey))


@st.cache_data(show_spinner=False)
def cached_mc(b, s, skey, pkey, n, seed):
    return m.monte_carlo(b, s, from_key(skey), m.Params(*pkey), n, seed)


@st.cache_data(show_spinner=False)
def cached_sens(skey, pkey, bed_costs, staff_costs):
    return m.sensitivity_costs(from_key(skey), m.Params(*pkey), bed_costs, staff_costs)


@st.cache_data(show_spinner=False)
def cached_benefit_sens(skey, pkey, field, values):
    return m.sensitivity_one_at_a_time(from_key(skey), m.Params(*pkey), field, values)


def pkey_of(p: m.Params):
    return (p.benefit_general, p.benefit_emergency, p.cost_bed, p.cost_staff,
            p.max_beds, p.max_staff)


# ---------------------------------------------------------------- header
st.title("🏥 Hospital Resource Allocation under Uncertain Patient Demand")
st.caption("Stochastic optimization mini project  |  exact enumeration + Monte Carlo + sensitivity analysis")
st.warning(
    "**Academic exercise only.** All demand numbers, probabilities, benefits and costs are "
    "**illustrative assumptions**, not real hospital data. Benefit values are hypothetical "
    "rupee-equivalent scores, **not** monetary valuations of patient health or lives. "
    "This tool must not be used for real clinical or hospital decisions.")

# ---------------------------------------------------------------- sidebar
sb = st.sidebar
sb.header("⚙️ Model inputs")
sb.subheader("Capacity limits")
max_beds = sb.number_input("Maximum bed capacity", 0, 500, 100, 5)
max_staff = sb.number_input("Maximum staff capacity", 0, 500, 100, 5)
sb.subheader("Benefits (₹-equivalent score)")
ben_g = sb.number_input("Benefit per general patient", 0.0, 100000.0, 1000.0, 100.0)
ben_e = sb.number_input("Benefit per emergency patient", 0.0, 100000.0, 2500.0, 100.0)
sb.subheader("Resource costs (₹ per unit)")
cost_b = sb.number_input("Cost per bed unit", 0.0, 100000.0, 250.0, 10.0)
cost_s = sb.number_input("Cost per staff unit", 0.0, 100000.0, 180.0, 10.0)
sb.subheader("Monte Carlo")
n_sims = sb.number_input("Number of simulations", 100, 1_000_000, 10000, 1000)
seed = sb.number_input("Random seed", 0, 2**31 - 1, 42, 1)

params = m.Params(ben_g, ben_e, cost_b, cost_s, int(max_beds), int(max_staff))

# ---------------------------------------------------------------- scenarios
st.header("1. Demand scenarios")
try:
    base_df = pd.read_csv(DATA_FILE)
    base_scenarios = m.scenarios_from_dataframe(base_df)
except Exception:  # fall back to built-in defaults if the CSV is missing
    base_scenarios = m.default_scenarios()

st.write("You can edit the table below (probabilities must sum to 1).")
edited = st.data_editor(
    m.scenarios_to_dataframe(base_scenarios), num_rows="fixed", width="stretch",
    key="scenario_editor",
    column_config={
        "scenario": st.column_config.TextColumn("Scenario"),
        "probability": st.column_config.NumberColumn("Probability", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"),
        "general_patients": st.column_config.NumberColumn("General patients", min_value=0, step=1),
        "emergency_patients": st.column_config.NumberColumn("Emergency patients", min_value=0, step=1),
    })

try:
    scenarios = m.scenarios_from_dataframe(edited)
    m.validate_scenarios(scenarios)
    m.validate_params(params)
except Exception as exc:
    st.error(f"❌ Invalid input: {exc}")
    st.stop()

total_p = sum(s.probability for s in scenarios)
ed = m.expected_demand(scenarios)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Probability total", f"{total_p:.2f}", "valid ✓")
c2.metric("Expected general demand", f"{ed['general']:.1f}")
c3.metric("Expected emergency demand", f"{ed['emergency']:.1f}")
c4.metric("Expected total demand", f"{ed['total']:.1f}")

skey, pkey = to_key(scenarios), pkey_of(params)

# ---------------------------------------------------------------- optimisation
st.header("2. Optimization result (exact enumeration)")
opt = cached_optimize(skey, pkey)
B, S = opt["beds"], opt["staff"]

r1 = st.columns(4)
r1[0].metric("Recommended beds (B)", B)
r1[1].metric("Recommended staff units (S)", S)
r1[2].metric("Effective capacity min(B,S)", opt["effective_capacity"])
r1[3].metric("Expected net value", rs(opt["expected_net_value"]))
r2 = st.columns(4)
r2[0].metric("Expected patient-care benefit", rs(opt["expected_benefit"]))
r2[1].metric("Resource cost", rs(opt["resource_cost"]))
r2[2].metric("Expected patients served", f"{opt['expected_served']:.1f}")
r2[3].metric("Expected patients unserved", f"{opt['expected_unserved']:.1f}")

with st.expander("📖 Why was this allocation selected?", expanded=True):
    cap = opt["effective_capacity"]
    per_unit = params.cost_bed + params.cost_staff
    st.markdown(
        f"The program evaluated **{opt['n_combinations_checked']:,}** feasible (B, S) pairs "
        f"(0 ≤ B ≤ {params.max_beds}, 0 ≤ S ≤ {params.max_staff}) and picked the pair with the "
        f"highest expected net value: **B = {B}, S = {S}**.\n\n"
        f"- Effective capacity is `min(B, S)`, so buying more of only one resource adds cost but no "
        f"extra patients served. The optimum therefore balances beds and staff"
        f"{' (B = S)' if B == S else ''}.\n"
        f"- One extra unit of capacity costs **{rs(per_unit)}** (bed + staff). It is worth adding while "
        f"its *expected* benefit (probability that the unit is actually used × benefit per patient) "
        f"exceeds that cost.\n"
        f"- Emergency patients are served first, so early units of capacity are very valuable; later "
        f"units serve only general patients and only in the higher-demand scenarios, so their expected "
        f"benefit falls until it drops below the cost.\n"
        f"- Capacity limits are {'**binding** (the optimum sits on a limit, so raising the limit may help)' if cap >= min(params.max_beds, params.max_staff) and cap > 0 else 'not binding'}.\n"
        f"- Number of tied optimal pairs: {opt['n_tied_optima']} (ties are broken by lower cost).")

# ---------------------------------------------------------------- visualisations
st.header("3. Expected value versus capacity")
grid = cached_grid(skey, pkey)
curve = m.ev_vs_capacity_curve(scenarios, params)

col_a, col_b = st.columns(2)
with col_a:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(curve["capacity"], curve["expected_net_value"], color=BLUE, lw=2,
            label="Expected net value (B = S = capacity)")
    ax.scatter([cap], [opt["expected_net_value"]], color=RED, s=90, zorder=5,
               label=f"Recommended: {cap} units")
    ax.axvline(cap, color=RED, ls="--", lw=1)
    ax.set_xlabel("Capacity (beds = staff units)")
    ax.set_ylabel("Expected net value (₹)")
    ax.set_title("Expected net value vs. capacity")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    st.pyplot(fig); plt.close(fig)
with col_b:
    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(grid.T, origin="lower", aspect="auto", cmap="viridis")
    ax.scatter([B], [S], color="red", marker="*", s=200, label=f"Optimum (B={B}, S={S})")
    ax.set_xlabel("Beds allocated (B)"); ax.set_ylabel("Staff units allocated (S)")
    ax.set_title("Expected net value over all (B, S) pairs")
    fig.colorbar(im, ax=ax, label="Expected net value (₹)")
    ax.legend(fontsize=8, loc="upper left")
    st.pyplot(fig); plt.close(fig)
st.caption("Left: slice where B = S. Right: full search space; the ridge along the diagonal shows that "
           "beds and staff must be matched because capacity = min(B, S).")

# ---------------------------------------------------------------- scenario analysis
st.header("4. Scenario analysis for the recommended allocation")
sdf = m.scenario_table(B, S, scenarios, params)
show = sdf[["scenario", "probability", "emergency_demand", "general_demand",
            "emergency_served", "general_served", "total_unserved", "service_rate", "net_value"]].copy()
show["service_rate"] = (show["service_rate"] * 100).round(1)
show.columns = ["Scenario", "Probability", "Emergency demand", "General demand",
                "Emergency served", "General served", "Total unserved", "Service rate (%)", "Net value (₹)"]
st.dataframe(show.style.format({"Probability": "{:.2f}", "Service rate (%)": "{:.1f}", "Net value (₹)": "₹{:,.0f}"}),
             width="stretch", hide_index=True)

x = np.arange(len(sdf)); w = 0.38
ca, cb = st.columns(2)
with ca:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(x - w/2, sdf["emergency_served"], w, label="Emergency served", color=RED)
    ax.bar(x + w/2, sdf["general_served"], w, label="General served", color=BLUE)
    ax.set_xticks(x); ax.set_xticklabels(sdf["scenario"])
    ax.set_ylabel("Patients served"); ax.set_title("Patients served by scenario")
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)
    st.pyplot(fig); plt.close(fig)
with cb:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(x - w/2, sdf["emergency_unserved"], w, label="Emergency unserved", color=RED)
    ax.bar(x + w/2, sdf["general_unserved"], w, label="General unserved", color=ORANGE)
    ax.set_xticks(x); ax.set_xticklabels(sdf["scenario"])
    ax.set_ylabel("Patients unserved"); ax.set_title("Unserved patients by scenario")
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)
    st.pyplot(fig); plt.close(fig)

worst = sdf.loc[sdf["service_rate"].idxmin()]
st.info(f"**Reading the results:** the allocation is sized for the *expected* mix of demand, not the worst case. "
        f"In **{worst['scenario']}** only {worst['service_rate']*100:.1f}% of patients are served "
        f"({int(worst['total_unserved'])} unserved), and the other scenarios are served at their own "
        f"rates shown above. Emergency patients are prioritised, so general patients are the first to go unserved.")

# ---------------------------------------------------------------- Monte Carlo
st.header("5. Monte Carlo risk analysis")
st.write("Exact enumeration (section 2) **chooses the optimum**. Monte Carlo simulation does **not** search "
         "for a better allocation; it shows how *variable* the outcome of a fixed allocation is when demand "
         "is randomly sampled. You can test the recommended allocation or your own.")
use_custom = st.checkbox("Test a custom allocation instead of the recommended one")
if use_custom:
    mc_b = st.number_input("Beds to simulate", 0, int(max_beds), min(B, int(max_beds)))
    mc_s = st.number_input("Staff units to simulate", 0, int(max_staff), min(S, int(max_staff)))
else:
    mc_b, mc_s = B, S
mc = cached_mc(int(mc_b), int(mc_s), skey, pkey, int(n_sims), int(seed))
exact_val = m.expected_net_value(int(mc_b), int(mc_s), scenarios, params)

k = st.columns(6)
k[0].metric("Mean", rs(mc["mean"]))
k[1].metric("Std. deviation", rs(mc["std"]))
k[2].metric("Median", rs(mc["median"]))
k[3].metric("5th percentile", rs(mc["p5"]))
k[4].metric("95th percentile", rs(mc["p95"]))
k[5].metric("Exact expected value", rs(exact_val), f"MC error {rs(mc['mean']-exact_val)}", delta_color="off")

mc_df = pd.Series(mc["values"]).value_counts().sort_index()
fig, ax = plt.subplots(figsize=(9, 4))
labels = [rs(v) for v in mc_df.index]
ax.bar(labels, mc_df.values / len(mc["values"]), color=BLUE, width=0.5)
ax.axhline(0, color="black", lw=0.5)
ax.set_ylabel("Fraction of simulations"); ax.set_xlabel("Net value of outcome (₹)")
ax.set_title(f"Monte Carlo outcome distribution ({int(n_sims):,} simulations, seed {int(seed)})")
for i, (v, c) in enumerate(mc_df.items()):
    ax.text(i, c / len(mc["values"]), f"{c/len(mc['values'])*100:.1f}%", ha="center", va="bottom", fontsize=9)
ax.axvline(-0.5, alpha=0)  # keep layout stable
st.pyplot(fig); plt.close(fig)
st.caption("With only three demand scenarios, each simulation can take just three possible values, so the "
           "distribution is discrete. The spread between the 5th and 95th percentile measures risk that the "
           "expected value alone hides.")

# ---------------------------------------------------------------- Sensitivity
st.header("6. Sensitivity analysis")
st.write("Bed cost and staff cost are varied around the current sidebar values and the problem is "
         "**re-optimised for every combination**.")
spread = st.slider("Cost variation (±%)", 10, 90, 50, 10) / 100
steps = 5
bed_costs = tuple(round(v, 2) for v in m.default_cost_range(params.cost_bed, steps, spread))
staff_costs = tuple(round(v, 2) for v in m.default_cost_range(params.cost_staff, steps, spread))
sens = cached_sens(skey, pkey, bed_costs, staff_costs)

disp = sens.copy()
disp.columns = ["Bed cost (₹)", "Staff cost (₹)", "Optimal beds", "Optimal staff", "Effective capacity",
                "Expected net value (₹)", "Expected unserved"]
st.dataframe(disp.style.format({"Bed cost (₹)": "{:,.0f}", "Staff cost (₹)": "{:,.0f}",
                                "Expected net value (₹)": "₹{:,.0f}", "Expected unserved": "{:.1f}"}),
             width="stretch", hide_index=True, height=300)

hc1, hc2 = st.columns(2)
for col, field, title, cmap, fmt in [
        (hc1, "effective_capacity", "Optimal effective capacity", "Blues", "{:.0f}"),
        (hc2, "expected_net_value", "Maximum expected net value (₹)", "Greens", "{:,.0f}")]:
    piv = sens.pivot(index="staff_cost", columns="bed_cost", values=field)
    fig, ax = plt.subplots(figsize=(6, 4.2))
    im = ax.imshow(piv.values, origin="lower", cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels([f"{v:,.0f}" for v in piv.columns])
    ax.set_yticks(range(len(piv.index))); ax.set_yticklabels([f"{v:,.0f}" for v in piv.index])
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            ax.text(j, i, fmt.format(piv.values[i, j]), ha="center", va="center", fontsize=8,
                    color="white" if im.norm(piv.values[i, j]) > 0.6 else "black")
    ax.set_xlabel("Cost per bed unit (₹)"); ax.set_ylabel("Cost per staff unit (₹)")
    ax.set_title(title)
    with col:
        st.pyplot(fig)
    plt.close(fig)

st.subheader("Effect of the benefit values")
mult = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
gvals = tuple(round(params.benefit_general * f, 2) for f in mult)
evals = tuple(round(params.benefit_emergency * f, 2) for f in mult)
sg = cached_benefit_sens(skey, pkey, "benefit_general", gvals)
se = cached_benefit_sens(skey, pkey, "benefit_emergency", evals)
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].plot(sg["benefit_general"], sg["effective_capacity"], "o-", color=BLUE)
axes[0].set_xlabel("Benefit per general patient (₹)"); axes[0].set_ylabel("Optimal effective capacity")
axes[0].set_title("Optimal capacity vs. general-patient benefit"); axes[0].grid(alpha=0.3)
axes[1].plot(se["benefit_emergency"], se["effective_capacity"], "o-", color=RED)
axes[1].set_xlabel("Benefit per emergency patient (₹)"); axes[1].set_ylabel("Optimal effective capacity")
axes[1].set_title("Optimal capacity vs. emergency-patient benefit"); axes[1].grid(alpha=0.3)
st.pyplot(fig); plt.close(fig)
st.caption("Higher resource costs push the optimum toward less capacity; higher benefits push it toward more. "
           "A flat line means that parameter does not change the decision over this range: e.g. emergency "
           "patients are always worth serving, so the choice of capacity is decided by the marginal general patients.")

# ---------------------------------------------------------------- footer
st.divider()
st.caption("Illustrative academic model. Results are computed live from the model in `model.py`; "
           "no values are hard-coded. Not suitable for real clinical decisions.")
