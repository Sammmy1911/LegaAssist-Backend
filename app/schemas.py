from pydantic import BaseModel, EmailStr
from typing import Optional, Literal

class RegistroUsuario(BaseModel):
    nombre: str
    telefono: str
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    rol: Literal["CIUDADANO", "GESTOR_COMUNITARIO", "ADMIN"] = "CIUDADANO"

class LoginUsuario(BaseModel):
    email: EmailStr
    password: str

class CiudadanoCreate(BaseModel):
    nombre: str
    telefono: str

class SolicitudCreate(BaseModel):
    tipo_ingreso: Literal["AUTOSERVICIO", "ASISTIDO"]
    gestor_id: Optional[str] = None
    ciudadano: CiudadanoCreate
    tipo_tramite: Literal["DERECHO_PETICION", "TUTELA", "LIQUIDACION", "CONTRATO"]
    problema_descripcion: str

class RevisionSolicitud(BaseModel):
    asesor_id: str
    contenido_texto_aprobado: str
    estado: Literal["APROBADO", "RECHAZADO"]