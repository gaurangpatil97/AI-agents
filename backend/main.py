from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import os
import sys

sys.path.append(os.path.dirname(__file__))
from orchestrator import run_pipeline

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/charts", StaticFiles(directory="charts"), name="charts")

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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
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
                lambda: run_pipeline(question, callback=callback)
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
