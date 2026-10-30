"""Build presentation/Hospital_Allocation_Presentation.pptx from real model output.
Run from repo root after tools/make_figures.py:  python tools/build_presentation.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

import model as m

sc, P = m.default_scenarios(), m.Params()
opt = m.optimize(sc, P); B, S = opt["beds"], opt["staff"]
mc = m.monte_carlo(B, S, sc, P, 10000, 42)
sdf = m.scenario_table(B, S, sc, P)
rs = lambda x: f"₹{x:,.0f}"
FIG, SHOT = ROOT / "report" / "figures", ROOT / "screenshots"

NAVY, TEAL, LIGHT, GREY = RGBColor(0x1F, 0x3A, 0x5F), RGBColor(0x1A, 0x8F, 0x9C), RGBColor(0xF3, 0xF6, 0xFA), RGBColor(0x55, 0x5F, 0x6B)
prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
blank = prs.slide_layouts[6]


def text(slide, x, y, w, h, s, size=18, bold=False, color=NAVY, align=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame
    tf.word_wrap = True; p = tf.paragraphs[0]; r = p.add_run(); r.text = s
    r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color; r.font.name = "Calibri"
    if align: p.alignment = align
    return tb


def bullets(slide, x, y, w, h, items, size=20):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run(); r.text = "•  " + it; r.font.size = Pt(size); r.font.color.rgb = RGBColor(0x22, 0x2B, 0x36)
        r.font.name = "Calibri"; p.space_after = Pt(10)


def new_slide(title, n):
    s = prs.slides.add_slide(blank)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.1))
    bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()
    text(s, 0.6, 0.18, 12, 0.8, title, 30, True, RGBColor(255, 255, 255))
    text(s, 0.6, 7.05, 10, 0.35, "Illustrative academic assumptions - not real hospital data - not for clinical use", 11, False, GREY)
    text(s, 12.2, 7.05, 0.8, 0.35, str(n), 11, False, GREY, PP_ALIGN.RIGHT)
    return s


def table(slide, x, y, w, rows, col_w, size=15, row_h=0.5):
    t = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows))).table
    for j, cw in enumerate(col_w): t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.text = str(v); p = c.text_frame.paragraphs[0]
            p.runs[0].font.size = Pt(size); p.runs[0].font.name = "Calibri"
            if i == 0:
                c.fill.solid(); c.fill.fore_color.rgb = NAVY; p.runs[0].font.color.rgb = RGBColor(255, 255, 255); p.runs[0].font.bold = True
            else:
                c.fill.solid(); c.fill.fore_color.rgb = LIGHT if i % 2 else RGBColor(255, 255, 255)
    return t


# 1 title
s = prs.slides.add_slide(blank)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height); bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
text(s, 0.9, 2.0, 11.5, 2.2, "Hospital Resource Allocation under Uncertain Patient Demand Using Stochastic Optimization", 40, True, RGBColor(255, 255, 255))
text(s, 0.9, 4.5, 11, 0.6, "B.Tech Stochastic Decision Making - Mini Project", 22, False, RGBColor(0xBF, 0xD8, 0xE0))
text(s, 0.9, 5.4, 11, 1.0, "[Your Name]  |  [Roll No.]  |  [Department]  |  Guide: [Faculty Name]", 18, False, RGBColor(255, 255, 255))
text(s, 0.9, 6.7, 11.5, 0.4, "All data are illustrative academic assumptions, not real hospital data.", 13, False, RGBColor(0xBF, 0xD8, 0xE0))

# 2 motivation + problem
s = new_slide("Motivation and problem statement", 2)
bullets(s, 0.7, 1.5, 6.1, 5, ["Hospitals must fix beds and staff before knowing how many patients will arrive",
                              "Too little capacity: patients go unserved",
                              "Too much capacity: costly resources sit idle",
                              "Planning on the average hides busy and quiet days"], 22)
card = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.2), Inches(1.6), Inches(5.5), Inches(4.2)); card.fill.solid(); card.fill.fore_color.rgb = LIGHT; card.line.fill.background()
text(s, 7.5, 1.8, 5, 0.5, "Problem", 22, True, TEAL)
text(s, 7.5, 2.4, 4.9, 3.2, "Choose bed capacity B and staff capacity S in advance to maximise the expected net value: patient-care benefit minus resource cost, when demand is uncertain.", 19, False, RGBColor(0x22, 0x2B, 0x36))

# 3 concept
s = new_slide("Stochastic decision making", 3)
bullets(s, 0.7, 1.5, 12, 5, ["Deterministic model: assumes one demand number - ignores risk",
                             "Stochastic model: demand is random, described by scenarios with probabilities",
                             "Decide first, observe demand later; judge a decision by its expected outcome E[V] = Σ pᵢ Vᵢ",
                             "Also examine the spread of outcomes: Monte Carlo simulation",
                             "Check robustness: sensitivity analysis"], 24)

# 4 scenarios
s = new_slide("Demand scenarios (illustrative)", 4)
table(s, 0.7, 1.6, 7.6, [["Scenario", "Probability", "General", "Emergency"]] + [[x.name, f"{x.probability:.2f}", x.general, x.emergency] for x in sc], [2.5, 1.9, 1.5, 1.7], 18, 0.6)
ed = m.expected_demand(sc)
text(s, 0.7, 4.4, 7.6, 0.6, f"Expected demand: {ed['general']:.1f} general + {ed['emergency']:.1f} emergency = {ed['total']:.1f} patients", 18, True)
table(s, 8.8, 1.6, 4.0, [["Parameter", "Value"], ["Benefit / general", rs(P.benefit_general)], ["Benefit / emergency", rs(P.benefit_emergency)], ["Cost / bed unit", rs(P.cost_bed)], ["Cost / staff unit", rs(P.cost_staff)], ["Limits (B, S)", "0 to 100"]], [2.4, 1.6], 15, 0.55)
text(s, 0.7, 5.3, 12, 0.9, "Benefits are hypothetical rupee-equivalent scores, not valuations of patient health or lives.", 16, False, GREY)

# 5 math
s = new_slide("Mathematical model", 5)
bullets(s, 0.7, 1.4, 12, 3.4, ["Decision variables: B (beds), S (staff units), integers with 0 ≤ B ≤ 100, 0 ≤ S ≤ 100",
                               "Effective capacity: C = min(B, S)",
                               "Emergency first: eᵢ = min(Eᵢ, C),  then general: gᵢ = min(Gᵢ, C − eᵢ)",
                               "Scenario value: V = eᵢ·2500 + gᵢ·1000 − 250·B − 180·S"], 22)
card = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.7), Inches(5.0), Inches(12), Inches(1.5)); card.fill.solid(); card.fill.fore_color.rgb = LIGHT; card.line.fill.background()
text(s, 1.0, 5.15, 11.4, 0.5, "Objective", 18, True, TEAL)
text(s, 1.0, 5.65, 11.4, 0.7, "maximise  E[V(B,S)] = Σ pᵢ · V(B,S,Dᵢ)     subject to  Σ pᵢ = 1,  pᵢ ≥ 0", 22, True)

# 6 algorithm
s = new_slide("Optimization algorithm: exact enumeration", 6)
steps = ["Validate inputs", "Enumerate all (B, S)", "Compute E[V] for each", "Pick the maximum", "Break down by scenario"]
for i, t in enumerate(steps):
    x = 0.6 + i * 2.5
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(1.7), Inches(2.2), Inches(1.3)); b.fill.solid(); b.fill.fore_color.rgb = TEAL if i % 2 == 0 else NAVY; b.line.fill.background()
    tf = b.text_frame; tf.word_wrap = True; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = t; r.font.size = Pt(18); r.font.bold = True; r.font.color.rgb = RGBColor(255, 255, 255)
bullets(s, 0.7, 3.5, 12, 3.2, [f"{opt['n_combinations_checked']:,} feasible allocations evaluated - the answer is computed, never hard-coded",
                               "Ties broken by lower cost; a loop-based version cross-checks the vectorised optimizer in the tests",
                               "Since C = min(B, S), the optimum balances beds and staff (B = S)",
                               "Hand check: a capacity unit costs ₹430; it earns ≥ ₹800 expected up to unit 72, only ₹300 after"], 20)

# 7 dashboard screenshots
s = new_slide("Dashboard (real screenshots of the running app)", 7)
s.shapes.add_picture(str(SHOT / "05_optimization_results.png"), Inches(0.5), Inches(1.4), width=Inches(7.0))
s.shapes.add_picture(str(SHOT / "06_value_charts.png"), Inches(7.8), Inches(1.4), width=Inches(5.0))
text(s, 0.5, 5.6, 7.0, 1.2, "Left: optimization results panel. Right: expected-value charts. Captured from the running Streamlit app with default inputs.", 15, False, GREY)

# 8 results
s = new_slide("Results", 8)
table(s, 0.6, 1.5, 5.8, [["Quantity", "Result"], ["Recommended B / S", f"{B} / {S}"], ["Expected benefit", rs(opt["expected_benefit"])], ["Resource cost", rs(opt["resource_cost"])], ["Expected net value", rs(opt["expected_net_value"])], ["Expected served / unserved", f"{opt['expected_served']:.1f} / {opt['expected_unserved']:.1f}"]], [3.3, 2.5], 16, 0.55)
table(s, 0.6, 5.0, 5.8, [["Scenario", "Service rate", "Unserved"]] + [[r.scenario, f"{r.service_rate*100:.1f}%", r.total_unserved] for r in sdf.itertuples()], [2.4, 1.9, 1.5], 14, 0.38)
s.shapes.add_picture(str(FIG / "ev_vs_capacity.png"), Inches(6.8), Inches(1.5), width=Inches(6.1))
text(s, 6.8, 5.4, 6.1, 1.2, "Expected net value peaks at 72 units. High demand leaves 33 general patients unserved; all emergency patients are served.", 16, False, GREY)

# 9 MC + sensitivity
s = new_slide("Monte Carlo risk and sensitivity analysis", 9)
s.shapes.add_picture(str(FIG / "monte_carlo.png"), Inches(0.5), Inches(1.4), width=Inches(6.1))
s.shapes.add_picture(str(FIG / "sensitivity_heatmap.png"), Inches(6.8), Inches(1.4), width=Inches(6.1))
text(s, 0.6, 5.2, 6.0, 1.7, f"10,000 runs, seed 42: mean {rs(mc['mean'])}, std {rs(mc['std'])}, 5th pct {rs(mc['p5'])}, 95th pct {rs(mc['p95'])}. Enumeration picks the optimum; Monte Carlo shows variability.", 15, False, RGBColor(0x22, 0x2B, 0x36))
text(s, 6.9, 5.2, 6.0, 1.7, "Cost ±50%, re-optimised for each pair: capacity stays 72 over a wide range and jumps to the 100-unit limit when costs are low.", 15, False, RGBColor(0x22, 0x2B, 0x36))

# 10 limitations + conclusion
s = new_slide("Limitations and conclusion", 10)
text(s, 0.7, 1.4, 5.8, 0.5, "Limitations", 24, True, TEAL)
bullets(s, 0.7, 2.0, 5.8, 4.5, ["Only three scenarios, one period", "No queues, stays or staff types", "Hypothetical benefits and constant costs", "Not validated on real data; not for clinical use"], 18)
text(s, 7.0, 1.4, 5.8, 0.5, "Conclusion", 24, True, TEAL)
bullets(s, 7.0, 2.0, 5.8, 4.5, [f"Stochastic model gives B = S = {B}, expected net value {rs(opt['expected_net_value'])}", "Expected value alone hides risk: Monte Carlo shows the spread", "Decision is stable over a cost range, then changes in steps", "41 automated tests; future work: richer demand, multi-period, risk-averse objectives"], 18)

out = ROOT / "presentation" / "Hospital_Allocation_Presentation.pptx"
prs.save(out); print("saved", out)
