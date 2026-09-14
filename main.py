"""
Venok - Asistente de voz personal (estilo Jarvis)

Uso:
    python main.py
"""

import re

import speech_recognition as sr

from config import NOMBRE_ASISTENTE, IDIOMA_RECONOCIMIENTO
from voz import hablar
import acciones
from acciones import normalizar
import control_mouse_teclado as control
import personalidad
import capacidades
import memoria
import permisos
import monitoreo
import archivos
import recordatorios
import inicio_automatico
import analisis_equipo
import navegador_ia
import claude_api
import correo
import agente

reconocedor = sr.Recognizer()

PALABRAS_REDES_SOCIALES = {"facebook", "instagram"}

_microfono_calibrado = False


def escuchar() -> str:
    global _microfono_calibrado
    with sr.Microphone() as fuente:
        # Calibrar el ruido ambiental cuesta medio segundo, y antes se hacía
        # en CADA ciclo de escucha. Con hacerlo una vez basta: el
        # reconocedor sigue ajustando el umbral solo mientras escucha
        # (dynamic_energy_threshold).
        if not _microfono_calibrado:
            reconocedor.adjust_for_ambient_noise(fuente, duration=0.8)
            _microfono_calibrado = True
        print("Escuchando...")
        try:
            audio = reconocedor.listen(fuente, timeout=6, phrase_time_limit=6)
        except sr.WaitTimeoutError:
            return ""

    try:
        texto = reconocedor.recognize_google(audio, language=IDIOMA_RECONOCIMIENTO)
        print(f"Escuché: {texto}")
        return texto
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as error:
        print(f"Error con el servicio de reconocimiento: {error}")
        return ""


_PATRON_ENVIAR_CORREO = re.compile(
    r"(?:envia|manda|escribe)(?:le)?\s+un\s+correo\s+a\s+(.+?)\s+"
    r"(?:diciendo(?:le)?\s+(?:que\s+)?|con\s+el\s+mensaje\s+)(.+?)\s*[.]?$"
)
_PATRON_TRADUCIR = re.compile(r"traduce(?:me)?\s+(.+?)\s+a[lo]?\s+(\w+)\s*[.?]?$")
_PATRON_COMO_SE_DICE = re.compile(r"como\s+se\s+dice\s+(.+?)\s+en\s+(\w+)\s*[.?]?$")

PALABRAS_DE_DATOS = (
    "distancia", "masa", "velocidad", "densidad", "temperatura", "raiz",
    "poblacion", "altura", "peso", "equivale", "formula", "orbita",
    "cuantos", "cuantas", "cuanta",
)


def _abrir_sitio_con_permiso(nombre: str) -> str:
    if nombre in PALABRAS_REDES_SOCIALES:
        return permisos.solicitar(
            personalidad.sugerencia("abrir_red_social"),
            lambda: acciones.abrir_sitio(nombre),
            mensaje_cancelado="Entendido, no la abro por ahora.",
        )
    return acciones.abrir_sitio(nombre)


# Palabras que siguen a "de"/"en" pero NO son una ciudad ("el clima de hoy").
_NO_SON_CIUDADES = {"hoy", "manana", "ahora", "aqui", "aca", "mi ciudad", "esta semana"}


def _ciudad_del_comando(comando: str, comando_norm: str):
    """Saca la ciudad de frases como 'clima en Madrid' o 'clima de Madrid'.
    Antes solo se aceptaba 'en', así que 'el clima de Madrid' respondía con
    la ciudad por defecto sin avisar que se había equivocado."""
    for separador in (" en ", " de "):
        if separador in comando_norm:
            candidata = comando.split(separador, 1)[-1].strip(" ?¿.,!¡")
            if candidata and normalizar(candidata) not in _NO_SON_CIUDADES:
                return candidata
    return None


def _parece_pregunta_de_datos(comando_norm: str) -> bool:
    """Si la pregunta trae números o pide una magnitud concreta, conviene
    mandarla a Wolfram Alpha antes que a Claude: es más preciso para eso,
    y no cuesta."""
    if re.search(r"\d", comando_norm):
        return True
    return any(palabra in comando_norm for palabra in PALABRAS_DE_DATOS)


def interpretar(comando: str) -> str:
    if not comando:
        return ""

    comando_norm = normalizar(comando)

    # --- Confirmación pendiente ---
    # Si Venok acaba de pedir confirmación para una acción sensible, lo que
    # sea que diga el usuario ahora se interpreta como esa respuesta (sí/no),
    # sin importar si vino por voz o por texto.
    if permisos.hay_pendiente():
        return permisos.resolver(comando_norm)

    # --- Memoria: datos del usuario ---
    if comando_norm.startswith("me llamo ") or comando_norm.startswith("mi nombre es "):
        nombre = re.sub(r"^(me llamo|mi nombre es)\s*", "", comando_norm).strip()
        if not nombre:
            return "¿Cuál es tu nombre?"
        memoria.establecer_nombre(nombre)
        return f"Un gusto, {nombre.title()}. Lo recordaré."

    if comando_norm.startswith("mi ciudad es ") or comando_norm.startswith("vivo en "):
        ciudad = re.sub(r"^(mi ciudad es|vivo en)\s*", "", comando_norm).strip()
        if not ciudad:
            return "¿En qué ciudad vives?"
        memoria.establecer_ciudad_favorita(ciudad)
        return f"Listo, guardé {ciudad.title()} como tu ciudad."

    if "olvida mis datos" in comando_norm or "borra tu memoria" in comando_norm or "olvida lo que sabes de mi" in comando_norm:
        memoria.olvidar_todo()
        return "Listo, olvidé tu nombre y tu ciudad guardados."

    # --- Personalización de Venok (nombre del asistente y tono) ---
    if comando_norm.startswith("llamate ") or comando_norm.startswith("cambiate el nombre a ") or comando_norm.startswith("tu nombre es "):
        nuevo_nombre = re.sub(r"^(llamate|cambiate el nombre a|tu nombre es)\s*", "", comando_norm).strip()
        if not nuevo_nombre:
            return "¿Cómo quieres que me llame?"
        memoria.establecer_nombre_asistente(nuevo_nombre)
        return f"Listo, desde ahora me llamo {nuevo_nombre.title()}."

    if "modo formal" in comando_norm or "se mas formal" in comando_norm or "tono formal" in comando_norm:
        memoria.establecer_tono("formal")
        return "Entendido. Hablaré de manera más formal a partir de ahora."

    if "modo gracioso" in comando_norm or "se mas gracioso" in comando_norm or "tono gracioso" in comando_norm or "hazte el chistoso" in comando_norm:
        memoria.establecer_tono("gracioso")
        return "¡Hecho! Prepárate para mi lado más divertido."

    if "modo amigable" in comando_norm or "tono normal" in comando_norm or "tono amigable" in comando_norm:
        memoria.establecer_tono("amigable")
        return "Listo, vuelvo a mi tono normal."

    # --- Inicio automático con Windows ---
    frases_activar_inicio = ("inicia con windows", "abrete con windows", "arranca con windows", "activate al iniciar windows")
    if any(frase in comando_norm for frase in frases_activar_inicio):
        return permisos.solicitar(
            "Esto hará que me abra solo cada vez que inicies sesión en Windows. ¿Confirmas?",
            inicio_automatico.activar,
            mensaje_cancelado="Entendido, no me abriré automáticamente.",
        )

    if "no inicies con windows" in comando_norm or "desactiva el inicio automatico" in comando_norm or "quita el inicio automatico" in comando_norm:
        return inicio_automatico.desactivar()

    if "inicio automatico" in comando_norm:
        estado = "activado" if inicio_automatico.esta_activado() else "desactivado"
        return f"El inicio automático con Windows está {estado}."

    # --- Correo ---
    if ("correo" in comando_norm or "correos" in comando_norm) and any(
        palabra in comando_norm for palabra in ("revisa", "tengo", "nuevos", "sin leer", "bandeja")
    ):
        return correo.revisar()

    coincidencia_correo = _PATRON_ENVIAR_CORREO.search(comando_norm)
    if coincidencia_correo:
        destinatario = correo.resolver_destinatario(coincidencia_correo.group(1))
        if not destinatario:
            return (f"No sé a qué dirección mandarle a {coincidencia_correo.group(1)}. "
                    f"Puedes agregarlo a la agenda en correo.py o decirme la dirección completa.")
        # El mensaje se recorta del comando ORIGINAL para no perder acentos.
        cuerpo = comando[coincidencia_correo.start(2):coincidencia_correo.end(2)].strip()
        if not cuerpo:
            return "¿Qué quieres que le diga?"
        return permisos.solicitar(
            f'Voy a enviarle a {destinatario} el mensaje: "{cuerpo}". ¿Lo mando?',
            lambda: correo.enviar(destinatario, cuerpo),
            mensaje_cancelado="Entendido, no envío el correo.",
        )

    # --- Recordatorios ---
    if comando_norm.startswith("recuerdame"):
        respuesta_recordatorio = recordatorios.crear_desde_comando(comando_norm[len("recuerdame"):])
        if respuesta_recordatorio:
            return respuesta_recordatorio
        # No se entendió la fecha: sigue de largo para que el agente de IA lo
        # intente, en vez de responder con un callejón sin salida.

    if "cancela" in comando_norm and "recordatorio" in comando_norm:
        recordatorios.cancelar_todos()
        return "Listo, cancelé todos tus recordatorios pendientes."

    if "recordatorios" in comando_norm:
        return recordatorios.listar_pendientes()

    # --- Ayuda ---
    if "ayuda" in comando_norm or "que puedes hacer" in comando_norm:
        return (
            "Puedo abrir y cerrar aplicaciones, sitios web y juegos, buscar cosas, "
            "controlar el mouse y teclado, decirte el clima, noticias, hora y fecha, "
            "hacer cálculos, definir palabras, convertir monedas, controlar el volumen "
            "y la música, crear carpetas, tomar capturas, y hasta contarte un chiste. "
            "También puedo recordar tu nombre y tu ciudad si me los dices, por ejemplo "
            "'me llamo Ana' o 'mi ciudad es Madrid'. Además reviso el uso de procesador, "
            "memoria, disco y batería, busco, abro o elimino archivos en tus carpetas, "
            "y puedo poner recordatorios, como 'recuérdame llamar a mamá mañana a las 5'. "
            "También puedes cambiarme el nombre ('llámate Jarvis') o mi tono "
            "('modo formal', 'modo gracioso', 'modo amigable'), y decirme que "
            "'inicie con Windows' para abrirme solo al encender tu computadora. "
            "Puedo darte las especificaciones de tu equipo y sus programas instalados, "
            "investigar temas en internet y resumírtelos con inteligencia artificial, "
            "traducir a varios idiomas, por ejemplo 'traduce buenos días al inglés', "
            "y revisar o enviar correos si configuraste tu cuenta. "
            "Si no reconozco un comando, hago lo posible por conversar contigo de todos modos."
        )

    # --- Diversión ---
    if "chiste" in comando_norm:
        return capacidades.chiste()
    if "lanza una moneda" in comando_norm or "tira una moneda" in comando_norm or "cara o cruz" in comando_norm:
        return capacidades.lanzar_moneda()
    if "lanza un dado" in comando_norm or "tira un dado" in comando_norm:
        return capacidades.lanzar_dado()

    # --- Información ---
    if "clima" in comando_norm or "tiempo" in comando_norm:
        ciudad = _ciudad_del_comando(comando, comando_norm)
        if not ciudad:
            # Sin ciudad explícita: usa la última consultada en esta sesión,
            # luego la ciudad favorita guardada, antes de caer al valor por
            # defecto de capacidades.py.
            ciudad = memoria.obtener_contexto("ultima_ciudad") or memoria.obtener_ciudad_favorita()
        memoria.recordar_contexto("ultima_ciudad", ciudad or capacidades.CIUDAD_DEFECTO)
        return capacidades.clima(ciudad)

    if "noticia" in comando_norm:
        return capacidades.noticias()

    if "que hora es" in comando_norm:
        if " en " in comando_norm:
            pais = comando.split(" en ", 1)[-1].strip()
            return capacidades.hora_en_pais(pais)
        return capacidades.hora_actual()
    if "que dia es" in comando_norm or "que fecha es" in comando_norm:
        return capacidades.fecha_actual()

    if comando_norm.startswith("que es ") or comando_norm.startswith("define ") or "definicion de" in comando_norm:
        termino = re.sub(r"^(que es|define|definicion de)\s*", "", comando_norm).strip()
        return capacidades.definir(termino)

    # --- Traductor ---
    # La detección se hace sobre el texto normalizado (para que funcione con
    # o sin tildes), pero lo que se traduce se recorta del comando ORIGINAL,
    # así no se pierden los acentos de la frase.
    for patron in (_PATRON_TRADUCIR, _PATRON_COMO_SE_DICE):
        coincidencia = patron.search(comando_norm)
        if coincidencia:
            texto_a_traducir = comando[coincidencia.start(1):coincidencia.end(1)]
            return capacidades.traducir(texto_a_traducir, coincidencia.group(2))

    if "convierte" in comando_norm and " a " in comando_norm:
        respuesta_moneda = capacidades.convertir_moneda_comando(comando)
        if respuesta_moneda:
            return respuesta_moneda
        # No eran monedas (grados, kilómetros, kilos...): se deja seguir para
        # que termine en Wolfram Alpha, que sí resuelve unidades.

    # --- Control de navegador con IA (busca, abre y resume con Claude) ---
    if comando_norm.startswith("investiga sobre ") or comando_norm.startswith("investiga "):
        tema = re.sub(r"^investiga(\s+sobre)?\s*", "", comando_norm).strip()
        return navegador_ia.buscar_y_resumir(tema)

    if comando_norm.startswith("resume la pagina ") or comando_norm.startswith("resume el sitio ") or comando_norm.startswith("resume esta pagina "):
        url = re.sub(r"^resume\s+(la pagina|el sitio|esta pagina)\s*", "", comando_norm).strip()
        return navegador_ia.resumir_pagina(url)

    # --- Calculadora ---
    if "cuanto es" in comando_norm or comando_norm.startswith("calcula"):
        expresion = re.sub(r"^(cuanto es|calcula)\s*", "", comando_norm).strip()
        return capacidades.calcular(expresion)

    # --- Sistema ---
    if "sube el volumen" in comando_norm or "sube volumen" in comando_norm:
        return capacidades.volumen("subir")
    if "baja el volumen" in comando_norm or "baja volumen" in comando_norm:
        return capacidades.volumen("bajar")
    if "silencia" in comando_norm or "mutea" in comando_norm:
        return capacidades.volumen("silenciar")

    if "bloquea la pantalla" in comando_norm or "bloquear pantalla" in comando_norm:
        return capacidades.bloquear_pantalla()

    if "vacia la papelera" in comando_norm or "vaciar papelera" in comando_norm:
        return permisos.solicitar(
            personalidad.sugerencia("accion_riesgosa"),
            capacidades.vaciar_papelera,
            mensaje_cancelado="Entendido, no vacío la papelera.",
        )

    # --- Monitoreo del sistema (solo lectura, sin confirmación) ---
    if "como esta mi computadora" in comando_norm or "estado del sistema" in comando_norm or "informacion del sistema" in comando_norm:
        return monitoreo.resumen_sistema()

    if (("programas" in comando_norm or "procesos" in comando_norm) and "abiertos" in comando_norm) or "que esta corriendo" in comando_norm:
        return monitoreo.procesos_principales()

    if "cpu" in comando_norm or "procesador" in comando_norm:
        return monitoreo.uso_cpu()

    # Ojo: "ram"/"memoria" a secas chocarían con palabras como "programa"
    # (contiene "ram") o con la memoria de nombre/ciudad de más arriba, por
    # eso se piden frases más completas y específicas.
    if "ram" in comando_norm.split() or "memoria ram" in comando_norm or "uso de memoria" in comando_norm:
        return monitoreo.uso_ram()

    if "espacio en disco" in comando_norm or "espacio libre" in comando_norm or "disco duro" in comando_norm:
        return monitoreo.espacio_disco()

    if "bateria" in comando_norm:
        return monitoreo.estado_bateria()

    # --- Análisis del equipo (specs e inventario, no uso en vivo) ---
    if "especificaciones" in comando_norm or "que computadora tengo" in comando_norm or "analisis del equipo" in comando_norm:
        return analisis_equipo.especificaciones()

    if "programas instalados" in comando_norm:
        return analisis_equipo.programas_instalados()

    # --- Multimedia ---
    if "reproduce" in comando_norm or "pausa la musica" in comando_norm or comando_norm.strip() == "play":
        return capacidades.multimedia("reproducir")
    if "siguiente cancion" in comando_norm:
        return capacidades.multimedia("siguiente")
    if "cancion anterior" in comando_norm:
        return capacidades.multimedia("anterior")

    # --- Captura de pantalla ---
    if "captura" in comando_norm:
        return capacidades.captura_pantalla()

    # --- Archivos y carpetas ---
    if "crea una carpeta" in comando_norm or "crea carpeta" in comando_norm:
        nombre = re.sub(r"^.*carpeta( llamada| que se llame)?\s*", "", comando_norm).strip()
        return capacidades.crear_carpeta(nombre)

    # --- Cerrar aplicación ---
    if "cierra" in comando_norm or "cerrar" in comando_norm:
        for nombre, proceso in capacidades.PROCESOS.items():
            if normalizar(nombre) in comando_norm:
                return permisos.confirmar_cierre_de_app(proceso)

        # Sin nombre explícito ("ciérrala", "cierra eso"): usa la última
        # app que Venok abrió en esta sesión, si conoce su proceso.
        if "eso" in comando_norm or "cierrala" in comando_norm or "cierralo" in comando_norm:
            ultima_app = memoria.obtener_contexto("ultima_app")
            proceso = capacidades.PROCESOS.get(ultima_app) if ultima_app else None
            if proceso:
                return permisos.confirmar_cierre_de_app(proceso)
            return "No recuerdo qué aplicación abrí para cerrarla."

        parecido = acciones.buscar_parecido(comando_norm, capacidades.PROCESOS)
        if parecido:
            return permisos.confirmar_cierre_de_app(capacidades.PROCESOS[parecido])

        return "¿Qué aplicación quiere que cierre?"

    # --- Control de mouse y teclado (accesibilidad) ---
    if "mueve el mouse" in comando_norm or "mover el mouse" in comando_norm:
        for direccion in ("arriba", "abajo", "izquierda", "derecha"):
            if direccion in comando_norm:
                return control.mover_mouse(direccion)
        return "¿Hacia dónde muevo el mouse?"

    if "clic derecho" in comando_norm:
        return control.clic("derecho")
    if "doble clic" in comando_norm:
        return control.doble_clic()
    if "haz clic" in comando_norm or comando_norm.strip() == "clic":
        return control.clic("izquierdo")

    if re.search(r"\bescribe\b", comando_norm):
        # Se busca "escribe" en el comando ORIGINAL (sin normalizar, sin
        # distinguir mayúsculas) para no perder el texto exacto que hay que
        # escribir. Si se usara comando_norm perdería mayúsculas y tildes
        # del texto a escribir.
        coincidencia = re.search(r"escribe\b", comando, re.IGNORECASE)
        texto = comando[coincidencia.end():].strip() if coincidencia else ""
        return control.escribir_texto(texto) if texto else "¿Qué quiere que escriba?"

    if "presiona" in comando_norm or "presionar" in comando_norm:
        for tecla in ("enter", "espacio", "escape", "esc", "tabulador", "tab", "borrar"):
            if tecla in comando_norm:
                return control.presionar_tecla(tecla)
        return "¿Qué tecla presiono?"

    if "desplaza" in comando_norm or "scroll" in comando_norm:
        direccion = "abajo" if "abajo" in comando_norm else "arriba"
        return control.desplazar(direccion)

    # --- Archivos: buscar, abrir, eliminar ---
    if "archivo" in comando_norm and ("busca" in comando_norm or "encuentra" in comando_norm or "encontrar" in comando_norm):
        nombre_archivo = comando_norm.split("archivo", 1)[-1].strip()
        return archivos.buscar_archivo(nombre_archivo)

    if "archivo" in comando_norm and ("abre" in comando_norm or "abrir" in comando_norm):
        nombre_archivo = comando_norm.split("archivo", 1)[-1].strip()
        return archivos.abrir_archivo(nombre_archivo)

    if "archivo" in comando_norm and any(palabra in comando_norm for palabra in ("elimina", "eliminar", "borra", "borrar")):
        nombre_archivo = comando_norm.split("archivo", 1)[-1].strip()
        if not nombre_archivo:
            return "¿Qué archivo quieres que elimine?"
        ruta, nombre_visible, error = archivos.preparar_eliminacion(nombre_archivo)
        if error:
            return error
        return permisos.solicitar(
            f"¿Confirmas que quieres eliminar {nombre_visible}? Se enviará a la papelera de reciclaje.",
            lambda ruta=ruta: archivos.eliminar_archivo(ruta),
            mensaje_cancelado="Entendido, no elimino el archivo.",
        )

    # --- Búsquedas en un sitio específico: "busca X en youtube" ---
    if "busca" in comando_norm and " en " in comando_norm:
        try:
            resto = comando_norm.split("busca", 1)[1]
            busqueda, sitio = resto.rsplit(" en ", 1)
            return acciones.abrir_sitio_con_busqueda(sitio.strip(), busqueda.strip())
        except ValueError:
            return "No entendí bien qué y dónde quiere que busque."

    # --- Abrir cosas ---
    if "abre" in comando_norm or "abrir" in comando_norm:
        if "juego" in comando_norm:
            for nombre in acciones.JUEGOS:
                if normalizar(nombre) in comando_norm:
                    return acciones.abrir_juego(nombre)
            parecido = acciones.buscar_parecido(comando_norm, acciones.JUEGOS)
            if parecido:
                return acciones.abrir_juego(parecido)
            return "¿Qué juego quiere que abra?"

        for nombre in capacidades.CARPETAS_COMUNES:
            if normalizar(nombre) in comando_norm:
                return capacidades.abrir_carpeta_comun(nombre)

        for nombre in acciones.APPS:
            if normalizar(nombre) in comando_norm:
                memoria.recordar_contexto("ultima_app", nombre)
                return acciones.abrir_app(nombre)

        for nombre in acciones.SITIOS:
            if normalizar(nombre) in comando_norm:
                return _abrir_sitio_con_permiso(nombre)

        # Nada coincidió exacto. El reconocedor de voz escribe mal los
        # nombres propios muy seguido ("cromo" por "chrome"), así que se
        # busca el más parecido antes de rendirse.
        parecido = acciones.buscar_parecido(comando_norm, acciones.APPS)
        if parecido:
            memoria.recordar_contexto("ultima_app", parecido)
            return acciones.abrir_app(parecido)

        parecido = acciones.buscar_parecido(comando_norm, acciones.SITIOS)
        if parecido:
            return _abrir_sitio_con_permiso(parecido)

        parecido = acciones.buscar_parecido(comando_norm, capacidades.CARPETAS_COMUNES)
        if parecido:
            return capacidades.abrir_carpeta_comun(parecido)

        # Ni exacto ni parecido: se sigue de largo para que el agente de IA
        # lo intente ("abre el navegador y busca recetas de pizza" no nombra
        # ninguna app, pero sí se puede resolver).

    # --- Conversación / personalidad ---
    if "hola" in comando_norm:
        return personalidad.saludo(memoria.obtener_nombre())

    if "gracias" in comando_norm:
        return "Con gusto. Para eso estoy."

    if "adios" in comando_norm or "salir" in comando_norm:
        claude_api.limpiar_historial()
        return "SALIR"

    # --- Último recurso: Wolfram Alpha y Claude, en el orden más conveniente ---
    # Wolfram tarda ~3.5 s (traduce al inglés, consulta, y retraduce) mientras
    # que Claude tarda ~1 s. Por eso Wolfram solo va primero cuando la
    # pregunta parece de cálculo o datos duros, que es donde gana en precisión
    # y además es gratis. Para todo lo demás Claude responde primero, y si no
    # está disponible (sin API key o sin internet) Wolfram queda de respaldo.
    def _intentar_wolfram():
        return capacidades.preguntar_wolfram(comando)

    def _intentar_claude():
        # El agente resuelve las dos cosas en una sola llamada: si lo pedido
        # coincide con alguna capacidad de Venok la ejecuta, y si no,
        # simplemente conversa.
        nombre_asistente = memoria.obtener_nombre_asistente() or NOMBRE_ASISTENTE
        return agente.atender(comando, memoria.obtener_tono(), nombre_asistente)

    if _parece_pregunta_de_datos(comando_norm):
        intentos = (_intentar_wolfram, _intentar_claude)
    else:
        intentos = (_intentar_claude, _intentar_wolfram)

    for intentar in intentos:
        respuesta = intentar()
        if respuesta:
            return respuesta

    return personalidad.no_entendido()


def main() -> None:
    recordatorios.iniciar_verificador(hablar)
    nombre_asistente = memoria.obtener_nombre_asistente() or NOMBRE_ASISTENTE
    hablar(f"{nombre_asistente} en línea. " + personalidad.saludo(memoria.obtener_nombre()))

    while True:
        comando = escuchar()
        try:
            respuesta = interpretar(comando)
        except Exception as error:
            # Igual que en app.py: un comando que falle no debe tumbar a Venok.
            print(f"[Venok] Error al interpretar comando: {error}")
            hablar("Tuve un problema procesando eso. ¿Puedes repetirlo?")
            continue

        if respuesta == "SALIR":
            hablar(personalidad.despedida())
            break

        if respuesta:
            hablar(respuesta)


if __name__ == "__main__":
    main()
