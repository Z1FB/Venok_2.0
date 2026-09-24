"""
El número de rescate de Venok: "haz lo tuyo".

Para cuando el que expone se queda en blanco. Son dos tiempos, como un
chiste: Venok se hace el que no entiende, y cuando le insisten se presenta
solo. Así el silencio en la sala se convierte en parte del guion.

Todo lo que dice aquí sale de datos locales: no llama a ninguna API ni
necesita internet, que es justo lo que puede fallar en una presentación.
Los números que menciona se cuentan de los mismos diccionarios que usa el
resto del programa, para que no se queden desactualizados al agregar cosas.
"""

import acciones
import capacidades
import memoria
import personalidad
from config import NOMBRE_ASISTENTE

# Primera parte: se hace el desentendido.
SALIDAS_EVASIVAS = (
    "¿Lo mío? No sé a qué se refiere.",
    "¿Lo mío? Uy, qué misterio. No me suena.",
    "¿Lo mío? Tendrá que ser más específico.",
)

# Lo que cuenta como insistir. Cualquier otra cosa cancela el número y se
# procesa como un comando normal: si el usuario cambia de tema, Venok no se
# queda esperando una frase que ya no va a llegar.
_INSISTENCIAS = (
    "como que no", "claro que sabes", "si sabes", "si lo sabes", "no te hagas",
    "la informacion", "de la informacion", "eso", "ya sabes", "presentate",
    "presentacion", "quien eres", "dale", "hazlo", "vamos", "anda", "por favor",
    "lo tuyo", "si", "claro",
)

# Frases con las que se puede pedir la presentación de una vez, sin el
# número de los dos tiempos. Es la red de seguridad: si el usuario se pone
# nervioso y olvida la segunda frase, con cualquiera de estas se arranca.
DISPARADORES_DIRECTOS = (
    "presentate", "haz tu presentacion", "preséntate", "quien eres",
    "quien sos", "hablales de ti", "diles quien eres", "presentate tu",
)

# Se aceptan las variantes juntas y la falta de hache: el reconocedor de voz
# escribe "has lo tuyo" con bastante frecuencia.
DISPARADORES_DEL_NUMERO = (
    "haz lo tuyo", "hazlo tuyo", "has lo tuyo", "haslo tuyo",
    "haga lo suyo", "hagalo suyo", "hacelo tuyo",
    "haz tu magia", "has tu magia", "muestra lo tuyo", "muestrales lo tuyo",
    "ensenales lo tuyo", "ensenale lo tuyo",
)

_esperando_insistencia = False


def hay_numero_pendiente() -> bool:
    return _esperando_insistencia


def le_pidieron_el_numero(comando_norm: str) -> bool:
    return any(frase in comando_norm for frase in DISPARADORES_DEL_NUMERO)


def le_pidieron_presentarse(comando_norm: str) -> bool:
    return any(frase in comando_norm for frase in DISPARADORES_DIRECTOS)


def hacerse_el_desentendido() -> str:
    global _esperando_insistencia
    _esperando_insistencia = True
    return personalidad.variar(SALIDAS_EVASIVAS, "evasivas")


def insistieron(comando_norm: str) -> bool:
    """¿La respuesta del usuario es insistir? Sea cual sea, el número se da
    por cerrado: o se presenta ahora, o el comando sigue su camino normal."""
    global _esperando_insistencia
    _esperando_insistencia = False
    return any(frase in comando_norm for frase in _INSISTENCIAS)


def cancelar() -> None:
    global _esperando_insistencia
    _esperando_insistencia = False


def presentarse() -> str:
    """La presentación que Venok hace de sí mismo, para leerla en voz alta.
    Dura alrededor de un minuto: el tiempo justo para que quien expone
    respire y retome el hilo."""
    nombre_asistente = memoria.obtener_nombre_asistente() or NOMBRE_ASISTENTE
    dueno = memoria.obtener_nombre()
    presentacion = f"Ah, eso. Haberlo dicho antes. Buenas: soy {nombre_asistente}"
    if dueno:
        presentacion += f", el asistente de escritorio que programó {dueno}"
    presentacion += (
        ". Estoy hecho en Python, hablo con la voz de Windows y escucho por el "
        "micrófono, así que basta con decir mi nombre para despertarme. "
        f"Sé abrir {len(acciones.APPS)} programas, {len(acciones.SITIOS)} sitios web "
        "y los juegos de esta computadora; manejo el volumen, el mouse y el teclado; "
        "y le puedo decir cuánta memoria, cuánto disco y cuánta batería le queda a "
        "este equipo sin necesidad de internet. "
        f"Busco y reproduzco videos en YouTube, traduzco a {len(capacidades.IDIOMAS)} idiomas, "
        f"doy la hora de {len(capacidades.ZONAS_HORARIAS)} países, leo las imágenes que me "
        "manden, programo recordatorios y contesto preguntas con Wolfram Alpha y con "
        "inteligencia artificial. "
        "Me acuerdo de lo que hablamos, así que puedo seguir una conversación en vez de "
        "contestar frases sueltas, y antes de cerrar un programa o borrar un archivo "
        "siempre pido permiso: esa parte no la negocio. "
        "Eso es lo mío."
    )
    if dueno:
        presentacion += f" ¿Seguimos, {dueno}?"
    return presentacion
