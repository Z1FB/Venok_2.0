"""
Personalidad de Venok: razonable, atento, y siempre buscando sugerir
o confirmar antes de actuar — al estilo de Jarvis (Tony Stark).

El tono (formal / amigable / gracioso) es elegible por el usuario y se
guarda en memoria.py; aquí solo se definen las frases de cada uno. Los
mensajes de confirmación de acciones sensibles (SUGERENCIAS_ANTES_DE_ACTUAR)
NO cambian con el tono a propósito: deben quedar claros sin importar qué
tan formal o gracioso esté configurado Venok.
"""

import random

import memoria

TONOS = {
    "formal": {
        "saludos": [
            "Buenas. ¿En qué puedo asistirle?",
            "A sus órdenes. Indíqueme en qué puedo ayudarle.",
            "Quedo atento a sus instrucciones.",
        ],
        "no_entendido": [
            "Disculpe, no logré comprender su solicitud. ¿Podría reformularla?",
            "No he captado la instrucción con claridad. ¿Sería tan amable de repetirla?",
        ],
        "despedidas": [
            "Ha sido un placer. Quedo a su disposición.",
            "Con gusto. Hasta la próxima ocasión.",
        ],
    },
    "amigable": {
        "saludos": [
            "A su servicio. ¿En qué puedo ayudarle hoy?",
            "Aquí estoy. Dígame qué necesita.",
            "Todo listo por aquí. ¿Qué hacemos primero?",
        ],
        "no_entendido": [
            "No estoy seguro de haber entendido. ¿Puede repetirlo de otra forma?",
            "Disculpe, no capté bien ese comando. ¿Lo intentamos de nuevo?",
        ],
        "despedidas": [
            "Con gusto. Aquí estaré si me necesita.",
            "Hasta pronto. Fue un placer ayudarle.",
        ],
    },
    "gracioso": {
        "saludos": [
            "¡Ey! Aquí Venok, listo para hacer magia (o al menos intentarlo).",
            "Reportándome para el turno. ¿Qué travesura hacemos hoy?",
            "Encendido y con café imaginario en mano. ¿Qué se te ofrece?",
        ],
        "no_entendido": [
            "Eh... ¿eso fue en español? Inténtalo de nuevo, por favor.",
            "Creo que se me cruzaron los cables. ¿Me lo repites?",
        ],
        "despedidas": [
            "Me voy a modo siesta digital. ¡Nos vemos!",
            "Apagando motores. Ha sido divertido, como siempre.",
        ],
    },
}

CONFIRMACIONES_ACCION = [
    "Entendido, procedo con {accion}.",
    "Claro, voy a {accion}.",
    "De acuerdo, {accion} en un momento.",
]

SUGERENCIAS_ANTES_DE_ACTUAR = {
    "cerrar_app": "Antes de cerrar, ¿guardó su trabajo? Puedo esperar si lo necesita.",
    "abrir_red_social": "Le recuerdo tomar descansos de las redes de vez en cuando. ¿Aun así continúo?",
    "accion_riesgosa": "Esa acción no se puede deshacer fácilmente. ¿Confirma que desea continuar?",
}


def _frases(categoria: str) -> list:
    tono = memoria.obtener_tono()
    return TONOS.get(tono, TONOS[memoria.TONO_DEFECTO])[categoria]


def saludo(nombre: str = None) -> str:
    base = random.choice(_frases("saludos"))
    return f"Hola, {nombre}. {base}" if nombre else base


def confirmar(accion: str) -> str:
    return random.choice(CONFIRMACIONES_ACCION).format(accion=accion)


def sugerencia(tipo: str) -> str:
    return SUGERENCIAS_ANTES_DE_ACTUAR.get(tipo, "")


def no_entendido() -> str:
    return random.choice(_frases("no_entendido"))


def despedida() -> str:
    return random.choice(_frases("despedidas"))
