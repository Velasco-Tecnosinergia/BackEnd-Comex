from fastapi import FastAPI
from auth.routes import router as auth_router

app = FastAPI(title="Backend Login")

# Rutas de autenticación
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

@app.get("/")
def root():
    return {"message": "API funcionando ✅"}
