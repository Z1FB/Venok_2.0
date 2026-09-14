"""
Recordatorios de Venok: guarda tareas para una fecha/hora futura y avisa
cuando llega el momento, revisando en un hilo de fondo cada cierto tiempo.

Se guardan en ~/.venok/recordatorios.json (misma carpeta que memoria.py)
para sobrevivir a reinicios: si cierras Venok antes de la hora, al volver
a abrirlo el recordatorio sigue ahí y se avisa en cuanto corresponda.

Entiende frases como:
  "recuérdame llamar a mamá mañana a las 5"
  "recuérdame que hay tarea el lunes a las 8"
  "recuérdame tomar agua en 20 minutos"
No es un parser de fechas completo (no hay librería de por medio), cubre
los casos más comunes en español. Si no logra entender el "cuándo", le
pregunta al usuario en vez de adivinar.
"""

import datetime
import json
import os
import re
import threading
import time

_RUTA = os.path.join(os.path.expanduser("~"), ".venok", "recordatorios.json")
_lock = threading.Lock()

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

_PATRON_RELATIVO = re.compile(r"en (\d+) (minutos?|horas?)")
_PATRON_HORA = re.compile(r"a las (\d{1,2})(?::(\d{2}))?( de la (manana|tarde|noche))?")
_PATRON_DIA = re.compile(r"(el )?(" + "|".join(DIAS_SEMANA) + r")")


def _cargar() -> list:
    try:
        with open(_RUTA, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _guardar(lista: list) -> None:
    os.makedirs(os.path.dirname(_RUTA), exist_ok=True)
    with open(_RUTA, "w", encoding="utf-8") as archivo:
        json.dump(lista, archivo, ensure_ascii=False, indent=2)


def _extraer_momento(texto: str):
    """Busca en `texto` (ya normalizado: sin tildes, minúsculas) una
    referencia temporal. Regresa (datetime_futuro, texto_sin_esa_parte),
    o (None, texto_original) si no encontró ninguna."""
    coincidencia = _PATRON_RELATIVO.search(texto)
    if coincidencia:
        cantidad = int(coincidencia.group(1))
        delta = (
            datetime.timedelta(hours=cantidad)
            if coincidencia.group(2).startswith("hora")
            else datetime.timedelta(minutes=cantidad)
        )
        resto = texto[: coincidencia.start()] + texto[coincidencia.end():]
        return datetime.datetime.now() + delta, resto

    ahora = datetime.datetime.now()
    hora, minuto = 9, 0  # si no dice hora, se asume las 9 de la mañana
    coincidencia_hora = _PATRON_HORA.search(texto)
    if coincidencia_hora:
        hora = int(coincidencia_hora.group(1))
        minuto = int(coincidencia_hora.group(2) or 0)
        periodo = coincidencia_hora.group(4)
        if periodo in ("tarde", "noche") and hora < 12:
            hora += 12
        texto = texto[: coincidencia_hora.start()] + texto[coincidencia_hora.end():]

    if "manana" in texto:
        objetivo = (ahora + datetime.timedelta(days=1)).replace(
            hour=hora, minute=minuto, second=0, microsecond=0
        )
        return objetivo, texto.replace("manana", "")

    if "hoy" in texto:
        objetivo = ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if objetivo <= ahora:
            objetivo += datetime.timedelta(days=1)
        return objetivo, texto.replace("hoy", "")

    coincidencia_dia = _PATRON_DIA.search(texto)
    if coincidencia_dia:
        dia = coincidencia_dia.group(2)
        indice = DIAS_SEMANA.index(dia)
        dias_para_llegar = (indice - ahora.weekday()) % 7 or 7  # si es hoy, el próximo, no ahorita
        objetivo = (ahora + datetime.timedelta(days=dias_para_llegar)).replace(
            hour=hora, minute=minuto, second=0, microsecond=0
        )
        resto = texto[: coincidencia_dia.start()] + texto[coincidencia_dia.end():]
        return objetivo, resto

    if coincidencia_hora:
        # Solo dijo una hora ("a las 5"), sin día: hoy, o mañana si esa
        # hora ya pasó.
        objetivo = ahora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if objetivo <= ahora:
            objetivo += datetime.timedelta(days=1)
        return objetivo, texto

    return None, texto


def agregar(tarea: str, momento: datetime.datetime) -> str:
    """Guarda un recordatorio ya con su fecha resuelta. Lo usan tanto el
    parseo de frases en español como el agente de IA."""
    with _lock:
        lista = _cargar()
        lista.append({"tarea": tarea, "momento": momento.isoformat(), "avisado": False})
        _guardar(lista)

    return f"Listo, te recordaré \"{tarea}\" el {momento.strftime('%d/%m a las %H:%M')}."


# Al quitar el "cuándo" de la frase quedan palabras sueltas al inicio
# ("el próximo martes" deja "el próximo"), que suenan raro al repetir la tarea.
_RELLENO_SOBRANTE = re.compile(r"^(?:el|la|los|las|este|esta|proximo|proxima|que|de)\s+")


def _limpiar_tarea(texto: str) -> str:
    tarea = re.sub(r"\s{2,}", " ", texto).strip(" ,.")
    anterior = None
    while tarea != anterior:
        anterior = tarea
        tarea = _RELLENO_SOBRANTE.sub("", tarea).strip()
    return tarea


def crear_desde_comando(texto: str) -> str:
    """`texto` es lo que sigue después de 'recuérdame' (ya normalizado)."""
    texto = texto.strip()
    if texto.startswith("que "):
        texto = texto[4:]

    momento, texto_sin_cuando = _extraer_momento(texto)
    tarea = _limpiar_tarea(texto_sin_cuando)

    if not momento:
        # No se pudo sacar la fecha de la frase (ej. "en media hora"). Se
        # regresa None para que main.py se lo pase al agente de IA, que sí
        # sabe interpretar momentos escritos de cualquier forma.
        return None
    if not tarea:
        return "¿De qué quieres que te recuerde?"

    return agregar(tarea, momento)


def listar_pendientes() -> str:
    with _lock:
        lista = [r for r in _cargar() if not r["avisado"]]

    if not lista:
        return "No tienes recordatorios pendientes."

    lista.sort(key=lambda r: r["momento"])
    partes = [
        f"{r['tarea']} el {datetime.datetime.fromisoformat(r['momento']).strftime('%d/%m a las %H:%M')}"
        for r in lista
    ]
    return "Tus recordatorios pendientes son: " + "; ".join(partes) + "."


def cancelar_todos() -> None:
    with _lock:
        _guardar([])


def iniciar_verificador(avisar) -> None:
    """Lanza un hilo en segundo plano que revisa cada 20 segundos si algún
    recordatorio ya llegó a su hora, y llama a `avisar(mensaje)` una sola
    vez por cada uno."""

    def bucle() -> None:
        while True:
            with _lock:
                lista = _cargar()
                ahora = datetime.datetime.now()
                pendientes_de_avisar = []
                for recordatorio in lista:
                    if recordatorio["avisado"]:
                        continue
                    if datetime.datetime.fromisoformat(recordatorio["momento"]) <= ahora:
                        recordatorio["avisado"] = True
                        pendientes_de_avisar.append(recordatorio["tarea"])
                if pendientes_de_avisar:
                    _guardar(lista)

            for tarea in pendientes_de_avisar:
                avisar(f"Recordatorio: {tarea}.")

            time.sleep(20)

    threading.Thread(target=bucle, daemon=True).start()
