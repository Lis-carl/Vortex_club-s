"""Propuestas de evento y calendario de eventos aprobados."""
import calendar
from datetime import date, datetime

from .. import formularios as frm
from ..acceso import requiere_sesion, club_o_404, contexto_club, exigir_miembro, exigir_responsable, destino_seguro
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..nucleo import Fila
from ..repositorios import clubes, eventos, notificaciones
from ..utilidades import MESES_LARGOS
from ..vistas import render


DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


@ruta("GET", "/eventos")
@requiere_sesion
def proximos(p):
    """Calendario mensual de actividades (pedido en la encuesta) y lista de próximos eventos."""
    hoy = date.today()
    try:
        anio, mes = (int(x) for x in (p.consulta.get("mes") or "").split("-"))
        date(anio, mes, 1)
    except ValueError:
        anio, mes = hoy.year, hoy.month
    solo_mios = p.consulta.get("vista") == "mios"
    orden = "votos" if p.consulta.get("orden") == "votos" else "fecha"
    del_mes = eventos.del_mes(p.bd, p.usuario.id, anio, mes, solo_mios, orden)
    por_dia = {}
    for e in del_mes:
        por_dia.setdefault(int(e.fecha_inicio[8:10]), []).append(e)
    semanas = [[Fila(dia=d, eventos=por_dia.get(d, []), hoy=(date(anio, mes, d) == hoy) if d else False)
                for d in semana] for semana in calendar.Calendar(firstweekday=0).monthdayscalendar(anio, mes)]
    anterior = (anio - 1, 12) if mes == 1 else (anio, mes - 1)
    siguiente = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
    return render(p, "eventos.html", semanas=semanas, dias_semana=DIAS_SEMANA, titulo_mes=f"{MESES_LARGOS[mes - 1]} {anio}",
                  mes_anterior=f"{anterior[0]:04d}-{anterior[1]:02d}", mes_siguiente=f"{siguiente[0]:04d}-{siguiente[1]:02d}",
                  mes_actual=f"{anio:04d}-{mes:02d}", vista="mios" if solo_mios else "todos", orden=orden,
                  destacados=eventos.destacados(p.bd, p.usuario.id), eventos_mes=del_mes)


@ruta("POST", "/eventos/<id>/asistencia")
@requiere_sesion
def asistencia(p, id):
    """Confirma o cancela la asistencia a un evento aprobado y futuro."""
    e = eventos.evento(p.bd, id, p.usuario.id)
    if not e:
        raise ErrorHttp(404, "Ese evento no existe o no está aprobado.")
    volver = Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), "/eventos"))
    if e.fecha_inicio < datetime.now().strftime("%Y-%m-%d %H:%M"):
        return volver.con_aviso("error", "Ese evento ya ocurrió.")
    try:
        confirmado = eventos.alternar_asistencia(p.bd, p.usuario.id, id)
    except ValueError as error:
        return volver.con_aviso("error", str(error))
    return volver.con_aviso("ok", f"Asistencia confirmada a «{e.titulo}». Te lo recordaremos en tu inicio."
                            if confirmado else f"Cancelaste tu asistencia a «{e.titulo}».")


@ruta("GET", "/clubes/<slug>/eventos")
@requiere_sesion
def eventos_club(p, slug):
    club = club_o_404(p, slug)
    ctx = contexto_club(p, club, "eventos")
    proximos_club, pasados = eventos.del_club(p.bd, club.id, p.usuario.id)
    if ctx["es_responsable"]:
        for e in proximos_club:
            e["asistentes"] = eventos.asistentes(p.bd, e.id)
    return render(p, "club_eventos.html", proximos=proximos_club, pasados=pasados,
                  pendientes=eventos.pendientes(p.bd, club.id, p.usuario.id) if ctx["es_miembro"] else [],
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
    responsables = [m.usuario_id for m in clubes.integrantes(p.bd, club.id) if m.rol in ("lider", "capitan")]
    notificaciones.crear_para_varios(p.bd, responsables, f"Nueva propuesta de evento en {club.nombre}: {titulo}",
                                     f"/clubes/{slug}/eventos", excepto=p.usuario.id)
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
    enlace = f"/clubes/{club.slug}/eventos"
    resultado = "aprobada" if decision == "aprobar" else "rechazada"
    notificaciones.crear(p.bd, propuesta.proponente_id, f"Tu propuesta «{propuesta.titulo}» fue {resultado}.", enlace)
    if decision == "aprobar":
        notificaciones.crear_para_club(p.bd, club.id, f"Nuevo evento en {club.nombre}: {propuesta.titulo}. "
                                       "Confirma tu asistencia.", enlace, excepto=propuesta.proponente_id)
    return volver.con_aviso("ok", "Propuesta aprobada." if decision == "aprobar" else "Propuesta rechazada.")


@ruta("POST", "/propuestas/<id>/votar")
@requiere_sesion
def votar_propuesta(p, id):
    """Los miembros apoyan o rechazan una propuesta. Si alcanza el umbral de apoyos, se aprueba sola."""
    propuesta = eventos.por_id(p.bd, id)
    if not propuesta:
        raise ErrorHttp(404, "Esa propuesta no existe.")
    club = clubes.por_id_simple(p.bd, propuesta.club_id)
    if propuesta.estado == "aprobada":
        return _votar_evento(p, propuesta)
    m = clubes.membresia(p.bd, p.usuario.id, club.id)
    if not m or m.estado != "activa":
        raise ErrorHttp(403, "Solo los miembros del club pueden votar sus propuestas.")
    volver = Respuesta.redirigir(f"/clubes/{club.slug}/eventos#propuesta-{id}")
    if propuesta.estado != "pendiente":
        return volver.con_aviso("error", "Esa propuesta ya fue revisada.")
    if propuesta.proponente_id == p.usuario.id:
        return volver.con_aviso("error", "No puedes votar tu propia propuesta.")
    valor = p.formulario.get("valor")
    if valor not in ("1", "-1"):
        raise ErrorHttp(400, "Voto no válido.")
    apoyos, contras = eventos.votar_propuesta(p.bd, p.usuario.id, id, int(valor))
    umbral = eventos.umbral_votacion(p.bd, club.id)
    futura = datetime.strptime(propuesta.fecha_inicio, "%Y-%m-%d %H:%M") > datetime.now()
    if apoyos >= umbral and apoyos > contras and futura:
        eventos.revisar(p.bd, id, p.usuario.id, True, f"Aprobada por votación de los miembros ({apoyos} apoyos).")
        enlace = f"/clubes/{club.slug}/eventos"
        notificaciones.crear(p.bd, propuesta.proponente_id,
                             f"Tu propuesta «{propuesta.titulo}» fue aprobada por votación de los miembros.", enlace)
        notificaciones.crear_para_club(p.bd, club.id, f"Nuevo evento en {club.nombre}: {propuesta.titulo}. "
                                       "Confirma tu asistencia.", enlace, excepto=propuesta.proponente_id)
        return Respuesta.redirigir(f"/clubes/{club.slug}/eventos").con_aviso(
            "ok", f"¡La propuesta alcanzó {apoyos} apoyos y quedó aprobada!")
    faltan = max(0, umbral - apoyos)
    return volver.con_aviso("ok", f"Voto registrado. Faltan {faltan} apoyo{'s' if faltan != 1 else ''} para aprobarla."
                            if faltan else "Voto registrado.")


def _votar_evento(p, propuesta):
    """Con el evento ya aprobado, cualquier estudiante puede votar «Me interesa» para posicionarlo
    entre los eventos de todos los clubes (calendario general y destacados)."""
    volver = Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), "/eventos"))
    if propuesta.fecha_inicio < datetime.now().strftime("%Y-%m-%d %H:%M"):
        return volver.con_aviso("error", "Ese evento ya ocurrió.")
    if propuesta.proponente_id == p.usuario.id:
        return volver.con_aviso("error", "No puedes votar el evento que tú propusiste.")
    valor = p.formulario.get("valor")
    if valor not in ("1", "-1"):
        raise ErrorHttp(400, "Voto no válido.")
    eventos.votar_propuesta(p.bd, p.usuario.id, propuesta.id, int(valor))
    return volver
