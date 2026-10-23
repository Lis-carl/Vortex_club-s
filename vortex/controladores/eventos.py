"""Propuestas de evento y calendario de eventos aprobados."""
from datetime import datetime

from .. import formularios as frm
from ..acceso import requiere_sesion, club_o_404, contexto_club, exigir_miembro, exigir_responsable
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import clubes, eventos
from ..vistas import render


@ruta("GET", "/eventos")
@requiere_sesion
def proximos(p):
    return render(p, "eventos.html", eventos=eventos.proximos(p.bd))


@ruta("GET", "/clubes/<slug>/eventos")
@requiere_sesion
def eventos_club(p, slug):
    club = club_o_404(p, slug)
    ctx = contexto_club(p, club, "eventos")
    proximos_club, pasados = eventos.del_club(p.bd, club.id)
    return render(p, "club_eventos.html", proximos=proximos_club, pasados=pasados,
                  pendientes=eventos.pendientes(p.bd, club.id) if ctx["es_responsable"] else [],
                  mias=eventos.mias(p.bd, club.id, p.usuario.id) if ctx["es_miembro"] else [], **ctx)


@ruta("GET", "/clubes/<slug>/eventos/proponer")
@requiere_sesion
def proponer_formulario(p, slug):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    return render(p, "proponer_evento.html", valores={}, errores=frm.Errores(), **contexto_club(p, club, "eventos"))


@ruta("POST", "/clubes/<slug>/eventos/proponer")
@requiere_sesion
def proponer(p, slug):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    f, errores = p.formulario, frm.Errores()
    titulo = frm.texto(f, errores, "titulo", "El título", 3, 150)
    descripcion = frm.texto(f, errores, "descripcion", "La descripción", 10, 3000, una_linea=False)
    lugar = frm.texto(f, errores, "lugar", "El lugar", 2, 120)
    recursos = frm.texto(f, errores, "recursos", "Los recursos", 1, 1000, obligatorio=False, una_linea=False)
    cupo = frm.entero(f, errores, "cupo", "El cupo", 1, 10000)
    fecha_txt = (f.get("fecha_inicio") or "").strip()
    fecha = None
    try:
        fecha = datetime.strptime(fecha_txt, "%Y-%m-%dT%H:%M")
    except ValueError:
        errores["fecha_inicio"] = "Elige una fecha y hora válidas."
    if fecha and fecha <= datetime.now():
        errores["fecha_inicio"] = "La fecha del evento debe ser posterior a este momento."
    if errores:
        return render(p, "proponer_evento.html", 400, errores=errores, **contexto_club(p, club, "eventos"),
                      valores={"titulo": titulo, "descripcion": descripcion, "lugar": lugar, "recursos": recursos,
                               "cupo": f.get("cupo"), "fecha_inicio": fecha_txt})
    eventos.proponer(p.bd, club.id, p.usuario.id, titulo, descripcion, fecha.strftime("%Y-%m-%d %H:%M"), lugar,
                     cupo, recursos)
    return Respuesta.redirigir(f"/clubes/{slug}/eventos").con_aviso(
        "ok", "Propuesta enviada. Un líder o capitán la revisará.")


@ruta("POST", "/propuestas/<id>/revisar")
@requiere_sesion
def revisar(p, id):
    propuesta = eventos.por_id(p.bd, id)
    if not propuesta:
        raise ErrorHttp(404, "Esa propuesta no existe.")
    club = clubes.por_id_simple(p.bd, propuesta.club_id)
    exigir_responsable(p, club)
    volver = Respuesta.redirigir(f"/clubes/{club.slug}/eventos")
    if propuesta.estado != "pendiente":
        return volver.con_aviso("error", "Esa propuesta ya fue revisada.")
    decision = p.formulario.get("decision")
    if decision not in ("aprobar", "rechazar"):
        raise ErrorHttp(400, "Decisión no válida.")
    comentario = frm.texto(p.formulario, frm.Errores(), "comentario", "El comentario", 1, 500, obligatorio=False)
    if decision == "aprobar":
        if datetime.strptime(propuesta.fecha_inicio, "%Y-%m-%d %H:%M") <= datetime.now():
            return volver.con_aviso("error", "No se puede aprobar: la fecha del evento ya pasó.")
    eventos.revisar(p.bd, id, p.usuario.id, decision == "aprobar", comentario)
    return volver.con_aviso("ok", "Propuesta aprobada." if decision == "aprobar" else "Propuesta rechazada.")
