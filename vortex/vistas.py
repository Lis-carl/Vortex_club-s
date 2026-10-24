"""Ayudantes para generar respuestas HTML a partir de plantillas."""
from .nucleo import Fila, Respuesta
from .plantillas import motor
from .acceso import es_admin, ROLES_ACCESO
from .repositorios import (clubes as repo_clubes, eventos as repo_eventos, notificaciones as repo_notificaciones,
                           privados as repo_privados)
from .utilidades import fecha_larga


def avisar_eventos_proximos(p):
    """Los eventos confirmados de las próximas 48 horas quedan como recordatorio en Notificaciones."""
    if p.usuario and p.bd:
        repo_notificaciones.recordar_eventos(p.bd, p.usuario.id, repo_eventos.recordatorios(p.bd, p.usuario.id), fecha_larga)


def render(p, nombre, estado=200, **contexto):
    avisar_eventos_proximos(p)
    base = {
        "usuario": p.usuario,
        "es_admin": es_admin(p),
        "rol_acceso": p.usuario.rol_acceso if p.usuario else None,
        "rol_acceso_nombre": ROLES_ACCESO.get(p.usuario.rol_acceso) if p.usuario else None,
        "n_notificaciones": repo_notificaciones.no_leidas(p.bd, p.usuario.id) if p.usuario and p.bd else 0,
        "n_mensajes": repo_privados.no_leidos(p.bd, p.usuario.id) if p.usuario and p.bd else 0,
        "csrf": p.token_csrf(),
        "aviso": p.aviso,
        "ruta": p.ruta,
        "ruta_completa": p.ruta_completa,
        "mis_clubes": repo_clubes.mis_clubes(p.bd, p.usuario.id) if p.usuario and p.bd else [],
    }
    base.update(contexto)
    if isinstance(base.get("valores"), dict):   # permite valores.campo en las plantillas
        base["valores"] = Fila(base["valores"])
    respuesta = Respuesta.html(motor.renderizar(nombre, base), estado)
    if p.aviso:
        respuesta.borrar_cookie("aviso")
    if p.csrf_nuevo:
        respuesta.cookie("csrf_anon", p.csrf_nuevo, max_age=60 * 60 * 24 * 30)
    return respuesta


def error(p, estado, mensaje):
    titulos = {403: "Acceso denegado", 404: "No encontrado", 405: "No permitido", 413: "Demasiado grande"}
    return render(p, "error.html", estado, codigo=estado,
                  titulo=titulos.get(estado, "Algo salió mal"), mensaje=mensaje)
