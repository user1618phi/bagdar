# Defense notes

Format: 2 minutes problem and objectives, 3 to 5 minutes live demo, 2 minutes on the three AI topics, up to 3 minutes of questions. Speak slowly: the scripts below are about 260 words each, which is 2 minutes at a calm pace.

## Before you start

1. Same laptop as in rehearsal, charger in, notifications off, browser zoom 110%.
2. Terminal: `python -m bagdar` and leave it running. The page opens by itself.
3. On the start screen press "erase progress" twice, so the demo starts from zero.
4. Keep `docs/media/bagdar-demo.mp4` open in a second window. If anything breaks, do not debug for more than 45 seconds: say "let me show the recording of the same session" and play it.
5. Keep a second terminal ready with `python -m bagdar demo` typed, in case you are asked for console output.

## Part 1. Problem and objectives (2 minutes)

> When a student prepares for an exam, two things are usually missing. The first is position: what do I really know? A score of seven out of ten does not tell me, because some of those seven were guesses and some of the three were slips. The second is direction: out of twenty topics, which one should I study now, and should I read or practise?
>
> Chat assistants do not solve this. In a randomised study published in PNAS in 2025, students who practised with unrestricted ChatGPT scored 17 percent lower on the later exam without it. Khan Academy reports that about 15 percent of students who have its AI tutor use it regularly. The missing piece is not more chat. It is knowing what the learner knows and what to do next.
>
> My project, Bagdar, treats studying as navigation. Bağdar is the Kazakh word for direction. A GPS does three things: it finds where you are from noisy signals, it plans the cheapest route, and it tells you the next manoeuvre. Bagdar does the same three things with three algorithms from this course: a hidden Markov model, A-star search, and a Markov decision process.
>
> My objectives were measurable. First, estimate knowledge as a probability and check that the estimate is honest. Second, always return the cheapest route and prove it against brute force. Third, choose each step by expected value and beat simple rules. Fourth, show every number, so that the decisions can be checked by hand.

## Part 2. Live demo (about 4 minutes)

| Step | Do | Say |
|---|---|---|
| 1 | Start screen. "Defense day" is selected. Press **Plan my route**. | "I choose a destination: the three algorithms of this project. A-star has planned 13 stops, about 67 minutes. The chance to pass today is 5 percent, because the model knows nothing about me yet." |
| 2 | Point at the right column. | "This is the belief of the hidden Markov model for the first skill: unknown 0.50, fragile 0.30, mastered 0.20. That is the prior." |
| 3 | Pick a **wrong** option, press **Not sure**. | "I answer wrong and I say I am not sure. The belief is updated: Bayes' rule takes unknown from 0.50 to 0.79, and since answering also teaches, it ends at 0.71. And I get the explanation, not just right or wrong." |
| 4 | Press **Continue**. A lesson appears. | "Now the decision process compares the options. A lesson is worth 3.77, a question 3.64, moving on minus 10.69. So it teaches first." |
| 5 | Press **Got it, test me**, answer correctly with **I'm sure**, twice. | "Correct and sure is strong evidence. After two such answers, P of mastered passes 0.885 and the tutor moves on. That threshold is not chosen by hand. It follows from the costs." |
| 6 | Answer two more skills correctly (keys 1 to 4, then S, then Enter). | "A learner who already knows a skill passes it in two questions. The marker, the time left and the pass chance update each time." |
| 7 | Open **map**. Click "perceptron" (bottom right), press **Study this now**. | "This is the prerequisite map. Fill is the probability of mastery, numbers are the A-star order, dashed lines are helpful but optional prerequisites. I can take a detour, and the tutor tells me what it costs: here, 7 minutes." Then press "back to the planned route". |
| 8 | Open **engine**, tab **hmm**. | "Nothing is hidden. Here is the forward algorithm step by step, and the Viterbi path." |
| 9 | Tab **mdp**. | "Value iteration converged in 47 sweeps. The policy: unknown, lesson. Fragile, question. Mastered, move on." |
| 10 | Tab **a\***, press **Compare**. | "The same problem with four algorithms. A-star and uniform-cost search always find the same cost, and A-star expands far fewer states. Greedy and breadth-first carry no guarantee: on the full course they almost never find the optimum." |
| 11 | Tab **evidence**. | "And the evidence. On real students from the ASSISTments data the fitted model forecasts unseen answers with AUC 0.709 and stays calibrated. Below are simulations, including learners who break my assumptions, where the tutor gets worse, and I show that too." |

## Part 3. The three AI topics (2 minutes)

> The first topic is probabilistic reasoning over time: a hidden Markov model. The hidden state of each skill is unknown, fragile or mastered. The observation is the answer together with the confidence, so there are four symbols. After every answer I apply the forward algorithm: multiply the belief by the likelihood of the observation, normalise, which is Bayes' rule, and then apply the transition, because answering also teaches. Viterbi gives the single most likely history. I chose an HMM because answers are noisy: a guess is right 25 percent of the time, and a master still slips.
>
> The second topic is sequential decision making: a Markov decision process. Three states, three actions: lesson, question, move on. Rewards are minutes: a lesson costs two, a question one, and moving on pays plus ten if the skill is mastered and minus fifteen if it is unknown. Value iteration applies the Bellman update until the values stop changing. Since the true state is hidden, I act on the belief: Q of belief and action is the belief-weighted sum of the optimal Q values. This is called QMDP.
>
> The third topic is search: A-star. A state is the set of completed skills. An action is studying one more skill whose prerequisites are done. The cost is the expected minutes, which come from the belief and from the policy. The heuristic is the time of the required skills still missing. It never overestimates, so the first complete route is the cheapest.
>
> They form one chain: the belief feeds the decision and the route costs, and the route tells the decision process which skill to act on.

## Questions you should expect

**Why an HMM and not just the percentage of correct answers?** A percentage treats a guess and a slip as knowledge and ignorance. The HMM models both, uses the order of answers, and gives a calibrated probability. On real students the fitted HMM had calibration error 0.012 against 0.056 for a running average.

**What exactly is one HMM update?** Two lines. Condition: `b(x) = alpha * P(e | x) * b(x)`. Predict: `b(x') = sum over x of b(x) * P(x' | x, action)`. The observation is emitted by the state before learning, so conditioning comes first. This is the same order as Bayesian Knowledge Tracing.

**Filtering versus Viterbi?** Filtering gives the distribution of the current state given all evidence so far, using sums. Viterbi gives the single most likely sequence of states, using max instead of sum and back-pointers. Both cost `O(T * S^2)`.

**Why three states and not two?** Two states (knows or does not) is classical knowledge tracing. The middle state, fragile, separates "can answer sometimes" from "mastered", and it is what makes the choice between a lesson and a question meaningful. A three-state version was published by Zhang and Yao in 2018.

**Where do the probabilities come from?** They are stated assumptions, which the guidelines allow: guess is one in four for four options. I then checked them against real data: Baum-Welch fitted on 3,322 real students gave P(correct) of 0.27, 0.64 and 0.81 per state, against my assumed 0.25, 0.65 and 0.92. The first two match; real students slip more than I assumed.

**What is Baum-Welch?** Expectation-maximisation for HMMs. The E-step runs forward-backward to get the posterior of every state and transition. The M-step re-estimates the parameters from those expected counts. The likelihood never decreases, and I test that.

**Write the Bellman equation.** `V(s) = max over a of [ R(s,a) + gamma * sum over s' of P(s'|s,a) * V(s') ]`. Value iteration repeats this update. With gamma below one it is a contraction, so it converges to a unique solution. Mine stops after 47 sweeps when the largest change is below `1e-10`.

**Why gamma 0.95?** It guarantees convergence and expresses a mild preference for finishing sooner. Rewards are in minutes, so most of the pressure to be quick comes from the step costs.

**What is QMDP and what is its weakness?** Solve the MDP as if the state were visible, then weight the Q values by the belief. It assumes the uncertainty disappears after one step, so it never takes an action only to gain information. I measured a repair, one step of expectimax over the possible answers: payoff 2.10 against 1.97. I kept QMDP in the product because it is explainable in one line.

**Why does the tutor move on at 0.885 and not at 0.95?** 0.95 is a convention from the 1995 knowledge-tracing paper. Here the threshold is derived: it is where the expected value of moving on equals the expected value of one more question, given the costs I set.

**Define admissible and consistent. Is your heuristic both?** Admissible: never overestimates the true remaining cost. Consistent: `h(n) <= c(n, a, n') + h(n')`. My heuristic is the sum of base minutes of the required skills not yet completed. Every one of them must still be studied and penalties only add time, so it never overestimates. Completing a skill lowers `h` by at most its base cost, which is at most the step cost paid, so it is consistent. The tests check both on every reachable state of random graphs.

**Is this not just a topological sort?** It would be if all prerequisites were mandatory and costs were fixed. Soft prerequisites change that: skipping one makes the next skill 40 percent slower, so there is a real choice between studying the helpful topic first and paying the penalty. The best choice depends on the belief, so it changes as you learn.

**Why A-star and not uniform-cost search or BFS?** UCS is optimal but blind: on the full course it expands about 4,154 states where A-star expands 33, for the same cost. BFS minimises the number of skills, not the time, and greedy follows the heuristic only; on the full course both return worse routes (BFS in every run, greedy in 99.5 percent).

**How do you know the implementation is correct?** 81 tests. Textbook values for the umbrella world, 0.818 and 0.883. Viterbi and the routes against brute-force enumeration. MDP values against the closed form. Baum-Welch recovering known parameters. Fuzzed full sessions that must terminate with valid state.

**How do you know it helps real students?** I do not, and I say so. What I have: the knowledge model forecasts real students' answers better than six alternatives; the policy beats simple rules in simulation, including on learners built on a different theory. What I do not have: a study where real students were taught by it. That is the next step.

**What happens when the model is wrong?** I tested it. With different parameters the tutor still has the best payoff among the simple rules, but true mastery at the moment it moves on falls from 91 to 72 percent. So the parameters must be fitted on real answers before any claim.

**Why no neural network or LLM?** The task is to show course algorithms working together, and for this problem small, explainable models are an advantage: every number can be checked by hand, it runs offline with no dependencies, and there is nothing to hallucinate. An LLM could later write questions; it should not decide what the learner knows.

**What is original here?** Not the algorithms: they are classical. The integration is: belief to action values and to edge costs, policy to minutes, route back to the policy. And the honesty: the forecast ledger and the experiments on learners who break the model.

**Which environment properties does your agent face?** Partially observable (knowledge is hidden), stochastic, sequential, discrete, single-agent. That is why it needs a belief state.

**What would you do with one more month?** Fit the teaching parameters from our own logs with the Baum-Welch code that is already written, add forgetting and spaced review, and run a pilot with classmates that publishes predicted against actual.

## Numbers to remember

| | |
|---|---|
| Content | 20 skills, 80 questions, 20 lessons, 5 destinations |
| Prior | unknown 0.50, fragile 0.30, mastered 0.20 |
| P(correct) per state | 0.25, 0.65, 0.92 |
| After "wrong, not sure" | belief [0.71, 0.20, 0.09] |
| Optimal values | V = [3.03, 6.51, 10.00], 47 sweeps, gamma 0.95 |
| Policy | unknown: lesson, fragile: question, mastered: move on |
| Move-on threshold | P(mastered) >= 0.885 (when P(unknown) is 0) |
| Route, Defense day from zero | 13 skills, 66.9 minutes |
| A-star against UCS, full course | 33 against 4,154 states expanded, same cost |
| Real students | 3,322 to fit, 841 held out, 52,840 answers; AUC 0.709; calibration error 0.012 |
| Simulation | 6.48 minutes and 90.9% mastered, against 8.07 minutes and 92.4% for three in a row |
| Tests | 81 |

## Шпаргалка по-русски

**Идея одной фразой.** Bagdar — навигатор для учёбы: HMM определяет, где ты находишься (что знаешь), A\* строит кратчайший маршрут до цели, MDP говорит, что делать прямо сейчас.

**HMM (скрытая марковская модель).** У каждого навыка есть скрытое состояние: не знает, шатко, освоил. Мы его не видим, видим только ответ и уверенность. После каждого ответа два действия: умножаем убеждение на правдоподобие ответа и нормируем (это формула Байеса), затем применяем переход, потому что сам ответ тоже учит. Угадывание (25% при четырёх вариантах) и случайная ошибка заложены в таблицу эмиссий, поэтому один ответ не переворачивает оценку. Витерби даёт самую вероятную историю состояний: вместо суммы берётся максимум.

**MDP (марковский процесс принятия решений).** Три состояния, три действия: урок, вопрос, идти дальше. Награды в минутах: урок стоит 2, вопрос 1, «идти дальше» даёт +10, если навык освоен, −5, если шатко, и −15, если не знает. Value iteration повторяет уравнение Беллмана, пока значения не перестанут меняться (47 проходов). Истинное состояние скрыто, поэтому решение принимается по убеждению: Q(b, a) = сумма b(s)·Q(s, a). Это называется QMDP. Слабость: он не ценит информацию ради информации.

**A\*.** Состояние — множество пройденных навыков. Действие — изучить ещё один навык, у которого выполнены обязательные пререквизиты. Стоимость — ожидаемые минуты, они берутся из убеждения HMM и политики MDP. Эвристика — сумма времени обязательных навыков, которые ещё не пройдены. Она не завышает (допустима) и согласована, поэтому первый найденный маршрут оптимален. «Мягкие» пререквизиты делают задачу настоящим поиском: можно пропустить полезную тему, но следующая станет на 40% дольше.

**Как они связаны.** Ответ → убеждение HMM → оно задаёт и ценность действий в MDP, и стоимость рёбер в A\* → маршрут говорит MDP, с каким навыком работать.

**Что говорить честно.** Алгоритмы не новые. Реальных учеников этой системой ещё не учили. На реальных данных проверена только модель знаний. При неверных параметрах система чаще уходит с навыка слишком рано. Именно эта честность и есть отличие от конкурентов.
