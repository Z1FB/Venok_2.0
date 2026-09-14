"""
Correo: revisar la bandeja de entrada y enviar mensajes por voz.

Usa IMAP y SMTP de la librería estándar de Python, así que no agrega
dependencias. Está pensado para Gmail, que exige una "contraseña de
aplicación" (no sirve la contraseña normal de la cuenta): se genera en
https://myaccount.google.com/apppasswords y se guarda en el .env como
CORREO_USUARIO y CORREO_PASSWORD.

Al revisar la bandeja se usa BODY.PEEK a propósito, para que los correos
NO queden marcados como leídos solo porque Venok los miró.

Enviar un correo es una acción sensible: quien llame a `enviar` debe
pedir confirmación antes (ver permisos.py).
"""

import email
import imaplib
import smtplib
from email.header import decode_header
from email.message import EmailMessage

from config import CORREO_PASSWORD, CORREO_USUARIO

SERVIDOR_IMAP = "imap.gmail.com"
SERVIDOR_SMTP = "smtp.gmail.com"
PUERTO_SMTP = 587

ASUNTO_POR_DEFECTO = "Mensaje enviado desde Venok"

# Agenda para poder decir "envía un correo a mamá" en vez de deletrear una
# dirección. Agrega aquí los tuyos, igual que las APPS en acciones.py.
CONTACTOS = {
    # "mama": "correo_de_mama@gmail.com",
    # "profe": "profesor@colegio.edu",
}

_AVISO_SIN_CONFIGURAR = (
    "Todavía no tengo una cuenta de correo conectada. Se configura con "
    "CORREO_USUARIO y CORREO_PASSWORD en el archivo punto env."
)


def hay_credenciales() -> bool:
    return bool(CORREO_USUARIO and CORREO_PASSWORD)


def _decodificar(valor: str) -> str:
    """Los encabezados vienen codificados cuando traen tildes o emojis."""
    if not valor:
        return ""
    partes = []
    for texto, codificacion in decode_header(valor):
        if isinstance(texto, bytes):
            partes.append(texto.decode(codificacion or "utf-8", errors="replace"))
        else:
            partes.append(texto)
    return "".join(partes).strip()


def _solo_el_nombre(remitente: str) -> str:
    """De 'Ana Pérez <ana@x.com>' se queda con 'Ana Pérez', que suena mejor
    leído en voz alta que la dirección completa."""
    nombre, direccion = email.utils.parseaddr(remitente)
    return nombre or direccion or remitente


def revisar(cantidad: int = 3) -> str:
    if not hay_credenciales():
        return _AVISO_SIN_CONFIGURAR

    try:
        with imaplib.IMAP4_SSL(SERVIDOR_IMAP) as servidor:
            servidor.login(CORREO_USUARIO, CORREO_PASSWORD)
            servidor.select("INBOX")

            estado, datos = servidor.search(None, "UNSEEN")
            if estado != "OK":
                return "No pude revisar tu bandeja de entrada."

            identificadores = datos[0].split()
            if not identificadores:
                return "No tienes correos sin leer."

            resumenes = []
            for identificador in reversed(identificadores[-cantidad:]):
                estado, datos = servidor.fetch(
                    identificador, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])"
                )
                if estado != "OK" or not datos or not isinstance(datos[0], tuple):
                    continue
                encabezados = email.message_from_bytes(datos[0][1])
                remitente = _solo_el_nombre(_decodificar(encabezados.get("From", "")))
                asunto = _decodificar(encabezados.get("Subject", "")) or "sin asunto"
                resumenes.append(f"de {remitente}, sobre {asunto}")

            total = len(identificadores)
            encabezado = (
                f"Tienes {total} correo sin leer" if total == 1
                else f"Tienes {total} correos sin leer"
            )
            if not resumenes:
                return encabezado + "."
            return f"{encabezado}. Los más recientes: " + "; ".join(resumenes) + "."

    except imaplib.IMAP4.error:
        return ("No pude entrar a tu correo. Revisa que CORREO_USUARIO y "
                "CORREO_PASSWORD sean correctos y que uses una contraseña de aplicación.")
    except OSError as error:
        print(f"[Venok] Error de conexión al revisar correo: {error}")
        return "No pude conectarme para revisar tu correo."


def resolver_destinatario(nombre: str):
    """Acepta un contacto de la agenda o una dirección escrita directamente."""
    nombre = (nombre or "").strip().rstrip(".,")
    if not nombre:
        return None
    if "@" in nombre:
        return nombre.replace(" ", "")
    return CONTACTOS.get(nombre.lower())


def enviar(destinatario: str, cuerpo: str, asunto: str = ASUNTO_POR_DEFECTO) -> str:
    if not hay_credenciales():
        return _AVISO_SIN_CONFIGURAR

    mensaje = EmailMessage()
    mensaje["From"] = CORREO_USUARIO
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    try:
        with smtplib.SMTP(SERVIDOR_SMTP, PUERTO_SMTP, timeout=20) as servidor:
            servidor.starttls()
            servidor.login(CORREO_USUARIO, CORREO_PASSWORD)
            servidor.send_message(mensaje)
        return f"Listo, le envié el correo a {destinatario}."
    except smtplib.SMTPAuthenticationError:
        return ("No pude iniciar sesión en tu correo. Asegúrate de usar una "
                "contraseña de aplicación de Gmail, no la contraseña normal.")
    except (smtplib.SMTPException, OSError) as error:
        print(f"[Venok] Error al enviar correo: {error}")
        return "No pude enviar el correo en este momento."
