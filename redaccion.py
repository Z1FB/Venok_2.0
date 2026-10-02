"""
Redactar textos con IA y abrirlos en el Bloc de notas.

Para "escríbeme una carta de renuncia en el bloc de notas". Antes esa frase
caía en la regla de teclear y Venok escribía literalmente "una carta de
renuncia en el bloc de notas" en la ventana que estuviera enfrente.

Por qué se guarda en un archivo en vez de teclearlo: pyautogui solo teclea
los caracteres que están en el mapa del teclado, y las tildes, las eñes y
los signos de apertura NO lo están. Comprobado: "Estimándo señor:
presentó mi renuncia con satisfacción. ¡Gracias!" se tecleaba como
"Estimndo seor: present mi renuncia con satisfaccin. Gracias!". Escribiendo
el archivo y abriéndolo sale intacto, es instantáneo y además queda guardado.
"""

import os
import re
import subprocess
import unicodedata

import claude_api

# "en el bloc de notas", "en notepad", "en un documento"... Si la frase NO
# dice dónde, se respeta la regla de siempre (teclear tal cual lo dictado),
# que es una función de accesibilidad y no hay que romperla.
_DESTINOS = (
    "bloc de notas", "blog de notas", "block de notas", "notepad",
    "un documento", "el documento", "un archivo de texto", "un bloc",
)

_PATRON = re.compile(
    r"\b(?:escribe|escribeme|escribime|redacta|redactame|hazme|haceme|crea)\b"
    r"\s+(?:una|un|el|la|unas|unos)?\s*(.+)$"
)

# "redacta" por sí solo ya significa componer un texto, así que no hace
# falta que diga dónde.
_VERBOS_QUE_YA_IMPLICAN_REDACTAR = ("redacta", "redactame", "redactami", "redactime")

CARPETA_DESTINO = os.path.join(os.path.expanduser("~"), "Desktop")
LARGO_MAXIMO_NOMBRE = 40


def le_pidieron_redactar(comando_norm: str):
    """Regresa el tema a redactar, o None si el comando no es para esto."""
    tiene_destino = any(destino in comando_norm for destino in _DESTINOS)
    verbo_de_redactar = any(v in comando_norm for v in _VERBOS_QUE_YA_IMPLICAN_REDACTAR)
    if not tiene_destino and not verbo_de_redactar:
        return None

    coincidencia = _PATRON.search(comando_norm)
    if not coincidencia:
        return None

    tema = coincidencia.group(1)
    # Se quita la parte del destino: lo que queda es el tema de verdad.
    for destino in _DESTINOS:
        # El artículo es opcional: la gente dice "en el bloc de notas" y
        # también "en bloc de notas".
        tema = re.sub(
            rf"\s*\b(?:en|dentro de|usando)\s+(?:el|la|un|una)?\s*{re.escape(destino)}\b",
            "",
            tema,
        )
    return tema.strip(" .,") or None


def _nombre_de_archivo(tema: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", tema.lower())
        if unicodedata.category(c) != "Mn"
    )
    limpio = re.sub(r"[^a-z0-9]+", "_", sin_tildes).strip("_")[:LARGO_MAXIMO_NOMBRE]
    return (limpio or "texto") + ".txt"


def _ruta_libre(nombre: str) -> str:
    carpeta = CARPETA_DESTINO if os.path.isdir(CARPETA_DESTINO) else os.path.expanduser("~")
    ruta = os.path.join(carpeta, nombre)
    base, extension = os.path.splitext(ruta)
    numero = 2
    # Nunca se pisa un archivo que ya exista: se le pone un número al lado.
    while os.path.exists(ruta):
        ruta = f"{base}_{numero}{extension}"
        numero += 1
    return ruta


def _pedirle_el_texto_a_la_ia(tema: str, tono: str, nombre_asistente: str):
    sistema = (
        claude_api.instruccion_de_sistema(tono, nombre_asistente)
        + " Ahora NO estás conversando: estás redactando un documento que la "
        "persona va a guardar y leer. Escribe el texto completo y listo para "
        "usar, con sus saltos de línea y su estructura (encabezado, cuerpo y "
        "despedida si aplica). No lo comentes ni lo expliques, no uses "
        "asteriscos ni almohadillas, y deja entre corchetes los datos que no "
        "conozcas, como [Nombre] o [Fecha]."
    )
    return claude_api.preguntar(
        f"Escribe {tema}.",
        sistema=sistema,
        max_tokens=700,
        para_voz=False,   # un documento necesita sus saltos de línea
    )


def _limpiar_documento(texto: str) -> str:
    """Quita las marcas de Markdown que a veces se cuelan. En el Bloc de notas
    no se interpretan: un título queda como "# La fotosíntesis" y las negritas
    como asteriscos sueltos. Se respetan los saltos de línea, que en un
    documento sí forman parte del resultado."""
    lineas = []
    for linea in texto.split("\n"):
        linea = re.sub(r"^\s{0,3}#{1,6}\s*", "", linea)   # títulos
        linea = re.sub(r"\*\*(.+?)\*\*", r"\1", linea)     # negritas
        linea = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"\1", linea)  # cursivas
        lineas.append(linea.rstrip())
    return "\n".join(lineas).strip()


def redactar_y_abrir(tema: str, tono: str = "amigable", nombre_asistente: str = "Venok") -> str:
    if not claude_api.hay_api_key():
        return ("Para redactar textos necesito la clave de inteligencia artificial, "
                "y no la tengo configurada.")

    texto = _pedirle_el_texto_a_la_ia(tema, tono, nombre_asistente)
    if not texto:
        return "No pude redactar eso ahora mismo. ¿Lo intentamos de nuevo?"
    texto = _limpiar_documento(texto)

    ruta = _ruta_libre(_nombre_de_archivo(tema))
    try:
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(texto)
    except OSError as error:
        return f"Escribí el texto pero no pude guardarlo ({error})."

    try:
        # Se abre con el Bloc de notas a propósito, no con el programa que
        # el sistema tenga asociado a los .txt.
        subprocess.Popen(["notepad.exe", ruta])
    except OSError:
        return f"Lo guardé en {os.path.basename(ruta)}, en el escritorio, pero no pude abrir el Bloc de notas."

    return (f"Listo. Lo escribí y lo abrí en el Bloc de notas. "
            f"Quedó guardado como {os.path.basename(ruta)} en el escritorio.")
