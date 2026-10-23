"""Foro del club: publicaciones, comentarios, votos y reacciones."""
import secrets

from .. import config, formularios as frm
from ..acceso import (requiere_sesion, club_o_404, contexto_club, exigir_miembro, es_admin, es_responsable,
                      destino_seguro)
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import clubes, foro
from ..vistas import render
from .inicio import marcar_permisos


def _publicacion_o_404(p, id):
    pub = foro.publicacion(p.bd, id, p.usuario.id)
    if not pub:
        raise ErrorHttp(404, "Esa publicación no existe o fue eliminada.")
    return pub


def _puede_moderar(p, club_id, autor_id):
    return autor_id == p.usuario.id or es_admin(p) or es_responsable(clubes.membresia(p.bd, p.usuario.id, club_id))


@ruta("GET", "/clubes/<slug>")
@requiere_sesion
def foro_club(p, slug):
    club = club_o_404(p, slug)
    orden = "populares" if p.consulta.get("orden") == "populares" else "nuevos"
    pagina = int(p.consulta["pagina"]) if (p.consulta.get("pagina") or "").isdigit() else 1
    pubs = foro.listar(p.bd, p.usuario.id, club_id=club.id, orden=orden, limite=21, pagina=pagina)
    hay_mas = len(pubs) > 20
    return render(p, "club_foro.html", publicaciones=marcar_permisos(p, pubs[:20]), orden=orden, pagina=pagina,
                  hay_mas=hay_mas, **contexto_club(p, club, "foro"))


@ruta("GET", "/clubes/<slug>/publicar")
@requiere_sesion
def publicar_formulario(p, slug):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    return render(p, "publicar.html", valores={}, errores=frm.Errores(), **contexto_club(p, club, "foro"))


@ruta("POST", "/clubes/<slug>/publicar")
@requiere_sesion
def publicar(p, slug):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    errores = frm.Errores()
    titulo = frm.texto(p.formulario, errores, "titulo", "El título", 3, 150)
    contenido = frm.texto(p.formulario, errores, "contenido", "El texto", 1, 10000, obligatorio=False, una_linea=False)
    archivo = p.archivos.get("imagen")
    extension = frm.validar_imagen(archivo, errores)
    if errores:
        return render(p, "publicar.html", 400, valores={"titulo": titulo, "contenido": contenido}, errores=errores,
                      **contexto_club(p, club, "foro"))
    nombre_imagen = ""
    if extension:
        nombre_imagen = f"{secrets.token_hex(16)}.{extension}"
        (config.DIR_SUBIDAS / nombre_imagen).write_bytes(archivo.datos)
    nuevo_id = foro.crear_publicacion(p.bd, club.id, p.usuario.id, titulo, contenido, nombre_imagen)
    return Respuesta.redirigir(f"/publicaciones/{nuevo_id}").con_aviso("ok", "Publicación creada.")


@ruta("GET", "/publicaciones/<id>")
@requiere_sesion
def hilo(p, id):
    pub = _publicacion_o_404(p, id)
    club = clubes.por_slug(p.bd, pub.club_slug)
    ctx = contexto_club(p, club, "foro")
    pub["puede_eliminar"] = _puede_moderar(p, pub.club_id, pub.autor_id)
    lista = foro.comentarios(p.bd, id, p.usuario.id)
    roles_mod = ctx["es_responsable"] or es_admin(p)
    for c in lista:
        c["puede_eliminar"] = (not c.eliminado) and (c.autor_id == p.usuario.id or roles_mod)
    return render(p, "hilo.html", pub=pub, comentarios=lista, errores=frm.Errores(), **ctx)


@ruta("POST", "/publicaciones/<id>/comentar")
@requiere_sesion
def comentar(p, id):
    pub = _publicacion_o_404(p, id)
    club = clubes.por_slug(p.bd, pub.club_slug)
    exigir_miembro(p, club)
    errores = frm.Errores()
    contenido = frm.texto(p.formulario, errores, "contenido", "El comentario", 1, 5000, una_linea=False)
    padre_txt = p.formulario.get("padre_id") or ""
    padre = None
    if padre_txt.isdigit():
        candidato = foro.comentario(p.bd, int(padre_txt))
        if not candidato or candidato.publicacion_id != id:
            raise ErrorHttp(400, "El comentario al que respondes no existe.")
        padre = candidato.id
    if errores:
        return Respuesta.redirigir(f"/publicaciones/{id}").con_aviso("error", errores["contenido"])
    foro.crear_comentario(p.bd, id, p.usuario.id, padre, contenido)
    return Respuesta.redirigir(f"/publicaciones/{id}#comentarios").con_aviso("ok", "Comentario publicado.")


@ruta("POST", "/publicaciones/<id>/votar")
@requiere_sesion
def votar_publicacion(p, id):
    pub = _publicacion_o_404(p, id)
    valor = p.formulario.get("valor")
    if valor not in ("1", "-1"):
        raise ErrorHttp(400, "Voto no válido.")
    foro.votar(p.bd, "publicacion", p.usuario.id, id, int(valor))
    return Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), f"/publicaciones/{id}"))


@ruta("POST", "/comentarios/<id>/votar")
@requiere_sesion
def votar_comentario(p, id):
    comentario = foro.comentario(p.bd, id)
    if not comentario or comentario.eliminado:
        raise ErrorHttp(404, "Ese comentario no existe.")
    valor = p.formulario.get("valor")
    if valor not in ("1", "-1"):
        raise ErrorHttp(400, "Voto no válido.")
    foro.votar(p.bd, "comentario", p.usuario.id, id, int(valor))
    return Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), f"/publicaciones/{comentario.publicacion_id}"))


@ruta("POST", "/publicaciones/<id>/reaccion")
@requiere_sesion
def reaccionar(p, id):
    _publicacion_o_404(p, id)
    tipo = p.formulario.get("tipo") or ""
    if tipo not in foro.TIPOS_REACCION:
        raise ErrorHttp(400, "Reacción no válida.")
    foro.alternar_reaccion(p.bd, p.usuario.id, id, tipo)
    return Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), f"/publicaciones/{id}"))


@ruta("POST", "/publicaciones/<id>/eliminar")
@requiere_sesion
def eliminar_publicacion(p, id):
    pub = _publicacion_o_404(p, id)
    if not _puede_moderar(p, pub.club_id, pub.autor_id):
        raise ErrorHttp(403, "No tienes permiso para eliminar esta publicación.")
    foro.eliminar_publicacion(p.bd, id)
    return Respuesta.redirigir(f"/clubes/{pub.club_slug}").con_aviso("ok", "Publicación eliminada.")


@ruta("POST", "/comentarios/<id>/eliminar")
@requiere_sesion
def eliminar_comentario(p, id):
    comentario = foro.comentario(p.bd, id)
    if not comentario:
        raise ErrorHttp(404, "Ese comentario no existe.")
    if not _puede_moderar(p, comentario.club_id, comentario.autor_id):
        raise ErrorHttp(403, "No tienes permiso para eliminar este comentario.")
    foro.eliminar_comentario(p.bd, id)
    return Respuesta.redirigir(f"/publicaciones/{comentario.publicacion_id}#comentarios").con_aviso("ok", "Comentario eliminado.")
