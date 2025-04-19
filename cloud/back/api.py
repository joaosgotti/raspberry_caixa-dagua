from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
# dotenv import load_dotenv # <-- TYPO AQUI!
from dotenv import load_dotenv # <-- CORREÇÃO

load_dotenv() # OK

app = FastAPI() # OK

# CORS Middleware: OK (talvez restringir origins em produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão com o banco (Duplicada, mas funcional)
# import os              # Já importado
# import psycopg2        # Já importado
# from dotenv import load_dotenv # Já importado e chamado

# load_dotenv() # Já chamado

# Esta função connect_db é IDÊNTICA à do listener e parece CORRETA (usa env vars)
def connect_db():
    """
    Connects to the PostgreSQL database using credentials from environment variables...
    """
    # ... (código da função connect_db que usa os.getenv) ...
    # Verifica se as variáveis mais críticas foram definidas
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")

    required_vars = { # ... (verificação de vars) ... }
    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        # ... (print erro e return None) ...
        print(f"Erro Crítico: Variáveis de ambiente do banco de dados ausentes: {', '.join(missing_vars)}")
        return None

    try:
        # ... (tentativa de conexão com logs) ...
        print(f"Tentando conectar ao DB: host={db_host}, db={db_name}, user={db_user}...") # Log útil
        connection = psycopg2.connect(
            dbname=db_name, user=db_user, password=db_password, host=db_host, port=db_port
        )
        print("Conexão com o banco de dados estabelecida com sucesso!")
        return connection
    except psycopg2.OperationalError as e:
        # ... (print erro e return None) ...
        print(f"Erro OPERACIONAL ao conectar ao banco de dados: {e}")
        return None
    except psycopg2.Error as e:
        # ... (print erro e return None) ...
        print(f"Erro psycopg2 ao conectar ao banco de dados: {e}")
        return None
    except Exception as e:
         # ... (print erro e return None) ...
         print(f"Erro INESPERADO durante a conexão com o banco de dados: {e}")
         return None

# Endpoint /ultima-leitura: Parece CORRETO
@app.get("/ultima-leitura")
def ultima_leitura():
    conn = connect_db()
    # Adicionar verificação se a conexão falhou
    if not conn:
        # Retornar um erro HTTP apropriado
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao banco de dados")

    result = None # Inicializa result
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM leituras ORDER BY timestamp DESC LIMIT 1;")
        result = cur.fetchone()
        cur.close()
    except Exception as e:
         print(f"Erro ao buscar última leitura: {e}")
         # Retornar um erro HTTP apropriado
         from fastapi import HTTPException
         raise HTTPException(status_code=500, detail="Erro ao buscar dados no banco")
    finally:
        if conn:
            conn.close() # Garante que a conexão seja fechada
    return result if result else {} # Retorna {} se nada for encontrado

# Endpoint /ultimas-24h: Parece CORRETO
@app.get("/ultimas-24h")
def ultimas_24h():
    conn = connect_db()
    # Adicionar verificação se a conexão falhou
    if not conn:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao banco de dados")

    resultados = [] # Inicializa resultados
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        limite = datetime.now() - timedelta(hours=24)
        cur.execute("SELECT * FROM leituras WHERE timestamp >= %s ORDER BY timestamp ASC;", (limite,))
        resultados = cur.fetchall()
        cur.close()
    except Exception as e:
         print(f"Erro ao buscar últimas 24h: {e}")
         from fastapi import HTTPException
         raise HTTPException(status_code=500, detail="Erro ao buscar dados no banco")
    finally:
        if conn:
            conn.close() # Garante que a conexão seja fechada
    return resultados

# Não há bloco if __name__ == "__main__": uvicorn.run(...) - CORRETO para Render