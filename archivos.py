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

# Buscar por una o dos letras coincide con casi todos los archivos del usuario.
# Pasó de verdad: "borra todos mis archivos" acababa buscando "s" y Venok se
# ponía a leer en voz alta los nombres de los archivos personales. Delante de
# un público eso es un problema serio, así que no se busca con menos de esto.
LARGO_MINIMO_BUSQUEDA = 3

# Cuántos nombres se pueden decir en voz alta cuando hay varias coincidencias.
# Si hay muchas, se dice cuántas son pero NO se leen: puede haber un proyector
# encendido.
MAXIMO_NOMBRES_A_DECIR = 3
_DEMASIADAS_PARA_LEERLAS = 6


def _nombre_buscable(nombre: str) -> bool:
    return len(normalizar(nombre).replace(" ", "")) >= LARGO_MINIMO_BUSQUEDA


def _describir_coincidencias(coincidencias: list) -> str:
    """Lista unos pocos nombres, o solo la cantidad si son demasiados."""
    if len(coincidencias) >= _DEMASIADAS_PARA_LEERLAS:
        return f"Encontré {len(coincidencias)} archivos que coinciden. Dime un nombre más preciso."
    listado = ", ".join(os.path.basename(ruta) for ruta in coincidencias[:MAXIMO_NOMBRES_A_DECIR])
    return f"Encontré varios archivos que coinciden: {listado}."


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
    if not _nombre_buscable(nombre):
        return "¿Qué archivo busco? Dime al menos parte de su nombre."
    coincidencias = _buscar_coincidencias(nombre)
    if not coincidencias:
        return f"No encontré ningún archivo llamado {nombre} en tus carpetas comunes."
    if len(coincidencias) == 1:
        return f"Encontré {os.path.basename(coincidencias[0])} en {os.path.dirname(coincidencias[0])}."
    return _describir_coincidencias(coincidencias)


def abrir_archivo(nombre: str) -> str:
    if not _nombre_buscable(nombre):
        return "¿Qué archivo abro? Dime al menos parte de su nombre."
    coincidencias = _buscar_coincidencias(nombre)
    if not coincidencias:
        return f"No encontré ningún archivo llamado {nombre}."
    if len(coincidencias) > 1:
        return _describir_coincidencias(coincidencias)
    try:
        os.startfile(coincidencias[0])
        return f"Abriendo {os.path.basename(coincidencias[0])}."
    except OSError as error:
        return f"No pude abrir el archivo ({error})."


def preparar_eliminacion(nombre: str):
    """Para borrar hace falta EXACTAMENTE una coincidencia (nunca se borra
    a ciegas). Regresa (ruta, nombre_visible, None) si hay una sola, o
    (None, None, mensaje) explicando por qué no se puede proceder."""
    if not _nombre_buscable(nombre):
        return None, None, ("No voy a borrar nada así, sin saber qué. Dime el nombre "
                            "del archivo en concreto.")
    coincidencias = _buscar_coincidencias(nombre)
    if not coincidencias:
        return None, None, f"No encontré ningún archivo llamado {nombre}."
    if len(coincidencias) > 1:
        return None, None, _describir_coincidencias(coincidencias) + " Así no borro nada."
    ruta = coincidencias[0]
    return ruta, os.path.basename(ruta), None


def eliminar_archivo(ruta: str) -> str:
    try:
        send2trash(ruta)
        return f"Envié {os.path.basename(ruta)} a la papelera de reciclaje."
    except OSError as error:
        return f"No pude eliminar el archivo ({error})."
