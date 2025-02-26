# main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base
from recommendation import get_recommendations

from fastapi.middleware.cors import CORSMiddleware

# Crear las tablas en la BD (si aún no están creadas)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Recomendación para Piano Adaptado")

origins = [
    "http://localhost:4200"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Important if you're using cookies or sessions
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)


# Dependency: obtener la sesión de la BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/recommendations/{user_id}")
def recommendations(user_id: int, db: Session = Depends(get_db)):
    try:
        recs = get_recommendations(user_id, db)
        return {"user_id": user_id, "recommendations": recs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint de prueba
@app.get("/")
def read_root():
    return {"message": "FastAPI con recomendador de canciones para piano adaptado"}
