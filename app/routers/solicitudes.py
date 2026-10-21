from typing import Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from app.schemas import SolicitudCreate, RevisionSolicitud
from app.database import supabase
from app.services.llm_service import generar_documento_legal_rctfv
from app.services.sms_service import enviar_notificacion
from app.services.pdf_service import generar_pdf_y_guardar

router = APIRouter()

# Schema para el envío de mensajes en el chat interno
class MensajePayload(BaseModel):
    emisor_id: str
    emisor_tipo: str = "ADMIN"  # 'ADMIN' o 'CIUDADANO'
    mensaje: str


@router.post("/")
def crear_solicitud(payload: SolicitudCreate):
    try:
        # 1. Buscar o crear al ciudadano en la tabla 'usuarios'
        res_usuario = supabase.table("usuarios")\
            .select("id")\
            .eq("telefono", payload.ciudadano.telefono)\
            .execute()

        if res_usuario.data:
            ciudadano_id = res_usuario.data[0]["id"]
        else:
            # Si el usuario no existe, lo creamos
            nuevo_usuario = supabase.table("usuarios").insert({
                "nombre": payload.ciudadano.nombre,
                "telefono": payload.ciudadano.telefono,
                "rol": "CIUDADANO"
            }).execute()
            ciudadano_id = nuevo_usuario.data[0]["id"]

        # 2. Insertar la solicitud inicial asociándola al ciudadano_id
        solicitud_resp = supabase.table("solicitudes").insert({
            "ciudadano_id": ciudadano_id,
            "tipo_ingreso": payload.tipo_ingreso,
            "tipo_tramite": payload.tipo_tramite,
            "problema_descripcion": payload.problema_descripcion,
            "estado": "EN_REVISION"
        }).execute()

        solicitud_id = solicitud_resp.data[0]["id"]

        # 3. Generar el borrador con la IA (Groq)
        borrador = generar_documento_legal_rctfv(
            tipo_tramite=payload.tipo_tramite,
            descripcion=payload.problema_descripcion,
            nombre_ciudadano=payload.ciudadano.nombre
        )

        print("DEBUG - TEXTO GENERADO POR IA:", borrador)

        # 4. Guardar el borrador en 'documentos_generados'
        supabase.table("documentos_generados").insert({
            "solicitud_id": solicitud_id,
            "tipo_documento": payload.tipo_tramite,
            "contenido_texto_ia": borrador
        }).execute()

        # 5. Retornar la respuesta con el borrador generado
        return {
            "mensaje": "Solicitud creada y enviada a revisión",
            "solicitud_id": solicitud_id,
            "estado": "EN_REVISION",
            "borrador_ia": borrador
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pendientes")
def listar_pendientes():
    res = supabase.table("solicitudes")\
        .select("*, usuarios!fk_ciudadano(nombre, telefono), documentos_generados(*)")\
        .eq("estado", "EN_REVISION")\
        .execute()
    return res.data


@router.post("/{solicitud_id}/revisar")
def revisar_solicitud(solicitud_id: str, payload: RevisionSolicitud):
    try:
        # 0. Obtener el texto a usar
        texto_a_usar = getattr(payload, "contenido_texto_aprobado", None)
        
        if not texto_a_usar or not texto_a_usar.strip():
            res_doc = supabase.table("documentos_generados")\
                .select("contenido_texto_ia")\
                .eq("solicitud_id", solicitud_id)\
                .execute()
            
            if res_doc.data:
                texto_a_usar = res_doc.data[0].get("contenido_texto_ia")
            
            if not texto_a_usar:
                raise HTTPException(
                    status_code=400, 
                    detail="No se encontró el borrador previo de la IA ni un texto aprobado."
                )

        # 1. Si el estado es APROBADO, generamos el PDF final
        pdf_url = None
        if payload.estado == "APROBADO":
            pdf_url = generar_pdf_y_guardar(solicitud_id, texto_a_usar)

        # 2. Actualizar la tabla 'solicitudes'
        supabase.table("solicitudes").update({"estado": payload.estado}).eq("id", solicitud_id).execute()

        # 3. Actualizar 'documentos_generados'
        datos_actualizacion = {
            "contenido_texto_revisado": texto_a_usar
        }
        if pdf_url:
            datos_actualizacion["archivo_pdf_url"] = pdf_url

        supabase.table("documentos_generados").update(datos_actualizacion).eq("solicitud_id", solicitud_id).execute()

        # 4. Notificar al ciudadano
        res_sol = supabase.table("solicitudes").select("*, usuarios!fk_ciudadano(id, nombre, telefono)").eq("id", solicitud_id).execute()
        ciudadano = res_sol.data[0]["usuarios"]

        msg = f"¡Hola {ciudadano['nombre']}! Tu documento legal fue APROBADO. Descárgalo aquí: {pdf_url}" if payload.estado == "APROBADO" else f"Hola {ciudadano['nombre']}, tu solicitud requiere observaciones/ajustes."
        
        enviar_notificacion(solicitud_id, ciudadano["telefono"], msg)

        # 5. Registrar el mensaje en la mensajería interna
        supabase.table("mensajes_solicitud").insert({
            "solicitud_id": solicitud_id,
            "emisor_tipo": "ADMIN",
            "emisor_id": payload.asesor_id if hasattr(payload, "asesor_id") and payload.asesor_id else "SISTEMA",
            "mensaje": msg
        }).execute()

        return {
            "mensaje": f"Solicitud {payload.estado} con éxito",
            "pdf_url": pdf_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# NUEVOS ENDPOINTS: CÉDULA Y MENSAJERÍA
# ==========================================

@router.post("/{solicitud_id}/subir-cedula")
def subir_cedula_ciudadano(solicitud_id: str, file: UploadFile = File(...)):
    """
    Sube la foto de la cédula a Supabase Storage y guarda su URL en la solicitud.
    """
    try:
        file_bytes = file.file.read()
        file_extension = file.filename.split(".")[-1]
        file_name = f"cedula_{solicitud_id}.{file_extension}"

        # Subir archivo al bucket 'cedulas'
        supabase.storage.from_("cedulas").upload(
            path=file_name,
            file=file_bytes,
            file_options={"content-type": file.content_type, "upsert": "true"}
        )

        # Obtener URL pública
        public_url_res = supabase.storage.from_("cedulas").get_public_url(file_name)
        cedula_url = public_url_res if isinstance(public_url_res, str) else public_url_res.get("publicUrl", "")

        # Actualizar la solicitud con la URL de la cédula
        supabase.table("solicitudes").update({
            "cedula_url": cedula_url
        }).eq("id", solicitud_id).execute()

        return {
            "mensaje": "Cédula subida con éxito",
            "cedula_url": cedula_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{solicitud_id}/mensajes")
def enviar_mensaje_solicitud(solicitud_id: str, payload: MensajePayload):
    """
    Permite a un Administrador o Ciudadano enviar mensajes/observaciones sobre la solicitud.
    """
    try:
        response = supabase.table("mensajes_solicitud").insert({
            "solicitud_id": solicitud_id,
            "emisor_tipo": payload.emisor_tipo,
            "emisor_id": payload.emisor_id,
            "mensaje": payload.mensaje
        }).execute()

        # Si el mensaje lo envía el ADMIN, podemos marcar opcionalmente la solicitud como OBSERVADO
        if payload.emisor_tipo == "ADMIN":
            supabase.table("solicitudes").update({"estado": "OBSERVADO"}).eq("id", solicitud_id).execute()

        return {
            "mensaje": "Mensaje enviado correctamente",
            "detalle": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{solicitud_id}/mensajes")
def obtener_historial_mensajes(solicitud_id: str):
    """
    Obtiene todo el historial de conversación/requerimientos asociados a la solicitud.
    """
    try:
        response = supabase.table("mensajes_solicitud")\
            .select("*")\
            .eq("solicitud_id", solicitud_id)\
            .order("creado_en", desc=False)\
            .execute()
            
        return {
            "mensajes": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))