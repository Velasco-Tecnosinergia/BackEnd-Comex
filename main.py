from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
from requests.auth import HTTPDigestAuth
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

# Conexión a MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["passenger_flow"]

users_collection = db["users"]
statistics_collection = db["statistics"]


# -----------------------------
# 📌 MODELOS
# -----------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


# -----------------------------
# 📌 CREAR ADMIN SI NO EXISTE
# -----------------------------
@app.on_event("startup")
def startup_event():
    admin = users_collection.find_one({"username": "admin"})
    if not admin:
        users_collection.insert_one({
            "username": "admin",
            "email": "jair.velasco@tecnosinergia.com",
            "password": "Admin123.",
            "created_at": datetime.datetime.utcnow()
        })


@app.get("/")
def root():
    return {"message": "Backend funcionando 🚀"}


# -----------------------------
# 📌 LOGIN (desde Mongo)
# -----------------------------
@app.post("/login")
def login(request: LoginRequest):
    user = users_collection.find_one({"username": request.username})
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    return {"user": user["username"], "message": "Login exitoso"}


# -----------------------------
# 📌 FETCH DE ESTADÍSTICAS
# -----------------------------
@app.post("/statistics/fetch")
def fetch_statistics(request: LoginRequest):
    user = users_collection.find_one({"username": request.username})
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

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
            auth=HTTPDigestAuth(user["username"], user["password"]),
            timeout=10
        )
        #print(">>> PUT RESPONSE:", put_resp.text)  # 👈 DEBUG
        put_resp.raise_for_status()
        remote_response = put_resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PUT failed: {str(e)}")

    search_id = remote_response.get("Response", {}).get("Data", {}).get("SearchID")
    if not search_id:
        raise HTTPException(status_code=500, detail="No SearchID en respuesta del PUT")

    # Paso 2: GET Progress
    try:
        progress_resp = requests.get(
            f"{base_url}/Progress?SearchID={search_id}",
            auth=HTTPDigestAuth(user["username"], user["password"]),
            timeout=10
        )
        #print(">>> GET Progress:", progress_resp.text)  # 👈 DEBUG
        progress_resp.raise_for_status()
        progress_data = progress_resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GET Progress failed: {str(e)}")

    # Paso 3: si Percent == 100, hacemos GET Statistics
    percent = progress_data.get("Response", {}).get("Data", {}).get("Percent")
    stats_data = None

    if percent == 100:
        try:
            stats_resp = requests.get(
                f"{base_url}?SearchID={search_id}",
                auth=HTTPDigestAuth(user["username"], user["password"]),
                timeout=10
            )
            #print(">>> GET Statistics:", stats_resp.text)  # 👈 DEBUG
            stats_resp.raise_for_status()
            stats_data = stats_resp.json()

            # ✅ Guardar en Mongo
            statistics_collection.insert_one({
                "username": user["username"],
                "search_id": search_id,
                "percent": percent,
                "final_statistics": stats_data,
                "created_at": datetime.datetime.utcnow()
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"GET Statistics failed: {str(e)}")

    return {
        "search_id": search_id,
        "progress": progress_data,
        "final_statistics": stats_data
    }


# -----------------------------
# 📌 OBTENER ÚLTIMA ESTADÍSTICA
# -----------------------------
@app.get("/statistics/latest")
def get_latest_statistics():
    doc = statistics_collection.find_one(sort=[("created_at", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="No hay estadísticas aún")

    doc["_id"] = str(doc["_id"])  # convertir ObjectId a string
    return doc
