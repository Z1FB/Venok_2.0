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

import memoria
from config import ANTHROPIC_API_KEY

MODELO = "claude-haiku-4-5-20251001"

_URL = "https://api.anthropic.com/v1/messages"
_VERSION_API = "2023-06-01"

# Últimos turnos de conversación, para que Venok entienda preguntas de
# seguimiento ("¿y de los perros?", "otro", "¿por qué?").
#
# Lo llena main.interpretar() con TODOS los intercambios, no solo con los que
# contesta la IA: si Venok cuenta un chiste con una regla y no queda en el
# historial, el "otro" siguiente llega sin nada a lo que referirse.
#
# Se guarda en disco (memoria.py) para que cerrar Venok no corte la charla,
# pero se mantiene en esta lista mientras el programa corre: releer el archivo
# en cada pregunta sería ir al disco para nada. Son pocos turnos a propósito,
# porque cada mensaje viejo se reenvía en la siguiente pregunta y cuesta tokens.
_historial = None  # None = todavía no se ha leído del disco
_MAXIMO_MENSAJES = memoria.MAXIMO_MENSAJES_GUARDADOS  # 6 intercambios

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


def lo_que_sabe_del_usuario() -> str:
    """Los datos que Venok ya tiene guardados de la persona. Sirven para que
    hable como alguien que la conoce y no vuelva a preguntar lo mismo."""
    partes = []
    nombre = memoria.obtener_nombre()
    if nombre:
        partes.append(f"se llama {nombre}")
    ciudad = memoria.obtener_ciudad_favorita()
    if ciudad:
        partes.append(f"vive en {ciudad}")
    if not partes:
        return ""
    return f" La persona con la que hablas {' y '.join(partes)}."


def instruccion_de_sistema(tono: str = "amigable", nombre_asistente: str = "Venok") -> str:
    """La personalidad de Venok, para mandarla como instrucción de sistema en
    vez de repetirla dentro de cada pregunta."""
    estilo = _DESCRIPCION_TONO.get(tono, _DESCRIPCION_TONO["amigable"])
    return (
        f"Eres {nombre_asistente}, el asistente de escritorio de esta persona. "
        f"Responde en español, en un tono {estilo}, de forma breve (2 a 4 "
        f"oraciones) porque tu respuesta se leerá en voz alta. Ya se conocen: "
        f"no vuelvas a presentarte ni a saludar en cada respuesta."
        + lo_que_sabe_del_usuario()
    )


def _historial_vivo() -> list:
    """La conversación en curso. La primera vez la trae del disco, donde pudo
    quedar de antes de cerrar Venok (memoria.py decide si sigue vigente o si
    pasó tanto tiempo que conviene empezar de cero)."""
    global _historial
    if _historial is None:
        _historial = memoria.obtener_conversacion()
    return _historial


def obtener_historial() -> list:
    return list(_historial_vivo())


def recordar_intercambio(pregunta: str, respuesta: str) -> None:
    historial = _historial_vivo()
    historial.append({"role": "user", "content": pregunta})
    historial.append({"role": "assistant", "content": respuesta})
    del historial[:-_MAXIMO_MENSAJES]
    memoria.establecer_conversacion(historial)


def limpiar_historial() -> None:
    global _historial
    _historial = []
    memoria.establecer_conversacion([])


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
