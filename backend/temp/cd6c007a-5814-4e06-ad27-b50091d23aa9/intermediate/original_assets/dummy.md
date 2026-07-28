**Analytical Dynamics of a Monkeypox Model Using Caputo-Fabrizio
Fractional Derivative and Sumudu Transform Method**

**Ariyanatchi M^1^, G.M.Vijayalakshmi^2^, Paulraj Jayasimman^3^, Roselyn
Besi P^4^ and Ali Akgül^5,6^** ^,\*^

^1^Post Doctoral Fellow, Mathematics, AMET University, Chennai.

^2^Professor, Mathematics, Vel tech Rangarajan Dr Sagunthala R&D
Institute of science and technology, Chennai.Department of Mathematics,

^3^Professor,Department of Mathematics,AMET University, Chennai.

^4^Coimbatore Institute of technology, Coimbatore, India.

^5^Department of Electronics and Communication Engineering, Saveetha
School of Engineering,SIMATS, Chennai, Tamilnadu, India

^6^Siirt University, Art and Science Faculty, Department of Mathematics,
56100 Siirt, Türkiye

Correspondence: aliakgul@siirt.edu.tr

**Abstract**

This study presents a fractional-order mathematical model for the
transmission dynamics of monkeypox, formulated using the Caputo-Fabrizio
fractional derivative to better capture the memory and hereditary
properties inherent in real-world biological systems. The model
incorporates key epidemiological compartments to reflect the stages of
monkeypox infection and transmission. To obtain analytical solutions,
the Sumudu transform method is employed due to its efficiency in
handling fractional differential equations. The existence and uniqueness
of solutions are rigorously verified using fixed-point theory and the
Picard--Lindelöf approach, ensuring mathematical consistency and
reliability of the model. The proposed framework provides deeper
insights into the progression of monkeypox and offers a robust
analytical approach for studying disease dynamics under fractional-order
settings. This work contributes significantly to understanding the
impact of memory effects in disease modelling and can inform future
control strategies for emerging infectious diseases like monkeypox.

**Keywords**

Monkeypox, Fractional-Order Model, Caputo-Fabrizio Derivative, Sumudu
Transform, Fixed-Point Theory, Picard-Lindelöf Approach, Disease
Dynamics.

**1.Introduction**

Mpox, formerly known as monkeypox, is a viral disease caused by the
monkeypox virus (MPXV), part of the *Orthopoxvirus* genus. There are two
main clades: clade I (with subclades Ia and Ib) and clade II (with
subclades IIa and IIb). The virus spreads through close contact with
infected individuals, contaminated materials, or infected animals. It
can also be transmitted during pregnancy or birth. Symptoms typically
appear 1--21 days after exposure and include fever, rash, muscle aches,
swollen lymph nodes, and low energy. The rash often progresses from flat
sores to fluid-filled blisters that crust and fall off. While many
recover within 2--4 weeks, severe cases can occur, especially in
children, pregnant individuals, and people with weakened immune systems.
Complications may include secondary infections, pneumonia, sepsis,
encephalitis, or even death \[1-3\].

Diagnosis relies on PCR testing of lesions, while treatment focuses on
symptom relief and supportive care, including hydration, nutrition, and
management of pain and fever. Although there is no specific antiviral
approved for mpox, some experimental antivirals are under evaluation.
Vaccination, both pre- and post-exposure, is recommended for high-risk
groups such as health workers, close contacts. During outbreaks,
isolation, hygiene measures, and personal protective equipment (PPE) are
essential to limit transmission \[4,5\]. Mpox outbreaks have
historically occurred in central and west Africa, with the first human
case detected in 1970. However, the 2022--2023 global outbreak, driven
by clade IIb, highlighted the disease's potential to spread rapidly
across continents, reinforcing the importance of global surveillance,
research, and public health preparedness \[6,7\].

Mathematical modelling is a valuable tool in understanding and managing
the spread of monkeypox, especially due to its ability to simulate
disease dynamics and assess intervention strategies. Because monkeypox
was previously under-researched, early models helped identify critical
factors like isolation and transmission pathways. A deterministic model
presented in \[8\] showed that isolating infected individuals could
significantly reduce new infections. Similarly, the model developed in
\[9\] used nonlinear differential equations to examine how monkeypox
spreads, revealing that a person's immune system influences recovery.
More research works \[10--13\] have expanded on this by studying
different aspects of transmission and control strategies for infectious
diseases. In \[14\], a model emphasized the role of non-pharmaceutical
interventions in eliminating monkeypox outbreaks. Likewise, a simulation
study in \[15\] found that medical treatment can help remove the virus
from both human and animal populations. Furthermore, recent models with
environmental factors have been proposed in \[16,17\] to better explain
how monkeypox spread during the 2022 outbreak. These mathematical models
play a key role in guiding public health policies and developing
targeted prevention methods

Fractional calculus has become increasingly important in modelling
real-world problems, particularly in disease dynamics, because of its
unique ability to capture memory and hereditary effects---features often
missing in classical models \[18--22\]. In recent years,
fractional-order models have been applied to infectious diseases like
COVID-19 \[23--27\], providing more accurate results compared to
traditional models. In \[28\], a stochastic fractional model was used to
analyze cross-infection in monkeypox transmission, and \[29\] introduced
a fractal--fractional approach to study animal-to-human spread. Compared
to standard derivatives, fractional derivatives allow better
understanding of processes with long-term memory and time delays. Many
researchers have used fractional models with Mittag--Leffler kernels and
Caputo--Fabrizio operators for diseases such as dengue, Ebola, HIV/AIDS,
and COVID-19 \[30--39\]. In \[40\], Mittag--Leffler kernels helped model
Ebola--malaria co-infections effectively, while \[41\] used them to
study HIV/AIDS, proving that infection rates could be reduced by
adjusting fractional parameters. The Caputo--Fabrizio operator, known
for its non-singular behaviour and exponential decay, has been preferred
in works like \[40--45\] for modelling typhoid, Alzheimer's, and other
diseases. In \[46\], real-world data from Nigeria was used in a
fractional model to evaluate control strategies for monkeypox, showing
how mathematical analysis helps guide effective public health decisions.
Similarly, \[47\] confirmed that isolating infected people can control
monkeypox transmission effectively. These studies highlight how
fractional calculus significantly improves disease modelling and
enhances predictive outcomes.

The Sumudu transform has emerged as an efficient tool for solving
fractional-order differential equations due to its ability to preserve
the original dimensionality of functions, ease of handling initial
conditions, and compatibility with various fractional derivatives such
as Caputo and Atangana-Baleanu. Compared to the Laplace transform, the
Sumudu transform offers simpler inversion, operates in the real domain,
and is often more suitable for physical systems with memory effects. In
\[48\], the authors applied the Sumudu transform to a fractional
COVID-19 model and demonstrated its effectiveness in capturing the
epidemic dynamics with reduced computational complexity. Similarly, in
\[49\], a fractional model incorporating quarantine and isolation
compartments was developed to assess containment strategies,
highlighting the practical relevance of fractional derivatives in
real-world epidemiological modelling.

The scope of this research lies in enhancing the analytical
understanding of monkeypox dynamics by applying a fractional-order
approach that accounts for the disease\'s temporal memory
characteristics. By structuring the model with relevant compartments and
incorporating the Caputo-Fabrizio operator, the study addresses
limitations of classical integer-order models in capturing delayed and
hereditary effects in transmission. The use of the Sumudu transform
offers a streamlined technique for solving the fractional system,
allowing for more accessible and dimensionally consistent solutions. A
key advantage of this study is its rigorous mathematical foundation,
ensuring the existence and uniqueness of solutions through fixed-point
techniques. Moreover, the model\'s structure and methodology provide a
flexible framework that can be extended to other infectious diseases,
highlighting the potential of fractional modelling in supporting
data-driven public health strategies.

In summary, this paper presents a comprehensive framework for modelling
and controlling Dengue transmission using Caputo Fabrizio fractional
derivatives and Sumudu transform techniques, offering significant
improvements in disease management.

This paper is organized as follows: Section 2 presents the preliminary
concepts and mathematical tools used in the study. Section 3 develops
the fractional-order mathematical model for monkeypox transmission and
introduces the key epidemiological compartments. Section 4 provides a
qualitative analysis of the model, including existence and uniqueness of
solutions. Section 5 focuses on the numerical analysis and simulation
techniques. Section 6 discusses the results obtained from the
simulations and interprets their epidemiological implications. Finally,
Section 7 concludes the paper with a summary of findings and potential
directions for future work.

**2. Preliminaries**

The Sumudu transform over the set of functions

$Ą = \left\{ Ӻ(ե)|\exists Ɱ,\tau_{1},\tau_{2} > 0,\left| Ӻ(ե) \right| < Ɱe^{\frac{|ե|}{\tau_{j}}},\ ե \in ( - 1)^{j} \times \lbrack 0,\infty) \right\}$

Is defined as

$G(u) = S\left\lbrack Ӻ(ե) \right\rbrack = \int_{0}^{\infty}{}e^{- uե}\ Ӻ(ե)dե$
(1)

The Sumudu transform of Caputo fractional derivative is explained below

$ST\left\lbrack {0CD}_{ե}^{\alpha}Ӻ(ӿ,ե):ѕ \right\rbrack = ѕ^{- \alpha}ST\left\{ Ӻ(ӿ,ե) \right\} - ѕ^{- \alpha}\sum_{к = 0}^{₥ - 1}{}ѕ^{к}Ӻ^{к}(ӿ,0)$
(2)

The following definition of the Sumudu transform of Caputo-Fabrizio
fractional differential coefficient of $Ӻ(ե)$ is based on the assumption
that $Ӻ(ե)$ is a function whose Caputo-Fabrizio derivative occurs

$ST\left( {0CfD}_{ե}^{\alpha} \right)\left( Ӻ(ե) \right) = Ɱ(\alpha)\left\lbrack \frac{ST\left( Ӻ(ե) \right) - Ӻ(0)}{1 - \alpha + \alpha u} \right\rbrack$
(3)

**3. Model Formulation**

This study proposes a fractional-order differential equation model to
describe the transmission dynamics of monkeypox involving interactions
between two populations: humans and animals. Each population is
subdivided into relevant epidemiological compartments to reflect the
stages of infection and recovery.

Human Population Compartments:

The human population is divided into four compartments:

- $Ş_{ɓ}$: Susceptible humans

- $ɬ_{ɓ}$ : Infected humans

- $℞_{ɓ}$: Recovered humans

- $Ᵽ_{ɓ}$: Protected humans (e.g., through immunity or vaccination)

The total human population is denoted by $N_{ɓ} = Ş_{ɓ} + ɬ_{ɓ}$
+$℞_{ɓ} + Ᵽ_{ɓ}$. New individuals are recruited into the human
population at a constant rate $\pi_{ɓ}$. Susceptible humans may become
infected through contact with infected animals or other infected humans.
The effective contact rate between susceptible humans and infected
animals is represented by $\beta_{ɓ_{1}}$, and the contact rate between
susceptible and infected humans is given by $\beta_{ɓ_{2}}$.

Infected humans recover at a rate $\gamma_{ɓ}$, while a proportion of
recovered individuals move to the protected class at a rate
$\theta_{ɓ}$. The model also accounts for the natural death rate
$\mu_{ɓ}$ and disease-induced death rate $ԃ_{ɓ}$ among the human
population.

Animal Population Compartments:

The animal population is categorized into three compartments:

- $Ş_{ɑ}$: Susceptible animals

- $ɬ_{ɑ}$: Infected animals

- $℞_{ɑ}$: Recovered animals

The total animal population is $N_{ɑ} = Ş_{ɑ}$+$ɬ_{ɑ} + ℞_{ɑ}$. Animals
are recruited at a rate $\pi_{ɑ}$. Susceptible animals can become
infected through contact with infected animals at an effective contact
rate $\beta_{ɑ}$. Infected animals recover at a rate $\gamma_{ɑ}$. The
model includes both the natural death rate $\mu_{ɑ}$ and the
disease-induced death rate $ԃ_{ɑ}$ for animals.

Model Dynamics:

The transition of individuals between compartments is governed by a
system of nonlinear differential equations that describe the rates of
change in each compartment over time. The interaction terms,
recruitment, recovery, protection, and mortality are all included to
reflect realistic biological and epidemiological processes. This
compartmental structure enables the model to capture the dynamics of
monkeypox spread within and between human and animal populations.

$\frac{ԃŞ_{ɓ}}{ԃե} = \left( 1 - Ᵽ_{ɓ} \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \mu_{ɓ}Ş_{ɓ}$

$\frac{ԃɬ_{ɓ}}{ԃե} = \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ}$

$\frac{ԃ℞_{ɓ}}{ԃե} = \gamma_{ɓ}ɬ_{ɓ} - \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}℞_{ɓ}$

$\frac{ԃⱣ_{ɓ}}{ԃե} = Ᵽ_{ɓ}\pi_{ɓ} + \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}Ᵽ_{ɓ}$

$\frac{ԃŞ_{ɑ}}{ԃե} = \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \mu_{ɑ}Ş_{ɑ}$

$\frac{dɬ_{ɑ}}{ԃե} = \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ}$

$\frac{ԃ℞_{ɑ}}{ԃե} = \gamma_{ɑ}ɬ_{ɑ} - \mu_{ɑ}℞_{ɑ}$ (4)

The above differential equation (4) is converted using the
Caputo-Fabrizio fractional derivative to incorporate memory effects and
non-local behaviour in the system dynamics. This approach ensures a more
accurate representation of real-world disease progression without
singular kernel issues.

${0CfD}_{ե}^{\alpha}Ş_{ɓ} = \left( 1 - Ᵽ_{ɓ} \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \mu_{ɓ}Ş_{ɓ}$

${0CfD}_{ե}^{\alpha}ɬ_{ɓ} = \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ}$

${0CfD}_{ե}^{\alpha}℞_{ɓ}\  = \gamma_{ɓ}ɬ_{ɓ} - \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}℞_{ɓ}$

${0CfD}_{ե}^{\alpha}Ᵽ_{ɓ}\  = Ᵽ_{ɓ}\pi_{ɓ} + \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}Ᵽ_{ɓ}$

${0CfD}_{ե}^{\alpha}Ş_{ɑ}\  = \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \mu_{ɑ}Ş_{ɑ}$

${0CfD}_{ե}^{\alpha}ɬ_{ɑ} = \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ}$

${0CfD}_{ե}^{\alpha}℞_{ɑ} = \gamma_{ɑ}ɬ_{ɑ} - \mu_{ɑ}℞_{ɑ}$ (5)

These equations describe the dynamic evolution of the variables
$Ş_{ɓ} \geq 0,ɬ_{ɓ} \geq 0,\ ℞_{ɓ} \geq 0,$

$Ᵽ_{ɓ} \geq 0,Ş_{ɑ} \geq 0,\ ɬ_{ɑ} \geq 0,\ ℞_{ɑ} \geq 0\ \$over time
within the framework of the proposed model. The Caputo Fabrizio
fractional ($CF$), represented by ${0CfD}_{ե}^{\alpha}$, where
$0\  < \eta < 1$.

Table 1. Parameter values used in the proposed fuzzy fractional-order
monkeypox transmission model.

  ----------------------------------- -----------------------------------
               Parameter                            Values

              $$\pi_{ɓ}$$                           0.0056

           $$\beta_{ɓ_{1}}$$                         0.002

           $$\beta_{ɓ_{2}}$$                         0.004

            $$\gamma_{ɓ}$$                           0.094

            $$\theta_{ɓ}$$                           0.025

               $$Ᵽ_{ɓ}$$                             0.02

              $$\mu_{ɓ}$$                            0.01

               $$ԃ_{ɓ}$$                             0.005

              $$\pi_{ɑ}$$                            0.001

             $$\beta_{ɑ}$$                           0.04

            $$\gamma_{ɑ}$$                           0.02

              $$\mu_{ɑ}$$                            0.015

               $$ԃ_{ɑ}$$                             0.08
  ----------------------------------- -----------------------------------

**3. Qualitative Analysis**

***3.1 Existence of the solutions of desired model***

**Theorem 3.1**

Describe $Q_{1},\ Q_{2},Q_{3},Q_{4},Q_{5},Q_{6},Q_{7}$ and explain how
they relate to variables.

**Proof**

Transforming the aforementioned proposed system (5) into an integral
equation system-

$Ş_{ɓ}(ե) - Ş_{ɓ}(0) = {0CFT}_{ե}^{\alpha}\left\lbrack \left( 1 - Ᵽ_{ɓ} \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \mu_{ɓ}Ş_{ɓ} \right\rbrack$

${ɬ_{ɓ}(ե) - ɬ_{ɓ}(0) = 0CFT}_{ե}^{\alpha}\left\lbrack \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ} \right\rbrack$

$℞_{ɓ}(ե) - ℞_{ɓ}(0) = {0CFT}_{ե}^{\alpha}\left\lbrack \gamma_{ɓ}ɬ_{ɓ} - \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}℞_{ɓ} \right\rbrack$

$Ᵽ_{ɓ}(ե) - Ᵽ_{ɓ}(0) = {0CFT}_{ե}^{\alpha}\left\lbrack \pi_{ɓ}Ᵽ_{ɓ} + \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}Ᵽ_{ɓ} \right\rbrack$

$Ş_{ɑ}(ե) - Ş_{ɑ}(0) = {0CFT}_{ե}^{\alpha}\left\lbrack \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \mu_{ɑ}Ş_{ɑ} \right\rbrack$

$ɬ_{ɑ}(ե) - ɬ_{ɑ}(0) = {0CFT}_{ե}^{\alpha}\left\lbrack \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ} \right\rbrack$

$℞_{ɑ}(ե) - ℞_{ɑ}(0) = {0CFT}_{ե}^{\alpha}\left\lbrack \gamma_{ɑ}ɬ_{ɑ} - \mu_{ɑ}℞_{ɑ} \right\rbrack$
(6)

Using Nieto's definition, we then arrive at,

$Ş_{ɓ}(ե) = Ş_{ɓ}(0) + \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\left\lbrack \left( 1 - Ᵽ_{ɓ}(ե) \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)Ş_{ɓ}(ե)}{N_{ɓ}(ե)} - \mu_{ɓ}Ş_{ɓ}(ե) \right\rbrack$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\lbrack \left( 1 - Ᵽ_{ɓ}(s) \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(s) + \beta_{ɓ_{2}}ɬ_{ɓ}(s) \right)Ş_{ɓ}(s)}{N_{ɓ}(ե)} - \mu_{ɓ}Ş_{ɓ}(s) \right\rbrack ԃs$

$ɬ_{ɓ}(ե) = ɬ_{ɓ}(0) + \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\left\lbrack \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)Ş_{ɓ}(ե)}{N_{ɓ}(ե)} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ}(ե) \right\rbrack$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\lbrack \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(s) + \beta_{ɓ_{2}}ɬ_{ɓ}(s) \right)Ş_{ɓ}(s)}{N_{ɓ}(s)} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ}(s) \right\rbrack ԃs$

$℞_{ɓ}(ե) = ℞_{ɓ}(0) + \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\left\lbrack \gamma_{ɓ}ɬ_{ɓ}(ե) - \theta_{ɓ}℞_{ɓ}(ե) - \mu_{ɓ}℞_{ɓ}(ե) \right\rbrack$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\lbrack \gamma_{ɓ}ɬ_{ɓ}(s) - \theta_{ɓ}℞_{ɓ}(s) - \mu_{ɓ}℞_{ɓ}(s) \right\rbrack ԃs$

$Ᵽ_{ɓ}(ե) = Ᵽ_{ɓ}(0) + \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\left\lbrack \pi_{ɓ}Ᵽ_{ɓ}(ե) + \theta_{ɓ}℞_{ɓ}(ե) - \mu_{ɓ}Ᵽ_{ɓ}(ե) \right\rbrack$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\lbrack \pi_{ɓ}Ᵽ_{ɓ}(s) + \theta_{ɓ}℞_{ɓ}(s) - \mu_{ɓ}Ᵽ_{ɓ}(s) \right\rbrack ԃs$

$Ş_{ɑ}(ե) = Ş_{ɑ}(0) + \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\left\lbrack \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ}(ե)ɬ_{ɑ}(ե)}{N_{ɑ}(ե)} - \mu_{ɑ}Ş_{ɑ}(ե) \right\rbrack$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\lbrack \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ}(s)ɬ_{ɑ}(s)}{N_{ɑ}(s)} - \mu_{ɑ}Ş_{ɑ}(s) \right\rbrack ԃs$

$ɬ_{ɑ}(ե) = ɬ_{ɑ}(0) + \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\left\lbrack \frac{\beta_{ɑ}Ş_{ɑ}{(ե)ɬ}_{ɑ}(ե)}{N_{ɑ}(ե)} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ}(ե) \right\rbrack$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\lbrack \frac{\beta_{ɑ}Ş_{ɑ}{(s)ɬ}_{ɑ}(s)}{N_{ɑ}(s)} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ}(s) \right\rbrack ԃs$

$℞_{ɑ}(ե) = ℞_{ɑ}(0) + \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\left\lbrack \gamma_{ɑ}ɬ_{ɑ}(ե) - \mu_{ɑ}℞_{ɑ}(ե) \right\rbrack$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\lbrack \gamma_{ɑ}ɬ_{ɑ}(s) - \mu_{ɑ}℞_{ɑ}(s) \right\rbrack ԃs$
(7)

Let's now assume that the kernels are provided as

$Q_{1}\left( ե,Ş_{ɓ} \right) = \left( 1 - Ᵽ_{ɓ}(ե) \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)Ş_{ɓ}(ե)}{N_{ɓ}(ե)} - \mu_{ɓ}Ş_{ɓ}(ե)$

$Q_{2}\left( ե,ɬ_{ɓ} \right) = \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)Ş_{ɓ}(ե)}{N_{ɓ}(ե)} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ}(ե)$

$Q_{3}\left( ե,℞_{ɓ} \right) = \gamma_{ɓ}ɬ_{ɓ}(ե) - \theta_{ɓ}℞_{ɓ}(ե) - \mu_{ɓ}℞_{ɓ}(ե)$

$Q_{4}\left( ե,Ᵽ_{ɓ} \right) = \pi_{ɓ}Ᵽ_{ɓ}(ե) + \theta_{ɓ}℞_{ɓ}(ե) - \mu_{ɓ}Ᵽ_{ɓ}(ե)$

$Q_{5}\left( ե,Ş_{ɑ} \right) = \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ}(ե)ɬ_{ɑ}(ե)}{N_{ɑ}(ե)} - \mu_{ɑ}Ş_{ɑ}(ե)$

$Q_{6}\left( ե,ɬ_{ɑ} \right) = \frac{\beta_{ɑ}Ş_{ɑ}{(ե)ɬ}_{ɑ}(ե)}{N_{ɑ}(ե)} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ}(ե)$

$Q_{7}\left( ե,℞_{ɑ} \right) = \gamma_{ɑ}ɬ_{ɑ}(ե) - \mu_{ɑ}℞_{ɑ}(ե)$ (8)

**Theorem 3.2**

Demonstrate that $Q_{1},\ Q_{2},Q_{3},Q_{4},Q_{5},Q_{6}$ and$\ Q_{7}$
fulfil the Lipschitz requirement.

**Proof**

We will first demonstrate this for $Q_{1}$. Considering that $Ş_{ɓ}$ and
${Ş_{ɓ}}_{1}$ are any two functions, we have

$\| Q_{1}\left( ե,Ş_{ɓ} \right) - Q_{1}\left( ե,{Ş_{ɓ}}_{1} \right)\| = \| - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)}{N_{ɓ}(ե)}Ş_{ɓ}(ե) - \mu_{ɓ}Ş_{ɓ}(ե) + \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)}{N_{ɓ}(ե)}{Ş_{ɓ}}_{1}(ե) + \mu_{ɓ}{Ş_{ɓ}}_{1}(ե)\|$

> $\leq \| - \left( \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)}{N_{ɓ}(ե)} + \mu_{ɓ} \right)\|\| Ş_{ɓ}(ե) - {Ş_{ɓ}}_{1}(ե)\|$

$\| Q_{1}\left( ե,Ş_{ɓ} \right) - Q_{1}\left( ե,{Ş_{ɓ}}_{1} \right)\| \leq Ⱨ_{1}\| Ş_{ɓ}(ե) - {Ş_{ɓ}}_{1}(ե)\|$

Where
$\| - \left( \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)}{N_{ɓ}(ե)} + \mu_{ɓ} \right)\| \leq Ⱨ_{1} < 1$.

Similarly, we can have

$\| Q_{2}\left( ե,ɬ_{ɓ} \right) - Q_{2}\left( ե,{ɬ_{ɓ}}_{1} \right)\| \leq \|\frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)Ş_{ɓ}(ե)}{N_{ɓ}(ե)} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ}(ե) - \ \frac{\ \left( \ \beta_{ɓ_{1}}ɬ_{ɑ}(ե) + \beta_{ɓ_{2}}ɬ_{ɓ}(ե) \right)Ş_{ɓ}(ե)}{N_{ɓ}(ե)} + \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right){ɬ_{ɓ}}_{1}(ե)\|$

$\leq \|\left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)\|\| ɬ_{ɓ}(ե) - {ɬ_{ɓ}}_{1}(ե)\|$

$\| Q_{2}\left( ե,ɬ_{ɓ} \right) - Q_{2}\left( ե,{ɬ_{ɓ}}_{1} \right)\| \leq Ⱨ_{2}\| ɬ_{ɓ}(ե) - {ɬ_{ɓ}}_{1}(ե)\|$

Where $\|\left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)\| \leq Ⱨ_{2} < 1$.

Now,

$\| Q_{3}\left( ե,℞_{ɓ} \right) - Q_{3}\left( ե,{℞_{ɓ}}_{1} \right)\| \leq \|\gamma_{ɓ}ɬ_{ɓ}(ե) - \theta_{ɓ}℞_{ɓ}(ե) - \mu_{ɓ}℞_{ɓ}(ե) - \gamma_{ɓ}ɬ_{ɓ}(ե) + \theta_{ɓ}{℞_{ɓ}}_{1}(ե) + \mu_{ɓ}{℞_{ɓ}}_{1}(ե)\|$

$\leq \|\left( \theta_{ɓ} + \mu_{ɓ} \right)\|\| ℞_{ɓ}(ե) - {℞_{ɓ}}_{1}(ե)\|$

$\| Q_{3}\left( ե,℞_{ɓ} \right) - Q_{3}\left( ե,{℞_{ɓ}}_{1} \right)\| \leq Ⱨ_{3}\| ℞_{ɓ}(ե) - {℞_{ɓ}}_{1}(ե)\|$

Where $\|\left( \theta_{ɓ} + \mu_{ɓ} \right)\| \leq Ⱨ_{3} < 1$.

and

$\| Q_{4}\left( ե,Ᵽ_{ɓ} \right) - Q_{4}\left( ե,{Ᵽ_{ɓ}}_{1} \right)\| \leq Ⱨ_{4}\| Ᵽ_{ɓ}(ե) - {Ᵽ_{ɓ}}_{1}(ե)\|$

Where $\|\left( \pi_{ɓ} + \mu_{ɓ} \right)\| \leq Ⱨ_{4} < 1$

$\| Q_{5}\left( ե,Ş_{ɑ} \right) - Q_{5}\left( ե,{Ş_{ɑ}}_{1} \right)\| \leq Ⱨ_{5}\| Ş_{ɑ}(ե) - {Ş_{ɑ}}_{1}(ե)\|$

Where
$\|\left( \frac{\beta_{ɑ}ɬ_{ɑ}(ե)}{N_{ɑ}(ե)} + \mu_{ɑ} \right)\| \leq Ⱨ_{5} < 1$.

$\| Q_{6}\left( ե,ɬ_{ɑ} \right) - Q_{6}\left( ե,{ɬ_{ɑ}}_{1} \right)\| \leq Ⱨ_{6}\| ɬ_{ɑ}(ե) - {ɬ_{ɑ}}_{1}(ե)\|$

Where
$\| - \left( \frac{\beta_{ɑ}Ş_{ɑ}}{N_{ɑ}(ե)} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right) \right)\| \leq Ⱨ_{6} < 1$.

$\| Q_{7}\left( ե,℞_{ɑ} \right) - Q_{7}\left( ե,{℞_{ɑ}}_{1} \right)\| \leq Ⱨ_{7}\| ℞_{ɑ}(ե) - {℞_{ɑ}}_{1}(ե)\|$
, Where $\|\mu_{ɑ}\| \leq Ⱨ_{7} < 1$.

Now consider the recurrence formula, we can acquire

${Ş_{ɓ}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{1}\left( ե,{Ş_{ɓ}}_{r - 1} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{1}\left( s,{Ş_{ɓ}}_{r - 1} \right)ds\$

${ɬ_{ɓ}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{2}\left( ե,{ɬ_{ɓ}}_{r - 1} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{2}\left( s,{ɬ_{ɓ}}_{r - 1} \right)ds\$

${℞_{ɓ}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{3}\left( ե,{℞_{ɓ}}_{r - 1} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{3}\left( s,{℞_{ɓ}}_{r - 1} \right)ds\$

${Ᵽ_{ɓ}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{4}\left( ե,{Ᵽ_{ɓ}}_{r - 1} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{4}\left( s,{Ᵽ_{ɓ}}_{r - 1} \right)ds\$

${Ş_{ɑ}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{5}\left( ե,{Ş_{ɑ}}_{r - 1} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{5}\left( s,{Ş_{ɑ}}_{r - 1} \right)ds$

${ɬ_{ɑ}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{6}\left( ե,{ɬ_{ɑ}}_{r - 1} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{6}\left( s,{ɬ_{ɑ}}_{r - 1} \right)ds$

${℞_{ɑ}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{7}\left( ե,{℞_{ɑ}}_{r - 1} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{7}\left( s,{℞_{ɑ}}_{r - 1} \right)ds$
(9)

When a norm is used in the concept of majorizing, the distinction
between sub-sequent terms that implies

$U_{r}(ե) = {Ş_{ɓ}}_{r}(ե) - {Ş_{ɓ}}_{r - 1}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{1}\left( ե,{Ş_{ɓ}}_{r - 1} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{1}\left( s,{Ş_{ɓ}}_{r - 1} \right)ds$

$- \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{1}\left( ե,{Ş_{ɓ}}_{r - 2} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{1}\left( s,{Ş_{ɓ}}_{r - 2} \right)ds$

\(10\)

$U_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{1}\left( ե,{Ş_{ɓ}}_{r - 1} \right) - \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{1}\left( ե,{Ş_{ɓ}}_{r - 2} \right)$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\{ Q_{1}\left( s,{Ş_{ɓ}}_{r - 1} \right) - Q_{1}\left( s,{Ş_{ɓ}}_{r - 2} \right) \right\} ds$
(11)

Now

$\| U_{r}(ե)\| = \|{Ş_{ɓ}}_{r}(ե) - {Ş_{ɓ}}_{r - 1}(ե)\|$

> $= \|\frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{1}\left( ե,{Ş_{ɓ}}_{r - 1} \right) - \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{1}\left( ե,{Ş_{ɓ}}_{r - 2} \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\{ Q_{1}\left( s,{Ş_{ɓ}}_{r - 1} \right) - Q_{1}\left( s,{Ş_{ɓ}}_{r - 2} \right) \right\} ds\|$
>
> $\leq \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\| Q_{1}\left( ե,{Ş_{ɓ}}_{r - 1} \right) - Q_{1}\left( ե,{Ş_{ɓ}}_{r - 2} \right)\| + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\|\int_{0}^{ե}{}\left\{ Q_{1}\left( s,{Ş_{ɓ}}_{r - 1} \right) - Q_{1}\left( s,{Ş_{ɓ}}_{r - 2} \right) \right\} ds\|$
> (12)

But $Q_{1}$ satisfies Lipchitz condition so,

$\| U_{r}(ե)\| \leq \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}H_{1}\|{Ş_{ɓ}}_{r - 1} - {Ş_{ɓ}}_{r - 2}\| + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}K_{1}\|{Ş_{ɓ}}_{r - 1} - {Ş_{ɓ}}_{r - 2}\| ds$
(13)

In the same way, we have

$\| V_{r}(ե)\| \leq \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}H_{2}\|{ɬ_{ɓ}}_{r - 1} - {ɬ_{ɓ}}_{r - 2}\| + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}K_{2}\|{ɬ_{ɓ}}_{r - 1} - {ɬ_{ɓ}}_{r - 2}\| ds$^,^
(14)

$\| W_{r}(ե)\| \leq \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}H_{3}\|{℞_{ɓ}}_{r - 1} - {℞_{ɓ}}_{r - 2}\| + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}K_{3}\|{℞_{ɓ}}_{r - 1} - {℞_{ɓ}}_{r - 2}\| ds$
(15)

$\| T_{r}(ե)\| \leq \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}H_{4}\|{Ᵽ_{ɓ}}_{r - 1} - {Ᵽ_{ɓ}}_{r - 2}\| + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}K_{4}\|{Ᵽ_{ɓ}}_{r - 1} - {Ᵽ_{ɓ}}_{r - 2}\| ds$
(16)

$\| X_{r}(ե)\| \leq \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}H_{5}\|{Ş_{ɑ}}_{r - 1} - {Ş_{ɑ}}_{r - 2}\| + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}K_{5}\|{Ş_{ɑ}}_{r - 1} - {Ş_{ɑ}}_{r - 2}\| ds$
(17)

$\| Y_{r}(ե)\| \leq \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}H_{6}\|{S_{m}}_{r - 1} - {S_{m}}_{r - 2}\| + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}K_{6}\|{ɬ_{ɑ}}_{r - 1} - {ɬ_{ɑ}}_{r - 2}\| ds$
(18)

$\| Z_{r}(ե)\| \leq \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}H_{7}\|{℞_{ɑ}}_{r - 1} - {℞_{ɑ}}_{r - 2}\| + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}K_{7}\|{℞_{ɑ}}_{r - 1} - {℞_{ɑ}}_{r - 2}\| ds$
(19)

**Theorem 3.3**

> The outcome of suggested fractional order system (5) exists under the
> recommended operator.

**Proof**

Using a recursive approach in above equation (13) - (19) presents the
set of equation as follows

$\| U_{r}(ե)\| \leq \| S_{h}(0)\| + \left\{ \left( \frac{2(1 - \alpha)H_{1}}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\} + \left\{ \left( \frac{2\alpha K_{1}ե}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\}$
(20)

$\| V_{r}(ե)\| \leq \| E_{h}(0)\| + \left\{ \left( \frac{2(1 - \alpha)H_{2}}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\} + \left\{ \left( \frac{2\eta K_{2}ե}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\}$
(21)

$\| W_{r}(ե)\| \leq \| T_{h}(0)\| + \left\{ \left( \frac{2(1 - \alpha)H_{3}}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\} + \left\{ \left( \frac{2\eta K_{3}ե}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\}$
(22)

$\| T_{r}(ե)\| \leq \| Ᵽ_{ɓ}(0)\| + \left\{ \left( \frac{2(1 - \alpha)H_{4}}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\} + \left\{ \left( \frac{2\eta K_{4}ե}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\}$
(23)

$\| X_{r}(ե)\| \leq \| R_{h}(0)\| + \left\{ \left( \frac{2(1 - \alpha)H_{5}}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\} + \left\{ \left( \frac{2\alpha K_{5}ե}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\}$
(24)

$\| Y_{r}(ե)\| \leq \| S_{m}(0)\| + \left\{ \left( \frac{2(1 - \alpha)H_{6}}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\} + \left\{ \left( \frac{2\alpha K_{6}ե}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\}$
(25)

$\| Z_{r}(ե)\| \leq \| T_{m}(0)\| + \left\{ \left( \frac{2(1 - \alpha)H_{7}}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\} + \left\{ \left( \frac{2\alpha K_{7}ե}{(2 - \alpha)Ɱ(\alpha)} \right)^{r} \right\}$
(26)

Consequently, the presence of results, which are also continuous, are
confirmed.

We now get

$Ş_{ɓ}(ե) = {Ş_{ɓ}}_{r}(ե) - E_{1,r}(ե),ɬ_{ɓ}(ե) = {ɬ_{ɓ}}_{r}(ե) - E_{2,r}(ե),ɬ_{ɓ}(ե) = {ɬ_{ɓ}}_{r}(ե) - E_{3,r}(ե),$

$Ᵽ_{ɓ}(ե) = {Ᵽ_{ɓ}}_{r}(ե) - E_{4,r}(ե),\ Ş_{ɑ}(ե) = {Ş_{ɑ}}_{r}(ե) - E_{5,r}(ե),\ ɬ_{ɑ}(ե) = {ɬ_{ɑ}}_{r}(ե) - E_{6,r}(ե),$

$℞_{ɑ}(ե) = {℞_{ɑ}}_{r}(ե) - E_{7,r}(ե).$ (27)

Where
$E_{1,r}(ե),E_{2,r}(ե),E_{3,r}(ե),E_{4,r}(ե),E_{5,r}(ե),E_{6,r}(ե)$ and
$E_{7,r}(ե)$ represent the series solution\'s remaining terms.
Consequently

$S_{h}(ե) - {S_{h}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{1}\left( ե,S_{h} - E_{1,r}(ե) \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}Q_{1}\left( s,S_{h} - E_{1,r}(s) \right)ds$,

$E_{h}(ե) - {E_{h}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{2}\left( ե,E_{h} - E_{2,r}(ե) \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}Q_{2}\left( s,E_{h} - E_{2,r}(s) \right)ds$,

$T_{h}(ե) - {T_{h}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{3}\left( ե,T_{h} - E_{3,r}(ե) \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}Q_{3}\left( s,T_{h} - E_{3,r}(s) \right)ds,$

$H_{h}(ե) - {H_{h}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{4}\left( ե,H_{h} - E_{4,r}(ե) \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}Q_{4}\left( s,H_{h} - E_{4,r}(s) \right)ds$

$R_{h}(ե) - {R_{h}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{5}\left( ե,R_{h} - E_{5,r}(ե) \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}Q_{5}\left( s,R_{h} - E_{5,r}(s) \right)ds$,

$S_{m}(ե) - {S_{m}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{6}\left( ե,S_{m} - E_{6,r}(ե) \right) + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}Q_{6}\left( s,S_{m} - E_{6,r}(s) \right)ds$

$T_{m}(ե) - {T_{m}}_{r}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}Q_{7}\left( ե,T_{m} - E_{7,r}(ե) \right)$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)} \times \int_{0}^{ե}{}Q_{7}\left( s,T_{m} - E_{7,r}(s) \right)ds$
(28)

By applying the Lipschitz axiom and using the terms on both sides, the
above claim is established.

$\| S_{h}(ե) - \frac{2(1 - \alpha)Q_{1}\left( ե,S_{h} \right)}{(2 - \alpha)Ɱ(\alpha)} - S_{h}(0) - \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{1}\left( s,S_{h} \right)ds\|$

$\leq \| E_{1,r}(ե)\|\left\{ 1 + \left( \frac{2(1 - \alpha)H_{1}}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha K_{1}ե}{(2 - \alpha)Ɱ(\alpha)} \right) \right\}$

$\| E_{h}(ե) - \frac{2(1 - \alpha)Q_{2}\left( ե,E_{h} \right)}{(2 - \alpha)Ɱ(\alpha)} - E_{h}(0) - \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{2}\left( s,E_{h} \right)ds\|$

$\leq \| E_{2,r}(ե)\|\left\{ 1 + \left( \frac{2(1 - \alpha)H_{2}}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha K_{2}ե}{(2 - \alpha)Ɱ(\alpha)} \right) \right\}$

$\| T_{h}(ե) - \frac{2(1 - \alpha)Q_{3}\left( ե,T_{h} \right)}{(2 - \alpha)Ɱ(\alpha)} - T_{h}(0) - \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{3}\left( s,T_{h} \right)ds\|$

$\leq \| E_{3,r}(ե)\|\left\{ 1 + \left( \frac{2(1 - \alpha)H_{3}}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha K_{3}ե}{(2 - \alpha)Ɱ(\alpha)} \right) \right\}$

$\| H_{h}(ե) - \frac{2(1 - \alpha)Q_{4}\left( ե,H_{h} \right)}{(2 - \alpha)Ɱ(\alpha)} - H_{h}(0) - \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{4}\left( s,H_{h} \right)ds\|$

$\leq \| E_{4,r}(ե)\|\left\{ 1 + \left( \frac{2(1 - \alpha)H_{4}}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha K_{4}ե}{(2 - \alpha)Ɱ(\alpha)} \right) \right\}$,

$\| R_{h}(ե) - \frac{2(1 - \alpha)Q_{5}\left( ե,R_{h} \right)}{(2 - \alpha)Ɱ(\alpha)} - R_{h}(0) - \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{5}\left( s,R_{h} \right)ds\|$

$\leq \| E_{5,r}(ե)\|\left\{ 1 + \left( \frac{2(1 - \alpha)H_{5}}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha K_{5}ե}{(2 - \alpha)Ɱ(\alpha)} \right) \right\}$,

$\| S_{m}(ե) - \frac{2(1 - \alpha)Q_{6}\left( ե,S_{m} \right)}{(2 - \alpha)Ɱ(\alpha)} - S_{m}(0) - \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{6}\left( s,S_{m} \right)ds\|$

$\leq \| E_{6,r}(ե)\|\left\{ 1 + \left( \frac{2(1 - \alpha)H_{6}}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha K_{6}ե}{(2 - \alpha)Ɱ(\alpha)} \right) \right\}$,

$\| T_{m}(ե) - \frac{2(1 - \alpha)Q_{7}\left( ե,T_{m} \right)}{(2 - \alpha)Ɱ(\alpha)} - T_{m}(0) - \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{7}\left( s,T_{m} \right)ds\|$

$\leq \| E_{7,r}(ե)\|\left\{ 1 + \left( \frac{2(1 - \alpha)H_{7}}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha K_{7}ե}{(2 - \alpha)Ɱ(\alpha)} \right) \right\}$
(29)

When lim$\ r \rightarrow \infty$ is used, it indicates that

${Ş_{ɓ}}_{h}(ե) = Ş_{ɓ}(0) + \frac{2(1 - \alpha)Q_{1}\left( ե,Ş_{ɓ} \right)}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{1}\left( s,Ş_{ɓ} \right)ds$

$ɬ_{ɓ}(ե) = ɬ_{ɓ}(0) + \frac{2(1 - \eta)Q_{2}\left( ե,ɬ_{ɓ} \right)}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{2}\left( s,ɬ_{ɓ} \right)ds$

$℞_{ɓ}(ե) = ℞_{ɓ}(0) + \frac{2(1 - \eta)Q_{3}\left( ե,℞_{ɓ} \right)}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{3}\left( s,℞_{ɓ} \right)ds$

$Ᵽ_{ɓ}(ե) = Ᵽ_{ɓ}(0) + \frac{2(1 - \eta)Q_{4}\left( ե,Ᵽ_{ɓ} \right)}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{4}\left( s,Ᵽ_{ɓ} \right)ds$

$Ş_{ɑ}(ե) = Ş_{ɑ}(0) + \frac{2(1 - \alpha)Q_{5}\left( ե,Ş_{ɑ} \right)}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{5}\left( s,Ş_{ɑ} \right)ds$

$ɬ_{ɑ}(ե) = ɬ_{ɑ}(0) + \frac{2(1 - \alpha)Q_{6}\left( ե,ɬ_{ɑ} \right)}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{6}\left( s,ɬ_{ɑ} \right)ds$

$℞_{ɑ}(ե) = ℞_{ɑ}(0) + \frac{2(1 - \alpha)Q_{7}\left( ե,℞_{ɑ} \right)}{(2 - \alpha)Ɱ(\alpha)} + \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}Q_{7}\left( s,℞_{ɑ} \right)ds$
(30)

It demonstrates the results, such as the above-mentioned solutions as
provided by the proposed model\'s Eqn. (5).

***3.2 Uniqueness of Result***

In the following section, we will attempt to establish that the outcomes
that were mentioned in the section that came before this one are
completely independent. We presume that more sets of results are
available for the configuration specified in Eqn. (29).

**Theorem 3.4**

The suggested fractional order epidemiological model Eqn. (5) has a
unique solution.

**Proof**

We assume that
$\left( {Ş_{ɓ}}_{1},{ɬ_{ɓ}}_{1},{℞_{ɓ}}_{1},{Ᵽ_{ɓ}}_{1},{Ş_{ɑ}}_{1},{ɬ_{ɑ}}_{1},{℞_{ɑ}}_{1} \right)$is
also the solutions of suggested fractional model (5), based on the
foundation of contradiction. Therefore

$Ş_{ɓ}(ե) - {Ş_{ɓ}}_{1}(ե) = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\left\lbrack Q_{1}\left( ե,Ş_{ɓ} \right) - Q_{1}\left( ե,{Ş_{ɓ}}_{1} \right) \right\rbrack$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\lbrack Q_{1}\left( s,Ş_{ɓ} \right) - Q_{1}\left( s,{Ş_{ɓ}}_{1} \right) \right\rbrack ds$
(31)

Using the norm on both sides, we obtain

$\| Ş_{ɓ} - {Ş_{ɓ}}_{1}\| = \frac{2(1 - \alpha)}{(2 - \alpha)Ɱ(\alpha)}\left\lbrack \| Q_{1}\left( ե,Ş_{ɓ} \right) - Q_{1}\left( ե,{Ş_{ɓ}}_{1} \right)\| \right\rbrack$

$+ \frac{2\alpha}{(2 - \alpha)Ɱ(\alpha)}\int_{0}^{ե}{}\left\lbrack \| Q_{1}\left( s,Ş_{ɓ} \right) - Q_{1}\left( s,{Ş_{ɓ}}_{1} \right)\| \right\rbrack ds$
(32)

Lipchitz condition is used to get

$\| Ş_{ɓ} - {Ş_{ɓ}}_{1}\| < \frac{2(1 - \alpha)H_{1}}{(2 - \alpha)Ɱ(\alpha)} + \left( \frac{2\alpha K_{1}ե}{(2 - \alpha)Ɱ(\alpha)} \right)^{r}$
(33)

Which is true for all$\ r,\$so $Ş_{ɓ} = {Ş_{ɓ}}_{1}$,

Similarly,$\ ɬ_{ɓ} = {ɬ_{ɓ}}_{1}$,$℞_{ɓ} = {℞_{ɓ}}_{1},Ᵽ_{ɓ} = {Ᵽ_{ɓ}}_{1}$,$Ş_{ɑ} = {Ş_{ɑ}}_{1}$,$ɬ_{ɑ} = {ɬ_{ɑ}}_{1}$
and $℞_{ɑ} = {℞_{ɑ}}_{1}$.

Hence, it claims uniqueness of the system.

**4. Results of the Model Using Sumudu Transform with Caputo-Fabrizio
Derivative**

Using the Caputo Fabrizio approach defined by the Sumudu Transform we
obtain the following:

$M(\alpha)\frac{ST\left( Ş_{ɓ}(ե) \right) - Ş_{ɓ}(0)}{1 - \alpha + \Delta\alpha} = ST\left\lbrack \left( 1 - Ᵽ_{ɓ} \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \mu_{ɓ}Ş_{ɓ} \right\rbrack$

$M(\alpha)\frac{ST\left( ɬ_{ɓ}(ե) \right) - ɬ_{ɓ}(0)}{1 - \alpha + \Delta\alpha} = ST\left\lbrack \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ} \right\rbrack$

$M(\alpha)\frac{ST\left( ℞_{ɓ}(ե) \right) - ℞_{ɓ}(0)}{1 - \alpha + \Delta\alpha} = ST\left\lbrack \gamma_{ɓ}ɬ_{ɓ} - \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}℞_{ɓ} \right\rbrack$

$M(\alpha)\frac{ST\left( Ᵽ_{ɓ}(ե) \right) - Ᵽ_{ɓ}(0)}{1 - \alpha + \Delta\alpha} = ST\left\lbrack \pi_{ɓ}Ᵽ_{ɓ} + \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}Ᵽ_{ɓ} \right\rbrack$

$M(\alpha)\frac{ST\left( Ş_{ɑ}(ե) \right) - Ş_{ɑ}(0)}{1 - \alpha + \Delta\alpha} = ST\left\lbrack \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \mu_{ɑ}Ş_{ɑ} \right\rbrack$

$M(\alpha)\frac{ST\left( ɬ_{ɑ}(ե) \right) - ɬ_{ɑ}(0)}{1 - \alpha + \Delta\alpha} = ST\left\lbrack \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ} \right\rbrack$

$M(\alpha)\frac{ST\left( ℞_{ɑ}(ե) \right) - ℞_{ɑ}(0)}{1 - \alpha + \Delta\alpha} = ST\left\lbrack \gamma_{ɑ}ɬ_{ɑ} - \mu_{ɑ}℞_{ɑ} \right\rbrack$
(34)

By rearranging

$ST\left( Ş_{ɓ}(ե) \right) = Ş_{ɓ}(0) + \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \left( 1 - Ᵽ_{ɓ} \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \mu_{ɓ}Ş_{ɓ} \right\rbrack$

$ST\left( ɬ_{ɓ}(ե) \right) = ɬ_{ɓ}(0) + \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ} \right\rbrack$

$ST\left( ℞_{ɓ}(ե) \right) = ℞_{ɓ}(0) + \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \gamma_{ɓ}ɬ_{ɓ} - \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}℞_{ɓ} \right\rbrack$

$ST\left( Ᵽ_{ɓ}(ե) \right) = H_{h}(0) + \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \pi_{ɓ}Ᵽ_{ɓ} + \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}Ᵽ_{ɓ} \right\rbrack$

$ST\left( Ş_{ɑ}(ե) \right) = Ş_{ɑ}(0) + \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \mu_{ɑ}Ş_{ɑ} \right\rbrack$

$ST\left( ɬ_{ɑ}(ե) \right) = ɬ_{ɑ}(0) + \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ} \right\rbrack$

$ST\left( ℞_{ɑ}(ե) \right) = ℞_{ɑ}(0) + \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \gamma_{ɑ}ɬ_{ɑ} - \mu_{ɑ}℞_{ɑ} \right\rbrack$
(35)

Using inverse Sumudu transform on system (35), we get

$Ş_{ɓ}(ե) = Ş_{ɓ}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \left( 1 - Ᵽ_{ɓ} \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \mu_{ɓ}Ş_{ɓ} \right\rbrack \right\rbrack$

$ɬ_{ɓ}(ե) = ɬ_{ɓ}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ} + \beta_{ɓ_{2}}ɬ_{ɓ} \right)Ş_{ɓ}}{N_{ɓ}} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ} \right\rbrack \right\rbrack$

$℞_{ɓ}(ե) = ℞_{ɓ}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \gamma_{ɓ}ɬ_{ɓ} - \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}℞_{ɓ} \right\rbrack \right\rbrack$

$Ᵽ_{ɓ}(ե) = Ᵽ_{ɓ}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \pi_{ɓ}Ᵽ_{ɓ} + \theta_{ɓ}℞_{ɓ} - \mu_{ɓ}Ᵽ_{ɓ} \right\rbrack \right\rbrack$

$Ş_{ɑ}(ե) = Ş_{ɑ}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \mu_{ɑ}Ş_{ɑ} \right\rbrack \right\rbrack$

$ɬ_{ɑ}(ե) = ɬ_{ɑ}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \frac{\beta_{ɑ}Ş_{ɑ}ɬ_{ɑ}}{N_{ɑ}} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ} \right\rbrack \right\rbrack$

$℞_{ɑ}(ե) = ℞_{ɑ}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \gamma_{ɑ}ɬ_{ɑ} - \mu_{ɑ}℞_{ɑ} \right\rbrack \right\rbrack$
(36)

Given recursive technique is as follows

$Ş_{ɓ_{n + 1}}(ե) = Ş_{ɓ_{n}}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \left( 1 - Ᵽ_{ɓ_{n}} \right)\pi_{ɓ} - \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ_{n}} + \beta_{ɓ_{2}}ɬ_{ɓ_{n}} \right)Ş_{ɓ_{n}}}{N_{ɓ}} - \mu_{ɓ}Ş_{ɓ_{n}} \right\rbrack \right\rbrack$

$ɬ_{ɓ_{n + 1}}(ե) = ɬ_{ɓ_{n}}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \frac{\left( \beta_{ɓ_{1}}ɬ_{ɑ_{n}} + \beta_{ɓ_{2}}ɬ_{ɓ_{n}} \right)Ş_{ɓ_{n}}}{N_{ɓ}} - \left( \gamma_{ɓ} + \mu_{ɓ} + ԃ_{ɓ} \right)ɬ_{ɓ_{n}} \right\rbrack \right\rbrack$

$℞_{ɓ_{n + 1}}(ե) = ℞_{ɓ_{n}}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \gamma_{ɓ}ɬ_{ɓ_{n}} - \theta_{ɓ}℞_{ɓ_{n}} - \mu_{ɓ}℞_{ɓ_{n}} \right\rbrack \right\rbrack$

$Ᵽ_{ɓ_{n + 1}}(ե) = Ᵽ_{ɓ_{n}}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \pi_{ɓ}Ᵽ_{ɓ_{n}} + \theta_{ɓ}℞_{ɓ_{n}} - \mu_{ɓ}Ᵽ_{ɓ_{n}} \right\rbrack \right\rbrack$

$Ş_{ɑ_{n + 1}}(ե) = Ş_{ɑ_{n}}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \pi_{ɑ} - \frac{\beta_{ɑ}Ş_{ɑ_{n}}ɬ_{ɑ_{n}}}{N_{ɑ}} - \mu_{ɑ}Ş_{ɑ_{n}} \right\rbrack \right\rbrack$

$ɬ_{ɑ_{n + 1}}(ե) = ɬ_{ɑ_{n}}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \frac{\beta_{ɑ}Ş_{ɑ_{n}}ɬ_{ɑ_{n}}}{N_{ɑ}} - \left( \gamma_{ɑ} + \mu_{ɑ} + ԃ_{ɑ} \right)ɬ_{ɑ_{n}} \right\rbrack \right\rbrack$

$℞_{ɑ_{n + 1}}(ե) = ℞_{ɑ_{n}}(0) + {ST}^{- 1}\left\lbrack \frac{1 - \alpha + \Delta\alpha}{M(\alpha)}ST\left\lbrack \gamma_{ɑ}ɬ_{ɑ_{n}} - \mu_{ɑ}℞_{ɑ_{n}} \right\rbrack \right\rbrack$
(37)

and the solution is given

$Ş_{ɓ}(ե) = Ş_{ɓ_{n}}(ե)\ ,ɬ_{ɓ}(ե) = ɬ_{ɓ_{n}}(ե)\ ,℞_{ɓ}(ե) = ℞_{ɓ_{n}}(ե)\ ,$

$Ᵽ_{ɓ}(ե) = Ᵽ_{ɓ_{n}}(ե)\ ,Ş_{ɑ}(ե) = Ş_{ɑ_{n}}(ե)\ ,ɬ_{ɑ}(ե) = ɬ_{ɑ_{n}}(ե)\ ,$

$℞_{ɑ}(t) = ℞_{ɑ_{n}}(t)\ .$ (38)

**5. Result and Discussion**

This section presents the numerical simulations of the proposed
monkeypox transmission model using the Sumudu transform method at
varying fractional orders. The analysis is performed to understand how
changes in the fractional order affect the progression of disease within
human and animal populations. The simulations are conducted using
MATLAB, based on Equation (38), and employ parameter values provided in
Table 1. The results are visualized through Figures 1 to 3.

Figure 1 illustrates the transmission dynamics of monkeypox within the
human population for three different fractional orders: 0.6, 0.8, and
1.0. At a lower fractional order of 0.6, the susceptible population
declines more sharply, indicating that the infection spreads rapidly
through the population during the initial stages. This sharper decline
is attributed to the stronger memory effect present in systems of lower
fractional order, which accelerates the movement between compartments.
In contrast, at higher fractional orders of 0.8 and 1.0, the decline of
the susceptible population is more gradual, suggesting a slower
transmission rate and delayed progression of the infection. The infected
population, however, grows more prominently at higher fractional orders.
This suggests that with a weaker memory effect, the infection persists
for longer durations and reaches a higher peak, especially in the case
of the classical model (fractional order 1.0). The recovered and
protected compartments also demonstrate increased accumulation at higher
fractional orders, indicating that more individuals eventually
transition out of infection as the system evolves more slowly over time.
In lower fractional-order cases, the transitions are more rapid but
result in fewer individuals being retained in the recovered or protected
states over the simulated period.

Figure 2 focuses on the animal population dynamics under the same
fractional orders. The behaviour observed in animal hosts complements
the findings in the human population. The susceptible animal population
shows a slower decline as the fractional order increases, reflecting a
more prolonged exposure period and delayed transmission. Meanwhile, the
infected and recovered animal populations display more significant
growth at higher fractional orders, which is consistent with the reduced
pace of change inherent in such systems. The gradual progression and
delayed peak in the infected compartment at higher orders again
highlight how fractional calculus, particularly with larger α values,
slows the system evolution, thereby extending the duration of disease
presence within the population. These simulations confirm that
fractional-order modelling provides valuable insight into the real-world
dynamical behaviour of infectious diseases, especially when memory
effects and complex transitions are involved.

Figure 3 depicts the dynamics of the full proposed monkeypox model,
incorporating both human and animal populations, based on real data from
reported monkeypox cases in India as cited in \[48\] and detailed in
Table 1. Unlike Figures 1 and 2, this simulation is conducted with the
model calibrated to actual outbreak data, providing a realistic picture
of disease transmission and recovery patterns. The trajectories of the
different compartments validate the model's capability to capture real
epidemic behaviour. The simulation results align well with observed
data, demonstrating the model\'s effectiveness in portraying disease
spread, peak infection periods, and eventual recovery dynamics. The
consistency between the model outcomes and empirical data underscores
the potential of using fractional-order systems in combination with the
Sumudu transform to realistically represent complex infectious disease
processes, offering better flexibility and accuracy in capturing delayed
responses and memory-dependent phenomena.

In conclusion, the simulation outcomes underscore the significance of
fractional-order parameters in shaping the transmission dynamics of
monkeypox. Lower fractional orders accelerate transitions and reduce
disease persistence, while higher orders induce slower, more sustained
outbreaks. The Sumudu transform method proves effective in resolving the
model equations, enabling clearer visualization and interpretation of
complex system behavior under varying fractional dynamics.

![](G:\work\Journal2LaTeX\backend\temp\cd6c007a-5814-4e06-ad27-b50091d23aa9\intermediate\media/media/image1.png){width="6.268055555555556in"
height="4.825in"}

**Figure 1:** Transmission dynamics of monkeypox in the human population
at different fractional orders (0.6, 0.8, and 1.0) using the Sumudu
transform.

![](G:\work\Journal2LaTeX\backend\temp\cd6c007a-5814-4e06-ad27-b50091d23aa9\intermediate\media/media/image2.png){width="5.7347222222222225in"
height="4.767361111111111in"}

**Figure 2:** Animal population dynamics under different fractional
orders (0.6, 0.8, and 1.0), showing variations in susceptible, infected,
and recovered compartments.

![](G:\work\Journal2LaTeX\backend\temp\cd6c007a-5814-4e06-ad27-b50091d23aa9\intermediate\media/media/image3.png){width="5.112774496937883in"
height="5.238167104111986in"}

> **Figure 3:** Simulation of the proposed monkeypox model using real
> data, illustrating the disease progression across human and animal
> populations.

**6.Conclusion**

In this research, a novel fractional-order monkeypox transmission model
has been developed using the Caputo-Fabrizio fractional derivative to
effectively capture the memory and hereditary characteristics inherent
in biological systems. By incorporating key epidemiological
compartments, the model realistically reflects the stages of monkeypox
infection and transmission. The Sumudu transform method was employed to
derive analytical solutions, demonstrating its efficiency in handling
fractional differential equations. To ensure the reliability of the
results, the existence and uniqueness of solutions were established
using fixed-point theory and the Picard--Lindelöf approach. This study
offers several advantages, including the ability to model nonlocal and
memory-dependent dynamics, a simplified analytical procedure through the
Sumudu transform, and a mathematically rigorous framework that enhances
the understanding of disease progression. The proposed model not only
provides deeper insights into the complex behaviour of monkeypox spread
but also serves as a valuable tool for informing public health
strategies. Future research may focus on incorporating optimal control
techniques to evaluate the effectiveness of intervention measures such
as vaccination and public awareness campaigns, integrating real
epidemiological data for validation, and extending the model to include
spatial dynamics and stochastic influences for a more comprehensive
representation of monkeypox outbreaks.

**Declaration of competing interest**

The authors declare there is no competing interest.

**Acknowledgement**

All authors have read and approved the article.

**Author's credit**

M.R have overall writing, M.A have conceptualised, J.P have supervised,
G.M.V have validated and P.R.B have done visualisation.

**Funding**

No funding received.

**References**

1.  Sklenovská, N., & Van Ranst, M. (2018). *Emergence of monkeypox as
    the most important orthopoxvirus infection in humans*. Frontiers in
    Public Health, 6, 241.
    [[https://doi.org/10.3389/fpubh.2018.00241]{.underline}](https://doi.org/10.3389/fpubh.2018.00241)

2.  Centers for Disease Control and Prevention, National Center for
    Emerging and Zoonotic Infectious Diseases (NCEZID), Division of
    High-Consequence Pathogens and Pathology (DHCPP), Monkeypox (2021,
    accessed 11, Nov
    2021). [[https://cdc.gov/poxvirus/monkeypox/index.html]{.underline}](https://cdc.gov/poxvirus/monkeypox/index.html).

3.  Bunge, E. M., Hoet, B., Chen, L., Lienert, F., Weidenthaler, H.,
    Baer, L. R., & Steffen, R. (2022). *The changing epidemiology of
    human monkeypox---A potential threat? A systematic review*. PLoS
    Neglected Tropical Diseases, 16(2), e0010141.
    [[https://doi.org/10.1371/journal.pntd.0010141]{.underline}](https://doi.org/10.1371/journal.pntd.0010141)

4.  Yinka-Ogunleye, A., Aruna, O., Dalhat, M., et al. (2018). *Outbreak
    of human monkeypox in Nigeria in 2017--18: A clinical and
    epidemiological report*. The Lancet Infectious Diseases, 19(8),
    872--879.

5.  Thornhill, J. P., Barkati, S., Walmsley, S., et al. (2022).
    *Monkeypox virus infection in humans across 16 countries ---
    April--June 2022*. New England Journal of Medicine, 387(8),
    679--691.

6.  Reynolds, M. G., Damon, I. K., & McCollum, A. M. (2019). *Vaccines
    and immunotherapeutics for monkeypox: A review of the current
    pipeline*. Vaccine, 37(43), 5995--6000.

7.  Rao, A. K., Petersen, B. W., Whitehill, F., et al. (2022). *Use of
    JYNNEOS (smallpox and monkeypox vaccine, live, nonreplicating) for
    preexposure vaccination of persons at risk for occupational exposure
    to orthopoxviruses: Recommendations of the Advisory Committee on
    Immunization Practices --- United States, 2022*. MMWR Morb Mortal
    Wkly Rep, 71(22), 734--742.

8.  Peter, O. J., Kumar, S., Kumari, N., Oguntolu, F. A., Oshinubi, K.,
    & Musa, R. (2022). Transmission dynamics of Monkeypox virus: a
    mathematical modelling approach. *Modeling Earth Systems and
    Environment*, 1-12.

9.  Ngungu, M., Addai, E., Adeniji, A., Adam, U. M., & Oshinubi, K.
    (2023). Mathematical epidemiological modeling and analysis of
    monkeypox dynamism with non-pharmaceutical intervention using real
    data from United Kingdom. *Frontiers in Public Health*, *11*,
    1101436.

10. Baba, B. A., & Bilgehan, B. (2021). Optimal control of a fractional
    order model for the COVID--19 pandemic. *Chaos, Solitons &
    Fractals*, *144*, 110678.

11. Ameen, I., Baleanu, D., & Ali, H. M. (2020). An efficient algorithm
    for solving the fractional optimal control of SIRV epidemic model
    with a combination of vaccination and treatment. *Chaos, Solitons &
    Fractals*, *137*, 109892.

12. Abioye, A. I., Peter, O. J., Ogunseye, H. A., Oguntolu, F. A.,
    Oshinubi, K., Ibrahim, A. A., & Khan, I. (2021). Mathematical model
    of COVID-19 in Nigeria with optimal control. *Results in
    Physics*, *28*, 104598.

13. Kumar, S., Chauhan, R. P., Momani, S., & Hadid, S. (2024). Numerical
    investigations on COVID‐19 model through singular and non‐singular
    fractional operators. *Numerical Methods for Partial Differential
    Equations*, *40*(1), e22707.

14. Bankuru, S. V., Kossol, S., Hou, W., Mahmoudi, P., Rychtář, J., &
    Taylor, D. (2020). A game-theoretic model of Monkeypox to assess
    vaccination strategies. *PeerJ*, *8*, e9272.

15. Usman, S., & Adamu, I. I. (2017). Modeling the transmission dynamics
    of the monkeypox virus infection with treatment and vaccination
    interventions. *Journal of Applied Mathematics and
    Physics*, *5*(12), 2335.

16. Alshehri, A., & Ullah, S. (2023). Optimal control analysis of
    Monkeypox disease with the impact of environmental
    transmission. *Aims Math*, *8*(7), 16926-16960.

17. Allehiany, F. M., DarAssi, M. H., Ahmad, I., Khan, M. A., &
    Tag-Eldin, E. M. (2023). Mathematical modeling and backward
    bifurcation in monkeypox disease under real observed data. *Results
    in Physics*, *50*, 106557.

18. Rihan, F. A., Baleanu, D., Lakshmanan, S., & Rakkiyappan, R. (2014).
    On fractional SIRC model with salmonella bacterial infection.
    In *Abstract and Applied Analysis* (Vol. 2014, No. 1, p. 136263).
    Hindawi Publishing Corporation.

19. Baba, I. A., & Nasidi, B. A. (2021). Fractional order epidemic model
    for the dynamics of novel COVID-19. *Alexandria Engineering
    Journal*, *60*(1), 537-548.

20. Rihan, F. A. (2013). Numerical modeling of fractional‐order
    biological systems. In *Abstract and applied analysis* (Vol. 2013,
    No. 1, p. 816803). Hindawi Publishing Corporation.

21. Ali, A., Ullah, S., & Khan, M. A. (2022). The impact of vaccination
    on the modeling of COVID-19 dynamics: a fractional order
    model. *Nonlinear Dynamics*, *110*(4), 3921-3940.

22. Saeedian, M., Khalighi, M., Azimi-Tafreshi, N., Jafari, G. R., &
    Ausloos, M. (2017). Memory effects on epidemic evolution: The
    susceptible-infected-recovered epidemic model. *Physical Review
    E*, *95*(2), 022409.

23. Ahmed, I., Baba, I. A., Yusuf, A., Kumam, P., & Kumam, W. (2020).
    Analysis of Caputo fractional-order model for COVID-19 with
    lockdown. *Advances in difference equations*, *2020*(1), 394.

24. Aba Oud, M. A., Ali, A., Alrabaiah, H., Ullah, S., Khan, M. A., &
    Islam, S. (2021). A fractional order mathematical model for COVID-19
    dynamics with quarantine, isolation, and environmental viral
    load. *Advances in Difference Equations*, *2021*, 1-19.

25. Vijayalakshmi, G. M., & Roselyn Besi, P. (2022). ABC fractional
    order vaccination model for Covid-19 with self-protective
    measures. *International Journal of Applied and Computational
    Mathematics*, *8*(3), 130.

26. Vijayalakshmi, G. M., Besi, P. R., Kalaivani, A., Sujitha, G. I., &
    Mahesh, S. (2024). Microbial coinfections in COVID-19: mathematical
    analysis using Atangana--Baleanu--Caputo type. *Multiscale and
    Multidisciplinary Modeling, Experiments and Design*, *7*(4),
    4097-4116.

27. Vijayalakshmi, G. M., Roselyn Besi, P., & Akgül, A. (2024).
    Fractional commensurate model on COVID‐19 with microbial
    co‐infection: An optimal control analysis. *Optimal Control
    Applications and Methods*, *45*(3), 1108-1121.

28. Khan, A., Sabbar, Y., & Din, A. (2022). Stochastic modeling of the
    Monkeypox 2022 epidemic with cross-infection hypothesis in a highly
    disturbed environment. *Math. Biosci. Eng*, *19*(12), 13560-13581.

29. Alzubaidi, A. M., Othman, H. A., Ullah, S., Ahmad, N., & Alam, M. M.
    (2023). Analysis of Monkeypox viral infection with human to animal
    transmission via a fractional and Fractal-fractional operators with
    power law kernel. *Math. Biosci. Eng*, *20*(4), 6666-6690.

30. Asamoah, J. K. K., Okyere, E., Yankson, E., Opoku, A. A.,
    Adom-Konadu, A., Acheampong, E., & Arthur, Y. D. (2022).
    Non-fractional and fractional mathematical analysis and simulations
    for Q fever. *Chaos, Solitons & Fractals*, *156*, 111821.

31. Vijayalakshmi, G. M., & Ariyanatchi, M. (2024). Adams--Bashforth
    Moulton Numerical Approach on Dengue Fractional Atangana Baleanu
    Caputo Model and Stability Analysis. *International Journal of
    Applied and Computational Mathematics*, *10*(1), 32.

32. Ariyanatchi, M., & Vijayalakshmi, G. M. (2024). Nonlinear Robust
    Adaptive Sliding Mode Control Strategies Involve a Fractional
    Ordered Approach to Reducing Dengue Vectors. *Results in Control and
    Optimization*, *14*, 100406.

33. Peter, O. J., Shaikh, A. S., Ibrahim, M. O., Nisar, K. S., Baleanu,
    D., Khan, I., & Abioye, A. I. (2021). Analysis and dynamics of
    fractional order mathematical model of COVID-19 in Nigeria using
    atangana-baleanu operator.

34. Morales-Delgadoa, V. F., Gomez-Aguilar, J. F., Taneco-Hernandez, M.
    A., Escobar Jiménez, R. F., & Olivares Peregrino, V. H. (2018).
    Mathematical modeling of the smoking dynamics using fractional
    differential equations with local and nonlocal kernel. *J. Nonlinear
    Sci. Appl*, *11*(8), 994-1014.

35. Vijayalakshmi, G. M., Ariyanatchi, M., Cepova, L., & Karthik, K.
    (2024). Advanced optimal control approaches for immune boosting and
    clinical treatment to enhance dengue viremia models using ABC
    fractional-order analysis. *Frontiers in Public Health*, *12*,
    1398325.

36. Vijayalakshmi, G. M., Ariyanatchi, M., Govindan, V., & Inc, M.
    (2025). Fractal-fractional modelling of thrombocytopenia influence
    on pregnant women in the context of dengue infection with
    Mittag--Leffler decay analysis. *Modeling Earth Systems and
    Environment*, *11*(2), 1-18

37. Zhang, L., Addai, E., Ackora-Prah, J., Arthur, Y. D., &
    Asamoah, J. K. K. (2022). Fractional‐Order Ebola‐Malaria Coinfection
    Model with a Focus on Detection and Treatment Rate. *Computational
    and Mathematical Methods in Medicine*, *2022*(1), 6502598.

38. Aslam, M., Murtaza, R., Abdeljawad, T., Rahman, G. U., Khan, A.,
    Khan, H., & Gulzar, H. (2021). A fractional order HIV/AIDS epidemic
    model with Mittag-Leffler kernel. *Advances in Difference
    Equations*, *2021*, 1-15.

39. Addai, E., Zhang, L., Preko, A. K., & Asamoah, J. K. K. (2022).
    Fractional order epidemiological model of SARS-CoV-2 dynamism
    involving Alzheimer's disease. *Healthcare Analytics*, *2*, 100114.

40. Shaikh, A. S., & Nisar, K. S. (2019). Transmission dynamics of
    fractional order Typhoid fever model using Caputo--Fabrizio
    operator. *Chaos, Solitons & Fractals*, *128*, 355-365.

41. Higazy, M., & Alyami, M. A. (2020). New Caputo-Fabrizio fractional
    order SEIASqEqHR model for COVID-19 epidemic transmission with
    genetic algorithm based control strategy. *Alexandria Engineering
    Journal*, *59*(6), 4719-4736.

42. Baba, I. A., & Ghanbari, B. (2019). Existence and uniqueness of
    solution of a fractional order tuberculosis model. *The European
    Physical Journal Plus*, *134*, 1-10.

43. Fatmawati, Khan, M. A., Alfiniyah, C., & Alzahrani, E. (2020).
    Analysis of dengue model with fractal-fractional Caputo--Fabrizio
    operator. *Advances in Difference Equations*, *2020*(1), 422.

44. Qureshi, S., Yusuf, A., Ali Shaikh, A., İnç, M., & Baleanu, D.
    (2020). Mathematical modeling for adsorption process of dye removal
    nonlinear equation using power law and exponentially decaying
    kernels. *Chaos: An Interdisciplinary Journal of Nonlinear
    Science*, *30*(4).

45. Sher, M., Shah, K., Khan, Z. A., Khan, H., & Khan, A. (2020).
    Computational and theoretical modeling of the transmission dynamics
    of novel COVID-19 under Mittag-Leffler power law. *Alexandria
    Engineering Journal*, *59*(5), 3133-3147.

46. Peter, O. J., Oguntolu, F. A., Ojo, M. M., Olayinka Oyeniyi, A.,
    Jan, R., & Khan, I. (2022). Fractional order mathematical model of
    monkeypox transmission dynamics. *Physica Scripta*, *97*(8), 084005.

47. Peter, O. J., Kumar, S., Kumari, N., Oguntolu, F. A., Oshinubi, K.,
    & Musa, R. (2022). *Transmission dynamics of monkeypox virus: a
    mathematical modeling approach. Model Earth Syst Environ 8:
    3423--3434*.

48. [Monkeypox Cases: 27 confirmed monkeypox cases reported in India:
    Government to Lok Sabha - The Economic
    Times](https://economictimes.indiatimes.com/news/india/27-confirmed-monkeypox-cases-reported-in-india-government-to-lok-sabha/articleshow/102208281.cms).
    <https://economictimes.indiatimes.com//news/india/27-confirmed-monkeypox-cases-reported-in-india-government-to-lok-sabha/articleshow/102208281.cms?utm_source=contentofinterest&utm_medium=text&utm_campaign=cppst>
