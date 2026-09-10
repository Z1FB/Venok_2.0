"""
Monitoreo del sistema: procesador, memoria RAM, disco, batería y procesos
en ejecución. Todo es de solo lectura (no cambia nada en el equipo), así
que a diferencia de acciones como cerrar apps o vaciar la papelera, esto
NO necesita pasar por permisos.py.
"""

import platform

import psutil

SISTEMA = platform.system()


def uso_cpu() -> str:
    porcentaje = psutil.cpu_percent(interval=0.6)
    return f"El procesador está usando el {porcentaje:.0f} por ciento de su capacidad."


def uso_ram() -> str:
    memoria = psutil.virtual_memory()
    usados_gb = memoria.used / (1024 ** 3)
    total_gb = memoria.total / (1024 ** 3)
    return (
        f"Estás usando {usados_gb:.1f} de {total_gb:.1f} gigabytes de RAM "
        f"({memoria.percent:.0f} por ciento)."
    )


def espacio_disco(unidad: str = None) -> str:
    unidad = unidad or ("C:\\" if SISTEMA == "Windows" else "/")
    try:
        disco = psutil.disk_usage(unidad)
    except (FileNotFoundError, OSError):
        return f"No encontré la unidad {unidad}."

    libres_gb = disco.free / (1024 ** 3)
    total_gb = disco.total / (1024 ** 3)
    return f"Tienes {libres_gb:.1f} gigabytes libres de {total_gb:.1f} en el disco {unidad}"


def estado_bateria() -> str:
    bateria = psutil.sensors_battery()
    if bateria is None:
        return "No detecté batería; parece una computadora de escritorio, o no pude leerla."
    estado = "cargando" if bateria.power_plugged else "sin cargador"
    return f"La batería está al {bateria.percent:.0f} por ciento, {estado}."


def procesos_principales(cantidad: int = 5) -> str:
    totales = {}
    for proceso in psutil.process_iter(["name", "memory_info"]):
        try:
            info = proceso.info
            if not info["name"] or info["memory_info"] is None:
                continue
            # Un mismo programa suele tener varios procesos (ej. Chrome);
            # se suman para dar un número que tenga sentido para el usuario.
            totales[info["name"]] = totales.get(info["name"], 0) + info["memory_info"].rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    top = sorted(totales.items(), key=lambda item: item[1], reverse=True)[:cantidad]
    if not top:
        return "No pude leer la lista de procesos."

    listado = ", ".join(f"{nombre} ({memoria / (1024 ** 2):.0f} MB)" for nombre, memoria in top)
    return f"Los programas que más recursos usan ahora son: {listado}."


def resumen_sistema() -> str:
    partes = [uso_cpu(), uso_ram(), espacio_disco()]
    if psutil.sensors_battery() is not None:
        partes.append(estado_bateria())
    return " ".join(partes)
