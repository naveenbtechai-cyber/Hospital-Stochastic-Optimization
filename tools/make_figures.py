"""Generate report/presentation figures from the real model (run from repo root:
python tools/make_figures.py)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import model as m

OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
sc, p = m.default_scenarios(), m.Params()
opt = m.optimize(sc, p)
B, S = opt["beds"], opt["staff"]
BLUE, RED, ORANGE = "#1f77b4", "#d62728", "#ff7f0e"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=160)
    plt.close(fig)


# 1 expected value vs capacity
curve = m.ev_vs_capacity_curve(sc, p)
fig, ax = plt.subplots(figsize=(6.4, 4))
ax.plot(curve["capacity"], curve["expected_net_value"], color=BLUE, lw=2)
ax.scatter([B], [opt["expected_net_value"]], color=RED, s=80, zorder=5, label=f"Optimum: {B} units")
ax.axvline(B, color=RED, ls="--", lw=1)
ax.set_xlabel("Capacity (B = S)"); ax.set_ylabel("Expected net value (₹)")
ax.set_title("Expected net value vs. capacity"); ax.grid(alpha=.3); ax.legend()
save(fig, "ev_vs_capacity.png")

# 2 scenario service
sdf = m.scenario_table(B, S, sc, p)
x = np.arange(len(sdf)); w = .38
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].bar(x - w/2, sdf["emergency_served"], w, color=RED, label="Emergency served")
axes[0].bar(x + w/2, sdf["general_served"], w, color=BLUE, label="General served")
axes[0].set_xticks(x); axes[0].set_xticklabels(sdf["scenario"]); axes[0].set_ylabel("Patients")
axes[0].set_title("Patients served"); axes[0].legend(); axes[0].grid(axis="y", alpha=.3)
axes[1].bar(x - w/2, sdf["emergency_unserved"], w, color=RED, label="Emergency unserved")
axes[1].bar(x + w/2, sdf["general_unserved"], w, color=ORANGE, label="General unserved")
axes[1].set_xticks(x); axes[1].set_xticklabels(sdf["scenario"]); axes[1].set_ylabel("Patients")
axes[1].set_title("Patients unserved"); axes[1].legend(); axes[1].grid(axis="y", alpha=.3)
save(fig, "scenario_service.png")

# 3 Monte Carlo distribution
mc = m.monte_carlo(B, S, sc, p, 10000, 42)
vals, cnt = np.unique(mc["values"], return_counts=True)
fig, ax = plt.subplots(figsize=(6.4, 4))
ax.bar([f"₹{v:,.0f}" for v in vals], cnt / cnt.sum(), color=BLUE, width=.5)
for i, c in enumerate(cnt):
    ax.text(i, c / cnt.sum(), f"{c/cnt.sum()*100:.1f}%", ha="center", va="bottom")
ax.set_ylabel("Fraction of simulations"); ax.set_xlabel("Net value of outcome")
ax.set_title("Monte Carlo outcomes (10,000 runs, seed 42)")
save(fig, "monte_carlo.png")

# 4 sensitivity heatmap
bc, scst = m.default_cost_range(p.cost_bed), m.default_cost_range(p.cost_staff)
sens = m.sensitivity_costs(sc, p, bc, scst)
piv = sens.pivot(index="staff_cost", columns="bed_cost", values="effective_capacity")
fig, ax = plt.subplots(figsize=(6.4, 4.2))
im = ax.imshow(piv.values, origin="lower", cmap="Blues", aspect="auto")
ax.set_xticks(range(5)); ax.set_xticklabels([f"{v:,.0f}" for v in piv.columns])
ax.set_yticks(range(5)); ax.set_yticklabels([f"{v:,.0f}" for v in piv.index])
for i in range(5):
    for j in range(5):
        ax.text(j, i, f"{piv.values[i, j]:.0f}", ha="center", va="center",
                color="white" if im.norm(piv.values[i, j]) > .6 else "black")
ax.set_xlabel("Cost per bed unit (₹)"); ax.set_ylabel("Cost per staff unit (₹)")
ax.set_title("Optimal effective capacity under cost changes")
save(fig, "sensitivity_heatmap.png")

# 5 benefit sensitivity
sg = m.sensitivity_one_at_a_time(sc, p, "benefit_general", [250, 500, 750, 1000, 1250, 1500, 2000])
fig, ax = plt.subplots(figsize=(6.4, 4))
ax.plot(sg["benefit_general"], sg["effective_capacity"], "o-", color=BLUE)
ax.set_xlabel("Benefit per general patient (₹)"); ax.set_ylabel("Optimal capacity")
ax.set_title("Optimal capacity vs. general-patient benefit"); ax.grid(alpha=.3)
save(fig, "benefit_sensitivity.png")
print("figures written to", OUT)
