import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from eval_judge import judge_answer

result = judge_answer(
    question="What is the capital of France?",
    answer="The capital of France is Paris.",
    criteria="The answer should correctly state that Paris is the capital of France."
)
print(result)

result2 = judge_answer(
    question="What is the capital of France?",
    answer="The capital of France is Berlin.",
    criteria="The answer should correctly state that Paris is the capital of France."
)
print(result2)