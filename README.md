# 📊 Multi-Agent Data Analysis System

> A full-stack AI-powered business intelligence platform built with a multi-agent architecture, real-time streaming, and Google Drive integration.

![Python](https://img.shields.io/badge/Python-3.13-blue?style=flat-square&logo=python)
![Next.js](https://img.shields.io/badge/Next.js-15-black?style=flat-square&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat-square&logo=openai)
![Google Drive](https://img.shields.io/badge/Google%20Drive-MCP-4285F4?style=flat-square&logo=googledrive)

---

## 🧠 What Is This?

This is a multi-agent AI system that lets you have a natural language conversation with your data. Ask questions, get answers, generate charts — all in real time.

```
"Which product had the highest sales?"
→ Laptop — $2,469,320.66

"Show me sales by region as a pie chart"
→ [Chart appears inline, uploaded to Google Drive automatically]

"What percentage of total sales does electronics contribute?"
→ Electronics contributes 83.31% of total sales
```

Built entirely from scratch — no LangChain, no LangGraph — to understand every layer of how AI agents actually work.

---

## 🏗️ Architecture

```
User Question (Next.js Frontend)
        ↓  WebSocket
FastAPI Backend
        ↓
Orchestrator Agent          ← coordinates everything
        ↓
Memory Agent                ← reads last Q&A from session logs
        ↓
Clarifier Agent             ← resolves vague pronouns ("it", "that")
        ↓
Analysis Agent              ← runs pandas code, generates charts
        ↓
Drive Agent                 ← uploads charts to Google Drive
        ↓
Response streamed back to frontend
```

### Non-Linear Routing

The orchestrator makes decisions:
```
Question is vague ("what about it?")  →  Clarifier Agent runs
Question is clear                      →  Skip clarifier, go direct
Chart generated                        →  Drive Agent uploads
No chart generated                     →  Drive Agent skipped
```

---

## 📁 Project Structure

```
ai-agent/
├── backend/
│   ├── main.py                  ← FastAPI app + WebSocket endpoint
│   ├── orchestrator.py          ← coordinates all agents
│   ├── salesAgent.py            ← core analysis + chart generation
│   ├── memoryAgent.py           ← session memory from logs
│   ├── clarifierAgent.py        ← resolves vague follow-up questions
│   ├── driveAgent.py            ← Google Drive MCP integration
│   ├── guardrails.py            ← safety checks (question + code level)
│   ├── database.py              ← SQLite session management
│   ├── sales_data.csv           ← sample dataset (2000 rows)
│   ├── inventory_data.csv       ← sample inventory dataset
│   ├── customer_data.csv        ← sample customer dataset
│   ├── charts/                  ← generated charts (gitignored)
│   └── logs/                    ← audit logs JSON/CSV/TXT (gitignored)
│
├── frontend/
│   └── app/
│       ├── page.tsx             ← main chat interface
│       └── layout.tsx
│
├── .env                         ← API keys (gitignored)
├── requirements.txt
└── README.md
```

---

## ✨ Features

### AI Agents
- **Orchestrator** — routes questions through the right agents
- **Memory Agent** — maintains context across questions using audit logs (zero extra API cost)
- **Clarifier Agent** — rewrites vague questions like *"what about it?"* into precise queries
- **Analysis Agent** — writes and executes real pandas code against your data
- **Drive Agent** — automatically uploads generated charts to Google Drive

### Data Analysis
- Natural language to pandas code execution
- Supports bar charts, pie charts, line charts, horizontal bars
- Charts display inline in the chat UI
- Cross-dataset analysis across sales, inventory, and customer data

### Sessions
- Session-based workflow: choose dataset → chat → end session
- SQLite database stores all sessions, messages, and chart references
- Session summary auto-generated on end (pure Python, no extra LLM call)
- Three dataset sources: preloaded CSVs, file upload, Google Drive fetch

### Safety & Observability
- **Guardrails** — blocks dangerous code patterns (`os.system`, `subprocess`, etc.) and harmful questions
- **Audit Logs** — every tool call logged to JSON, CSV, and TXT
- **Real-time pipeline** — see every agent step as it happens in the UI

### Google Drive Integration
- Fetch datasets directly from your Drive
- Charts automatically uploaded to `AgentReports/` folder
- Clickable Drive links shown after each chart

---

## 🖥️ UI

Two states:

**State 1 — Dataset Selection**
```
Choose your dataset
├── Use existing dataset (sales / inventory / customer)
├── Upload a CSV file
└── Fetch from Google Drive
        ↓
[Start Session]
```

**State 2 — Active Chat**
```
[Pipeline messages streaming live]
🎯 Orchestrator received...
🧠 Memory Agent fetching context...
💡 Clarifier: rewrote question...
🤖 Analysis Agent working...
🛠️ Using tool: analyze_data
🛠️ Using tool: generate_chart
📊 Chart saved: charts/filename.png
[Chart image inline]
☁️ Drive Agent: uploading...
🔗 Chart link: https://drive.google.com/...

[Final answer card]
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.13+
- Node.js 22+
- OpenAI API key
- Google Cloud project with Drive API enabled

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/ai-agent.git
cd ai-agent
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` in the root:
```env
OPENAI_API_KEY=sk-your-key-here
```

### 3. Google Drive Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Google Drive API**
3. Create OAuth credentials → **Desktop app**
4. Download as `credentials.json` → place in `backend/`
5. Add your Google account as a test user in OAuth consent screen

First run will open browser for authentication and create `token.json` automatically.

### 4. Frontend Setup

```bash
cd frontend
npm install
```

### 5. Run

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/datasets` | List available datasets |
| `POST` | `/session/start` | Start a new session |
| `POST` | `/session/end` | End session + generate summary |
| `GET` | `/session/{id}` | Get session details |
| `GET` | `/logs` | Get audit logs |
| `WS` | `/ws` | WebSocket for real-time chat |
| `GET` | `/charts/{filename}` | Serve generated chart images |

---

## 📊 Sample Datasets

Three datasets for TechCorp (fictional electronics retailer):

**sales_data.csv** — 2000 rows
```
Date, Product, Category, Region, Age Group, Units Sold, Unit Price, Total Sales
```

**inventory_data.csv** — 500 rows
```
Date, Product, Category, Region, Stock_Level, Reorder_Point, Units_Received, Warehouse_Cost
```

**customer_data.csv** — 1500 rows
```
Customer_ID, Age_Group, Region, Preferred_Category, Total_Purchases, Total_Spent, Last_Purchase_Date, Loyalty_Score
```

Cross-dataset queries:
```
"Which products are low on stock but have high sales?"
"Which customers buy the most laptops?"
"Which region has high sales but low inventory?"
```

---

## 🛡️ Safety

Questions are checked before reaching the agent:
- Blocked keywords: `delete`, `drop`, `os.system`, `subprocess`, `exec(`
- Max question length enforced
- Empty question protection

Generated code is checked before execution:
- Dangerous system calls blocked
- File system access restricted
- All blocks logged to audit trail

---

## 📋 Audit Logs

Every session generates three log files:

```
logs/
├── audit_log.json    ← structured, for programmatic access
├── audit_log.csv     ← open in Excel, filter by session
└── audit_log.txt     ← human readable diary
```

Each entry contains: question, tool used, code executed, result, time taken, success/failure.

---

## 🗄️ Database Schema

```sql
sessions
├── session_id     TEXT PRIMARY KEY
├── dataset_name   TEXT
├── dataset_source TEXT  (local/upload/drive)
├── started_at     TIMESTAMP
├── ended_at       TIMESTAMP
├── status         TEXT  (active/ended)
└── summary        TEXT

messages
├── message_id     INTEGER PRIMARY KEY
├── session_id     TEXT (FK → sessions)
├── question       TEXT
├── answer         TEXT
├── timestamp      TIMESTAMP
└── step_count     INTEGER

charts
├── chart_id       INTEGER PRIMARY KEY
├── message_id     INTEGER (FK → messages)
├── session_id     TEXT (FK → sessions)
├── filename       TEXT
├── local_path     TEXT
├── drive_link     TEXT
└── created_at     TIMESTAMP
```

---

## 🔮 Roadmap

- [ ] Word-by-word streaming (currently sends complete answer)
- [ ] RAG implementation (ChromaDB for business document context)
- [ ] Rebuild agents in LangChain/LangGraph
- [ ] User authentication + multi-tenant support
- [ ] Production deployment
- [ ] Show uploaded/Drive datasets in dataset picker
- [ ] Cross-dataset analysis UI

---

## 🧪 Example Questions

```
# Analysis
"What is the total revenue generated across all years?"
"Which product had the highest total sales?"
"What percentage of sales does electronics contribute?"

# Charts
"Show me top 5 products by total sales as a bar chart"
"Show me sales by region as a pie chart"
"Show me average order value by age group as a bar chart"

# Follow-ups (memory + clarifier working)
"Which region has the lowest sales?"
"By how much does it differ from the highest?"  ← clarifier resolves "it"

# Cross-dataset
"Which products are low on stock but have high sales?"
```

---

## 🙏 Built With

- [OpenAI API](https://platform.openai.com) — GPT-4o-mini
- [FastAPI](https://fastapi.tiangolo.com) — async Python backend
- [Next.js](https://nextjs.org) — React frontend
- [Pandas](https://pandas.pydata.org) — data analysis
- [Matplotlib](https://matplotlib.org) — chart generation
- [Google Drive API](https://developers.google.com/drive) — cloud storage
- [SQLite](https://sqlite.org) — session database

---

*Built from scratch to understand every layer of multi-agent AI systems.*
