import os
import json
from openai import OpenAI
from ddgs import DDGS
from dotenv import load_dotenv
from datetime import date

# ── SETUP ─────────────────────────────────────────
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
today = date.today().strftime("%B %d, %Y")

# ── TOOL DEFINITION ───────────────────────────────
tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for real information on a topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# ── REAL SEARCH FUNCTION ──────────────────────────
def web_search(query: str) -> str:
    print(f"🌐 Searching: {query}")
    results = []

    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=3):
            results.append(f"Title: {r['title']}\nSummary: {r['body']}\nURL: {r['href']}\n")

    if not results:
        return "No results found."

    return "\n".join(results)

# ── AGENT LOOP ────────────────────────────────────
def run_agent(user_question: str):
    print(f"\n🔍 Question: {user_question}")
    print("-" * 50)

    messages = [
        {"role": "system", "content": f"You are a research assistant. Today's date is {today}. You have access to real-time web search. ALWAYS use the web_search tool and base your answer ONLY on the search results returned. Never say you don't have access to recent information — you do, via the search tool. Search for the most current information available."},
        {"role": "user", "content": user_question}
    ]

    max_iterations = 5
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
                query = json.loads(tool_call.function.arguments)["query"]
                result = web_search(query)
                print(f"📄 Got results, thinking...")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        else:
            final_answer = choice.message.content
            print(f"\n✅ Answer:\n{final_answer}")
            return final_answer

    print("\n⚠️ Max iterations reached!")
    return None

# ── RUN ───────────────────────────────────────────
run_agent("Who is the latest prime minister of Nepal")