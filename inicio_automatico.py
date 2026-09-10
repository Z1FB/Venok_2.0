"""
Inicio automático de Venok con Windows, usando la clave de registro
"Run" del usuario actual (HKEY_CURRENT_USER), que no requiere permisos
de administrador y solo afecta el inicio de sesión del usuario que lo activó.

Detecta si Venok está corriendo ya empacado (.exe con PyInstaller) o desde
el código fuente (`python app.py`), y guarda el comando correcto en cada
caso para que el inicio automático funcione igual en ambos escenarios.
"""

import os
import sys

import winreg

_CLAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NOMBRE_ENTRADA = "Venok"


def _comando_de_inicio() -> str:
    if getattr(sys, "frozen", False):
        # Empacado con PyInstaller: sys.executable ES Venok.exe.
        return f'"{sys.executable}"'
    # Corriendo desde el código fuente: hay que decirle a Windows qué
    # intérprete de Python usar y qué archivo correr.
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "app.py"))
    return f'"{sys.executable}" "{script}"'


def activar() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLAVE_RUN, 0, winreg.KEY_SET_VALUE) as clave:
            winreg.SetValueEx(clave, _NOMBRE_ENTRADA, 0, winreg.REG_SZ, _comando_de_inicio())
        return "Listo, Venok se abrirá automáticamente cuando inicies sesión en Windows."
    except OSError as error:
        return f"No pude activar el inicio automático ({error})."


def desactivar() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLAVE_RUN, 0, winreg.KEY_SET_VALUE) as clave:
            winreg.DeleteValue(clave, _NOMBRE_ENTRADA)
        return "Listo, ya no me abriré automáticamente con Windows."
    except FileNotFoundError:
        return "El inicio automático ya estaba desactivado."
    except OSError as error:
        return f"No pude desactivar el inicio automático ({error})."


def esta_activado() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLAVE_RUN, 0, winreg.KEY_QUERY_VALUE) as clave:
            winreg.QueryValueEx(clave, _NOMBRE_ENTRADA)
        return True
    except OSError:
        return False
