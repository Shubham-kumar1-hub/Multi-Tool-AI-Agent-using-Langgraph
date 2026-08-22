GOLDEN_DATASET = [
    # --- Calculator ---
    {
        "question": "What's 12 multiplied by 4?",
        "expected_tool": "calculator",
        "expected_keyword": "48",
    },
    {
        "question": "What is 100 divided by 5?",
        "expected_tool": "calculator",
        "expected_keyword": "20",
    },
    {
        "question": "Add 250 and 375 for me.",
        "expected_tool": "calculator",
        "expected_keyword": "625",
    },

    # --- Stock price ---
    {
        "question": "What is the current stock price of AAPL?",
        "expected_tool": "get_stock_price",
        "expected_keyword": "AAPL",
    },
    {
        "question": "How much is TSLA trading at right now?",
        "expected_tool": "get_stock_price",
        "expected_keyword": "TSLA",
    },

    # --- Web search ---
    {
        "question": "Search the web for the latest news on OpenAI.",
        "expected_tool": "search_tool",
        "expected_keyword": None,
    },
    {
        "question": "What's happening in the stock market today?",
        "expected_tool": "search_tool",
        "expected_keyword": None,
    },

    # --- Purchase / Sell (HITL — expect the tool call, not a final answer,
    # since these pause on interrupt() before finishing) ---
    {
        "question": "Buy 10 shares of AAPL.",
        "expected_tool": "purchase_stock",
        "expected_keyword": None,
    },
    {
        "question": "Sell 5 shares of TSLA.",
        "expected_tool": "sell_stock",
        "expected_keyword": None,
    },

    # --- General knowledge, no tool expected ---
    {
        "question": "What is the capital of France?",
        "expected_tool": None,
        "expected_keyword": "Paris",
    },
    {
        "question": "Explain what a stock split is in one sentence.",
        "expected_tool": None,
        "expected_keyword": "split",
    },

    # --- Multi-step reasoning (tests if agent chains tools correctly) ---
    {
        "question": "What is AAPL's price multiplied by 2?",
        "expected_tool": "get_stock_price",
        "expected_keyword": None,
    },
]

RAG_TEST_CASE = {
    "question": "Summarize the document I uploaded.",
    "expected_tool": "rag_tool",
    "expected_keyword": None,
}