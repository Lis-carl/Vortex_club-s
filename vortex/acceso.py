"""Control de acceso: decoradores de sesión y permisos por club.

El tipo de usuario lo determina la cuenta (``usuario.rol_acceso``, calculado en cada petición):

* **administración**: la cuenta de administración; permiso total sobre todos los clubes;
* **líder / capitán**: si alguien lo nombró en algún club; tiene esos permisos en ese club;
* **estudiante**: permisos de miembro.
"""
from functools import wraps
from urllib.parse import quote

from .nucleo import ErrorHttp, Fila, Respuesta
from .repositorios import clubes as repo_clubes, eventos as repo_eventos

ROLES_ACCESO = {"estudiante": "Estudiante", "capitan": "Capitán", "lider": "Líder", "admin": "Administración"}


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
            raise ErrorHttp(403, "Esta sección es solo para la administración.")
        return funcion(p, **parametros)
    return interno


def es_admin(p):
    """Administración con permiso total."""
    return bool(p.usuario and p.usuario.rol_global == "admin" and p.usuario.rol_acceso == "admin")


def modo_gestion(p):
    """La cuenta es líder o capitán de algún club."""
    return bool(p.usuario and p.usuario.rol_acceso in ("capitan", "lider"))


def destino_seguro(valor, defecto="/"):
    """Solo se aceptan rutas internas (evita redirecciones abiertas)."""
    # Se rechazan «//sitio», barras invertidas y cualquier espacio o carácter de control: los navegadores
    # ignoran tabulaciones y saltos de línea, así que «/\t/sitio-malo» terminaría en «//sitio-malo».
    if (valor and valor.startswith("/") and not valor.startswith("//") and "\\" not in valor
            and all(32 < ord(c) != 127 for c in valor)):
        return valor
    return defecto


def club_o_404(p, slug):
    club = repo_clubes.por_slug(p.bd, slug)
    if not club or (club.estado != "activo" and not es_admin(p)):
        raise ErrorHttp(404, "Ese club no existe o fue desactivado.")
    return club


def _membresia_activa(p, club_id):
    m = repo_clubes.membresia(p.bd, p.usuario.id, club_id)
    return m if m and m.estado == "activa" else None


def es_responsable_en(p, club_id):
    """Líder o capitán del club (con el rol de gestión activo) o administración."""
    if es_admin(p):
        return True
    m = _membresia_activa(p, club_id)
    return bool(m and m.rol in ("lider", "capitan") and modo_gestion(p))


def es_lider_en(p, club_id):
    if es_admin(p):
        return True
    m = _membresia_activa(p, club_id)
    return bool(m and m.rol == "lider" and modo_gestion(p))


def exigir_miembro(p, club):
    if es_admin(p):
        return Fila(rol="admin", estado="activa")
    m = _membresia_activa(p, club.id)
    if not m:
        raise ErrorHttp(403, "Debes ser miembro del club para hacer esto.")
    return m


def exigir_responsable(p, club):
    if not es_responsable_en(p, club.id):
        raise ErrorHttp(403, "Solo el líder, los capitanes del club o la administración pueden hacer esto.")
    return _membresia_activa(p, club.id) or Fila(rol="admin", estado="activa")


def contexto_club(p, club, pestana):
    """Datos que necesita la cabecera con pestañas de cualquier página de club."""
    mi = repo_clubes.membresia(p.bd, p.usuario.id, club.id)
    responsable = es_responsable_en(p, club.id)
    puede_pedir_capitan = bool(mi and mi.estado == "activa" and mi.rol == "miembro"
                               and not repo_clubes.solicitud_capitan_pendiente(p.bd, p.usuario.id, club.id))
    return {
        "club": club,
        "mi": mi,
        "es_miembro": bool(mi and mi.estado == "activa") or es_admin(p),
        "es_responsable": responsable,
        "es_lider": es_lider_en(p, club.id),
        "puede_pedir_capitan": puede_pedir_capitan,
        "capitan_pendiente": bool(mi and repo_clubes.solicitud_capitan_pendiente(p.bd, p.usuario.id, club.id)),
        "pestana": pestana,
        "lider": repo_clubes.lider(p.bd, club.id),
        "pend_miembros": repo_clubes.contar_pendientes(p.bd, club.id) if responsable else 0,
        "pend_eventos": repo_eventos.contar_pendientes(p.bd, club.id) if responsable else 0,
    }
