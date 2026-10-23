"""Panel de administración."""
from .. import formularios as frm
from ..acceso import requiere_admin
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import clubes, usuarios
from ..vistas import render


@ruta("GET", "/admin")
@requiere_admin
def panel(p):
    return render(p, "admin.html", estadisticas=usuarios.estadisticas(p.bd),
                  solicitudes=clubes.solicitudes_pendientes(p.bd), lista_usuarios=usuarios.listar(p.bd),
                  lista_clubes=clubes.todos(p.bd))


@ruta("POST", "/admin/solicitudes/<id>")
@requiere_admin
def resolver_solicitud(p, id):
    decision = p.formulario.get("decision")
    if decision not in ("aprobar", "rechazar"):
        raise ErrorHttp(400, "Decisión no válida.")
    comentario = frm.texto(p.formulario, frm.Errores(), "comentario", "El comentario", 1, 500, obligatorio=False)
    slug = clubes.resolver_solicitud(p.bd, id, p.usuario.id, decision == "aprobar", comentario)
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


@ruta("POST", "/admin/clubes/<id>")
@requiere_admin
def cambiar_estado_club(p, id):
    club = clubes.por_id_simple(p.bd, id)
    if not club:
        raise ErrorHttp(404, "Ese club no existe.")
    activar = p.formulario.get("activo") == "1"
    clubes.cambiar_estado(p.bd, id, "activo" if activar else "inactivo")
    return Respuesta.redirigir("/admin").con_aviso("ok", "Club reactivado." if activar else "Club desactivado.")
