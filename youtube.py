"""
Buscar y reproducir videos de YouTube.

Hasta ahora, "busca X en youtube" solo abría la página de resultados
(acciones.abrir_sitio_con_busqueda) y había que elegir el video a mano.
Aquí se usa la API oficial (YouTube Data API v3) para quedarse con el
primer resultado y abrir ese video directamente, que además arranca solo
en la mayoría de navegadores.

Requiere YOUTUBE_API_KEY en el .env (ver config.py). Sin esa clave no
falla: avisa que no está configurada, y quien llama puede recurrir a la
búsqueda de siempre — igual que hace Wolfram Alpha en capacidades.py.

La confirmación ("¿lo reproduzco?") NO se pide aquí: la arma main.py con
permisos.solicitar(), para que funcione igual por voz y por texto.
"""

import html
import re
import webbrowser

import requests

from config import YOUTUBE_API_KEY

URL_BUSQUEDA = "https://www.googleapis.com/youtube/v3/search"
URL_VIDEO = "https://www.youtube.com/watch?v={}"

TIEMPO_LIMITE = 8  # segundos

# Los títulos de YouTube vienen llenos de emojis y a veces son una ristra de
# hashtags ("#brainrot #cute #zzz ..."). Leídos en voz alta suenan fatal, así
# que se limpian antes de repetírselos al usuario.
_SIMBOLOS = re.compile("[🀀-🫿←-⯿️‍]")
LARGO_MAXIMO_TITULO = 70


def _limpiar_titulo(titulo: str) -> str:
    limpio = _SIMBOLOS.sub("", titulo)
    limpio = re.sub(r"\s+", " ", limpio).strip(" -|·")
    if len(limpio) > LARGO_MAXIMO_TITULO:
        limpio = limpio[:LARGO_MAXIMO_TITULO].rsplit(" ", 1)[0] + "…"
    return limpio or titulo


def hay_credenciales() -> bool:
    return bool(YOUTUBE_API_KEY)


def buscar(consulta: str):
    """Busca en YouTube y devuelve (video, error). `video` es un diccionario
    con 'id', 'titulo' y 'canal'; si algo sale mal, `video` es None y `error`
    trae un mensaje ya listo para decirle al usuario."""
    consulta = (consulta or "").strip()
    if not consulta:
        return None, "¿Qué quiere que busque en YouTube?"

    if not hay_credenciales():
        return None, ("No tengo configurada la clave de YouTube, así que no puedo "
                      "reproducir videos directamente.")

    try:
        respuesta = requests.get(
            URL_BUSQUEDA,
            params={
                "part": "snippet",
                "q": consulta,
                "type": "video",       # sin esto devuelve también canales y listas
                "maxResults": 1,
                "safeSearch": "moderate",
                "key": YOUTUBE_API_KEY,
            },
            timeout=TIEMPO_LIMITE,
        )
    except requests.RequestException:
        return None, "No pude conectarme a YouTube. Revise su conexión a internet."

    if respuesta.status_code in (400, 403):
        # 403 es el caso típico: clave inválida, API sin habilitar, o se acabó
        # la cuota diaria gratuita. Conviene distinguirlo de "no hay internet".
        return None, ("YouTube rechazó la búsqueda. Puede que la clave no sea válida "
                      "o que se haya agotado la cuota diaria.")
    if respuesta.status_code != 200:
        return None, f"YouTube respondió con un error {respuesta.status_code}."

    resultados = respuesta.json().get("items", [])
    if not resultados:
        return None, f"No encontré ningún video de {consulta} en YouTube."

    primero = resultados[0]
    datos = primero.get("snippet", {})
    identificador = primero.get("id", {}).get("videoId")
    if not identificador:
        return None, f"No encontré ningún video de {consulta} en YouTube."

    return {
        # Los títulos vienen con entidades HTML (&quot;, &#39;) que también
        # habría que leer en voz alta si no se traducen.
        "titulo": _limpiar_titulo(html.unescape(datos.get("title", ""))),
        "canal": html.unescape(datos.get("channelTitle", "")).strip(),
        "id": identificador,
    }, None


def url_de(video: dict) -> str:
    return URL_VIDEO.format(video["id"])


def reproducir(video: dict) -> str:
    """Abre el video en el navegador. Solo se llama después de que el usuario
    haya confirmado (ver permisos.solicitar en main.py)."""
    webbrowser.open(url_de(video))
    return f"Reproduciendo {video['titulo']}."
