"""
Acciones que Venok puede ejecutar en la laptop: abrir aplicaciones,
pestañas del navegador y juegos.

IMPORTANTE: ajusta las rutas de APPS y JUEGOS a lo que exista en TU laptop
antes de la demo. Los nombres de la izquierda son los que el usuario dirá
en voz alta (o escribirá) para activar cada acción.
"""

import webbrowser
import subprocess
import platform
import unicodedata

SISTEMA = platform.system()  # "Windows", "Darwin" (macOS) o "Linux"


def normalizar(texto: str) -> str:
    """Quita tildes y pasa a minúsculas, para comparar sin importar acentos.
    Ej: 'CONFIGURACIÓN' y 'configuracion' se comparan igual."""
    texto = texto.lower().strip()
    forma_descompuesta = unicodedata.normalize("NFD", texto)
    return "".join(c for c in forma_descompuesta if unicodedata.category(c) != "Mn")


# --- Sitios web / "pestañas" que Venok puede abrir ---
SITIOS = {
    "youtube": "https://www.youtube.com",
    "chatgpt": "https://chat.openai.com",
    "correo": "https://mail.google.com",
    "noticias": "https://news.google.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "google": "https://www.google.com",
}

# Sitios que soportan búsqueda directa por URL (para "abre youtube y busca X")
SITIOS_CON_BUSQUEDA = {
    "youtube": "https://www.youtube.com/results?search_query={busqueda}",
    "google": "https://www.google.com/search?q={busqueda}",
    "facebook": "https://www.facebook.com/search/top?q={busqueda}",
}


def abrir_sitio_con_busqueda(nombre: str, busqueda: str) -> str:
    """Abre un sitio con una búsqueda específica, ej: YouTube -> 'tutoriales de python'."""
    nombre = nombre.lower().strip()
    if nombre in SITIOS_CON_BUSQUEDA:
        url = SITIOS_CON_BUSQUEDA[nombre].format(busqueda=busqueda.replace(" ", "+"))
        webbrowser.open(url)
        return f"Buscando {busqueda} en {nombre}."
    return abrir_sitio(nombre)


# --- Aplicaciones instaladas en la laptop (ajusta las rutas) ---
# En Windows normalmente basta el nombre del ejecutable si está en el PATH,
# o puedes poner la ruta completa entre comillas.
APPS = {
    "spotify": "spotify",
    "calculadora": "calc" if SISTEMA == "Windows" else "gnome-calculator",
    "bloc de notas": "notepad" if SISTEMA == "Windows" else "gedit",
    "configuración": "start ms-settings:" if SISTEMA == "Windows" else "gnome-control-center",
    "explorador de archivos": "explorer" if SISTEMA == "Windows" else "nautilus",
    "chrome": "chrome" if SISTEMA == "Windows" else "google-chrome",
    "panel de control": "control" if SISTEMA == "Windows" else "gnome-control-center",
    "discord": "discord",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "visual studio code": "code",
    "edge": "msedge",
    "administrador de tareas": "taskmgr",
    # Para agregar una app tuya que no esté aquí:
    #   "nombre que dirás": "nombre_del_programa_o_ruta_completa",
    # Ejemplo con ruta completa (usa r"..." para que las \ no den problema):
    #   "epic games": r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe",
}

# --- Juegos instalados (ajusta las rutas a donde estén en tu laptop) ---
JUEGOS = {
    "minecraft": r"C:\Program Files (x86)\Minecraft Launcher\MinecraftLauncher.exe",
    "steam": "steam" if SISTEMA != "Windows" else r"C:\Program Files (x86)\Steam\Steam.exe",
}


def abrir_sitio(nombre: str) -> str:
    nombre = nombre.lower().strip()
    if nombre in SITIOS:
        webbrowser.open(SITIOS[nombre])
        return f"Abriendo {nombre}."
    return f"No conozco el sitio {nombre} todavía."


def abrir_app(nombre: str) -> str:
    nombre = nombre.lower().strip()
    if nombre in APPS:
        try:
            subprocess.Popen(APPS[nombre], shell=True)
            return f"Abriendo {nombre}."
        except Exception:
            return f"No pude abrir {nombre}. Revisa la ruta en acciones.py."
    return f"No tengo registrada la aplicación {nombre}."


def abrir_juego(nombre: str) -> str:
    nombre = nombre.lower().strip()
    if nombre in JUEGOS:
        try:
            subprocess.Popen(JUEGOS[nombre], shell=True)
            return f"Iniciando {nombre}. ¡Que lo disfrutes!"
        except Exception:
            return f"No pude iniciar {nombre}. Revisa la ruta en acciones.py."
    return f"No tengo registrado el juego {nombre}."
