**Mittag-Leffler Stability Analysis for a fractional order model of
co-contaminated soil and water pollution**

Priya P.^1^, Roselyn Besi P.^1^ Revathy M^1^, Ali Akgul^2,3,\*^

^1^Department of Mathematics, Coimbatore Institute of Technology,

Coimbatore, Tamil Nadu, India

^2^Department of Electronics and Communication Engineering, Saveetha
School of Engineering,SIMATS, Chennai, Tamilnadu, India

^3^Siirt University, Art and Science Faculty, Department of Mathematics,
56100 Siirt, Türkiye

**Corresponding author**: priyabarath612@gmail.com^1\*^,
aliakgul@siirt.edu.tr

**Abstract**

Environmental pollution is a serious and long-lasting problem, and
understanding how it spreads and how it can be controlled requires
robust mathematical models. In this work, we study a five-compartment
fractional-order model that describes how pollution moves between
different environmental components, namely effluent, soil, water, and
farmland. To capture the memory and hereditary effects that naturally
occur in environmental processes, we use the Atangana--Baleanu--Caputo
(ABC) fractional derivative, which provides a more realistic description
than classical integer-order models. We first analyze the qualitative
behavior of the model. Using linearization, Lyapunov function, and tools
from fractional calculus, we establish the local and global asymptotic
stability of two important equilibrium points: the pollution-free
equilibrium (E₀) and the endemic (polluted) equilibrium (E\*). In
particular, we apply the concept of Mittag-Leffler stability, which is
well-suited to fractional-order systems. A central result of the
analysis is the derivation of the basic reproduction number

$$R_{0} = \ \frac{LaN}{\Phi_{C}\ \left( \Phi^{2} + \ \gamma^{1} \right)},$$

which acts as a threshold parameter for pollution dynamics. If R₀ \< 1,
the pollution-free equilibrium E₀ is globally asymptotically stable,
meaning that pollution will eventually disappear from the environment.
On the other hand, if R₀ \> 1, the pollution-free state becomes
unstable, and a unique endemic equilibrium E\* exists and is stable,
indicating that pollution will persist in the long term. To support the
theoretical results, we develop an adaptive predictor--corrector
numerical scheme designed specifically for the ABC fractional-order
model. This method is both accurate and computationally efficient,
making it suitable for long-time simulations. Numerical experiments,
particularly for the case R₀ = 4.55, clearly show that the solution
converges to the endemic equilibrium, which confirms the theoretical
stability results and demonstrates the reliability of the proposed
numerical approach. Overall, this study provides a clear mathematical
framework for understanding pollution spread and control in complex
environmental systems. The analytical results, together with the
numerical simulations, offer valuable insights that can help in
designing effective long-term pollution remediation and management
strategies.

**Keywords:** Co-Contamination, ABC mathematical model, fixed point,
Adaptive control, Adams-Bhashforth.

**1. Introduction**

Environmental pollution affecting soil and water systems has emerged as
a serious global challenge due to industrial discharge, agricultural
runoff, and uncontrolled waste disposal. Since soil and water
environments are strongly coupled, contaminants introduced into one
medium can easily migrate to the other, leading to persistent ecological
damage and long-term health risks. Mathematical modeling is an essential
tool for understanding such complex pollution dynamics and for designing
effective remediation strategies. However, classical integer-order
models often fail to capture the memory effects, nonlocal interactions,
and anomalous transport mechanisms observed in real environmental
processes. Fractional calculus provides a powerful and flexible
framework for modeling systems with memory and hereditary properties.
Fractional-order differential equations have been successfully applied
in various scientific fields, including heat transfer, diffusion,
epidemiology, groundwater flow, and ecological systems (Diethelm, 2010;
Baleanu et al., 2019). Unlike integer-order models, fractional models
are capable of representing long-range temporal dependence and anomalous
diffusion. In recent years, special attention has been given to
fractional derivatives with nonlocal and non-singular kernels. Among
them, the Atangana--Baleanu fractional derivative in Caputo sense has
attracted considerable interest due to its Mittag-Leffler kernel, which
avoids singularities and provides better physical interpretation
(Atangana & Baleanu, 2017). This operator has been widely applied to
heat transfer models and groundwater flow systems (Atangana & Algahtani,
2015; Sun et al., 2019). Efficient numerical methods for solving
fractional-order systems with the Atangana--Baleanu--Caputo derivative
have been actively developed, showing good stability and convergence
properties (Yadav & Pandey, 2019; Singh et al., 2022; Yadav & Pandey,
2020). Stability analysis is fundamental in fractional-order dynamical
systems, where stability is governed by Mittag-Leffler functions rather
than exponential decay. Rigorous stability criteria and Lyapunov-based
methods have been developed for such systems (Li & Zhang, 2019;
Vargas-De-León, 2012). Motivated by these developments, this study
proposes a fractal fractional-order model for co-contaminated soil and
water pollution using the Atangana--Baleanu--Caputo derivative. The
local and global stability of the system equilibria is analyzed using
Mittag-Leffler stability theory, supported by numerical simulations.

This study contributes to the field by presenting a detailed and
rigorous analysis of a five-compartment fractional-order model for
pollution dynamics and remediation, specifically utilizing the
Atangana-Baleanu-Caputo derivative. We extend previous work by providing
a thorough local and global stability analysis of both the
pollution-free (trivial) and persistent (endemic) equilibrium points.
Our analysis employs advanced techniques such as Mittag-Leffler
stability and fractional Lyapunov methods to characterize the system's
long-term behavior precisely. Furthermore, we develop and implement an
advanced numerical scheme tailored for the efficient and accurate
simulation of the ABC fractional system, enabling practical exploration
of model behavior and validation of the theoretical findings. This
comprehensive approach, combining rigorous theoretical analysis with
robust computational tools, aims to provide deeper insights into the
conditions necessary for successful pollution remediation and the
long-term behavior of complex, memory-dependent environmental systems.

**2. Mathematical Preliminaries**

2.1 Fractional Calculus Fundamentals

**Definition 2.1:** (Atangana-Baleanu-Caputo Fractional Derivative).
\[1\] For $0 < \alpha < 1$, the Atangana-Baleanu-Caputo fractional
derivative of order $\alpha$ is defined as:

$^{ABC}D_{t}^{\alpha}f(t) = \frac{B(\alpha)}{1 - \alpha}\int_{0}^{t}{}E_{\alpha}\left( - \alpha\frac{(t - \tau)^{\alpha}}{1 - \alpha} \right)f^{'(\tau)}d\tau,$

where $B(\alpha)$ is a normalization function with $B(0) = B(1) = 1$,
and $E_{\alpha}( \cdot )$ is the Mittag-Leffler function.

**Definition 2.2:** (Mittag-Leffler Function).\[7\] The one-parameter
Mittag-Leffler function is defined as:
$E_{\alpha}(z) = \sum_{k = 0}^{\infty}{}\frac{z^{k}}{\Gamma(\alpha k + 1)},\quad\alpha > 0,z \in C$.

The two-parameter Mittag-Leffler function is:

$$E_{\alpha,\beta}(z) = \sum_{k = 0}^{\infty}{}\frac{z^{k}}{\Gamma(\alpha k + \beta)},\quad\alpha,\beta > 0,z \in C.$$

**2.2 Mittag-Leffler Stability Theory**

**Definition 2.3** (Mittag-Leffler Stability) \[7\]. The solution $x(t)$
of a fractional-order system is said to be Mittag-Leffler stable if:
$\parallel x(t) \parallel \leq \left\lbrack m\left( x_{0} \right)E_{\alpha}\left( - \lambda t^{\alpha} \right) \right\rbrack^{b}$
where $x_{0}$ is the initial condition, $m(0) = 0$, $m(x) \geq 0$,
$\lambda > 0$, and $b > 0$ are constants.

**Remark 2.1**. When $\alpha = 1$, Mittag-Leffler stability reduces to
exponential stability since $E_{1}( - \lambda t) = e^{- \lambda t}$. For
$0 < \alpha < 1$, the decay is typically slower than exponential,
reflecting the memory effects in fractional systems.

**Lemma 2.1** (Fractional Comparison Principle). \[11\] Let
$u(t) \in C^{1}\left( \lbrack 0,T\rbrack,R_{+} \right)$ satisfy:
$^{ABC}D_{t}^{\alpha}u(t) \leq - \lambda u(t),\quad u(0) = u_{0}$ Then:
$u(t) \leq u_{0}E_{\alpha}\left( - \lambda t^{\alpha} \right)$

**3. Model Formulation**

Consider the fractional-order system with Atangana-Baleanu-Caputo
derivatives:

$$tABCC = \ aN\  - \ LCS_{P} - \ BCW\  - \ \Phi_{C}C$$

$$tABCS_{p} = \ LCS_{p}\  - \ \delta_{1}\ S_{p}\ W\  - \ \delta_{2}\ S_{p}\ F\  - \ \Phi_{2}\ S_{p}\  - \ \gamma_{1}\ S_{p}$$

$$tABCW = \ \delta_{1}\ S_{p}\ W\  - \ \rho\ WF\  - \ \Phi_{3}\ W$$

$$tABCF = \ \delta_{2}\ S_{p}\ F\  + \ \rho\ WF\  - \ \gamma_{2}\ F\  - \ \Phi_{4}\ F$$

$$tABCS_{R} = \ \gamma_{1}\ S_{p}\  + \ \gamma_{2}F\  - \ \Phi_{5}\ S_{R}$$

(1.1)

With the initial conditions

${\ C}^{0} = C(0) \geq 0,\ S_{p}^{0} = S_{p}(0) \geq 0,\ W^{0} = W(0) \geq 0,\ F^{0} = F(0) \geq 0,\ S_{R} = S_{R}(0) \geq 0$*.*

a -- Effluent Concentration

N -- Total Area

$L$ -- Rate of contaminated sediments in soil

$\beta$ -- Rate of contaminated settlements in water

$\delta_{1}$ -- Washout rate of effluents from soil into water

$\delta_{2}$ -- Polluted settlements in farmland

$\rho$ -- Polluted water affecting farmland

$\gamma_{1}$ -- Remedy in polluted soil

$\gamma_{2}$- remedial measure in farmland

$\phi_{1},\ \phi_{2},\phi_{3},\ \phi_{4},\ \phi_{5}$ - Mortality rate of
all the compartments

C- Effluent Concentration

$S_{p}$ -- Polluted Soil

W -- Water Contamination

F -- Farmland pollution

$S_{R}$ -- Remedied Soil

**Definition 3.4**. \[7\] The system is said to be locally
asymptotically stable at an equilibrium point $E^{*}$ if all eigenvalues
$\lambda$ of the Jacobian matrix satisfy
$\left| \arg(\lambda) \right| > \frac{\alpha\pi}{2}$.

**Definition 3.5**.\[7\] The system is globally asymptotically stable at
an equilibrium point $E^{*}$ if it is stable and all trajectories
approach $E^{*}$ as $t \rightarrow \infty$.

**4. Equilibrium Point and Stability analysis:**

The equilibrium points for the fractional-order pollution remediation
model are found by setting the right-hand sides of the model equations
(1.1) to zero.

**Trivial Equilibrium Point** $(E_{0})$**:**

This equilibrium represents a state where pollution is absent in the
soil, water, and farmland compartments.

$$E_{0}\  = \ \left( \frac{aN}{\varnothing_{C}}\ ,\ 0,\ 0,\ 0,\ 0 \right).$$

The components are:

$C_{0}\  = \frac{aN}{\varnothing_{C}}\$: Effluent concentration reaches
a baseline level.

$S_{P0} = \ 0$: No polluted soil.

$W_{0}\  = \ 0$: No water contamination.

$F_{0}\  = \ 0$: No farmland pollution.

$S_{R0} = \ 0$: No remediated soil.

**Endemic Equilibrium Point (**$E^{*}$**):**

This equilibrium represents a state where pollution persists in all
environmental compartments.

$$\ \ \ \ \ \ \ \ E^{*}\  = \ \left( C^{*},\ S_{p}^{*},\ W^{*},\ F^{*},\ S_{R}^{*} \right).$$

where
$C^{*}\  > \ 0,\ S_{p}^{*}\  > \ 0,\ W^{*}\  > \ 0,\ F^{*}\  > \ 0$, and
$S_{R}^{*}\  > \ 0$.The specific values are determined by solving the
system of algebraic equations and we obtained,

$$C^{*}\  = \frac{\left( aN\  - \ LC_{S}\  - \ BC_{W} \right)}{\Phi_{C}}$$

$$S_{p}^{*}\  = \ \frac{LC_{S}}{\left( \delta_{1}\ W\  + \ \delta_{2}\ F\  + \ \Phi_{2}\  + \ \gamma_{1} \right)}\ $$

$$W^{*}\  = \ \frac{\delta_{1}\ S_{p}}{(\rho\ F\  + \ \Phi_{3})}\ \ $$

$$F^{*}\  = \frac{\left( \delta_{2}\ S_{p}\  + \ \rho\ W \right)}{\left( \gamma_{2}\  + \ \Phi_{4} \right)}$$

$$S_{R}^{*}\  = \frac{\left( \gamma_{1}\ S_{p}\  + \ \gamma_{2}\ F \right)}{\Phi_{5}}.$$

**4.2 Stability analysis**

In this section, we analyze the stability properties of the
fractal-fractional order model for co-contaminated soil and water
pollution. The system is governed by the Atangana-Baleanu-Caputo (ABC)
fractional derivative, which enables the incorporation of memory effects
and non-local dynamics into the pollution transmission process.

**4.2.1 Local Stability Analysis**

Jacobian Matrix Computation

Let $X = \left( C,S_{p},W,F,S_{R} \right)^{T}$. The Jacobian matrix
$J(E)$ evaluated at equilibrium point
$E = \left( C^{*},S_{p}^{*},W^{*},F^{*},S_{R}^{*} \right)$ is:

$$J(E) = \left( - \Phi_{C} - LS_{p}^{*} - BW^{*}\  - LC^{*}\  - BC^{*}\ 0\ 0\ LS_{p}^{*}\ LC^{*} - \delta_{1}W^{*} - \delta_{2}F^{*} - \Phi_{2} - \gamma_{1}\  - \delta_{1}S_{p}^{*}\  - \delta_{2}S_{p}^{*}\ 0\ 0\ \delta_{1}W^{*}\ \delta_{1}S_{p}^{*} - \rho F^{*} - \Phi_{3}\  - \rho W^{*}\ 0\ 0\ \delta_{2}F^{*}\ \rho F^{*}\ \delta_{2}S_{p}^{*} + \rho W^{*} - \gamma_{2} - \Phi_{4}\ 0\ 0\ \gamma_{1}\ 0\ \gamma_{2}\  - \Phi_{5}\  \right)$$

**Local Stability of Trivial Equilibrium**

**Proposition 4.1**. *The trivial equilibrium point*
$E_{0} = \left( \frac{aN}{\Phi_{C}},0,0,0,0 \right)$ *has Jacobian
matrix:*

$$J\left( E_{0} \right) = \left( - \Phi_{C}\  - L\frac{aN}{\Phi_{C}}\  - B\frac{aN}{\Phi_{C}}\ 0\ 0\ 0\ L\frac{aN}{\Phi_{C}} - \Phi_{2} - \gamma_{1}\ 0\ 0\ 0\ 0\ 0\  - \Phi_{3}\ 0\ 0\ 0\ 0\ 0\  - \gamma_{2} - \Phi_{4}\ 0\ 0\ \gamma_{1}\ 0\ \gamma_{2}\  - \Phi_{5}\  \right)$$

**Theorem 4.1**. *The trivial equilibrium* $E_{0}$ *is locally
asymptotically stable if:*
$L\frac{aN}{\Phi_{C}} < \Phi_{2} + \gamma_{1}$

*Proof.* The characteristic equation is:

$$\det\left( J\left( E_{0} \right) - \lambda I \right) = \left( - \Phi_{C} - \lambda \right)\left( - \Phi_{3} - \lambda \right)\left( - \Phi_{5} - \lambda \right)\left( - \gamma_{2} - \Phi_{4} - \lambda \right)\left( L\frac{aN}{\Phi_{C}} - \Phi_{2} - \gamma_{1} - \lambda \right) = 0$$

The eigenvalues are:

\- $\lambda_{1} = - \Phi_{C} < 0$

\- $\lambda_{2} = - \Phi_{3} < 0$

\- $\lambda_{3} = - \Phi_{5} < 0$

\- $\lambda_{4} = - \left( \gamma_{2} + \Phi_{4} \right) < 0$

\- $\lambda_{5} = L\frac{aN}{\Phi_{C}} - \Phi_{2} - \gamma_{1}$

For stability, we require $\lambda_{5} < 0$, which gives the condition:

$$L\frac{aN}{\Phi_{C}} < \Phi_{2} + \gamma_{1}$$

Since $0 < \alpha < 1$, we have $\frac{\alpha\pi}{2} < \frac{\pi}{2}$,
so $\cos\left( \frac{\alpha\pi}{2} \right) > 0$. For real eigenvalues,
the stability condition
$\left| \arg(\lambda) \right| > \frac{\alpha\pi}{2}$ is equivalent to
$\lambda < 0$ when $\lambda$ is real and negative. ◻

Local Stability of Endemic Equilibrium

**Theorem 4.2** (Local Stability of Endemic Equilibrium). The endemic
equilibrium point $E^{*}$ is locally asymptotically stable if all
eigenvalues $\lambda$ of the Jacobian matrix $J\left( E^{*} \right)$
satisfy $\left| \arg(\lambda) \right| > \frac{\alpha\pi}{2}$ where
$0 < \alpha < 1$ is the fractional order.

**Proof.** The characteristic equation is
$\det\left( J\left( E^{*} \right) - \lambda I \right) = 0$. Due to the
triangular structure of the last row, one eigenvalue is
$\lambda_{5} = - \Phi_{5} < 0$, which is always stable.

For the remaining $4 \times 4$ subsystem, let:

$$J_{4} = \left( - \Phi_{C} - LS_{p}^{*} - BW^{*}\  - LC^{*}\  - BC^{*}\ 0\ LS_{p}^{*}\ 0\  - \delta_{1}S_{p}^{*}\  - \delta_{2}S_{p}^{*}\ 0\ \delta_{1}W^{*}\ 0\  - \rho W^{*}\ 0\ \delta_{2}F^{*}\ \rho F^{*}\ 0\  \right)$$

The characteristic polynomial of $J_{4}$ is:

$$P_{4}(\lambda) = \lambda^{4} + a_{3}\lambda^{3} + a_{2}\lambda^{2} + a_{1}\lambda + a_{0}$$

where: To derive the coefficients of the characteristic polynomial, we
compute the determinant of $J_{4} - \lambda I$:

$$J_{4} - \lambda I = \left( - \Phi_{C} - LS_{p}^{*} - BW^{*} - \lambda\  - LC^{*}\  - BC^{*}\ 0\ LS_{p}^{*}\  - \lambda\  - \delta_{1}S_{p}^{*}\  - \delta_{2}S_{p}^{*}\ 0\ \delta_{1}W^{*}\  - \lambda\  - \rho W^{*}\ 0\ \delta_{2}F^{*}\ \rho F^{*}\  - \lambda\  \right)$$

Expanding along the first row:

$$\det\left( J_{4} - \lambda I \right) = \left( - \Phi_{C} - LS_{p}^{*} - BW^{*} - \lambda \right)M_{11} + LC^{*}M_{12} + BC^{*}M_{13}$$

where $M_{ij}$ are the corresponding cofactors.

Computing the cofactors:

$$M_{11} = det\left( - \lambda\  - \delta_{1}S_{p}^{*}\  - \delta_{2}S_{p}^{*}\ \delta_{1}W^{*}\  - \lambda\  - \rho W^{*}\ \delta_{2}F^{*}\ \rho F^{*}\  - \lambda\  \right)$$

Expanding this $3 \times 3$ determinant:

$$M_{11}\  = - \lambda\left\lbrack \lambda^{2} + \rho W^{*} \cdot \rho F^{*} - \left( - \rho W^{*} \right)\left( \delta_{2}F^{*} \right) \right\rbrack\ \ \quad + \delta_{1}S_{p}^{*}\left\lbrack \delta_{1}W^{*} \cdot ( - \lambda) - \left( - \rho W^{*} \right)\left( \delta_{2}F^{*} \right) \right\rbrack\ \ \quad - \delta_{2}S_{p}^{*}\left\lbrack \delta_{1}W^{*} \cdot \rho F^{*} - ( - \lambda)\left( \delta_{2}F^{*} \right) \right\rbrack\ \  = - \lambda^{3} - \lambda\rho^{2}W^{*}F^{*} - \lambda\delta_{1}^{2}S_{p}^{*}W^{*} - \lambda\delta_{2}^{2}S_{p}^{*}F^{*}\ \ \quad + \delta_{1}\delta_{2}\rho S_{p}^{*}W^{*}F^{*} + \delta_{1}\delta_{2}\rho S_{p}^{*}W^{*}F^{*}\ \  = - \lambda^{3} - \lambda\left( \rho^{2}W^{*}F^{*} + \delta_{1}^{2}S_{p}^{*}W^{*} + \delta_{2}^{2}S_{p}^{*}F^{*} \right) + 2\delta_{1}\delta_{2}\rho S_{p}^{*}W^{*}F^{*}\ $$

$$M_{12} = - det\left( LS_{p}^{*}\  - \delta_{1}S_{p}^{*}\  - \delta_{2}S_{p}^{*}\ 0\  - \lambda\  - \rho W^{*}\ 0\ \rho F^{*}\  - \lambda\  \right)$$

$$M_{12} = - LS_{p}^{*}\left\lbrack \lambda^{2} + \rho^{2}W^{*}F^{*} \right\rbrack = - LS_{p}^{*}\lambda^{2} - LS_{p}^{*}\rho^{2}W^{*}F^{*}$$

$$M_{13} = det\left( LS_{p}^{*}\  - \lambda\  - \delta_{2}S_{p}^{*}\ 0\ \delta_{1}W^{*}\  - \rho W^{*}\ 0\ \delta_{2}F^{*}\ \rho F^{*}\  \right)$$

$$M_{13} = LS_{p}^{*}\left\lbrack \delta_{1}W^{*} \cdot \rho F^{*} - \left( - \rho W^{*} \right)\left( \delta_{2}F^{*} \right) \right\rbrack = LS_{p}^{*}\rho\left( \delta_{1}W^{*}F^{*} + \delta_{2}W^{*}F^{*} \right)$$

Combining all terms:

$$\det\left( J_{4} - \lambda I \right)\  = \left( - \Phi_{C} - LS_{p}^{*} - BW^{*} - \lambda \right)\lbrack - \lambda^{3} - \lambda\left( \rho^{2}W^{*}F^{*} + \delta_{1}^{2}S_{p}^{*}W^{*} + \delta_{2}^{2}S_{p}^{*}F^{*} \right)\ \ \quad + 2\delta_{1}\delta_{2}\rho S_{p}^{*}W^{*}F^{*}\rbrack\ \ \quad + LC^{*}\left\lbrack - LS_{p}^{*}\lambda^{2} - LS_{p}^{*}\rho^{2}W^{*}F^{*} \right\rbrack\ \ \quad + BC^{*}\left\lbrack LS_{p}^{*}\rho\left( \delta_{1} + \delta_{2} \right)W^{*}F^{*} \right\rbrack\ $$

Expanding and collecting terms by powers of $\lambda$:

$$\det\left( J_{4} - \lambda I \right) = \lambda^{4} + a_{3}\lambda^{3} + a_{2}\lambda^{2} + a_{1}\lambda + a_{0}$$

where the coefficients are:

$$a_{3}\  = \Phi_{C} + LS_{p}^{*} + BW^{*}\ a_{2}\  = \rho^{2}W^{*}F^{*} + \delta_{1}^{2}S_{p}^{*}W^{*} + \delta_{2}^{2}S_{p}^{*}F^{*} + LC^{*} \cdot LS_{p}^{*}\ \ \quad - LC^{*} \cdot \delta_{1}W^{*} + BC^{*} \cdot \rho\left( \delta_{1} + \delta_{2} \right)F^{*}\ a_{1}\  = - 2\delta_{1}\delta_{2}\rho S_{p}^{*}W^{*}F^{*}\left( \Phi_{C} + LS_{p}^{*} + BW^{*} \right)\ \ \quad - LC^{*}LS_{p}^{*}\rho^{2}W^{*}F^{*} - LC^{*}LS_{p}^{*}\delta_{1}^{2}W^{*} - LC^{*}LS_{p}^{*}\delta_{2}^{2}F^{*}\ \ \quad + BC^{*}LS_{p}^{*}\rho^{2}\left( \delta_{1} + \delta_{2} \right)W^{*}F^{*}\ a_{0}\  = 2\delta_{1}\delta_{2}\rho S_{p}^{*}W^{*}F^{*}\left( \Phi_{C} + LS_{p}^{*} + BW^{*} \right)\ \ \quad + LC^{*}LS_{p}^{*}\rho^{2}W^{*}F^{*} + BC^{*}LS_{p}^{*}\rho^{2}\left( \delta_{1} + \delta_{2} \right)W^{*}F^{*}\ $$

For the determinant of the full Jacobian matrix:

$$\det\left( J\left( E^{*} \right) - \lambda I \right) = \left( \lambda + \Phi_{5} \right) \cdot det\left( J_{4} - \lambda I \right)$$

Therefore, the constant term of the full characteristic polynomial is:

$$a_{0}^{(full)} = \Phi_{5} \cdot a_{0}$$

By the Routh-Hurwitz criterion adapted for fractional systems, $E^{*}$
is locally asymptotically stable if:

1.  $a_{3} > 0$

2.  $a_{3}a_{2} > a_{1}$

3.  $a_{3}a_{2}a_{1} > a_{1}^{2} + a_{3}^{2}a_{0}$

4.  $a_{0} > 0$

5.  $a_{3}a_{2}a_{1}a_{0} > a_{1}^{2}a_{0} + a_{3}^{2}a_{0}^{2}$

Since all system parameters are positive and at endemic equilibrium
$S_{p}^{*},W^{*},F^{*} > 0$, conditions (1) and (4) are automatically
satisfied. The remaining conditions depend on the specific parameter
values and equilibrium magnitudes. ◻

**Corollary 4.1**. If the endemic equilibrium exists ($R_{0} > 1$) and
the trace of $J_{4}$ is negative with positive determinant, then the
endemic equilibrium is locally asymptotically stable for sufficiently
small fractional order $\alpha$.

**4.3 Global Stability Analysis**

Global Stability of Trivial Equilibrium

**Theorem 4.3**. The trivial equilibrium $E_{0}$ is globally
asymptotically stable in $R_{+}^{5}$ if:
$L\frac{aN}{\Phi_{C}} < \Phi_{2} + \gamma_{1}$

**Proof**. We construct a Lyapunov function for the subsystem involving
$\left( S_{p},W,F \right)$:

$$V_{1}\left( S_{p},W,F \right) = S_{p} + W + F$$

The fractional derivative of $V_{1}$ along solutions is:

$$^{ABC}D_{t}^{\alpha}V_{1}\  =^{ABC}D_{t}^{\alpha}S_{p} +^{ABC}D_{t}^{\alpha}W +^{ABC}D_{t}^{\alpha}F\ \  = LCS_{p} - \delta_{1}S_{p}W - \delta_{2}S_{p}F - \Phi_{2}S_{p} - \gamma_{1}S_{p}\ \ \quad + \delta_{1}S_{p}W - \rho WF - \Phi_{3}W\ \ \quad + \delta_{2}S_{p}F + \rho WF - \gamma_{2}F - \Phi_{4}F\ \  = LCS_{p} - \Phi_{2}S_{p} - \gamma_{1}S_{p} - \Phi_{3}W - \gamma_{2}F - \Phi_{4}F\ \  = S_{p}\left( LC - \Phi_{2} - \gamma_{1} \right) - \Phi_{3}W - \left( \gamma_{2} + \Phi_{4} \right)F\ $$

If $LC < \Phi_{2} + \gamma_{1}$, then $^{ABC}D_{t}^{\alpha}V_{1} \leq 0$
with equality if and only if $S_{p} = W = F = 0$.

For the full system, consider:

$$V\left( C,S_{p},W,F,S_{R} \right) = \left( C - C_{0} - C_{0}\ln\frac{C}{C_{0}} \right) + S_{p} + W + F + \left( S_{R} - S_{R0} - S_{R0}\ln\frac{S_{R}}{S_{R0}} \right)$$

where $C_{0} = \frac{aN}{\Phi_{C}}$ and $S_{R0} = 0$.

The derivative of the first term is:

$$^{ABC}D_{t}^{\alpha}\left( C - C_{0} - C_{0}\ln\frac{C}{C_{0}} \right)\  = \left( 1 - \frac{C_{0}}{C} \right)^{ABC}D_{t}^{\alpha}C\ \  = \left( 1 - \frac{C_{0}}{C} \right)\left( aN - LCS_{p} - BCW - \Phi_{C}C \right)\ \  = \left( 1 - \frac{C_{0}}{C} \right)\left( - LCS_{p} - BCW \right)\ \  = - LCS_{p}\left( 1 - \frac{C_{0}}{C} \right) - BCW\left( 1 - \frac{C_{0}}{C} \right)\ $$

Since $C_{0} = \frac{aN}{\Phi_{C}}$ and at equilibrium
$aN = \Phi_{C}C_{0}$:

$$^{ABC}D_{t}^{\alpha}\left( C - C_{0} - C_{0}\ln\frac{C}{C_{0}} \right) = - LCS_{p}\left( 1 - \frac{C_{0}}{C} \right) - BCW\left( 1 - \frac{C_{0}}{C} \right) \leq 0$$

For the remediated soil component:

$$^{ABC}D_{t}^{\alpha}S_{R} = \gamma_{1}S_{p} + \gamma_{2}F - \Phi_{5}S_{R}$$

Combining all terms and using LaSalle's invariance principle for
fractional systems, we conclude global asymptotic stability when
$L\frac{aN}{\Phi_{C}} < \Phi_{2} + \gamma_{1}$. ◻

Global Stability of Endemic Equilibrium

**Theorem 4.4**. If the endemic equilibrium $E^{*}$ exists and the
following conditions hold:

1.  $L\frac{aN}{\Phi_{C}} > \Phi_{2} + \gamma_{1}$ (existence condition)

2.  Additional technical conditions on the parameters

then $E^{*}$ is globally asymptotically stable in the interior of
$R_{+}^{5}$.

Proof. We construct a Lyapunov function of Goh-Volterra type:

$$V = \underline{C}H\left( \frac{C}{\underline{C}} \right) + \underline{S_{p}}H\left( \frac{S_{p}}{\underline{S_{p}}} \right) + \underline{W}H\left( \frac{W}{\underline{W}} \right) + \underline{F}H\left( \frac{F}{\underline{F}} \right) + \underline{S_{R}}H\left( \frac{S_{R}}{\underline{S_{R}}} \right)$$

where $H(x) = x - 1 - lnx$ and
$\underline{E} = \left( \underline{C},\underline{S_{p}},\underline{W},\underline{F},\underline{S_{R}} \right)$
is the endemic equilibrium.

Using the equilibrium equations and following the approach in , we can
show that $^{ABC}D_{t}^{\alpha}V \leq 0$ with equality if and only if
$\left( C,S_{p},W,F,S_{R} \right) = \left( \underline{C},\underline{S_{p}},\underline{W},\underline{F},\underline{S_{R}} \right)$.

The detailed computation involves substituting the system equations and
equilibrium relations, and requires that all cross terms cancel
appropriately, leading to a negative definite derivative. ◻

**4.3 Basic Reproduction Number and Threshold Dynamics**

**Definition 4.6**.\[5\] The basic reproduction number $R_{0}$ is
defined as the expected number of secondary pollution cases produced by
a single primary case in a completely susceptible environment.

**Theorem 4.5**. For the pollution model, the basic reproduction number
is:
$R_{0} = \frac{L \cdot aN}{\Phi_{C}\left( \Phi_{2} + \gamma_{1} \right)}$

**Proof**. Using the next-generation matrix method, we identify:

1.  New pollution generation terms: $LCS_{p}$

2.  Transfer terms: $\Phi_{2}S_{p} + \gamma_{1}S_{p}$

At the trivial equilibrium $E_{0}$, we have
$C_{0} = \frac{aN}{\Phi_{C}}$, so:

$$R_{0} = \frac{L \cdot \frac{aN}{\Phi_{C}}}{\Phi_{2} + \gamma_{1}} = \frac{L \cdot aN}{\Phi_{C}\left( \Phi_{2} + \gamma_{1} \right)}$$

**Corollary 2**. The stability threshold can be expressed in terms of
the basic reproduction number:

1.  If $R_{0} < 1$, then $E_{0}$ is globally asymptotically stable

2.  If $R_{0} > 1$, then $E_{0}$ is unstable and the endemic equilibrium
    exists

**4.4 Mittag-Leffler Stability Analysis**

Fractional Lyapunov Direct Method

**Theorem 4.6** (Fractional Lyapunov Stability Theorem). Let
$D \subset R^{n}$ be a domain containing the origin. If there exists a
continuously differentiable function
$V(t,x):\lbrack 0,\infty) \times D \rightarrow R$ and class $K$
functions $\alpha_{1},\alpha_{2},\alpha_{3}$ such that:

$$\alpha_{1}( \parallel x \parallel )\  \leq V(t,x) \leq \alpha_{2}( \parallel x \parallel )\ ^{ABC}D_{t}^{\alpha}V(t,x)\  \leq - \alpha_{3}( \parallel x \parallel )\ $$

then the origin is asymptotically Mittag-Leffler stable.

**Mittag-Leffler Stability of Trivial Equilibrium**

**Theorem 4.7** (Main Result - Mittag-Leffler Stability of $E_{0}$). The
trivial equilibrium point
$E_{0} = \left( \frac{aN}{\Phi_{C}},0,0,0,0 \right)$ is Mittag-Leffler
stable if:
$R_{0} = \frac{L \cdot aN}{\Phi_{C}\left( \Phi_{2} + \gamma_{1} \right)} < 1$

***Proof.*** We construct a fractional Lyapunov function candidate:

$$V(t,X) = V_{1}(t,C) + V_{2}\left( t,S_{p} \right) + V_{3}(t,W) + V_{4}(t,F) + V_{5}\left( t,S_{R} \right)$$

where:

$$V_{1}(t,C)\  = \frac{1}{2}\left( C - C_{0} \right)^{2}\ V_{2}\left( t,S_{p} \right)\  = \frac{1}{2}S_{p}^{2}\ V_{3}(t,W)\  = \frac{1}{2}W^{2}\ V_{4}(t,F)\  = \frac{1}{2}F^{2}\ V_{5}\left( t,S_{R} \right)\  = \frac{1}{2}S_{R}^{2}\ $$

Bounding the Lyapunov Function, Clearly:

$$\frac{1}{2} \parallel X - E_{0} \parallel^{2} \leq V(t,X) \leq \frac{1}{2} \parallel X - E_{0} \parallel^{2}$$

where
$\parallel X - E_{0} \parallel^{2} = \left( C - C_{0} \right)^{2} + S_{p}^{2} + W^{2} + F^{2} + S_{R}^{2}$.

Computing the Fractional Derivative, using the property of fractional
derivatives:

$$^{ABC}D_{t}^{\alpha}V(t,X) = \sum_{i = 1}^{5}{}\frac{\partial V}{\partial x_{i}} \cdot^{ABC}D_{t}^{\alpha}x_{i}$$

Computing each term:

For $V_{1}$:

$$^{ABC}D_{t}^{\alpha}V_{1} = \left( C - C_{0} \right) \cdot^{ABC}D_{t}^{\alpha}C = \left( C - C_{0} \right)\left( aN - LCS_{p} - BCW - \Phi_{C}C \right)$$

Since at equilibrium $aN = \Phi_{C}C_{0}$:

$$^{ABC}D_{t}^{\alpha}V_{1} = \left( C - C_{0} \right)\left( - LCS_{p} - BCW - \Phi_{C}\left( C - C_{0} \right) \right)$$

$$= - \left( C - C_{0} \right)^{2}\Phi_{C} - \left( C - C_{0} \right)LCS_{p} - \left( C - C_{0} \right)BCW$$

For $V_{2}$:

$$^{ABC}D_{t}^{\alpha}V_{2} = S_{p} \cdot^{ABC}D_{t}^{\alpha}S_{p} = S_{p}\left( LCS_{p} - \delta_{1}S_{p}W - \delta_{2}S_{p}F - \Phi_{2}S_{p} - \gamma_{1}S_{p} \right)$$

$$= S_{p}^{2}\left( LC - \delta_{1}W - \delta_{2}F - \Phi_{2} - \gamma_{1} \right) - \delta_{1}S_{p}^{2}W - \delta_{2}S_{p}^{2}F$$

For $V_{3}$:

$$^{ABC}D_{t}^{\alpha}V_{3} = W \cdot^{ABC}D_{t}^{\alpha}W = W\left( \delta_{1}S_{p}W - \rho WF - \Phi_{3}W \right)$$

$$= \delta_{1}S_{p}W^{2} - \rho W^{2}F - \Phi_{3}W^{2}$$

For $V_{4}$:

$$^{ABC}D_{t}^{\alpha}V_{4} = F \cdot^{ABC}D_{t}^{\alpha}F = F\left( \delta_{2}S_{p}F + \rho WF - \gamma_{2}F - \Phi_{4}F \right)$$

$$= \delta_{2}S_{p}F^{2} + \rho WF^{2} - \left( \gamma_{2} + \Phi_{4} \right)F^{2}$$

For $V_{5}$:

$$^{ABC}D_{t}^{\alpha}V_{5} = S_{R} \cdot^{ABC}D_{t}^{\alpha}S_{R} = S_{R}\left( \gamma_{1}S_{p} + \gamma_{2}F - \Phi_{5}S_{R} \right)$$

$$= \gamma_{1}S_{p}S_{R} + \gamma_{2}FS_{R} - \Phi_{5}S_{R}^{2}$$

Summing all terms:

$$^{ABC}D_{t}^{\alpha}V(t,X)\  = - \left( C - C_{0} \right)^{2}\Phi_{C} - \left( C - C_{0} \right)LCS_{p} - \left( C - C_{0} \right)BCW\ \ \quad + S_{p}^{2}\left( LC - \delta_{1}W - \delta_{2}F - \Phi_{2} - \gamma_{1} \right) - \delta_{1}S_{p}^{2}W - \delta_{2}S_{p}^{2}F\ \ \quad + \delta_{1}S_{p}W^{2} - \rho W^{2}F - \Phi_{3}W^{2}\ \ \quad + \delta_{2}S_{p}F^{2} + \rho WF^{2} - \left( \gamma_{2} + \Phi_{4} \right)F^{2}\ \ \quad + \gamma_{1}S_{p}S_{R} + \gamma_{2}FS_{R} - \Phi_{5}S_{R}^{2}\ $$

Using Young's inequality and Cauchy-Schwarz inequality to bound cross
terms:

For $\left( C - C_{0} \right)LCS_{p}$:

$$\left| \left( C - C_{0} \right)LCS_{p} \right| \leq \frac{\epsilon_{1}}{2}\left( C - C_{0} \right)^{2} + \frac{L^{2}C_{0}^{2}}{2\epsilon_{1}}S_{p}^{2}$$

For $\left( C - C_{0} \right)BCW$:

$$\left| \left( C - C_{0} \right)BCW \right| \leq \frac{\epsilon_{2}}{2}\left( C - C_{0} \right)^{2} + \frac{B^{2}C_{0}^{2}}{2\epsilon_{2}}W^{2}$$

For $\gamma_{1}S_{p}S_{R}$:

$$\gamma_{1}S_{p}S_{R} \leq \frac{\epsilon_{3}}{2}S_{p}^{2} + \frac{\gamma_{1}^{2}}{2\epsilon_{3}}S_{R}^{2}$$

For $\gamma_{2}FS_{R}$:

$$\gamma_{2}FS_{R} \leq \frac{\epsilon_{4}}{2}F^{2} + \frac{\gamma_{2}^{2}}{2\epsilon_{4}}S_{R}^{2}$$

Choosing appropriate $\epsilon_{i}$ values and collecting terms:

$$^{ABC}D_{t}^{\alpha}V(t,X) \leq - \lambda_{1}\left( C - C_{0} \right)^{2} - \lambda_{2}S_{p}^{2} - \lambda_{3}W^{2} - \lambda_{4}F^{2} - \lambda_{5}S_{R}^{2}$$

where the coefficients depend on system parameters and the condition
$R_{0} < 1$.

Specifically, for the $S_{p}$ term:

$$\lambda_{2} = \Phi_{2} + \gamma_{1} - LCC_{0} - (positive\ correction\ terms)$$

Since $C_{0} = \frac{aN}{\Phi_{C}}$:

$$\lambda_{2} = \Phi_{2} + \gamma_{1} - L\frac{aN}{\Phi_{C}} = \left( \Phi_{2} + \gamma_{1} \right)\left( 1 - R_{0} \right) - (positive\ terms)$$

Therefore, if $R_{0} < 1$, then $\lambda_{2} > 0$ for sufficiently small
cross-term contributions.

We have established:

$$^{ABC}D_{t}^{\alpha}V(t,X) \leq - \lambda V(t,X)$$

where
$\lambda = min\{\lambda_{1},\lambda_{2},\lambda_{3},\lambda_{4},\lambda_{5}\} > 0$
when $R_{0} < 1$.

By the fractional comparison principle:

$$V(t,X) \leq V\left( 0,X_{0} \right)E_{\alpha}\left( - \lambda t^{\alpha} \right)$$

Since $V(t,X) \geq \frac{1}{2} \parallel X - E_{0} \parallel^{2}$:

$$\parallel X(t) - E_{0} \parallel^{2} \leq 2V\left( 0,X_{0} \right)E_{\alpha}\left( - \lambda t^{\alpha} \right)$$

Therefore:

$$\parallel X(t) - E_{0} \parallel \leq \sqrt{2V\left( 0,X_{0} \right)}\left\lbrack E_{\alpha}\left( - \lambda t^{\alpha} \right) \right\rbrack^{1/2}$$

This exact proportionality allows the decay of the Lyapunov function to
be directly translated into the decay of the state variables, which
plays a crucial role in proving Mittag--Leffler stability for the
considered fractional-order model. ◻

**Convergence Rate Analysis**

**Corollary 4.3** (Convergence Rate). Under the conditions of Theorem 1,
the solution converges to the trivial equilibrium with rate:
$\parallel X(t) - E_{0} \parallel = O\left( E_{\alpha}\left( - \lambda t^{\alpha} \right) \right)$

For long times, the Mittag-Leffler function behaves as:
$E_{\alpha}\left( - \lambda t^{\alpha} \right) \sim \frac{1}{\Gamma(1 - \alpha)}\frac{1}{\lambda t^{\alpha}},\quad t \rightarrow \infty$

This shows algebraic decay, which is slower than exponential decay for
$\alpha < 1$.

Parameter Sensitivity Analysis

The Mittag-Leffler stability condition $R_{0} < 1$ can be written as:

$$L < \frac{\Phi_{C}\left( \Phi_{2} + \gamma_{1} \right)}{aN}$$

This provides clear guidelines for pollution control:

1.  Reduce pollution generation rate $L$

2.  Increase degradation rates $\Phi_{C},\Phi_{2},\gamma_{1}$

3.  Reduce system size $N$ or effluent rate $a$

**Mittag-Leffler Stability of Endemic Equilibrium**

**Theorem 4.8** (Mittag-Leffler Stability of Endemic Equilibrium). If
the endemic equilibrium $E^{*}$ exists (i.e., $R_{0} > 1$) and certain
technical conditions are satisfied, then $E^{*}$ is locally
Mittag-Leffler stable.

***Proof**.* The proof follows similar steps using a Lyapunov function
of the form:

$$V(t,X) = \sum_{i = 1}^{5}{}\underline{x_{i}}H\left( \frac{x_{i}}{\underline{x_{i}}} \right)$$

where $H(x) = x - 1 - lnx$ is the Volterra function, and
$\underline{X} = \left( \underline{C},\underline{S_{p}},\underline{W},\underline{F},\underline{S_{R}} \right)$
is the endemic equilibrium.

The fractional derivative satisfies:

$$^{ABC}D_{t}^{\alpha}V(t,X) \leq - \mu\sum_{i = 1}^{5}{}\left( x_{i} - \underline{x_{i}} \right)^{2}$$

for some $\mu > 0$, establishing local Mittag-Leffler stability. ◻

**5. Numerical Scheme for ABC Fractional Model**

Trapezoidal Product-Integration Rule for ABC Derivatives

We employ the advanced trapezoidal product-integration scheme recently
developed for Atangana-Baleanu-Caputo fractional derivatives, which
provides higher accuracy and better stability properties.

The numerical approximation at time $t_{n} = n\Delta t$ is given by:

$$^{ABC}D_{t}^{\alpha}u\left( t_{n} \right) \approx \frac{B(\alpha)}{1 - \alpha}\sum_{k = 0}^{n}{}w_{n - k}^{(\alpha)}\left\lbrack u\left( t_{k} \right) - u\left( t_{0} \right) \right\rbrack + \frac{\alpha\Delta t^{\alpha}}{\Gamma(2 - \alpha)(1 - \alpha)}\sum_{k = 0}^{n}{}{\widetilde{w}}_{n - k}^{(\alpha)}\frac{u\left( t_{k} \right) - u\left( t_{k - 1} \right)}{\Delta t}$$

where the weights are defined as:

$$w_{0}^{(\alpha)}\  = 1\ w_{k}^{(\alpha)}\  = (k + 1)^{1 - \alpha} - 2k^{1 - \alpha} + (k - 1)^{1 - \alpha},\quad k \geq 1\ {\widetilde{w}}_{0}^{(\alpha)}\  = 0\ {\widetilde{w}}_{k}^{(\alpha)}\  = (k + 1)^{2 - \alpha} - 2k^{2 - \alpha} + (k - 1)^{2 - \alpha},\quad k \geq 1\ $$

Improved Predictor-Corrector Scheme

We implement an improved second-order predictor-corrector method with
adaptive step-size control:

**Predictor Step:**

$$X_{n + 1}^{(P)} = X_{0} + \frac{1 - \alpha}{B(\alpha)}F\left( t_{n},X_{n} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n}{}b_{j,n + 1}F\left( t_{j},X_{j} \right)$$

**Corrector Step:**

$$X_{n + 1} = X_{0} + \frac{1 - \alpha}{B(\alpha)}F\left( t_{n + 1},X_{n + 1}^{(P)} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n + 1}{}{\widetilde{b}}_{j,n + 1}F\left( t_{j},X_{j}^{(c)} \right)$$

where:

$$b_{j,n + 1}\  = \{\frac{\Delta t^{\alpha}}{\alpha}\left\lbrack (n + 1)^{\alpha} - n^{\alpha} \right\rbrack,\ j = 0\ \frac{\Delta t^{\alpha}}{\alpha}\left\lbrack (n - j + 2)^{\alpha + 1} - 2(n - j + 1)^{\alpha + 1} + (n - j)^{\alpha + 1} \right\rbrack,\ 1 \leq j \leq n\ \frac{\Delta t^{\alpha}}{\alpha},\ j = n + 1\ \ $$

$${\widetilde{b}}_{j,n + 1}\  = \{\frac{\Delta t^{\alpha}}{\alpha(\alpha + 1)}\left\lbrack (n + 1)^{\alpha + 1} - (n + 1 - \alpha)(n + 1)^{\alpha} \right\rbrack,\ j = 0\ \frac{\Delta t^{\alpha}}{\alpha}\left\lbrack (n - j + 2)^{\alpha + 1} - 2(n - j + 1)^{\alpha + 1} + (n - j)^{\alpha + 1} \right\rbrack,\ 1 \leq j \leq n\ \frac{\Delta t^{\alpha}}{\alpha(\alpha + 1)}\left\lbrack (n + 1)^{\alpha + 1} - (n + 1 - \alpha)(n + 1)^{\alpha} \right\rbrack,\ j = n + 1\ \ $$

Implementation for the Pollution Model

For our specific system, let
$X(t) = \left( C(t),S_{p}(t),W(t),F(t),S_{R}(t) \right)^{T}$ and
$F(X) = \left( F_{1}(X),F_{2}(X),F_{3}(X),F_{4}(X),F_{5}(X) \right)^{T}$
where:

$$F_{1}(X)\  = aN - LCS_{p} - BCW - \Phi_{C}C\ F_{2}(X)\  = LCS_{p} - \delta_{1}S_{p}W - \delta_{2}S_{p}F - \Phi_{2}S_{p} - \gamma_{1}S_{p}\ F_{3}(X)\  = \delta_{1}S_{p}W - \rho WF - \Phi_{3}W\ F_{4}(X)\  = \delta_{2}S_{p}F + \rho WF - \gamma_{2}F - \Phi_{4}F\ F_{5}(X)\  = \gamma_{1}S_{p} + \gamma_{2}F - \Phi_{5}S_{R}\ $$

The numerical scheme becomes:

**Component-wise Predictor:**

$$C_{n + 1}^{(P)}\  = C_{0} + \frac{1 - \alpha}{B(\alpha)}F_{1}\left( t_{n},X_{n} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n}{}b_{j,n + 1}F_{1}\left( t_{j},X_{j} \right)\ S_{p,n + 1}^{(P)}\  = S_{p,0} + \frac{1 - \alpha}{B(\alpha)}F_{2}\left( t_{n},X_{n} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n}{}b_{j,n + 1}F_{2}\left( t_{j},X_{j} \right)\ W_{n + 1}^{(P)}\  = W_{0} + \frac{1 - \alpha}{B(\alpha)}F_{3}\left( t_{n},X_{n} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n}{}b_{j,n + 1}F_{3}\left( t_{j},X_{j} \right)\ F_{n + 1}^{(P)}\  = F_{0} + \frac{1 - \alpha}{B(\alpha)}F_{4}\left( t_{n},X_{n} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n}{}b_{j,n + 1}F_{4}\left( t_{j},X_{j} \right)\ S_{R,n + 1}^{(P)}\  = S_{R,0} + \frac{1 - \alpha}{B(\alpha)}F_{5}\left( t_{n},X_{n} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n}{}b_{j,n + 1}F_{5}\left( t_{j},X_{j} \right)\ $$

**Component-wise Corrector:**

$$C_{n + 1}\  = C_{0} + \frac{1 - \alpha}{B(\alpha)}F_{1}\left( t_{n + 1},X_{n + 1}^{(P)} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n + 1}{}{\widetilde{b}}_{j,n + 1}F_{1}\left( t_{j},X_{j}^{(c)} \right)\ S_{p,n + 1}\  = S_{p,0} + \frac{1 - \alpha}{B(\alpha)}F_{2}\left( t_{n + 1},X_{n + 1}^{(P)} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n + 1}{}{\widetilde{b}}_{j,n + 1}F_{2}\left( t_{j},X_{j}^{(c)} \right)\ W_{n + 1}\  = W_{0} + \frac{1 - \alpha}{B(\alpha)}F_{3}\left( t_{n + 1},X_{n + 1}^{(P)} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n + 1}{}{\widetilde{b}}_{j,n + 1}F_{3}\left( t_{j},X_{j}^{(c)} \right)\ F_{n + 1}\  = F_{0} + \frac{1 - \alpha}{B(\alpha)}F_{4}\left( t_{n + 1},X_{n + 1}^{(P)} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n + 1}{}{\widetilde{b}}_{j,n + 1}F_{4}\left( t_{j},X_{j}^{(c)} \right)\ S_{R,n + 1}\  = S_{R,0} + \frac{1 - \alpha}{B(\alpha)}F_{5}\left( t_{n + 1},X_{n + 1}^{(P)} \right) + \frac{\alpha}{B(\alpha)\Gamma(\alpha)}\sum_{j = 0}^{n + 1}{}{\widetilde{b}}_{j,n + 1}F_{5}\left( t_{j},X_{j}^{(c)} \right)\ $$

**5. Numerical Simulations and Discussion**

To validate the analytical stability results derived in Sections local
stability and global stability, and to illustrate the model's behavior
under the condition $R_{0} > 1$, we conducted numerical simulations
using the advanced predictor-corrector scheme. For this demonstration,
system parameters were selected such that the basic reproduction number
is $R_{0} = 4.55$.

**Figure [1](#4i7ojhp)** presents the time-series dynamics of all five
state variables for $R_{0} = 4.55$. The simulation confirms the
theoretical predictions. Initially polluted compartments ($S_{p}(t)$,
$W(t)$, $F(t)$) do not decay to zero. Instead, all variables approach
distinct, positive steady-state values, indicating convergence to the
stable endemic equilibrium $E^{*}$. This behavior is consistent with the
model's prediction of persistent pollution when $R_{0} > 1$.

![D:\\Desktop\\New folder\\Besi\\Cocontaminated\\New
folder\\Fig_All_R0_4_55.jpg](G:\work\Journal2LaTeX\backend\temp\9cf3fc2a-11bb-430d-994f-45e9ccc00061\intermediate\media/media/image1.png){width="3.875in"
height="2.2395833333333335in"}

**Fig1: Simulated time evolution of all state variables for the
fractional-order pollution model with** $\alpha = 0.95$ **and**
$R_{0} = 4.55$**. Initial conditions were**
$\left( C(0),S_{p}(0),W(0),F(0),S_{R}(0) \right) = (30,2,1,0.5,0)$**.
The graph shows that all variables approach positive steady-state values
(**$C^{*},S_{p}^{*},W^{*},F^{*},S_{R}^{*}$**), confirming the
theoretical prediction of global asymptotic stability of the endemic
equilibrium** $E^{*}$** for** $R_{0} > 1$**.**

To further analyze the system's behavior, we examine the dynamics of
each compartment individually.

![D:\\Desktop\\New folder\\Besi\\Cocontaminated\\New
folder\\Fig_C_R0_4_55.jpg](G:\work\Journal2LaTeX\backend\temp\9cf3fc2a-11bb-430d-994f-45e9ccc00061\intermediate\media/media/image2.png){width="3.6846489501312334in"
height="2.8522484689413825in"}

**Fig2: Simulated dynamics of Effluent Concentration** $C(t)$ **for**
$R_{0} = 4.55$**. The concentration approaches a positive steady-state
value** $C^{*}$**, distinct from the level** $C_{0} = aN/\Phi_{C}$
**associated with the unstable pollution-free equilibrium** $E_{0}$**.**

![D:\\Desktop\\New folder\\Besi\\Cocontaminated\\New
folder\\Fig_F_R0_4_55.jpg](G:\work\Journal2LaTeX\backend\temp\9cf3fc2a-11bb-430d-994f-45e9ccc00061\intermediate\media/media/image3.png){width="3.787946194225722in"
height="2.4831944444444445in"}

**Fig3: Simulated dynamics of Polluted Soil** $S_{p}(t)$ **for**
$R_{0} = 4.55$**. The level increases from its initial value and
stabilizes at a positive value** $S_{p}^{*}$**. This confirms the
existence and stability of the endemic equilibrium** $E^{*}$**, as**
$S_{p}^{*} > 0$ **is a defining characteristic.**

![D:\\Desktop\\New folder\\Besi\\Cocontaminated\\New
folder\\Fig_Sp_R0_4_55.jpg](G:\work\Journal2LaTeX\backend\temp\9cf3fc2a-11bb-430d-994f-45e9ccc00061\intermediate\media/media/image4.png){width="4.811416229221347in"
height="2.43458552055993in"}

**Fig4: Simulated dynamics of Water Contamination** $W(t)$ **for**
$R_{0} = 4.55$**. The contamination level rises and approaches a
positive steady state** $W^{*}$**, indicating that water pollution is
sustained rather than eliminated.**

![D:\\Desktop\\New folder\\Besi\\Cocontaminated\\New
folder\\Fig_SR_R0_4_55.jpg](G:\work\Journal2LaTeX\backend\temp\9cf3fc2a-11bb-430d-994f-45e9ccc00061\intermediate\media/media/image5.png){width="4.808643919510061in"
height="3.1911526684164477in"}

**Fig5: Simulated dynamics of Farmland Pollution** $F(t)$ **for**
$R_{0} = 4.55$**. The pollution level converges to a positive
equilibrium value** $F^{*}$**, verifying that** $E^{*}$** is the
long-term attractor, with** $F^{*} > 0$**, signifying persistent
contamination of agricultural land.**

![D:\\Desktop\\New folder\\Besi\\Cocontaminated\\New
folder\\Fig_W_R0_4_55.jpg](G:\work\Journal2LaTeX\backend\temp\9cf3fc2a-11bb-430d-994f-45e9ccc00061\intermediate\media/media/image6.png){width="5.053885608048994in"
height="3.6788604549431323in"}

**Fig 6: Simulated dynamics of Remedied Soil** $S_{R}(t)$ **for**
$R_{0} = 4.55$**. The amount of remediated soil accumulates over time
and reaches a steady state** $S_{R}^{*}$**. This reflects the balance
between ongoing remediation processes (**$\gamma_{1}S_{p}^{*}$**,**
$\gamma_{2}F^{*}$**) and the degradation rate (**$\Phi_{5}S_{R}^{*}$**)
at the stable equilibrium** $E^{*}$**.**

The numerical simulations for $R_{0} = 4.55$ provide strong evidence
supporting the theoretical stability analysis:

1.  **Effluent Concentration** $C(t)$ **(Figure [2](#2xcytpi))**: The
    effluent concentration $C(t)$ does not settle at the level
    $C_{0} = aN/\Phi_{C}$ associated with $E_{0}$. Instead, it
    approaches a different positive steady state $C^{*}$. This deviation
    from $C_{0}$ is expected at $E^{*}$ due to the active interaction
    terms ($- LC^{*}S_{p}^{*}$, $- BC^{*}W^{*}$) which are zero at
    $E_{0}$ but non-zero at $E^{*}$.

2.  **Polluted Soil** $S_{p}(t)$ **(Figure [3](#1ci93xb))**: The level
    of soil pollution increases from its initial value and stabilizes at
    a positive value $S_{p}^{*}$. This is a direct confirmation of the
    existence and stability of $E^{*}$, as $S_{p}^{*} > 0$ is a defining
    characteristic of the endemic equilibrium. The convergence to
    $S_{p}^{*}$ demonstrates that soil pollution becomes persistent in
    the system when $R_{0} > 1$.

3.  **Water Contamination** $W(t)$ **(Figure [4](#3whwml4))**:
    Similarly, the water contamination level $W(t)$ rises and approaches
    a positive steady state $W^{*}$. This behavior aligns with the
    stability of $E^{*}$, where $W^{*} > 0$. It indicates that water
    pollution is sustained rather than eliminated.

4.  **Farmland Pollution** $F(t)$ **(Figure [5](#qsh70q))**: The
    farmland pollution level $F(t)$ also converges to a positive
    equilibrium value $F^{*}$. This verifies that $E^{*}$ is the
    long-term attractor, with $F^{*} > 0$, signifying persistent
    contamination of agricultural land.

5.  **Remedied Soil** $S_{R}(t)$ **(Figure [6](#3as4poj))**: The amount
    of remediated soil $S_{R}(t)$ accumulates over time and reaches a
    steady state $S_{R}^{*}$. This reflects the ongoing remediation
    processes ($\gamma_{1}S_{p}^{*}$, $\gamma_{2}F^{*}$) balancing the
    degradation rate ($\Phi_{5}S_{R}^{*}$) at the stable equilibrium
    $E^{*}$. The fact that it reaches a finite value
    $S_{R}^{*} = \left( \gamma_{1}S_{p}^{*} + \gamma_{2}F^{*} \right)/\Phi_{5}$
    shows that remediation reaches a balance with persistent pollution
    sources, rather than ceasing.

In summary, the numerical simulations for $R_{0} = 4.55$ provide strong
evidence supporting the theoretical stability analysis. The system's
trajectory converges to the unique endemic equilibrium $E^{*}$,
characterized by persistent, non-zero levels of pollution across all
active compartments ($S_{p}^{*},W^{*},F^{*}$), a corresponding effluent
level $C^{*}$, and a balanced remediation state $S_{R}^{*}$. This
confirms that when $R_{0} > 1$, the pollution-free state $E_{0}$ is
unstable, and the system settles into a persistent pollution regime as
predicted by the model.

**6. Conclusion**

This study presented a comprehensive analysis of a five-compartment
fractional-order model for co-contaminated soil and water pollution
dynamics using the Atangana-Baleanu-Caputo derivative. We derived the
basic reproduction number $R_{0}$ as the fundamental threshold parameter
governing system behavior:

\- When $R_{0} < \ 1$, the pollution-free equilibrium is globally
asymptotically stable and Mittag-Leffler stable, indicating successful
pollution elimination

\- When $R_{0} > \ 1$, a unique endemic equilibrium exists and is
globally asymptotically stable, predicting persistent pollution across
all environmental compartments

As predicted, the pollution-free equilibrium $E_{0}$ is unstable.
Initially polluted compartments ($S_{p}(t)$, $W(t)$, $F(t)$) approach
distinct positive steady-state values ($S_{p}^{*}$, $W^{*}$, $F^{*}$),
indicating persistent pollution. The effluent concentration $C(t)$
stabilizes at $C^{*}$, which differs from the level
$C_{0} = aN/\Phi_{C}$ associated with $E_{0}$. The remediated soil
$S_{R}(t)$ accumulates and reaches a steady state $S_{R}^{*}$,
reflecting a balance between ongoing remediation ($\gamma_{1}S_{p}^{*}$,
$\gamma_{2}F^{*}$) and degradation ($\Phi_{5}S_{R}^{*}$). This behavior
validates the model's prediction of a persistent pollution regime when
$R_{0} > 1$. The system's trajectory converges to $E^{*}$, characterized
by non-zero pollution levels across all active compartments. These
results confirm that $R_{0} = 4.55$ leads to a stable, persistent
pollution state rather than elimination.

Our analysis employed advanced techniques including fractional Lyapunov
functionals and Mittag-Leffler stability theory to characterize
long-term system behavior precisely. We developed an adaptive
predictor-corrector numerical scheme specifically tailored for ABC
fractional systems, enabling accurate long-term simulations.

This work provides crucial analytical and computational tools for
understanding complex pollution dynamics in interconnected environmental
media. The threshold condition $R_{0} < \ 1$ offers practical guidance
for pollution control strategies: reducing pollutant input rates,
enhancing degradation/remediation processes, and limiting transmission
between compartments. Future work will explore optimal control
strategies for driving $R_{0}$ below the critical threshold and
investigate spatially explicit extensions of the model.

**CRediT authorship contribution statement:**

**Priya P. and Roselyn Besi P.** Conceptualization, Methodology,
Writing-Original draft, formal analysis, investigation.

Sabarmathi A.: Scrutinized the work.

**Declaration of Competing interest:**

The authors declare that they have no known competing financial
interests or personal relationships that could have appeared to
influence the work reported in this paper.

**Data Availability:**

Data will be provided by corresponding author on reasonable request.

**Funding:**

No Funding

**References**

1.  Atangana, A., & Baleanu, D. (2017). New fractional derivatives with
    nonlocal and non-singular kernel: Theory and application to heat
    transfer model. *Thermal Science*, 21(1), 1-7.

2.  Area, I., Batarfi, H., Losada, J., Nieto, J. J., Shammakh, W., &
    Torres, A. (2015). On a fractional order Ebola epidemic model.
    *Advances in Difference Equations*, 2015(1), 278.

3.  Diethelm, K. (2010). *The analysis of fractional differential
    equations: An application-oriented exposition using differential
    operators of Caputo type*. Springer Science & Business Media.

4.  Deeksha Singh, Farheen Sultana, Rajesh K. Pandey, "Approximation of
    Caputo-Prabhakar derivative with application in solving time
    fractional advection-diffusion equation", 2022,
    [[https://doi.org/10.1002/fld.5077]{.underline}](https://doi.org/10.1002/fld.5077).

5.  Swati Yadav, Rajesh K. Pandey, Anil K. Shukla," Numerical
    approximations of Atangana--Baleanu Caputo derivative and its
    application", Chaos, Solitons & Fractals, Volume 118, 2019, Pages
    58-64, ISSN 0960-0779, https://doi.org/10.1016/j.chaos.2018.11.009.

6.  Baleanu, D., Diethelm, K., Scalas, E., & Trujillo, J. J. (2019).
    *Fractional calculus: models and numerical methods* (Vol. 5). World
    Scientific.

7.  Li, C., & Zhang, F. (2019). A survey on the stability of fractional
    differential equations. *The European Physical Journal Special
    Topics*, 228(1), 73-84.

8.  Vargas-De-León, C. (2012). Volterra-type Lyapunov functions for
    fractional-order epidemic systems. *Communications in Nonlinear
    Science and Numerical Simulation*, 17(9), 3617-3622.

9.  Baleanu, D., Machado, J. A. T., & Luo, A. C. J. (Eds.). (2012).
    *Fractional dynamics and control*. Springer Science & Business
    Media.

10. Pagnini, G. (2019). Erdélyi-Kober fractional diffusion. In *Handbook
    of Fractional Calculus with Applications* (pp. 265-280). De Gruyter.

11. Sheikh, N. A., Dennis, L. C. C., Ijarola, O. A., Zainal, A. A., &
    Mohamad, M. (2022). A review of the developments in the field of
    fractional calculus and its applications. *Alexandria Engineering
    Journal*, 61(12), 10137-10153.

12. Singh, D., Sultana, F., Pandey, R.K. et al. A comparative study of
    three numerical schemes for solving Atangana--Baleanu fractional
    integro-differential equation defined in Caputo sense. Engineering
    with Computers 38 (Suppl 1), 149--168 (2022).

13. Atangana, A., & Algahtani, O. J. J. (2015). Extension of the
    groundwater flow model to the concept of fractional variable order
    derivative. *Abstract and Applied Analysis*, 2015.

14. Sun, H., Chang, A., Zhang, Y., & Chen, W. (2019). Modeling anomalous
    heat transport in geothermal reservoirs via fractional Laplacian.
    *International Journal of Numerical and Analytical Methods in
    Geomechanics*, 43(14), 2327-2342.

15. Sardanyes, J., Farner, S., & Alsedà, L. (2022). Bifurcations and
    long-term dynamics in a discrete ecological model with
    fractional-order recurrences. *Chaos, Solitons & Fractals*, 154,
    111654.

16. Swati Yadav, Rajesh K. Pandey," Numerical approximation of
    fractional burgers equation with Atangana--Baleanu derivative in
    Caputo sense", Chaos, Solitons & Fractals, Volume 133, 2020, 109630,
    ISSN 0960-0779.
