
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


# Buscar el archivo .env en la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path, override=True)


def generar_documento_legal_rctfv(
    tipo_tramite: str,
    descripcion: str,
    nombre_ciudadano: str,
) -> str:
    """
    Genera un borrador de documento jurídico colombiano mediante Groq.

    Args:
        tipo_tramite: DERECHO_PETICION o TUTELA.
        descripcion: Descripción de los hechos del ciudadano.
        nombre_ciudadano: Nombre completo del solicitante.

    Returns:
        Documento jurídico generado por el modelo de IA.

    Raises:
        ValueError: Si faltan datos obligatorios o la API key.
        RuntimeError: Si ocurre un error durante la generación.
    """

    # 1. Validar los datos de entrada
    if not tipo_tramite or not tipo_tramite.strip():
        raise ValueError("El tipo de trámite es obligatorio.")

    if not descripcion or not descripcion.strip():
        raise ValueError("La descripción de los hechos es obligatoria.")

    if not nombre_ciudadano or not nombre_ciudadano.strip():
        raise ValueError("El nombre del ciudadano es obligatorio.")

    tipo_tramite = tipo_tramite.strip().upper()
    descripcion = descripcion.strip()
    nombre_ciudadano = nombre_ciudadano.strip()

    # 2. Obtener las credenciales desde las variables de entorno
    api_key = os.getenv("GROQ_API_KEY")
    modelo = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    if not api_key:
        raise ValueError(
            f"GROQ_API_KEY no encontrada. Verifica el archivo: {env_path}"
        )

    # 3. Configurar el documento según el trámite
    if tipo_tramite == "DERECHO_PETICION":
        titulo_doc = "DERECHO DE PETICIÓN EN INTERÉS PARTICULAR"

        normativa_clave = (
            "Artículo 23 de la Constitución Política de Colombia, "
            "Ley 1755 de 2015 y demás normas pertinentes según "
            "la naturaleza del asunto."
        )

        estructura_tramite = """
1. Encabezado y destinatario.
2. Identificación del peticionario, cuando los datos estén disponibles.
3. Hechos y antecedentes.
4. Fundamentos jurídicos pertinentes.
5. Peticiones concretas y numeradas.
6. Anexos y pruebas, si fueron mencionados.
7. Notificaciones, cuando se disponga de los datos necesarios.
"""

    elif tipo_tramite == "TUTELA":
        titulo_doc = "ACCIÓN DE TUTELA"

        normativa_clave = (
            "Artículo 86 de la Constitución Política de Colombia, "
            "Decreto 2591 de 1991 y, cuando corresponda, "
            "Ley Estatutaria 1751 de 2015 en asuntos de salud."
        )

        estructura_tramite = """
1. Encabezado y autoridad judicial competente.
2. Identificación del accionante, con los datos disponibles.
3. Identificación de la entidad accionada, si está identificada.
4. Hechos numerados y cronológicos.
5. Derechos fundamentales presuntamente vulnerados.
6. Fundamentos jurídicos pertinentes.
7. Pretensiones concretas.
8. Manifestación bajo juramento, cuando corresponda.
9. Pruebas y anexos disponibles.
10. Notificaciones, si se dispone de los datos necesarios.
"""

    else:
        raise ValueError(
            "Tipo de trámite no válido. "
            "Usa DERECHO_PETICION o TUTELA."
        )

    # 4. Construir las instrucciones para la IA
    prompt = f"""
Redacta un borrador jurídico formal conforme al derecho colombiano.

DATOS DEL SOLICITANTE
Nombre: {nombre_ciudadano}
Tipo de trámite: {tipo_tramite}
Título del documento: {titulo_doc}

DESCRIPCIÓN DE LOS HECHOS
{descripcion}

NORMATIVA DE REFERENCIA
{normativa_clave}

ESTRUCTURA RECOMENDADA
{estructura_tramite}

INSTRUCCIONES OBLIGATORIAS

1. Redacta un documento claro, formal, coherente y organizado.
2. Utiliza todos los datos personales, fechas, nombres de entidades,
   números de identificación y demás información que aparezcan
   explícitamente en los datos proporcionados.
3. No inventes hechos, fechas, pruebas, documentos, datos personales,
   direcciones, teléfonos, correos, NIT ni representantes legales.
4. No inventes artículos legales, sentencias ni citas jurisprudenciales.
5. No agregues campos vacíos, líneas de guiones, líneas de subrayado
   ni marcadores como [COMPLETAR], [PENDIENTE] o similares.
6. Si no se proporciona un dato personal, omite ese campo.
   No escribas etiquetas sin información después de ellas.
7. Si la entidad destinataria no está identificada en los datos,
   no inventes su nombre ni sus datos de contacto.
8. No atribuyas a una entidad hechos que no estén respaldados por
   la descripción suministrada.
9. Organiza los hechos en orden cronológico cuando la información
   disponible permita hacerlo.
10. Formula solicitudes concretas que correspondan a los hechos.
11. Incluye únicamente las secciones pertinentes al caso.
12. No afirmes que un derecho fue vulnerado como hecho probado si
    requiere una valoración jurídica.
13. No agregues una firma ficticia ni inventes información para
    completar los requisitos de presentación.
14. No afirmes que el documento está listo para radicar si requiere
    datos adicionales, pruebas o verificaciones.
15. Devuelve únicamente el texto del documento jurídico, sin explicar
    las instrucciones ni añadir comentarios dirigidos al desarrollador.

IMPORTANTE:
El documento debe aprovechar toda la información realmente disponible.
Es preferible omitir un campo desconocido antes que dejar espacios vacíos
o presentar información inventada.

El resultado es un borrador que debe revisarse antes de su presentación.
"""

    # 5. Generar el documento mediante Groq
    try:
        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente especializado en redacción "
                        "jurídica colombiana. Elaboras borradores formales "
                        "y rigurosos utilizando exclusivamente los datos "
                        "disponibles. No inventas información personal, "
                        "hechos, normas ni jurisprudencia. No dejas campos "
                        "vacíos ni incluyes marcadores de información "
                        "pendiente. Si un dato no está disponible, "
                        "omites el campo correspondiente."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
            max_tokens=3000,
        )

        borrador_generado = response.choices[0].message.content

        if not borrador_generado or not borrador_generado.strip():
            raise ValueError("Groq devolvió una respuesta vacía.")

        print(
            ">>> DOCUMENTO GENERADO EXITOSAMENTE POR GROQ "
            f"({len(borrador_generado)} caracteres)"
        )

        return borrador_generado.strip()

    except Exception as e:
        print(f"ERROR EN GROQ: {type(e).__name__} - {e}")

        raise RuntimeError(
            "No fue posible generar el documento jurídico mediante IA."
        ) from e
