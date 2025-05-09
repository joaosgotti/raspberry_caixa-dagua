# database_handler.py

from datetime import datetime
from models import Leitura, Session
from sqlalchemy.exc import SQLAlchemyError

class DatabaseHandler:
    """Lida com a conexão e inserção no banco de dados PostgreSQL."""

    def insert_reading(self, distancia: float, created_on_dt: datetime) -> bool:
        """
        Insere uma leitura de distância na tabela 'leituras' usando SQLAlchemy ORM.
        """
        session = Session()  # Cria uma nova sessão para interagir com o banco de dados
        success = False
        try:
            nova_leitura = Leitura(distancia=distancia, created_on=created_on_dt)
            session.add(nova_leitura)
            session.commit()
            print(f"  [DB Handler] Inserção OK: Dist={distancia:.1f}, CreatedOn={created_on_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            success = True
        except SQLAlchemyError as e:
            print(f"  [DB Handler] ERRO ao inserir no DB: {e}")
            session.rollback()
        finally:
            session.close() # Certifique-se de fechar a sessão após a operação
        return success