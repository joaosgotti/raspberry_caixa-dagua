# api.py

# --- Importação de Bibliotecas ---
# Importa módulos necessários para a aplicação web, banco de dados e manipulação de datas.
from fastapi import FastAPI, HTTPException # HTTPException para retornar erros HTTP
from fastapi.middleware.cors import CORSMiddleware # Middleware para lidar com requisições CORS (acesso de frontend)
import psycopg2 # Driver para interagir com o banco de dados PostgreSQL
from psycopg2.extras import RealDictCursor # Permite que os resultados das queries sejam dicionários Python
from datetime import datetime, timedelta, timezone # Importa timezone para manipulação de fusos horários
import os # Para acessar variáveis de ambiente
from dotenv import load_dotenv # Para carregar variáveis de ambiente de um arquivo .env
import pytz # Biblioteca para trabalhar com fusos horários (pip install pytz)

# --- Carregamento de Variáveis de Ambiente ---
load_dotenv()

# --- Configuração da Aplicação FastAPI ---
app = FastAPI(
    title="API de Leituras do Sensor de Distância",
    description="API para acessar dados de distância do sensor salvos no banco de dados.",
    version="1.0.0",
)

# --- Configuração do Middleware CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em produção, use domínios específicos: ["https://seu-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Função de Conexão com o Banco de Dados ---
def connect_db():
    """
    Estabelece uma conexão com o banco de dados PostgreSQL usando credenciais de variáveis de ambiente.

    Verifica se as variáveis de ambiente necessárias para a conexão existem.
    Retorna um objeto de conexão do psycopg2 ou None se a conexão falhar
    ou se as variáveis de ambiente estiverem ausentes.
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
    missing_vars = [k for k, v in required_vars.items() if not v]

    if missing_vars:
        print(f"API Erro Crítico: Variáveis de ambiente do banco de dados ausentes: {', '.join(missing_vars)}")
        return None

    try:
        connection = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            connect_timeout=5
        )
        # print("API Conexão com DB estabelecida com sucesso.") # Log opcional
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

@app.get("/leituras/ultima", summary="Obter a última leitura de distância")
def get_ultima_leitura():
    """
    Busca a leitura de distância mais recente registrada no banco de dados e a retorna com o fuso horário de Recife.

    Retorna um objeto JSON contendo os detalhes da última leitura (distância, timestamp no fuso horário de Recife).
    Se nenhuma leitura for encontrada, retorna um objeto vazio {}.
    Retorna 503 se não conseguir conectar ao DB, 500 para outros erros.
    """
    conn = None
    try:
        conn = connect_db()
        if not conn:
            raise HTTPException(status_code=503, detail="Serviço indisponível: Falha na conexão com o banco de dados")

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Busca a leitura mais recente
            cur.execute("SELECT id, distancia, created_on FROM leituras ORDER BY created_on DESC LIMIT 1;")
            result = cur.fetchone()

        if result:
            # --- CORREÇÃO DE FUSO HORÁRIO APLICADA ---
            original_datetime = result['created_on']

            # Verificação opcional: Se o datetime do DB for 'naive' (sem fuso), assume UTC.
            # Isso é uma segurança caso a coluna não seja TIMESTAMPTZ ou algo deu errado na inserção.
            if original_datetime.tzinfo is None:
                print(f"AVISO (ID: {result['id']}): Timestamp do DB veio como naive. Assumindo UTC.")
                original_datetime = original_datetime.replace(tzinfo=timezone.utc)

            # Define o fuso horário de Recife
            local_timezone = pytz.timezone('America/Recife')

            # Converte o datetime original (que deve ser aware e em UTC) para o fuso de Recife
            local_datetime = original_datetime.astimezone(local_timezone)

            # Atualiza o dicionário com o timestamp formatado em ISO e com o offset correto
            result['created_on'] = local_datetime.isoformat()
            return result
        else:
            # Nenhuma leitura encontrada
            return {}

    except HTTPException as http_exc:
        raise http_exc
    except (Exception, psycopg2.Error) as e:
        print(f"API Erro em /leituras/ultima: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao buscar última leitura")
    finally:
        if conn:
            try:
                conn.close()
                # print("API Conexão com DB fechada.") # Log opcional
            except psycopg2.Error as close_err:
                print(f"API Erro ao fechar conexão DB em /leituras/ultima: {close_err}")


@app.get("/leituras", summary="Obter leituras de distância em um período")
def get_leituras_por_periodo(
    periodo_horas: int = 24 # Parâmetro de query opcional
):
    """
    Busca leituras dentro de um período e as retorna com o fuso horário de Recife.

    Args:
        periodo_horas: Número de horas para trás a partir do momento atual. Padrão: 24.

    Retorna lista de leituras com timestamp no fuso de Recife, ordenada por timestamp ascendente.
    Retorna lista vazia [] se nenhuma leitura for encontrada.
    Retorna 503 se não conseguir conectar ao DB, 500 para outros erros.
    """
    conn = None
    try:
        conn = connect_db()
        if not conn:
            raise HTTPException(status_code=503, detail="Serviço indisponível: Falha na conexão com o banco de dados")

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Calcula o timestamp limite em UTC
            limite_tempo_utc = datetime.now(timezone.utc) - timedelta(hours=periodo_horas)

            # Busca leituras dentro do período, ordenadas da mais antiga para a mais recente
            cur.execute(
                "SELECT id, distancia, created_on FROM leituras WHERE created_on >= %s ORDER BY created_on ASC;",
                (limite_tempo_utc,)
            )
            resultados = cur.fetchall()

        # Define o fuso horário de Recife uma vez fora do loop
        local_timezone = pytz.timezone('America/Recife')

        # Processa cada leitura para converter o fuso horário
        leituras_convertidas = []
        for leitura in resultados:
            # --- CORREÇÃO DE FUSO HORÁRIO APLICADA ---
            original_datetime = leitura['created_on']

            # Verificação opcional: Se o datetime do DB for 'naive', assume UTC.
            if original_datetime.tzinfo is None:
                 print(f"AVISO (ID: {leitura['id']}): Timestamp do DB veio como naive. Assumindo UTC.")
                 original_datetime = original_datetime.replace(tzinfo=timezone.utc)

            # Converte para o fuso de Recife
            local_datetime = original_datetime.astimezone(local_timezone)

            # Atualiza o dicionário com o timestamp formatado
            leitura['created_on'] = local_datetime.isoformat()
            leituras_convertidas.append(leitura) # Adiciona à lista final

        return leituras_convertidas

    except HTTPException as http_exc:
        raise http_exc
    except (Exception, psycopg2.Error) as e:
        print(f"API Erro em /leituras: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao buscar histórico")
    finally:
        if conn:
            try:
                conn.close()
                # print("API Conexão com DB fechada.") # Log opcional
            except psycopg2.Error as close_err:
                print(f"API Erro ao fechar conexão DB em /leituras: {close_err}")

# --- Execução com Uvicorn (se este script for executado diretamente) ---
# Geralmente, você usará o comando 'uvicorn api:app --reload' ou o seu script 'run_backend.py'
# Mas esta seção permite rodar com 'python api.py' para testes rápidos.
if __name__ == "__main__":
    import uvicorn
    print("Executando API diretamente com Uvicorn (para teste)...")
    print("Use 'run_backend.py' ou 'uvicorn api:app --host 0.0.0.0 --port 8000' para execução normal.")
    uvicorn.run(app, host="127.0.0.1", port=8000) # Roda localmente por padrão se executado diretamente