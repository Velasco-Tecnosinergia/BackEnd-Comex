from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import engine, Base, get_db
from models import User
import requests
from requests.auth import HTTPDigestAuth

app = FastAPI()

# 🚀 Middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas
Base.metadata.create_all(bind=engine)

# Modelo de request
class LoginRequest(BaseModel):
    username: str
    password: str

# Insertar admin si no existe
def create_admin(db: Session):
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        new_admin = User(
            username="admin",
            email="jair.velasco@tecnosinergia.com",
            password="Admin123."
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

@app.on_event("startup")
def startup_event():
    db = next(get_db())
    create_admin(db)

@app.get("/")
def root():
    return {"message": "Backend funcionando 🚀"}

@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or user.password != request.password:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # JSON 1
    credentials = {
        "user": user.username,
        "password": user.password
    }

    # JSON 2
    statistics = {
        "Num": 16,
        "IDs": [i for i in range(1, 17)],
        "StatisticsType": 2,
        "StatisticsUnit": 2,
        "Begin": 1756274400,
        "End": 1756360800
    }

    # URL del PUT con Digest Auth
    url = "http://201.139.102.51:9191/LAPI/V1.0/Channels/Smart/PassengerFlowStatistics/CustomTimeStart"

    try:
        response = requests.put(
            url,
            json=statistics,
            auth=HTTPDigestAuth(user.username, user.password),
            timeout=10
        )
        response.raise_for_status()
        remote_response = response.json() if response.headers.get("content-type") == "application/json" else response.text
    except Exception as e:
        remote_response = {"error": str(e)}

    # Retornamos todo junto
    return {
        "credentials": credentials,
        "statistics": statistics,
        "remote_response": remote_response
    }
