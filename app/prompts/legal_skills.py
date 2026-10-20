# app/prompts/legal_skills.py

SKILL_DERECHO_PETICION = """
[ESTRUCTURA DETALLADA OBLIGATORIA PARA DERECHO DE PETICIÓN]
1. ENCABEZADO Y DESTINATARIO
   - Nombre de la Entidad o Empresa accionado.
   - Referencia: DERECHO DE PETICIÓN EN INTERÉS PARTICULAR (Art. 23 C.P. y Ley 1755 de 2015).

2. IDENTIFICACIÓN DEL PETICIONARIO
   - Nombre completo, documento de identidad, lugar de residencia y calidad en la que actúa.

3. HECHOS Y ANTECEDENTES (Escribir en orden cronológico, claro y detallado)
   - Detalle de la situación, fechas exactas si las hay, incumplimientos ocobros indebidos.

4. FUNDAMENTOS JURÍDICOS Y MARCO LEGAL
   - Artículo 23 de la Constitución Política de Colombia.
   - Ley 1755 de 2015 (Reglamentación del Derecho de Petición).
   - Ley 142 de 1994 (Si aplica a Servicios Públicos Domiciliarios, Arts. 152, 154, 158 sobre respuesta oportuna y debido proceso).
   - Jurisprudencia de la Corte Constitucional sobre el derecho fundamental de petición (Sentencia T-487/17, C-951/14).

5. PETICIONES CONCRETAS (Numeradas y redactadas en tono formal)
   - Solicitar respuesta clara, precisa y de fondo.
   - Solicitar visitas técnicas, reliquidaciones o inspecciones si aplica.

6. ANEXOS Y PRUEBAS
   - Copia de facturas, cédula, peticiones previas sin responder.

7. NOTIFICACIONES Y FIRMA
"""

SKILL_TUTELA = """
[ESTRUCTURA DETALLADA OBLIGATORIA PARA ACCIÓN DE TUTELA]
1. ENCABEZADO: Señor Juez Promiscuo Municipal / Civil del Circuito (Reparto).
2. ACCIONANTE Y ACCIONADO.
3. DERECHOS FUNDAMENTALES VULNERADOS: Salud (Ley 1751/2015), Vida Digna (Art. 11 C.P.), Minimum Vital, Mínimo de Subsistencia, Mínimo de Dignidad.
4. HECHOS CRONOLÓGICOS Y DETALLADOS.
5. PROCEDIBILIDAD Y SUBSIDIARIEDAD (Explicar por qué no hay otro medio de defensa o existe un perjuicio irremediable).
6. FUNDAMENTOS DE DERECHO Y JURISPRUDENCIA APLICABLE (Sentencia T-760 de 2008, Artículos 11, 48, 49 de la C.P.).
7. PRETENSIONES Y MEDIDA CAUTELAR / PROVISIONAL (Si aplica).
8. JURAMENTO DE NO HABER PRESENTADO OTRA TUTELA POR LOS MISMOS HECHOS.
9. NOTIFICACIONES Y FIRMA.
"""

SYSTEM_LEGAL_DESIGN_PROMPT = """
Eres un abogado experto en Derecho Constitucional Colombiano y Legal Design.
Tu objetivo es redactar escritos jurídicos completos, extensos, rigurosos y formalmente válidos en Colombia.
NO resumas ni omitas secciones. Debes desarrollar en profundidad cada uno de los acápites exigidos por la plantilla del trámite.
"""