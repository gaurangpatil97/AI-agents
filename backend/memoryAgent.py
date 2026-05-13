# # FUNCTIONALITIES 
# 1. Read audit_log.json
# 2. Grab last 1 entry
# 3. Extract question + final_answer
# 4. Return raw Q&A as formatted string

import json
import os

def get_memory_summary(callback=None) -> str:
    """
    Reads last Q&A pair from audit log
    and returns it as a formatted string
    """
    def emit(msg: str):
        if callback:
            callback(msg)
        else:
            print(msg)
    
    log_path = "logs/audit_log.json"

    # no logs yet — return empty
    if not os.path.exists(log_path):
        return "No previous context available."

    with open(log_path, "r") as f:
        logs = json.load(f)

    # nothing in logs yet
    if not logs:
        return "No previous context available."

    # grab last 1 entry
    last_entry = logs[-1]

    # extract Q&A
    question = last_entry.get("question", "")
    answer = last_entry.get("final_answer", "")

    if not question or not answer:
        return "No previous context available."

    # return formatted string
    memory_str = f"Previous Q: {question}\nPrevious A: {answer}"
    emit(f"🧠 Memory context: {memory_str}\n")
    return memory_str
    