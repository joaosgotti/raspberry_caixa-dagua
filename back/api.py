# --- Importação de Bibliotecas ---
# Importa módulos necessários para a aplicação web, banco de dados e manipulação de datas.
from fastapi import FastAPI, HTTPException # HTTPException para retornar erros HTTP
from fastapi.middleware.cors import CORSMiddleware # Middleware para lidar com requisições CORS (acesso de frontend)
import psycopg2 # Driver para interagir com o banco de dados PostgreSQL
from psycopg2.extras import RealDictCursor # Permite que os resultados das queries sejam dicionários Python
from datetime import datetime, timedelta # Para trabalhar com datas e calcular intervalos de tempo
import os # Para acessar variáveis de ambiente
from dotenv import load_dotenv # Para carregar variáveis de ambiente de um arquivo .env

# --- Carregamento de Variáveis de Ambiente ---
# Carrega variáveis definidas em um arquivo .env no ambiente do processo.
# Isso é essencial para manter credenciais e configurações fora do código-fonte.
load_dotenv()

# --- Configuração da Aplicação FastAPI ---
# Cria a instância principal da aplicação FastAPI.
app = FastAPI(
    title="API de Leituras do Sensor de Distância", # Título para a documentação interativa (Swagger/OpenAPI)
    description="API para acessar dados de distância do sensor salvos no banco de dados.",
    version="1.0.0",
)

# --- Configuração do Middleware CORS ---
# CORS (Cross-Origin Resource Sharing) permite que navegadores web em outras origens (domínios, portas)
# acessem sua API. Configure allow_origins para domínios específicos em produção por segurança.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Define quais origens podem acessar a API. Use ["*"] apenas para desenvolvimento/teste.
                         # Em produção, substitua por uma lista de strings, ex: ["https://seu-frontend.com"]
    allow_credentials=True, # Permite cookies e cabeçalhos de autenticação na requisição cross-origin
    allow_methods=["*"], # Métodos HTTP permitidos (GET, POST, PUT, DELETE, etc.). "*" permite todos.
    allow_headers=["*"], # Cabeçalhos HTTP permitidos na requisição cross-origin. "*" permite todos.
)

# --- Função de Conexão com o Banco de Dados ---
# Encapsula a lógica para estabelecer uma conexão com o banco de dados PostgreSQL.
def connect_db():
    """
    Estabelece uma conexão com o banco de dados PostgreSQL usando credenciais de variáveis de ambiente.

    Verifica se as variáveis de ambiente necessárias para a conexão existem.
    Retorna um objeto de conexão do psycopg2 ou None se a conexão falhar
    ou se as variáveis de ambiente estiverem ausentes.
    """
    # Busca as variáveis de ambiente para as credenciais do DB
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    # Define a porta padrão como 5432, mas permite sobrescrever via variável de ambiente
    db_port = os.getenv("DB_PORT", "5432")

    # --- Validação das Variáveis de Ambiente do DB ---
    required_vars = {
        'DB_NAME': db_name,
        'DB_USER': db_user,
        'DB_PASSWORD': db_password,
        'DB_HOST': db_host
    }
    # Identifica quais variáveis essenciais estão faltando (são None ou string vazia)
    missing_vars = [k for k, v in required_vars.items() if not v]

    # Se houver variáveis faltando, imprime um erro e retorna None
    if missing_vars:
        # Note: Erros são logados aqui, a API retornará um erro HTTP 503 depois.
        print(f"API Erro Crítico: Variáveis de ambiente do banco de dados ausentes: {', '.join(missing_vars)}")
        return None

    # --- Tentativa de Conexão ---
    try:
        # Tenta conectar ao banco de dados usando as variáveis carregadas
        connection = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            # Adiciona um timeout para a conexão (opcional, mas recomendado)
            connect_timeout=5
        )
        # print("API Conexão com DB estabelecida com sucesso.") # Log opcional de sucesso
        return connection

    # --- Tratamento de Erros na Conexão ---
    # Captura erros operacionais específicos do psycopg2 (ex: DB offline, credenciais erradas)
    except psycopg2.OperationalError as e:
        print(f"API Erro OPERACIONAL ao conectar ao banco de dados: {e}")
        return None
    # Captura outros erros gerais do psycopg2
    except psycopg2.Error as e:
        print(f"API Erro psycopg2 ao conectar ao banco de dados: {e}")
        return None
    # Captura quaisquer outros erros inesperados durante o processo de conexão
    except Exception as e:
        print(f"API Erro INESPERADO durante a conexão com o banco de dados: {e}")
        return None

# --- Endpoints da API ---

@app.get("/leitura/ultima", summary="Obter a última leitura de distância")
def get_ultima_leitura():
    """
    Busca a leitura de distância mais recente registrada no banco de dados.

    Retorna um objeto JSON contendo os detalhes da última leitura (distância, timestamp).
    Se nenhuma leitura for encontrada, retorna um objeto vazio {}.
    Retorna 503 se não conseguir conectar ao DB, 500 para outros erros.
    """
    conn = None # Inicializa a variável de conexão como None
    try:
        # Tenta obter uma conexão com o banco de dados
        conn = connect_db()
        # Se a conexão falhou (retornou None), levanta uma exceção HTTP 503 (Serviço Indisponível)
        if not conn:
            # A mensagem de erro detalhada já foi logada em connect_db()
            raise HTTPException(status_code=503, detail="Serviço indisponível: Falha na conexão com o banco de dados")

        # Usa um bloco 'with' para garantir que o cursor seja fechado automaticamente
        # O cursor_factory=RealDictCursor garante que cada linha retornada seja um dicionário
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Executa a query para selecionar todos os campos (*) da tabela 'leituras'
            # Ordena por 'created_on' (coluna usada para o timestamp na inserção MQTT) em ordem decrescente (mais recente primeiro)
            # Limita o resultado a 1 linha para obter apenas a última leitura
            cur.execute("SELECT * FROM leituras ORDER BY created_on DESC LIMIT 1;")
            # Obtém a primeira (e única) linha do resultado
            result = cur.fetchone()

        # Se uma leitura foi encontrada, retorna o dicionário. Caso contrário, retorna um dicionário vazio.
        return result if result else {}

    # Re-levanta exceções HTTPException que já foram geradas (ex: 503 da falha de conexão)
    except HTTPException as http_exc:
        raise http_exc
    # Captura quaisquer outros erros (de banco de dados ou inesperados)
    except (Exception, psycopg2.Error) as e:
        # Loga o erro no servidor
        print(f"API Erro em /leitura/ultima: {e}")
        # Levanta uma exceção HTTP 500 (Erro Interno do Servidor)
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao buscar última leitura")
    # O bloco finally sempre executa antes de sair do try/except
    finally:
        # Garante que a conexão com o banco de dados seja fechada se ela foi aberta com sucesso
        if conn:
            try:
                conn.close()
                # print("API Conexão com DB fechada.") # Log opcional de fechamento
            except psycopg2.Error as close_err:
                 print(f"API Erro ao fechar conexão DB em /leitura/ultima: {close_err}")


@app.get("/leituras", summary="Obter leituras de distância em um período")
def get_leituras_por_periodo(
    periodo_horas: int = 24 # Parâmetro de query opcional com valor padrão de 24
):
    """
    Busca todas as leituras de distância registradas no banco de dados
    dentro de um determinado período de tempo em relação ao momento atual.

    Args:
        periodo_horas: O número de horas para trás a partir do momento atual
                       para incluir nas leituras. Padrão: 24 horas.

    Retorna uma lista de objetos JSON (dicionários) contendo as leituras
    dentro do período especificado, ordenadas por timestamp ascendente.
    Se nenhuma leitura for encontrada no período, retorna uma lista vazia [].
    Retorna 503 se não conseguir conectar ao DB, 500 para outros erros.
    """
    conn = None # Inicializa a variável de conexão como None
    try:
        # Tenta obter uma conexão com o banco de dados
        conn = connect_db()
        # Se a conexão falhou (retornou None), levanta uma exceção HTTP 503
        if not conn:
            raise HTTPException(status_code=503, detail="Serviço indisponível: Falha na conexão com o banco de dados")

        # Usa um bloco 'with' para o cursor e o RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Calcula o timestamp limite subtraindo o período_horas do momento atual
            limite_tempo = datetime.now() - timedelta(hours=periodo_horas)

            # Executa a query para selecionar leituras onde 'created_on' (timestamp da leitura)
            # é maior ou igual ao limite_tempo calculado.
            # Ordena os resultados por 'created_on' em ordem ascendente (mais antiga primeiro).
            # Usa %s como placeholder para o valor limite_tempo para evitar SQL injection.
            cur.execute("SELECT * FROM leituras WHERE created_on >= %s ORDER BY created_on ASC;", (limite_tempo,))
            # Obtém todas as linhas do resultado da query em uma lista de dicionários
            resultados = cur.fetchall()

        # Retorna a lista de resultados. Se não houver resultados, retorna uma lista vazia [].
        return resultados

    # Re-levanta exceções HTTPException (ex: 503 da falha de conexão)
    except HTTPException as http_exc:
        raise http_exc
    # Captura quaisquer outros erros
    except (Exception, psycopg2.Error) as e:
        print(f"API Erro em /leituras: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor ao buscar histórico")
    # O bloco finally sempre executa
    finally:
        # Garante que a conexão com o banco de dados seja fechada
        if conn:
             try:
                conn.close()
                # print("API Conexão com DB fechada.") # Log opcional de fechamento
             except psycopg2.Error as close_err:
                 print(f"API Erro ao fechar conexão DB em /leituras: {close_err}")


# --- Como Rodar a API ---
# Este script NÃO inclui o bloco if __name__ == "__main__": uvicorn.run(...)
# Isso é comum quando a aplicação será executada por um servidor WSGI (como uvicorn)
# em ambientes de produção (como Render, Heroku, etc.), onde o comando de startup
# é configurado externamente.
#
# Para rodar localmente para testes, você usaria um comando no terminal como:
# uvicorn seu_arquivo_api:app --reload
# (Assumindo que o arquivo se chama 'seu_arquivo_api.py')