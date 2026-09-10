"""
Configuración general de Venok.
La API key NUNCA se escribe aquí directamente: se lee de un archivo .env
o de una variable de entorno, para que no quede expuesta si compartes
o proyectas el código.
"""

import os
import sys
from dotenv import load_dotenv

# Busca el .env junto al .exe (empacado) o junto a este archivo (código
# fuente), sin importar cuál sea el directorio de trabajo actual —
# necesario porque al hacer doble clic en el .exe desde otra carpeta,
# load_dotenv() sin ruta no siempre encuentra el archivo correcto.
if getattr(sys, "frozen", False):
    _CARPETA_BASE = os.path.dirname(sys.executable)
else:
    _CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(_CARPETA_BASE, ".env"))

# --- Motor de voz ---
# "sistema"    -> usa las voces que ya trae Windows (gratis, sin internet, sin API key)
# "elevenlabs" -> usa la API de ElevenLabs (requiere plan pagado para voces de biblioteca)
MOTOR_VOZ = os.environ.get("MOTOR_VOZ", "sistema")

# --- ElevenLabs (solo se usa si MOTOR_VOZ = "elevenlabs") ---
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

# Voces candidatas para Venok (cambia cuál está activa comentando/descomentando,
# o exporta ELEVENLABS_VOICE_ID para sobreescribir sin tocar el código):
VOZ_ARCHIE = "kmSVBPu7loj4ayNinwWM"
VOZ_NAYVA = "h2dQOVyUfIDqY2whPOMo"
VOZ_BRITTNEY = "kPzsL2i3teMYv0FxEYQ6"

ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", VOZ_ARCHIE)  # <- cambia aquí la voz activa
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"

# --- Wake word / activación ---
NOMBRE_ASISTENTE = "Venok"

# --- Idioma para el reconocimiento de voz ---
IDIOMA_RECONOCIMIENTO = "es-SV"  # es-ES / es-MX / es-SV según prefieras

# --- Wolfram Alpha (para preguntas de conocimiento general/ciencia/matemáticas) ---
WOLFRAM_APP_ID = os.environ.get("WOLFRAM_APP_ID")

# --- Anthropic / Claude (para investigar y resumir páginas web con IA) ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

if MOTOR_VOZ == "elevenlabs" and not ELEVENLABS_API_KEY:
    print(
        "[AVISO] No se encontró ELEVENLABS_API_KEY.\n"
        "Configúrala de una de estas formas antes de correr Venok:\n"
        "  1) Crea un archivo .env en esta carpeta con:\n"
        "       ELEVENLABS_API_KEY=tu_clave_aqui\n"
        "  2) O expórtala en terminal:\n"
        "       Windows (PowerShell):  $env:ELEVENLABS_API_KEY='tu_clave_aqui'\n"
        "       macOS/Linux:           export ELEVENLABS_API_KEY='tu_clave_aqui'\n"
    )
