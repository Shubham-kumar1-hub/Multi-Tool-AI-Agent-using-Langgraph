GOLDEN_DATASET = [
 
    # ---------------------------------------------------------
    # CALCULATOR — happy path
    # ---------------------------------------------------------
    {
        "question": "What's 12 multiplied by 4?",
        "expected_tool": "calculator",
        "expected_keyword": "48",
        "judge_criteria": None,
    },
    {
        "question": "What is 100 divided by 5?",
        "expected_tool": "calculator",
        "expected_keyword": "20",
        "judge_criteria": None,
    },
    {
        "question": "Add 250 and 375 for me.",
        "expected_tool": "calculator",
        "expected_keyword": "625",
        "judge_criteria": None,
    },
 
    # ---------------------------------------------------------
    # CALCULATOR — edge cases
    # ---------------------------------------------------------
    {
        "question": "What is 10 divided by 0?",
        "expected_tool": None,
        "expected_keyword": "zero",
        "judge_criteria": None,
        # The agent should explain division by zero isn't possible, not crash or hallucinate a number.
    },
    {
        "question": "What is 7 xor 3?",
        "expected_tool": None,
        "expected_keyword": None,
        "judge_criteria": "The agent should explain it cannot perform an XOR operation, since the calculator tool only supports add/subtract/multiply/divide. It should not attempt to guess an answer or silently fail.",
        # Tests behavior when asked for something outside the tool's supported operations.
    },
 
    # ---------------------------------------------------------
    # STOCK PRICE — happy path
    # ---------------------------------------------------------
    {
        "question": "What is the current stock price of AAPL?",
        "expected_tool": "get_stock_price",
        "expected_keyword": "AAPL",
        "judge_criteria": None,
    },
    {
        "question": "How much is TSLA trading at right now?",
        "expected_tool": "get_stock_price",
        "expected_keyword": "TSLA",
        "judge_criteria": None,
    },
 
    # ---------------------------------------------------------
    # STOCK PRICE — edge cases
    # ---------------------------------------------------------
    {
        "question": "What is the stock price of ZZZZFAKE?",
        "expected_tool": "get_stock_price",
        "expected_keyword": None,
        "judge_criteria": "The agent should clearly state it could not find data for this symbol, rather than inventing a fake price.",
        # Tests handling of an invalid/non-existent ticker symbol.
    },
    {
        "question": "Can you tell me the price of 3 stocks?",
        "expected_tool": None,
        "expected_keyword": None,
        "judge_criteria": "The agent should ask the user which three stock symbols they mean, since none were specified, rather than guessing or picking random stocks.",
        # Tests handling of an ambiguous request missing required information.
    },
 
    # ---------------------------------------------------------
    # WEB SEARCH — happy path
    # ---------------------------------------------------------
    {
        "question": "Search the web for the latest news on OpenAI.",
        "expected_tool": "search_tool",
        "expected_keyword": None,
        "judge_criteria": None,
    },
    {
        "question": "What's happening in the stock market today?",
        "expected_tool": "search_tool",
        "expected_keyword": None,
        "judge_criteria": None,
    },
 
    # ---------------------------------------------------------
    # WEB SEARCH — edge case
    # ---------------------------------------------------------
    {
        "question": "asdkjaslkdj alksjd??",
        "expected_tool": None,
        "expected_keyword": None,
        "judge_criteria": "The agent should recognize this input is gibberish/unclear and ask the user to rephrase or clarify what they meant, rather than guessing at an interpretation.",
        # Tests handling of nonsensical/garbled input.
    },
 
    # ---------------------------------------------------------
    # BUY / SELL (HITL) — happy path
    # ---------------------------------------------------------
    {
        "question": "Buy 10 shares of AAPL.",
        "expected_tool": "purchase_stock",
        "expected_keyword": None,
        "judge_criteria": None,
    },
    {
        "question": "Sell 5 shares of TSLA.",
        "expected_tool": "sell_stock",
        "expected_keyword": None,
        "judge_criteria": None,
    },
 
    # ---------------------------------------------------------
    # BUY / SELL — edge cases
    # ---------------------------------------------------------
    {
        "question": "Buy some AAPL shares.",
        "expected_tool": None,
        "expected_keyword": None,
        "judge_criteria": "The agent should ask the user how many shares they want to buy, since no quantity was given, instead of guessing a number or calling purchase_stock with a made-up quantity.",
        # Tests ambiguous input missing a required parameter (quantity).
    },
    {
        "question": "Buy 999999 shares of AAPL.",
        "expected_tool": "purchase_stock",
        "expected_keyword": "reject",
        "judge_criteria": None,
    },
    {
        "question": "Buy 10 shares of ZZZZFAKE123.",
        "expected_tool": "purchase_stock",
        "expected_keyword": None,
        "judge_criteria": "The agent should reject this trade because the symbol format is invalid, and explain why, rather than proceeding to ask for approval.",
        # Tests the symbol-format guardrail fires correctly.
    },
 
    # ---------------------------------------------------------
    # GENERAL KNOWLEDGE — happy path
    # ---------------------------------------------------------
    {
        "question": "What is the capital of France?",
        "expected_tool": None,
        "expected_keyword": "Paris",
        "judge_criteria": None,
    },
    {
        "question": "Explain what a stock split is in one sentence.",
        "expected_tool": None,
        "expected_keyword": "split",
        "judge_criteria": None,
    },
 
    # ---------------------------------------------------------
    # GENERAL KNOWLEDGE — edge case (open-ended, needs judging not keywords)
    # ---------------------------------------------------------
    {
        "question": "Explain the difference between REST and GraphQL APIs.",
        "expected_tool": None,
        "expected_keyword": None,
        "judge_criteria": "The answer should correctly explain that REST uses multiple fixed endpoints while GraphQL uses a single flexible endpoint where clients specify exactly what data they need. It should be accurate and not contain factual errors about either technology.",
    },
    {
        "question": "Can you tell me some things about Cristiano Ronaldo",
        "expected_tool": None,
        "expected_keyword": "Ronaldo",
        "judge_criteria": "The answer should be factually accurate and reasonably concise, not an overly long essay, consistent with the agent's instruction to keep answers concise unless asked for more detail.",
    },
 
    # ---------------------------------------------------------
    # MULTI-STEP / MULTI-TOOL — tests tool selection under compound requests
    # ---------------------------------------------------------
    {
        "question": "What is AAPL's price multiplied by 2?",
        "expected_tool": "get_stock_price",
        "expected_keyword": None,
        "judge_criteria": None,
    },
    {
        "question": "Get me AAPL's stock price and also search for the latest Tesla news.",
        "expected_tool": "get_stock_price",
        "expected_keyword": None,
        "judge_criteria": "The answer should include both a real AAPL stock price and some real, specific Tesla news — not a generic or vague statement, and not skipping either part of the request.",
        # Tests whether the agent handles a genuinely compound request covering two different tools.
    },
 
    # ---------------------------------------------------------
    # RAG (PDF) — see eval_agent.py's run_rag_eval() for the primary case;
    # this one is a follow-up asking about content the PDF does NOT contain.
    # ---------------------------------------------------------
    {
    "question": "Does the uploaded document mention anything about machine learning?",
    "expected_tool": None,
    "expected_keyword": None,
    "judge_criteria": "Since no PDF has been uploaded in this fresh thread, the agent should clearly say it cannot check because no document was uploaded, rather than fabricating an answer or claiming a document exists.",
    },
]

RAG_TEST_CASE = {
    "question": "Summarize the document I uploaded.",
    "expected_tool": "rag_tool",
    "expected_keyword": None,
    "judge_criteria": "The summary should accurately reflect real content from the uploaded PDF, not generic or fabricated information, and should not claim there is no document when one was actually uploaded.",
}