# Viva questions and answers

1. **What is stochastic optimization?** Optimization where some inputs (here patient demand) are random. We choose a decision before knowing the outcome and optimise its expected (or risk-adjusted) result.
2. **Why is the problem stochastic and not deterministic?** Future demand is unknown. A deterministic model would assume one demand number and could badly over- or under-provide capacity.
3. **What is a scenario?** One possible future, here a combination of general and emergency patient numbers with a probability (Low, Normal, High demand).
4. **What is a discrete probability distribution?** A list of possible outcomes with probabilities that are non-negative and sum to 1 (0.2 + 0.5 + 0.3 = 1).
5. **What is expected value?** The probability-weighted average of outcomes: E[V] = Σ pᵢVᵢ. It is the long-run average if the situation repeated many times.
6. **What are the decision variables?** B (bed units) and S (staff units), non-negative integers within limits.
7. **What is effective capacity and why min(B, S)?** A patient needs both a bed and staff, so the scarcer resource limits service. Extra beds without staff serve nobody.
8. **Why does the optimum have B = S?** Any extra unit of one resource beyond the other adds cost but no service, so it can only lower the objective.
9. **What does emergency-first mean?** Capacity is first given to emergency patients; leftover capacity serves general patients. This reflects medical priority and the higher benefit per emergency patient.
10. **What is the objective function?** Maximise expected net value = expected patient-care benefit minus bed and staff costs.
11. **What constraints do you have?** Integer bounds 0 ≤ B ≤ Bmax, 0 ≤ S ≤ Smax, non-negative demand, probabilities in [0,1] summing to 1.
12. **How do you solve it?** Exact enumeration: evaluate every feasible (B, S) pair and take the one with the highest expected net value. For 101 × 101 pairs that is 10,201 evaluations, which is instant.
13. **Is enumeration always practical?** Not for huge problems (it grows with the number of combinations). For larger models one would use integer programming or heuristics.
14. **What did the program find with the default data?** B = S = 72, expected net value ₹56,640 (computed, not hard-coded). Hand check: each extra unit costs ₹430; up to 72 units it earns at least ₹800 expected, afterwards only ₹300.
15. **What is Monte Carlo simulation?** Repeatedly sampling random demand scenarios by their probabilities and computing the outcome for a fixed allocation. It estimates the mean and spread of outcomes.
16. **Why use Monte Carlo if we already have the exact expected value?** The exact value gives only the average. Monte Carlo shows variability and risk (std. deviation, 5th and 95th percentiles).
17. **Why a random seed?** To make results reproducible; the same seed gives the same random draws.
18. **Why does the Monte Carlo mean differ slightly from the exact value?** Sampling error; it shrinks as the number of simulations grows.
19. **What is sensitivity analysis?** Changing an input (costs, benefits) and re-optimising to see how robust the decision is.
20. **What did sensitivity show?** The optimal capacity changes in steps: it stays 72 across a range of costs, then jumps (e.g. to the 100 limit when costs are low).
21. **Are the benefits real money?** No. They are hypothetical rupee-equivalent scores for an academic exercise, not valuations of patient health or lives.
22. **What are the limitations?** Three scenarios, one time period, no queues or length of stay, no staff types, assumed constants, no real data, not for clinical use.
23. **How could you improve it?** More scenarios or continuous distributions, multi-period model, risk measures such as CVaR, penalties for unserved patients, real data, integer programming.
24. **How did you verify correctness?** 41 unit tests, a hand-solvable two-scenario example, a brute-force loop cross-check against the vectorised optimizer, and a manual marginal-analysis argument for the default case.
