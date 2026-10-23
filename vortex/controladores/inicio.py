"""Feed de inicio y anuncios generales."""
from .. import formularios as frm
from ..acceso import requiere_sesion, es_admin, es_responsable, destino_seguro
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import anuncios, clubes, eventos, foro
from ..vistas import render


def marcar_permisos(p, publicaciones):
    """Agrega a cada publicación si el usuario puede eliminarla (autor, líder/capitán del club o admin)."""
    roles ={c.id: c.rol for c in clubes.mis_clubes(p.bd, p.usuario.id)}
    for pub in publicaciones:
        pub["puede_eliminar"] = (pub.autor_id == p.usuario.id or es_admin(p)
                                 or roles.get(pub.club_id) in ("lider", "capitan"))
    return publicaciones


@ruta("GET", "/")
@requiere_sesion
def feed(p):
    tiene_clubes = bool(clubes.mis_clubes(p.bd, p.usuario.id))
    ver = p.consulta.get("ver") or ("mis" if tiene_clubes else "todos")
    orden = "populares" if p.consulta.get("orden") == "populares" else "nuevos"
    pagina = int(p.consulta["pagina"]) if (p.consulta.get("pagina") or "").isdigit() else 1
    pubs = foro.listar(p.bd, p.usuario.id, solo_mis_clubes=(ver == "mis"), orden=orden, limite=21, pagina=pagina)
    hay_mas = len(pubs) > 20
    pubs = marcar_permisos(p, pubs[:20])
    return render(p, "inicio.html", publicaciones=pubs, ver=ver, orden=orden, pagina=pagina, hay_mas=hay_mas,
                  tiene_clubes=tiene_clubes, anuncios_generales=anuncios.listar(p.bd, None, 3),
                  proximos=eventos.proximos(p.bd, 3))


@ruta("GET", "/anuncios")
@requiere_sesion
def anuncios_generales(p):
    return render(p, "anuncios.html", anuncios=anuncios.listar(p.bd, None), valores={}, errores=frm.Errores())


@ruta("POST", "/anuncios")
@requiere_sesion
def publicar_anuncio_general(p):
    if not es_admin(p):
        raise ErrorHttp(403, "Solo la administración puede publicar anuncios generales.")
    errores = frm.Errores()
    titulo = frm.texto(p.formulario, errores, "titulo", "El título", 3, 150)
    contenido = frm.texto(p.formulario, errores, "contenido", "El contenido", 1, 5000, una_linea=False)
    fijado = p.formulario.get("fijado") == "1"
    if errores:
        return render(p, "anuncios.html", 400, anuncios=anuncios.listar(p.bd, None),
                      valores={"titulo": titulo, "contenido": contenido}, errores=errores)
    anuncios.crear(p.bd, None, p.usuario.id, titulo, contenido, fijado)
    return Respuesta.redirigir("/anuncios").con_aviso("ok", "Anuncio publicado.")


@ruta("POST", "/anuncios/<id>/eliminar")
@requiere_sesion
def eliminar_anuncio(p, id):
    anuncio = anuncios.por_id(p.bd, id)
    if not anuncio:
        raise ErrorHttp(404, "Ese anuncio no existe.")
    permitido = es_admin(p)
    if anuncio.club_id and not permitido:
        permitido = es_responsable(clubes.membresia(p.bd, p.usuario.id, anuncio.club_id))
    if not permitido:
        raise ErrorHttp(403, "No tienes permiso para eliminar este anuncio.")
    anuncios.eliminar(p.bd, id)
    return Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), "/anuncios")).con_aviso("ok", "Anuncio eliminado.")
