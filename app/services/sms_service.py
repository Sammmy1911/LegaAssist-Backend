import os
from twilio.rest import Client
from app.database import supabase

def enviar_notificacion(solicitud_id: str, telefono: str, mensaje: str, canal: str = "WHATSAPP"):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    # Si no hay credenciales de Twilio configuradas, hacemos un mock en consola
    if not account_sid or not auth_token or account_sid == "tu_account_sid_de_twilio":
        print(f"\n📱 [MOCK WHATSAPP A {telefono}]: {mensaje}\n")
    else:
        try:
            client = Client(account_sid, auth_token)
            
            # Asegurar formato correcto para WhatsApp (ej: whatsapp:+573001234567)
            formatted_phone = telefono if telefono.startswith("whatsapp:") else f"whatsapp:{telefono}"

            message = client.messages.create(
                body=mensaje,
                from_=twilio_number,
                to=formatted_phone
            )
            print(f"✅ [WHATSAPP REAL ENVIADO] SID: {message.sid}")
        except Exception as e:
            print(f"⚠️ [ERROR ENVIANDO WHATSAPP REAL]: {str(e)}")

    # Registrar siempre la traza en la base de datos (Supabase)
    try:
        supabase.table("notificaciones").insert({
            "solicitud_id": solicitud_id,
            "canal": canal,
            "mensaje": mensaje,
            "estado_envio": "ENVIADO"
        }).execute()
    except Exception as db_error:
        print(f"⚠️ [ERROR BD NOTIFICACIONES]: {str(db_error)}")