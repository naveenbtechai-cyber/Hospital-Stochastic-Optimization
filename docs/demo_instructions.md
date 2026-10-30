# Demo instructions (about 8-10 minutes)

**Setup (before the viva):** `.venv\Scripts\activate`, then `streamlit run app.py`. Keep the
tests ready: `python -m unittest -v`.

1. **Intro (1 min).** Read the yellow banner: data are illustrative, not for clinical use.
2. **Scenarios (1 min).** Show the table, probabilities sum to 1, expected demand 77.1 patients.
   Try changing a probability so it no longer sums to 1: the app shows an error.
3. **Optimization (2 min).** Show B = 72, S = 72, expected net value ₹56,640. Open the
   "Why was this allocation selected?" box. Explain marginal reasoning: a unit costs ₹430;
   it is worth adding while expected benefit > ₹430 (₹800 up to 72, ₹300 after).
4. **Charts (1 min).** Value-vs-capacity curve peaks at 72. Heat map shows the diagonal ridge:
   beds and staff must match because capacity = min(B, S).
5. **Scenarios (1 min).** High demand: 33 general patients unserved, emergency patients all served.
6. **Monte Carlo (2 min).** Mean about ₹56.5k, 5th percentile ₹29,040, 95th ₹71,040. Change the seed to
   show a slightly different mean; same seed reproduces it. Stress: enumeration picks the optimum,
   Monte Carlo shows variability.
7. **Sensitivity (1 min).** Lower bed/staff costs push capacity to the limit (100); raise the cost
   and it stays at 72 until a threshold. Change the sidebar and watch results update.
8. **Tests (1 min).** Run `python -m unittest -v`: all 41 tests should pass.
9. **Close.** State limitations: three scenarios, one period, hypothetical benefits.
