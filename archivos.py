"""
Búsqueda, apertura y eliminación de archivos del usuario, dentro de sus
carpetas comunes (Escritorio, Descargas, Documentos).

Por seguridad, `eliminar_archivo` NUNCA borra permanentemente: manda el
archivo a la papelera de reciclaje con send2trash, para que sea
recuperable si Venok se equivocó o el usuario se arrepiente. Quien llame
a `eliminar_archivo` debe pedir confirmación antes (ver permisos.py) —
esta función solo ejecuta la acción ya confirmada.
"""

import os

from send2trash import send2trash

from acciones import normalizar

CARPETAS_BUSQUEDA = [
    os.path.join(os.path.expanduser("~"), "Desktop"),
    os.path.join(os.path.expanduser("~"), "Downloads"),
    os.path.join(os.path.expanduser("~"), "Documents"),
]

_PROFUNDIDAD_MAXIMA = 2  # niveles de subcarpetas a revisar, para no tardar una eternidad


def _buscar_coincidencias(nombre: str) -> list:
    nombre = normalizar(nombre)
    if not nombre:
        return []

    coincidencias = []
    for carpeta_raiz in CARPETAS_BUSQUEDA:
        if not os.path.isdir(carpeta_raiz):
            continue
        nivel_raiz = carpeta_raiz.rstrip(os.sep).count(os.sep)
        for carpeta_actual, subcarpetas, archivos_encontrados in os.walk(carpeta_raiz):
            if carpeta_actual.rstrip(os.sep).count(os.sep) - nivel_raiz >= _PROFUNDIDAD_MAXIMA:
                subcarpetas[:] = []  # no seguir bajando de nivel
            for archivo in archivos_encontrados:
                if nombre in normalizar(archivo):
                    coincidencias.append(os.path.join(carpeta_actual, archivo))

    return coincidencias


def buscar_archivo(nombre: str) -> str:
    coincidencias = _buscar_coincidencias(nombre)
    if not coincidencias:
        return f"No encontré ningún archivo llamado {nombre} en tus carpetas comunes."
    if len(coincidencias) == 1:
        return f"Encontré {os.path.basename(coincidencias[0])} en {os.path.dirname(coincidencias[0])}."
    listado = ", ".join(os.path.basename(ruta) for ruta in coincidencias[:5])
    return f"Encontré varios archivos que coinciden: {listado}."


def abrir_archivo(nombre: str) -> str:
    coincidencias = _buscar_coincidencias(nombre)
    if not coincidencias:
        return f"No encontré ningún archivo llamado {nombre}."
    if len(coincidencias) > 1:
        listado = ", ".join(os.path.basename(ruta) for ruta in coincidencias[:5])
        return f"Encontré varios archivos que coinciden, sé más específico: {listado}."
    try:
        os.startfile(coincidencias[0])
        return f"Abriendo {os.path.basename(coincidencias[0])}."
    except OSError as error:
        return f"No pude abrir el archivo ({error})."


def preparar_eliminacion(nombre: str):
    """Para borrar hace falta EXACTAMENTE una coincidencia (nunca se borra
    a ciegas). Regresa (ruta, nombre_visible, None) si hay una sola, o
    (None, None, mensaje) explicando por qué no se puede proceder."""
    coincidencias = _buscar_coincidencias(nombre)
    if not coincidencias:
        return None, None, f"No encontré ningún archivo llamado {nombre}."
    if len(coincidencias) > 1:
        listado = ", ".join(os.path.basename(ruta) for ruta in coincidencias[:5])
        return None, None, f"Encontré varios archivos que coinciden, sé más específico: {listado}."
    ruta = coincidencias[0]
    return ruta, os.path.basename(ruta), None


def eliminar_archivo(ruta: str) -> str:
    try:
        send2trash(ruta)
        return f"Envié {os.path.basename(ruta)} a la papelera de reciclaje."
    except OSError as error:
        return f"No pude eliminar el archivo ({error})."
