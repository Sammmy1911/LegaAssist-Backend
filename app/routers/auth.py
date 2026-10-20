from fastapi import APIRouter, HTTPException
from app.schemas import RegistroUsuario, LoginUsuario
from app.database import supabase

router = APIRouter()

@router.post("/registro")
def registrar_usuario(payload: RegistroUsuario):
    try:
        # Generamos un UUID falso o usamos uno para pruebas y evitamos el bloqueo de Supabase Auth
        import uuid
        user_id = str(uuid.uuid4())

        # Insertar directamente en la tabla 'usuarios' de Supabase
        response = supabase.table("usuarios").insert({
            "id": user_id,
            "nombre": payload.nombre,
            "telefono": payload.telefono,
            "email": payload.email,
            "rol": payload.rol
        }).execute()

        return {
            "message": "Usuario registrado exitosamente (Modo Local/MVP)",
            "user_id": user_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login_usuario(payload: LoginUsuario):
    try:
        # Buscamos al usuario en la tabla 'usuarios' por su email
        response = supabase.table("usuarios").select("*").eq("email", payload.email).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Usuario no encontrado")
            
        usuario = response.data[0]
        
        # Como estamos en modo desarrollo local MVP, simulamos la generación de un token de acceso
        return {
            "access_token": "fake-jwt-token-para-desarrollo-local-12345",
            "token_type": "bearer",
            "usuario": {
                "id": usuario["id"],
                "nombre": usuario["nombre"],
                "rol": usuario["rol"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))