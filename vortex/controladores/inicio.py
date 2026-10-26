"""Inicio, anuncios generales, notificaciones y panel de gestión de líderes y capitanes."""
from datetime import datetime, timedelta

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
    mios = {c.id: c.rol for c in clubes.mis_clubes(p.bd, p.usuario.id)}
    roles = mios if modo_gestion(p) else {}
    for pub in publicaciones:
        pub["puede_eliminar"] = (pub.autor_id == p.usuario.id or es_admin(p)
                                 or roles.get(pub.club_id) in ("lider", "capitan"))
        # vista previa de comentarios desplegable en el feed
        pub["puede_comentar"] = pub.club_id in mios
        pub["vista_comentarios"] = foro.comentarios(p.bd, pub.id, p.usuario.id)[:3] if pub.n_comentarios else []
    return publicaciones


_PERIODOS = {"todo": None, "hoy": timedelta(days=1), "semana": timedelta(days=7), "mes": timedelta(days=30)}
_NOMBRES_PERIODO = {"todo": "Cualquier fecha", "hoy": "Hoy", "semana": "Última semana", "mes": "Último mes"}


@ruta("GET", "/")
@requiere_sesion
def feed(p):
    mis = clubes.mis_clubes(p.bd, p.usuario.id)
    tiene_clubes = bool(mis)
    ver = p.consulta.get("ver") if p.consulta.get("ver") in ("mis", "todos", "agenda") else ("mis" if tiene_clubes else "todos")
    orden = "nuevos" if p.consulta.get("orden") == "nuevos" else "populares"   # por omisión, las más votadas arriba
    pagina = int(p.consulta["pagina"]) if (p.consulta.get("pagina") or "").isdigit() else 1
    # Filtros del ícono de embudo: club, fecha y orden
    opciones_club = [c for c in clubes.todos(p.bd) if c.estado == "activo"]
    club_filtro = next((c for c in opciones_club if c.slug == p.consulta.get("club")), None)
    fecha = p.consulta.get("fecha") if p.consulta.get("fecha") in _PERIODOS else "todo"
    desde = (datetime.now() - _PERIODOS[fecha]).strftime("%Y-%m-%d %H:%M:%S") if _PERIODOS[fecha] else None
    if fecha == "hoy":
        desde = datetime.now().strftime("%Y-%m-%d 00:00:00")
    # Se preparan las dos listas («Mis clubes» y «Toda la UAM») para cambiar de pestaña sin recargar.
    # «Agenda» (celular) muestra eventos y anuncios en lugar del feed.
    listas = {}
    for clave in ("mis", "todos"):
        pubs = [] if ver == "agenda" else foro.listar(
            p.bd, p.usuario.id, solo_mis_clubes=(clave == "mis"), club_id=club_filtro.id if club_filtro else None,
            orden=orden, limite=21, pagina=pagina, desde=desde)
        listas[clave] = (marcar_permisos(p, pubs[:20]), len(pubs) > 20)
    avisar_eventos_proximos(p)
    return render(p, "inicio.html", publicaciones_mis=listas["mis"][0], hay_mas_mis=listas["mis"][1],
                  publicaciones_todos=listas["todos"][0], hay_mas_todos=listas["todos"][1],
                  ver=ver, orden=orden, pagina=pagina,
                  opciones_club=opciones_club, club_filtro=club_filtro, fecha=fecha, nombres_periodo=_NOMBRES_PERIODO,
                  n_filtros=(1 if club_filtro else 0) + (fecha != "todo") + (orden != "populares"),
                  tiene_clubes=tiene_clubes,
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
@ruta("POST", "/notificaciones/limpiar")
@requiere_sesion
def limpiar_notificaciones(p):
    """Botón de papelera del panel: las quita del panel flotante (siguen en la página de Notificaciones)."""
    notificaciones.quitar_todas(p.bd, p.usuario.id)
    return Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), "/")).con_aviso("ok", "Notificaciones quitadas del panel. Siguen en Notificaciones.")


@ruta("POST", "/notificaciones/<id>/quitar")
@requiere_sesion
def quitar_notificacion(p, id):
    notificaciones.quitar(p.bd, p.usuario.id, id)
    return Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), "/"))


@ruta("POST", "/notificaciones/leidas")
@requiere_sesion
def marcar_notificaciones_leidas(p):
    """Botón del panel de la campana: deja todas las notificaciones como leídas."""
    notificaciones.marcar_leidas(p.bd, p.usuario.id)
    return Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), "/"))


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
