# db_handler.py
import config # Importa as configurações de DB
from datetime import datetime
from typing import Optional
import sys
# --- Dependências Externas ---
try:
    import psycopg2
    import psycopg2.extensions
except ImportError as e:
     print(f"Erro: Dependência psycopg2 não encontrada - {e}")
     print("Instale: pip install psycopg2-binary")
     sys.exit(1)

class DatabaseHandler:
    """Gerencia a conexão e operações com o banco de dados PostgreSQL."""

    def __init__(self):
        """Armazena as configurações do banco de dados."""
        self.dbname = config.DB_NAME
        self.user = config.DB_USER
        self.password = config.DB_PASSWORD
        self.host = config.DB_HOST
        self.port = config.DB_PORT
        print("[DB Handler] Instância criada.")

    def connect(self) -> Optional[psycopg2.extensions.connection]:
        """
        Estabelece uma conexão com o banco de dados.

        Returns:
            Um objeto de conexão psycopg2 ou None em caso de erro.
        """
        if not config.check_db_config(): # Verifica se as configs estão carregadas
             return None
        try:
            print(f"[DB Handler] Conectando ao DB: host={self.host}, db={self.dbname}...")
            connection = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                connect_timeout=10 # Timeout de conexão (segundos)
            )
            print("[DB Handler] Conexão com o banco de dados estabelecida.")
            return connection
        except psycopg2.OperationalError as e:
            print(f"[DB Handler] Erro OPERACIONAL ao conectar: {e}")
            return None
        except psycopg2.Error as e:
            print(f"[DB Handler] Erro psycopg2 ao conectar: {e}")
            return None
        except Exception as e:
            print(f"[DB Handler] Erro INESPERADO ao conectar: {e}")
            return None

    def insert_reading(self, connection: psycopg2.extensions.connection, distancia: float, created_on_dt: datetime) -> bool:
        """
        Insere uma leitura na tabela 'leituras' usando a coluna 'created_on'.

        Args:
            connection: A conexão ativa com o banco de dados.
            distancia: O valor da distância (float).
            created_on_dt: O objeto datetime da leitura (vindo de 'created_on' do JSON).

        Returns:
            True se a inserção for bem-sucedida, False caso contrário.
        """
        if connection is None or connection.closed:
             print("  [DB Handler] Erro: Conexão com o banco de dados está fechada ou inválida.")
             return False

        cursor = None
        try:
            cursor = connection.cursor()
            # Usa a coluna "created_on" no SQL INSERT
            sql = "INSERT INTO leituras (distancia, created_on) VALUES (%s, %s);"
            cursor.execute(sql, (distancia, created_on_dt))
            connection.commit()
            print(f"  [DB Handler] Leitura inserida: Dist={distancia:.1f}, CreatedOn={created_on_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            return True
        except psycopg2.Error as e:
            print(f"  [DB Handler] Erro ao inserir leitura na coluna 'created_on': {e}")
            print(f"  SQL: {sql}, Dados: ({distancia}, {created_on_dt})") # Log extra
            if connection:
                try:
                    connection.rollback() # Desfaz a transação em caso de erro
                    print("  [DB Handler] Rollback realizado.")
                except psycopg2.Error as rb_err:
                     print(f"  [DB Handler] Erro durante o rollback: {rb_err}")
            return False
        except Exception as e:
            print(f"  [DB Handler] Erro inesperado na inserção: {e}")
            if connection:
                 try:
                    connection.rollback()
                    print("  [DB Handler] Rollback realizado.")
                 except psycopg2.Error as rb_err:
                     print(f"  [DB Handler] Erro durante o rollback: {rb_err}")
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except psycopg2.Error as cur_err:
                     print(f"  [DB Handler] Erro ao fechar cursor: {cur_err}")


    def close(self, connection: Optional[psycopg2.extensions.connection]):
        """Fecha a conexão com o banco de dados, se estiver aberta."""
        if connection and not connection.closed:
            try:
                connection.close()
                print("[DB Handler] Conexão com o banco de dados fechada.")
            except psycopg2.Error as e:
                print(f"[DB Handler] Erro psycopg2 ao fechar conexão: {e}")
            except Exception as e:
                print(f"[DB Handler] Erro inesperado ao fechar conexão: {e}")
        else:
            print("[DB Handler] Tentativa de fechar conexão já fechada ou nula.")