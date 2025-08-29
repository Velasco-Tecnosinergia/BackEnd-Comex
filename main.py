from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import engine, Base, get_db
from models import User

app = FastAPI()

# 🚀 Middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # ⚡ solo este
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas
Base.metadata.create_all(bind=engine)

# Modelo de request (lo que recibimos del frontend)
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
    return {"message": "Login exitoso 🎉", "user": user.username}
