**Optimal control strategies for overwhelming social media scrolling
addiction by using fractional order mathematical modelling**

**G.M. Vijayalakshmi ^1^, G. Susila^\*^ ^1,2^, [Z. Che Muda ^3^,]{.mark}
Sudesh Nair Baskara^3^, P. Roselyn Besi ^4^, Ali Akgül ^5,6\*^**

^1^Department of Mathematics, Vel Tech Rangarajan Dr. Sagunthala R & D
Institute of Science and Technology, Avadi, Tamil Nadu, 600 062, India.

^2^Meenakshi College of Engineering, Chennai -78

[^3^Department of Civil Engineering, Faculty of Engineering and Quantity
Surveyor, INTI International University, 71800 Nilai, Negeri Sembilan,
Malaysia]{.mark}

^4^Coimbatore Institute of Technology, Coimbatore-641014.

^5^Department of Electronics and Communication Engineering, Saveetha
School of Engineering, SIMATS, Chennai, Tamilnadu, India

^6^Siirt University, Art and Science Faculty, Department of Mathematics,
56100 Siirt, Türkiye

Correspondence: aliakgul@siirt.edu.tr, susimohi@gmail.com

ABSTRACT: Scrolling in mobile allows navigation through information
beyond the visible display. Scrolling addiction, sometimes known as
\"doom scrolling\" or excessive feed consumption, has become a severe
behavioral concern in the digital age. However, its addictive nature has
generated worries about excessive screen time, mental weariness, a
detrimental influence on [mental health]{.mark}, social comparison, low
self-esteem, and decreased productivity. This study introduces a novel
fractional order mathematical model for scrolling, taking into account
the app\'s usage as an epidemic. The model is carefully confirmed using
stability analyses of both local and global equilibrium. Furthermore,
disease-free and non-trivial equilibrium scenarios are examined by
estimating their reproduction rates. This study seeks to raise awareness
of scrolling\'s possible misuse and to investigate control theory
remedies to addiction by using Optimal control theory. Furthermore,
statistical data is used to illustrate numerical findings and
investigate the effect of control factors on the scrolling model.

Keywords: Scrolling addiction, Fractional--order Caputo model, Optimal
control theory,

Numerical Simulation, Behavioural epidemiology, [Mental health]{.mark}
intervention.

**Contents**

1\. Introduction

2\. Fractional Elementary Concepts

3\. Model Formulation

4\. Stability analysis

**5.** Optimal Control Theory

6\. Numerical simulation

7\. Conclusion

1.  **Introduction**

In the current digital era, smartphones have become an essential part of
our lives, especially for young people. With more than 6.04 billion
individuals using the internet worldwide, social media networks have
become more significant but also present challenges. Particularly among
Indian youth, more than 60% of those between the ages of 9 and 17 spend
more than three hours a day on social media or gaming websites. Concerns
regarding scrolling addiction, a behavioral habit characterized by
excessive and compulsive scrolling and [mental health]{.mark} issues
sometimes accompanied by feelings of guilt, anxiety and decreased
productivity have been raised by this increased \[1-[10]{.mark}\] screen
time.

Strong tools for comprehending such intricate biological and social
systems are mathematical models. They offer organized frameworks for
depicting interactions, forecasting results, and identifying trends in
data. Models show how changes in one component affect system-wide
behavior by quantifying important variables. Mathematical modeling is
used in many different domains, such as fluid mechanics, neurobiology,
and the dynamics of infectious diseases. Crucially, these models enable
researchers to replicate situations that could be difficult, expensive,
or immoral to evaluate experimentally \[11--14\]. This prediction
ability advances scientific knowledge and directs evidence-based
decision-making in public health, neurology, and medicine. Fractional
mathematical models have become more significant in recent years due to
their ability to better represent real-world dynamics, especially memory
and heredity effects, which are generally ignored by classical
integer-order models \[8, 11\].

When examining irregular phenomena like anomalous diffusion, fractional
calculus provides more flexibility \[13,23\], allowing for the creation
of more practical and efficient solutions. The complexity of drug
addiction is reflected in the literature. The interaction of biological,
psychological, and social elements in determining addiction consequences
is constantly highlighted by research. Research highlights the
significance of neurochemical changes, environmental stresses,
hereditary predisposition, and the difficulties of chronicity and
relapse. For instance, Vandaele and Ahmed (2021) investigated the shift
from voluntary behavior to compulsive usage, concentrating on underlying
brain circuits, while De Angelis et al. (2020) showed the negative
consequences of smoking, drinking, and drug addiction on female
fertility.

Ceceli, Bradberry, and Goldstein (2022) \[15\] examined prefrontal brain
pathology and shown how addiction affects impulse control and
decision-making. Zanib et al. (2024) \[16\] presented a compartmental
framework (SD, ED, HD, LD, RD, CD) that differentiates between severe
and light addiction in addition to rehabilitation from a modeling
standpoint. The significance of early detection and treatment in
managing addiction was emphasized by their simulations using the RK4
approach in Maple. In their comprehensive review of recovery capital,
Bunaciu et al. (2024) \[17\] offered instruments to assess the strengths
that facilitate long-term recovery.

While Muli (2025) \[19\] expanded this paradigm to incorporate policing
and rehabilitation, drawing comparisons with infectious disease models,
other studies, including Mamo et al. (2024) \[18\], looked at the
dynamic interaction between crime and drug misuse. L. Yaseen et al. /
Eur. J. Pure Appl. Math, 18 (4) (2025), 6711 3 of 29 targeted
interventions can significantly lower addiction rates and social costs,
according to Alharbi et al. (2025) \[20\]\'s four-compartment model that
incorporates social factors. Artificial intelligence (AI) has also been
incorporated into new methods. According to Kim et al. (2025) \[21\],
AI-mediated communication can increase participation and health outcomes
by improving treatment, prevention, and control techniques.

Following a review of the literature, we discovered a number of research
gaps. In order to fill these gaps, we created a mathematical model that
distinguishes between those who are at high and low risk of addiction by
incorporating the crucial idea of proneness. This idea is used in
conjunction with treatment as a control technique to lessen drug
addiction. It represents the vulnerability of people or communities to
particular consequences. Proneness is frequently used to evaluate
vulnerabilities resulting from social and environmental factors, such as
disease outbreaks and ecological shifts \[20--25\]. The current study
offers a thorough mathematical model of drug addiction dynamics,
building on this foundation. The model determines important threshold
values, evaluates stability and sensitivity, and categorizes groups
based on risk level and treatment status.

Numerical simulations illustrate the crucial elements affecting the
spread and control of addiction, while the fundamental reproduction
number is computed to evaluate the potential for addiction transmission.
The results highlight the significance of prompt treatment interventions
and offer insightful information for developing successful public health
initiatives to lower substance usage \[15--20\].

2.  **Fractional Elementary Concepts**

The basic definitions are presented related to fractional calculus.

**Definition 2.1 RLFI \[Riemann -- Liouville fractional integral\]**

A function $B(t) \in L^{1}(\lbrack a,b\rbrack,R)$ has a fractional
integral of order $\alpha^{\ast}\epsilon R^{+}$, which is specified as
$I_{a +}^{\alpha^{\ast}}B(t) = \frac{1}{\Gamma(\alpha^{\ast})}\int_{0}^{t}{}{(t - s)}^{\alpha^{\ast} - 1}B(s)ds$.
(2.1)

**Definition 2.2 CFOD \[Caputo -- Fractional Order Derivative\]**

The function\'s Caputo fractional-order derivative is

${\ \ cD}_{0 +}^{\alpha^{\ast}}B(t) = \ \frac{1}{\Gamma(n - \alpha^{\ast})}\int_{0}^{t}{}(t - s)^{n - \alpha^{\ast} - 1}B^{n}(s)ds$
(2.2) $B(t) \in C^{n}\lbrack a,b\rbrack$ in this case,
$0 < \alpha^{\ast} < 1,\ \ n = \lbrack\alpha^{\ast}\rbrack + 1.$

# 3. Model Formulation

To analyse the transmission of addiction dynamics through the Caputo
fractional operator, we examine the tuberculosis model given in \[10\] .
Based on their correlation with scrolling addiction, the entire human
population is divided into six groups. The social media Scrolling
Addiction Model (SAM), which takes into consideration different
treatment types and risk levels, is broken up into six compartments.
They are

$S(t) - \$ Susceptible- Individuals that are susceptible to scrolling
addiction, frequently as a result of their social media presence or peer
influence.

$E(t)$ - Exposed - People who are occasionally exposed to scrolling
triggers but have not yet become hooked.

$I(t)$ - Addicted - Individuals who engage in compulsive scrolling have
reported negative consequences on their mental health or relationships.

$T(t) -$Treated - People seeking assistance or implementing ways to
reduce scrolling.

$R(t)$- Recovered - Those who\'ve reduced scrolling.

$L(t)$ -- Relaps - Those who return to excessive scrolling after
attempting recovery

**3.1 Scrolling Addiction Model**

![](G:\work\Journal2LaTeX\backend\temp\81805053-33ba-4272-96aa-99d478ddc373\intermediate\media/media/image1.png){width="5.319444444444445in"
height="4.083333333333333in"}

**3.2 Parameters**

λ -- Recruitment rate.

b -- Contact/interaction rate between susceptible and addicted
individuals.

N -- Total population size.

ξ -- Natural exit rate.

β -- Progression rate from exposed to addicted.

τ -- Transition feedback from exposed to latent.

γ -- Treatment rate.

δ -- Recovery rate.

ρ -- Relapse rate.

σ -- Latent return rate.

The nonlinear fractional differential system under these assumptions is
described as follows.

$CD_{t}^{\alpha}\ S(t) = \lambda - \frac{b\ SI}{N} - \xi S\ CD_{t}^{\alpha}\ E(t) = \frac{b\ SI}{N} - \xi E - \beta E + \tau\ E\ CD_{t}^{\alpha}\ I(t) = \beta E(t) - \xi\ I - \gamma I + \sigma\ L\ CD_{t}^{\alpha}T(t) = \gamma I - \xi\ T - \delta T\ CD_{t}^{\alpha}R(t) = \delta T - \xi\ R - \rho R\ CD_{t}^{\alpha}L(t) = \rho R - \xi\ L - \sigma\ L - \tau\ E\ \}$
(3.1)

**3.3 Properties of the Model**

**3.3.1. Positively Invariant Region**

SAM is explored in a feasible region $N \subset \ R_{+}^{6}$ such that
$\Omega = \ \left\{ S(t),E(t),I(t),T(t),R(t),\ L(t)\epsilon R^{}:N(t) \leq \frac{\lambda}{\xi} \right\}$
. (3.2)

**Lemma 3.1** $N \subset \ R_{+}^{6}$ is a region that is positively
invariant and has nonnegative beginning conditions for model (3.1) in
$R_{+}^{6}.$

Proof. The net populace becomes

$$CD_{t}^{\alpha}\ N(t) = CD_{t}^{\alpha}\ S(t) + CD_{t}^{\alpha}\ E(t) + CD_{t}^{\alpha}\ I(t) + CD_{t}^{\alpha}T(t) + CD_{t}^{\alpha}R(t) + CD_{t}^{\alpha}L(t)$$

and then, we have $CD_{t}^{\alpha}\ N(t) + \xi N(t) \leq \lambda$ (3.3)

Integrating (3.3) we get $N(t) \leq \frac{\lambda}{\xi}$. (3.4)

Our SAM solution with nonnegative requirements in Ω remains in
$R_{+}^{6}$, since Ω is positive invariant and attracts all solutions in
Ω.

We now define the positivity of the model solution.

$R_{+}^{6} = {\{ u\epsilon R_{+}^{6}\ and\ \ \ u(t) = (S(t),E(t),I(t),T(t),R(t),L(t))}^{T}.$
(3.5)

**Lemma 3.2** We recognized that $j(t)\epsilon U\lbrack c,d\rbrack$ and
$CD_{t}^{\alpha}\ j(t)\epsilon\ (c,d\rbrack$ where
$\alpha \in (0,1\rbrack$. If
$CD_{t}^{\alpha}\ j(t)\epsilon\ (c,d\rbrack \geq 0,\forall u \in (c,d)$
then $j(t)$ is non -decreasing.

$CD_{t}^{\alpha}\ j(t)\epsilon\ (c,d\rbrack \leq 0,\forall u \in (c,d)$
then $j(t)$ is decreasing.

**3**$\mathbf{.3.2}$ **Positivity and Boundedness**

**Lemma 3.3** SAM solution is non-negative and bounded by
$\forall(S(0),E(0),I(0),T(0),R(0),L(0))\epsilon R_{+}^{6}$ for t \>0.

Proof. At the initial condition Model (3.1) gives

> $CD_{t}^{\alpha}\ {S|}_{S = 0} = \lambda > 0,\ CD_{t}^{\alpha}\ {E|}_{E = 0} = \frac{b\ SI}{N} \geq 0,\ CD_{t}^{\alpha}{I|}_{I = 0} = \beta E(t) + \sigma\ L \geq 0,\ CD_{t}^{\alpha}{T|}_{T = 0} = \gamma I \geq 0,\ CD_{t}^{\alpha}R|_{R = 0} = \delta T \geq 0,\ CD_{t}^{\alpha}L|_{L = 0} = \rho R \geq 0,\ \}$
> (3.6)

then by **Lemma 3.2** $S(t),E(t),I(t),T(t),R(t)\ \&\ L(t)\$ are non
decreasing .

Hence
$\Omega = \ \left\{ \ (S,E,I,T,R,L)\epsilon R_{+}^{5}:\ (S,E,I,T,R,L) \geq 0 \right\}.$
(3.7)

As a result, the SAM solution is bounded.

**3.4 Basic reproduction number**

To find the reproduction number we use Next Generation Matrix method.
$SS^{\ast}$

> $y = (S\ E\ \ I\ T\ R\ L\ )$ (3.8)

We take our model as $\frac{dy}{dt} = \ v(y) - w(y)$ (3.9)

Where $v(y) = \left( \frac{b\ SI}{N}\ 0\ 0\ 0\  \right)$ and
$w(y) = \left( \ (\xi + \beta)E\  - \beta E + (\xi + \gamma)I - \sigma\ L\  - \gamma I + (\xi + \delta)T\  - \rho R + (\xi + \sigma)\ L\  \right)$
(3.10)

Then the jacobian matrices for $v(y)\$ and $w(y)$ are given as

$J_{D_{f}}^{w} = \ \left( \xi + \beta - \tau\ 0\ 0\ 0\  - \beta\ \xi + \gamma\ 0\  - \sigma\ 0\  - \gamma\ \xi + \delta\ 0\  - \tau\ 0\ 0\ \xi + \sigma)\  \right)$and
$J_{D_{f}}^{v} = \ \left( \frac{b\ S}{N}\ 0\ 0\ 0\ 0\ 0\ 0\ 0\ 0\ 0\ 0\ 0\ 0\ 0\ 0\ 0\  \right)$.
(3.11)

The basic reproduction number is the spectral radius of
$\left( J_{D_{f}}^{v}({J_{D_{f}}^{w})}^{- 1} \right)$.

Thus the reproduction number $R_{0}$ is given by

$R_{0} = \frac{b\ \lambda(\xi + \delta)\lbrack\beta\ \ (\xi + \sigma) + \tau\sigma\rbrack}{\ \ N\xi(\xi + \beta - \tau)\lbrack(\xi + \gamma)(\xi + \delta)\ (\xi + \sigma)}$
(3.12)

If $\ R_{0} < 1$, scrolling addiction dies out and if $R_{0} > 1\ \$
addiction persists at endemic levels.

**3.5 SAM equilibriums**

The fractional system (3.1) have at the most two equilibriums which are
scrolling addiction-free equilibrium (SAFE)
${\ E}_{0} = \ (\frac{\lambda}{\xi}$,0,0,0,0,0) and Scrolling Addiction
Endemic Equilibrium (SAEE)
${\ E}_{1} = \left( S^{\ast},E^{\ast},I^{\ast},T^{\ast},R^{\ast},\ L^{\ast} \right)$
among the population.

**Theorem 3.1** SAM admits a unique SAFE is given by
${\ E}_{0} = \ (\frac{\lambda}{\xi}$,0,0,0,0,0). (3.13)

Proof

At $(S,0,0,0,0,0)$ the addiction free or SAFE is
${\ E}_{0}\  = \ (\frac{\lambda}{\xi},0,0,0,0,0).\$ (3.14)

**Theorem.3.2** SAM admits a unique SAEE
${\ E}_{1} = \left( S^{\ast}(t),E^{\ast}(t),I^{\ast}(t),T^{\ast}(t),R^{\ast}(t),\ L^{\ast}(t) \right).$
(3.15)

Proof

Scrolling addiction persists in the population. given by

${\ E}_{1} = \left( S^{\ast}(t),E^{\ast}(t),I^{\ast}(t),T^{\ast}(t),R^{\ast}(t),\ L^{\ast}(t) \right).$

SEE of model (1) is determined by

To get the equilibria for scrolling addiction system (3.1)

$CD_{t}^{\alpha}\ S = CD_{t}^{\alpha}\ E = CD_{t}^{\alpha}\ I = CD_{t}^{\alpha}T = CD_{t}^{\alpha}R = CD_{t}^{\alpha}L = 0$
(3.16

Therefore

$$\frac{b\ SI}{N} - \xi E - \beta E = 0$$

$\beta E(t) - \xi\ I - \gamma I + \sigma\ L = 0$ (3.17)

$$\gamma I - \xi\ T - \delta T = 0$$

$$\delta T - \xi\ R - \rho R = 0$$

$$\rho R - \xi\ L - \sigma\ L,$$

If we solve the above equations we get

$S^{\ast}(t) = \frac{N}{R_{0}}$

$\ E^{\ast}(t) = \ \frac{\xi + \gamma - \sigma\ K}{\beta}{\ I}^{\ast} = \frac{(\xi + \gamma - \sigma\ K)(}{\beta}\frac{\xi N)}{b}(R_{0} - 1)$
${\ I}^{\ast}(t) = \frac{\xi N}{b}(R_{0} - 1)$

$T^{\ast}(t) = \frac{\gamma}{(\xi + \delta)}{\ I}^{\ast} = \frac{\gamma\xi N}{(\xi + \delta)b}(R_{0} - 1)$
(3.18)

$R^{\ast}(t) = \frac{\delta}{(\xi + \rho)}T^{\ast} = \frac{\delta\gamma\xi N}{(\xi + \rho)(\xi + \delta)b}(R_{0} - 1)$

$L^{\ast}(t) = \frac{\rho}{(\xi + \sigma\ )}R^{\ast} = \ \frac{\rho\delta\gamma\xi N}{(\xi + \rho)(\xi + \delta)(\xi + \sigma\ )b}\ \ (R_{0} - 1)$.

**4. Stability analysis**

**Theorem 4.1**

The fractional order SAM is locally asymptotically stable at SAFE if
$R_{0} < 1.$

Proof

The Jacobian matrix of ${\ E}_{0}\$ is defined by

$J\left( {\ E}_{0} \right) = \left( - \xi\ 0\  - b\ 0\ 0\ 0\ 0\  - (\xi + \beta\ )\ b\ 0\ 0\ 0\ 0\ \beta\  - (\xi + \gamma)\ 0\ 0\ \sigma\ \ 0\ 0\ \gamma\  - (\xi + \delta)\ 0\ 0\ 0\ 0\ 0\ \delta\  - (\xi + \rho)\ 0\ 0\ 0\ 0\ 0\ \rho\  - (\xi + \sigma)\  \right)$
(4.1)

Let the diagonal elements of the above Jacobian matrix as

> $c_{1} = \ \xi$,
>
> $c_{2} = \ \xi + \delta$,

$$c_{3} = (\xi + \rho)$$

$$c_{4} = \ \xi + \sigma$$

> $c_{5} = \xi + \beta$,
>
> $c_{6} = \ \xi + \gamma$,

The characteristic polynomial of the above Jacobian matrix

$\left| J\left( {\ E}_{0} \right) - \lambda I \right| = \lambda^{6} + A_{1}\lambda^{5} + A_{2}\lambda^{4} + A_{3}\lambda^{3} + A_{4}\lambda^{2} + A_{5}\lambda + A_{6}$
(4.2) The coefficients for the polynomial are

$A_{1} = \sum_{i = 1\ \ }^{6}{}c_{i}$,${\ A}_{2} = \sum_{i = 1\ \ }^{6}{}c_{i}c_{j} - b\beta$
(4.3)

$${\ \ A}_{3} = \sum_{1 \leq i < j < k \leq 4\ \ }^{}{}c_{i}c_{j}c_{k} + {(c}_{5} + c_{6})\sum_{1 \leq i < j \leq 4\ \ }^{}{}c_{i}c_{j} + (c_{5}c_{6} - b\beta)\sum_{i = 1\ \ }^{4}{}c_{i}$$

(4.4)

$${\ \ A}_{4} = \sum_{1 \leq i < j < k < l \leq 4\ \ }^{}{}c_{i}c_{j}c_{k}c_{l} + {(c}_{5} + c_{6})\sum_{1 \leq i < j < k \leq 4\ \ }^{}{}c_{i}c_{j}c_{k}$$

$+ (c_{5}c_{6} - b\beta)\sum_{1 \leq i < j \leq 4\ \ }^{}{}c_{i}c_{j}$
(4.5)

${\ A}_{5} = \ {{(c}_{5} + c_{6})c}_{1}c_{2}c_{3}c_{4} + (c_{5}c_{6} - b\beta)\sum_{1 \leq i < j < k \leq 4\ \ }^{}{}c_{i}c_{j}c_{k}$
(4.6)

${\ \ A}_{6} = \xi\ (\xi + \delta)(\ \xi + \sigma)(\xi + \rho)\lbrack(\xi + \beta)(\xi + \gamma) - b\beta\ \rbrack$
(4.7)

It is clearly observe that $A_{3},A_{4}\ and\ A_{5}$ are strictly
positive.

${A_{5}\ and\ A}_{6} > 0$ only if $R_{0} < 1$.

Therefore SAFE is locally asymptotically stable only if $R_{0} < 1.$

**Theorem 4.2**

The fractional order SAM is globally asymptotically stable at SAFE if
$R_{0} < 1.$

Let us define the Lyapunov function V as

$V = x_{1}\left( S - S^{\ast} - S^{\ast}\ In\ \frac{S}{S^{\ast}} \right) + x_{2}\left( E - E^{\ast} - E^{\ast}\ In\ \frac{E}{E^{\ast}} \right) + x_{3}\left( I - I^{\ast} - I^{\ast}\ In\ \frac{I}{I^{\ast}} \right)x_{4} + x_{4}\left( T - T^{\ast} - T^{\ast}\ In\ \frac{T}{T^{\ast}} \right) + x_{5}\left( R - R^{\ast} - R^{\ast}\ In\ \frac{R}{R^{\ast}} \right) + x_{6}\left( L - L^{\ast} - L^{\ast}\ In\ \frac{L}{L^{\ast}} \right)$
(4.8)

Where $x_{i}$ are the undetermined coefficient.

Then

$V' = x_{1}\left( 1 - \frac{S}{S^{\ast}} \right)S' + x_{2}\left( 1 - \frac{E}{E^{\ast}} \right)E' + x_{3}\left( 1 - \frac{I}{I^{\ast}} \right)I' + x_{4}\left( \left( 1 - \frac{T}{T^{\ast}} \right)T' \right) + x_{5}\left( 1 - \frac{R}{R^{\ast}} \right)R' + x_{6}\left( 1 - \frac{L}{L^{\ast}} \right)L'$
(4.9)

$$V' = x_{1}\left( 1 - \frac{S}{S^{\ast}} \right)\left( \ \lambda - \frac{b\ SI}{N} - \xi S \right) + x_{2}\left( 1 - \frac{E}{E^{\ast}} \right)\left( \frac{b\ SI}{N} - \xi E - \beta E + \tau\ E \right) + x_{3}\left( 1 - \frac{I}{I^{\ast}} \right)\left( \beta E(t) - \xi\ I - \gamma I + \sigma\ L \right) + x_{4}\left( \left( 1 - \frac{T}{T^{\ast}} \right)CD_{t}^{\alpha}T(t) = \gamma I - \xi\ T - \delta T \right) + x_{5}\left( 1 - \frac{R}{R^{\ast}} \right)(\delta T - \xi\ R - \rho R) + x_{6}\left( 1 - \frac{L}{L^{\ast}} \right)(\rho R - \xi\ L - \sigma\ L - \tau\ E).$$

$$V' = x_{1}\left( 1 - \frac{S}{S^{\ast}} \right)\left( \ \lambda - \frac{b\ SI}{N} - \xi S \right) + x_{2}\left( 1 - \frac{E}{E^{\ast}} \right)\left( \frac{b\ SI}{N} - \xi E - \beta E + \tau\ E \right) + x_{3}\left( 1 - \frac{I}{I^{\ast}} \right)\left( \beta E(t) - \xi\ I - \gamma I + \sigma\ L \right) + x_{4}\left( \left( 1 - \frac{T}{T^{\ast}} \right)(\gamma I - \xi\ T - \delta T \right) + x_{5}\left( 1 - \frac{R}{R^{\ast}} \right)(\delta T - \xi\ R - \rho R) + x_{6}\left( 1 - \frac{L}{L^{\ast}} \right)(\rho R - \xi\ L - \sigma\ L - \tau\ E)$$

$$V' = x_{1}\left( 1 - \frac{S}{S^{\ast}} \right)\left( \ \lambda - \frac{b\ SI}{N} - \xi S \right) + x_{2}\left( 1 - \frac{E}{E^{\ast}} \right)\left( \frac{b\ SI}{N} - \xi E - \beta E + \tau\ E \right) + x_{3}\left( 1 - \frac{I}{I^{\ast}} \right)\left( \beta E(t) - \xi\ I - \gamma I + \sigma\ L \right) + x_{4}\left( \left( 1 - \frac{T}{T^{\ast}} \right)(\gamma I - \xi\ T - \delta T \right) + x_{5}\left( 1 - \frac{R}{R^{\ast}} \right)(\delta T - \xi\ R - \rho R) + x_{6}\left( 1 - \frac{L}{L^{\ast}} \right)(\rho R - \xi\ L - \sigma\ L - \tau\ E)$$

At addiction free
$E^{\ast} = I^{\ast} = T^{\ast} = R^{\ast} = \ \ L^{\ast} = 0$.

$V' = x_{1}\left( 1 - \frac{S}{S^{\ast}} \right)(\ \lambda - \xi S) < - x_{1}\xi$
(4.13)

Thus $V' < 0$ whenever $R_{0} < 1$.

Therefore, fractional order SAM is globally asymptotically stable at the
SAFE if $R_{0} < 1.$

**5. Optimal Control Theory**

In this section, we initially created three control variables,
$u_{1}$,$\ u_{2}$, and $u_{3}$ based on the presence status of the
scrolling addiction from being hooked to scrolling since the addiction
is present in the susceptible and exposed population. Among these,
$u_{1}$ stands for education or awareness control, which, for instance,
lowers contact rate b and susceptibility. $u_{2}$denotes prompt
symptomatic treatment and rehabilitation for monitoring, which speeds up
the transition from addiction to recovery and treatment.$\ u_{3}$ stands
for relapse prevention control, which lowers immunity loss and relapse.
The forward-backward scanning algorithm optimizes the control function.
We obtain the following equation based on our control variables,
$u_{1}$,$\ u_{2}$, and $u_{3}$

$CD_{t}^{\alpha}\ E(t) = \frac{b\ (1 - u_{1})SI}{N} - \xi E - \beta E + \tau\ E,$

$CD_{t}^{\alpha}\ I(t) = \beta E(t) - (\xi + \gamma + u_{2})I + \sigma\ L,$
(5.1)

$$CD_{t}^{\alpha}T(t) = (\gamma{+ u}_{2})I - \xi\ T - \delta T,$$

$$CD_{t}^{\alpha}R(t) = \delta T - (\xi + \rho\left( 1 - u_{3} \right))R,$$

$CD_{t}^{\alpha}L(t) = \rho\left( 1 - u_{3} \right)R - \xi\ L - \sigma(1 - u_{3})\ \ L - \tau\ E,$

Subject to the initial condition

$S(0) = S_{0},E(0) = E_{0},I(0) = I_{0},T(0) = T_{0},R(0) = R_{0},L(0) = L_{0}$
(5.2)

In our system three control variables are applied in optimal control
analysis with the two primary goals of minimizing control costs and
controlling addiction. To do this, we present the objective function
that follows. The objective functional for the minimization problem is
as follows,

$O = {mini}_{\left( u_{1},u_{2},u_{3} \right)}\int_{0}^{t_{f}}{}(c_{1}S + c_{2}\ I + c_{3}L + \frac{1}{2}\left( c_{3}{u_{1}}^{2} + c_{4}{u_{2}}^{2} + c_{5}{u_{3}}^{2} \right)dt\ \ \ \ \ \ \$(5.3)

each control is bounded $0 \leq u_{i} \leq 1$. i= 1,2,3.

The weight constants of $S,\ I\ and\ L$ are denoted by
$c_{1},c_{2}\ and\ c_{3}$, while the weight constants of the control
variables $u_{1},u_{2}\ and\ u_{3}$ are denoted by
$c_{3},c_{4}\ and\ c_{5}$.Additionally, these control variables are
defined as $u_{1}$ for $S$ to lessen vulnerability and exposure to
addictive scrolling, $u_{2}$ for $I$ to improve recovery and treatment
success, and $u_{3}$ for$\ L$ to lessen immunity loss and relapse.

Only terms that can benefit from these controls have been assigned these
parameters. For example, the term $\frac{b\ SI}{N}$, describes the
population among susceptible interacting users with infected ones. As a
result, in comparison to other populations, the control parameter will
effectively affect these variables.

Fractional optimum control issues can now be solved using Pontryagin\'s
maximum principle (PMP).

The Hamiltonian function is defined by

$H = c_{1}\ S + c_{2}\ I + c_{3}L + \frac{1}{2}\left( c_{3}{u_{1}}^{2} + c_{4}{u_{2}}^{2} + c_{5}{u_{3}}^{2} \right) + \Phi_{1}\left( {cD}_{0 +}^{\alpha}S(t)(t) \right) + \Phi_{2}\left( {cD}_{0 +}^{\alpha}E(t) \right)\ \ \ \ \ \  + \Phi_{3}\left( {cD}_{0 +}^{\alpha}I(t)(t) \right) + \Phi_{4}{cD}_{0 +}^{\alpha}T(t) + \Phi_{5}{cD}_{0 +}^{\alpha}R(t) + \Phi_{6}{cD}_{0 +}^{\alpha}L(t)\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \$
(5.4)

The adjoint variables
$\Phi_{1},\Phi_{2},\Phi_{3},\Phi_{4},\Phi_{5}\ \&\ \Phi_{6}$ correspond
to the state variables $S,E,I,T,R\ \&\ L$ respectively

Next, we will use Agrawal's method to solve fractional optimal control
problems (FOCP) \[38\].

Theorem 5.1. Set $u_{1}^{\ast}$,$\ u_{2}^{\ast}$ and $u_{3}^{\ast}$ for
the control system of control variables . Then the control variable can
be expressed as

$\{ u_{1}^{\ast} = \left\{ 0,\left( 1,\frac{\left( \Phi_{1} - \Phi_{2} \right)SI}{c_{1}} \right)\  \right\}\ \ u_{2}^{\ast} = \left\{ 0,\left( 1,\frac{\left( \Phi_{2} - \Phi_{3} \right)I}{c_{2}} \right)\  \right\}\ \ u_{3}^{\ast} = \left\{ 0,\left( 1,\frac{\left( \Phi_{3} - \Phi_{6} \right)L}{c_{3}} \right)\  \right\}\ \$
(5.5)

where the adoint variables
$,\Phi_{1},\Phi_{2},\Phi_{3,},\Phi_{4},\Phi_{5}\ and\ \Phi_{6}$
satisfying

$${cD}_{0 +}^{\alpha}\Phi_{1} = {- c}_{1} + \frac{b\ \left( 1 - u_{1} \right)I}{N}\left( \Phi_{1} - \Phi_{2} \right) + {\xi\Phi}_{1}$$

${cD}_{0 +}^{\alpha}\Phi_{2} = \beta\left( \Phi_{2} - \Phi_{3} \right) + \Phi_{2}\xi + (\Phi_{6} - \Phi_{2})\tau$

${cD}_{0 +}^{\alpha}\Phi_{3} = \ \frac{b\ \left( 1 - u_{1} \right)S}{N}\left( \Phi_{1} - \Phi_{3} \right) + (\gamma{+ u}_{2})\left( \Phi_{3} - \Phi_{4} \right) + \ \xi\Phi_{3}$
(5.6)

$${cD}_{0 +}^{\alpha}\Phi_{4} = \ \delta\left( \Phi_{4} - \Phi_{5} \right) + \xi\Phi_{4}$$

$${cD}_{0 +}^{\alpha}\Phi_{5} = \left( \Phi_{5} - \Phi_{6} \right)\rho\left( 1 - u_{3} \right) + \Phi_{5}\xi\ $$

$${cD}_{0 +}^{\alpha}\Phi_{6} = \  - c_{3}\left( \Phi_{6} - \Phi_{3} \right)\sigma + \Phi_{6}\xi$$

have boundary conditions
$\Phi_{1}\left( t_{f} \right) = \Phi_{2}\left( t_{f} \right) = \Phi_{3}\left( t_{f} \right) = \Phi_{4}\left( t_{f} \right) = \Phi_{5}\left( t_{f} \right) = \Phi_{6}\left( t_{f} \right) = 0,$

Proof

The system of adjoint variables can be formed from the Hamiltonian
function using the following relations and have boundary conditions.

${cD}_{0 +}^{\alpha}\Phi_{1} = \frac{- \partial H}{\partial S} = {- c}_{1} + \Phi_{1}\left\lbrack \frac{b\ \left( 1 - u_{1} \right)I}{N} + \xi \right\rbrack{- \Phi}_{2}\left\lbrack \frac{b\ \left( 1 - u_{1} \right)I}{N} \right\rbrack = \ {- c}_{1} + \frac{b\ \left( 1 - u_{1} \right)I}{N}\left( \Phi_{1} - \Phi_{2} \right) + {\xi\Phi}_{1}$,

${cD}_{0 +}^{\alpha}\Phi_{2} = \frac{- \partial H}{\ \ \partial E} = \Phi_{2}(\xi + \beta - \tau) - \Phi_{3}\beta + \Phi_{6}\tau = \beta\left( \Phi_{2} - \Phi_{3} \right) + \Phi_{2}\xi + (\Phi_{6} - \Phi_{2})\tau$

${cD}_{0 +}^{\alpha}\Phi_{3} = \frac{- \partial H}{\ \ \partial I} = - c_{2} + \Phi_{1}\frac{b\ \left( 1 - u_{1} \right)S}{N} - \Phi_{2}\frac{b\ \left( 1 - u_{1} \right)S}{N} + \Phi_{3}\left( \xi + \gamma + u_{2} \right) - \Phi_{4}(\gamma{+ u}_{2})$,
(5.7)

$= \frac{b\ \left( 1 - u_{1} \right)S}{N}\left( \Phi_{1} - \Phi_{3} \right) + (\gamma{+ u}_{2})\left( \Phi_{3} - \Phi_{4} \right) + \ \xi\Phi_{3}\$

$${cD}_{0 +}^{\alpha}\Phi_{4} = \frac{- \partial H}{\ \ \partial T} = \Phi_{4}(\xi + \delta) - \Phi_{5}\delta = \delta\left( \Phi_{4} - \Phi_{5} \right) + \xi\Phi_{4},$$

${cD}_{0 +}^{\alpha}\Phi_{5} = \frac{- \partial H}{\ \ \partial R} = \Phi_{5}\left( \xi + \rho\left( 1 - u_{3} \right) \right) - \Phi_{6}\rho\left( 1 - u_{3} \right) = \left( \Phi_{5} - \Phi_{6} \right)\rho\left( 1 - u_{3} \right) + \Phi_{5}\xi$

$\$
${cD}_{0 +}^{\alpha}\Phi_{6} = \frac{- \partial H}{\ \ \partial\ L\ } = - c_{3} - \Phi_{3}\sigma + \Phi_{6}(\xi + \sigma\ ) = - c_{3}\left( \Phi_{6} - \Phi_{3} \right)\sigma + \Phi_{6}\xi$

The optimal control variables can be obtained from

$$\frac{\partial H}{\partial u_{1}} = 0,\frac{\partial H}{\partial u_{2}} = 0,\frac{\partial H}{\partial u_{3}} = 0.$$

$$\frac{\partial H}{\partial u_{1}} = c_{3}u_{1} - \Phi_{1}\frac{b\ ( - 1)SI}{N} + \Phi_{2}\frac{b\ ( - 1)SI}{N} = c_{3}u_{1} + \left( \Phi_{1} - \Phi_{2} \right)\frac{b\ ( - 1)SI}{N} = 0.$$

$$\frac{\partial H}{\partial u_{2}} = c_{4}u_{2} - \Phi_{3}I + \Phi_{4}I = c_{4}u_{2} + {(\Phi}_{4} - \Phi_{3})I = 0.$$

$$\frac{\partial H}{\partial u_{3}} = c_{5}u_{3} - \Phi_{5}\rho( - 1)R + \Phi_{6}\rho( - 1)R = c_{5}u_{3} + {(\Phi}_{6} - \Phi_{5})\rho R = 0.$$

Hence the proof.

**Table 1: Parameter values**

+-----------------+-----------------+-----------------+
| **Parameters**  | **Values/ day** | **Sources**     |
|                 |                 |                 |
| **λ**           | **0.0001**      | **\[25\]**      |
|                 |                 |                 |
| **b**           | **0.005-0.02**  | **\[25\]**      |
|                 |                 |                 |
| **ξ**           | **0.002**       | **\[25\]**      |
|                 |                 |                 |
| **β**           | **0.1-0.4**     | **\[25\]**      |
|                 |                 |                 |
| **τ**           | **0.005- 0.02** | **\[25\]**      |
|                 |                 |                 |
| **γ**           | **0.15- 0.6**   | **\[25\]**      |
|                 |                 |                 |
| **δ**           | **0.05-.2**     | **\[25\]**      |
|                 |                 |                 |
| **ρ**           | **0.005-0.2**   | **\[25\]**      |
|                 |                 |                 |
| **σ**           | **0.005-0.2**   | **\[25\]**      |
+-----------------+-----------------+-----------------+

**6. Numerical simulation**

![C:\\Users\\DELL\\Downloads\\ima
2.png](G:\work\Journal2LaTeX\backend\temp\81805053-33ba-4272-96aa-99d478ddc373\intermediate\media/media/image2.png){width="5.20625in"
height="3.6194444444444445in"}

Figure 1: Dynamics of the Susceptible Population in the SAM with varying
contact rate b.

The simulation results demonstrate that the susceptible population
declines rapidly over time, and the rate of decline is strongly
influenced by the contact/interaction rate b. Higher values of b
accelerate the depletion of susceptibles, indicating that increased
exposure and interaction with addicted individuals significantly
heightens the risk of transitioning into addiction. Conversely, lower
values of b slow down this process, allowing the susceptible population
to remain larger for a longer period. This sensitivity analysis
highlights the critical role of the contact rate in shaping addiction
dynamics and underscores the importance of preventive strategies, such
as awareness campaigns and behavioral interventions, which effectively
reduce the effective contact rate. By controlling b, the spread of
scrolling addiction can be mitigated, thereby preserving the susceptible
population and promoting healthier digital habits.

![C:\\Users\\DELL\\Downloads\\ima
3.png](G:\work\Journal2LaTeX\backend\temp\81805053-33ba-4272-96aa-99d478ddc373\intermediate\media/media/image3.png){width="5.206944444444445in"
height="3.6465277777777776in"}

Figure 2: Dynamics of the Exposed Population in the SAM with varying β.

The simulation results for the exposed population reveal how the
progression rate β significantly influences addiction dynamics. At the
beginning, the exposed population rises sharply, reflecting the initial
influx of individuals transitioning from susceptibility to exposure.
However, the long-term behavior depends on the value of β. When β is low
β=0.05, individuals remain in the exposed class for a longer period,
leading to a slower decline and a higher steady-state level of exposure.
As β increases β=0.1 and β=0.2, the exposed population progresses more
quickly into the addicted class, causing a faster decline in exposure
and a lower equilibrium level. This pattern highlights that higher
progression rates accelerate the movement of individuals into addiction,
while lower rates prolong the exposure stage. The analysis underscores
the importance of controlling β through interventions such as awareness
campaigns or preventive measures, which can slow down progression and
reduce the overall burden of addiction in the population.

![C:\\Users\\DELL\\Downloads\\ima
4.png](G:\work\Journal2LaTeX\backend\temp\81805053-33ba-4272-96aa-99d478ddc373\intermediate\media/media/image4.png){width="5.206944444444445in"
height="3.6465277777777776in"}

Figure 3: Dynamics of the Addicted Population in the SAM with varying
treatment Rate **γ**.

The simulation results clearly show that the treatment rate γ plays a
decisive role in reducing the addicted population over time. When the
treatment rate is low (γ=0.025), the addicted population reaches a
higher peak and stabilizes at a relatively large steady-state level,
indicating that insufficient treatment allows addiction to persist
widely. As the treatment rate increases γ=0.05 and γ=0.1, both the peak
and the long-term equilibrium of the addicted population decline
significantly. This demonstrates that stronger treatment efforts
accelerate recovery, lower the maximum burden of addiction, and
ultimately stabilize the system at a healthier state. The analysis
highlights the importance of effective rehabilitation programs and
interventions, as higher treatment rates directly translate into fewer
individuals remaining addicted in the long run.

![C:\\Users\\DELL\\Downloads\\ima
5.png](G:\work\Journal2LaTeX\backend\temp\81805053-33ba-4272-96aa-99d478ddc373\intermediate\media/media/image5.png){width="5.206944444444445in"
height="3.6465277777777776in"}

Figure 4: Dynamics of the treated population in the SAM with varying
recovery rate **δ**.

The simulation results for the treated population highlight the impact
of the recovery rate δ on treatment dynamics. When the recovery rate is
low (δ=0.025), the treated population reaches a higher peak and remains
elevated for a longer period, reflecting slower recovery and prolonged
treatment duration. As δ increases (δ=0.05 and δ=0.075), the peak of the
treated population becomes progressively lower, and the system
stabilizes at smaller equilibrium levels. This indicates that higher
recovery rates accelerate the transition of individuals from treatment
to full recovery, thereby reducing the overall size of the treated
class. The analysis emphasizes that effective recovery mechanisms
shorten treatment periods and lower the long-term burden on
rehabilitation resources, ultimately contributing to healthier outcomes
in managing scrolling addiction.

![C:\\Users\\DELL\\Downloads\\imag
6.png](G:\work\Journal2LaTeX\backend\temp\81805053-33ba-4272-96aa-99d478ddc373\intermediate\media/media/image6.png){width="5.206944444444445in"
height="3.6465277777777776in"}

Figure 5: Dynamics of the Recovered Population in the SAM with Varying
relapse rate **ρ**.

The simulation results for the recovered population demonstrate how
relapse rate ρ directly affects long-term recovery outcomes. When
relapse is low, the recovered population reaches its highest peak and
stabilizes at a relatively large level, indicating that most individuals
remain in recovery. As relapse increases the recovered population peaks
at progressively lower values and declines more sharply, reflecting the
fact that more individuals slip back into addiction. This pattern
highlights that higher relapse rates undermine the sustainability of
recovery, while lower relapse rates strengthen the recovered class. The
analysis emphasizes the importance of relapse prevention strategies,
such as continuous support programs and behavioral interventions, which
help maintain recovery and reduce the risk of individuals returning to
addictive scrolling behavior.

![C:\\Users\\DELL\\Downloads\\ima
7.png](G:\work\Journal2LaTeX\backend\temp\81805053-33ba-4272-96aa-99d478ddc373\intermediate\media/media/image7.png){width="5.206944444444445in"
height="3.6465277777777776in"}

Figure 6: Dynamics of the Latent population in the SAM with varying
transition feedback τ.

The simulation results for the latent population reveal that the
transition feedback parameter τ strongly influences the build up of
individuals in the latent class. When τ is small (τ=0.005), the latent
population grows more slowly and stabilizes at a lower level, indicating
limited re-entry of individuals into latency. As τ increases (τ=0.01 and
τ=0.015), the latent population rises more quickly and reaches higher
equilibrium values, reflecting stronger feedback that channels
individuals back into the latent stage. This behavior shows that higher
transition feedback sustains a larger.

**Conclusion**

In this research, a fractional order compartmental framework for
scrolling addiction is established and thoroughly examined using
threshold dynamics, positivity, boundedness, invariant areas, and
equilibrium stability. The findings demonstrate that while persistence
happens above the reproduction threshold, addiction can be eradicated
when it is less than unity. Numerical simulations revealed that
awareness, treatment, and relapse prevention were the best control
techniques for lowering prevalence. When taken as a whole, these results
give a solid mathematical basis and practical insights for reducing
scrolling addiction, providing direction for behavioral therapies and
digital health policy in the contemporary period. The mathematical
framework can be strengthened, empirical validation can be strengthened,
and policy relevance can be expanded through future study. As a result,
the model will become more practical, useful, and significant for both
theory and practice.

References

1\. Christiane Eichenber, Raphaela Schneider and Helena Rumpl, Social
media addiction associations with attachment style, mental distress, and
personality. BMC Psychiatry. (2024) 24-278.

2\. Abu Safyan Ali, Zesha Faiz and Farhan Khan , Analysis of fractional
order mathematical model of social media addiction and depression.
Modeling Earth Systems and Environment. 9(2026) 12.

3\. Caroline Brand , Camila Felin Fochesatto, Anelise Reis Gaya , Felipe
Barreto Schuch and José Francisco López-Gil, Scrolling through
adolescence: unveiling the relationship of the use of social networks
and its addictive behavior with psychosocial health, Child and
Adolescent, Psychiatry and Mental Health. (2024) 18-107.

4\. Sanjay Bhatter, Sangeeta Kumawat, Sunil Dutt Purohit & D. L. Suthar,
Mathematical modeling of tuberculosis using Caputo fractional
derivative: a comparative analysis with real data. Scientific reports.
15 (2025) 12672.

5\. Rajeshwari S., S. Meenakshi, The age of doom scrolling Social
media's attractive addiction.Journal of Education and Health
Promotion.(2023) 838 -- 22.

6\. Xiao-Hong Zhang, Aatif Ali , Muhammad Altaf Khan , Mohammad Y.
Alshahrani, Taseer Muhammad and Saeed Islam, Mathematical Analysis of
the TB Model with Treatment via Caputo-Type Fractional Derivative.
Hindawi 2021(2021) 9512371-86.

7\. Mostofa Kamal , Md. Al Amin a , Mostak Ahmed a , Payer Ahmed a , Md.
Asraful Islam, Mathematical modeling and optimal control of social media
addiction with stability and sensitivity analysis. Franklin Open. 12
(2025)100354.

8\. Young, K. S., Psychology of computer use: Addictive use of the
internet, a case that breaks the stereotype. Psychological Reports,79
(1996)899-902.

[9. Changhe Wu, Walton Wider,]{.mark} Wei Xuan Yew, Khine Zar Zar Thet,
Chengen Li, Alex S. Borromeo, [Exploring the negative impact of social
media on employee mental health in Malaysia: A Delphi study, Online
Journal of Communication and Media Technologies, 2026, 16(2),
e202616]{.mark}.

[10.]{.mark} [Amjad Islam Amjad]{.mark}, Sana Javaid, Sair, Shamim
Akhter, Mohamad Ahmad Saleem Khasawneh, Thabet Bin Saeed Al-Kahlan,
[Influence of digital media use, environmental awareness, and
eco-anxiety on university students' mental health, *Discover Psychology*
(2026) 6:103,
[doi.org/10.1007/s44202-026-00643-5](https://doi.org/10.1007/s44202-026-00643-5)]{.mark}

11.Ye Hoon Lee, Juhee Hwang, Walking for Mental Health: Effects of
Mobile-Based Walking on Stress and Affectivity in College Students. Int.
J. Ment. Health Promot.27(2), (2025) 179-191.

12\. Chen, T. M., Rui, J., Wang, A mathematical model for simulating the
phase-based transmissibility of a novel corona virus. Infectious
diseases of poverty. 9(1)(2020) 1-8.

13\. Khan, M. A., Atangana A., Modeling the dynamics of novel
coronavirus (2019-nCov) with fractional derivative. Alexandria.59 (2020)
2379-2389.

14\. Hussain, Z., Griffiths, M. D., The associations between problematic
social networking site use and sleep quality, attention-deficit
hyperactivity disorder, depression, anxiety and stress. International
Journal of Mental Health and Addiction. (2019)1--15.

15\. Ravi Shankar Dubey, Manvendra Narayan Mishra, Effect of Covid-19 in
India- A prediction through mathematical modeling using Atangana Baleanu
fractional derivative. Journal of Interdisciplinary Mathematics.
25(2022) 2431--2444 .

16\. Weidong Li 1 ,Zh Yeng Chong ,Yaqing Mao ,Wanying Zhang ,Wei Xu
,Mingwei Li ,Yiyun Wang ,Huaxia Xiong, The Impacts of a Teaching
Personal and Social Responsibility Intervention on Social and Emotional
Competence in Physical Education, A Quasi-Experimental Study. Int. J.
Ment. Health Promot.27 (2025) 1462-3730.

17\. Huo, H., Jing, S.L., Wang, X.Y., Xiang, H., Modelling and analysis
of an alcoholism model with treatment and effect of Twitter. AIMS Math.
16 (2019) 3595--3622.

18\. Li, T., Guo, Y., Stability and optimal control in a mathematical
model of online game addiction. Filomat 33(17) (2019) 5691--5711.

19\. Samad, S.A., Islam, M.T., Tomal, S.T.H., Biswas, M.: Mathematical
assessment of the dynamical model of smoking tobacco epidemic in
Bangladesh. Int. J. Sci. Manag. Stud. 3(2) (2020)36--48.

20\. Lu, X., Huang, P., Feng, X., He, Y.,A stabilized difference finite
element method for the 3D steady incompressible Navier-Stokes equations.
J. Sci. Comput. 92(3) (2022)104 .

21\. Alemneh, H.T., Alemu, N.Y.: Mathematical modeling with optimal
control analysis of social media addiction. Infect. Dis. Model.
6(2021)405--419.

22\. Lu, X., Huang, P., Feng, X., He, Y., A stabilized difference finite
element method for the 3D steady incompressible Navier-Stokes equations.
J. Sci. Comput. 92(3) (2022) 104.

23\. Kongson, J., Thaiprayoon, C., Sudsutad, W., Analysis of a
fractional model for HIV CD4+ T-cells with treatment under generalized
Caputo fractional derivative. AIMS Math. 6(7) (2021) 7285--7304.

24\. Tianyi Pu ,Marco Fasondini,The numerical solution of fractional
integral equations via orthogonal polynomials in fractional Powers. Adv
Comput Math . 49(2023)7.

25\. Shenghu Xu , Yanhui Hu, Dynamic analysis of a Caputo
fractional-order SEIR model with a general incidence rate. Scientific
reports. 15 (2025)17561.

26\. Muhammad Farman , Cicik Alfniyah,Muhammad Saqib, Global Stability
with Lyapunov Function and Dynamics of SEIR-Modified Lassa Fever Model
in Sight Power Law Kernel.Hindawi.27 (2024) 3562684.

27\. Fareeha Sami Khan, M. Khalid Ali ,Hasan Ali , F.Ghanim, Optimal
control strategies for taming TikTok addiction: a mathematical model and
analysis. Arabian Journal of Mathematics. (2025),

28\. Ling Zhang, Xuewen Tan, Jia Li and Fan Yang, Dynamic analysis and
optimal control of leptospirosis based on Caputo fractional derivative .
Network and Heterogeneous Media. 19(3) (2024) 1262--1285.

29\. Bentout S, Age-structured modeling of COVID-19 epidemic in the USA,
UAE and Algeria. 60(1) (2021)401--411.

30\. Djilali, Lahbib Benahmadi, Abdessamad, Khadia., Modeling the impact
of unreported cases of the COVID-19 in the north African countries.
9(11) (2020) 373.

31\. Salih Djilali, Soufiane Bentout, Sunil Kumar,  Tarik Mohammed
Touaoula, Approximating the asymptomatic infectious cases of the
COVID-19 disease in Algeria, and India. 13(4)(2022).

32\. Michele Caputo and Mauro Fabrizio, A new deﬁnition of fractional
derivative without singular kernel. 73(2015),

33\. I. Podlubny, Fractional Diﬀerential Equations, Academic Press, San
Diego, 1999.

34\. Abdon Atangana, Dumitru Baleanu., New fractional derivatives with
nonlocal and non-singular kernel theory and application to heat transfer
model thermal Science. 20(2016).

35\. A Atangana, S Qureshi., Modeling attractors of chaotic dynamical
systems with fractal-fractional operators. Chaos, solitons & fractals,
123( 2019) 320-337.

36\. Lei Shi a, Jiaying Zhou, Yong Ye., Global stability and Hopf
bifurcation of networked respiratory disease model with delay, 151
(2024) 109000.

37\. HF Huo, Q Wang., Modelling the inﬂuence of awareness programs by
media on the drinking dynamics. Abstract and Applied Analysis,
2014(1)(2014) 938080.

38\. Om P. Agrawal, Ozlem Defterli, Dumitru Baleanu, Fractional Optimal
Control Problems with Several State and Control Variables. Journal of
Vibration and Control.16(13) (2010).

39\. Tingting Li,Youming Guo., Stability and optimal control in a
mathematical model of online game addiction. Filomat. 33(2019),
5691--5711.

40\. Abdon Atangana, Seda Igret.,Fractional Stochastic Diﬀerential
Equations. Springer,

\(2022\)

42\. Vijayalakshmi. G.M, P. Roselin Besi., Ali Akgul., Fractional
commensurate model on Covid-19 with microbial confections. An optimal
control analysis.45(3) (2024) 1108-1121.

43\. Vijayalakshmi G.M, M.Ariyanatchi Adams--Bashforth Moulton Numerical
Approach on Dengue Fractional Atangana Baleanu Caputo Model and
Stability Analysis.10(32)(2024).

44\. G. M. Vijayalakshmi,  M. Ariyanatchi,  Vediyappan Govindan,  Haewon
Byeon,  Busayamas Pimpunchat., Stability and Hopf Bifurcations Analysis
in a Three-Phase Dengue Diffusion Model With Time Delay in Fractional
Derivative and Laplace--Adomian Decomposition Numerical Approach.
Mathematical Methods in the Applied Science. 48(12) (2025).

45\. Vijayalakshmi G.M, Nisar. K.S, Shiva Reddy. K, Mittag--Leffler
kernel operator on prey-predator model interfusing intra-specific
competition and prey fear factor, 9(2024).

46\. G. M. Vijayalakshmi., P. Roselyn Besi., ABC fractional order
vaccination model for COVID-19 with self-productive measures.8 (132)
(2022).

47\. G. M. Vijayalakshmi., P. Roselyn Besi., A fractal fractional order
model of COVID-19 pandemic using Adams Moulton Analysis. Result in
control and Optimization, 8(2022).
