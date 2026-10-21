from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import solicitudes, auth

app = FastAPI(title="JurisBot Rural API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lega-assist-fron-end.vercel.app",  # Tu frontend en Vercel
        "http://localhost:5173",                     # Tu frontend local (si usas Vite por defecto)
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(solicitudes.router, prefix="/api/solicitudes", tags=["Solicitudes"])
@app.get("/")
def root():
    return {"status": "ok", "message": "JurisBot Rural API corriendo en Windows"}