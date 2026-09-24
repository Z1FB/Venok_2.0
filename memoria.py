"""
Memoria de Venok, en dos capas:

- Memoria persistente: datos del usuario que sobreviven a reiniciar Venok
  (su nombre, su ciudad favorita). Se guardan en un JSON dentro de la
  carpeta del usuario (~/.venok/memoria.json), no en la carpeta del
  proyecto, para que funcione igual corriendo con `python app.py` o ya
  empacado como .exe (donde la carpeta del programa puede no ser escribible).
- Memoria de sesión: contexto de la conversación actual (última ciudad
  consultada, última app abierta) para permitir seguimientos como "ciérrala"
  sin repetir el nombre. Vive solo en memoria RAM, se pierde al cerrar Venok.
- Conversación reciente: los últimos turnos de lo que se habló, guardados
  junto al resto para que cerrar Venok no borre el hilo de la charla.
"""

import datetime
import json
import os
import re

_RUTA_MEMORIA = os.path.join(os.path.expanduser("~"), ".venok", "memoria.json")

_datos_persistentes = None  # caché; se carga del disco una sola vez

_contexto_sesion = {
    "ultima_ciudad": None,
    "ultima_app": None,
}


def _cargar() -> dict:
    global _datos_persistentes
    if _datos_persistentes is not None:
        return _datos_persistentes
    try:
        with open(_RUTA_MEMORIA, "r", encoding="utf-8") as archivo:
            _datos_persistentes = json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError):
        _datos_persistentes = {}
    return _datos_persistentes


def _guardar() -> None:
    os.makedirs(os.path.dirname(_RUTA_MEMORIA), exist_ok=True)
    with open(_RUTA_MEMORIA, "w", encoding="utf-8") as archivo:
        json.dump(_datos_persistentes, archivo, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------
# Memoria persistente (entre reinicios)
# ------------------------------------------------------------------
def obtener_nombre():
    return _cargar().get("nombre")


def establecer_nombre(nombre: str) -> None:
    _cargar()["nombre"] = nombre.strip().title()
    _guardar()


def obtener_ciudad_favorita():
    return _cargar().get("ciudad_favorita")


def establecer_ciudad_favorita(ciudad: str) -> None:
    _cargar()["ciudad_favorita"] = ciudad.strip().title()
    _guardar()


def olvidar_todo() -> None:
    """Borra los datos DEL USUARIO: su nombre, su ciudad y la conversación
    guardada. El nombre que le pusiste a Venok y el tono elegido son
    configuración del asistente, no datos del usuario, así que no se tocan."""
    datos = _cargar()
    datos.pop("nombre", None)
    datos.pop("ciudad_favorita", None)
    datos.pop("conversacion", None)
    datos.pop("conversacion_fecha", None)
    _guardar()


# ------------------------------------------------------------------
# Conversación reciente (sobrevive a cerrar Venok)
# ------------------------------------------------------------------
MAXIMO_MENSAJES_GUARDADOS = 12

# Un amigo retoma la charla de hace un rato, no la de hace tres días: si
# pasaron más de estas horas desde el último mensaje, se empieza de cero.
# Sin esto, abrir Venok por la mañana y decir "otro" seguiría contestando
# sobre el chiste de anoche.
HORAS_PARA_OLVIDAR_CONVERSACION = 6

_FORMATO_FECHA = "%Y-%m-%dT%H:%M:%S"


def _conversacion_caducada(datos: dict) -> bool:
    marca = datos.get("conversacion_fecha")
    if not isinstance(marca, str):
        return True
    try:
        ultima = datetime.datetime.strptime(marca, _FORMATO_FECHA)
    except ValueError:
        return True
    transcurrido = datetime.datetime.now() - ultima
    return transcurrido > datetime.timedelta(hours=HORAS_PARA_OLVIDAR_CONVERSACION)


def obtener_conversacion() -> list:
    """Los últimos turnos de la charla, listos para mandarlos a la API.

    Se revisa la forma de lo que hay en el disco en vez de confiar en él: el
    archivo es de texto y se puede editar a mano, y esto se envía tal cual a
    la API, que exige turnos alternos empezando por el usuario.
    """
    datos = _cargar()
    guardada = datos.get("conversacion", [])
    if not isinstance(guardada, list) or _conversacion_caducada(datos):
        return []

    alternados = []
    esperado = "user"
    for mensaje in guardada[-MAXIMO_MENSAJES_GUARDADOS:]:
        if not isinstance(mensaje, dict):
            break
        if mensaje.get("role") != esperado or not isinstance(mensaje.get("content"), str):
            break
        if not mensaje["content"].strip():
            break
        alternados.append({"role": esperado, "content": mensaje["content"]})
        esperado = "assistant" if esperado == "user" else "user"

    # Un último mensaje del usuario sin respuesta dejaría la lista terminada
    # en "user", y el siguiente turno mandaría dos seguidos.
    if alternados and alternados[-1]["role"] == "user":
        alternados.pop()
    return alternados


def establecer_conversacion(mensajes) -> None:
    datos = _cargar()
    if not mensajes:
        datos.pop("conversacion", None)
        datos.pop("conversacion_fecha", None)
        _guardar()
        return

    datos["conversacion"] = [
        {"role": m["role"], "content": m["content"]}
        for m in list(mensajes)[-MAXIMO_MENSAJES_GUARDADOS:]
    ]
    datos["conversacion_fecha"] = datetime.datetime.now().strftime(_FORMATO_FECHA)
    _guardar()


# ------------------------------------------------------------------
# Personalización de Venok (nombre del asistente, tono de personalidad)
# ------------------------------------------------------------------
TONO_DEFECTO = "amigable"
TONOS_VALIDOS = ("formal", "amigable", "gracioso")


def obtener_nombre_asistente():
    """Regresa None si no se ha personalizado (quien llame decide el
    valor por defecto, ej. config.NOMBRE_ASISTENTE)."""
    return _cargar().get("nombre_asistente")


def establecer_nombre_asistente(nombre: str) -> None:
    _cargar()["nombre_asistente"] = nombre.strip().title()
    _guardar()


def obtener_tono() -> str:
    return _cargar().get("tono", TONO_DEFECTO)


def establecer_tono(tono: str) -> bool:
    if tono not in TONOS_VALIDOS:
        return False
    _cargar()["tono"] = tono
    _guardar()
    return True


# Apariencia de la interfaz: color principal, color de fondo y tamaño de letra.
_PATRON_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
ESCALA_LETRA_MINIMA = 0.8
ESCALA_LETRA_MAXIMA = 1.5


def obtener_apariencia() -> dict:
    return dict(_cargar().get("apariencia", {}))


def establecer_apariencia(apariencia) -> None:
    """Llega desde JavaScript y se vuelve a inyectar en el CSS de la ventana,
    así que solo se guarda lo que tenga la forma exacta esperada."""
    if not isinstance(apariencia, dict):
        return

    limpia = {}
    for clave in ("principal", "fondo"):
        color = apariencia.get(clave)
        if isinstance(color, str) and _PATRON_COLOR.match(color):
            limpia[clave] = color.lower()

    escala = apariencia.get("escala")
    if isinstance(escala, (int, float)) and not isinstance(escala, bool):
        limpia["escala"] = round(min(ESCALA_LETRA_MAXIMA, max(ESCALA_LETRA_MINIMA, float(escala))), 2)

    _cargar()["apariencia"] = limpia
    _guardar()


# ------------------------------------------------------------------
# Memoria de sesión (contexto de la conversación actual)
# ------------------------------------------------------------------
def recordar_contexto(clave: str, valor) -> None:
    _contexto_sesion[clave] = valor


def obtener_contexto(clave: str):
    return _contexto_sesion.get(clave)
