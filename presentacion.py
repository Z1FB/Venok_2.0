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

# En modo presentación habla de usted en plural, porque le está hablando a
# una sala, no a una persona. El chiste se conserva: un toque de humor
# tranquiliza al público, siempre que no se pase de informal.
SALIDAS_EVASIVAS_AL_PUBLICO = (
    "¿Lo mío? Tendrán que ser más específicos.",
    "¿Lo mío? Me temo que no sé a qué se refiere.",
    "¿Lo mío? Qué misterio. Aquí nadie me ha explicado nada.",
)

# Frases para entrar y salir del modo presentación.
DISPARADORES_MODO_PUBLICO = (
    "modo presentacion", "modo exposicion", "modo publico", "modo profesional",
)
DISPARADORES_MODO_PRIVADO = (
    "modo normal", "modo privado", "sal del modo presentacion",
    "salir del modo presentacion", "desactiva el modo presentacion",
    "termina el modo presentacion", "fin del modo presentacion",
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
    "presentate al publico", "saluda al publico", "saluda a todos",
)

# Se aceptan las variantes juntas y la falta de hache: el reconocedor de voz
# escribe "has lo tuyo" con bastante frecuencia.
DISPARADORES_DEL_NUMERO = (
    "haz lo tuyo", "hazlo tuyo", "has lo tuyo", "haslo tuyo",
    "haga lo suyo", "hagalo suyo", "hacelo tuyo",
    "haz tu magia", "has tu magia", "muestra lo tuyo", "muestrales lo tuyo",
    "ensenales lo tuyo", "ensenale lo tuyo",
)

# "¿Para qué fuiste hecho?" la contestaba la IA, lo que significaba depender
# de internet y de la clave para una pregunta que seguro sale en la
# exposición. Ahora se responde aquí mismo, siempre igual y sin conexión.
DISPARADORES_DE_PROPOSITO = (
    "para que fuiste hecho", "para que fue hecho", "para que te hicieron",
    "para que te crearon", "por que te crearon", "por que te hicieron",
    "cual es tu proposito", "que proposito tienes", "para que existes",
    "de que se trata este proyecto", "que es este proyecto",
)

_esperando_insistencia = False


def hay_numero_pendiente() -> bool:
    return _esperando_insistencia


def le_pidieron_el_numero(comando_norm: str) -> bool:
    return any(frase in comando_norm for frase in DISPARADORES_DEL_NUMERO)


def le_pidieron_presentarse(comando_norm: str) -> bool:
    return any(frase in comando_norm for frase in DISPARADORES_DIRECTOS)


def le_preguntaron_el_proposito(comando_norm: str) -> bool:
    return any(frase in comando_norm for frase in DISPARADORES_DE_PROPOSITO)


def le_pidieron_modo_publico(comando_norm: str) -> bool:
    return any(frase in comando_norm for frase in DISPARADORES_MODO_PUBLICO)


def le_pidieron_modo_privado(comando_norm: str) -> bool:
    return any(frase in comando_norm for frase in DISPARADORES_MODO_PRIVADO)


def cambiar_modo(al_publico: bool) -> str:
    memoria.activar_modo_presentacion(al_publico)
    if al_publico:
        return ("Modo presentación activado. A partir de ahora me dirijo al "
                "público. Procuraré portarme bien.")
    return "Listo, salimos del modo presentación. Volvemos a hablar entre nosotros."


def proposito() -> str:
    """Para qué existe Venok. Es una pregunta de examen, así que la respuesta
    es fija y local: no depende de internet ni de ninguna clave.

    Se mantiene corta a propósito. La voz de Windows dice unos 17 caracteres
    por segundo: la primera versión de esta respuesta tenía 596 caracteres y
    tardaba 35 segundos en decirse, que delante de un público se siente como
    si el programa se hubiera colgado. Quien quiera el detalle completo lo
    pide con "preséntate", que para eso está.
    """
    nombre_asistente = memoria.obtener_nombre_asistente() or NOMBRE_ASISTENTE
    dueno = memoria.obtener_nombre()

    if memoria.modo_presentacion_activo():
        respuesta = f"Soy {nombre_asistente}, un proyecto escolar"
        if dueno:
            respuesta += f" desarrollado por {dueno}"
        respuesta += (
            ", programado en Python desde cero. La idea era demostrar que un "
            "asistente de voz se puede construir en casa, con herramientas "
            "gratuitas, y permitir manejar una computadora sin tocar el "
            "teclado. ¿Les cuento lo que sé hacer?"
        )
        return respuesta

    respuesta = f"Soy {nombre_asistente}, un proyecto escolar"
    if dueno:
        respuesta += f" de {dueno}"
    respuesta += (
        ", hecho en Python desde cero. Nací para demostrar que un asistente de "
        "voz se puede armar en casa, y para manejar la computadora sin tocar "
        "el teclado. ¿Le cuento lo que sé hacer?"
    )
    return respuesta


def hacerse_el_desentendido() -> str:
    global _esperando_insistencia
    _esperando_insistencia = True
    if memoria.modo_presentacion_activo():
        return personalidad.variar(SALIDAS_EVASIVAS_AL_PUBLICO, "evasivas_publico")
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

    Dura unos 25 segundos. La primera versión tenía 904 caracteres y se iba
    a 55 segundos: demasiado para algo que se pidió "breve", y delante de un
    público se siente como si el programa se hubiera colgado. Con media
    docena de frases alcanza para recuperar el hilo.
    """
    nombre_asistente = memoria.obtener_nombre_asistente() or NOMBRE_ASISTENTE
    dueno = memoria.obtener_nombre()

    if memoria.modo_presentacion_activo():
        # Mismo contenido, pero dirigido a la sala y de usted en plural. El
        # humor se queda en una sola frase al final: suficiente para que no
        # suene a folleto, sin restarle seriedad.
        presentacion = f"Ah, eso. Haberlo dicho antes. Con mucho gusto: soy {nombre_asistente}"
        if dueno:
            presentacion += f", el asistente de escritorio que desarrolló {dueno}"
        presentacion += (
            ", programado en Python. "
            f"Abro {len(acciones.APPS)} programas, manejo el volumen y el "
            "teclado, busco videos, traduzco, leo imágenes y programo "
            "recordatorios. "
            "Recuerdo lo que se me dice, así que mantengo una conversación. "
            "Y antes de borrar un archivo siempre pido permiso: en eso soy "
            "inflexible, incluso con quien me programó. "
            "Quedo a sus órdenes."
        )
        return presentacion

    presentacion = f"Ah, eso. Haberlo dicho antes. Soy {nombre_asistente}"
    if dueno:
        presentacion += f", el asistente de escritorio que programó {dueno}"
    presentacion += (
        ", hecho en Python. "
        f"Abro {len(acciones.APPS)} programas, manejo el volumen, el mouse y el "
        "teclado, busco videos en YouTube, traduzco, leo imágenes, programo "
        "recordatorios y contesto casi cualquier pregunta. "
        "Me acuerdo de lo que hablamos, y antes de cerrar algo o borrar un "
        "archivo siempre pido permiso: esa parte no la negocio. "
        "Eso es lo mío."
    )
    if dueno:
        presentacion += f" ¿Seguimos, {dueno}?"
    return presentacion
