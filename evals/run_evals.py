"""
LLM-as-Judge Eval Harness
Runs the agent swarm against a set of queries and scores responses
using Claude as the judge. Produces a JSON report.
"""

import json
import os
import time
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

import anthropic
from langchain_core.messages import HumanMessage
from app.graph.build_graph import build_graph


JUDGE_PROMPT = """You are evaluating a customer support AI agent for InfinitePay, a Brazilian fintech.

Query: {query}
Expected agent: {expected_agent}
Actual agent used: {actual_agent}
Agent response: {response}
Expected topics to cover: {expected_topics}

Score this response on three dimensions (1-5 each):

1. ROUTING (1-5): Was the right agent used?
   - 5: Correct agent used
   - 1: Wrong agent used

2. ACCURACY (1-5): Is the response factually correct and helpful?
   - 5: Fully accurate, directly answers the question
   - 3: Partially correct or missing key details
   - 1: Incorrect or unhelpful

3. COVERAGE (1-5): Does the response cover the expected topics?
   - 5: Covers all expected topics
   - 3: Covers some expected topics
   - 1: Misses most expected topics

Respond with ONLY a JSON object in this exact format:
{{"routing": N, "accuracy": N, "coverage": N, "comment": "one sentence explanation"}}
"""


def judge_response(
    query: str,
    expected_agent: str,
    actual_agent: str,
    response: str,
    expected_topics: list,
) -> dict:
    """Use Claude to score an agent response."""
    client = anthropic.Anthropic()

    prompt = JUDGE_PROMPT.format(
        query=query,
        expected_agent=expected_agent,
        actual_agent=actual_agent,
        response=response[:1000],
        expected_topics=", ".join(expected_topics),
    )

    msg = client.messages.create(
        model=os.getenv("ROUTER_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        scores = json.loads(raw.strip())
        return scores
    except json.JSONDecodeError:
        return {"routing": 0, "accuracy": 0, "coverage": 0, "comment": "parse error"}


def run_evals():
    """Run all eval queries and produce a report."""
    print("═" * 60)
    print("InfinitePay Agent Swarm — Eval Harness")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 60)

    # Load queries
    queries_path = os.path.join(os.path.dirname(__file__), "queries.json")
    with open(queries_path) as f:
        queries = json.load(f)

    graph = build_graph()
    results = []
    total_scores = {"routing": 0, "accuracy": 0, "coverage": 0}

    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] {query['id']}: {query['message'][:50]}...")

        # Run the agent
        try:
            config = {"configurable": {"thread_id": f"eval-{query['id']}"}}
            result = graph.invoke(
                {
                    "messages": [HumanMessage(content=query["message"])],
                    "user_id": query["user_id"],
                    "agent_used": "",
                    "final_response": "",
                    "escalate": False,
                },
                config=config,
            )
            actual_agent = result.get("agent_used", "unknown")
            response = result.get("final_response", "")

        except Exception as e:
            actual_agent = "error"
            response = str(e)

        # Judge the response
        scores = judge_response(
            query=query["message"],
            expected_agent=query["expected_agent"],
            actual_agent=actual_agent,
            response=response,
            expected_topics=query["expected_topics"],
        )

        # Calculate overall score
        overall = round(
            (scores.get("routing", 0) + scores.get("accuracy", 0) + scores.get("coverage", 0)) / 3,
            1
        )

        routing_ok = "✓" if actual_agent == query["expected_agent"] else "✗"
        print(f"  Agent: {actual_agent} (expected: {query['expected_agent']}) {routing_ok}")
        print(f"  Scores → routing: {scores.get('routing')}/5  accuracy: {scores.get('accuracy')}/5  coverage: {scores.get('coverage')}/5  overall: {overall}/5")
        print(f"  Comment: {scores.get('comment', '')}")

        # Accumulate
        for key in total_scores:
            total_scores[key] += scores.get(key, 0)

        results.append({
            "id": query["id"],
            "message": query["message"],
            "user_id": query["user_id"],
            "expected_agent": query["expected_agent"],
            "actual_agent": actual_agent,
            "routing_correct": actual_agent == query["expected_agent"],
            "scores": scores,
            "overall": overall,
            "response_preview": response[:200],
        })

        time.sleep(1)  # Avoid rate limits

    # Summary
    n = len(queries)
    routing_accuracy = sum(1 for r in results if r["routing_correct"]) / n * 100
    avg_scores = {k: round(v / n, 2) for k, v in total_scores.items()}
    avg_overall = round(sum(r["overall"] for r in results) / n, 2)

    print(f"\n{'═' * 60}")
    print("EVAL SUMMARY")
    print(f"{'═' * 60}")
    print(f"Total queries:     {n}")
    print(f"Routing accuracy:  {routing_accuracy:.0f}%")
    print(f"Avg routing:       {avg_scores['routing']}/5")
    print(f"Avg accuracy:      {avg_scores['accuracy']}/5")
    print(f"Avg coverage:      {avg_scores['coverage']}/5")
    print(f"Avg overall:       {avg_overall}/5")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_queries": n,
            "routing_accuracy_pct": routing_accuracy,
            "avg_routing": avg_scores["routing"],
            "avg_accuracy": avg_scores["accuracy"],
            "avg_coverage": avg_scores["coverage"],
            "avg_overall": avg_overall,
        },
        "results": results,
    }

    report_path = os.path.join(os.path.dirname(__file__), "eval_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Report saved to evals/eval_report.json")
    print("═" * 60)

    return report


if __name__ == "__main__":
    run_evals()