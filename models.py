# models.py

from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError # Para capturar erros do SQLAlchemy
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

print("[Models] Carregando variáveis de ambiente do arquivo .env...")
DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Leitura(Base):
    """
    Modelo SQLAlchemy que representa a tabela 'leituras'.
    """
    __tablename__ = 'leituras'  # Nome exato da sua tabela no banco de dados

    id = Column(Integer, primary_key=True, autoincrement=True) # Assumindo que você tem um ID autoincrementável
    distancia = Column(Float, nullable=False)
    created_on = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Leitura(id={self.id}, distancia={self.distancia}, created_on='{self.created_on}')>"

