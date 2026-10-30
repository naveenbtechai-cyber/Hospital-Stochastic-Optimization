# Hospital Resource Allocation under Uncertain Patient Demand Using Stochastic Optimization

B.Tech Stochastic Decision Making mini project. A Python + Streamlit application that chooses
hospital **bed** and **staff-capacity** levels when future patient demand is uncertain.

> **Academic exercise only.** All demand numbers, probabilities, benefits and costs are
> **illustrative assumptions**, not real hospital data. Benefit values are hypothetical
> rupee-equivalent scores, **not** monetary valuations of patient health or lives. The tool must
> not be used for real clinical or hospital decisions.

## Objectives
- Model demand uncertainty with a discrete probability distribution (scenarios).
- Formulate and solve a stochastic optimization problem by **exact enumeration**.
- Quantify risk with **Monte Carlo simulation**.
- Study robustness with **sensitivity analysis** and **scenario analysis**.
- Present everything in an interactive dashboard.

## Features
- Editable demand scenarios with validation (probabilities must sum to 1, no negative demand).
- Exact optimum over every integer (B, S) pair; nothing is hard-coded.
- Expected benefit, cost, net value, expected served / unserved patients.
- Charts: value vs. capacity, full B x S heat map, served / unserved by scenario, Monte Carlo
  distribution, sensitivity heat maps and benefit-sensitivity curves.
- Monte Carlo with reproducible seed (mean, std, median, 5th and 95th percentile).
- Cost sensitivity grid that re-optimises for each combination; results update with the sidebar.
- 41 automated unit tests.

## Mathematical formulation
Decision variables: `B` (bed units), `S` (staff units), integers with `0 <= B <= Bmax`, `0 <= S <= Smax`.
Effective capacity: `C = min(B, S)`.

For demand scenario `i` with `E_i` emergency and `G_i` general patients (emergency served first):

```
emergency served  e_i = min(E_i, C)
general served    g_i = min(G_i, C - e_i)
V(B,S,D_i) = e_i * benefit_E + g_i * benefit_G - cost_B * B - cost_S * S
```

Objective: `maximize  E[V(B,S)] = sum_i p_i * V(B,S,D_i)`, with `sum_i p_i = 1`, `p_i >= 0`.

Because `C = min(B, S)`, extra beds without extra staff (or vice versa) cost money and serve nobody, so
the optimum has `B = S`. Ties in expected value are broken by lower total cost.

### Illustrative inputs
| Scenario | Probability | General patients | Emergency patients |
|---|---|---|---|
| Low demand | 0.20 | 40 | 8 |
| Normal demand | 0.50 | 60 | 12 |
| High demand | 0.30 | 85 | 20 |

Benefit per general patient ₹1,000; per emergency patient ₹2,500; cost per bed unit ₹250;
cost per staff unit ₹180; limits 100 beds and 100 staff units (all illustrative).

## Example results (produced by the actual program with the defaults above)
| Quantity | Value |
|---|---|
| Recommended allocation | B = 72, S = 72 (effective capacity 72) |
| Expected patient-care benefit | ₹87,600 |
| Resource cost | ₹30,960 |
| **Expected net value** | **₹56,640** |
| Expected patients served / unserved | 67.2 / 9.9 |
| Combinations checked | 10,201 |

Scenario outcomes at B = S = 72: Low and Normal demand are fully served (100%); High demand serves
20 emergency + 52 general patients (68.6%), leaving 33 general patients unserved.

Monte Carlo (10,000 runs, seed 42): mean ₹56,468, std ₹14,793, median ₹59,040,
5th percentile ₹29,040, 95th percentile ₹71,040 (exact expected value ₹56,640).

Hand check: each extra unit of capacity costs ₹430. Units 1-72 add expected benefit of at least ₹800
(they are used in Normal and High demand, which have probability 0.8, at ₹1,000 or more), but unit 73+
is used only in High demand: 0.3 x ₹1,000 = ₹300 < ₹430. So 72 is optimal.

Your numbers will match these if you keep the default inputs. Screenshots of the running dashboard
are in `screenshots/`.

## Technologies
Python 3.10+, Streamlit, NumPy, Pandas, Matplotlib, `unittest`.

## Installation and running (Windows)
Open **Command Prompt** or PowerShell in the project folder:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
(PowerShell may need `Set-ExecutionPolicy -Scope Process RemoteSigned` before activating.)
Streamlit opens `http://localhost:8501`.

## Running the tests
```bat
python -m unittest -v
```

## Regenerating figures, report and slides (optional)
```bat
pip install -r requirements-docs.txt
python tools/make_figures.py
python tools/build_report.py
python tools/build_presentation.py
```

## Repository structure
```
Hospital-Stochastic-Optimization/
├── app.py                    Streamlit dashboard
├── model.py                  Mathematical model, optimizer, Monte Carlo, sensitivity
├── test_model.py             41 unit tests
├── requirements.txt          Runtime dependencies
├── requirements-docs.txt     Extra deps to rebuild report/slides
├── data/demand_scenarios.csv Illustrative demand scenarios
├── docs/                     report outline, viva questions, demo instructions
├── report/                   Word report + figures
├── presentation/             PowerPoint slides
├── screenshots/              Real dashboard screenshots
├── tools/                    Scripts that generate figures, report and slides
├── .gitignore
└── LICENSE
```

## Assumptions and limitations
- Only three demand scenarios; real demand is continuous and time-dependent.
- A single time period; no patient stays, queues, arrivals over time, or length of stay.
- Beds and staff are interchangeable units with capacity `min(B, S)`; no staff skill types.
- Benefits are hypothetical scores; costs are assumed constants.
- Unserved patients incur no explicit penalty (only lost benefit).
- Not validated against any real hospital data; not for clinical use.

## License
MIT (see `LICENSE`; replace the placeholder name with yours).
