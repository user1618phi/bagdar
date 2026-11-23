# Design decisions and their reasons

Values are quoted from `web/kit.css`, `web/app.css`, `web/index.html` and `web/js`. "Secondary" means the research notes confirmed a finding only through a secondary source.

## Principles

1. One decision per screen.
2. Empty space is the main material.
3. No cards or shadows. Structure comes from lines and the ruler.
4. One accent colour, used at most three times per screen.
5. State is never shown by colour alone.
6. Motion only on transform and opacity, with reduced-motion respected.

## Decision table

| Element | Decision | Reason | Evidence |
|---|---|---|---|
| Accent colour | Purple, hue 305: `--acc: oklch(58% 0.233 305)`. Accent text `oklch(56% 0.233 305)` light, `oklch(78% 0.112 305)` dark. Primary button: accent with white text | Chosen by the owner's design-core colour tool, so the product is distinct from the blue of the campus LMS and other education products. Contrast measured with the tool: 5.02:1 accent text on light, 4.83:1 white on the button, 9.47:1 accent text on dark | [WCAG 2.2](https://www.w3.org/TR/WCAG22/) 1.4.3 asks 4.5:1; design-core rule |
| Neutral bases | Background `oklch(98.5% 0.004 305)` light, `oklch(15% 0.004 305)` dark. Text `oklch(21% 0.008 305)` and `oklch(94% 0.004 305)` | Near-white and near-black leave the accent as the only colour with meaning | design-core rule |
| Headings | Source Serif 4, weight 300, tracking -0.022em, line height 1.04; `h1` is `clamp(40px, 6.4vw, 88px)` | Large and light, never bold. The core allows one heading font per product | design-core rule |
| Text | Medeo Sans, body 16px, line height 1.55; question prompt `clamp(20px, 2vw, 24px)` | The question is the largest text of a step | design-core rule |
| Labels | Medeo Mono, 12.5px, lowercase, muted colour (`.label`) | One quiet voice for labels, numbers and statuses | design-core rule |
| Numbers | `font-variant-numeric: tabular-nums` on `.num` and numeric table cells | Digits change after each answer and must not shift | design-core rule |
| Radii | 18px panels, 13px buttons and fields, 10px small parts | An inner part gets the smaller radius | design-core rule |
| Spacing | 4px base: 4, 8, 12, 16, 24, 32, 48, 64, 96 | One grid for every gap | design-core rule |
| Route scale | 34px ruler with 1px ticks: 7px pending, 13px for done and current stops, all neutral; "stop N of M" | Progress is distance covered and distance left | Goal gradient: [Kivetz, Urminsky & Zheng 2006](https://business.columbia.edu/sites/default/files-efs/pubfiles/1200/goalgradient.pdf), secondary. A loyalty-card experiment; analogy only |
| "Here" marker | 9px accent square placed at (completed stops + P(mastered) of the current skill) / all stops; it glides to each new position with a transform over 900ms | It moves only when the belief moves, so the progress is real | Endowed progress: [Nunes & Drèze 2006](https://msbfile03.usc.edu/digitalmeasures/jnunes/intellcont/Endowed%20Progress%20Effect-1.pdf), secondary; a marketing study |
| ETA and pass chance | "≈ N min left" and "N% chance to pass if the exam were today"; hover text gives the pass mark | A number, not a word. "Today" marks it as a snapshot. No range or frequency is shown yet | Probability words are read as closer to 50%: [Budescu et al. 2014](https://ideas.repec.org/a/nat/natcli/v4y2014i6d10.1038_nclimate2194.html), secondary |
| Attempt first | The explanation appears only after an answer. A lesson ends with "Got it, test me" | Retrieval beats re-reading after a delay | [Roediger & Karpicke 2006](https://psychology.ecu.edu/wp-content/pv-uploads/sites/216/2019/03/Roediger-Karpicke-2006.pdf): 61% against 40% after one week. Free recall, not multiple choice |
| Four options | All 80 questions have four options, keyed a to d | Fits working memory and fixes the guess rate at 0.25 | About four chunks: [Cowan 2001](https://pubmed.ncbi.nlm.nih.gov/11515286/), secondary |
| Options as rows | Full-width rows with a 1px line above, 52px minimum height, no fill | No cards; a large target | design-core rule; [WCAG 2.2 target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), 24px minimum |
| "I'm sure" / "Not sure" | The two submit buttons, disabled until an option is chosen | Confidence is captured with zero extra clicks, before the answer is visible | [Butler, Karpicke & Roediger 2008](https://pcllab.github.io/downloads/2008/2008_Butler_Karpicke_Roediger_JEPLMC.pdf), secondary; [Koriat & Bjork 2005](https://cris.haifa.ac.il/en/publications/illusions-of-competence-in-monitoring-ones-knowledge-during-study/), secondary |
| Primary button | One `.btn.primary` per screen: "Plan my route", "I'm sure", "Continue", "Got it, test me" | One obvious next action | design-core rule. The notes call it a heuristic, not a proven law |
| Feedback wording | "Correct." or "Not yet." in the feedback headline (the engine tables label an answer "wrong") | Speaks about the task, not the person, and keeps the stakes low | [Hattie & Timperley 2007](https://www.uky.edu/~gmswan3/575/Hattie_Timperly_2007.pdf), secondary; test anxiety: [von der Embse et al. 2018](https://pubmed.ncbi.nlm.nih.gov/29156362/), secondary |
| Explanation | The reason is shown after every answer, right or wrong, with both options marked | Right/wrong alone teaches almost nothing | Effects 0.49 for explanation, 0.32 for the correct answer, 0.05 for right/wrong: [Van der Kleij, Feskens & Eggen 2015](https://ris.utwente.nl/ws/files/6806219/effects.pdf), secondary |
| Confident error note | "You were sure of this one. Confident errors are the ones that stick best once corrected..." Another note follows an unsure correct answer | Confidence decides which feedback is shown | Hypercorrection, Butterfield & Metcalfe 2001, via a [later review](https://pmc.ncbi.nlm.nih.gov/articles/PMC3079415), secondary |
| No streaks, points or badges | None in the code. The recurring numbers are stops, minutes and pass chance | The hook is the learner's own goal | Rewards lower intrinsic motivation: [Deci, Koestner & Ryan 1999](https://pubmed.ncbi.nlm.nih.gov/10589297/), secondary; broken streaks: [Silverman & Barasch 2023](https://www.colorado.edu/business/faculty-research/2023/04/19/or-track-how-broken-streaks-affect-consumer-decisions), secondary |
| Learner control | "show me the lesson first" on a question; "Study this now" on the map; then "Your detour adds N min" and "back to the planned route" | A small override with its price shown | [Dietvorst, Simmons & Massey 2018](https://marketing.wharton.upenn.edu/wp-content/uploads/2020/07/Dietvorst-Overcoming-Algorithm-Aversion.pdf), secondary; forecasting tasks, transfer to studying untested |
| Belief | Three labelled 3px bars (unknown, fragile, mastered), each with a two-decimal value, plus "Estimated from N steps" | The model is shown as an estimate with its evidence | [Long & Aleven 2017](https://link.springer.com/doi/10.1007/s11257-016-9186-6), secondary; mixed overall: [Robles Mucho et al. 2026](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1760183/full) |
| Action values | Bars for lesson, question and move on, with their values. The chosen one has a 7px neutral square and a one-sentence reason | The learner sees why this step was picked | No study found on explaining route choices; design-core rule for the mark |
| Confidence record | For example "when sure 4/5", "when not 1/3", shown after three answers | Calibration as counts, not as a score to maximise | Natural frequencies: [review](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.01186/pdf), secondary |
| Status marks | `.mark`: an 8px square plus a lowercase word, such as "correct answer" or "your answer" | State never by colour alone | WCAG 2.2 1.4.1; red-green deficiency in about 8% of men of European origin: [Birch 2012](https://pubmed.ncbi.nlm.nih.gov/22472762/) |
| Map | 18px square nodes; fill height is P(mastered); solid edge required, dashed edge optional; route order "01" beside each stop | Shape, fill, line style and numbers carry the state | WCAG 2.2 1.4.1; open-model evidence is mixed (see Belief) |
| Navigation | Three 92px links in an 18px-radius panel with `blur(16px) saturate(1.5)`. From 900px wide it sits in the top bar and scrolls with the page; on a phone it floats at the bottom. Hidden on the start screen | On a wide screen nothing may cover content, so the panel is part of the header; on a phone the thumb reaches the bottom edge. Blur only on floating panels | design-core rule; overlap found in the end-to-end check and in the owner's review of the demo video |
| Segmented control | Four 96px tabs; the indicator slides by `translateX` in 560ms on the spring curve, as in the dock | The selection travels instead of blinking | design-core rule |
| Engine tables | Forward-algorithm trace, Q values, value-iteration sweeps, A* expansions, experiments and the forecast ledger, as right-aligned monospace numbers | Every decision shows its numbers | People leave an algorithm after seeing it err: [Dietvorst, Simmons & Massey 2015](https://faculty.wharton.upenn.edu/wp-content/uploads/2016/11/20-Dietvorst-Simmons-Massey-2015.pdf), secondary. Shown errors are a risk |
| Press | `scale(.93)` in 110ms; return in 560ms with `cubic-bezier(.34,1.56,.64,1)` | What is pressed springs back | design-core rule |
| Entrance | 900ms, 22px shift plus opacity, staggered 70ms. Played only when a screen or step is new. Off under `prefers-reduced-motion` | Choosing an option does not replay the motion | design-core rule; WCAG 2.2 2.3.3 |
| Keyboard | 1-4 choose, s sure, n not sure, named in a hint line; "Continue" takes focus after an answer | A whole question cycle without the mouse | WCAG 2.2 |
| Focus | `:focus-visible`: 2px outline in the text colour, 2px offset; map nodes get a 2px stroke; a skip link | The keyboard position is always visible | WCAG 2.2 |
| ARIA roles | `radiogroup` for destinations and options; `status` for the verdict and the toast; `tablist` in the engine; `alert` on errors | Assistive technology gets the same structure | WCAG 2.2 |
| Phone layout | At 900px the columns stack and the "why" panel moves under the step. At 520px buttons stretch and the top label hides. The map scrolls sideways | A study tool without a mobile version draws complaints | User complaints on [Hacker News](https://news.ycombinator.com/item?id=43241499); not a study |
| Dark theme | Follows `prefers-color-scheme` unless the "theme" toggle sets `data-theme`, which is saved | Both themes are equal | design-core rule |
| Error state | A line in `--bad`, the mark "engine unreachable", the message, "Nothing is lost: your answers are kept in this browser." and "Try again" | The error says what is safe and what to do | design-core rule |
| Data | Kept in `localStorage` only (key `meje.v1`); every access is guarded. The local engine keeps no session state. "erase progress" needs two presses | Learner data stays on the device and the app runs without internet | No study; product decision |

## What the evidence does NOT support

- The 85% rule is derived for neural networks trained by gradient descent, not for students ([Wilson et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6831579/)). Meje sets no such target.
- Confidence marking alone is not proven to improve learning. The one direct study used a different answer format ([Sparck, Bjork & Bjork 2016](https://link.springer.com/article/10.1186/s41235-016-0003-x), secondary).
- Streaks raise retention in one company's product, not learning ([Duolingo blog](https://blog.duolingo.com/improving-the-streak), secondary).
- An open learner model is not proven to improve learning. The 2026 synthesis gives no pooled effect.
- No study was found on how showing a personal pass probability affects students. This is a product risk and needs user testing.

## Checklist result

- The design-core audit of the code scores 100 of 100 with no violations.
- Both themes and phone width were checked in a real browser.
- Accent count was checked by hand, because the audit does not count it. The question screen uses the accent three times: the "here" marker, the selected option and the primary button. The brand square, the ticks, the route numbers on the map and the chosen-action mark are neutral.
- The feel of motion cannot be judged from code. It needs the owner's eyes.
