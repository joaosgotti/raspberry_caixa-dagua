# cloud/back/main.py
from fastapi import FastAPI
from mqtt_service import start_mqtt

app = FastAPI()

@app.on_event("startup")
def on_startup():
    start_mqtt()

@app.get("/")
def root():
    return {"status": "API online"}
