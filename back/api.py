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
    allow_origins=["*"], # Em produção, use domínios específicos: ["https://seu-frontend-app.onrender.com"] ou o domínio correto
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
            connect_timeout=5 # Timeout de 5 segundos para conexão
        )
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

@app.get("/leituras/ultima", summary="Obter a última leitura (distância e nível calculado)")
def get_ultima_leitura():
    """
    Busca a leitura de distância mais recente, calcula o 'nivel' e retorna com fuso de Recife.

    Retorna um objeto JSON com 'distancia', 'created_on' (Recife TZ) e 'nivel'.
    Retorna {} se nenhuma leitura for encontrada.
    Retorna 503 (DB Error), 500 (Server Error).
    """
    conn = None
    try:
        conn = connect_db()
        if not conn:
            raise HTTPException(status_code=503, detail="Serviço indisponível: Falha na conexão com o banco de dados")

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Busca a leitura mais recente do banco
            cur.execute("SELECT id, distancia, created_on FROM leituras ORDER BY created_on DESC LIMIT 1;")
            result = cur.fetchone() # Pega a linha do DB como um dicionário Python

        # Verifica se um resultado foi encontrado
        if result:
            # 1. Processa o Timestamp para o fuso horário de Recife
            original_datetime = result['created_on']
            # Garante que o datetime seja 'aware' (tenha fuso horário), assumindo UTC se for 'naive'
            if original_datetime.tzinfo is None:
                print(f"AVISO (ID: {result['id']}): Timestamp do DB veio como naive. Assumindo UTC.")
                original_datetime = original_datetime.replace(tzinfo=timezone.utc)
            # Define o fuso horário de destino
            local_timezone = pytz.timezone('America/Recife')
            # Converte o datetime para o fuso de Recife
            local_datetime = original_datetime.astimezone(local_timezone)
            # Atualiza o campo 'created_on' no dicionário com a string formatada ISO
            result['created_on'] = local_datetime.isoformat()

            # 2. Calcula e Adiciona o campo 'nivel' ao dicionário
            distancia_original = result.get('distancia') # Pega o valor da distância do resultado do DB
            if isinstance(distancia_original, (int, float)): # Verifica se a distância é um número válido
                nivel_calculado = distancia_original * 3  # Calcula o nível multiplicando por 3
                result['nivel'] = round(nivel_calculado, 1) # Adiciona o campo 'nivel' arredondado ao dicionário
            else:
                # Se a distância não for um número (ou for None), define 'nivel' como None
                result['nivel'] = None

            # 3. Retorna o dicionário completo ('result') que agora contém o campo 'nivel'
            return result
        else:
            # Se a query não retornou nenhuma linha (tabela vazia?)
            return {} # Retorna um dicionário vazio

    except HTTPException as http_exc:
        # Re-levanta exceções HTTP específicas para o FastAPI tratar
        raise http_exc
    except (Exception, psycopg2.Error) as e:
        # Captura outros erros genéricos ou do psycopg2
        print(f"API Erro em /leituras/ultima: {e}")
        # Retorna um erro 500 genérico para o cliente
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao buscar última leitura")
    finally:
        # Garante que a conexão com o banco de dados seja fechada, mesmo se ocorrer um erro
        if conn:
            try:
                conn.close()
            except psycopg2.Error as close_err:
                # Loga um erro se o fechamento da conexão falhar, mas não impede a resposta
                print(f"API Erro ao fechar conexão DB em /leituras/ultima: {close_err}")


@app.get("/leituras", summary="Obter leituras de distância em um período")
def get_leituras_por_periodo(
    periodo_horas: int = 24 # Parâmetro de query opcional, padrão 24 horas
):
    """
    Busca leituras de DISTÂNCIA dentro de um período e as retorna com o fuso horário de Recife.
    (Não calcula o 'nivel' para o histórico).

    Args:
        periodo_horas: Número de horas para trás a partir do momento atual. Padrão: 24.

    Retorna lista de leituras (com 'distancia' e 'created_on' no fuso de Recife),
    ordenada por timestamp ascendente (mais antiga primeiro).
    Retorna lista vazia [] se nenhuma leitura for encontrada no período.
    Retorna 503 (DB Error), 500 (Server Error).
    """
    conn = None
    try:
        conn = connect_db()
        if not conn:
            raise HTTPException(status_code=503, detail="Serviço indisponível: Falha na conexão com o banco de dados")

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Calcula o timestamp limite em UTC para a consulta no banco
            limite_tempo_utc = datetime.now(timezone.utc) - timedelta(hours=periodo_horas)

            # Busca leituras dentro do período, ordenadas da mais antiga para a mais recente
            cur.execute(
                "SELECT id, distancia, created_on FROM leituras WHERE created_on >= %s ORDER BY created_on ASC;",
                (limite_tempo_utc,)
            )
            resultados = cur.fetchall() # Pega todas as linhas que correspondem como uma lista de dicionários

        # Define o fuso horário de Recife uma vez fora do loop para eficiência
        local_timezone = pytz.timezone('America/Recife')

        # Processa cada leitura APENAS para converter o fuso horário
        leituras_processadas = []
        for leitura in resultados:
            # --- CORREÇÃO DE FUSO HORÁRIO APLICADA ---
            original_datetime = leitura['created_on']
            # Garante que seja 'aware', assumindo UTC se 'naive'
            if original_datetime.tzinfo is None:
                 print(f"AVISO (ID: {leitura['id']}): Timestamp do DB veio como naive. Assumindo UTC.")
                 original_datetime = original_datetime.replace(tzinfo=timezone.utc)
            # Converte para o fuso de Recife
            local_datetime = original_datetime.astimezone(local_timezone)
            # Atualiza o campo 'created_on' no dicionário da leitura atual
            leitura['created_on'] = local_datetime.isoformat()

            # Adiciona o dicionário 'leitura' (APENAS com timestamp ajustado) à lista final
            leituras_processadas.append(leitura)

        # Retorna a lista de leituras processadas (sem o campo 'nivel')
        return leituras_processadas

    except HTTPException as http_exc:
        # Re-levanta exceções HTTP
        raise http_exc
    except (Exception, psycopg2.Error) as e:
        # Captura outros erros
        print(f"API Erro em /leituras: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao buscar histórico")
    finally:
        # Garante o fechamento da conexão
        if conn:
            try:
                conn.close()
            except psycopg2.Error as close_err:
                print(f"API Erro ao fechar conexão DB em /leituras: {close_err}")

# --- Execução com Uvicorn (se este script for executado diretamente) ---
# Permite rodar com 'python api.py' para testes rápidos locais.
# Para produção ou execução normal, use 'run_backend.py' ou o comando uvicorn diretamente.
if __name__ == "__main__":
    import uvicorn
    print("Executando API diretamente com Uvicorn (para teste)...")
    print("Use 'run_backend.py' ou 'uvicorn api:app --host 0.0.0.0 --port 8000' para execução normal.")
    # Roda na máquina local (127.0.0.1) na porta 8000 por padrão quando executado diretamente
    uvicorn.run(app, host="127.0.0.1", port=8000)