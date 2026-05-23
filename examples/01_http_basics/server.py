"""HTTP basics - the simplest possible server.

Run: uvicorn server:app --port 8101
"""
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()
hit_count = 0


@app.get("/")
def root():
    global hit_count
    hit_count += 1
    return {
        "message": "hello",
        "hit_number": hit_count,
        "server_time": datetime.utcnow().isoformat(),
        "note": "I am a stateless server. I don't know who you are between requests.",
    }


@app.get("/echo")
def echo(msg: str = "ping"):
    return {"you_said": msg, "i_say": msg.upper()}
