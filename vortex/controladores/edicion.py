"""Editar contenido ya publicado: publicaciones, comentarios, anuncios y mensajes de chat.

Cada autor edita lo suyo; los anuncios también los pueden editar quienes pueden eliminarlos (líder,
capitanes y administración). Lo editado queda marcado con la fecha de edición («editado»).
"""
from .. import formularios as frm
from ..acceso import requiere_sesion, club_o_404, es_admin, es_responsable_en, destino_seguro, exigir_miembro
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import anuncios, chat, foro, privados, usuarios
from ..vistas import render


def _formulario(p, estado=200, **contexto):
    contexto.setdefault("errores", frm.Errores())
    return render(p, "editar.html", estado, **contexto)


# --- Publicaciones ------------------------------------------------------------------------------
def _mi_publicacion(p, id):
    pub = foro.publicacion(p.bd, id, p.usuario.id)
    if not pub:
        raise ErrorHttp(404, "Esa publicación no existe o fue eliminada.")
    if pub.autor_id != p.usuario.id:
        raise ErrorHttp(403, "Solo quien escribió la publicación puede editarla.")
    return pub


@ruta("GET", "/publicaciones/<id>/editar")
@requiere_sesion
def editar_publicacion_formulario(p, id):
    pub = _mi_publicacion(p, id)
    return _formulario(p, titulo_pagina="Editar publicación", accion=f"/publicaciones/{id}/editar",
                       volver=f"/publicaciones/{id}", con_titulo=True, etiqueta_contenido="Texto (opcional)",
                       max_contenido=10000, valores={"titulo": pub.titulo, "contenido": pub.contenido})


@ruta("POST", "/publicaciones/<id>/editar")
@requiere_sesion
def editar_publicacion(p, id):
    _mi_publicacion(p, id)
    errores = frm.Errores()
    titulo = frm.texto(p.formulario, errores, "titulo", "El título", 3, 150)
    contenido = frm.texto(p.formulario, errores, "contenido", "El texto", 1, 10000, obligatorio=False, una_linea=False)
    if errores:
        return _formulario(p, 400, titulo_pagina="Editar publicación", accion=f"/publicaciones/{id}/editar",
                           volver=f"/publicaciones/{id}", con_titulo=True, etiqueta_contenido="Texto (opcional)",
                           max_contenido=10000, valores={"titulo": titulo, "contenido": contenido}, errores=errores)
    foro.editar_publicacion(p.bd, id, titulo, contenido)
    return Respuesta.redirigir(f"/publicaciones/{id}").con_aviso("ok", "Publicación editada.")


# --- Comentarios --------------------------------------------------------------------------------
@ruta("POST", "/comentarios/<id>/editar")
@requiere_sesion
def editar_comentario(p, id):
    comentario = foro.comentario(p.bd, id)
    if not comentario or comentario.eliminado:
        raise ErrorHttp(404, "Ese comentario no existe.")
    if comentario.autor_id != p.usuario.id:
        raise ErrorHttp(403, "Solo quien escribió el comentario puede editarlo.")
    volver = Respuesta.redirigir(f"/publicaciones/{comentario.publicacion_id}#comentario-{id}")
    errores = frm.Errores()
    contenido = frm.texto(p.formulario, errores, "contenido", "El comentario", 1, 5000, una_linea=False)
    if errores:
        return volver.con_aviso("error", errores["contenido"])
    foro.editar_comentario(p.bd, id, contenido)
    return volver.con_aviso("ok", "Comentario editado.")


# --- Anuncios -----------------------------------------------------------------------------------
@ruta("POST", "/anuncios/<id>/editar")
@requiere_sesion
def editar_anuncio(p, id):
    anuncio = anuncios.por_id(p.bd, id)
    if not anuncio:
        raise ErrorHttp(404, "Ese anuncio no existe.")
    permitido = (anuncio.autor_id == p.usuario.id or es_admin(p)
                 or (anuncio.club_id and es_responsable_en(p, anuncio.club_id)))
    if not permitido:
        raise ErrorHttp(403, "No tienes permiso para editar este anuncio.")
    volver = Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), "/anuncios"))
    errores = frm.Errores()
    titulo = frm.texto(p.formulario, errores, "titulo", "El título", 3, 150)
    contenido = frm.texto(p.formulario, errores, "contenido", "El contenido", 1, 5000, una_linea=False)
    if errores:
        return volver.con_aviso("error", next(iter(errores.values())))
    anuncios.editar(p.bd, id, titulo, contenido)
    return volver.con_aviso("ok", "Anuncio editado.")


# --- Mensajes del chat del club y privados -----------------------------------------------------
def _editar_mensaje(p, mensaje, accion, volver, guardar):
    if not mensaje:
        raise ErrorHttp(404, "Ese mensaje no existe.")
    if mensaje.autor_id != p.usuario.id:
        raise ErrorHttp(403, "Solo puedes editar tus propios mensajes.")
    datos = dict(titulo_pagina="Editar mensaje", accion=accion, volver=volver, con_titulo=False,
                 etiqueta_contenido="Mensaje", max_contenido=1000)
    if p.metodo == "GET":
        return _formulario(p, valores={"contenido": mensaje.contenido}, **datos)
    errores = frm.Errores()
    contenido = frm.texto(p.formulario, errores, "contenido", "El mensaje", 1, 1000)
    if errores:
        return _formulario(p, 400, valores={"contenido": contenido}, errores=errores, **datos)
    guardar(contenido)
    return Respuesta.redirigir(volver).con_aviso("ok", "Mensaje editado.")


@ruta("GET", "/clubes/<slug>/chat/<id>/editar")
@ruta("POST", "/clubes/<slug>/chat/<id>/editar")
@requiere_sesion
def editar_mensaje_club(p, slug, id):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    mensaje = chat.mensaje(p.bd, id)
    if mensaje and mensaje.club_id != club.id:
        mensaje = None
    return _editar_mensaje(p, mensaje, f"/clubes/{slug}/chat/{id}/editar", f"/clubes/{slug}/chat",
                           lambda texto: chat.editar(p.bd, id, texto))


@ruta("GET", "/mensajes/<cif>/<id>/editar")
@ruta("POST", "/mensajes/<cif>/<id>/editar")
@requiere_sesion
def editar_mensaje_privado(p, cif, id):
    otro = usuarios.por_cif(p.bd, cif)
    mensaje = privados.mensaje(p.bd, id)
    if not otro or (mensaje and mensaje.receptor_id != otro.id):
        mensaje = None
    return _editar_mensaje(p, mensaje, f"/mensajes/{cif}/{id}/editar", f"/mensajes/{cif}",
                           lambda texto: privados.editar(p.bd, id, texto))
