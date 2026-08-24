from eval_agent import run_eval, run_rag_eval

results = run_eval()
results.append(run_rag_eval())

passed = sum(1 for r in results if r["passed"])

print(f"\n{passed}/{len(results)} test cases passed\n")

for r in results:
    status = "PASS" if r["passed"] else "FAIL"
    print(f"[{status}] {r['question']}")
    if not r["passed"]:
        print(f"   expected_tool={r['expected_tool']}, called_tools={r.get('called_tools')}")
        print(f"   expected_keyword={r['expected_keyword']}, got={r.get('final_text')}")
        if r.get("judge_reason"):
            print(f"   judge_reason={r['judge_reason']}")
        if r.get("faithfulness_reason"):
            print(f"   faithfulness_reason={r['faithfulness_reason']}")