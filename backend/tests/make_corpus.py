"""Generate structurally diverse manuscripts for template-agnostic parser tests.

Each document below deliberately uses a *different* convention for the same
logical content, mirroring how Springer, IEEE, Elsevier, MDPI, a university
thesis and a plain Word manuscript actually lay a paper out.  None of them uses
the target journal's formatting, and several use no Word heading styles at all.

Run:  python3 tests/make_corpus.py
"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.oxml import parse_xml

OUT = Path(__file__).resolve().parent / "corpus"

M = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _run(text, sty=None):
    sty = f"<m:rPr>{sty}</m:rPr>" if sty else ""
    return f"<m:r {M} {W}>{sty}<m:t>{text}</m:t></m:r>"


def frac(num, den):
    return (f'<m:f {M}><m:fPr><m:type m:val="bar"/></m:fPr>'
            f"<m:num>{num}</m:num><m:den>{den}</m:den></m:f>")


def nary(char, sub, sup, body):
    return (f'<m:nary {M}><m:naryPr><m:chr m:val="{char}"/>'
            f'<m:limLoc m:val="subSup"/></m:naryPr>'
            f"<m:sub>{sub}</m:sub><m:sup>{sup}</m:sup><m:e>{body}</m:e></m:nary>")


def ssub(base, sub):
    return f"<m:sSub {M}><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>"


def ssup(base, sup):
    return f"<m:sSup {M}><m:e>{base}</m:e><m:sup>{sup}</m:sup></m:sSup>"


def matrix(rows):
    body = ""
    for row in rows:
        cells = "".join(f"<m:e>{c}</m:e>" for c in row)
        body += f"<m:mr>{cells}</m:mr>"
    return (f'<m:d {M}><m:dPr><m:begChr m:val="["/><m:endChr m:val="]"/></m:dPr>'
            f"<m:e><m:m>{body}</m:m></m:e></m:d>")


def omath(inner):
    return f"<m:oMath {M} {W}>{inner}</m:oMath>"


def omath_para(inner):
    """Display equation: an oMathPara wrapper is how Word marks display math."""
    return f"<m:oMathPara {M} {W}>{omath(inner)}</m:oMathPara>"


def add_math_para(doc, inner, trailing_number=None, display=True):
    p = doc.add_paragraph()
    p._p.append(parse_xml(omath_para(inner) if display else omath(inner)))
    if trailing_number:
        p.add_run(f"\t({trailing_number})")
    return p


def add_inline_math(doc, before, inner, after):
    p = doc.add_paragraph()
    p.add_run(before)
    p._p.append(parse_xml(omath(inner)))
    p.add_run(after)
    return p


def styled(doc, text, size=None, bold=False, align=None, italic=False, caps=False):
    p = doc.add_paragraph()
    r = p.add_run(text.upper() if caps else text)
    r.bold = bold
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    if align:
        p.alignment = align
    return p


CENTER = WD_ALIGN_PARAGRAPH.CENTER


# --------------------------------------------------------------------------
def plain_word():
    """Plain Word manuscript: no heading styles at all, unnumbered headings,
    heading-ness expressed only as bold + larger font."""
    d = Document()
    styled(d, "Thermal Drift Compensation in Low-Cost MEMS Accelerometers",
           size=18, bold=True, align=CENTER)
    styled(d, "Laura Petersen, Ahmed R. Khalil and Mei-Ling Chou",
           size=12, align=CENTER)
    styled(d, "Department of Mechanical Engineering, Aalborg University, Denmark",
           size=10, italic=True, align=CENTER)
    styled(d, "Corresponding author: l.petersen@mech.aau.dk", size=10, align=CENTER)

    styled(d, "Abstract", size=13, bold=True)
    d.add_paragraph(
        "Low-cost inertial sensors exhibit a bias that drifts substantially with "
        "temperature, which limits their use in long-duration navigation. This "
        "paper develops a compensation model calibrated over a wide thermal "
        "range and evaluates it on three commercial devices. The compensated "
        "bias instability improves by a factor of four across the tested range, "
        "and the residual error remains bounded over eight-hour trials.")
    styled(d, "Keywords: MEMS, inertial navigation, thermal drift, calibration", size=10)

    styled(d, "Introduction", size=14, bold=True)
    d.add_paragraph(
        "Micro-electromechanical accelerometers have become ubiquitous in "
        "consumer and industrial systems because of their cost and size. Their "
        "principal weakness is a bias that varies with die temperature.")
    add_inline_math(d, "The measured specific force is denoted ",
                    ssub(_run("f"), _run("m")), " throughout this work.")

    styled(d, "Model", size=14, bold=True)
    d.add_paragraph("The compensated output is modelled as a polynomial in temperature:")
    add_math_para(d, ssub(_run("f"), _run("c")) + _run("=") + ssub(_run("f"), _run("m"))
                  + _run("-") + nary("&#8721;", ssub(_run("i"), _run("")) + _run("=0"),
                                     _run("n"),
                                     ssub(_run("a"), _run("i"))
                                     + ssup(_run("T"), _run("i"))), "1")
    d.add_paragraph("where the coefficients are estimated by least squares.")
    add_math_para(d, frac(_run("&#8706;b"), _run("&#8706;T")) + _run("=")
                  + frac(_run("&#945;"), _run("1+&#946;T")), "2")

    styled(d, "Results", size=14, bold=True)
    d.add_paragraph("Table 1 summarises the residual bias for each device.")
    t = d.add_table(rows=3, cols=3)
    t.style = "Table Grid"
    for i, row in enumerate([["Device", "Before (mg)", "After (mg)"],
                             ["A", "12.4", "3.1"],
                             ["B", "9.8", "2.6"]]):
        for j, v in enumerate(row):
            t.cell(i, j).text = v
    d.add_paragraph("Table 1. Residual bias before and after compensation.")

    styled(d, "Conclusion", size=14, bold=True)
    d.add_paragraph("A simple polynomial model removes most of the thermal bias.")

    styled(d, "References", size=14, bold=True)
    d.add_paragraph("[1] Groves, P. Principles of GNSS Navigation. Artech House, 2013.")
    d.add_paragraph("[2] Woodman, O. An introduction to inertial navigation. 2007.")
    return d


def ieee_style():
    """IEEE: 'Index Terms' instead of Keywords, numbered ALL-CAPS headings,
    author block with superscript affiliation markers."""
    d = Document()
    styled(d, "A Robust Estimator for Sparse Channel Identification",
           size=20, bold=True, align=CENTER)
    styled(d, "Diego M. Alvarez1, Priya Nair2, and Tomas Bergqvist1",
           size=11, align=CENTER)
    styled(d, "1Signal Processing Group, KTH Royal Institute of Technology, Stockholm, Sweden",
           size=9, align=CENTER)
    styled(d, "2Department of Electrical Engineering, IIT Madras, Chennai, India",
           size=9, align=CENTER)
    styled(d, "Email: alvarez@kth.se", size=9, align=CENTER)

    styled(d, "Abstract—We propose a robust estimator for sparse channel "
              "identification under impulsive noise. The estimator combines an "
              "l1 penalty with a redescending influence function, and we derive "
              "conditions under which the resulting problem remains convex. "
              "Simulations show a 6 dB gain over least squares at moderate "
              "contamination levels.", size=9, bold=False, italic=True)
    styled(d, "Index Terms—sparse estimation, robust statistics, channel "
              "identification, convex optimization", size=9, italic=True)

    styled(d, "I. INTRODUCTION", size=10, bold=True)
    d.add_paragraph(
        "Channel identification underpins equalization and precoding in modern "
        "communication systems. Classical least-squares identification degrades "
        "sharply when the noise departs from Gaussianity.")

    styled(d, "II. PROBLEM FORMULATION", size=10, bold=True)
    d.add_paragraph("We consider the linear observation model below.")
    add_math_para(d, _run("y=Hx+n"), "1")
    d.add_paragraph("The estimator solves the following programme:")
    add_math_para(d, ssub(_run("min"), _run("x")) + _run(" ")
                  + nary("&#8721;", _run("i=1"), _run("N"),
                         _run("&#961;(") + ssub(_run("y"), _run("i")) + _run("-")
                         + ssub(_run("h"), _run("i")) + _run("x)"))
                  + _run("+&#955;&#8741;x&#8741;"), "2")
    add_inline_math(d, "with tuning parameter ", _run("&#955;>0"), " chosen by cross-validation.")

    styled(d, "III. RESULTS", size=10, bold=True)
    d.add_paragraph("The covariance of the estimate is given by the matrix")
    add_math_para(d, matrix([[_run("&#963;&#178;"), _run("0")],
                             [_run("0"), _run("&#963;&#178;")]]), "3")

    styled(d, "REFERENCES", size=10, bold=True)
    d.add_paragraph("[1] P. Huber, Robust Statistics, Wiley, 1981.")
    d.add_paragraph("[2] S. Boyd and L. Vandenberghe, Convex Optimization, CUP, 2004.")
    return d


def springer_style():
    """Springer: author block and affiliations in a TABLE (front-matter table),
    numbered headings with Word Heading styles, abstract label on its own line."""
    d = Document()
    styled(d, "Adaptive Mesh Refinement for Shallow-Water Flows over Complex "
              "Bathymetry", size=17, bold=True)

    t = d.add_table(rows=2, cols=1)
    t.cell(0, 0).text = "Ingrid Sørensen · Kwame Osei · Renata Bianchi"
    t.cell(1, 0).text = ("Institute of Applied Mathematics, University of Bergen, "
                         "Allégaten 41, 5007 Bergen, Norway. "
                         "e-mail: ingrid.sorensen@uib.no")

    styled(d, "Abstract", size=11, bold=True)
    d.add_paragraph(
        "We present an adaptive mesh refinement strategy for the shallow-water "
        "equations over strongly varying bathymetry. The refinement criterion "
        "combines a gradient indicator with a well-balancing residual, and the "
        "scheme preserves lake-at-rest states to machine precision. Benchmarks "
        "on tsunami run-up problems show a threefold reduction in degrees of "
        "freedom at equal accuracy.")
    styled(d, "Keywords Shallow water · Adaptive mesh refinement · "
              "Well-balanced schemes · Finite volume", size=10)

    d.add_heading("1 Introduction", level=1)
    d.add_paragraph(
        "Shallow-water models are the workhorse of coastal hazard assessment. "
        "Resolving the relevant scales uniformly is prohibitively expensive.")

    d.add_heading("2 Governing equations", level=1)
    d.add_paragraph("The system in conservative form reads")
    add_math_para(d, frac(_run("&#8706;h"), _run("&#8706;t")) + _run("+")
                  + frac(_run("&#8706;(hu)"), _run("&#8706;x")) + _run("=0"))
    d.add_heading("2.1 Well-balancing", level=2)
    d.add_paragraph("The source term is discretised so that steady states are preserved.")
    add_math_para(d, nary("&#8747;", ssub(_run("x"), _run("L")),
                          ssub(_run("x"), _run("R")),
                          _run("S(U)dx")), "4")

    d.add_heading("3 Conclusion", level=1)
    d.add_paragraph("The proposed indicator is inexpensive and robust.")

    d.add_heading("References", level=1)
    d.add_paragraph("Toro, E.F.: Shock-Capturing Methods for Free-Surface Flows. Wiley (2001)")
    d.add_paragraph("LeVeque, R.J.: Finite Volume Methods for Hyperbolic Problems. CUP (2002)")
    return d


def elsevier_style():
    """Elsevier: spaced 'A B S T R A C T' heading, 'Corresponding author.'
    footnote convention, headings numbered with a trailing period."""
    d = Document()
    styled(d, "Photocatalytic degradation of micropollutants using doped "
              "titania nanosheets", size=16, bold=True)
    styled(d, "Marta Kowalczyk°, Hiroshi Tanaka, Nadia El-Sayed", size=11)
    styled(d, "Faculty of Chemistry, Jagiellonian University, Kraków, Poland", size=9, italic=True)
    styled(d, "∗ Corresponding author. E-mail address: m.kowalczyk@uj.edu.pl", size=8)

    styled(d, "A B S T R A C T", size=10, bold=True)
    d.add_paragraph(
        "Doped titania nanosheets were synthesised by a template-free route and "
        "evaluated for the degradation of three persistent micropollutants. "
        "Nitrogen doping shifted the absorption edge into the visible region and "
        "raised the apparent rate constant by an order of magnitude relative to "
        "undoped material. Reusability over five cycles was demonstrated without "
        "measurable loss of activity.")
    styled(d, "Keywords: Photocatalysis; Titania; Micropollutants; Visible light", size=9)

    styled(d, "1. Introduction", size=12, bold=True)
    d.add_paragraph(
        "Advanced oxidation processes are attractive for removing trace organic "
        "contaminants that survive conventional treatment.")

    styled(d, "2. Materials and methods", size=12, bold=True)
    styled(d, "2.1. Synthesis", size=11, bold=True)
    d.add_paragraph("Nanosheets were grown hydrothermally at 180 degrees Celsius.")
    styled(d, "2.2. Kinetics", size=11, bold=True)
    d.add_paragraph("Degradation followed pseudo-first-order kinetics:")
    add_math_para(d, _run("ln") + frac(ssub(_run("C"), _run("0")), _run("C"))
                  + _run("=kt"), "1")
    add_inline_math(d, "The half-life is therefore ",
                    frac(_run("ln2"), _run("k")), " for each compound.")

    styled(d, "3. Results and discussion", size=12, bold=True)
    d.add_paragraph("The apparent rate constants are collected in Table 1.")

    styled(d, "References", size=12, bold=True)
    d.add_paragraph("Fujishima, A., Honda, K., 1972. Nature 238, 37-38.")
    return d


def thesis_style():
    """University thesis: chapter-level hierarchy, no abstract label variants,
    long unnumbered front matter, deep subsection nesting."""
    d = Document()
    styled(d, "STOCHASTIC MODELS OF URBAN WATER DEMAND UNDER CLIMATE "
              "UNCERTAINTY", size=16, bold=True, align=CENTER)
    styled(d, "A dissertation submitted in partial fulfilment of the "
              "requirements for the degree of Doctor of Philosophy", size=11, align=CENTER)
    styled(d, "Jonathan A. Whitfield", size=13, bold=True, align=CENTER)
    styled(d, "School of Civil and Environmental Engineering, University of "
              "Auckland, New Zealand", size=10, align=CENTER)
    styled(d, "j.whitfield@auckland.ac.nz", size=10, align=CENTER)

    styled(d, "ABSTRACT", size=13, bold=True, align=CENTER)
    d.add_paragraph(
        "Urban water demand is increasingly difficult to project because both "
        "climate and consumer behaviour are shifting. This thesis develops a "
        "hierarchical stochastic model that separates weather-driven and "
        "structural components of demand, and propagates climate-model "
        "uncertainty through to supply-reliability estimates. The framework is "
        "applied to three New Zealand cities over a forty-year horizon.")
    styled(d, "Key words: water demand; stochastic modelling; climate change", size=10)

    styled(d, "Chapter 1. Introduction", size=14, bold=True)
    d.add_paragraph("Reliable demand projections underpin infrastructure investment.")
    styled(d, "1.1 Background", size=12, bold=True)
    d.add_paragraph("Demand has historically been projected by per-capita extrapolation.")
    styled(d, "1.1.1 Limitations of extrapolation", size=11, bold=True)
    d.add_paragraph("Such methods cannot represent behavioural change.")

    styled(d, "Chapter 2. Methodology", size=14, bold=True)
    d.add_paragraph("Daily demand is decomposed into a base and a weather term.")
    add_math_para(d, ssub(_run("D"), _run("t")) + _run("=")
                  + ssub(_run("&#956;"), _run("t")) + _run("+")
                  + ssub(_run("&#947;"), _run("1"))
                  + ssub(_run("T"), _run("t")) + _run("+")
                  + ssub(_run("&#949;"), _run("t")), "2.1")
    d.add_paragraph("The variance component is modelled hierarchically:")
    add_math_para(d, ssup(_run("&#963;"), _run("2")) + _run("=")
                  + frac(_run("1"), _run("N")) + nary("&#8721;", _run("t=1"), _run("N"),
                                                      ssup(_run("(") + ssub(_run("D"), _run("t"))
                                                           + _run("-&#956;)"), _run("2"))), "2.2")

    styled(d, "Chapter 3. Conclusions", size=14, bold=True)
    d.add_paragraph("The hierarchical model improves reliability estimates.")

    styled(d, "Bibliography", size=14, bold=True)
    d.add_paragraph("Box, G.E.P. and Jenkins, G.M. Time Series Analysis. Holden-Day, 1970.")
    return d


def mdpi_style():
    """MDPI: affiliations addressed by superscript index with a separate
    correspondence line, headings numbered with no trailing period, and an
    abstract whose label shares its paragraph with the text."""
    d = Document()
    styled(d, "Machine-Learning Prediction of Corrosion Rates in Marine "
              "Reinforced Concrete", size=16, bold=True, align=CENTER)
    styled(d, "Elena Ruiz 1, Samuel Achebe 2 and Wei-Lun Hsu 1,*",
           size=11, align=CENTER)
    styled(d, "1 Department of Civil Engineering, Universitat Politecnica de "
              "Valencia, 46022 Valencia, Spain", size=9, align=CENTER)
    styled(d, "2 School of Materials Science, University of Lagos, Lagos, Nigeria",
           size=9, align=CENTER)
    styled(d, "* Correspondence: w.hsu@upv.es", size=9, align=CENTER)

    styled(d, "Abstract: Chloride-induced corrosion governs the service life of "
              "marine reinforced concrete, yet empirical rate models generalise "
              "poorly across exposure zones. We assemble a dataset of 1,240 "
              "field measurements and train gradient-boosted regressors to "
              "predict corrosion current density from mixture design and "
              "exposure descriptors. The model attains a mean absolute error of "
              "0.11 microamperes per square centimetre on held-out structures.",
           size=9)
    styled(d, "Keywords: corrosion; reinforced concrete; machine learning; "
              "service life", size=9)

    styled(d, "1. Introduction", size=12, bold=True)
    d.add_paragraph(
        "Service-life prediction for marine structures rests on models of "
        "chloride ingress and subsequent depassivation of the reinforcement.")

    styled(d, "2. Materials and Methods", size=12, bold=True)
    styled(d, "2.1. Dataset", size=11, bold=True)
    d.add_paragraph("Field measurements were pooled from twelve published campaigns.")
    styled(d, "2.2. Model", size=11, bold=True)
    d.add_paragraph("Chloride transport is described by the diffusion equation")
    add_math_para(d, frac(_run("&#8706;C"), _run("&#8706;t")) + _run("=D")
                  + frac(ssup(_run("&#8706;"), _run("2")) + _run("C"),
                         _run("&#8706;") + ssup(_run("x"), _run("2"))), "1")
    add_inline_math(d, "with an apparent diffusivity ",
                    ssub(_run("D"), _run("app")),
                    " fitted per exposure zone.")

    styled(d, "3. Results", size=12, bold=True)
    d.add_paragraph("Predicted and measured rates agree across all three zones.")

    styled(d, "References", size=12, bold=True)
    d.add_paragraph("1. Angst, U. Challenges in corrosion of steel in concrete. "
                    "Mater. Struct. 2018, 51, 4.")
    return d


def tandf_style():
    """Taylor & Francis: unnumbered headings in sentence case with no styles,
    author list carrying ORCID-style footnote glyphs, and a separate
    'CONTACT' line instead of a corresponding-author footnote."""
    d = Document()
    styled(d, "Participatory mapping of flood exposure in informal settlements",
           size=16, bold=True)
    styled(d, "Grace Mwangi†, Tobias Lindqvist and Rafael Duarte†", size=11)
    styled(d, "Centre for Urban Resilience, University of Nairobi, Nairobi, Kenya",
           size=9, italic=True)
    styled(d, "CONTACT Grace Mwangi  g.mwangi@uonbi.ac.ke", size=9)

    styled(d, "ABSTRACT", size=10, bold=True)
    d.add_paragraph(
        "Flood exposure in informal settlements is poorly captured by official "
        "cadastral data. We combine participatory mapping with drone imagery to "
        "build an exposure layer for three settlements, and compare the result "
        "with the national hazard map. The participatory layer identifies "
        "roughly twice as many exposed dwellings, concentrated along drainage "
        "corridors that the official map omits entirely.")
    styled(d, "KEYWORDS: flood risk; participatory mapping; informal "
              "settlements; urban resilience", size=9)

    styled(d, "Introduction", size=13, bold=True)
    d.add_paragraph(
        "Exposure data underpins every quantitative flood risk assessment, and "
        "its omissions propagate directly into loss estimates.")

    styled(d, "Study area and methods", size=13, bold=True)
    d.add_paragraph("Exposure is aggregated over mapped dwelling footprints:")
    add_math_para(d, _run("E=") + nary("&#8721;", _run("j=1"), _run("M"),
                                       ssub(_run("a"), _run("j"))
                                       + ssub(_run("p"), _run("j"))))
    styled(d, "Data collection", size=12, bold=True)
    d.add_paragraph("Community mappers digitised footprints over rectified imagery.")

    styled(d, "Results and discussion", size=13, bold=True)
    d.add_paragraph("The participatory layer doubles the count of exposed dwellings.")

    styled(d, "References", size=13, bold=True)
    d.add_paragraph("Mwangi, G. 2021. Mapping the unmapped. Urban Studies 58: 1--20.")
    return d


def math_heavy():
    """Every OMML construction the converter must handle, in one manuscript:
    inline and display math, fractions, integrals, summations, matrices, Greek
    letters, and several display equations sharing a single Word paragraph."""
    d = Document()
    styled(d, "Spectral Methods for Nonlinear Diffusion: A Worked Derivation",
           size=16, bold=True, align=CENTER)
    styled(d, "Hana Novakova and Peter Osborne", size=11, align=CENTER)
    styled(d, "Institute of Mathematics, Charles University, Prague, Czechia",
           size=9, italic=True, align=CENTER)
    styled(d, "Corresponding author: h.novakova@matfyz.cuni.cz", size=9, align=CENTER)

    styled(d, "Abstract", size=12, bold=True)
    d.add_paragraph(
        "We derive a spectral discretisation of a nonlinear diffusion equation "
        "and establish an energy estimate for the semi-discrete scheme. The "
        "derivation is carried out in full so that every algebraic step is "
        "available for verification, and the resulting bound is sharp in the "
        "diffusion coefficient.")
    styled(d, "Keywords: spectral methods, nonlinear diffusion, energy estimates", size=9)

    styled(d, "1. Preliminaries", size=13, bold=True)
    add_inline_math(d, "Throughout, the diffusion coefficient is written ",
                    ssub(_run("&#954;"), _run("0")),
                    " and the domain is the unit interval.")
    add_inline_math(d, "The nonlinearity is measured by the ratio ",
                    frac(_run("&#945;"), _run("&#946;+&#947;")),
                    ", which stays bounded.")

    styled(d, "2. Governing equation", size=13, bold=True)
    d.add_paragraph("The evolution problem is stated as")
    add_math_para(d, frac(_run("&#8706;u"), _run("&#8706;t")) + _run("=")
                  + frac(_run("&#8706;"), _run("&#8706;x"))
                  + _run("(&#954;(u)") + frac(_run("&#8706;u"), _run("&#8706;x"))
                  + _run(")"), "1")
    d.add_paragraph("Integrating against a test function gives the weak form")
    add_math_para(d, nary("&#8747;", _run("0"), _run("1"),
                          _run("&#954;(u)") + ssub(_run("u"), _run("x"))
                          + ssub(_run("v"), _run("x")) + _run("dx"))
                  + _run("=0"), "2")

    styled(d, "3. Energy estimate", size=13, bold=True)
    d.add_paragraph("The energy satisfies the summed bound")
    add_math_para(d, nary("&#8721;", _run("n=1"), _run("N"),
                          ssup(_run("&#8741;") + ssup(_run("u"), _run("n"))
                               + _run("&#8741;"), _run("2")))
                  + _run("&#8804;") + frac(_run("C"), ssub(_run("&#954;"), _run("0"))),
                  "3")
    # Two display equations inside one Word paragraph: the converter must keep
    # both, gathered, rather than dropping one or flattening them to text.
    p = d.add_paragraph()
    p._p.append(parse_xml(omath_para(ssub(_run("E"), _run("0")) + _run("=")
                                     + frac(_run("1"), _run("2"))
                                     + ssup(_run("&#8741;u&#8741;"), _run("2")))))
    p._p.append(parse_xml(omath_para(ssub(_run("E"), _run("n")) + _run("&#8804;")
                                     + ssub(_run("E"), _run("0"))
                                     + ssup(_run("e"), _run("-&#955;t")))))

    styled(d, "4. Matrix form", size=13, bold=True)
    d.add_paragraph("In the spectral basis the operator is represented by")
    add_math_para(d, matrix([[_run("&#955;"), _run("0"), _run("0")],
                             [_run("0"), ssup(_run("&#955;"), _run("2")), _run("0")],
                             [_run("0"), _run("0"), ssup(_run("&#955;"), _run("3"))]]),
                  "4")
    add_inline_math(d, "whose condition number grows like ",
                    ssup(_run("N"), _run("2")), " with the truncation order.")

    styled(d, "5. Conclusion", size=13, bold=True)
    d.add_paragraph("The estimate is sharp and the scheme is unconditionally stable.")

    styled(d, "References", size=13, bold=True)
    d.add_paragraph("Canuto, C. et al. Spectral Methods. Springer, 2006.")
    return d


BUILDERS = {
    "plain_word.docx": plain_word,
    "ieee_style.docx": ieee_style,
    "springer_style.docx": springer_style,
    "elsevier_style.docx": elsevier_style,
    "thesis_style.docx": thesis_style,
    "mdpi_style.docx": mdpi_style,
    "tandf_style.docx": tandf_style,
    "math_heavy.docx": math_heavy,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, builder in BUILDERS.items():
        builder().save(OUT / name)
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
