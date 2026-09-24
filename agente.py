"""
Agente de IA: le da a Claude acceso a las capacidades reales de Venok.

El problema que resuelve: las reglas de main.py son rápidas y gratis, pero
solo entienden frases casi exactas. "Recuérdame en media hora sacar la ropa"
no tenía números que parsear, y "el clima de Madrid" (con "de" en vez de
"en") terminaba dando el clima de la ciudad por defecto, sin avisar que se
había equivocado.

Cómo encaja: las reglas siguen yendo primero. Solo cuando ninguna coincide
se llama aquí, y en esa misma llamada Claude decide si usar una herramienta
o simplemente conversar — así que no cuesta una llamada extra respecto a lo
que ya se hacía antes.

Las acciones sensibles siguen pasando por permisos.py: que la decisión venga
de la IA no la exime de pedir confirmación.
"""

import datetime

import acciones
import archivos
import capacidades
import claude_api
import monitoreo
import permisos
import recordatorios


def _opciones(diccionario) -> list:
    return sorted(diccionario)


def definir_herramientas() -> list:
    """Las capacidades que Venok le ofrece a Claude. Las listas de nombres
    válidos se arman desde los mismos diccionarios que usan los comandos,
    para que nunca se desincronicen."""
    return [
        {
            "name": "crear_recordatorio",
            "description": (
                "Programa un recordatorio para avisarle al usuario más tarde. "
                "Úsala cuando pida que le recuerdes algo, sin importar cómo "
                "exprese el momento ('en media hora', 'el viernes a las 3')."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "tarea": {
                        "type": "string",
                        "description": "Qué hay que recordarle, en pocas palabras.",
                    },
                    "fecha_hora": {
                        "type": "string",
                        "description": (
                            "Momento exacto en formato ISO 8601 "
                            "(AAAA-MM-DDTHH:MM), calculado a partir de la fecha actual."
                        ),
                    },
                },
                "required": ["tarea", "fecha_hora"],
            },
        },
        {
            "name": "consultar_clima",
            "description": "Dice el clima actual de una ciudad.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ciudad": {
                        "type": "string",
                        "description": "Nombre de la ciudad. Omitir para usar la del usuario.",
                    }
                },
            },
        },
        {
            "name": "consultar_hora",
            "description": "Dice la hora actual, opcionalmente en otro país.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pais": {"type": "string", "description": "País, si preguntan por otro lugar."}
                },
            },
        },
        {
            "name": "abrir_aplicacion",
            "description": "Abre un programa instalado en la computadora.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "enum": _opciones(acciones.APPS)}
                },
                "required": ["nombre"],
            },
        },
        {
            "name": "abrir_sitio_web",
            "description": (
                "Abre una página web, sin buscar nada en ella. Si además quieren "
                "buscar algo, usa buscar_en_sitio en lugar de esta."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "enum": _opciones(acciones.SITIOS)}
                },
                "required": ["nombre"],
            },
        },
        {
            "name": "buscar_en_sitio",
            "description": (
                "Abre un sitio con una búsqueda ya hecha. Úsala para cosas como "
                "'busca recetas de pizza' o 'pon música de los 80 en YouTube'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "sitio": {"type": "string", "enum": _opciones(acciones.SITIOS_CON_BUSQUEDA)},
                    "busqueda": {"type": "string", "description": "Qué buscar."},
                },
                "required": ["sitio", "busqueda"],
            },
        },
        {
            "name": "cerrar_aplicacion",
            "description": "Cierra un programa abierto. Le pedirá confirmación al usuario.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "enum": _opciones(capacidades.PROCESOS)}
                },
                "required": ["nombre"],
            },
        },
        {
            "name": "traducir_texto",
            "description": "Traduce una frase a otro idioma.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "texto": {"type": "string"},
                    "idioma": {"type": "string", "enum": _opciones(capacidades.IDIOMAS)},
                },
                "required": ["texto", "idioma"],
            },
        },
        {
            "name": "estado_del_sistema",
            "description": "Informa el uso de procesador, memoria, disco y batería del equipo.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "buscar_archivo",
            "description": "Busca un archivo en Escritorio, Descargas y Documentos.",
            "input_schema": {
                "type": "object",
                "properties": {"nombre": {"type": "string"}},
                "required": ["nombre"],
            },
        },
        # El volumen y la reproducción ya existían como comandos, pero no como
        # herramientas. Al conversar eso se notaba: ante un "súbelo otra vez"
        # el modelo contestaba que lo hacía y en realidad no tocaba nada.
        {
            "name": "controlar_volumen",
            "description": (
                "Sube, baja o silencia el volumen del equipo. Úsala también para "
                "seguimientos como 'súbelo otra vez' o 'un poco más'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "enum": ["subir", "bajar", "silenciar"]}
                },
                "required": ["accion"],
            },
        },
        {
            "name": "controlar_reproduccion",
            "description": (
                "Controla la música o el video que ya esté sonando: reproducir o "
                "pausar, pasar a la siguiente canción o volver a la anterior."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "enum": ["reproducir", "siguiente", "anterior"]}
                },
                "required": ["accion"],
            },
        },
    ]


def _crear_recordatorio(argumentos) -> str:
    tarea = (argumentos.get("tarea") or "").strip()
    if not tarea:
        return "¿De qué quieres que te recuerde?"
    try:
        momento = datetime.datetime.fromisoformat(argumentos.get("fecha_hora", ""))
    except ValueError:
        return "No entendí para cuándo era el recordatorio. ¿Me repites la hora?"

    if momento <= datetime.datetime.now():
        return "Esa hora ya pasó. ¿Para cuándo lo quieres?"
    return recordatorios.agregar(tarea, momento)


def _cerrar_aplicacion(argumentos) -> str:
    proceso = capacidades.PROCESOS.get(argumentos.get("nombre", ""))
    if not proceso:
        return "No tengo registrada esa aplicación para cerrarla."
    return permisos.confirmar_cierre_de_app(proceso)


def ejecutar(nombre: str, argumentos: dict) -> str:
    """Corre la herramienta que eligió Claude y regresa lo que Venok dirá."""
    argumentos = argumentos or {}

    if nombre == "crear_recordatorio":
        return _crear_recordatorio(argumentos)
    if nombre == "consultar_clima":
        return capacidades.clima(argumentos.get("ciudad"))
    if nombre == "consultar_hora":
        pais = argumentos.get("pais")
        return capacidades.hora_en_pais(pais) if pais else capacidades.hora_actual()
    if nombre == "abrir_aplicacion":
        return acciones.abrir_app(argumentos.get("nombre", ""))
    if nombre == "abrir_sitio_web":
        return acciones.abrir_sitio(argumentos.get("nombre", ""))
    if nombre == "buscar_en_sitio":
        return acciones.abrir_sitio_con_busqueda(
            argumentos.get("sitio", ""), argumentos.get("busqueda", "")
        )
    if nombre == "cerrar_aplicacion":
        return _cerrar_aplicacion(argumentos)
    if nombre == "traducir_texto":
        return capacidades.traducir(argumentos.get("texto", ""), argumentos.get("idioma", ""))
    if nombre == "estado_del_sistema":
        return monitoreo.resumen_sistema()
    if nombre == "buscar_archivo":
        return archivos.buscar_archivo(argumentos.get("nombre", ""))
    if nombre == "controlar_volumen":
        return capacidades.volumen(argumentos.get("accion", ""))
    if nombre == "controlar_reproduccion":
        return capacidades.multimedia(argumentos.get("accion", ""))

    return None


_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _calendario_proximo() -> str:
    """Lista los próximos días con su fecha ya resuelta. Pedirle al modelo que
    calcule '¿qué fecha es el viernes?' es donde se equivoca; dándole el
    calendario hecho, solo tiene que leerlo."""
    hoy = datetime.datetime.now()
    proximos = []
    for adelanto in range(1, 8):
        dia = hoy + datetime.timedelta(days=adelanto)
        proximos.append(f"{_DIAS[dia.weekday()]} {dia.strftime('%d/%m')}")
    return ", ".join(proximos)


def _instruccion(tono: str, nombre_asistente: str) -> str:
    ahora = datetime.datetime.now()
    return (
        claude_api.instruccion_de_sistema(tono, nombre_asistente)
        + f" Ahora mismo es {_DIAS[ahora.weekday()]} "
        f"{ahora.strftime('%d/%m/%Y a las %H:%M')}. Los próximos días son: "
        f"{_calendario_proximo()}. Úsalos para resolver fechas relativas. "
        f"Si el usuario pide algo que puedas hacer con una herramienta, úsala en vez "
        f"de decir que no puedes. Si no aplica ninguna, simplemente responde conversando. "
        # Los mensajes anteriores que se mandan como historial incluyen lo que
        # Venok respondió con sus propias reglas (la hora, un chiste, "abriendo
        # Spotify"). Sin esta instrucción el modelo los ignora y contesta como
        # si cada pregunta fuera la primera.
        f"Hablan como dos amigos: los mensajes anteriores son parte de la MISMA "
        f"conversación, incluidos los que respondiste tú. Cuando la persona diga "
        f"algo que solo se entiende mirando atrás ('otro', '¿y por qué?', "
        f"'repite eso', 'más'), resuélvelo con lo último que se dijo en vez de "
        f"preguntar a qué se refiere. Enlaza con lo anterior con naturalidad y no "
        f"repitas la pregunta antes de responder. "
        f"Nunca digas que hiciste algo si no lo hiciste con una herramienta: "
        f"si no tienes con qué hacerlo, dilo claramente."
    )


def atender(pregunta: str, tono: str = "amigable", nombre_asistente: str = "Venok"):
    """Punto de entrada: Claude decide si usar una capacidad de Venok o
    conversar. Regresa el texto que Venok dirá, o None si no hay API key o
    la llamada falló, para que main.py use su propio respaldo."""
    if not claude_api.hay_api_key():
        return None

    herramienta, datos = claude_api.preguntar_con_herramientas(
        pregunta,
        definir_herramientas(),
        sistema=_instruccion(tono, nombre_asistente),
        historial=claude_api.obtener_historial(),
    )

    # Nota: aquí ya NO se guarda el intercambio. Lo hace main.interpretar()
    # para todas las respuestas por igual (reglas, Wolfram y agente); si se
    # guardara en los dos sitios, las del agente saldrían duplicadas.
    if herramienta:
        return ejecutar(herramienta, datos) or None

    return datos
