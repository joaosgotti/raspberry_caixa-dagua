from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

app = FastAPI()

# Permitir CORS (acesso do front-end)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão com o banco
def connect_db():
    return psycopg2.connect(
        dbname="caixa_dagua",
        user="postgres",
        password="1234",
        host="localhost",
        port="5432"
    )

@app.get("/ultima-leitura")
def ultima_leitura():
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM leituras ORDER BY timestamp DESC LIMIT 1;")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

@app.get("/ultimas-24h")
def ultimas_24h():
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    limite = datetime.now() - timedelta(hours=24)
    cur.execute("SELECT * FROM leituras WHERE timestamp >= %s ORDER BY timestamp ASC;", (limite,))
    resultados = cur.fetchall()
    cur.close()
    conn.close()
    return resultados
