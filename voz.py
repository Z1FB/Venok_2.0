"""
Módulo de voz: convierte el texto de las respuestas de Venok en audio.

Soporta dos motores (ver MOTOR_VOZ en config.py):
- "sistema"    -> voz de Windows (gratis, sin internet)
- "elevenlabs" -> API de ElevenLabs (voz más realista, requiere plan pagado
                  para usar voces de biblioteca por API)

Para el motor "sistema" hay dos caminos:
  1. SAPI (el motor de voz de Windows) usado directamente, desde UN solo
     hilo dedicado que vive toda la sesión. Evita lanzar un proceso nuevo
     por cada respuesta.
  2. PowerShell/System.Speech como respaldo, si SAPI no arranca en alguna
     máquina. Funciona seguro, pero lanza un proceso y carga .NET cada vez.

Por qué no pyttsx3: en Windows solo habla la PRIMERA vez que se reutiliza
el motor; las llamadas siguientes regresan al instante sin sonar (su evento
de fin de frase llega con completed=False). Por eso Venok saludaba al abrir
y después se quedaba mudo.

Por qué un hilo dedicado: los objetos COM de SAPI pertenecen al hilo que
los creó, y en app.py cada respuesta sale de un hilo distinto.
"""

import queue
import threading

from config import MOTOR_VOZ

_candado = threading.Lock()  # una sola locución a la vez: hablar encimado suena horrible

_cola = queue.Queue()
_hilo_sapi = None
_sapi_listo = threading.Event()
_sapi_disponible = True


def _es_voz_en_espanol(token) -> bool:
    # Ojo: no sirve buscar "es" dentro del id, porque la ruta del registro
    # de Windows trae "Voices" y hace match con CUALQUIER voz.
    return "_ES-" in (token.Id or "").upper()


def _trabajador_sapi() -> None:
    """Único hilo que toca SAPI en toda la sesión: lo crea y atiende la cola."""
    global _sapi_disponible
    try:
        import comtypes
        import comtypes.client

        comtypes.CoInitialize()
        voz = comtypes.client.CreateObject("SAPI.SpVoice")
        for token in voz.GetVoices():
            if _es_voz_en_espanol(token):
                voz.Voice = token
                break
        voz.Rate = 1  # un poco más ágil que el ritmo por defecto
    except Exception as error:
        print(f"[Venok] No pude iniciar la voz de Windows ({error}). Uso el método de respaldo.")
        _sapi_disponible = False
        _sapi_listo.set()
        return

    _sapi_listo.set()
    while True:
        texto, terminado, resultado = _cola.get()
        try:
            voz.Speak(texto, 0)  # 0 = síncrono: regresa cuando termina de hablar
            resultado["ok"] = True
        except Exception as error:
            print(f"[Venok] La voz de Windows falló ({error}). Uso el método de respaldo.")
            resultado["ok"] = False
        finally:
            terminado.set()


def _hablar_rapido(texto: str) -> bool:
    """Regresa True si logró hablar; False para que se use el respaldo."""
    global _hilo_sapi, _sapi_disponible
    if _hilo_sapi is None:
        _hilo_sapi = threading.Thread(target=_trabajador_sapi, daemon=True, name="voz-sapi")
        _hilo_sapi.start()
    _sapi_listo.wait(timeout=10)
    if not _sapi_disponible:
        return False

    terminado = threading.Event()
    resultado = {}
    _cola.put((texto, terminado, resultado))

    # Holgado a propósito (a este ritmo se dicen ~15 caracteres por segundo):
    # solo debe vencer si SAPI se colgó, no si la respuesta es larga.
    if not terminado.wait(timeout=max(15, len(texto) * 0.2)):
        print("[Venok] La voz de Windows no respondió a tiempo. Uso el método de respaldo.")
        _sapi_disponible = False
        return False
    return resultado.get("ok", False)


def _hablar_sistema(texto: str) -> None:
    # Guardamos el texto en un archivo temporal y hacemos que PowerShell lo
    # LEA de ahí, en vez de meterlo directo en el comando. Así no importa
    # qué símbolos traiga el texto (comillas, comas, signos, etc.) — antes
    # esto rompía el comando con textos largos como titulares de noticias.
    import subprocess
    import tempfile
    import os

    ruta_temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as archivo_temporal:
            archivo_temporal.write(texto)
            ruta_temporal = archivo_temporal.name

        comando_ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = 1; "
            "$vocesEs = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'es*' }; "
            "if ($vocesEs.Count -gt 0) { $s.SelectVoice($vocesEs[0].VoiceInfo.Name) }; "
            f"$texto = Get-Content -LiteralPath '{ruta_temporal}' -Raw -Encoding UTF8; "
            "$s.Speak($texto)"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", comando_ps],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except Exception as error:
        print(f"[Venok] No pude generar la voz del sistema ({error}). Sigo solo con texto.")
    finally:
        if ruta_temporal:
            try:
                os.remove(ruta_temporal)
            except OSError:
                pass


def _hablar_elevenlabs(texto: str) -> None:
    import io
    import requests
    import pygame
    from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID

    if not ELEVENLABS_API_KEY:
        return

    pygame.mixer.init()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": texto,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        respuesta = requests.post(url, json=payload, headers=headers, timeout=15)
        respuesta.raise_for_status()
        audio_bytes = io.BytesIO(respuesta.content)

        pygame.mixer.music.load(audio_bytes, "mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except requests.exceptions.RequestException as error:
        print(f"[Venok] No pude generar la voz con ElevenLabs ({error}). Sigo solo con texto.")


def hablar(texto: str) -> None:
    print(f"[Venok] {texto}")

    with _candado:
        if MOTOR_VOZ == "elevenlabs":
            _hablar_elevenlabs(texto)
        elif not _hablar_rapido(texto):
            _hablar_sistema(texto)
