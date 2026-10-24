"""Inicio, anuncios generales, notificaciones y panel de gestión de líderes y capitanes."""

from .. import formularios as frm
from ..acceso import requiere_sesion, es_admin, es_responsable_en, modo_gestion, destino_seguro
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import anuncios, clubes, eventos, foro, notificaciones
from ..vistas import avisar_eventos_proximos, render


def marcar_permisos(p, publicaciones):
    """Cada publicación indica si el usuario puede eliminarla.

    Un estudiante solo puede eliminar lo que él mismo publicó. El líder o capitán (con ese rol activo)
    puede eliminar en su club, y la administración en todos.
    """
    roles = {c.id: c.rol for c in clubes.mis_clubes(p.bd, p.usuario.id)} if modo_gestion(p) else {}
    for pub in publicaciones:
        pub["puede_eliminar"] = (pub.autor_id == p.usuario.id or es_admin(p)
                                 or roles.get(pub.club_id) in ("lider", "capitan"))
    return publicaciones


@ruta("GET", "/")
@requiere_sesion
def feed(p):
    mis = clubes.mis_clubes(p.bd, p.usuario.id)
    tiene_clubes = bool(mis)
    ver = p.consulta.get("ver") or ("mis" if tiene_clubes else "todos")
    orden = "populares" if p.consulta.get("orden") == "populares" else "nuevos"
    pagina = int(p.consulta["pagina"]) if (p.consulta.get("pagina") or "").isdigit() else 1
    pubs = foro.listar(p.bd, p.usuario.id, solo_mis_clubes=(ver == "mis"), orden=orden, limite=21, pagina=pagina)
    hay_mas = len(pubs) > 20
    avisar_eventos_proximos(p)
    return render(p, "inicio.html", publicaciones=marcar_permisos(p, pubs[:20]), ver=ver, orden=orden, pagina=pagina,
                  hay_mas=hay_mas, tiene_clubes=tiene_clubes,
                  recordatorios=notificaciones.recordatorios_sin_leer(p.bd, p.usuario.id),
                  anuncios_generales=anuncios.listar(p.bd, None, 3), proximos=eventos.proximos(p.bd, p.usuario.id, 3),
                  slides=eventos.proximos(p.bd, p.usuario.id, 5))


# --- Anuncios generales ----------------------------------------------------------------------
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
    notificaciones.crear_para_todos(p.bd, f"Nuevo anuncio general: {titulo}", "/anuncios", excepto=p.usuario.id)
    return Respuesta.redirigir("/anuncios").con_aviso("ok", "Anuncio publicado y notificado a todos los estudiantes.")


@ruta("POST", "/anuncios/<id>/eliminar")
@requiere_sesion
def eliminar_anuncio(p, id):
    anuncio = anuncios.por_id(p.bd, id)
    if not anuncio:
        raise ErrorHttp(404, "Ese anuncio no existe.")
    permitido = es_admin(p) or (anuncio.club_id and es_responsable_en(p, anuncio.club_id))
    if not permitido:
        raise ErrorHttp(403, "No tienes permiso para eliminar este anuncio.")
    anuncios.eliminar(p.bd, id)
    return Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), "/anuncios")).con_aviso("ok", "Anuncio eliminado.")


# --- Notificaciones ----------------------------------------------------------------------------
@ruta("GET", "/notificaciones")
@requiere_sesion
def ver_notificaciones(p):
    lista = notificaciones.listar(p.bd, p.usuario.id)
    notificaciones.marcar_leidas(p.bd, p.usuario.id)   # al abrir la bandeja quedan leídas
    return render(p, "notificaciones.html", lista=lista, n_notificaciones=0)


# --- Panel de gestión (líderes y capitanes) ----------------------------------------------------
@ruta("GET", "/gestion")
@requiere_sesion
def gestion(p):
    if not (modo_gestion(p) or es_admin(p)):
        raise ErrorHttp(403, "El panel de gestión es para líderes y capitanes.")
    return render(p, "gestion.html", a_cargo=clubes.clubes_a_cargo(p.bd, p.usuario.id))
