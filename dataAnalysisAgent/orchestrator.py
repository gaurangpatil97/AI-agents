import os
import time
from dotenv import load_dotenv
from memoryAgent import get_memory_summary
from salesAgent import run_agent
from driveAgent import fetch_csv_from_drive, upload_chart_to_drive

load_dotenv()

def run_pipeline(user_question: str):
    print(f"\n{'='*60}")
    print(f"🎯 Orchestrator received: {user_question}")
    print(f"{'='*60}")

    # ── STEP 1: GET MEMORY CONTEXT ────────────────
    print("\n🧠 Memory Agent: fetching context...")
    memory_context = get_memory_summary(n=3)

    # ── STEP 2: RECORD TIME BEFORE RUNNING ────────
    time_before = time.time()

    # ── STEP 3: RUN ANALYSIS AGENT ────────────────
    print("🤖 Analysis Agent: working on it...")
    answer = run_agent(user_question, memory_context=memory_context)

    # ── STEP 4: ONLY UPLOAD IF NEW CHART GENERATED ─
    if answer:
        charts_dir = "charts"
        if os.path.exists(charts_dir):
            new_charts = [
                f for f in os.listdir(charts_dir)
                if f.endswith(".png") and
                os.path.getmtime(os.path.join(charts_dir, f)) > time_before
            ]
            if new_charts:
                latest = os.path.join(charts_dir, new_charts[0])
                print(f"\n☁️  Drive Agent: uploading {new_charts[0]} to Drive...")
                link = upload_chart_to_drive(latest)
                print(f"🔗 Chart link: {link}")

    return answer


# ── MAIN ENTRY POINT ──────────────────────────────
if __name__ == "__main__":
    print("\n🚀 Multi-Agent Data Analysis System")
    print("━"*60)
    print("Agents: Orchestrator → Memory Agent → Analysis Agent → Drive Agent")
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