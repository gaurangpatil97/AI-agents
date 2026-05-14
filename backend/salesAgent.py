import os
import json
import time
import re
import pandas as pd
import matplotlib
matplotlib.use('Agg')
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

# ── DYNAMIC DATASET LOADER ────────────────────────
def load_dataset(filename: str):
    global df
    df = pd.read_csv(filename, parse_dates=["Date"] if "Date" in pd.read_csv(filename, nrows=1).columns else [])
    print(f"✅ Loaded dataset: {filename} — {len(df)} rows")
    return list(df.columns)

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
        print(f"\n📋 Logs saved!")

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
                        "description": "Python code to generate a chart. Follow this exact pattern:\n1. Compute data from df (always reset_index())\n2. fig, ax = plt.subplots(figsize=(10, 6))\n3. Plot using ax methods (ax.bar, ax.plot, ax.pie)\n4. ax.set_title(), ax.set_xlabel(), ax.set_ylabel()\n5. plt.tight_layout()\n6. plt.savefig(filename, dpi=100, bbox_inches='tight')\n7. plt.close()\nAvailable: df, pd, plt, sns, filename"
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
        if not last_line.startswith("result") and not re.search(r'^\s*\w+\s*=', last_line):
            lines[-1] = f"result = {last_line}"
            code = "\n".join(lines)

        is_safe, reason = check_code(code)
        if not is_safe:
            log_block(reason, code=code)
            logger.log_step(tool="analyze_data", code=code, result=f"BLOCKED: {reason}", success=False, time_taken="0s")
            return f"🚫 Blocked: {reason}"

        local_vars = {"df": df.copy(), "pd": pd, "np": __import__('numpy')}
        exec(code, local_vars, local_vars)

        result = local_vars.get("result", None)
        if result is None or (hasattr(result, 'empty') and result.empty):
            result = "No result found."
        elif hasattr(result, 'to_string'):
            result = result.to_string()
        else:
            result = str(result)

        time_taken = f"{time.time() - start:.2f}s"
        logger.log_step(tool="analyze_data", code=code, result=str(result), success=True, time_taken=time_taken)
        return str(result)

    except Exception as e:
        time_taken = f"{time.time() - start:.2f}s"
        logger.log_step(tool="analyze_data", code=code, result=str(e), success=False, time_taken=time_taken)
        return f"Error running analysis: {str(e)}"


def generate_chart(code: str, description: str, filename: str, callback=None) -> str:
    start = time.time()
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"charts/{filename}_{timestamp}.png"
        os.makedirs("charts", exist_ok=True)

        is_safe, reason = check_code(code)
        if not is_safe:
            log_block(reason, code=code)
            logger.log_step(tool="generate_chart", code=code, result=f"BLOCKED: {reason}", success=False, time_taken="0s")
            return f"🚫 Blocked: {reason}"

        local_vars = {"df": df.copy(), "pd": pd, "plt": plt, "sns": sns, "filename": safe_filename}
        exec(code, local_vars, local_vars)

        # ── VERIFY OUTPUT FILE EXISTS ─────────────────────────────────────────────
        if os.path.exists(safe_filename):
            print(f"✅ Verified chart exists: {safe_filename}")
        else:
            import glob
            import shutil

            new_pngs = glob.glob("*.png")
            if new_pngs:
                dest = f"charts/{new_pngs[0]}"
                shutil.move(new_pngs[0], dest)
                safe_filename = dest
                print(f"✅ Moved chart to: {safe_filename}")
            else:
                return f"Error: Chart file was not created"

        time_taken = f"{time.time() - start:.2f}s"
        logger.log_step(tool="generate_chart", code=code, filename=safe_filename, result=description, success=True, time_taken=time_taken)
        chart_msg = f"📊 Chart saved: {safe_filename}"
        if callback:
            callback(chart_msg)
        print(chart_msg)
        return f"✅ Chart saved: {safe_filename}"

    except Exception as e:
        time_taken = f"{time.time() - start:.2f}s"
        logger.log_step(tool="generate_chart", code=code, result=str(e), success=False, time_taken=time_taken)
        print(f"Chart generation error: {str(e)}")
        return f"Error generating chart: {str(e)}"


# ── STREAMING AGENT LOOP ───────────────────────────
def run_agent(user_question: str, memory_context: str = "No previous context available.", callback=None):
    def emit(msg: str):
        if callback:
            callback(msg)
        else:
            print(msg)
    
    emit(f"\n🔍 Question: {user_question}")
    emit("-" * 50)

    logger.start_question(user_question)

    is_safe, reason = check_question(user_question)
    if not is_safe:
        log_block(reason, question=user_question)
        logger.finish_question(f"BLOCKED: {reason}")
        return None

    date_col = 'Date' if 'Date' in df.columns else 'Last_Purchase_Date' if 'Last_Purchase_Date' in df.columns else None
    date_range_str = f"The data spans from {df[date_col].min()} to {df[date_col].max()}." if date_col else "No date column available."

    messages = [
        {"role": "system", "content": f"""You are a data analysis agent. Today is {today}.
You have access to a sales dataset with these columns: {list(df.columns)}.
The Date column is already parsed as datetime.
{date_range_str} Total records: {len(df)}.
Use analyze_data to answer questions and generate_chart to create visualizations.

=== CHART GENERATION PATTERN (ALWAYS FOLLOW) ===
When generating charts, use this exact pattern:

Step 1: Compute the data fresh from df:
   data = df.groupby('Column')['Value'].mean().reset_index()

Step 2: Create the plot:
   fig, ax = plt.subplots(figsize=(10, 6))

Step 3: Plot the data using ax:
   ax.bar(data['Column'], data['Value'])

Step 4: Add labels:
   ax.set_xlabel('...')
   ax.set_ylabel('...')
   ax.set_title('...')

Step 5: Save and close - ALWAYS use filename variable:
   plt.tight_layout()
   plt.savefig(filename, dpi=100, bbox_inches='tight')
   plt.close()

RULES:
- NEVER use seaborn for complex charts
- NEVER reference variables from previous tool calls
- ALWAYS use plt.subplots() instead of plt.figure()
- ALWAYS call plt.close() at the end
- ALWAYS use the filename variable for saving
- Import nothing - pd, plt, sns, df are already available

--- PREVIOUS CONTEXT ---
{memory_context}
------------------------"""},
        {"role": "user", "content": user_question}
    ]

    max_iterations = 15
    iteration = 0
    final_answer = ""

    while iteration < max_iterations:
        iteration += 1

        # ── STREAMING CALL ─────────────────────────
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            tools=tools,
            messages=messages,
            stream=True
        )

        # ── COLLECT STREAM ─────────────────────────
        collected_content = ""
        collected_tool_calls = []
        current_tool_call = None
        finish_reason = None

        emit("\n✅ Answer:\n")

        for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta
            finish_reason = choice.finish_reason

            # ── TEXT CHUNK → collect completely ────
            if delta.content:
                collected_content += delta.content
                if not callback:
                    print(delta.content, end="", flush=True)

            # ── TOOL CALL CHUNK → collect fully ────
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index is not None:
                        # new tool call starting
                        if len(collected_tool_calls) <= tc.index:
                            collected_tool_calls.append({
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            })
                        if tc.id:
                            collected_tool_calls[tc.index]["id"] = tc.id
                        if tc.function.name:
                            collected_tool_calls[tc.index]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            collected_tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

        # ── AFTER STREAM ENDS ──────────────────────
        if finish_reason == "tool_calls":
            # clear the "Answer:" line since it was a tool call
            if not callback:
                print("\r" + " " * 20 + "\r", end="", flush=True)

            # build assistant message
            assistant_message = {"role": "assistant", "content": collected_content or None, "tool_calls": []}
            tool_results = []

            for tc in collected_tool_calls:
                fn_name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])

                emit(f"🛠️  Using tool: {fn_name}")
                assistant_message["tool_calls"].append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": fn_name, "arguments": tc["function"]["arguments"]}
                })

                if fn_name == "analyze_data":
                    result = analyze_data(args["code"])
                elif fn_name == "generate_chart":
                    result = generate_chart(args["code"], args["description"], args["filename"], callback=callback)
                else:
                    result = "Unknown tool."

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result
                })

            messages.append(assistant_message)
            messages.extend(tool_results)

        else:
            # final answer streamed completely
            final_answer = collected_content
            if callback:
                callback(f"FINAL_ANSWER:{final_answer}")
            else:
                emit("")  # newline after streaming
                print(f"\n✅ Answer:\n{final_answer}")
            logger.finish_question(final_answer)
            return final_answer

    emit("\n⚠️ Max iterations reached!")
    logger.finish_question("Max iterations reached.")
    return None