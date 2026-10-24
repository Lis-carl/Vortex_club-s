"""Chat por club, sin JavaScript.

La página del chat incrusta un marco (iframe) con los mensajes; ese marco se recarga solo cada
5 segundos con <meta http-equiv="refresh">, así los mensajes nuevos aparecen sin escribir código
en el navegador. Enviar un mensaje es un formulario POST normal.
"""
from .. import formularios as frm
from ..acceso import requiere_sesion, club_o_404, contexto_club, exigir_miembro
from ..enrutador import ruta
from ..nucleo import Respuesta
from ..plantillas import motor
from ..repositorios import chat
from ..vistas import render


@ruta("GET", "/clubes/<slug>/chat")
@requiere_sesion
def sala(p, slug):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    return render(p, "club_chat.html", **contexto_club(p, club, "chat"))


@ruta("GET", "/clubes/<slug>/chat/mensajes")
@requiere_sesion
def mensajes(p, slug):
    """Contenido del marco: últimos mensajes, del más nuevo al más antiguo."""
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    lista = list(reversed(chat.ultimos(p.bd, club.id)))
    return Respuesta.html(motor.renderizar("chat_marco.html", {"mensajes": lista, "usuario": p.usuario,
                                                                "editar_base": f"/clubes/{slug}/chat/"}))


@ruta("POST", "/clubes/<slug>/chat")
@requiere_sesion
def enviar(p, slug):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    errores = frm.Errores()
    contenido = frm.texto(p.formulario, errores, "contenido", "El mensaje", 1, 1000)
    volver = Respuesta.redirigir(f"/clubes/{slug}/chat")
    if errores:
        return volver.con_aviso("error", errores["contenido"])
    chat.enviar(p.bd, club.id, p.usuario.id, contenido)
    return volver
