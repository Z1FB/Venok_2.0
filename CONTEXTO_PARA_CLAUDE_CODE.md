# Contexto del proyecto Venok (para Claude Code)

Venok es un asistente de voz de escritorio para Windows, hecho en Python,
estilo Jarvis. Proyecto escolar que busca llegar a nivel "profesional"
para el 30 de septiembre.

## Estructura actual

- `app.py` — punto de entrada principal (interfaz + voz + chat + palabra
  de activación "Oye Venok"). Usa pywebview.
- `main.py` — versión solo de consola (sin interfaz), útil para pruebas
  rápidas. Contiene `escuchar()` e `interpretar()`, el cerebro que decide
  qué hacer con cada comando.
- `voz.py` — texto a voz. Dos motores: "sistema" (voz de Windows vía
  PowerShell/System.Speech, gratis) o "elevenlabs" (requiere plan pagado
  para voces de biblioteca). Configurado en `config.py` con `MOTOR_VOZ`.
- `acciones.py` — abrir apps, sitios web, juegos. Incluye `normalizar()`
  (quita tildes/mayúsculas para comparar texto).
- `capacidades.py` — clima, noticias, hora, fecha, definiciones
  (Wikipedia), conversión de moneda, calculadora, volumen, multimedia,
  bloquear pantalla, vaciar papelera, crear carpetas, capturas de
  pantalla, chistes, y Wolfram Alpha como último recurso para preguntas
  abiertas (con traducción automática español↔inglés).
- `control_mouse_teclado.py` — mover mouse, clic, escribir, teclas.
- `personalidad.py` — frases y tono tipo Jarvis.
- `config.py` — configuración y claves (lee de `.env`, nunca hardcodeadas).
- `ui/index.html` — interfaz visual: núcleo central animado tipo HUD,
  panel de chat con historial, botones de modo voz/texto, varios estados
  visuales (reposo/escuchando/procesando/hablando/error).

## Cómo correr

- `python app.py` → versión completa con interfaz.
- `python main.py` → solo consola, sin interfaz.
- Entorno virtual ya configurado con Python 3.12 (`venv`).
- `.env` tiene: `ELEVENLABS_API_KEY`, `WOLFRAM_APP_ID`, `MOTOR_VOZ=sistema`.

## Empaquetado

Se genera un `.exe` con PyInstaller:
```
pyinstaller --onefile --windowed --add-data "ui;ui" --name Venok app.py
```
Nota: algunos antivirus (Avast) dan falso positivo con el .exe empacado
—es un problema conocido de PyInstaller, no del código.

## Ya completado (Fase 1 de la v2.0)

- Interfaz nueva con panel de chat funcional (texto ↔ voz).
- Palabra de activación "Oye Venok" (simple: ignora comandos que no
  empiecen con esa frase, no es un wake-word de bajo consumo real).
- Modo voz / modo texto intercambiable desde la interfaz.

## Pendiente (fases futuras, ver documento "Venok v2.0" del usuario)

Personalidad más natural con memoria de contexto, sistema de permisos
con confirmación, control más profundo de Windows (archivos, CPU/RAM),
control de navegador con IA, análisis del equipo, calendario/recordatorios,
correo, inicio automático con Windows, animación de inicio, temas de
color personalizables, panel de actividad reciente.

## Reglas importantes

- NO reemplazar código que ya funciona sin explicar por qué.
- Cualquier acción sensible (borrar archivos, enviar correos, cambios de
  sistema) debe pedir confirmación al usuario.
- Mantener el proyecto modular (no meter toda la lógica en un solo archivo).
