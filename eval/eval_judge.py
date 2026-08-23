# eval_judge.py
# A small "LLM-as-judge" using Google Gemini

import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

load_dotenv() 

from langchain_google_genai import ChatGoogleGenerativeAI


judge_llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    temperature=0,
    max_output_tokens=200,
)


def judge_answer(question: str, answer: str, criteria: str) -> dict:
    """
    Asks the LLM to grade whether `answer` satisfies `criteria` for the
    given `question`. Returns a dict with 'passed' (bool) and 'reason' (str).
    """
 
    prompt = f"""You are grading an AI agent's answer to a user's question.
 
Question: {question}
 
Agent's Answer:
{answer}
 
Grading Criteria:
{criteria}
 
Does the answer satisfy the criteria above? Reply in EXACTLY this format,
nothing else:
 
VERDICT: PASS
REASON: <one short sentence explaining why>
 
or
 
VERDICT: FAIL
REASON: <one short sentence explaining why>
"""
 
    response = judge_llm.invoke(prompt)

    if isinstance(response.content, list):
        # Gemini returns content as a list of blocks like [{'type': 'text', 'text': '...'}]
        text = "".join(
            block.get("text", "") for block in response.content if isinstance(block, dict)
        ).strip()
    else:
        text = str(response.content).strip()
 
    # Parse the verdict line. Default to FAIL if the format wasn't followed —
    # safer to flag it for a human to check than to silently mark it PASS.
    passed = False
    reason = text
 
    for line in text.splitlines():
        line_upper = line.strip().upper()
        if line_upper.startswith("VERDICT:"):
            passed = "PASS" in line_upper
        if line.strip().upper().startswith("REASON:"):
            reason = line.strip()[len("REASON:"):].strip()
 
    return {"passed": passed, "reason": reason}