from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import supabase

# ⚠️ SIN PREFIJO AQUÍ (déjalo completamente vacío)
router = APIRouter()

class LoginRequest(BaseModel):
    cedula: str

class RegistroRequest(BaseModel):
    nombre: str
    cedula: str
    telefono: str = None
    rol: str = "CIUDADANO"

@router.post("/registro")
def registrar_usuario(data: RegistroRequest):
    try:
        existente = supabase.table("usuarios").select("id").eq("cedula", data.cedula).execute()
        if existente.data:
            raise HTTPException(status_code=400, detail="Ya existe un usuario registrado con esta cédula.")

        response = supabase.table("usuarios").insert({
            "nombre": data.nombre,
            "cedula": data.cedula,
            "telefono": data.telefono,
            "rol": data.rol
        }).execute()
        
        return {"mensaje": "Usuario registrado con éxito", "usuario": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login_usuario(data: LoginRequest):
    try:
        response = supabase.table("usuarios").select("*").eq("cedula", data.cedula).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="No se encontró un usuario registrado con esta cédula.")
            
        usuario = response.data[0]
        return {"mensaje": "Login exitoso", "usuario": usuario}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))