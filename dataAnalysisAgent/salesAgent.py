import os
import json
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from openai import OpenAI
from dotenv import load_dotenv
from datetime import date, datetime
from guardrails import check_question, check_code, log_block

# ── SETUP ─────────────────────────────────────────
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
today = date.today().strftime("%B %d, %Y")

df = pd.read_csv("sales_data.csv", parse_dates=["Date"])
print(f"✅ Loaded dataset: {len(df)} rows, {len(df.columns)} columns")
print(f"📊 Columns: {list(df.columns)}\n")

# ── LOGGER ────────────────────────────────────────
class AuditLogger:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = time.time()
        self.current_log = None

    def start_question(self, question: str):
        self.current_log = {
            "session_id": self.session_id,
            "question": question,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "steps": [],
            "final_answer": None,
            "total_steps": 0,
            "total_time": None
        }
        self.question_start = time.time()

    def log_step(self, tool: str, code: str = None, filename: str = None, result: str = None, success: bool = True, time_taken: str = None):
        step = {
            "step": len(self.current_log["steps"]) + 1,
            "tool": tool,
            "success": success,
            "time_taken": time_taken
        }
        if code: step["code"] = code
        if filename: step["filename"] = filename
        if result: step["result"] = result[:200]
        self.current_log["steps"].append(step)

    def finish_question(self, final_answer: str):
        self.current_log["final_answer"] = final_answer
        self.current_log["total_steps"] = len(self.current_log["steps"])
        self.current_log["total_time"] = f"{time.time() - self.question_start:.2f}s"
        self._save_json()
        self._save_csv()
        self._save_txt()
        print(f"📋 Logs saved!")

    def _save_json(self):
        path = "logs/audit_log.json"
        logs = []
        if os.path.exists(path):
            with open(path, "r") as f:
                logs = json.load(f)
        logs.append(self.current_log)
        with open(path, "w") as f:
            json.dump(logs, f, indent=2)

    def _save_csv(self):
        path = "logs/audit_log.csv"
        rows = []
        for step in self.current_log["steps"]:
            rows.append({
                "session_id": self.current_log["session_id"],
                "timestamp": self.current_log["timestamp"],
                "question": self.current_log["question"],
                "step": step["step"],
                "tool": step["tool"],
                "success": step["success"],
                "time_taken": step["time_taken"],
                "code": step.get("code", ""),
                "filename": step.get("filename", ""),
                "result": step.get("result", "")
            })
        df_log = pd.DataFrame(rows)
        if os.path.exists(path):
            df_log.to_csv(path, mode="a", header=False, index=False)
        else:
            df_log.to_csv(path, index=False)

    def _save_txt(self):
        path = "logs/audit_log.txt"
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"SESSION:   {self.current_log['session_id']}\n")
            f.write(f"QUESTION:  {self.current_log['question']}\n")
            f.write(f"TIME:      {self.current_log['timestamp']}\n")
            f.write(f"{'-'*60}\n")
            for step in self.current_log["steps"]:
                status = "OK" if step["success"] else "FAILED"
                f.write(f"STEP {step['step']} | TOOL: {step['tool']} | {status} | {step['time_taken']}\n")
                if step.get("code"): f.write(f"CODE:   {step['code'][:150]}\n")
                if step.get("filename"): f.write(f"CHART:  {step['filename']}\n")
                if step.get("result"): f.write(f"RESULT: {step['result'][:150]}\n")
                f.write(f"{'-'*60}\n")
            f.write(f"FINAL ANSWER: {self.current_log['final_answer'][:200]}\n")
            f.write(f"TOTAL STEPS: {self.current_log['total_steps']} | TOTAL TIME: {self.current_log['total_time']}\n")
            f.write(f"{'='*60}\n")

logger = AuditLogger()

# ── TOOLS ─────────────────────────────────────────
tools = [
    {
        "type": "function",
        "function": {
            "name": "analyze_data",
            "description": "Run a pandas query or analysis on the sales data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python pandas code to run. The dataframe is called 'df'. 'pd' is also available. Always store result in a variable called 'result'."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart",
            "description": "Generate a chart or graph from the sales data and save it as a PNG file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python matplotlib/seaborn code. 'df', 'pd', 'plt', 'sns' are all available. ALWAYS recompute data from df from scratch. Always call plt.savefig(filename) and plt.close() at the end."
                    },
                    "description": {"type": "string", "description": "Short description of what this chart shows"},
                    "filename": {"type": "string", "description": "snake_case filename without extension e.g. 'sales_by_region'"}
                },
                "required": ["code", "description", "filename"]
            }
        }
    }
]

# ── TOOL FUNCTIONS ─────────────────────────────────
def analyze_data(code: str) -> str:
    start = time.time()
    try:
        code = code.replace(";", "\n")
        lines = code.strip().split("\n")
        last_line = lines[-1].strip()
        if not last_line.startswith("result") and "=" not in last_line:
            lines[-1] = f"result = {last_line}"
            code = "\n".join(lines)

        # ── DEBUG (commented out) ──
        # print(f"📝 Code being run:\n{code}\n")

        is_safe, reason = check_code(code)
        if not is_safe:
            log_block(reason, code=code)
            logger.log_step(tool="analyze_data", code=code, result=f"BLOCKED: {reason}", success=False, time_taken="0s")
            return f"🚫 Blocked: {reason}"

        local_vars = {"df": df.copy(), "pd": pd}
        exec(code, local_vars, local_vars)

        result = local_vars.get("result")
        if result is None:
            user_vars = {k: v for k, v in local_vars.items()
                        if k not in ["df", "pd"] and not k.startswith("__")}
            result = list(user_vars.values())[-1] if user_vars else "No result found."

        time_taken = f"{time.time() - start:.2f}s"
        logger.log_step(tool="analyze_data", code=code, result=str(result), success=True, time_taken=time_taken)
        return str(result)

    except Exception as e:
        time_taken = f"{time.time() - start:.2f}s"
        logger.log_step(tool="analyze_data", code=code, result=str(e), success=False, time_taken=time_taken)
        return f"Error running analysis: {str(e)}"


def generate_chart(code: str, description: str, filename: str) -> str:
    start = time.time()
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"charts/{filename}_{timestamp}.png"
        os.makedirs("charts", exist_ok=True)

        # ── DEBUG (commented out) ──
        # print(f"📝 Chart code being run:\n{code}\n")

        is_safe, reason = check_code(code)
        if not is_safe:
            log_block(reason, code=code)
            logger.log_step(tool="generate_chart", code=code, result=f"BLOCKED: {reason}", success=False, time_taken="0s")
            return f"🚫 Blocked: {reason}"

        local_vars = {"df": df.copy(), "pd": pd, "plt": plt, "sns": sns, "filename": safe_filename}
        exec(code, local_vars, local_vars)

        time_taken = f"{time.time() - start:.2f}s"
        logger.log_step(tool="generate_chart", code=code, filename=safe_filename, result=description, success=True, time_taken=time_taken)
        print(f"📊 Chart saved: {safe_filename}")
        return f"✅ Chart saved: {safe_filename} — {description}"

    except Exception as e:
        time_taken = f"{time.time() - start:.2f}s"
        logger.log_step(tool="generate_chart", code=code, result=str(e), success=False, time_taken=time_taken)
        return f"Error generating chart: {str(e)}"


# ── AGENT LOOP ─────────────────────────────────────
# memory_context is passed in from orchestrator
def run_agent(user_question: str, memory_context: str = "No previous context available."):
    print(f"\n🔍 Question: {user_question}")
    print("-" * 50)

    logger.start_question(user_question)

    is_safe, reason = check_question(user_question)
    if not is_safe:
        log_block(reason, question=user_question)
        logger.finish_question(f"BLOCKED: {reason}")
        return None

    messages = [
        {"role": "system", "content": f"""You are a data analysis agent. Today is {today}.
You have access to a sales dataset with these columns: {list(df.columns)}.
The Date column is already parsed as datetime.
The data spans from {df['Date'].min().date()} to {df['Date'].max().date()} with {len(df)} records.
Use analyze_data to answer questions and generate_chart to create visualizations.
IMPORTANT: In generate_chart code, always recompute data from scratch using df.
'pd', 'plt', 'sns', 'df' and 'filename' are always available in chart code.

--- PREVIOUS CONTEXT ---
{memory_context}
------------------------"""},
        {"role": "user", "content": user_question}
    ]

    max_iterations = 8
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            tools=tools,
            messages=messages
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                print(f"🛠️  Using tool: {fn_name}")

                if fn_name == "analyze_data":
                    result = analyze_data(args["code"])
                elif fn_name == "generate_chart":
                    result = generate_chart(args["code"], args["description"], args["filename"])
                else:
                    result = "Unknown tool."

                # ── DEBUG (commented out) ──
                # print(f"📄 Tool result: {result[:150]}...")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        else:
            final_answer = choice.message.content
            print(f"\n✅ Answer:\n{final_answer}")
            logger.finish_question(final_answer)
            return final_answer

    print("\n⚠️ Max iterations reached!")
    logger.finish_question("Max iterations reached — no final answer.")
    return None