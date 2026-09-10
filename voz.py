"""
Módulo de voz: convierte el texto de las respuestas de Venok en audio.

Soporta dos motores (ver MOTOR_VOZ en config.py):
- "sistema"    -> voz de Windows vía PowerShell/System.Speech (gratis, sin internet)
- "elevenlabs" -> API de ElevenLabs (voz más realista, requiere plan pagado
                  para usar voces de biblioteca por API)
"""

from config import MOTOR_VOZ


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

    if MOTOR_VOZ == "elevenlabs":
        _hablar_elevenlabs(texto)
    else:
        _hablar_sistema(texto)
