# models.py
from sqlalchemy import Column, Integer, String, Float, Date
from database import Base

class CancionInfo(Base):
    __tablename__ = "cancion_info"  # Asegúrate de que el nombre coincide (puede ser "Cancion_Info")
    
    id_cancion_info = Column(Integer, primary_key=True, index=True, autoincrement=True)
    idCancionId = Column(Integer, index=True)  # ID de la canción (relación)
    nombre = Column(String(255))
    numero_total_notas = Column(Integer)
    densidad_notas = Column(Float)
    cantidad_saltos_grandes = Column(Integer)
    notas_mano_izquierda = Column(Integer)
    notas_mano_derecha = Column(Integer)
    tuplets = Column(Integer)
    compositor = Column(String(255))


class Intento(Base):
    __tablename__ = "Intentos"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_cancion = Column(Integer, index=True)
    id_usuario = Column(Integer, index=True)
    id_calificacion = Column(Integer)  # Valores 1-5; 6 significa “no calificó”
    notas_correctas_max = Column(Integer, nullable=True)
    notas_incorrectas_max = Column(Integer, nullable=True)
    porcentaje_aciertos = Column(Float, nullable=True)  
    porcentaje_error = Column(Float, nullable=True)
    porcentaje_completado = Column(Float, nullable=True) # 1 si se completo el acierto, 0 si no.
    fecha = Column(Date)
