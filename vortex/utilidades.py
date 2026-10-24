"""Funciones auxiliares: slugs, fechas y textos."""
import re
import unicodedata
from datetime import datetime

MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                "octubre", "noviembre", "diciembre"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
_FORMATOS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S")
RESERVADOS = {"solicitar", "nuevo", "editar"}


def slugify(texto):
    """'Club de Ajedrez' -> 'club-de-ajedrez'."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")[:60].strip("-")
    slug = slug or "club"
    return slug + "-club" if slug in RESERVADOS else slug


def parsear_fecha(texto):
    for formato in _FORMATOS:
        try:
            return datetime.strptime(str(texto), formato)
        except ValueError:
            continue
    return None


def ahora_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def tiempo_relativo(texto):
    fecha = parsear_fecha(texto)
    if not fecha:
        return ""
    segundos = int((datetime.now() - fecha).total_seconds())
    if segundos < 60:
        return "hace un momento"
    if segundos < 3600:
        return f"hace {segundos // 60} min"
    if segundos < 86400:
        return f"hace {segundos // 3600} h"
    if segundos < 86400 * 30:
        return f"hace {segundos // 86400} d"
    return fecha_corta(texto)


def fecha_corta(texto):
    f = parsear_fecha(texto)
    return f"{f.day} {MESES[f.month - 1]} {f.year}" if f else ""


def fecha_larga(texto):
    f = parsear_fecha(texto)
    return f"{f.day} {MESES[f.month - 1]} {f.year}, {f:%H:%M}" if f else ""


def dia(texto):
    f = parsear_fecha(texto)
    return f"{f.day:02d}" if f else ""


def mes(texto):
    f = parsear_fecha(texto)
    return MESES[f.month - 1].upper() if f else ""


def hora(texto):
    f = parsear_fecha(texto)
    return f"{f:%H:%M}" if f else ""


def iniciales(texto):
    partes = [p for p in str(texto or "").split() if p]
    return "".join(p[0] for p in partes[:2]).upper() or "?"


# Tonos sobrios para los avatares de iniciales.
_COLORES = ["#009AA9", "#007A87", "#2F6F8F", "#4E7D5B", "#8A4F5E", "#5A6470", "#B07D2B", "#3C8D93"]


def color(texto):
    """Color estable para un avatar a partir de un texto."""
    return _COLORES[sum(ord(c) for c in str(texto or "")) % len(_COLORES)]


def extracto(texto, maximo=280):
    texto = str(texto or "")
    return texto if len(texto) <= maximo else texto[:maximo].rstrip() + "…"
