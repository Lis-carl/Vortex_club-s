"""Panel de administración."""
from .. import formularios as frm
from ..acceso import requiere_admin
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import clubes, notificaciones, usuarios
from ..vistas import render


@ruta("GET", "/admin")
@requiere_admin
def panel(p):
    return render(p, "admin.html", estadisticas=usuarios.estadisticas(p.bd),
                  solicitudes=clubes.solicitudes_pendientes(p.bd), lista_usuarios=usuarios.listar(p.bd),
                  solicitudes_capitan=clubes.solicitudes_capitan_pendientes(p.bd),
                  lista_clubes=clubes.todos(p.bd))


@ruta("POST", "/admin/solicitudes/<id>")
@requiere_admin
def resolver_solicitud(p, id):
    decision = p.formulario.get("decision")
    if decision not in ("aprobar", "rechazar"):
        raise ErrorHttp(400, "Decisión no válida.")
    comentario = frm.texto(p.formulario, frm.Errores(), "comentario", "El comentario", 1, 500, obligatorio=False)
    solicitud = clubes.solicitud_club(p.bd, id)
    slug = clubes.resolver_solicitud(p.bd, id, p.usuario.id, decision == "aprobar", comentario)
    if solicitud and solicitud.estado == "pendiente":
        if slug:
            notificaciones.crear(p.bd, solicitud.usuario_id, f"Tu solicitud fue aprobada: ya eres líder de {solicitud.nombre}.",
                                 f"/clubes/{slug}")
        elif decision == "rechazar":
            notificaciones.crear(p.bd, solicitud.usuario_id, f"Tu solicitud para crear {solicitud.nombre} fue rechazada.",
                                 "/clubes/solicitar")
    if decision == "aprobar" and not slug:
        return Respuesta.redirigir("/admin").con_aviso("error", "Esa solicitud ya fue resuelta.")
    return Respuesta.redirigir("/admin").con_aviso(
        "ok", "Club aprobado y creado." if decision == "aprobar" else "Solicitud rechazada.")


@ruta("POST", "/admin/usuarios/<id>")
@requiere_admin
def cambiar_estado_usuario(p, id):
    objetivo = usuarios.por_id(p.bd, id)
    if not objetivo:
        raise ErrorHttp(404, "Ese usuario no existe.")
    if objetivo.id == p.usuario.id:
        return Respuesta.redirigir("/admin").con_aviso("error", "No puedes desactivar tu propia cuenta.")
    activar = p.formulario.get("activo") == "1"
    usuarios.cambiar_activo(p.bd, id, activar)
    return Respuesta.redirigir("/admin").con_aviso("ok", "Cuenta reactivada." if activar else "Cuenta desactivada.")


@ruta("POST", "/admin/clubes/<id>/lider")
@requiere_admin
def asignar_lider(p, id):
    club = clubes.por_id_simple(p.bd, id)
    if not club:
        raise ErrorHttp(404, "Ese club no existe.")
    cif = (p.formulario.get("cif") or "").strip()
    persona = usuarios.por_cif(p.bd, cif) if frm.RE_CIF.match(cif) else None
    if not persona or not persona.activo:
        return Respuesta.redirigir("/admin").con_aviso("error", "No existe una cuenta activa con ese CIF.")
    clubes.asignar_lider(p.bd, club.id, persona.id)
    notificaciones.crear(p.bd, persona.id, f"La administración te asignó como líder de {club.nombre}.", f"/clubes/{club.slug}")
    return Respuesta.redirigir("/admin").con_aviso("ok", f"{persona.nombre} es ahora líder de {club.nombre}.")


@ruta("POST", "/admin/clubes/<id>")
@requiere_admin
def cambiar_estado_club(p, id):
    club = clubes.por_id_simple(p.bd, id)
    if not club:
        raise ErrorHttp(404, "Ese club no existe.")
    activar = p.formulario.get("activo") == "1"
    clubes.cambiar_estado(p.bd, id, "activo" if activar else "inactivo")
    return Respuesta.redirigir("/admin").con_aviso("ok", "Club reactivado." if activar else "Club desactivado.")


@ruta("POST", "/admin/capitanes/<id>")
@requiere_admin
def resolver_solicitud_capitan(p, id):
    """La administración aprueba (el miembro pasa a capitán) o rechaza una solicitud de capitán."""
    decision = p.formulario.get("decision")
    if decision not in ("aprobar", "rechazar"):
        raise ErrorHttp(400, "Decisión no válida.")
    comentario = frm.texto(p.formulario, frm.Errores(), "comentario", "El comentario", 1, 500, obligatorio=False)
    s = clubes.resolver_solicitud_capitan(p.bd, id, p.usuario.id, decision == "aprobar", comentario)
    if not s:
        return Respuesta.redirigir("/admin").con_aviso("error", "Esa solicitud ya fue resuelta.")
    club = clubes.por_id_simple(p.bd, s.club_id)
    if s.aprobada:
        notificaciones.crear(p.bd, s.usuario_id, f"Tu solicitud fue aprobada: ahora eres capitán de {club.nombre}.",
                             f"/clubes/{club.slug}")
        return Respuesta.redirigir("/admin").con_aviso("ok", f"Nuevo capitán asignado en {club.nombre}.")
    notificaciones.crear(p.bd, s.usuario_id, f"Tu solicitud para ser capitán de {club.nombre} no fue aprobada.",
                         f"/clubes/{club.slug}")
    return Respuesta.redirigir("/admin").con_aviso("ok", "Solicitud de capitán rechazada.")
