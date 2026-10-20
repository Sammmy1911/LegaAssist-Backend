from fastapi import APIRouter, HTTPException
from app.schemas import SolicitudCreate, RevisionSolicitud
from app.database import supabase
from app.services.llm_service import generar_documento_legal_rctfv
from app.services.sms_service import enviar_notificacion
from app.services.pdf_service import generar_pdf_y_guardar

router = APIRouter()

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
        # 0. Obtener el texto a usar: si el asesor envió un texto editado, se usa ese.
        # Si viene vacío o no se envió, buscamos automáticamente el borrador que hizo la IA.
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

        # 1. Si el estado es APROBADO, generamos el PDF final usando el texto obtenido
        pdf_url = None
        if payload.estado == "APROBADO":
            pdf_url = generar_pdf_y_guardar(solicitud_id, texto_a_usar)

        # 2. Actualizar la tabla 'solicitudes'
        supabase.table("solicitudes").update({"estado": payload.estado}).eq("id", solicitud_id).execute()

        # 3. Actualizar 'documentos_generados' con el texto y la URL del PDF
        datos_actualizacion = {
            "contenido_texto_revisado": texto_a_usar
        }
        if pdf_url:
            datos_actualizacion["archivo_pdf_url"] = pdf_url

        supabase.table("documentos_generados").update(datos_actualizacion).eq("solicitud_id", solicitud_id).execute()

        # 4. Notificar al ciudadano por SMS/WhatsApp
        res_sol = supabase.table("solicitudes").select("*, usuarios!fk_ciudadano(nombre, telefono)").eq("id", solicitud_id).execute()
        ciudadano = res_sol.data[0]["usuarios"]

        msg = f"¡Hola {ciudadano['nombre']}! Tu documento legal fue APROBADO. Descárgalo aquí: {pdf_url}" if payload.estado == "APROBADO" else f"Hola {ciudadano['nombre']}, tu solicitud requiere ajustes."
        
        enviar_notificacion(solicitud_id, ciudadano["telefono"], msg)

        return {
            "mensaje": f"Solicitud {payload.estado} con éxito",
            "pdf_url": pdf_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))