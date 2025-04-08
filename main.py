from fastapi import FastAPI
import sqlite3
import os
import threading
import leitura_sensor 

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "leituras.db")

# Rota para obter todas as leituras
@app.get("/leituras")
def obter_leituras():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leituras")
    dados = cursor.fetchall()
    conn.close()
    return {"leituras": dados}

# Inicia a leitura do sensor em uma thread separada
threading.Thread(target=leitura_sensor.iniciar_medicoes, daemon=True).start()
