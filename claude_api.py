"""
Cliente compartido de la API de Claude (Anthropic).

Vive en su propio módulo para que tanto navegador_ia.py (texto) como
imagen_ia.py (imagen + texto) usen la MISMA llamada HTTP y el MISMO
modelo. Si algún día hay que cambiar el modelo, los reintentos o el
límite de tokens, se cambia aquí y no en dos lugares que se
desincronizan.

Requiere ANTHROPIC_API_KEY en el .env (ver config.py).
"""

import re

import requests

from config import ANTHROPIC_API_KEY

MODELO = "claude-haiku-4-5-20251001"

_URL = "https://api.anthropic.com/v1/messages"
_VERSION_API = "2023-06-01"

# Últimos turnos de conversación, para que Venok entienda preguntas de
# seguimiento ("¿y de los perros?"). Vive solo en memoria: al cerrar Venok
# se empieza de cero. Se guardan pocos turnos a propósito, porque cada
# mensaje viejo se reenvía en la siguiente pregunta y cuesta tokens.
_historial = []
_MAXIMO_MENSAJES = 8  # 4 intercambios (pregunta + respuesta)

_DESCRIPCION_TONO = {
    "formal": "formal y respetuoso, tratando de usted",
    "amigable": "cercano y amable",
    "gracioso": "divertido y con humor ligero",
}


def hay_api_key() -> bool:
    return bool(ANTHROPIC_API_KEY)


def _limpiar_para_voz(texto: str) -> str:
    """Quita el formato Markdown que el modelo a veces devuelve. Leído en voz
    alta, un '#' o unos asteriscos suenan a ruido, y en el chat se ven feos."""
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)   # títulos
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)                  # negritas
    texto = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"\1", texto)      # cursivas
    texto = texto.replace("`", "")                                   # código
    texto = re.sub(r"^\s*[-•]\s+", "", texto, flags=re.MULTILINE)   # viñetas
    texto = re.sub(r"\s*\n+\s*", " ", texto)                         # todo en un párrafo
    return re.sub(r"\s{2,}", " ", texto).strip()


def instruccion_de_sistema(tono: str = "amigable", nombre_asistente: str = "Venok") -> str:
    """La personalidad de Venok, para mandarla como instrucción de sistema en
    vez de repetirla dentro de cada pregunta."""
    estilo = _DESCRIPCION_TONO.get(tono, _DESCRIPCION_TONO["amigable"])
    return (
        f"Eres {nombre_asistente}, un asistente de voz de escritorio. Responde "
        f"en español, en un tono {estilo}, de forma breve (2 a 4 oraciones) "
        f"porque tu respuesta se leerá en voz alta."
    )


def obtener_historial() -> list:
    return list(_historial)


def recordar_intercambio(pregunta: str, respuesta: str) -> None:
    _historial.append({"role": "user", "content": pregunta})
    _historial.append({"role": "assistant", "content": respuesta})
    del _historial[:-_MAXIMO_MENSAJES]


def limpiar_historial() -> None:
    _historial.clear()


def preguntar_con_herramientas(pregunta: str, herramientas: list, sistema: str = None,
                               max_tokens: int = 400, timeout: int = 25,
                               historial: list = None):
    """Le ofrece a Claude una lista de herramientas (las capacidades de Venok)
    y lo deja decidir si usar una o simplemente responder hablando.

    Regresa (nombre_herramienta, argumentos) si eligió una herramienta, o
    (None, texto) si prefirió contestar con palabras. Si algo falla regresa
    (None, None) para que quien llame use su propio respaldo.
    """
    if not ANTHROPIC_API_KEY:
        return None, None

    cuerpo = {
        "model": MODELO,
        "max_tokens": max_tokens,
        "tools": herramientas,
        "messages": list(historial or []) + [{"role": "user", "content": pregunta}],
    }
    if sistema:
        cuerpo["system"] = sistema

    try:
        resp = requests.post(
            _URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": _VERSION_API,
                "content-type": "application/json",
            },
            json=cuerpo,
            timeout=timeout,
        )
        resp.raise_for_status()
        bloques = resp.json().get("content", [])
    except (requests.exceptions.RequestException, ValueError) as error:
        print(f"[Venok] Error consultando a Claude con herramientas: {error}")
        return None, None

    for bloque in bloques:
        if bloque.get("type") == "tool_use":
            return bloque.get("name"), bloque.get("input", {})

    textos = [b.get("text", "") for b in bloques if b.get("type") == "text"]
    texto = _limpiar_para_voz(" ".join(textos)) if textos else None
    return None, (texto or None)


def preguntar(contenido, sistema: str = None, max_tokens: int = 300,
              timeout: int = 20, historial: list = None):
    """Manda un mensaje a Claude y regresa su respuesta como texto.

    `contenido` puede ser:
      - un string, para una pregunta de solo texto, o
      - una lista de bloques (ej. [{"type": "image", ...}, {"type": "text", ...}])
        para mensajes multimodales.

    `historial` son turnos previos para dar contexto de la conversación.

    Regresa None si no hay API key o si la llamada falla, para que quien
    llame decida qué mensaje mostrarle al usuario.
    """
    if not ANTHROPIC_API_KEY:
        return None

    cuerpo = {
        "model": MODELO,
        "max_tokens": max_tokens,
        "messages": list(historial or []) + [{"role": "user", "content": contenido}],
    }
    if sistema:
        cuerpo["system"] = sistema

    try:
        resp = requests.post(
            _URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": _VERSION_API,
                "content-type": "application/json",
            },
            json=cuerpo,
            timeout=timeout,
        )
        resp.raise_for_status()
        return _limpiar_para_voz(resp.json()["content"][0]["text"])
    except (requests.exceptions.RequestException, KeyError, IndexError) as error:
        print(f"[Venok] Error consultando a Claude: {error}")
        return None
