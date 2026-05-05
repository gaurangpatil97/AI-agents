import os
import time
from dotenv import load_dotenv
from memoryAgent import get_memory_summary
from salesAgent import run_agent
from driveAgent import fetch_csv_from_drive, upload_chart_to_drive
from clarifierAgent import clarify_question, is_vague

load_dotenv()

def run_pipeline(user_question: str):
    print(f"\n{'='*60}")
    print(f"🎯 Orchestrator received: {user_question}")
    print(f"{'='*60}")

    # ── STEP 1: GET MEMORY CONTEXT ────────────────
    print("\n🧠 Memory Agent: fetching context...")
    memory_context = get_memory_summary(n=3)

    # ── STEP 2: NON-LINEAR ROUTING ────────────────
    if is_vague(user_question):
        print("🔀 Clarifier Agent: question is vague, clarifying...")
        final_question = clarify_question(user_question, memory_context)
    else:
        print("✅ Question is clear, skipping clarifier")
        final_question = user_question

    # ── STEP 3: COUNT CHARTS BEFORE RUNNING ───────
    charts_dir = "charts"
    os.makedirs(charts_dir, exist_ok=True)
    charts_before = set(os.listdir(charts_dir))

    # ── STEP 4: RUN ANALYSIS AGENT ────────────────
    print("🤖 Analysis Agent: working on it...")
    answer = run_agent(final_question, memory_context=memory_context)

    # ── STEP 5: UPLOAD ONLY NEW CHARTS ────────────
    if answer:
        charts_after = set(os.listdir(charts_dir))
        new_charts = charts_after - charts_before  # only brand new files
        if new_charts:
            latest = os.path.join(charts_dir, list(new_charts)[0])
            print(f"\n☁️  Drive Agent: uploading {list(new_charts)[0]} to Drive...")
            link = upload_chart_to_drive(latest)
            print(f"🔗 Chart link: {link}")

    return answer


# ── MAIN ENTRY POINT ──────────────────────────────
if __name__ == "__main__":
    print("\n🚀 Multi-Agent Data Analysis System")
    print("━"*60)
    print("Agents: Orchestrator → Memory → Clarifier → Analysis → Drive")
    print("━"*60)

    # ── FETCH DATASET FROM DRIVE ──────────────────
    print("\n☁️  Fetching dataset from Google Drive...")
    local_path = fetch_csv_from_drive("sales_data.csv")
    if local_path.endswith(".csv"):
        print(f"✅ Dataset ready: {local_path}")
    else:
        print("⚠️  Using local dataset instead")

    while True:
        question = input("\n💬 Ask about your sales data (or 'quit' to exit): ")
        if question.lower() == "quit":
            break
        run_pipeline(question)