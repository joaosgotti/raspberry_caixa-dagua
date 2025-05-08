# database_handler.py
import psycopg2 
import config
from datetime import datetime, timezone

# --- Imports do SQLAlchemy ---
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError # Para capturar erros do SQLAlchemy

# --- Definição do Modelo SQLAlchemy ---
Base = declarative_base()

class Leitura(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'leituras'.
    """
    __tablename__ = 'leituras'  # Nome exato da sua tabela no banco de dados

    id = Column(Integer, primary_key=True, autoincrement=True) # Assumindo que você tem um ID autoincrementável
    distancia = Column(Float, nullable=False)
    created_on = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Leitura(id={self.id}, distancia={self.distancia}, created_on='{self.created_on}')>"


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