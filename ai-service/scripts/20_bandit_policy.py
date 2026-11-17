"""Learn the retrieval-mode policy from rewards: a contextual bandit (RL).

The rule-based agent hard-codes which retrieval mode to use (rules R5-R7).
Here the same decision is learned: each question is a context, each retrieval
mode an arm, and the reward of an arm is what the benchmark measured when that
mode answered the question:

    reward = passed (1/0) - LATENCY_COST * latency_seconds

Context features come from the agent's own perception (question shape, KB
entity present, article number). Learning uses UCB1 per context with replay of
the logged rewards; the policy is evaluated with leave-one-out so a question is
never scored by a policy that has seen its reward.

  docker compose exec ai-service python scripts/20_bandit_policy.py

Needs data/eval/results/{flat,graph,hybrid}_rag_generic.json (15_run_eval.py).
With 26 questions this shows the mechanism, not a statistically strong result.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent.perception import perceive  # noqa: E402

RESULTS = ROOT / "data/eval/results"
ARMS = ("flat_rag", "graph_rag", "hybrid_rag")
LATENCY_COST = 0.02  # reward lost per second of latency
EPISODES = 200
SEED = 7


def load_rewards() -> Tuple[Dict[str, Dict[str, float]], Dict[str, str]]:
    rewards: Dict[str, Dict[str, float]] = defaultdict(dict)
    questions: Dict[str, str] = {}
    for arm in ARMS:
        data = json.loads((RESULTS / f"{arm}_generic.json").read_text(encoding="utf-8"))
        for item in data["questions"]:
            reward = float(item["is_passed"]) - LATENCY_COST * item["latency_ms"] / 1000
            rewards[item["question_id"]][arm] = reward
            questions[item["question_id"]] = item["question"]
    return rewards, questions


def context(question: str) -> str:
    obs = perceive(question)
    return f"{obs.shape}|entity={int(obs.has_semantic_entity)}|article={int(bool(obs.article))}"


def train_ucb(qids: List[str], rewards, contexts, episodes: int = EPISODES, seed: int = SEED):
    """UCB1 per context, replaying logged rewards in random order."""
    rng = random.Random(seed)
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for _ in range(episodes):
        qid = rng.choice(qids)
        ctx = contexts[qid]
        tried = counts[ctx]
        untried = [arm for arm in ARMS if tried[arm] == 0]
        if untried:
            arm = untried[0]
        else:
            n = sum(tried.values())
            arm = max(ARMS, key=lambda a: totals[ctx][a] / tried[a] + math.sqrt(2 * math.log(n) / tried[a]))
        counts[ctx][arm] += 1
        totals[ctx][arm] += rewards[qid][arm]
    policy = {
        ctx: max(ARMS, key=lambda a: totals[ctx][a] / counts[ctx][a] if counts[ctx][a] else -1e9)
        for ctx in counts
    }
    return policy, counts, totals


def main() -> int:
    rewards, questions = load_rewards()
    qids = sorted(rewards)
    contexts = {qid: context(questions[qid]) for qid in qids}

    # Leave-one-out: the held-out question's reward is never used to choose its arm.
    chosen: Dict[str, str] = {}
    for held_out in qids:
        policy, _, _ = train_ucb([q for q in qids if q != held_out], rewards, contexts)
        chosen[held_out] = policy.get(contexts[held_out], "hybrid_rag")

    def score(pick) -> Dict[str, float]:
        values = [rewards[q][pick(q)] for q in qids]
        return {"mean_reward": round(sum(values) / len(qids), 4)}

    summary = {
        "always_flat_rag": score(lambda q: "flat_rag"),
        "always_graph_rag": score(lambda q: "graph_rag"),
        "always_hybrid_rag": score(lambda q: "hybrid_rag"),
        "bandit_leave_one_out": score(lambda q: chosen[q]),
        "oracle_best_arm": {"mean_reward": round(sum(max(rewards[q].values()) for q in qids) / len(qids), 4)},
    }
    agent_file = RESULTS / "agent_generic.json"
    if agent_file.exists():
        agent = json.loads(agent_file.read_text(encoding="utf-8"))
        summary["rule_based_agent"] = {
            "mean_reward": round(
                sum(float(i["is_passed"]) - LATENCY_COST * i["latency_ms"] / 1000 for i in agent["questions"])
                / len(agent["questions"]),
                4,
            )
        }

    final_policy, counts, totals = train_ucb(qids, rewards, contexts)
    learned = {
        ctx: {
            "arm": arm,
            "pulls": dict(counts[ctx]),
            "mean_reward": {a: round(totals[ctx][a] / counts[ctx][a], 3) for a in ARMS if counts[ctx][a]},
            "questions": sum(1 for q in qids if contexts[q] == ctx),
        }
        for ctx, arm in sorted(final_policy.items())
    }
    out = {
        "reward": f"passed - {LATENCY_COST} * latency_s",
        "episodes": EPISODES,
        "summary": summary,
        "learned_policy": learned,
        "per_question": {q: {"context": contexts[q], "chosen": chosen[q], "rewards": rewards[q]} for q in qids},
    }
    (RESULTS / "bandit_policy.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("| Chính sách | Phần thưởng TB |")
    print("|---|---:|")
    for name, values in summary.items():
        print(f"| {name} | {values['mean_reward']} |")
    print("\nChính sách học được (ngữ cảnh -> nhánh):")
    for ctx, values in learned.items():
        print(f"  {ctx:38s} -> {values['arm']:10s} n={values['questions']} {values['mean_reward']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
