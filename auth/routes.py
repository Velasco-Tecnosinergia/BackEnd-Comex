from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Modelo de login
class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(data: LoginRequest):
    if data.email == "admin" and data.password == "1234":
        return {"message": "Login exitoso 🎉", "token": "fake-jwt-token"}
    else:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
