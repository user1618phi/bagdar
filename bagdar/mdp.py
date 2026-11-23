"""Markov decision processes: value iteration, policy evaluation and the QMDP rule.

Course topic: sequential decision making (MDPs, week 5).
Notation follows Russell & Norvig, AIMA ch. 17, and Sutton & Barto ch. 4.

    Q(s, a) = R(s, a) + gamma * sum_s' P(s' | s, a) * V(s')      (non-terminal action)
    Q(s, a) = R(s, a)                                            (terminal action: episode ends)
    V(s)    = max_a Q(s, a)                                      (Bellman optimality equation)

Value iteration applies the Bellman update to every state until the largest change (the
Bellman residual) drops below `theta`. For gamma < 1 the update is a contraction, so it
converges to the unique optimal value function from any starting point.
"""

from __future__ import annotations

from dataclasses import dataclass

Vector = list[float]
Matrix = list[list[float]]


@dataclass(frozen=True)
class MDP:
    states: tuple[str, ...]
    actions: tuple[str, ...]
    transitions: dict[str, Matrix]  # transitions[a][s][s'] = P(s' | s, a)
    rewards: dict[str, Vector]  # rewards[a][s] = immediate reward of doing a in s
    terminal_actions: frozenset[str]  # actions that end the episode
    gamma: float

    def validate(self) -> None:
        if not 0.0 <= self.gamma < 1.0:
            raise ValueError("gamma must be in [0, 1) for value iteration to be a contraction")
        for action in self.actions:
            if len(self.rewards[action]) != len(self.states):
                raise ValueError(f"reward vector of '{action}' has the wrong length")
            if action in self.terminal_actions:
                continue
            for row in self.transitions[action]:
                if len(row) != len(self.states) or abs(sum(row) - 1.0) > 1e-9 or min(row) < 0.0:
                    raise ValueError(f"transition rows of '{action}' must be distributions")


@dataclass(frozen=True)
class ValueIterationResult:
    values: Vector  # V*(s)
    q: dict[str, Vector]  # q[a][s] = Q*(s, a)
    policy: list[str]  # greedy action per state
    iterations: int
    history: list[tuple[Vector, float]]  # (V after sweep k, Bellman residual of sweep k)


def q_value(mdp: MDP, values: Vector, state: int, action: str) -> float:
    """Expected return of taking `action` in `state` and following `values` afterwards."""
    reward = mdp.rewards[action][state]
    if action in mdp.terminal_actions:
        return reward
    row = mdp.transitions[action][state]
    return reward + mdp.gamma * sum(row[nxt] * values[nxt] for nxt in range(len(mdp.states)))


def bellman_update(mdp: MDP, values: Vector) -> Vector:
    """One synchronous sweep: V_{k+1}(s) = max_a Q_k(s, a) for every state."""
    return [max(q_value(mdp, values, s, a) for a in mdp.actions) for s in range(len(mdp.states))]


def value_iteration(mdp: MDP, theta: float = 1e-10, max_iterations: int = 10_000) -> ValueIterationResult:
    """Solve the MDP. Stops when max_s |V_{k+1}(s) - V_k(s)| < theta."""
    mdp.validate()
    values = [0.0] * len(mdp.states)
    history: list[tuple[Vector, float]] = []
    for _ in range(max_iterations):
        updated = bellman_update(mdp, values)
        residual = max(abs(updated[s] - values[s]) for s in range(len(values)))
        values = updated
        history.append((list(values), residual))
        if residual < theta:
            break
    q = {a: [q_value(mdp, values, s, a) for s in range(len(mdp.states))] for a in mdp.actions}
    policy = [greedy_action({a: q[a][s] for a in mdp.actions}) for s in range(len(mdp.states))]
    return ValueIterationResult(values, q, policy, len(history), history)


def greedy_action(action_values: dict[str, float]) -> str:
    """Argmax with a deterministic tie-break (first action in insertion order wins)."""
    return max(action_values, key=lambda a: (action_values[a], -list(action_values).index(a)))


def expected_cost_to_finish(mdp: MDP, policy: list[str], cost: dict[str, float], tolerance: float = 1e-12) -> Vector:
    """Policy evaluation of an undiscounted cost: how much is spent before the episode ends.

    Solves  c(s) = cost[pi(s)] + sum_s' P(s' | s, pi(s)) * c(s')  with c = cost of the terminal
    action when pi(s) ends the episode. Used to turn the optimal policy into expected minutes.
    The policy must be proper (it reaches a terminal action with probability 1).
    """
    size = len(mdp.states)
    result = [0.0] * size
    for _ in range(100_000):
        updated = []
        for s in range(size):
            action = policy[s]
            if action in mdp.terminal_actions:
                updated.append(cost[action])
            else:
                row = mdp.transitions[action][s]
                updated.append(cost[action] + sum(row[n] * result[n] for n in range(size)))
        change = max(abs(updated[s] - result[s]) for s in range(size))
        result = updated
        if change < tolerance:
            return result
    raise ValueError("policy evaluation did not converge: the policy never terminates")


def qmdp_values(q: dict[str, Vector], belief: Vector) -> dict[str, float]:
    """QMDP (Littman, Cassandra & Kaelbling, 1995): act on a belief with Q-values of the MDP.

        Q(b, a) = sum_s b(s) * Q*(s, a)

    The true state is hidden, so the exact problem is a POMDP. QMDP is the standard cheap
    approximation: it assumes the uncertainty disappears after one step, so it never takes an
    action purely to gain information. Here that is acceptable because asking a question both
    teaches and reveals the state.
    """
    return {a: sum(belief[s] * q[a][s] for s in range(len(belief))) for a in q}
