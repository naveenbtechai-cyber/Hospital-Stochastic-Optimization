"""Build report/Hospital_Allocation_Report.docx from real model output.
Run from repo root after tools/make_figures.py:  python tools/build_report.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

import model as m

sc, P = m.default_scenarios(), m.Params()
opt = m.optimize(sc, P)
B, S = opt["beds"], opt["staff"]
sdf = m.scenario_table(B, S, sc, P)
mc = m.monte_carlo(B, S, sc, P, 10000, 42)
ed = m.expected_demand(sc)
sens = m.sensitivity_costs(sc, P, m.default_cost_range(P.cost_bed), m.default_cost_range(P.cost_staff))
FIG = ROOT / "report" / "figures"
rs = lambda x: f"₹{x:,.0f}"

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)  # A4
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Inches(1))

st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
st.paragraph_format.space_after = Pt(6); st.paragraph_format.line_spacing = 1.15
for name, size in (("Heading 1", 16), ("Heading 2", 13)):
    h = doc.styles[name]; h.font.name = "Calibri"; h.font.size = Pt(size)
    h.font.bold = True; h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    h.element.rPr.rFonts.set(qn("w:asciiTheme"), "minorHAnsi") if False else None


def para(text, bold=False, italic=False, align=None, size=None):
    p = doc.add_paragraph(); r = p.add_run(text); r.bold = bold; r.italic = italic
    if size: r.font.size = Pt(size)
    if align: p.alignment = align
    return p


def bullets(items):
    for t in items:
        doc.add_paragraph(t, style="List Bullet")


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def table(header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h)
        r.bold = True; r.font.size = Pt(10); r.font.color.rgb = RGBColor(255, 255, 255); shade(c, "1F3A5F")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(10)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def figure(name, width, caption):
    doc.add_picture(str(FIG / name), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    c = para(caption, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=9)


def equation(text):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text); r.font.name = "Cambria Math"; r.italic = True


# ------------------------------------------------------------ title page
for _ in range(5): doc.add_paragraph()
para("Hospital Resource Allocation under Uncertain Patient Demand Using Stochastic Optimization",
     bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=22)
para("Mini Project Report - Stochastic Decision Making", align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
doc.add_paragraph()
para("Bachelor of Technology", align=WD_ALIGN_PARAGRAPH.CENTER, size=13)
for _ in range(3): doc.add_paragraph()
for line in ("Submitted by: [Your Name]", "Roll number: [Roll No.]", "Department: [Department]",
             "Institution: [College / University]", "Guide / Faculty: [Faculty Name]",
             "Academic year: [Year]"):
    para(line, align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
doc.add_paragraph()
para("Note: all data in this report are illustrative academic assumptions, not real hospital data.",
     italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10)
doc.add_page_break()

# ------------------------------------------------------------ 1 abstract
doc.add_heading("Abstract", 1)
para("Hospitals must decide how many beds and staff to provide before the number of arriving patients is "
     "known. This project models that decision as a stochastic optimization problem. Future demand is "
     "represented by three discrete scenarios (low, normal and high) with given probabilities. The "
     "decision variables are bed capacity B and staff capacity S, and the effective capacity is min(B, S). "
     "Emergency patients are served first, and the objective is to maximise the expected net value, "
     "defined as patient-care benefit minus resource cost. The problem is solved exactly by enumerating "
     f"all integer allocations. With the illustrative inputs, the program selects B = {B} and S = {S}, with an "
     f"expected net value of {rs(opt['expected_net_value'])}. Monte Carlo simulation of 10,000 demand draws shows "
     f"the variability of this decision (5th to 95th percentile: {rs(mc['p5'])} to {rs(mc['p95'])}), and sensitivity "
     "analysis shows how the decision changes with resource costs and benefit values. A Streamlit "
     "dashboard and 41 automated tests accompany the model. All numbers are hypothetical.")
para("Keywords: stochastic optimization, expected value, scenario analysis, Monte Carlo simulation, "
     "sensitivity analysis, hospital capacity.", italic=True)

# ------------------------------------------------------------ 2 intro
doc.add_heading("1. Introduction", 1)
para("Healthcare demand fluctuates from day to day. Too little capacity leaves patients untreated, while "
     "too much capacity wastes expensive resources. A plan built on the average demand alone ignores the "
     "possibility of busy and quiet periods. Stochastic decision making addresses this by describing "
     "the uncertainty with probabilities and choosing the decision that performs best on average, while "
     "also examining the risk around that average.")
para("This mini project builds a small, transparent model of the problem and implements it in Python. "
     "It is a teaching example: the numbers are illustrative, the model is simple, and it is not "
     "intended for real clinical or hospital decisions.")

doc.add_heading("2. Problem Statement", 1)
para("Given uncertain demand for general and emergency patient care, determine the number of bed units "
     "B and staff-capacity units S to allocate in advance so that the expected net value is maximised, "
     "where net value is the benefit of treating patients minus the cost of the allocated resources.")

doc.add_heading("3. Objectives", 1)
bullets(["Model uncertain patient demand with a discrete probability distribution.",
         "Formulate the allocation problem mathematically with decision variables, constraints and an objective.",
         "Find the optimal allocation by exact enumeration, without hard-coding the answer.",
         "Assess risk and variability of the chosen allocation with Monte Carlo simulation.",
         "Study the effect of changing costs and benefits through sensitivity analysis.",
         "Provide an interactive dashboard and a tested, reproducible implementation."])

# ------------------------------------------------------------ assumptions
doc.add_heading("4. Assumptions and Demand Data", 1)
para("All values below are illustrative academic assumptions. The benefit values are hypothetical "
     "rupee-equivalent scores used to compare outcomes; they are not monetary valuations of patient "
     "health or lives.")
table(["Scenario", "Probability", "General patients", "Emergency patients"],
      [[s.name, f"{s.probability:.2f}", s.general, s.emergency] for s in sc], [2, 1.3, 1.6, 1.7])
table(["Parameter", "Assumed value"],
      [["Benefit per general patient served", rs(P.benefit_general)],
       ["Benefit per emergency patient served", rs(P.benefit_emergency)],
       ["Cost per bed-capacity unit", rs(P.cost_bed)],
       ["Cost per staff-capacity unit", rs(P.cost_staff)],
       ["Maximum beds / staff units (search limits)", f"{P.max_beds} / {P.max_staff}"]], [3.6, 2.4])
para(f"Expected demand is {ed['general']:.1f} general and {ed['emergency']:.1f} emergency patients "
     f"({ed['total']:.1f} in total).")
bullets(["Single planning period; no queues, arrivals over time or length of stay.",
         "A patient needs both a bed and staff, so capacity is min(B, S).",
         "Emergency patients are served before general patients.",
         "Unserved patients only lose benefit; no explicit penalty is added."])

# ------------------------------------------------------------ math
doc.add_heading("5. Mathematical Formulation", 1)
para("Decision variables: B = bed capacity allocated and S = staff-capacity units allocated, both "
     "non-negative integers. Effective capacity:")
equation("C = min(B, S)")
para("For demand scenario i with Eᵢ emergency and Gᵢ general patients, the emergency-first rule gives:")
equation("eᵢ = min(Eᵢ, C)          gᵢ = min(Gᵢ, C − eᵢ)")
para("Unserved patients are (Eᵢ − eᵢ) emergency and (Gᵢ − gᵢ) general. The scenario value is:")
equation("V(B, S, Dᵢ) = eᵢ · bE + gᵢ · bG − cB · B − cS · S")
para("where bE and bG are the benefits per emergency and general patient and cB and cS are the costs per "
     "bed and staff unit.")

doc.add_heading("6. Constraints and Objective Function", 1)
equation("maximise  E[V(B, S)] = Σᵢ pᵢ · V(B, S, Dᵢ)")
para("subject to:")
bullets(["B and S are integers with 0 ≤ B ≤ Bmax and 0 ≤ S ≤ Smax.",
         "pᵢ ≥ 0 for every scenario and Σᵢ pᵢ = 1.",
         "Demand values Gᵢ, Eᵢ ≥ 0."])
para("Interaction of beds and staff: because the number of patients served depends only on min(B, S), "
     "a unit of one resource above the other adds cost but no benefit, so the optimum always has B = S "
     "when costs are positive. Marginal reasoning gives a useful check: with B = S, adding the k-th unit "
     "of capacity costs cB + cS and earns, in each scenario, the benefit of the patient who would use "
     "that unit (emergency benefit if k ≤ Eᵢ, general benefit if k ≤ Eᵢ + Gᵢ, otherwise nothing). "
     "Capacity should be increased while this expected benefit exceeds cB + cS.")

# ------------------------------------------------------------ method
doc.add_heading("7. Methodology and Workflow", 1)
bullets(["Validate the scenarios and parameters (probabilities sum to one, no negative values).",
         "Enumerate every integer pair (B, S) within the limits and compute its expected net value.",
         "Select the pair with the highest expected net value (ties: lower cost, then smaller B and S).",
         "Break the chosen allocation down by scenario: patients served, unserved, service rate.",
         "Run Monte Carlo simulation of the fixed allocation to measure variability.",
         "Re-optimise under changed costs and benefits (sensitivity analysis)."])

doc.add_heading("8. System Architecture", 1)
table(["File", "Role"],
      [["model.py", "Data classes, validation, scenario evaluation, exact optimizer, Monte Carlo, sensitivity"],
       ["app.py", "Streamlit dashboard (inputs, results, charts) using model.py"],
       ["test_model.py", "41 unit tests (unittest)"],
       ["data/demand_scenarios.csv", "Illustrative scenario data loaded by the dashboard"],
       ["tools/", "Scripts that generate figures, this report and the slides"]], [2.2, 4.0])

doc.add_heading("9. Implementation Details", 1)
bullets(["Python with NumPy, Pandas and Matplotlib; Streamlit for the interface.",
         "The optimizer evaluates all (B, S) pairs in one vectorised NumPy computation; a slower loop-based "
         "version using the scalar scenario function is used in the tests to cross-check it.",
         "Monte Carlo uses numpy.random.default_rng(seed) so results are reproducible.",
         "Streamlit caching keeps the dashboard responsive when widgets change.",
         "Nothing about the optimum is hard-coded; it is recomputed whenever inputs change."])

# ------------------------------------------------------------ results
doc.add_heading("10. Results and Discussion", 1)
para("All figures in this section are computed by the program from the illustrative inputs above.")
table(["Quantity", "Result"],
      [["Recommended beds B / staff S", f"{B} / {S}"],
       ["Effective capacity", opt["effective_capacity"]],
       ["Expected patient-care benefit", rs(opt["expected_benefit"])],
       ["Resource cost", rs(opt["resource_cost"])],
       ["Expected net value", rs(opt["expected_net_value"])],
       ["Expected patients served / unserved", f"{opt['expected_served']:.1f} / {opt['expected_unserved']:.1f}"],
       ["Allocations evaluated", f"{opt['n_combinations_checked']:,}"]], [3.6, 2.4])
para(f"Hand verification: each extra unit of capacity costs {rs(P.cost_bed + P.cost_staff)}. For units up to "
     "72, the expected benefit is at least ₹800 (the unit is used in Normal and High demand, probability 0.8, "
     "at ₹1,000 or more); unit 73 onward is used only in High demand, worth 0.3 × ₹1,000 = ₹300, which is below "
     "the cost. Hence 72 is optimal, in agreement with the program.")
figure("ev_vs_capacity.png", 4.6, "Figure 1: Expected net value versus capacity (B = S), computed by the program.")

doc.add_heading("Scenario comparison", 2)
table(["Scenario", "Emerg. served", "General served", "Unserved", "Service rate", "Net value"],
      [[r.scenario, r.emergency_served, r.general_served, r.total_unserved,
        f"{r.service_rate*100:.1f}%", rs(r.net_value)] for r in sdf.itertuples()],
      [1.4, 1.0, 1.1, 0.9, 1.0, 1.0])
figure("scenario_service.png", 5.8, "Figure 2: Patients served and unserved in each demand scenario.")
para("Low and Normal demand are fully served. In High demand all emergency patients are still served "
     "because of the priority rule, but 33 general patients cannot be served. The allocation is therefore "
     "sized for the expected demand mix rather than the worst case.")

doc.add_heading("Comparison with other allocations", 2)
rows = []
for b_, s_ in [(48, 48), (60, 60), (72, 72), (85, 85), (100, 100), (72, 50)]:
    e = m.expected_summary(b_, s_, sc, P)
    rows.append([f"B={b_}, S={s_}", rs(e["expected_net_value"]), f"{e['expected_unserved']:.1f}"])
table(["Allocation", "Expected net value", "Expected unserved"], rows, [2.2, 2.0, 1.8])
para("Larger allocations reduce unserved patients but their extra cost outweighs the extra benefit; the "
     "mismatched allocation B=72, S=50 is worse because the 22 surplus beds are paid for but unusable.")

# ------------------------------------------------------------ MC
doc.add_heading("11. Monte Carlo Risk Analysis", 1)
para("Exact enumeration chooses the optimal allocation. Monte Carlo simulation does not search for a "
     "better one; it samples demand scenarios according to their probabilities and records the net "
     "value of the fixed allocation, illustrating its variability.")
table(["Statistic (10,000 runs, seed 42)", "Value"],
      [["Mean", rs(mc["mean"])], ["Standard deviation", rs(mc["std"])], ["Median", rs(mc["median"])],
       ["5th percentile", rs(mc["p5"])], ["95th percentile", rs(mc["p95"])],
       ["Exact expected value", rs(opt["expected_net_value"])]], [3.6, 2.4])
figure("monte_carlo.png", 4.6, "Figure 3: Distribution of simulated net values (discrete, three scenarios).")
para("The simulated mean is close to the exact expected value; the small gap is sampling error. The wide "
     "spread shows that the actual outcome on a given day can be well below the average (Low demand gives "
     f"{rs(float(sdf.net_value.min()))}), so the expected value alone hides risk.")

# ------------------------------------------------------------ sens
doc.add_heading("12. Sensitivity Analysis", 1)
para("Bed and staff costs were varied by ±50% around the base values and the problem was re-optimised "
     "for each of the 25 combinations.")
figure("sensitivity_heatmap.png", 4.6, "Figure 4: Optimal effective capacity for different bed and staff costs.")
lo, hi = sens["effective_capacity"].min(), sens["effective_capacity"].max()
para(f"The optimal capacity ranges from {lo} to {hi} units. The decision changes in steps rather than "
     "smoothly: it stays at 72 while the cost per capacity unit is below ₹800 and above ₹300, and moves "
     "to the 100-unit search limit when costs fall below ₹300 (because unit 73 onward then pays for "
     "itself). The expected net value, however, changes continuously with cost. Varying the benefit per "
     "general patient shows the same stepwise pattern, while the emergency benefit does not change the "
     "optimal capacity in the tested range because emergency patients are always worth serving.")
figure("benefit_sensitivity.png", 4.4, "Figure 5: Optimal capacity versus benefit per general patient.")

# ------------------------------------------------------------ rest
doc.add_heading("13. Limitations", 1)
bullets(["Only three demand scenarios; real demand is continuous and varies over time.",
         "Single period; no patient flow, queues, length of stay or day-to-day carry-over.",
         "Beds and staff are treated as interchangeable units without skill types or shifts.",
         "Benefits are hypothetical scores and costs are constants; nothing is calibrated to real data.",
         "Search limit of 100 units can be binding when costs are low.",
         "Not suitable for any real clinical or hospital decision."])
doc.add_heading("14. Future Improvements", 1)
bullets(["Richer demand distributions (Poisson or fitted to data) and more scenarios.",
         "Multi-period and two-stage stochastic programming with recourse (e.g. overtime or transfers).",
         "Risk-averse objectives such as CVaR or penalties for unserved emergency patients.",
         "Separate bed types and staff roles; integer-programming solvers for larger problems."])
doc.add_heading("15. Conclusion", 1)
para(f"The project formulated hospital capacity allocation under uncertain demand as a stochastic "
     f"optimization problem and solved it exactly. For the illustrative inputs the best allocation is "
     f"B = S = {B}, with expected net value {rs(opt['expected_net_value'])}. Monte Carlo analysis showed "
     "considerable outcome variability around this expected value, and sensitivity analysis showed that "
     "the decision is stable over a range of costs but changes in steps beyond thresholds. The model, "
     "dashboard and tests are consistent and reproducible; the results illustrate the method and are not "
     "real hospital findings.")
doc.add_heading("16. References", 1)
for ref in ["J. R. Birge and F. Louveaux, Introduction to Stochastic Programming, 2nd ed., Springer, 2011.",
            "A. Shapiro, D. Dentcheva and A. Ruszczyński, Lectures on Stochastic Programming: Modeling and Theory, 2nd ed., SIAM, 2014.",
            "C. R. Harris et al., 'Array programming with NumPy', Nature, vol. 585, pp. 357-362, 2020.",
            "Streamlit documentation, https://docs.streamlit.io",
            "J. D. Hunter, 'Matplotlib: A 2D graphics environment', Computing in Science & Engineering, vol. 9, no. 3, pp. 90-95, 2007."]:
    doc.add_paragraph(ref, style="List Number")
para("Please verify reference details against your library or publisher listings before submission.",
     italic=True, size=9)

# page numbers
footer = sec.footer.paragraphs[0]; footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer.add_run()
for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
    if tag:
        el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), tag)
    else:
        el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = text
    run._r.append(el)

out = ROOT / "report" / "Hospital_Allocation_Report.docx"
doc.save(out); print("saved", out)
