"""Catálogo, solicitud de clubes, membresías, anuncios del club y miembros."""
import secrets

from .. import config, formularios as frm
from ..acceso import (requiere_sesion, club_o_404, contexto_club, exigir_responsable, es_lider_en, es_admin)
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import anuncios, clubes, notificaciones
from ..vistas import render


@ruta("GET", "/clubes")
@requiere_sesion
def catalogo(p):
    return render(p, "catalogo.html", lista=clubes.catalogo(p.bd, p.usuario.id))


@ruta("GET", "/clubes/solicitar")
@requiere_sesion
def solicitar_formulario(p):
    return render(p, "solicitar_club.html", valores={}, errores=frm.Errores(),
                  solicitudes=clubes.solicitudes_de(p.bd, p.usuario.id))


@ruta("POST", "/clubes/solicitar")
@requiere_sesion
def solicitar(p):
    f, errores = p.formulario, frm.Errores()
    nombre = frm.texto(f, errores, "nombre", "El nombre del club", 3, 60)
    descripcion = frm.texto(f, errores, "descripcion", "La descripción", 10, 1000, una_linea=False)
    justificacion = frm.texto(f, errores, "justificacion", "La justificación", 1, 1000, obligatorio=False, una_linea=False)
    if "nombre" not in errores and clubes.nombre_ocupado(p.bd, nombre):
        errores["nombre"] = "Ya existe un club (o una solicitud pendiente) con ese nombre."
    if errores:
        return render(p, "solicitar_club.html", 400, valores={"nombre": nombre, "descripcion": descripcion,
                      "justificacion": justificacion, "con_aprobacion": f.get("con_aprobacion")},
                      errores=errores, solicitudes=clubes.solicitudes_de(p.bd, p.usuario.id))
    clubes.crear_solicitud(p.bd, p.usuario.id, nombre, descripcion, justificacion, f.get("con_aprobacion") == "1")
    return Respuesta.redirigir("/clubes/solicitar").con_aviso(
        "ok", "Solicitud enviada. La administración la revisará y quedarás como líder del club.")


@ruta("POST", "/clubes/<slug>/unirse")
@requiere_sesion
def unirse(p, slug):
    club = club_o_404(p, slug)
    if club.estado != "activo":
        raise ErrorHttp(403, "Este club está desactivado.")
    existente = clubes.membresia(p.bd, p.usuario.id, club.id)
    if existente:
        mensaje = "Ya eres miembro de este club." if existente.estado == "activa" else "Tu solicitud ya está pendiente."
        return Respuesta.redirigir(f"/clubes/{slug}").con_aviso("error", mensaje)
    pendiente = bool(club.requiere_aprobacion)
    clubes.unirse(p.bd, p.usuario.id, club.id, pendiente)
    if pendiente:
        responsables = [m.usuario_id for m in clubes.integrantes(p.bd, club.id) if m.rol in ("lider", "capitan")]
        notificaciones.crear_para_varios(p.bd, responsables, f"{p.usuario.nombre} solicitó unirse a {club.nombre}.",
                                         f"/clubes/{slug}/miembros")
    mensaje = "Solicitud enviada; un responsable del club la revisará." if pendiente else "¡Te uniste al club!"
    return Respuesta.redirigir(f"/clubes/{slug}").con_aviso("ok", mensaje)


@ruta("POST", "/clubes/<slug>/salir")
@requiere_sesion
def salir(p, slug):
    club = club_o_404(p, slug)
    m = clubes.membresia(p.bd, p.usuario.id, club.id)
    if not m:
        raise ErrorHttp(404, "No perteneces a este club.")
    if m.rol == "lider":
        return Respuesta.redirigir(f"/clubes/{slug}/miembros").con_aviso(
            "error", "Eres el líder: transfiere el liderazgo a otro miembro antes de salir.")
    clubes.quitar(p.bd, m.id)
    return Respuesta.redirigir(f"/clubes/{slug}").con_aviso("ok", "Saliste del club.")


@ruta("GET", "/clubes/<slug>/editar")
@requiere_sesion
def editar_formulario(p, slug):
    club = club_o_404(p, slug)
    ctx = contexto_club(p, club, "editar")
    if not ctx["es_responsable"]:
        raise ErrorHttp(403, "Solo el líder, los capitanes o la administración pueden editar el club.")
    return render(p, "club_editar.html", errores=frm.Errores(),
                  valores={"descripcion": club.descripcion,
                           "con_aprobacion": "1" if club.requiere_aprobacion else ""}, **ctx)


@ruta("POST", "/clubes/<slug>/editar")
@requiere_sesion
def editar(p, slug):
    club = club_o_404(p, slug)
    ctx = contexto_club(p, club, "editar")
    if not ctx["es_responsable"]:
        raise ErrorHttp(403, "Solo el líder, los capitanes o la administración pueden editar el club.")
    f, errores = p.formulario, frm.Errores()
    descripcion = frm.texto(f, errores, "descripcion", "La descripción", 10, 1000, una_linea=False)
    if errores:
        return render(p, "club_editar.html", 400, errores=errores,
                      valores={"descripcion": descripcion,
                               "con_aprobacion": f.get("con_aprobacion")}, **ctx)
    clubes.actualizar(p.bd, club.id, descripcion, f.get("con_aprobacion") == "1")
    return Respuesta.redirigir(f"/clubes/{slug}").con_aviso("ok", "Cambios guardados.")


# --- Anuncios del club ------------------------------------------------------------------------
@ruta("GET", "/clubes/<slug>/anuncios")
@requiere_sesion
def anuncios_club(p, slug):
    club = club_o_404(p, slug)
    return render(p, "club_anuncios.html", anuncios=anuncios.listar(p.bd, club.id), valores={},
                  errores=frm.Errores(), **contexto_club(p, club, "anuncios"))


@ruta("POST", "/clubes/<slug>/anuncios")
@requiere_sesion
def publicar_anuncio(p, slug):
    club = club_o_404(p, slug)
    exigir_responsable(p, club)
    errores = frm.Errores()
    titulo = frm.texto(p.formulario, errores, "titulo", "El título", 3, 150)
    contenido = frm.texto(p.formulario, errores, "contenido", "El contenido", 1, 5000, una_linea=False)
    if errores:
        return render(p, "club_anuncios.html", 400, anuncios=anuncios.listar(p.bd, club.id),
                      valores={"titulo": titulo, "contenido": contenido}, errores=errores,
                      **contexto_club(p, club, "anuncios"))
    anuncios.crear(p.bd, club.id, p.usuario.id, titulo, contenido, p.formulario.get("fijado") == "1")
    notificaciones.crear_para_club(p.bd, club.id, f"Nuevo anuncio en {club.nombre}: {titulo}",
                                   f"/clubes/{slug}/anuncios", excepto=p.usuario.id)
    return Respuesta.redirigir(f"/clubes/{slug}/anuncios").con_aviso("ok", "Anuncio publicado.")


# --- Miembros -----------------------------------------------------------------------------------
@ruta("GET", "/clubes/<slug>/miembros")
@requiere_sesion
def miembros(p, slug):
    club = club_o_404(p, slug)
    ctx = contexto_club(p, club, "miembros")
    lista = clubes.integrantes(p.bd, club.id)
    return render(p, "club_miembros.html", lideres=[m for m in lista if m.rol == "lider"],
                  capitanes=[m for m in lista if m.rol == "capitan"], simples=[m for m in lista if m.rol == "miembro"],
                  pendientes=clubes.pendientes(p.bd, club.id) if ctx["es_responsable"] else [], **ctx)


@ruta("POST", "/clubes/<slug>/miembros/<mid>")
@requiere_sesion
def gestionar_miembro(p, slug, mid):
    club = club_o_404(p, slug)
    exigir_responsable(p, club)
    objetivo = clubes.membresia_por_id(p.bd, mid)
    if not objetivo or objetivo.club_id != club.id:
        raise ErrorHttp(404, "Ese integrante no existe en el club.")
    accion = p.formulario.get("accion") or ""
    volver = Respuesta.redirigir(f"/clubes/{slug}/miembros")

    if accion in ("aceptar", "rechazar"):
        if objetivo.estado != "pendiente":
            return volver.con_aviso("error", "Esa solicitud ya fue resuelta.")
        if accion == "aceptar":
            clubes.aceptar(p.bd, objetivo.id)
            notificaciones.crear(p.bd, objetivo.usuario_id, f"Tu solicitud para unirte a {club.nombre} fue aceptada.",
                                 f"/clubes/{slug}")
            return volver.con_aviso("ok", "Solicitud aceptada.")
        clubes.quitar(p.bd, objetivo.id)
        notificaciones.crear(p.bd, objetivo.usuario_id, f"Tu solicitud para unirte a {club.nombre} no fue aceptada.",
                             "/clubes")
        return volver.con_aviso("ok", "Solicitud rechazada.")

    if not es_lider_en(p, club.id):
        raise ErrorHttp(403, "Solo el líder o la administración pueden cambiar roles o expulsar.")
    if objetivo.estado != "activa":
        raise ErrorHttp(400, "Primero acepta la solicitud de ingreso.")
    if objetivo.rol == "lider":
        return volver.con_aviso("error", "No puedes modificar al líder. Usa «Transferir liderazgo» con otro miembro.")
    if accion == "hacer_capitan" and objetivo.rol == "miembro":
        clubes.cambiar_rol(p.bd, objetivo.id, "capitan")
        notificaciones.crear(p.bd, objetivo.usuario_id, f"Ahora eres capitán de {club.nombre}.", f"/clubes/{slug}")
        return volver.con_aviso("ok", "Ahora es capitán.")
    if accion == "quitar_capitan" and objetivo.rol == "capitan":
        clubes.cambiar_rol(p.bd, objetivo.id, "miembro")
        return volver.con_aviso("ok", "Ya no es capitán.")
    if accion == "expulsar":
        clubes.quitar(p.bd, objetivo.id)
        return volver.con_aviso("ok", "Integrante expulsado del club.")
    if accion == "transferir":
        clubes.transferir_liderazgo(p.bd, club.id, objetivo.id)
        notificaciones.crear(p.bd, objetivo.usuario_id, f"Ahora eres líder de {club.nombre}.", f"/clubes/{slug}")
        return volver.con_aviso("ok", "Liderazgo transferido. El líder anterior pasó a ser capitán.")
    raise ErrorHttp(400, "Acción no válida.")


# --- Solicitud para ser capitán ------------------------------------------------------------------
@ruta("POST", "/clubes/<slug>/solicitar-capitan")
@requiere_sesion
def solicitar_capitan(p, slug):
    """Un miembro pide ser capitán; la administración aprueba o rechaza la petición."""
    club = club_o_404(p, slug)
    m = clubes.membresia(p.bd, p.usuario.id, club.id)
    volver = Respuesta.redirigir(f"/clubes/{slug}")
    if not m or m.estado != "activa":
        raise ErrorHttp(403, "Debes ser miembro del club para pedir ser capitán.")
    if m.rol != "miembro":
        return volver.con_aviso("error", "Ya eres capitán o líder de este club.")
    if clubes.solicitud_capitan_pendiente(p.bd, p.usuario.id, club.id):
        return volver.con_aviso("error", "Ya tienes una solicitud pendiente para este club.")
    motivo = frm.texto(p.formulario, frm.Errores(), "motivo", "El motivo", 1, 500, obligatorio=False, una_linea=False)
    clubes.crear_solicitud_capitan(p.bd, p.usuario.id, club.id, motivo)
    notificaciones.crear_para_admins(p.bd, f"{p.usuario.nombre} pidió ser capitán de {club.nombre}.")
    return volver.con_aviso("ok", "Solicitud enviada. La administración la revisará.")


# --- Foto del club -------------------------------------------------------------------------------
def _borrar_archivo(nombre):
    if nombre:
        ruta = config.DIR_SUBIDAS / nombre
        if ruta.is_file():
            ruta.unlink()


@ruta("POST", "/clubes/<slug>/foto")
@requiere_sesion
def cambiar_foto_club(p, slug):
    """El líder, los capitanes o la administración cambian la foto de perfil del club."""
    club = club_o_404(p, slug)
    exigir_responsable(p, club)
    volver = Respuesta.redirigir(f"/clubes/{slug}/editar")
    archivo = p.archivos.get("foto")
    if not archivo or not archivo.datos:
        return volver.con_aviso("error", "Elige una imagen para la foto del club.")
    errores = frm.Errores()
    extension = frm.validar_imagen(archivo, errores, "foto")
    if errores:
        return volver.con_aviso("error", errores["foto"])
    nombre = f"{secrets.token_hex(16)}.{extension}"
    (config.DIR_SUBIDAS / nombre).write_bytes(archivo.datos)
    _borrar_archivo(clubes.cambiar_foto(p.bd, club.id, nombre))
    return volver.con_aviso("ok", "Foto del club actualizada.")


@ruta("POST", "/clubes/<slug>/foto/quitar")
@requiere_sesion
def quitar_foto_club(p, slug):
    club = club_o_404(p, slug)
    exigir_responsable(p, club)
    _borrar_archivo(clubes.cambiar_foto(p.bd, club.id, ""))
    return Respuesta.redirigir(f"/clubes/{slug}/editar").con_aviso("ok", "Quitaste la foto del club.")
