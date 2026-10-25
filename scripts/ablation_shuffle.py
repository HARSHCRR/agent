#!/usr/bin/env python3
"""
Ablation Study: Quantifying LLM Judge Positional Bias & Presentation Order Sensitivity.

Evaluates N briefing packs across two presentation orders:
  Order A: Case X = Bull, Case Y = Bear
  Order B: Case X = Bear, Case Y = Bull (Swapped)

Measures and prints the empirical Verdict-Flip Rate:
  flip_rate = (number of times verdict_A != verdict_B) / N * 100
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collector import build_pack
from analysts import run_dual_analysts, MockLLMClient
from judge import evaluate_cases_blind, MockJudgeLLMClient
from models import BriefingPack

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("AblationShuffle")


def run_ablation(n: int, replay_pack_path: str = None) -> None:
    logger.info(f"Starting Shuffler Ablation Study (Sample Size N = {n})...")

    # Load base pack
    if replay_pack_path and Path(replay_pack_path).exists():
        with open(replay_pack_path, "r") as f:
            base_pack = BriefingPack.model_validate_json(f.read())
        logger.info(f"Loaded canned pack from {replay_pack_path}")
        llm_client = MockLLMClient()
        judge_client = MockJudgeLLMClient()
    else:
        base_pack = build_pack()
        llm_client = None
        judge_client = None

    flips = 0
    identical = 0
    records = []

    for i in range(1, n + 1):
        # Generate Bull and Bear cases
        bull_case, bear_case = run_dual_analysts(base_pack, client=llm_client)
        b_dict = bull_case.model_dump()
        r_dict = bear_case.model_dump()
        b_dict.pop("side", None)
        r_dict.pop("side", None)

        # 1. Order A: Case X = Bull, Case Y = Bear
        res_a = evaluate_cases_blind(base_pack, b_dict, r_dict, client=judge_client)
        verdict_a = res_a.verdict

        # 2. Order B (Swapped): Case X = Bear, Case Y = Bull
        res_b = evaluate_cases_blind(base_pack, r_dict, b_dict, client=judge_client)
        verdict_b = res_b.verdict

        is_flip = verdict_a != verdict_b
        if is_flip:
            flips += 1
        else:
            identical += 1

        records.append({
            "iteration": i,
            "order_a_verdict": verdict_a,
            "order_b_verdict": verdict_b,
            "flipped": is_flip
        })

    flip_rate = (flips / n) * 100.0

    print("\n" + "=" * 55)
    print("          ABLATION STUDY: POSITION BIAS REPORT          ")
    print("=" * 55)
    print(f"Total Evaluations (N):            {n}")
    print(f"Identical Verdicts Across Swap:    {identical}")
    print(f"Verdict Flips (Order Sensitive):   {flips}")
    print(f"Measured Verdict-Flip Rate:        {flip_rate:.1f}%")
    print("-" * 55)
    if flip_rate > 0.0:
        print(f"INTERPRETATION: In {flip_rate:.1f}% of cases, simply swapping Case X")
        print("and Case Y altered the judge verdict, demonstrating measurable")
        print("positional bias and justifying the random shuffler middleware.")
    else:
        print("INTERPRETATION: Zero verdict flips observed across the evaluated sample.")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run position-bias ablation study")
    parser.add_argument("--n", type=int, default=10, help="Number of evaluations to run")
    parser.add_argument("--replay", type=str, default="tests/data/sample_pack.json", help="Path to canned briefing pack")
    args = parser.parse_args()

    run_ablation(n=args.n, replay_pack_path=args.replay)
