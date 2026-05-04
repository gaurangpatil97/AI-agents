# # FUNCTIONALITIES 
# 1. Read audit_log.json
# 2. Grab last 3 entries
# 3. Extract question + final_answer from each
# 4. Send to GPT with instruction to summarize
# 5. Return the summary string

import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_memory_summary(n: int = 3) -> str:
    """
    Reads last n Q&A pairs from audit log
    and returns a GPT generated summary
    """
    log_path = "logs/audit_log.json"

    # no logs yet — return empty
    if not os.path.exists(log_path):
        return "No previous context available."

    with open(log_path, "r") as f:
        logs = json.load(f)

    # nothing in logs yet
    if not logs:
        return "No previous context available."

    # grab last n entries
    recent = logs[-n:]

    # extract Q&A pairs
    qa_pairs = []
    for entry in recent:
        q = entry.get("question", "")
        a = entry.get("final_answer", "")
        if q and a:
            qa_pairs.append(f"Q: {q}\nA: {a[:200]}")

    if not qa_pairs:
        return "No previous context available."

    # format for GPT
    qa_text = "\n\n".join(qa_pairs)

    # one GPT call to summarize
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=150,
        messages=[
            {
                "role": "system",
                "content": "You are a memory summarizer. Summarize the following Q&A pairs into 2-3 sentences of key findings. Be concise and factual. Focus on numbers and insights found."
            },
            {
                "role": "user",
                "content": f"Summarize these recent findings:\n\n{qa_text}"
            }
        ]
    )

    summary = response.choices[0].message.content
    print(f"🧠 Memory context: {summary}\n")
    return summary
    