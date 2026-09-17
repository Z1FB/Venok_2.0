"""
Venok v2.0 - Aplicación de escritorio

Une la interfaz visual (ui/index.html) con el asistente (main.py) en una
sola ventana, agregando: palabra de activación ("Oye Venok"), un panel de
chat de texto, y cambio entre modo voz y modo texto.

IMPORTANTE: este archivo NO modifica main.py, capacidades.py, acciones.py,
control_mouse_teclado.py, voz.py ni personalidad.py — toda la lógica que
ya funcionaba se reutiliza tal cual, solo se le agrega esta capa nueva
encima.

Uso:
    python app.py
"""

import sys
import os
import threading
import time

# Cuando se empaqueta con PyInstaller usando --windowed (sin consola),
# sys.stdout y sys.stderr quedan como None, y cualquier print() interno
# haría que el programa se cierre solo con un error. Esto lo evita.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import webview

from config import NOMBRE_ASISTENTE
import voz
import personalidad
import memoria
import recordatorios
import imagen_ia
from acciones import normalizar
from main import escuchar, interpretar  # reutilizamos la lógica ya probada


def palabras_activacion() -> list:
    """Frases que activan a Venok en modo voz. Se recalculan cada vez para
    reflejar el nombre actual (el usuario puede cambiarlo con 'llámate X').
    No es un wake-word de bajo consumo como los de verdad tipo "Ok Google"
    — sigue usando la misma API de reconocimiento de antes — pero sí evita
    que responda a cualquier cosa que se diga cerca del micrófono."""
    nombre = normalizar(memoria.obtener_nombre_asistente() or NOMBRE_ASISTENTE)
    return [f"oye {nombre}", f"hola {nombre}", f"ey {nombre}", nombre]


ventana = None
modo_actual = "voz"  # "voz" o "texto", lo cambia la interfaz


def actualizar_estado(estado: str) -> None:
    if ventana:
        ventana.evaluate_js(f"venokUI.cambiarEstado('{estado}')")


def _escapar_para_js(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


def agregar_mensaje_chat(remitente: str, texto: str) -> None:
    if not ventana:
        return
    ventana.evaluate_js(f"venokUI.agregarMensaje('{remitente}', '{_escapar_para_js(texto)}')")


def agregar_actividad(texto: str) -> None:
    if not ventana:
        return
    ventana.evaluate_js(f"venokUI.agregarActividad('{_escapar_para_js(texto)}')")


def agregar_imagen_chat(miniatura_base64: str, texto: str) -> None:
    """Muestra en el chat la foto que adjuntó el usuario. El base64 no
    necesita escaparse (solo trae letras, dígitos, '+', '/' y '='), pero
    el texto sí."""
    if not ventana:
        return
    ventana.evaluate_js(
        f"venokUI.agregarImagenUsuario('{miniatura_base64}', '{_escapar_para_js(texto)}')"
    )


def hablar_ui(texto: str) -> None:
    agregar_mensaje_chat("venok", texto)
    actualizar_estado("hablando")
    voz.hablar(texto)
    actualizar_estado("reposo")


def procesar_imagen(ruta: str, texto_usuario: str) -> None:
    """Muestra la foto adjuntada en el chat y se la manda a Claude junto
    con lo que haya escrito el usuario. Corre en un hilo aparte porque
    tanto abrir la imagen como la llamada a la API tardan."""
    actualizar_estado("procesando")

    miniatura, para_enviar = imagen_ia.preparar(ruta)
    if not para_enviar:
        actualizar_estado("error")
        hablar_ui("No pude leer esa imagen. ¿Puedes intentar con otro archivo?")
        return

    agregar_imagen_chat(miniatura, texto_usuario)
    agregar_actividad(f"Imagen adjuntada: {os.path.basename(ruta)}")

    respuesta = imagen_ia.analizar(
        para_enviar,
        texto_usuario,
        memoria.obtener_tono(),
        memoria.obtener_nombre_asistente() or NOMBRE_ASISTENTE,
    )
    hablar_ui(respuesta)


def procesar_comando(texto_usuario: str) -> None:
    """Punto único que procesa un comando, venga de voz o de texto."""
    actualizar_estado("procesando")
    try:
        respuesta = interpretar(texto_usuario)
    except Exception as error:
        print(f"[Venok] Error al interpretar comando: {error}")
        actualizar_estado("error")
        agregar_actividad(f'Error al procesar "{texto_usuario}"')
        hablar_ui("Tuve un problema procesando eso. ¿Puedes repetirlo?")
        return

    if respuesta == "SALIR":
        agregar_actividad("Sesión finalizada por el usuario.")
        hablar_ui(personalidad.despedida())
        return

    if respuesta:
        agregar_actividad(f'"{texto_usuario}" → {respuesta}')
        hablar_ui(respuesta)
    else:
        actualizar_estado("reposo")


def quitar_palabra_activacion(texto: str):
    """Si el texto empieza con una palabra de activación, regresa el resto
    del comando (sin ella). Si no la trae, regresa None."""
    texto_norm = normalizar(texto)
    for palabra in palabras_activacion():
        if texto_norm.startswith(palabra):
            resto = texto[len(palabra):].strip(" ,.:")
            return resto
    return None


def bucle_voz() -> None:
    """Corre en un hilo aparte durante toda la vida del programa. Solo
    procesa algo si detecta la palabra de activación primero, y solo
    escucha activamente cuando el modo actual es 'voz'."""
    while True:
        if modo_actual != "voz":
            time.sleep(0.3)
            continue

        actualizar_estado("escuchando")
        comando = escuchar()
        actualizar_estado("reposo")

        if not comando:
            continue

        resto = quitar_palabra_activacion(comando)
        if resto is None:
            continue  # no dijo "Venok" primero, lo ignoramos en silencio

        agregar_mensaje_chat("usuario", comando)
        procesar_comando(resto if resto else comando)


class VenokAPI:
    """Métodos que la interfaz (JavaScript) puede llamar directamente,
    vía window.pywebview.api.<metodo>(...) desde el lado de la interfaz."""

    def enviar_texto(self, texto: str):
        if not texto or not texto.strip():
            return
        agregar_mensaje_chat("usuario", texto)
        threading.Thread(target=procesar_comando, args=(texto,), daemon=True).start()

    def adjuntar_imagen(self, texto: str = ""):
        """Abre el selector de archivos nativo para elegir una foto. El
        diálogo se abre aquí mismo (es rápido y necesita el hilo de la
        ventana); el análisis se va a un hilo aparte para no congelar la
        interfaz mientras responde la API."""
        if not ventana:
            return

        seleccion = ventana.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("Imágenes (*.png;*.jpg;*.jpeg;*.gif;*.webp;*.bmp)", "Todos los archivos (*.*)"),
        )
        if not seleccion:
            return  # el usuario canceló

        ruta = seleccion[0]
        threading.Thread(
            target=procesar_imagen, args=(ruta, texto or ""), daemon=True
        ).start()

    def cambiar_modo(self, modo: str):
        global modo_actual
        if modo in ("voz", "texto"):
            modo_actual = modo
        return modo_actual

    def obtener_configuracion(self):
        return {
            "nombre_asistente": memoria.obtener_nombre_asistente() or NOMBRE_ASISTENTE,
            "tono": memoria.obtener_tono(),
            "apariencia": memoria.obtener_apariencia(),
        }

    def establecer_apariencia(self, apariencia):
        memoria.establecer_apariencia(apariencia)

    def establecer_nombre_asistente(self, nombre: str):
        if nombre and nombre.strip():
            memoria.establecer_nombre_asistente(nombre)

    def establecer_tono(self, tono: str):
        memoria.establecer_tono(tono)


def iniciar() -> None:
    global ventana
    ruta_ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "index.html")

    api = VenokAPI()
    ventana = webview.create_window(
        "Venok",
        ruta_ui,
        width=1200,
        height=800,
        background_color="#050814",
        js_api=api,
    )

    def saludo_inicial():
        time.sleep(3)  # deja correr la animación de inicio (~2.9s) antes de hablar
        nombre_asistente = memoria.obtener_nombre_asistente() or NOMBRE_ASISTENTE
        hablar_ui(f"{nombre_asistente} en línea. " + personalidad.saludo(memoria.obtener_nombre()))

    def avisar_recordatorio(mensaje: str):
        agregar_actividad(f"⏰ {mensaje}")
        hablar_ui(mensaje)

    threading.Thread(target=saludo_inicial, daemon=True).start()
    threading.Thread(target=bucle_voz, daemon=True).start()
    recordatorios.iniciar_verificador(avisar_recordatorio)

    webview.start()


if __name__ == "__main__":
    iniciar()
