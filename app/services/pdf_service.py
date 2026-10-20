
import os
import tempfile
from html import escape
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from app.database import supabase


def generar_pdf_y_guardar(
    solicitud_id: str,
    texto_contenido: str,
) -> str:
    """
    Genera un PDF con el contenido legal, lo sube a Supabase Storage
    y devuelve la URL pública del archivo.

    Args:
        solicitud_id: Identificador de la solicitud.
        texto_contenido: Texto del documento jurídico aprobado.

    Returns:
        URL del PDF almacenado en Supabase.

    Raises:
        ValueError: Si faltan datos obligatorios.
        RuntimeError: Si falla la generación o subida del PDF.
    """

    if not solicitud_id or not solicitud_id.strip():
        raise ValueError("El ID de la solicitud es obligatorio.")

    if not texto_contenido or not texto_contenido.strip():
        raise ValueError("El contenido del documento está vacío.")

    nombre_archivo = f"documento_{solicitud_id}.pdf"
    bucket_name = "documentos"
    ruta_local = None

    try:
        # 1. Crear un archivo temporal compatible con Windows y Linux
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            prefix=f"documento_{solicitud_id}_",
            delete=False,
        ) as archivo_temporal:
            ruta_local = archivo_temporal.name

        # 2. Configurar el documento PDF
        doc = SimpleDocTemplate(
            ruta_local,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
            title=f"Documento legal - Solicitud {solicitud_id}",
        )

        styles = getSampleStyleSheet()

        style_body = ParagraphStyle(
            "LegalBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            spaceAfter=8,
            alignment=0,
        )

        style_heading = ParagraphStyle(
            "LegalHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            spaceBefore=10,
            spaceAfter=8,
        )

        elements = []

        # 3. Convertir el texto en párrafos
        for linea in texto_contenido.splitlines():
            linea = linea.strip()

            if not linea:
                elements.append(Spacer(1, 8))
                continue

            # Interpretar encabezados Markdown sencillos
            if linea.startswith("#"):
                titulo = linea.lstrip("#").strip()
                elements.append(
                    Paragraph(escape(titulo), style_heading)
                )
                continue

            # Eliminar marcadores Markdown básicos
            linea = linea.replace("**", "")
            linea = linea.replace("__", "")
            linea = linea.replace("*", "")

            # Escapar caracteres especiales para ReportLab
            linea_segura = escape(linea)

            elements.append(
                Paragraph(linea_segura, style_body)
            )

        doc.build(elements)

        # 4. Leer el PDF generado
        with open(ruta_local, "rb") as archivo:
            contenido_pdf = archivo.read()

        if not contenido_pdf:
            raise RuntimeError("El PDF generado está vacío.")

        # 5. Subir el archivo a Supabase Storage
        respuesta = supabase.storage.from_(bucket_name).upload(
            path=nombre_archivo,
            file=contenido_pdf,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true",
            },
        )

        print(
            f"PDF generado y subido correctamente: {nombre_archivo}"
        )

        # 6. Obtener la URL pública del archivo
        url_publica = supabase.storage.from_(
            bucket_name
        ).get_public_url(nombre_archivo)

        if not url_publica:
            raise RuntimeError(
                "Supabase no devolvió la URL del documento."
            )

        return url_publica

    except Exception as e:
        print(
            f"Error generando o subiendo PDF: "
            f"{type(e).__name__}: {e}"
        )

        raise RuntimeError(
            "No fue posible generar o guardar el documento PDF."
        ) from e

    finally:
        # 7. Eliminar el archivo temporal incluso si ocurre un error
        if ruta_local and os.path.exists(ruta_local):
            try:
                os.remove(ruta_local)
            except OSError as e:
                print(
                    f"No se pudo eliminar el archivo temporal: {e}"
                )
