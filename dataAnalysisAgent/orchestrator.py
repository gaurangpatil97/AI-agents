import os
from dotenv import load_dotenv
from memoryAgent import get_memory_summary
from salesAgent import run_agent

load_dotenv()

def run_pipeline(user_question: str):
    print(f"\n{'='*60}")
    print(f"🎯 Orchestrator received: {user_question}")
    print(f"{'='*60}")

    # ── STEP 1: GET MEMORY CONTEXT ────────────────
    print("\n🧠 Memory Agent: fetching context...")
    memory_context = get_memory_summary(n=3)

    # ── STEP 2: RUN ANALYSIS AGENT ────────────────
    print("🤖 Analysis Agent: working on it...")
    answer = run_agent(user_question, memory_context=memory_context)

    return answer


# ── MAIN ENTRY POINT ──────────────────────────────
if __name__ == "__main__":
    print("\n🚀 Multi-Agent Data Analysis System")
    print("━"*60)
    print("Agents: Orchestrator → Memory Agent → Analysis Agent")
    print("━"*60)

    while True:
        question = input("\n💬 Ask about your sales data (or 'quit' to exit): ")
        if question.lower() == "quit":
            break
        run_pipeline(question)