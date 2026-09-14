"""
Análisis de imágenes con IA: el usuario adjunta una foto desde el panel
de chat y Claude la describe o responde preguntas sobre ella.

De cada imagen se generan DOS versiones, a propósito:
  - una miniatura chica, solo para mostrarla en el chat sin inflar la
    interfaz (el base64 viaja como string hacia JavaScript);
  - una versión optimizada más grande, la que se le manda a Claude,
    reducida para respetar sus límites de tamaño y no encarecer la
    llamada de más.

Ambas se convierten a JPEG para que el tipo de archivo mandado a la API
sea siempre el mismo, sin importar si el original era PNG, WEBP, etc.
"""

import base64
import io

from PIL import Image

import claude_api

EXTENSIONES_SOPORTADAS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")

_LADO_MAXIMO_MINIATURA = 320
_LADO_MAXIMO_ENVIO = 1568  # límite recomendado por Anthropic para imágenes
_CALIDAD_MINIATURA = 70
_CALIDAD_ENVIO = 85

def _a_jpeg_base64(imagen: Image.Image, lado_maximo: int, calidad: int) -> str:
    copia = imagen.copy()
    copia.thumbnail((lado_maximo, lado_maximo), Image.LANCZOS)

    # JPEG no soporta transparencia ni paletas: se normaliza a RGB para
    # que no truene con PNGs o GIFs.
    if copia.mode != "RGB":
        copia = copia.convert("RGB")

    memoria = io.BytesIO()
    copia.save(memoria, format="JPEG", quality=calidad, optimize=True)
    return base64.b64encode(memoria.getvalue()).decode("ascii")


def preparar(ruta: str):
    """Abre la imagen y regresa (miniatura_base64, envio_base64), o
    (None, None) si el archivo no se pudo leer como imagen."""
    try:
        with Image.open(ruta) as imagen:
            imagen.load()
            return (
                _a_jpeg_base64(imagen, _LADO_MAXIMO_MINIATURA, _CALIDAD_MINIATURA),
                _a_jpeg_base64(imagen, _LADO_MAXIMO_ENVIO, _CALIDAD_ENVIO),
            )
    except (OSError, ValueError) as error:
        print(f"[Venok] No pude leer la imagen: {error}")
        return None, None


def analizar(imagen_base64: str, pregunta: str, tono: str = "amigable",
             nombre_asistente: str = "Venok") -> str:
    """Le manda la imagen a Claude junto con la pregunta del usuario."""
    if not claude_api.hay_api_key():
        return "Para analizar imágenes necesito una ANTHROPIC_API_KEY configurada en tu archivo .env."

    pregunta = (pregunta or "").strip() or "¿Qué ves en esta imagen?"

    contenido = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": imagen_base64,
            },
        },
        {"type": "text", "text": pregunta},
    ]

    respuesta = claude_api.preguntar(
        contenido,
        sistema=claude_api.instruccion_de_sistema(tono, nombre_asistente),
        max_tokens=400,
    )
    if not respuesta:
        return "Vi la imagen, pero no pude analizarla en este momento. ¿Lo intentamos de nuevo?"

    # En el historial se guarda solo texto, nunca la imagen: reenviar el
    # base64 en cada pregunta siguiente saldría caro sin necesidad.
    claude_api.recordar_intercambio(
        f"(El usuario compartió una imagen y preguntó: {pregunta})", respuesta
    )
    return respuesta
