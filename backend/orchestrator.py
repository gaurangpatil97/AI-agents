import os
import time
from dotenv import load_dotenv
from database import save_message, get_session_messages
from salesAgent import run_agent
from driveAgent import fetch_csv_from_drive, upload_chart_to_drive
from clarifierAgent import clarify_question, is_vague

load_dotenv()

def run_pipeline(user_question: str, callback=None, session_id: str = None):
    original_question = user_question

    def emit(msg: str):
        if callback:
            callback(msg)
        else:
            print(msg)
    
    emit(f"\n{'='*60}")
    emit(f"🎯 Orchestrator received: {user_question}")
    emit(f"{'='*60}")

    # ── STEP 1: GET MEMORY CONTEXT ────────────────
    emit("\n🧠 Memory: fetching last Q&A for this session...")
    # Get memory context from DB instead of audit log
    session_messages = get_session_messages(session_id) if session_id else []
    if session_messages:
        last = session_messages[-1]
        memory_context = f"Previous Q: {last['question']}\nPrevious A: {last['answer']}"
    else:
        memory_context = "No previous context available."

    # ── STEP 2: NON-LINEAR ROUTING ────────────────
    if is_vague(user_question):
        emit("🔀 Clarifier Agent: question is vague, clarifying...")
        final_question = clarify_question(user_question, memory_context, callback=callback)
    else:
        emit("✅ Question is clear, skipping clarifier")
        final_question = user_question

    # ── STEP 3: COUNT CHARTS BEFORE RUNNING ───────
    charts_dir = "charts"
    os.makedirs(charts_dir, exist_ok=True)
    charts_before = set(os.listdir(charts_dir))
    chart_path = None

    # ── STEP 4: RUN ANALYSIS AGENT ────────────────
    emit("🤖 Analysis Agent: working on it...")
    answer = run_agent(final_question, memory_context=memory_context, callback=callback)

    # ── STEP 5: UPLOAD ONLY NEW CHARTS ────────────
    if answer:
        charts_after = set(os.listdir(charts_dir))
        new_charts = charts_after - charts_before  # only brand new files
        if new_charts:
            latest = os.path.join(charts_dir, list(new_charts)[0])
            chart_path = latest
            emit(f"\n☁️  Drive Agent: uploading {list(new_charts)[0]} to Drive...")
            link = upload_chart_to_drive(latest)
            emit(f"🔗 Chart link: {link}")

        if session_id:
            save_message(
                session_id=session_id,
                question=original_question,
                answer=answer,
                chart_path=chart_path if chart_path else None,
            )

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