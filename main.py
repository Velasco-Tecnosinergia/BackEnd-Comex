from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import engine, Base, get_db
from models import User
import requests
from requests.auth import HTTPDigestAuth
from pymongo import MongoClient
import datetime

app = FastAPI()

# 🚀 Middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas SQL (para usuarios)
Base.metadata.create_all(bind=engine)

# Conexión a MongoDB (para estadísticas)
client = MongoClient("mongodb://localhost:27017/")
db = client["passenger_flow"]
statistics_collection = db["statistics"]

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

    credentials = {"user": user.username, "password": user.password}

    statistics = {
        "Num": 16,
        "IDs": [i for i in range(1, 17)],
        "StatisticsType": 2,
        "StatisticsUnit": 2,
        "Begin": 1756274400,
        "End": 1756360800
    }

    base_url = "http://201.139.102.51:9191/LAPI/V1.0/Channels/Smart/PassengerFlowStatistics"

    # Paso 1: PUT para generar SearchID
    try:
        put_resp = requests.put(
            f"{base_url}/CustomTimeStart",
            json=statistics,
            auth=HTTPDigestAuth(user.username, user.password),
            timeout=10
        )
        put_resp.raise_for_status()
        remote_response = put_resp.json()
    except Exception as e:
        return {"error": f"PUT failed: {str(e)}"}

    search_id = remote_response.get("Response", {}).get("Data", {}).get("SearchID")
    if not search_id:
        return {"error": "No SearchID en respuesta del PUT", "remote_response": remote_response}

    # Paso 2: GET Progress
    try:
        progress_resp = requests.get(
            f"{base_url}/Progress?SearchID={search_id}",
            auth=HTTPDigestAuth(user.username, user.password),
            timeout=10
        )
        progress_resp.raise_for_status()
        progress_data = progress_resp.json()
    except Exception as e:
        return {
            "remote_response": remote_response,
            "error": f"GET Progress failed: {str(e)}"
        }

    # Paso 3: si Percent == 100, hacemos GET Statistics
    percent = progress_data.get("Response", {}).get("Data", {}).get("Percent")
    stats_data = None

    if percent == 100:
        try:
            stats_resp = requests.get(
                f"{base_url}?SearchID={search_id}",
                auth=HTTPDigestAuth(user.username, user.password),
                timeout=10
            )
            stats_resp.raise_for_status()
            stats_data = stats_resp.json()

            # ✅ Guardar en Mongo
            statistics_collection.insert_one({
                "username": user.username,
                "search_id": search_id,
                "percent": percent,
                "final_statistics": stats_data,
                "created_at": datetime.datetime.utcnow()
            })

        except Exception as e:
            stats_data = {"error": f"GET Statistics failed: {str(e)}"}

    return {
        "credentials": credentials,
        "statistics": statistics,
        "remote_response": remote_response,
        "progress_response": progress_data,
        "final_statistics": stats_data
    }

# ✅ Endpoint para obtener la última estadística guardada
@app.get("/statistics/latest")
def get_latest_statistics():
    doc = statistics_collection.find_one(sort=[("created_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="No hay estadísticas aún")

    doc["_id"] = str(doc["_id"])  # convertir ObjectId a string
    return doc
