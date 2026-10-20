from app.database import supabase

def enviar_notificacion(solicitud_id: str, telefono: str, mensaje: str):
    print(f"📱 [NOTIFICACIÓN ENVIADA A {telefono}]: {mensaje}")

    supabase.table("notificaciones").insert({
        "solicitud_id": solicitud_id,
        "canal": "WHATSAPP",
        "mensaje": mensaje,
        "estado_envio": "ENVIADO"
    }).execute()