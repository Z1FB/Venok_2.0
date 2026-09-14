# Venok — Asistente de voz personal

Asistente de escritorio para Windows, estilo Jarvis, con interfaz visual
tipo HUD. Escucha comandos por voz o texto, responde con voz, recuerda
datos entre sesiones, pide confirmación antes de acciones sensibles, y
usa IA para entender lo que le pides aunque no lo digas con las palabras
exactas.

Proyecto escolar — ver [`CONTEXTO_PARA_CLAUDE_CODE.md`](CONTEXTO_PARA_CLAUDE_CODE.md)
para el historial de decisiones de diseño.

## Qué puede hacer

- **Agente de IA**: Claude tiene acceso a las capacidades reales de Venok,
  así que entiende frases naturales aunque no coincidan con ningún comando
  ("recuérdame en media hora sacar la ropa", "abre el navegador y busca
  recetas de pizza", "quiero escuchar música de los 80").
- **Conversación con contexto**: mantiene el hilo de los últimos turnos, así
  que funcionan las preguntas de seguimiento ("¿y de los perros?").
- **Memoria y personalidad**: recuerda tu nombre y ciudad entre sesiones;
  puedes cambiarle su propio nombre y su tono (formal / amigable / gracioso).
- **Imágenes**: adjunta una foto desde el chat con el botón 📎 y Venok la
  analiza y te cuenta qué ve.
- **Recordatorios**: "recuérdame llamar a mamá mañana a las 5" — avisa solo,
  en segundo plano, y sobreviven a reiniciar la app.
- **Información**: clima, hora en cualquier país, noticias, definiciones
  (Wikipedia), conversión de monedas y de unidades, calculadora.
- **Traductor**: "traduce buenos días al inglés", "¿cómo se dice niño en
  francés?" — 10 idiomas.
- **Sistema**: apps, sitios web y juegos (abrir/cerrar/buscar), volumen,
  bloquear pantalla, vaciar papelera, multimedia, capturas de pantalla,
  inicio automático con Windows.
- **Monitoreo y análisis del equipo**: uso de CPU/RAM/disco/batería en
  vivo, procesos que más consumen, especificaciones del equipo y
  programas instalados.
- **Archivos**: buscar, abrir y eliminar archivos en tus carpetas
  comunes (eliminar siempre va a la papelera de reciclaje, nunca borrado
  permanente).
- **Investigación web**: abre el navegador y te resume el tema con IA, o
  resume una página concreta que le indiques.
- **Correo** (opcional): revisar la bandeja de entrada y enviar mensajes.
- **Accesibilidad**: control de mouse y teclado por voz (mover, clic,
  escribir, teclas, scroll).
- **Permisos**: cualquier acción sensible (cerrar apps, vaciar la
  papelera, eliminar archivos, enviar correos, abrir redes sociales,
  activar el inicio automático) pide confirmación antes de ejecutarse —
  venga la orden de un comando o del agente de IA.

Todo funciona igual por voz o por texto, y desde `app.py` (con interfaz)
o `main.py` (solo consola).

## Cómo decide qué hacer

Venok intenta resolver cada frase en este orden, para ser rápido y barato
antes de gastar una llamada a la IA:

1. **Reglas** — los comandos conocidos se resuelven al instante y sin costo.
2. **Wolfram Alpha** — solo si la pregunta trae números o pide una magnitud
   ("¿cuántos km hay a la luna?"), que es donde es más preciso y es gratis.
3. **Agente de IA** — en una sola llamada decide si usar una capacidad de
   Venok (con los argumentos ya extraídos) o simplemente conversar.

Si una regla captura la frase pero no logra resolverla, cede el turno al
agente en vez de responder con un callejón sin salida.

## Paso 1 — Instalar Python

Descarga Python 3.10 o superior desde https://www.python.org/downloads/
Al instalar en Windows, marca la casilla **"Add Python to PATH"**.

## Paso 2 — Instalar dependencias

Abre una terminal dentro de la carpeta `venok` y corre:

```bash
pip install -r requirements.txt
```

En Windows, si `pyaudio` da error al instalar, prueba con:
```bash
pip install pipwin
pipwin install pyaudio
```

## Paso 3 — Configurar tu `.env`

Copia `.env.example` como `.env` en la misma carpeta. **El archivo `.env`
nunca debe compartirse ni subirse a internet** — ya está excluido en
`.gitignore` por esa razón.

Todas las claves son opcionales — sin ellas Venok sigue funcionando, solo
sin esa función específica:

| Variable             | Para qué sirve                                          | Dónde conseguirla |
|----------------------|----------------------------------------------------------|--------------------|
| `ELEVENLABS_API_KEY` | Voz más realista (requiere plan pagado, ~$5 USD/mes)     | https://elevenlabs.io |
| `WOLFRAM_APP_ID`     | Respuestas de ciencia/matemáticas/datos (gratis)         | https://developer.wolframalpha.com |
| `ANTHROPIC_API_KEY`  | El agente de IA: entender frases naturales, analizar imágenes, investigar, traducir y conversar (costo mínimo por uso) | https://console.anthropic.com/settings/keys |
| `CORREO_USUARIO` y `CORREO_PASSWORD` | Revisar y enviar correos. La contraseña es una "contraseña de aplicación", no la de tu cuenta | https://myaccount.google.com/apppasswords |

Por defecto (`MOTOR_VOZ=sistema`) Venok habla con las voces que ya trae
Windows, sin necesitar ninguna clave. Si quieres usar ElevenLabs, agrega
`MOTOR_VOZ=elevenlabs` a tu `.env`.

## Paso 4 — Personalizar acciones

Abre `acciones.py` y ajusta a lo que exista en TU laptop:
- `SITIOS` / `SITIOS_CON_BUSQUEDA`: páginas web que Venok puede abrir o buscar.
- `APPS`: aplicaciones instaladas (nombre del ejecutable o ruta completa).
- `JUEGOS`: rutas a tus lanzadores de juegos (Steam, Minecraft Launcher, etc.).

## Paso 5 — Correr la aplicación

```bash
python app.py
```

Abre una ventana con la interfaz visual (núcleo animado tipo HUD, panel
de chat, y animación de arranque). Di "Oye Venok" (o el nombre que le
hayas puesto) antes de cada comando en modo voz.

*(`python main.py` corre el mismo cerebro sin interfaz, solo por consola —
útil para pruebas rápidas.)*

### Algunos comandos para probar

```
Oye Venok, hola
Me llamo Ana
Clima de Madrid
Recuérdame en media hora sacar la ropa
Ponme un recordatorio para el viernes a las 3
Cómo está mi computadora
Traduce buenos días al inglés
Investiga sobre agujeros negros
Quiero escuchar música de los 80
Abre el navegador y busca recetas de pizza
Mueve el mouse a la derecha / Haz clic / Escribe hola / Presiona enter
Llámate Jarvis
Modo gracioso
Ayuda
```

`ayuda` (o "qué puedes hacer") hace que Venok resuma en voz alta todo lo
que sabe hacer. El botón **Herramientas** de la interfaz también muestra
atajos a los comandos más usados, y se ejecutan con un clic.

Para analizar una imagen: escribe tu pregunta (opcional), toca **📎** y
elige la foto.

## Paso 6 — Empaquetar como .exe (opcional)

Empaca todo (Python incluido) en un solo ejecutable, para poder abrirlo
con doble clic sin instalar nada.

**Importante:** compílalo directamente en la laptop que usarás para la
presentación (PyInstaller no genera bien un `.exe` de Windows si lo
armas desde otro sistema operativo).

1. Instala PyInstaller (ya viene en `requirements.txt`, o si falta):
   ```bash
   pip install pyinstaller
   ```

2. Desde la carpeta `venok`, corre:
   ```bash
   pyinstaller Venok.spec
   ```
   *(Este `.spec` ya incluye la carpeta `ui/`. Es el mismo resultado que
   `pyinstaller --onefile --windowed --add-data "ui;ui" --name Venok app.py`.)*

3. El ejecutable queda en `dist/Venok.exe`.

4. **Copia tu `.env` real a la carpeta `dist/`, junto al `.exe`.** El
   `.env` NO se empaca dentro del ejecutable a propósito — así nunca
   queda una clave incrustada en un binario que podrías compartir o
   subir sin querer. `Venok.exe` busca el `.env` en su misma carpeta al
   arrancar.

5. Prueba con anticipación: cierra la terminal donde compilaste y abre
   solo el `.exe` desde `dist/`, para confirmar que funciona standalone
   con su `.env` al lado.

## Personalización

Venok responde con un tono configurable (formal / amigable / gracioso,
ver `personalidad.py`), recuerda tu nombre y ciudad (`memoria.py`), y
puedes cambiarle su propio nombre y palabra de activación en cualquier
momento diciendo "llámate [nombre]". También hay un panel de
Configuración en la interfaz para cambiar el tema de color, el nombre y
el tono sin usar la voz.

## Accesibilidad

Pensado también para facilitar el uso de la computadora a personas con
alguna discapacidad, mediante control por voz de:
- Aplicaciones, sitios web y juegos (`acciones.py`)
- Archivos y carpetas (`archivos.py`)
- Mouse y teclado (`control_mouse_teclado.py`), usando `pyautogui`

**Nota de seguridad:** `pyautogui` tiene un "failsafe" activado — si
mueves el mouse físicamente a la esquina superior izquierda de la
pantalla, se detiene cualquier acción automática en curso.

## Seguridad y permisos

- Ninguna clave de API se escribe en el código: todas se leen de `.env`,
  que está excluido de git (`.gitignore`).
- Cerrar aplicaciones, vaciar la papelera, eliminar archivos, abrir
  redes sociales, o activar el inicio automático con Windows: todo eso
  pide confirmación antes de ejecutarse (`permisos.py`). Cualquier
  respuesta que no sea un claro "sí" cancela la acción.
- Eliminar un archivo lo manda a la papelera de reciclaje — nunca hace
  un borrado permanente.

## Notas para la demo

- Prueba todo (incluyendo el `.exe`) en la laptop real que usarás, con
  anticipación.
- Si el WiFi falla, Venok sigue funcionando en modo texto (sin voz)
  gracias al respaldo de voz del sistema, y las funciones que no
  necesitan internet (mouse/teclado, calculadora, apps locales) siguen
  funcionando igual.
- No dejes visible ninguna terminal ni el archivo `.env` mientras proyectas.

## Estructura del proyecto

```
venok/
├── app.py                    # Aplicación completa (interfaz + asistente)
├── main.py                   # Cerebro del asistente + versión solo consola
├── config.py                 # Configuración y claves de API (lee .env)
├── voz.py                    # Texto a voz (motor del sistema o ElevenLabs)
├── acciones.py                # Abrir sitios, apps y juegos + emparejado difuso
├── capacidades.py             # Clima, noticias, hora, definiciones, traductor, Wolfram
├── control_mouse_teclado.py  # Control de mouse/teclado por voz
├── personalidad.py           # Frases y tonos (formal/amigable/gracioso)
├── memoria.py                 # Memoria persistente y de sesión
├── permisos.py                 # Sistema de confirmación para acciones sensibles
├── monitoreo.py                # CPU, RAM, disco, batería, procesos (en vivo)
├── analisis_equipo.py          # Specs del equipo y programas instalados
├── archivos.py                  # Buscar, abrir y eliminar archivos
├── recordatorios.py             # Recordatorios con fechas en lenguaje natural
├── inicio_automatico.py         # Inicio automático con Windows (registro)
├── correo.py                     # Revisar y enviar correos (IMAP/SMTP)
├── claude_api.py                 # Cliente compartido de Claude + historial
├── agente.py                      # Herramientas que la IA puede usar
├── imagen_ia.py                   # Análisis de imágenes adjuntadas
├── navegador_ia.py               # Investigar/resumir páginas con IA
├── ui/index.html               # Interfaz visual (HUD, chat, actividad, config)
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Licencia

MIT — ver [`LICENSE`](LICENSE).
