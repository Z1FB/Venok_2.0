"""
Capacidades adicionales de Venok, organizadas por categoría:
- Información: clima, noticias, hora, fecha, definiciones, conversión de moneda
- Sistema: volumen, bloquear pantalla, vaciar papelera, cerrar apps
- Multimedia: reproducir/pausar, siguiente/anterior canción
- Archivos: crear carpetas, abrir carpetas comunes
- Diversión: chistes, moneda, dado
- Utilidades: calculadora, captura de pantalla

Usa APIs gratuitas que NO requieren API key:
- Open-Meteo para el clima
- RSS de Google Noticias para noticias
- Wikipedia (resumen) para definiciones
- Frankfurter para conversión de moneda
"""

import subprocess
import platform
import datetime
import os
import re
import random
import ast
import operator
import xml.etree.ElementTree as ET

import requests
import pyautogui

from acciones import normalizar
from config import WOLFRAM_APP_ID

SISTEMA = platform.system()

CIUDAD_DEFECTO = "San Salvador"  # cambia esto por tu ciudad si quieres

# Nombre del proceso real en Windows para poder cerrarlo con "cierra spotify"
PROCESOS = {
    "spotify": "Spotify.exe",
    "chrome": "chrome.exe",
    "bloc de notas": "notepad.exe",
    "calculadora": "CalculatorApp.exe",
    "discord": "Discord.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "visual studio code": "Code.exe",
    "edge": "msedge.exe",
    # OJO: no agregues aquí "cmd" ni "terminal" — cerraría también la
    # terminal donde está corriendo Venok, apagándolo de golpe.
    # Para agregar una app tuya: "nombre que dirás": "NombreDelProceso.exe"
    # (para saber el nombre exacto, abre el Administrador de tareas mientras
    # la app está abierta, pestaña "Detalles", y busca su .exe)
}

CARPETAS_COMUNES = {
    "escritorio": "Desktop",
    "descargas": "Downloads",
    "documentos": "Documents",
    "imagenes": "Pictures",
    "musica": "Music",
}


# ------------------------------------------------------------------
# Información
# ------------------------------------------------------------------
def clima(ciudad: str = None) -> str:
    ciudad = (ciudad or CIUDAD_DEFECTO).strip()
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": ciudad, "count": 1, "language": "es"},
            timeout=8,
        ).json()

        resultados = geo.get("results")
        if not resultados:
            return f"No encontré la ciudad {ciudad}."

        lugar = resultados[0]
        lat, lon = lugar["latitude"], lugar["longitude"]
        nombre_lugar = lugar.get("name", ciudad)

        clima_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": "true"},
            timeout=8,
        ).json()

        actual = clima_resp.get("current_weather", {})
        temperatura = actual.get("temperature")
        viento = actual.get("windspeed")

        if temperatura is None:
            return f"No pude obtener el clima de {nombre_lugar}."

        return f"En {nombre_lugar} hay {temperatura} grados, con viento de {viento} kilómetros por hora."

    except requests.exceptions.RequestException:
        return "No pude conectarme a internet para revisar el clima."


def noticias(cantidad: int = 2) -> str:
    try:
        respuesta = requests.get(
            "https://news.google.com/rss?hl=es-419&gl=SV&ceid=SV:es-419",
            timeout=8,
        )
        respuesta.raise_for_status()

        raiz = ET.fromstring(respuesta.content)
        titulares_crudos = [item.find("title").text for item in raiz.findall(".//item")[:cantidad]]

        # Google agrega " - NombreDelMedio" al final de cada titular; lo quitamos
        # porque leído en voz alta suena raro.
        titulares = [t.rsplit(" - ", 1)[0] if t else t for t in titulares_crudos]

        if not titulares:
            return "No encontré noticias en este momento."

        return "Estas son las noticias más recientes: " + ". ".join(titulares)

    except requests.exceptions.RequestException:
        return "No pude conectarme a internet para revisar las noticias."
    except ET.ParseError:
        return "Recibí las noticias pero no pude leerlas bien."


def hora_actual() -> str:
    ahora = datetime.datetime.now()
    return f"Son las {ahora.strftime('%I:%M %p')}."


# País/ciudad (como lo dirías) -> zona horaria IANA
ZONAS_HORARIAS = {
    "taiwan": "Asia/Taipei",
    "japon": "Asia/Tokyo",
    "china": "Asia/Shanghai",
    "corea del sur": "Asia/Seoul",
    "corea": "Asia/Seoul",
    "india": "Asia/Kolkata",
    "españa": "Europe/Madrid",
    "francia": "Europe/Paris",
    "alemania": "Europe/Berlin",
    "italia": "Europe/Rome",
    "reino unido": "Europe/London",
    "inglaterra": "Europe/London",
    "rusia": "Europe/Moscow",
    "estados unidos": "America/New_York",
    "eeuu": "America/New_York",
    "mexico": "America/Mexico_City",
    "guatemala": "America/Guatemala",
    "honduras": "America/Tegucigalpa",
    "nicaragua": "America/Managua",
    "costa rica": "America/Costa_Rica",
    "panama": "America/Panama",
    "el salvador": "America/El_Salvador",
    "colombia": "America/Bogota",
    "peru": "America/Lima",
    "chile": "America/Santiago",
    "argentina": "America/Argentina/Buenos_Aires",
    "brasil": "America/Sao_Paulo",
    "canada": "America/Toronto",
    "australia": "Australia/Sydney",
}


def hora_en_pais(nombre_pais: str) -> str:
    nombre_pais = nombre_pais.strip()
    zona = ZONAS_HORARIAS.get(normalizar(nombre_pais))

    if not zona:
        return (
            f"No tengo la zona horaria de {nombre_pais} guardada. "
            f"Puedo agregarla si me dices su nombre exacto."
        )

    try:
        resp = requests.get(
            f"https://timeapi.io/api/time/current/zone",
            params={"timeZone": zona},
            timeout=8,
        )
        resp.raise_for_status()
        datos = resp.json()
        hora = datos.get("time", "")[:5]  # solo HH:MM
        return f"En {nombre_pais} son las {hora}."
    except requests.exceptions.RequestException as error:
        print(f"[Venok] Error al buscar la hora: {error}")
        return f"No pude conectarme a internet para revisar la hora en {nombre_pais}."


def fecha_actual() -> str:
    ahora = datetime.datetime.now()
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dia_semana = dias[ahora.weekday()]
    return f"Hoy es {dia_semana} {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}."


def definir(termino: str) -> str:
    termino = termino.strip()
    # Wikipedia espera el nombre del artículo sin artículos gramaticales
    # iniciales (ej: "Sol", no "el sol")
    termino = re.sub(r"^(el|la|los|las|un|una)\s+", "", termino, flags=re.IGNORECASE).strip()

    if not termino:
        return "¿Qué palabra o tema quieres que te defina?"

    headers = {"User-Agent": "VenokAssistant/1.0 (proyecto escolar; contacto@example.com)"}

    try:
        # Paso 1: buscar el título REAL del artículo. Esto tolera frases
        # informales como "planeta Júpiter" en vez del título exacto que
        # usa Wikipedia, que sería "Júpiter (planeta)".
        busqueda = requests.get(
            "https://es.wikipedia.org/w/rest.php/v1/search/page",
            params={"q": termino, "limit": 1},
            headers=headers,
            timeout=8,
        )
        busqueda.raise_for_status()
        resultados = busqueda.json().get("pages", [])
        if not resultados:
            return f"No encontré información sobre {termino}."

        titulo_real = resultados[0]["key"]

        # Paso 2: obtener el resumen de ese artículo ya con el título correcto
        resp = requests.get(
            f"https://es.wikipedia.org/api/rest_v1/page/summary/{titulo_real}",
            headers=headers,
            timeout=8,
        )
        resp.raise_for_status()
        datos = resp.json()

        if datos.get("type") == "disambiguation":
            return (
                f"{termino} puede referirse a varias cosas. "
                f"¿Podrías ser más específico?"
            )

        extracto = datos.get("extract")
        if not extracto:
            return f"No encontré una definición clara de {termino}."

        oraciones = extracto.split(". ")
        resumen = ". ".join(oraciones[:2])
        if not resumen.endswith("."):
            resumen += "."
        return resumen

    except requests.exceptions.RequestException as error:
        print(f"[Venok] Error al buscar definición: {error}")
        return "No pude conectarme a internet para buscar esa definición."


MONEDAS = {
    "dolares": "USD", "dolar": "USD",
    "euros": "EUR", "euro": "EUR",
    "colones": "CRC", "colon": "CRC",
    "pesos mexicanos": "MXN", "pesos": "MXN",
    "libras": "GBP", "libra": "GBP",
    "yenes": "JPY", "yen": "JPY",
}


def convertir_moneda_comando(comando: str) -> str:
    # Si dice "$100" en vez de "100 dólares", no hay palabra de moneda entre
    # el número y "a" — en ese caso asumimos dólares por defecto.
    tiene_signo_dolar = "$" in comando
    texto = comando.replace("$", " ")

    coincidencia = re.search(
        r"(\d+(?:\.\d+)?)(?:\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+)?))?\s+a\s+(.+)",
        texto,
        re.IGNORECASE,
    )
    if not coincidencia:
        return "Dime la cantidad y las monedas, por ejemplo: convierte 100 dólares a euros."

    cantidad_texto, origen_texto, destino_texto = coincidencia.groups()
    cantidad = float(cantidad_texto)

    if not origen_texto:
        origen_texto = "dólares" if tiene_signo_dolar else "dólares"  # valor por defecto

    origen_codigo = MONEDAS.get(normalizar(origen_texto), normalizar(origen_texto).upper())
    destino_codigo = MONEDAS.get(normalizar(destino_texto), normalizar(destino_texto).upper())

    try:
        resp = requests.get(
            "https://api.frankfurter.dev/v1/latest",
            params={"amount": cantidad, "from": origen_codigo, "to": destino_codigo},
            timeout=8,
        )
        resp.raise_for_status()
        datos = resp.json()
        valor = datos.get("rates", {}).get(destino_codigo)
        if valor is None:
            return "No pude hacer esa conversión de moneda."
        return f"{cantidad_texto} {origen_texto} son aproximadamente {round(valor, 2)} {destino_texto}."
    except requests.exceptions.RequestException:
        return "No pude conectarme a internet para convertir la moneda."


# ------------------------------------------------------------------
# Utilidades: calculadora con palabras en español
# ------------------------------------------------------------------
_OPERADORES_PERMITIDOS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def _evaluar_nodo(nodo):
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)):
        return nodo.value
    if isinstance(nodo, ast.BinOp):
        op = _OPERADORES_PERMITIDOS.get(type(nodo.op))
        if op is None:
            raise ValueError("Operación no permitida")
        return op(_evaluar_nodo(nodo.left), _evaluar_nodo(nodo.right))
    if isinstance(nodo, ast.UnaryOp):
        op = _OPERADORES_PERMITIDOS.get(type(nodo.op))
        if op is None:
            raise ValueError("Operación no permitida")
        return op(_evaluar_nodo(nodo.operand))
    raise ValueError("Expresión no permitida")


def calcular(expresion: str) -> str:
    texto = expresion.lower()
    reemplazos = {
        " por ": " * ",
        " mas ": " + ",
        " menos ": " - ",
        " entre ": " / ",
        " dividido entre ": " / ",
        " dividido por ": " / ",
        "al cuadrado": " ** 2",
    }
    for palabra, simbolo in reemplazos.items():
        texto = texto.replace(palabra, simbolo)

    try:
        arbol = ast.parse(texto, mode="eval")
        resultado = _evaluar_nodo(arbol.body)
        if resultado == int(resultado):
            resultado = int(resultado)
        return f"El resultado es {resultado}."
    except Exception:
        return "No pude resolver esa operación, intenta decirla de otra forma."


# ------------------------------------------------------------------
# Sistema
# ------------------------------------------------------------------
def bloquear_pantalla() -> str:
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "Bloqueando la pantalla."
    except Exception as error:
        return f"No pude bloquear la pantalla ({error})."


def vaciar_papelera() -> str:
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -Confirm:$false"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return "Papelera de reciclaje vaciada."
    except Exception as error:
        return f"No pude vaciar la papelera ({error})."


def volumen(accion: str) -> str:
    if accion == "subir":
        for _ in range(5):
            pyautogui.press("volumeup")
        return "Subiendo el volumen."
    if accion == "bajar":
        for _ in range(5):
            pyautogui.press("volumedown")
        return "Bajando el volumen."
    if accion == "silenciar":
        pyautogui.press("volumemute")
        return "Silenciando."
    return "No entendí qué hacer con el volumen."


def cerrar_app(nombre_proceso: str) -> str:
    """Cierra un programa por su nombre de proceso, ej: 'Spotify.exe'."""
    try:
        if SISTEMA == "Windows":
            subprocess.run(["taskkill", "/IM", nombre_proceso, "/F"], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", nombre_proceso], capture_output=True)
        return f"Cerrando {nombre_proceso}."
    except Exception as error:
        return f"No pude cerrar {nombre_proceso} ({error})."


# ------------------------------------------------------------------
# Multimedia
# ------------------------------------------------------------------
def multimedia(accion: str) -> str:
    if accion in ("reproducir", "pausar"):
        pyautogui.press("playpause")
        return "Listo."
    if accion == "siguiente":
        pyautogui.press("nexttrack")
        return "Siguiente canción."
    if accion == "anterior":
        pyautogui.press("prevtrack")
        return "Canción anterior."
    return "No entendí esa acción multimedia."


# ------------------------------------------------------------------
# Archivos y carpetas
# ------------------------------------------------------------------
def crear_carpeta(nombre: str) -> str:
    nombre = nombre.strip()
    if not nombre:
        return "¿Cómo quieres que se llame la carpeta?"
    ruta_escritorio = os.path.join(os.path.expanduser("~"), "Desktop")
    ruta_nueva = os.path.join(ruta_escritorio, nombre)
    try:
        os.makedirs(ruta_nueva, exist_ok=True)
        return f"Creé la carpeta {nombre} en el escritorio."
    except Exception as error:
        return f"No pude crear la carpeta ({error})."


def abrir_carpeta_comun(nombre: str) -> str:
    carpeta = CARPETAS_COMUNES.get(normalizar(nombre))
    if not carpeta:
        return f"No conozco la carpeta {nombre}."
    ruta = os.path.join(os.path.expanduser("~"), carpeta)
    try:
        os.startfile(ruta)
        return f"Abriendo {nombre}."
    except Exception as error:
        return f"No pude abrir {nombre} ({error})."


# ------------------------------------------------------------------
# Utilidades varias
# ------------------------------------------------------------------
def captura_pantalla() -> str:
    try:
        nombre_archivo = f"captura_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        imagen = pyautogui.screenshot()
        imagen.save(nombre_archivo)
        return f"Captura guardada como {nombre_archivo}."
    except Exception as error:
        return f"No pude tomar la captura ({error})."


# ------------------------------------------------------------------
# Diversión / personalidad
# ------------------------------------------------------------------
CHISTES = [
    "¿Por qué los programadores prefieren el frío? Porque odian los bugs.",
    "¿Cómo se llama el campeón de buceo japonés? Tokofondo.",
    "Un byte le dice a otro: ¿te sientes bien? No, creo que tengo un bit suelto.",
    "¿Qué le dijo un cable a otro cable? Nada, no tenían conexión.",
    "¿Por qué la computadora fue al doctor? Porque tenía un virus.",
]


def chiste() -> str:
    return random.choice(CHISTES)


def lanzar_moneda() -> str:
    return random.choice(["Cara.", "Cruz."])


def lanzar_dado() -> str:
    return f"Salió {random.randint(1, 6)}."


# ------------------------------------------------------------------
# Wolfram Alpha: último recurso para preguntas de conocimiento general,
# ciencia y matemáticas que ningún otro comando reconoció.
# Nota: funciona mejor con preguntas en inglés; en español puede fallar
# con frases muy largas o coloquiales, pero suele andar bien con
# cálculos, unidades, y datos científicos/factuales cortos.
# ------------------------------------------------------------------
def _traducir(texto: str, origen: str, destino: str) -> str:
    """Traduce texto entre idiomas usando una API gratuita, sin clave.
    Si falla, regresa el texto original tal cual."""
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": texto, "langpair": f"{origen}|{destino}"},
            timeout=8,
        )
        resp.raise_for_status()
        datos = resp.json()
        traduccion = datos.get("responseData", {}).get("translatedText")
        return traduccion if traduccion else texto
    except requests.exceptions.RequestException:
        return texto


def preguntar_wolfram(pregunta: str):
    """Devuelve la respuesta de Wolfram Alpha (traducida a español), o None
    si no pudo responder (para que quien llame use un mensaje de respaldo)."""
    if not WOLFRAM_APP_ID:
        return None

    pregunta_en_ingles = _traducir(pregunta, "es", "en")

    try:
        resp = requests.get(
            "https://api.wolframalpha.com/v1/result",
            params={"appid": WOLFRAM_APP_ID, "i": pregunta_en_ingles},
            timeout=10,
        )
        if resp.status_code == 501:
            return None  # Wolfram Alpha no supo interpretar la pregunta
        resp.raise_for_status()
        respuesta_en_ingles = resp.text
        return _traducir(respuesta_en_ingles, "en", "es")
    except requests.exceptions.RequestException as error:
        print(f"[Venok] Error al consultar Wolfram Alpha: {error}")
        return None
