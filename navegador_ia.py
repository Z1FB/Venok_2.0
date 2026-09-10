"""
Control de navegador con IA: Venok abre tu navegador real para investigar
un tema, y usa la API de Claude (Anthropic) para explicártelo en voz alta
— o, si le das una página en concreto, la abre y resume su contenido.

Nota de diseño: raspar los resultados de un buscador (Google/DuckDuckGo)
es frágil — los motores de búsqueda cambian su HTML y bloquean scraping
automatizado con páginas de verificación (lo probé con DuckDuckGo: devolvía
un 202 sin resultados reales). Por eso, para "investiga sobre X" se abre
una búsqueda real en el navegador para que el usuario la vea, y aparte se
le pregunta a Claude directamente — más confiable que depender de poder
leer una página de resultados que puede cambiar en cualquier momento.
Para "resume la página X" sí se lee el contenido real de esa página
específica, que es una operación mucho más estable.

Requiere ANTHROPIC_API_KEY en el .env (ver config.py). Sin ella, avisa
que la función no está disponible en vez de fallar en silencio, igual
que Wolfram Alpha en capacidades.py.
"""

import webbrowser
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from config import ANTHROPIC_API_KEY

_MODELO = "claude-haiku-4-5-20251001"
_ENCABEZADOS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VenokAssistant/1.0"}
_LARGO_MAXIMO_TEXTO = 6000


def _extraer_texto(url: str):
    try:
        resp = requests.get(url, headers=_ENCABEZADOS, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        return None

    sopa = BeautifulSoup(resp.text, "html.parser")
    for etiqueta in sopa(["script", "style", "nav", "footer", "header"]):
        etiqueta.decompose()

    texto = " ".join(sopa.get_text(separator=" ").split())
    return texto[:_LARGO_MAXIMO_TEXTO] if texto else None


def _preguntar_a_claude(instruccion: str):
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": _MODELO,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": instruccion}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()
    except (requests.exceptions.RequestException, KeyError, IndexError) as error:
        print(f"[Venok] Error consultando a Claude: {error}")
        return None


_DESCRIPCION_TONO = {
    "formal": "formal y respetuoso, tratando de usted",
    "amigable": "cercano y amable",
    "gracioso": "divertido y con humor ligero",
}


def responder_pregunta_general(pregunta: str, tono: str = "amigable", nombre_asistente: str = "Venok"):
    """Último recurso conversacional: cuando ningún comando ni Wolfram Alpha
    supo responder, se le pregunta directamente a Claude. Regresa None si no
    hay API key configurada o si la llamada falla, para que quien llame
    (main.py) pueda seguir con su propio mensaje de 'no entendí'."""
    if not ANTHROPIC_API_KEY:
        return None

    estilo = _DESCRIPCION_TONO.get(tono, _DESCRIPCION_TONO["amigable"])
    instruccion = (
        f"Eres {nombre_asistente}, un asistente de voz de escritorio. Responde en "
        f"español, en un tono {estilo}, de forma breve (2 a 4 oraciones) porque tu "
        f"respuesta se leerá en voz alta. Pregunta o comentario del usuario: {pregunta}"
    )
    return _preguntar_a_claude(instruccion)


def buscar_y_resumir(consulta: str) -> str:
    if not ANTHROPIC_API_KEY:
        return "Esta función necesita una ANTHROPIC_API_KEY configurada en tu archivo .env para poder investigar con IA."

    consulta = consulta.strip()
    if not consulta:
        return "¿Sobre qué quieres que investigue?"

    webbrowser.open(f"https://www.google.com/search?q={quote(consulta)}")

    respuesta = _preguntar_a_claude(
        f'Explica brevemente sobre "{consulta}", en 3 o 4 oraciones claras '
        f"en español, como si se lo fueras a leer en voz alta a alguien."
    )
    if not respuesta:
        return f"Abrí una búsqueda sobre {consulta} en tu navegador, pero no pude generar una explicación con IA en este momento."
    return respuesta


def resumir_pagina(url: str) -> str:
    if not ANTHROPIC_API_KEY:
        return "Esta función necesita una ANTHROPIC_API_KEY configurada en tu archivo .env para poder resumir con IA."

    url = url.strip()
    if not url:
        return "¿Qué página quieres que resuma?"
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    webbrowser.open(url)

    texto = _extraer_texto(url)
    if not texto:
        return f"Abrí {url}, pero no pude leer su contenido para resumírtelo (algunos sitios bloquean este tipo de lectura automática)."

    resumen = _preguntar_a_claude(
        f"Resume el siguiente contenido web en español, en 3 o 4 oraciones "
        f"claras para leerlas en voz alta:\n\n{texto}"
    )
    return resumen or f"Abrí {url}, pero no pude generar el resumen con IA en este momento."
