"""Ayudantes para generar respuestas HTML a partir de plantillas."""
from .nucleo import Fila, Respuesta
from .plantillas import motor
from .repositorios import clubes as repo_clubes


def render(p, nombre, estado=200, **contexto):
    base = {
        "usuario": p.usuario,
        "es_admin": bool(p.usuario and p.usuario.rol_global == "admin"),
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
