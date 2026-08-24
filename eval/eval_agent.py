import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from uuid import uuid4
from backend.Agent_backend import send_message, ingest_pdf
from golden_dataset import GOLDEN_DATASET, RAG_TEST_CASE
from eval_judge import judge_answer, judge_faithfulness

def run_eval():
    results = []

    for case in GOLDEN_DATASET:
        thread_id = str(uuid4())  # fresh thread so tests don't interfere

        try:
            final_state = send_message(thread_id, case["question"])
        except Exception as e:
            results.append({**case, "passed": False, "error": str(e)})
            continue

        messages = final_state.get("messages", [])

        called_tools = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                called_tools += [call["name"] for call in msg.tool_calls]

        final_text = messages[-1].content if messages else ""

        tool_ok = case["expected_tool"] is None or case["expected_tool"] in called_tools
        keyword_ok = (
            case["expected_keyword"] is None
            or case["expected_keyword"].lower() in str(final_text).lower()
        )

        judge_reason = None
        if case.get("judge_criteria"):
            judge_result = judge_answer(
                question=case["question"],
                answer=str(final_text),
                criteria=case["judge_criteria"],
            )
            quality_ok = judge_result["passed"]
            judge_reason = judge_result["reason"]
        else:
            quality_ok = True

        results.append({
            **case,
            "called_tools": called_tools,
            "final_text": str(final_text)[:200],
            "judge_reason": judge_reason,
            "passed": tool_ok and keyword_ok and quality_ok,
        })

    return results

def run_rag_eval():
    thread_id = str(uuid4())

    with open(os.path.join(os.path.dirname(__file__), "sample.pdf"), "rb") as f:
        file_bytes = f.read()

    ingest_pdf(file_bytes=file_bytes, thread_id=thread_id, filename="sample.pdf")

    final_state = send_message(thread_id, RAG_TEST_CASE["question"])
    messages = final_state.get("messages", [])
    retrieved_context = ""
    for msg in messages:
        if getattr(msg, "name", None) == "rag_tool":
            retrieved_context = str(msg.content)
            break

    called_tools = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            called_tools += [call["name"] for call in msg.tool_calls]

    final_text = messages[-1].content if messages else ""

    tool_ok = RAG_TEST_CASE["expected_tool"] in called_tools

    judge_reason = None
    if RAG_TEST_CASE.get("judge_criteria"):
        judge_result = judge_answer(
            question=RAG_TEST_CASE["question"],
            answer=str(final_text),
            criteria=RAG_TEST_CASE["judge_criteria"],
        )
        quality_ok = judge_result["passed"]
        judge_reason = judge_result["reason"]
    else:
        quality_ok = True

    faithfulness_reason = None
    faithfulness_ok = True
    if retrieved_context:
        faithfulness_result = judge_faithfulness(str(final_text), retrieved_context)
        faithfulness_ok = faithfulness_result["passed"]
        faithfulness_reason = faithfulness_result["reason"]

    return {
        **RAG_TEST_CASE,
        "called_tools": called_tools,
        "final_text": str(final_text)[:200],
        "judge_reason": judge_reason,
        "faithfulness_reason": faithfulness_reason,
        "passed": tool_ok and quality_ok and faithfulness_ok,
    }

