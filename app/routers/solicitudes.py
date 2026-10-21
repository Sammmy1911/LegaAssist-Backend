from typing import Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, Query, Form
from pydantic import BaseModel
from app.schemas import RevisionSolicitud
from app.database import supabase
from app.services.llm_service import generar_documento_legal_rctfv
from app.services.sms_service import enviar_notificacion
from app.services.pdf_service import generar_pdf_y_guardar

router = APIRouter(tags=["solicitudes"])

# Schema para el envío de mensajes en el chat interno
class MensajePayload(BaseModel):
    emisor_id: str
    emisor_tipo: str = "ADMIN"  # 'ADMIN' o 'CIUDADANO'
    mensaje: str


@router.post("/")
def crear_solicitud(
    cedula_usuario: str = Form(...),
    tipo_tramite: str = Form(...),
    problema_descripcion: str = Form(...),
    telefono_contacto: Optional[str] = Form(None),
    tipo_ingreso: Optional[str] = Form("WEB"),
    file_cedula: Optional[UploadFile] = File(None)
):
    try:
        # 1. Buscar al ciudadano en la tabla 'usuarios' utilizando su cédula
        res_usuario = supabase.table("usuarios")\
            .select("id, nombre, telefono")\
            .eq("cedula", cedula_usuario)\
            .execute()

        if not res_usuario.data:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontró ningún usuario registrado con la cédula {cedula_usuario}. Por favor, regístralo primero."
            )

        usuario_ciudadano = res_usuario.data[0]
        ciudadano_id = usuario_ciudadano["id"]

        # 2. Insertar la solicitud inicial asociándola al ciudadano_id
        solicitud_resp = supabase.table("solicitudes").insert({
            "ciudadano_id": ciudadano_id,
            "tipo_ingreso": tipo_ingreso,
            "tipo_tramite": tipo_tramite,
            "problema_descripcion": problema_descripcion,
            "estado": "EN_REVISION"
        }).execute()

        solicitud_id = solicitud_resp.data[0]["id"]

        # 3. Si se adjuntó la foto de la cédula, subirla a Supabase Storage y guardar la URL
        cedula_url = None
        if file_cedula:
            file_bytes = file_cedula.file.read()
            file_extension = file_cedula.filename.split(".")[-1]
            file_name = f"cedula_{solicitud_id}.{file_extension}"

            # Subir archivo al bucket 'cedulas'
            supabase.storage.from_("cedulas").upload(
                path=file_name,
                file=file_bytes,
                file_options={"content-type": file_cedula.content_type, "upsert": "true"}
            )

            # Obtener URL pública de la cédula
            public_url_res = supabase.storage.from_("cedulas").get_public_url(file_name)
            cedula_url = public_url_res if isinstance(public_url_res, str) else public_url_res.get("publicUrl", "")

            # Actualizar la solicitud con la URL de la cédula
            supabase.table("solicitudes").update({
                "cedula_url": cedula_url
            }).eq("id", solicitud_id).execute()

        # 4. Generar el borrador legal con la IA (Groq) utilizando el nombre real del ciudadano
        borrador = generar_documento_legal_rctfv(
            tipo_tramite=tipo_tramite,
            descripcion=problema_descripcion,
            nombre_ciudadano=usuario_ciudadano["nombre"]
        )

        print("DEBUG - TEXTO GENERADO POR IA:", borrador)

        # 5. Guardar el borrador en 'documentos_generados'
        supabase.table("documentos_generados").insert({
            "solicitud_id": solicitud_id,
            "tipo_documento": tipo_tramite,
            "contenido_texto_ia": borrador
        }).execute()

        # 6. Retornar la respuesta con el borrador generado
        return {
            "mensaje": "Solicitud creada y enviada a revisión con éxito",
            "solicitud_id": solicitud_id,
            "estado": "EN_REVISION",
            "cedula_url": cedula_url,
            "borrador_ia": borrador
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pendientes")
def listar_pendientes():
    res = supabase.table("solicitudes")\
        .select("*, usuarios!fk_ciudadano(nombre, telefono, cedula), documentos_generados(*)")\
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

        # 4. Obtener datos del ciudadano de forma segura (evitando errores de join en Supabase)
        res_sol = supabase.table("solicitudes").select("*").eq("id", solicitud_id).execute()
        solicitud_data = res_sol.data[0]
        cedula_usuario = solicitud_data.get("cedula_usuario")

        # Consultar la tabla usuarios usando la cédula o el id correspondiente
        res_user = supabase.table("usuarios").select("*").eq("cedula", cedula_usuario).execute()
        ciudadano = res_user.data[0] if res_user.data else {"nombre": "Ciudadano", "telefono": "3005676789"}

        # 5. Construir mensaje según el estado
        if payload.estado == "APROBADO":
            msg = f"¡Hola {ciudadano.get('nombre', 'Ciudadano')}! Tu documento legal fue APROBADO. Descárgalo aquí: {pdf_url}"
        else:
            msg = f"Hola {ciudadano.get('nombre', 'Ciudadano')}, tu solicitud presenta observaciones o requiere ajustes por parte del operador."
        
        enviar_notificacion(solicitud_id, ciudadano.get("telefono", ""), msg)
        UUID_SISTEMA_DEFAULT = "00000000-0000-0000-0000-000000000000"
        asesor_id_raw = getattr(payload, "asesor_id", None)
        emisor_id_valido = UUID_SISTEMA_DEFAULT
        
        if asesor_id_raw and isinstance(asesor_id_raw, str) and len(asesor_id_raw) == 36 and "-" in asesor_id_raw:
            emisor_id_valido = asesor_id_raw
        # 6. Registrar el mensaje en la mensajería interna
        supabase.table("mensajes_solicitud").insert({
            "solicitud_id": solicitud_id,
            "emisor_tipo": "ADMIN",
            "emisor_id": emisor_id_valido,           
            "mensaje": msg
        }).execute()

        return {
            "mensaje": f"Solicitud {payload.estado} con éxito",
            "pdf_url": pdf_url
        }

    except Exception as e:
        print(f"🔥 ERROR CRÍTICO EN /revisar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno en revisión: {str(e)}")

@router.post("/{solicitud_id}/subir-cedula")
def subir_cedula_ciudadano(solicitud_id: str, file: UploadFile = File(...)):
    """
    Sube la foto de la cédula a Supabase Storage y guarda su URL en la solicitud por separado.
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

        # Si el mensaje lo envía el ADMIN, marcamos opcionalmente la solicitud como OBSERVADO
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

@router.get("/")
def listar_solicitudes(
    usuario_query: Optional[str] = Query(
        None,
        description="Filtrar por nombre o teléfono",
    ),
    estado: Optional[str] = Query(
        None,
        description="Filtrar por estado",
    ),
):
    try:
        # 📍 SOLUCIÓN: Agregamos documentos_generados(archivo_pdf_url) a la consulta
        consulta = supabase.table("solicitudes").select(
            "*, usuarios!fk_ciudadano(nombre, telefono, cedula), documentos_generados(archivo_pdf_url)"
        )

        # Filtrar por estado
        if estado:
            consulta = consulta.eq("estado", estado)

        # Ejecutar la consulta
        respuesta = consulta.execute()
        solicitudes = respuesta.data or []

        # Filtrar por nombre, teléfono o cédula
        if usuario_query:
            busqueda = usuario_query.strip().casefold()

            solicitudes = [
                solicitud
                for solicitud in solicitudes
                if busqueda in str(
                    (solicitud.get("usuarios") or {}).get("nombre") or ""
                ).casefold()
                or busqueda in str(
                    (solicitud.get("usuarios") or {}).get("telefono") or ""
                ).casefold()
                or busqueda in str(
                    (solicitud.get("usuarios") or {}).get("cedula") or ""
                ).casefold()
            ]

        # Ordenar por fecha de creación, de más reciente a más antigua
        solicitudes.sort(
            key=lambda solicitud: solicitud.get("created_at") or "",
            reverse=True,
        )

        return solicitudes

    except Exception as e:
        print(f"🔥 ERROR AL LISTAR SOLICITUDES: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))