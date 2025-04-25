# database_handler.py
import psycopg2
import config
from datetime import datetime

class DatabaseHandler:
    """Lida com a conexão e inserção no banco de dados PostgreSQL."""

    def __init__(self):
        """Inicializa o handler do banco de dados com as configurações."""
        self.db_config = {
            "host": config.DB_HOST,
            "port": config.DB_PORT,
            "dbname": config.DB_NAME,
            "user": config.DB_USER,
            "password": config.DB_PASSWORD,
            "connect_timeout": 10
        }
        print("[DB Handler] Instância criada.")

    def _get_connection(self):
        """Tenta estabelecer uma conexão com o banco de dados."""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
        except psycopg2.Error as e:
            print(f"[DB Handler] ERRO ao conectar ao DB: {e}")
        return conn

    def insert_reading(self, distancia: float, created_on_dt: datetime) -> bool:
        """
        Insere uma leitura de distância na tabela 'leituras'.

        Args:
            distancia (float): O valor da distância lida pelo sensor.
            created_on_dt (datetime): O timestamp da leitura.

        Returns:
            bool: True se a inserção foi bem-sucedida, False caso contrário.
        """
        sql = "INSERT INTO leituras (distancia, created_on) VALUES (%s, %s);"
        conn = self._get_connection()
        if conn is None:
            print("[DB Handler] Falha ao obter conexão DB. Inserção cancelada.")
            return False

        success = False
        cursor = None # Inicializa cursor fora do bloco try
        try:
            cursor = conn.cursor() # Cria um cursor para executar comandos SQL
            cursor.execute(sql, (distancia, created_on_dt))
            conn.commit() # Confirma a transação
            print(f"  [DB Handler] Inserção OK: Dist={distancia:.1f}, CreatedOn={created_on_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            success = True
        except psycopg2.Error as e:
            print(f"  [DB Handler] ERRO ao inserir no DB: {e}")
            if conn:
                conn.rollback() # Em caso de erro, desfaz as alterações
                print("  [DB Handler] Rollback realizado.")
        except Exception as e:
            print(f"  [DB Handler] Erro inesperado na inserção: {e}")
            if conn:
                conn.rollback()
        finally:
            if cursor:
                cursor.close() # Fecha o cursor
            if conn:
                conn.close() # Fecha a conexão com o banco de dados
        return success