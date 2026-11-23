# Competition: who is already here, and why Bagdar still has a way in

Basis: the research report and notes of 23 November 2026. "Unverified": the notes could not confirm the claim on a primary page. "Secondary": confirmed only through a retelling.

## The short answer

Bagdar's algorithms are about thirty years old: the hidden Markov model is Bayesian Knowledge Tracing ([Corbett & Anderson, 1995](https://link.springer.com/doi/10.1007/BF01099821)), and prerequisite graphs and belief-based step choice are just as old. Everyone has them: ALEKS, MATHia and Math Academy sell the same parts, and readiness scores are sold too. Incumbents win on content and distribution, not on a better algorithm. The report's own conclusion is that Bagdar wins on honesty, not on algorithms. The opening is narrow and specific: a numeric forecast that is checked in public, with a route and a reason for every step, for one exam (UNT) in Kazakh, in a product that is not a chat.

## The field

| Player | What is inside | Scale and price (with year) | Their path | Where it falls short | What Bagdar takes from it |
|---|---|---|---|---|---|
| Duolingo | Forgetting model for words ([Settles & Meeder, 2016](https://aclanthology.org/P16-1174/)); a difficulty model and an LLM layer (both unverified) | Q3 2026: 64.9M daily users, 13.1M paid, $309.0M revenue ([SEC 8-K](https://www.sec.gov/Archives/edgar/data/0001562088/000162828026069474/q3fy26duolingo9-30x26share.htm)) | Habit and distribution | Its streak numbers measure return visits, not learning ([Duolingo blog](https://blog.duolingo.com/improving-the-streak), secondary) | Scale comes from habit, not from the model. Bagdar does not model forgetting yet. |
| Khan Academy Khanmigo | LLM chat over Khan's mastery system ([THE Journal, 2025](https://thejournal.com/articles/2025/10/14/khan-academy-revamps-platform-for-school-districts.aspx)) | About 1M students expected this school year; $10-15 per student per year for districts ([AASA](https://www.aasa.org/resources/resource/a-conversation-with-sal-khan), read 2026) | Brand and schools | About 15% of students with access use it regularly ([EdTech Innovation Hub](https://www.edtechinnovationhub.com/news/only-15-percent-of-students-with-access-to-khanmigo-actually-use-it-khan-academy-admits)) | The bottleneck is showing up, not intelligence. Do not build a chat. |
| Math Academy | Knowledge graph, mastery learning, hierarchical spaced repetition ([Math Academy](https://mathacademy.com/how-our-ai-works)) | $49 per month by user comments, March 2025 ([HN](https://news.ycombinator.com/item?id=43241499)); revenue not found | Hand-built topic graph with content (researchers' assessment) | Price, long diagnostic, rigidity, no proper mobile version | The closest architecture. Its complaint list is a requirement list. |
| ALEKS (McGraw Hill) | Knowledge Space Theory with an adaptive diagnostic (unverified, [aleks.com](https://www.aleks.com/about_aleks/knowledge_space_theory)) | Not in the notes | Publisher product, 1990s technology (unverified) | g = 0.05 against traditional teaching in a 2021 meta-analysis of 33 studies ([OpenDevEd](https://docs.opendeved.net/lib/VRV8U8L2), secondary) | A graph gives navigation and diagnosis, not a proven gain. |
| Squirrel AI | "Large adaptive model" for all K-12 subjects | 24M students through about 3,000 partner centres, self-reported, undated ([WEF profile](https://www.weforum.org/organizations/squirrel-ai-learning/)) | Offline network of centres | Every figure is self-reported | Reach came through partners. Bagdar plans one or two course partners. |
| Carnegie Learning MATHia | Cognitive tutor with Bayesian Knowledge Tracing (unverified, [company page](https://www.carnegielearning.com/solutions/math/mathia/)) | Not in the notes | Not in the notes | Nothing recorded in the notes | The direct ancestor of Bagdar's HMM. Say so openly. |
| Knewton | Adaptive engine licensed to publishers | About $180M raised; assets sold to Wiley in 2019 ([Inside Higher Ed](https://www.insidehighered.com/blogs/just-visiting/knewton-gone-larger-threat-remains)) | Licensing to Pearson and others | No content and no learner of its own | Never pitch a "content-agnostic engine". |
| Speak | Voice LLM tutor, not a mastery engine | $78M round at a $1B valuation, December 2024 ([TechCrunch](https://techcrunch.com/2024/12/10/openai-backed-speak-raises-78m-at-1b-valuation-to-help-users-learn-languages-by-talking-out-loud)) | YC company; round led by Accel | A different product: no skill model | The one large YC outcome in the category is not an adaptive engine. |
| ChatGPT Study Mode | Socratic questions inside a general chat | Launched 29 July 2025 ([TechCrunch](https://techcrunch.com/2025/07/29/openai-launches-study-mode-in-chatgpt)); price not in the notes | Platform distribution | Can be switched off; schools cannot lock it | A platform risk, and an argument for "not a chat". |
| Anki / FSRS | Open scheduler with a memory model fitted to each user's history (unverified, [GitHub](https://github.com/open-spaced-repetition/fsrs4anki)) | Free; in Anki since version 23.10 (2023) | Open source | No trial found showing better exam results than a simpler schedule | The standard to match if Bagdar adds spaced reviews. |
| Readiness scores: UWorld, Achievable, AMBOSS | UWorld: pass chance in four categories, formula closed ([UWorld](https://nursing.uworld.com/blog/what-is-a-good-uworld-nclex-score-interpreting-your-uworld-nclex-score/)). Achievable: readiness 0-100% ([Achievable](https://achievable.me/exams/finra-series-7/faq/)). AMBOSS: score predictor with a published description ([AMBOSS](https://support.amboss.com/hc/en-us/articles/25051050379921-USMLE-Score-Predictor-Score-Calculation-and-How-to-Interpret)) | Prices not in the notes; pages read in 2026 | Question banks for licensing exams | No public predicted-versus-actual chart and no independent validation found | Readiness is not new. A public ledger would be. |
| UNT players: JUZ40, Qalan, iTest, others | Prep schools; iTest is a free trainer with about 60,000 questions ([App Store](https://apps.apple.com/us/app/id1102292074)). Score forecast or adaptive plan: unverified | Revenue: JUZ40 19.95bn tenge, Qalan 10.6bn tenge ([Digital Business](https://digitalbusiness.kz/2025-06-24/v-kazahstane-opredelili-luchshie-obrazovatelnie-kompanii-reyting/), 2025, secondary). Sabaq.online: 27,900-44,900 tenge per programme ([Informburo](https://informburo.kz/cards/kak-besplatno-podgotovitsia-k-ent-prilozeniia-servisy-i-obrazovatelnye-platformy)). Free state lessons ([gov.kz](https://www.gov.kz/memleket/entities/edu/press/news/details/299699?lang=ru)) | Brand and teacher-influencers; Qalan pays learners cashback | Unknown until checked by hand | Demand is proven and the market is occupied. Partner before competing. |

## Their mistakes, as lessons

1. **Knewton sold an engine.** It raised about $180M, licensed to publishers, and sold its assets in 2019 ([Inside Higher Ed](https://www.insidehighered.com/blogs/just-visiting/knewton-gone-larger-threat-remains)). Lesson: an engine without its own content and learner depends on partners. Bagdar ships its own content pack to its own learner.
2. **Khanmigo is rarely used.** About 15% of students with access use it regularly ([EdTech Innovation Hub](https://www.edtechinnovationhub.com/news/only-15-percent-of-students-with-access-to-khanmigo-actually-use-it-khan-academy-admits)). A two-year randomised trial in 18 Tennessee schools found +1.3 national percentile points per semester, comparable to ordinary Khan practice without AI ([NBER w35620](https://www.nber.org/papers/w35620); [KQED](https://www.kqed.org/mindshift/66662/students-didnt-get-answers-from-khanmigo-they-didnt-want-its-questions-either)). Lesson: a glass box does not create the will to study. Bagdar lists engagement as an open risk.
3. **Free ChatGPT practice lowered exam scores.** Among about 1,000 high-school students, a plain GPT-4 chat raised practice results by 48% and lowered the later unaided exam by 17%. A hints-only version mostly removed the harm but gave no gain (Bastani et al., 2025: [RePEc](https://ideas.repec.org/a/nas/journl/v122y2025pe2422633122.html), read from the abstract). Lesson: withholding answers avoids harm; it does not prove benefit. Bagdar asks for an attempt before any explanation.
4. **Readiness formulas are closed.** UWorld does not reveal its formula, and forum users report failing after a "very high" rating ([allnurses](https://allnurses.com/uworld-predictor-amp-actual-nclex-t650421)). Lesson: a number nobody can check is a claim. Bagdar computes every forecast P(correct) from the answers before it and lists it against what happened.
5. **Math Academy on Hacker News.** Users complain about price, a long starting diagnostic, rigidity (easy reviews as "punishment" for one careless error) and no proper mobile version ([HN](https://news.ycombinator.com/item?id=43241499)). Lesson: rigidity is the cost of structure. Bagdar diagnoses while teaching, models slips, allows a detour and works at phone width.
6. **Streaks and rewards.** A logged broken streak makes people less likely to continue ([Silverman & Barasch, 2023](https://www.colorado.edu/business/faculty-research/2023/04/19/or-track-how-broken-streaks-affect-consumer-decisions), secondary). Rewards for completion reduce intrinsic motivation, d = -0.36 ([Deci, Koestner & Ryan, 1999](https://pubmed.ncbi.nlm.nih.gov/10589297/), secondary). Lesson: streaks buy return visits, not knowledge. Bagdar has no streaks, points or badges.

## Where Bagdar is NOT different

- **Algorithms.** The HMM is BKT, the graph is standard since ALEKS, and rival planners are trained on millions of real trajectories. BKT-class models also trail other models on accuracy ([Gervet et al., 2020](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/451)).
- **Exam readiness as a feature.** UWorld, Achievable and AMBOSS already sell it.
- **Explainability as a reason to buy.** A teenager buys a score and a grant; a parent buys confidence (researchers' assessment).

## Where it is

- A numeric pass probability, an ETA in minutes and the reason for the step on one screen. Found competitors use coarse scales and closed methods.
- A public calibration ledger of predicted versus actual. No found competitor publishes one.
- Not a chat: the learner cannot ask for the answer, and the product has memory and a plan.
- Diagnosis while teaching instead of a long placement test.
- A soft response to a lucky guess or a slip, because the HMM models both.
- Learner control with a priced detour: the route shows the minutes a detour adds.
- Offline, zero dependencies, data stays on the device when run locally: relevant to schools with weak internet.
- Kazakh language and UNT format. Several official attempts per year allow fast public checks of the forecast.

## Why a small newcomer can still win

1. **A wedge incumbents ignore.** In 2026 about 233,000 applicants sat UNT 422,000 times, 73.1% of them in Kazakh ([Ministry of Science](https://www.gov.kz/memleket/entities/sci/press/news/details/1257149?lang=ru)). English-language products are weak here. Falsified if a local player already shows a score forecast, or a platform ships one in Kazakh.
2. **Trust compounds.** Each published forecast adds to a record that cannot be backdated. Falsified if the forecasts are badly calibrated on real learners, or if two mock exams predict as well.
3. **No LLM bill.** Standard-library Python and plain JavaScript: a free navigator costs almost nothing to run. Falsified if content, not compute, is the main cost, which the report expects.
4. **Speed on one exam.** One builder, one exam, one language. Falsified if a calibrated UNT question bank in Kazakh needs subject experts the founder does not have.
5. **Closed formulas are a business choice.** Publishing misses is hard to start once revenue rests on the predictor. This is reasoning, not a finding. Falsified if an incumbent publishes calibration, or if visible misses drive learners away ([Dietvorst et al., 2015](https://faculty.wharton.upenn.edu/wp-content/uploads/2016/11/20-Dietvorst-Simmons-Massey-2015.pdf), secondary).

## What must be proven next

1. Check by hand whether JUZ40, Qalan, iTest or Joo already show a score forecast or an adaptive plan. If so, the wedge narrows sharply.
2. Compare Bagdar's forecast with the average of two mock exams. If the model is not better, the engine adds nothing.
3. Run a pilot with real learners, with the metric announced in advance, and publish predicted versus actual.

The tutoring results so far are simulations (seed 7, 20,000 simulated skills per rule): payoff 1.97 against 0.71 for a three-in-a-row rule; forecast calibration error 0.002 when the model is right, 0.091 with wrong parameters. They are not evidence of real learning gains.

## Reasons this may fail

- Content costs more than the engine: a calibrated UNT bank in Kazakh is months of expert work.
- Cold-start parameters for a new content pack are assumed, so early forecasts will be poorly calibrated.
- Two mock exams may predict the score as well as the model.
- Engagement is unsolved: day-30 retention of education apps is about 2-8% ([Business of Apps](https://www.businessofapps.com/?p=98187); [GetStream](https://getstream.io/blog/app-retention-guide)).
- No study was found on how a personal pass probability affects students; an honest ETA may demotivate.
- A specialist sees the weak spots: A* is trivial on a graph with only hard prerequisites, QMDP puts no value on information, forgetting is not modelled, and multiple choice is a weak form of retrieval.
- The local market is occupied and small; the customer leaves after the exam; the payer is a parent.
- Platforms can close the wedge, and the ministry can change the UNT format by order.
- "Bagdar" was already used for a 2018 career-guidance system in Kazakhstan ([Astana Times](https://astanatimes.com/2018/09/bagdar-offers-innovative-approach-for-career-path-employment-and-education/)).

## Addendum: a first check on real students

After this analysis was written, the knowledge model was fitted and tested on public answer logs (ASSISTments 2009-2010, school mathematics). It was fitted with Baum-Welch on 3,322 students and asked to forecast 52,840 answers of 841 students it had never seen.

| Forecaster | AUC | Brier | Calibration error |
|---|---:|---:|---:|
| Skill average | 0.629 | 0.2107 | 0.011 |
| Student's running average | 0.706 | 0.1989 | 0.056 |
| BKT, 2 states, fitted | 0.680 | 0.1996 | 0.016 |
| Bagdar HMM, fitted, prior per skill | 0.709 | 0.1931 | 0.012 |

What this changes in the argument above:

- The claim "the forecast is calibrated" is no longer only a hypothesis for the knowledge model: on real students the calibration error is 0.012.
- The risk "a simple average may be as good" is partly real. A running average ranks answers almost as well (0.706 against 0.709). The model's measurable edge is calibration (0.012 against 0.056), which is exactly the property a public ledger depends on.
- Nothing here tests the teaching policy or the route. Nobody in these logs was taught by them, and the subject is not the AI course.

Reproduce with `python -m bagdar realdata`. Data: Feng, Heffernan and Koedinger (2009), *User Modeling and User-Adapted Interaction* 19(3), 243-266.

## Sources

- Models: https://link.springer.com/doi/10.1007/BF01099821 https://jedm.educationaldatamining.org/index.php/JEDM/article/view/451 https://aclanthology.org/P16-1174/
- Duolingo: https://www.sec.gov/Archives/edgar/data/0001562088/000162828026069474/q3fy26duolingo9-30x26share.htm https://blog.duolingo.com/improving-the-streak
- Khanmigo: https://thejournal.com/articles/2025/10/14/khan-academy-revamps-platform-for-school-districts.aspx https://www.aasa.org/resources/resource/a-conversation-with-sal-khan https://www.edtechinnovationhub.com/news/only-15-percent-of-students-with-access-to-khanmigo-actually-use-it-khan-academy-admits https://www.nber.org/papers/w35620 https://www.kqed.org/mindshift/66662/students-didnt-get-answers-from-khanmigo-they-didnt-want-its-questions-either
- Adaptive products: https://mathacademy.com/how-our-ai-works https://news.ycombinator.com/item?id=43241499 https://www.aleks.com/about_aleks/knowledge_space_theory https://docs.opendeved.net/lib/VRV8U8L2 https://www.weforum.org/organizations/squirrel-ai-learning/ https://www.carnegielearning.com/solutions/math/mathia/ https://github.com/open-spaced-repetition/fsrs4anki
- Knewton: https://www.insidehighered.com/blogs/just-visiting/knewton-gone-larger-threat-remains
- LLM tutors: https://techcrunch.com/2024/12/10/openai-backed-speak-raises-78m-at-1b-valuation-to-help-users-learn-languages-by-talking-out-loud https://techcrunch.com/2025/07/29/openai-launches-study-mode-in-chatgpt https://ideas.repec.org/a/nas/journl/v122y2025pe2422633122.html
- Readiness scores: https://nursing.uworld.com/blog/what-is-a-good-uworld-nclex-score-interpreting-your-uworld-nclex-score/ https://allnurses.com/uworld-predictor-amp-actual-nclex-t650421 https://achievable.me/exams/finra-series-7/faq/ https://support.amboss.com/hc/en-us/articles/25051050379921-USMLE-Score-Predictor-Score-Calculation-and-How-to-Interpret
- Motivation and trust: https://www.colorado.edu/business/faculty-research/2023/04/19/or-track-how-broken-streaks-affect-consumer-decisions https://pubmed.ncbi.nlm.nih.gov/10589297/ https://faculty.wharton.upenn.edu/wp-content/uploads/2016/11/20-Dietvorst-Simmons-Massey-2015.pdf https://www.businessofapps.com/?p=98187 https://getstream.io/blog/app-retention-guide
- Kazakhstan: https://www.gov.kz/memleket/entities/sci/press/news/details/1257149?lang=ru https://digitalbusiness.kz/2025-06-24/v-kazahstane-opredelili-luchshie-obrazovatelnie-kompanii-reyting/ https://apps.apple.com/us/app/id1102292074 https://informburo.kz/cards/kak-besplatno-podgotovitsia-k-ent-prilozeniia-servisy-i-obrazovatelnye-platformy https://www.gov.kz/memleket/entities/edu/press/news/details/299699?lang=ru https://astanatimes.com/2018/09/bagdar-offers-innovative-approach-for-career-path-employment-and-education/
