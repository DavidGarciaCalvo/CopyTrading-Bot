from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import Config

Base = declarative_base()

class Operacion(Base):
    __tablename__ = 'operaciones'

    id = Column(Integer, primary_key=True)
    asset = Column(String)
    side = Column(String, default="LONG")
    precio_entrada = Column(Float)
    cantidad_usdt = Column(Float)
    sl = Column(Float)
    tp = Column(Float)
    status = Column(String) # OPEN, CLOSED_SL, CLOSED_TP
    fecha_apertura = Column(DateTime, default=datetime.utcnow)
    fecha_cierre = Column(DateTime, nullable=True)
    resultado_neto = Column(Float, default=0.0)
    signature_solana = Column(String)

# Usamos la URL que definiste en Config (la que usa Pathlib)
engine = create_engine(Config.DB_URL)
Session = sessionmaker(bind=engine)

def inicializar_db():
    Base.metadata.create_all(engine)
    print("🗄️ Base de Datos sincronizada y lista.")