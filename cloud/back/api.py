from fastapi import FastAPI, HTTPException # Import HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor # Para retornar resultados como dicionários
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv # CORRIGIDO: from ... import ...

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# Cria a instância da aplicação FastAPI
app = FastAPI()

# Configura CORS para permitir acesso de qualquer origem (ajuste em produção se necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite todas as origens
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"], # Permite todos os cabeçalhos
)

# --- Função de Conexão com o Banco de Dados ---
# (Versão corrigida, igual à do listener)
def connect_db():
    """
    Connects to the PostgreSQL database using credentials from environment variables.
    Returns a connection object or None if connection fails or variables are missing.
    """
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")

    required_vars = {
        'DB_NAME': db_name,
        'DB_USER': db_user,
        'DB_PASSWORD': db_password,
        'DB_HOST': db_host
    }
    # CORRIGIDO: Verifica se algum valor é None ou vazio
    missing_vars = [k for k, v in required_vars.items() if not v]

    # CORRIGIDO: Checa se a lista não está vazia
    if missing_vars:
        print(f"API Erro: Variáveis de ambiente do banco de dados ausentes: {', '.join(missing_vars)}")
        return None # Retorna None se faltar variável essencial

    try:
        # Log removido daqui para não poluir logs da API a cada request
        # print(f"API Tentando conectar ao DB: host={db_host}...")
        connection = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        # print("API Conexão com DB estabelecida.") # Log opcional
        return connection
    except psycopg2.OperationalError as e:
        print(f"API Erro OPERACIONAL ao conectar ao banco de dados: {e}")
        return None
    except psycopg2.Error as e:
        print(f"API Erro psycopg2 ao conectar ao banco de dados: {e}")
        return None
    except Exception as e:
         print(f"API Erro INESPERADO durante a conexão com o banco de dados: {e}")
         return None

# --- Endpoints da API ---

@app.get("/ultima-leitura")
def get_ultima_leitura(): # Renomeado para seguir convenção Python
    """Busca a leitura mais recente do banco de dados."""
    conn = None # Inicializa conn fora do try
    try:
        conn = connect_db()
        if not conn:
            # Erro já logado em connect_db
            raise HTTPException(status_code=503, detail="Serviço indisponível: Falha na conexão com o banco de dados")

        with conn.cursor(cursor_factory=RealDictCursor) as cur: # Usar 'with' garante fechamento do cursor
            cur.execute("SELECT * FROM leituras ORDER BY timestamp DESC LIMIT 1;")
            result = cur.fetchone()
            # print(f"API /ultima-leitura: Resultado={result}") # Log opcional

        return result if result else {} # Retorna {} se não encontrar nada

    except HTTPException as http_exc:
        raise http_exc # Re-levanta exceções HTTP já tratadas
    except (Exception, psycopg2.Error) as e:
        print(f"API Erro em /ultima-leitura: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao buscar última leitura")
    finally:
        if conn:
            conn.close() # Garante fechamento da conexão

@app.get("/ultimas-24h")
def get_ultimas_24h(): # Renomeado para seguir convenção Python
    """Busca as leituras das últimas 24 horas do banco de dados."""
    conn = None # Inicializa conn fora do try
    try:
        conn = connect_db()
        if not conn:
            raise HTTPException(status_code=503, detail="Serviço indisponível: Falha na conexão com o banco de dados")

        with conn.cursor(cursor_factory=RealDictCursor) as cur: # Usar 'with'
            limite_tempo = datetime.now() - timedelta(hours=24)
            # Usar placeholder %s é mais seguro contra SQL Injection
            cur.execute("SELECT * FROM leituras WHERE timestamp >= %s ORDER BY timestamp ASC;", (limite_tempo,))
            resultados = cur.fetchall()
            # print(f"API /ultimas-24h: Resultados encontrados={len(resultados)}") # Log opcional

        return resultados

    except HTTPException as http_exc:
        raise http_exc
    except (Exception, psycopg2.Error) as e:
        print(f"API Erro em /ultimas-24h: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao buscar histórico")
    finally:
        if conn:
            conn.close()

# Nota: Nenhum bloco if __name__ == "__main__": uvicorn.run(...) aqui,
# o que está correto para deploy no Render onde o comando de start é definido externamente.