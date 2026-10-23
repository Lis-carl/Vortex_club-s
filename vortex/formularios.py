"""Lectura de formularios (urlencoded y multipart) y validaciones de entrada."""
import re
from email import policy
from email.parser import BytesParser
from urllib.parse import parse_qs

from . import config
from .nucleo import Fila

RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RE_CIF = re.compile(r"^\d{8}$")


class Errores(Fila):
    """campo -> mensaje de error. Vacío significa que todo es válido."""
    __slots__ = ()


# --- Lectura ---------------------------------------------------------------------------------
def leer_urlencoded(cuerpo):
    datos = parse_qs(cuerpo.decode("utf-8", "replace"), keep_blank_values=True, max_num_fields=200)
    return {clave: valores[0] for clave, valores in datos.items()}


def leer_multipart(tipo_contenido, cuerpo):
    """Devuelve (campos, archivos). Cada archivo es Fila(nombre, datos)."""
    cabecera = b"Content-Type: " + tipo_contenido.encode("latin-1", "replace") + b"\r\nMIME-Version: 1.0\r\n\r\n"
    mensaje = BytesParser(policy=policy.HTTP).parsebytes(cabecera + cuerpo)
    campos, archivos = {}, {}
    if not mensaje.is_multipart():
        return campos, archivos
    for parte in mensaje.iter_parts():
        nombre = parte.get_param("name", header="content-disposition")
        if not nombre:
            continue
        datos = parte.get_payload(decode=True) or b""
        nombre_archivo = parte.get_filename()
        if nombre_archivo is not None:
            if nombre_archivo or datos:
                archivos[nombre] = Fila(nombre=nombre_archivo, datos=datos)
        else:
            campos[nombre] = datos.decode(parte.get_content_charset() or "utf-8", "replace")
    return campos, archivos


# --- Validación ------------------------------------------------------------------------------
def texto(campos, errores, clave, etiqueta, minimo=1, maximo=200, obligatorio=True, una_linea=True):
    valor = (campos.get(clave) or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if una_linea:
        valor = " ".join(valor.split())
    if not valor:
        if obligatorio:
            errores[clave] = f"{etiqueta} es obligatorio."
        return valor
    if len(valor) < minimo:
        errores[clave] = f"{etiqueta} debe tener al menos {minimo} caracteres."
    elif len(valor) > maximo:
        errores[clave] = f"{etiqueta} no puede superar {maximo} caracteres."
    return valor


def entero(campos, errores, clave, etiqueta, minimo, maximo, obligatorio=False):
    crudo = (campos.get(clave) or "").strip()
    if not crudo:
        if obligatorio:
            errores[clave] = f"{etiqueta} es obligatorio."
        return None
    if not re.fullmatch(r"\d{1,9}", crudo) or not (minimo <= int(crudo) <= maximo):
        errores[clave] = f"{etiqueta} debe ser un número entre {minimo} y {maximo}."
        return None
    return int(crudo)


def tipo_imagen(datos):
    """Extensión según la firma binaria del archivo, o None si no es PNG/JPG/GIF/WEBP."""
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if datos.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if datos[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "webp"
    return None


def validar_imagen(archivo, errores, clave="imagen"):
    """Devuelve la extensión si la imagen es válida; si no, agrega un error y devuelve None."""
    if not archivo or not archivo.datos:
        return None
    if len(archivo.datos) > config.LIMITE_IMAGEN:
        errores[clave] = "La imagen no puede pesar más de 2 MB."
        return None
    extension = tipo_imagen(archivo.datos)
    if not extension:
        errores[clave] = "La imagen debe ser PNG, JPG, GIF o WEBP."
    return extension
