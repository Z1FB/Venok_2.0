"""
Control de mouse y teclado por voz — pensado para accesibilidad,
para que alguien pueda usar la laptop sin depender de tocar
físicamente el mouse o el teclado.

Requiere: pip install pyautogui
"""

import pyautogui

pyautogui.FAILSAFE = True  # mover el mouse a una esquina detiene todo (seguridad)

DISTANCIA_DEFECTO = 100  # píxeles por movimiento


def mover_mouse(direccion: str, distancia: int = DISTANCIA_DEFECTO) -> str:
    direccion = direccion.lower().strip()
    movimientos = {
        "arriba": (0, -distancia),
        "abajo": (0, distancia),
        "izquierda": (-distancia, 0),
        "derecha": (distancia, 0),
    }
    if direccion not in movimientos:
        return f"No reconozco la dirección {direccion}."

    dx, dy = movimientos[direccion]
    pyautogui.moveRel(dx, dy, duration=0.2)
    return f"Moviendo el mouse hacia {direccion}."


def clic(boton: str = "izquierdo") -> str:
    boton = boton.lower().strip()
    mapa_botones = {"izquierdo": "left", "derecho": "right"}
    pyautogui.click(button=mapa_botones.get(boton, "left"))
    return f"Clic {boton} realizado."


def doble_clic() -> str:
    pyautogui.doubleClick()
    return "Doble clic realizado."


def escribir_texto(texto: str) -> str:
    pyautogui.write(texto, interval=0.03)
    return "Texto escrito."


def presionar_tecla(tecla: str) -> str:
    """Ej: 'enter', 'espacio', 'esc', 'tab'."""
    mapa_teclas = {
        "enter": "enter",
        "espacio": "space",
        "escape": "esc",
        "esc": "esc",
        "tabulador": "tab",
        "tab": "tab",
        "borrar": "backspace",
    }
    tecla_normalizada = mapa_teclas.get(tecla.lower().strip())
    if not tecla_normalizada:
        return f"No reconozco la tecla {tecla}."
    pyautogui.press(tecla_normalizada)
    return f"Tecla {tecla} presionada."


def desplazar(direccion: str, cantidad: int = 300) -> str:
    direccion = direccion.lower().strip()
    if direccion == "arriba":
        pyautogui.scroll(cantidad)
        return "Desplazando hacia arriba."
    if direccion == "abajo":
        pyautogui.scroll(-cantidad)
        return "Desplazando hacia abajo."
    return f"No reconozco la dirección {direccion} para desplazar."
