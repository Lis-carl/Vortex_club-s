"""Control de acceso: decoradores de sesión y consultas de permisos por club."""
from functools import wraps
from urllib.parse import quote

from .nucleo import ErrorHttp, Fila, Respuesta
from .repositorios import clubes as repo_clubes, eventos as repo_eventos


def requiere_sesion(funcion):
    @wraps(funcion)
    def interno(p, **parametros):
        if not p.usuario:
            if p.metodo == "GET":
                return Respuesta.redirigir("/acceder?siguiente=" + quote(p.ruta_completa, safe=""))
            return Respuesta.redirigir("/acceder")
        return funcion(p, **parametros)
    return interno


def requiere_admin(funcion):
    @wraps(funcion)
    @requiere_sesion
    def interno(p, **parametros):
        if not es_admin(p):
            raise ErrorHttp(403, "Esta sección es solo para administradores.")
        return funcion(p, **parametros)
    return interno


def es_admin(p):
    return bool(p.usuario and p.usuario.rol_global == "admin")


def destino_seguro(valor, defecto="/"):
    """Solo se aceptan rutas internas (evita redirecciones abiertas)."""
    if (valor and valor.startswith("/") and not valor.startswith("//")
            and "\\" not in valor and "\n" not in valor and "\r" not in valor):
        return valor
    return defecto


def club_o_404(p, slug):
    club = repo_clubes.por_slug(p.bd, slug)
    if not club or (club.estado != "activo" and not es_admin(p)):
        raise ErrorHttp(404, "Ese club no existe o fue desactivado.")
    return club


def es_responsable(membresia):
    return bool(membresia and membresia.estado == "activa" and membresia.rol in ("lider", "capitan"))


def exigir_miembro(p, club):
    m = repo_clubes.membresia(p.bd, p.usuario.id, club.id)
    if not m or m.estado != "activa":
        raise ErrorHttp(403, "Debes ser miembro del club para hacer esto.")
    return m


def exigir_responsable(p, club):
    m = repo_clubes.membresia(p.bd, p.usuario.id, club.id)
    if not es_responsable(m):
        raise ErrorHttp(403, "Solo el líder o los capitanes del club pueden hacer esto.")
    return m


def contexto_club(p, club, pestana):
    """Datos que necesita la cabecera con pestañas de cualquier página de club."""
    mi = repo_clubes.membresia(p.bd, p.usuario.id, club.id)
    responsable = es_responsable(mi)
    return {
        "club": club,
        "mi": mi,
        "es_miembro": bool(mi and mi.estado == "activa"),
        "es_responsable": responsable,
        "es_lider": bool(mi and mi.estado == "activa" and mi.rol == "lider"),
        "pestana": pestana,
        "lider": repo_clubes.lider(p.bd, club.id),
        "pend_miembros": repo_clubes.contar_pendientes(p.bd, club.id) if responsable else 0,
        "pend_eventos": repo_eventos.contar_pendientes(p.bd, club.id) if responsable else 0,
    }
