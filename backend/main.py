from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import os
import sys
from uuid import uuid4
import pandas as pd

sys.path.append(os.path.dirname(__file__))
from database import init_db, create_session, generate_summary, end_session
from orchestrator import run_pipeline
from salesAgent import load_dataset

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/charts", StaticFiles(directory="charts"), name="charts")


@app.on_event("startup")
def startup() -> None:
    init_db()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/logs")
def get_logs():
    path = "logs/audit_log.json"
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

@app.get("/datasets")
async def get_datasets():
    datasets = [
        {
            "filename": "sales_data.csv",
            "name": "Sales Dataset",
            "description": "TechCorp retail sales data across regions and products",
            "rows": 2000,
            "date_range": "2022–2024"
        },
        {
            "filename": "inventory_data.csv",
            "name": "Inventory Dataset", 
            "description": "TechCorp warehouse stock levels and supply chain data",
            "rows": 1152,
            "date_range": "2022–2024"
        },
        {
            "filename": "customer_data.csv",
            "name": "Customer Dataset",
            "description": "TechCorp customer profiles, spending and loyalty data",
            "rows": 2000,
            "date_range": "2022–2024"
        }
    ]
    for d in datasets:
        try:
            df_temp = pd.read_csv(d["filename"])
            d["columns"] = list(df_temp.columns)
        except:
            d["columns"] = []
    return datasets

@app.post("/session/end")
async def end_session_endpoint(data: dict):
    session_id = data.get("session_id")
    if not session_id:
        return {"error": "session_id required"}
    summary = generate_summary(session_id)
    end_session(session_id, summary)
    return {"status": "ended", "summary": summary}

@app.post("/session/start")
async def start_session_endpoint(data: dict):
    dataset_name = data.get("dataset_name", "sales_data.csv")
    dataset_source = data.get("dataset_source", "local")
    load_dataset(dataset_name)
    session_id = create_session(
        session_id=str(uuid4()),
        dataset_name=dataset_name,
        dataset_source=dataset_source
    )
    return {
        "session_id": session_id,
        "dataset_name": dataset_name,
        "dataset_source": dataset_source
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = None):
    await websocket.accept()
    if not session_id:
        session_id = str(uuid4())
        create_session(session_id, dataset_name="sales_data.csv", dataset_source="local")
    try:
        while True:
            question = await websocket.receive_text()
            
            loop = asyncio.get_event_loop()
            
            def callback(msg: str):
                # Check if this is a final answer
                if msg.startswith("FINAL_ANSWER:"):
                    final_answer = msg.replace("FINAL_ANSWER:", "")
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_text(json.dumps({
                            "type": "answer",
                            "message": final_answer
                        })),
                        loop
                    )
                else:
                    # Regular update message
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_text(json.dumps({
                            "type": "update",
                            "message": msg
                        })),
                        loop
                    )
            
            await loop.run_in_executor(
                None,
                lambda: run_pipeline(question, callback=callback, session_id=session_id)
            )
            
            await websocket.send_text(json.dumps({
                "type": "done",
                "message": "DONE"
            }))
            
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
