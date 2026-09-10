"""
Análisis del equipo: una fotografía de las especificaciones y el software
instalado. A diferencia de monitoreo.py (que mide USO en tiempo real: %
de CPU, RAM libre, etc.), esto describe QUÉ es el equipo: modelo de
procesador, RAM total instalada, almacenamiento total, y qué programas
tiene instalados. Todo de solo lectura, sin necesidad de permisos.
"""

import platform

import psutil
import winreg

_CLAVES_DESINSTALACION = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

_PREFIJOS_IGNORADOS = ("actualizacion", "update for", "security update", "hotfix")


def _almacenamiento_total_gb() -> float:
    total_bytes = 0
    for particion in psutil.disk_partitions(all=False):
        try:
            total_bytes += psutil.disk_usage(particion.mountpoint).total
        except OSError:
            continue  # unidades ópticas sin disco, unidades de red desconectadas, etc.
    return total_bytes / (1024 ** 3)


def especificaciones() -> str:
    equipo = platform.node()
    sistema_operativo = f"{platform.system()} {platform.release()}"
    arquitectura = platform.machine()
    procesador = platform.processor() or "modelo no identificado"
    nucleos_fisicos = psutil.cpu_count(logical=False) or 0
    nucleos_logicos = psutil.cpu_count(logical=True) or 0
    ram_total_gb = psutil.virtual_memory().total / (1024 ** 3)

    return (
        f"Este equipo se llama {equipo} y corre {sistema_operativo}, arquitectura {arquitectura}. "
        f"El procesador es {procesador}, con {nucleos_fisicos} núcleos físicos "
        f"y {nucleos_logicos} lógicos. "
        f"Tiene {ram_total_gb:.1f} gigabytes de RAM instalados "
        f"y {_almacenamiento_total_gb():.0f} gigabytes de almacenamiento en total."
    )


def _listar_programas() -> list:
    nombres = set()
    for raiz, ruta in _CLAVES_DESINSTALACION:
        try:
            clave_raiz = winreg.OpenKey(raiz, ruta)
        except FileNotFoundError:
            continue

        with clave_raiz:
            total_subclaves = winreg.QueryInfoKey(clave_raiz)[0]
            for indice in range(total_subclaves):
                try:
                    nombre_subclave = winreg.EnumKey(clave_raiz, indice)
                    with winreg.OpenKey(clave_raiz, nombre_subclave) as subclave:
                        nombre, _ = winreg.QueryValueEx(subclave, "DisplayName")
                except (OSError, FileNotFoundError):
                    continue

                nombre = nombre.strip()
                if nombre and not nombre.lower().startswith(_PREFIJOS_IGNORADOS):
                    nombres.add(nombre)

    return sorted(nombres, key=str.lower)


def programas_instalados(cantidad: int = 20) -> str:
    programas = _listar_programas()
    if not programas:
        return "No pude leer la lista de programas instalados."

    listado = ", ".join(programas[:cantidad])
    if len(programas) > cantidad:
        return f"Tienes {len(programas)} programas instalados. Los primeros son: {listado}."
    return f"Tienes {len(programas)} programas instalados: {listado}."
