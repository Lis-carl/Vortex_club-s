"""Chats privados entre dos integrantes de un mismo club, sin JavaScript.

Funciona igual que el chat del club: un marco que se recarga solo cada 5 segundos muestra los
mensajes, y enviar es un formulario POST. Solo se puede escribir a alguien con quien se comparte al
menos un club activo; si dejan de compartirlo, la conversación anterior se puede leer pero no seguir.
"""
from .. import formularios as frm
from ..acceso import requiere_sesion, destino_seguro
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..plantillas import motor
from ..repositorios import privados, usuarios
from ..vistas import render


def _contacto(p, cif):
    """La otra persona de la conversación, si se puede ver."""
    otro = usuarios.por_cif(p.bd, cif)
    if not otro or not otro.activo or otro.id == p.usuario.id:
        raise ErrorHttp(404, "Esa persona no existe.")
    puede_escribir = privados.comparten_club(p.bd, p.usuario.id, otro.id)
    if not puede_escribir and not privados.hay_conversacion(p.bd, p.usuario.id, otro.id):
        raise ErrorHttp(403, "Solo puedes escribir a integrantes de tus clubes.")
    return otro, puede_escribir


@ruta("GET", "/mensajes")
@requiere_sesion
def bandeja(p):
    return render(p, "mensajes.html",
                  conversaciones=privados.conversaciones(p.bd, p.usuario.id),
                  contactos=privados.contactos(p.bd, p.usuario.id))


@ruta("GET", "/mensajes/<cif>")
@requiere_sesion
def conversacion(p, cif):
    otro, puede_escribir = _contacto(p, cif)
    return render(p, "mensaje_privado.html", otro=otro, puede_escribir=puede_escribir,
                  en_comun=privados.clubes_en_comun(p.bd, p.usuario.id, otro.id),
                  conversaciones=privados.conversaciones(p.bd, p.usuario.id))


@ruta("GET", "/mensajes/<cif>/marco")
@requiere_sesion
def marco(p, cif):
    """Contenido del marco; al verlo, los mensajes recibidos quedan leídos."""
    otro, _ = _contacto(p, cif)
    privados.marcar_leidos(p.bd, p.usuario.id, otro.id)
    lista = list(reversed(privados.ultimos(p.bd, p.usuario.id, otro.id)))
    return Respuesta.html(motor.renderizar("chat_marco.html", {"mensajes": lista, "usuario": p.usuario,
                                                                "editar_base": f"/mensajes/{cif}/"}))


@ruta("POST", "/mensajes/<cif>")
@requiere_sesion
def enviar(p, cif):
    otro, puede_escribir = _contacto(p, cif)
    volver = Respuesta.redirigir(destino_seguro(p.formulario.get("siguiente"), f"/mensajes/{cif}"))
    if not puede_escribir:
        return volver.con_aviso("error", "Ya no comparten ningún club, así que no puedes seguir esta conversación.")
    errores = frm.Errores()
    contenido = frm.texto(p.formulario, errores, "contenido", "El mensaje", 1, 1000)
    if errores:
        return volver.con_aviso("error", errores["contenido"])
    privados.enviar(p.bd, p.usuario.id, otro.id, contenido)
    if p.formulario.get("siguiente"):   # respuesta rápida desde el panel de chats
        return volver.con_aviso("ok", f"Mensaje enviado a {otro.nombre}.")
    return volver
