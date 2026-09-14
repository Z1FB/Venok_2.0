"""
Sistema de permisos/confirmación de Venok.

Regla del proyecto: cualquier acción sensible (borrar archivos, cambios de
sistema, etc.) debe pedir confirmación antes de ejecutarse.

En vez de bloquear esperando una respuesta por micrófono (lo cual rompe el
modo texto, donde no hay nada que escuchar), este módulo guarda la acción
pendiente y deja que sea la SIGUIENTE entrada del usuario —venga de voz o
de texto, da igual, ambas pasan por interpretar()— la que la confirme o
cancele. Así funciona igual en main.py y en app.py.
"""

import capacidades
import personalidad

PALABRAS_AFIRMATIVAS = (
    "si", "claro", "dale", "adelante", "confirmo", "ok", "de acuerdo", "va",
)

_pendiente = None  # {"ejecutar": callable, "mensaje_cancelado": str}


def hay_pendiente() -> bool:
    return _pendiente is not None


def solicitar(pregunta: str, ejecutar, mensaje_cancelado: str = "Entendido, no lo hago.") -> str:
    """Guarda `ejecutar` (una función sin argumentos) como acción pendiente
    y regresa `pregunta` para que Venok se la haga al usuario."""
    global _pendiente
    _pendiente = {"ejecutar": ejecutar, "mensaje_cancelado": mensaje_cancelado}
    return pregunta


def confirmar_cierre_de_app(proceso: str) -> str:
    """Cerrar una app puede hacer perder trabajo sin guardar, así que siempre
    se pregunta primero. Vive aquí para que tanto los comandos de siempre
    como el agente de IA pidan permiso exactamente igual."""
    return solicitar(
        personalidad.sugerencia("cerrar_app") + " ¿Confirmo el cierre?",
        lambda: capacidades.cerrar_app(proceso),
        mensaje_cancelado="Entendido, no la cierro.",
    )


def resolver(respuesta_normalizada: str) -> str:
    """Se llama con la siguiente entrada del usuario (ya normalizada) para
    confirmar o cancelar la acción pendiente. Cualquier respuesta que no
    sea claramente afirmativa cancela la acción, por seguridad."""
    global _pendiente
    accion = _pendiente
    _pendiente = None

    if any(palabra in respuesta_normalizada for palabra in PALABRAS_AFIRMATIVAS):
        return accion["ejecutar"]()
    return accion["mensaje_cancelado"]
