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
"""

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
    """Borra solo los datos DEL USUARIO (nombre, ciudad). El nombre que le
    pusiste a Venok y el tono elegido son configuración del asistente, no
    datos del usuario, así que no se tocan aquí."""
    datos = _cargar()
    datos.pop("nombre", None)
    datos.pop("ciudad_favorita", None)
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
