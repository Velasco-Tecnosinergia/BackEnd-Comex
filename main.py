from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import User

app = FastAPI()

# Crear las tablas
Base.metadata.create_all(bind=engine)

# Insertar usuario admin si no existe
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

# Ejecutamos al inicio
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    create_admin(db)

@app.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password != password:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return {"message": "Login exitoso 🎉", "user": user.username}
