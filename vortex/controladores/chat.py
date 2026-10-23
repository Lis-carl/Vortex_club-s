"""Chat por club (consulta periódica desde el navegador)."""
from .. import formularios as frm
from ..acceso import requiere_sesion, club_o_404, contexto_club, exigir_miembro
from ..enrutador import ruta
from ..nucleo import Respuesta
from ..repositorios import chat
from ..utilidades import hora
from ..vistas import render


def _a_json(mensaje, usuario_id):
    return {"id": mensaje.id, "autor": mensaje.autor_nombre, "cif": mensaje.autor_cif,
            "contenido": mensaje.contenido, "hora": hora(mensaje.creado_en), "mio": mensaje.autor_id == usuario_id}


@ruta("GET", "/clubes/<slug>/chat")
@requiere_sesion
def sala(p, slug):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    mensajes = chat.ultimos(p.bd, club.id)
    return render(p, "club_chat.html", mensajes=mensajes, ultimo_id=mensajes[-1].id if mensajes else 0,
                  **contexto_club(p, club, "chat"))


@ruta("GET", "/clubes/<slug>/chat/mensajes")
@requiere_sesion
def mensajes(p, slug):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    desde = int(p.consulta["desde"]) if (p.consulta.get("desde") or "").isdigit() else 0
    return Respuesta.json([_a_json(m, p.usuario.id) for m in chat.desde(p.bd, club.id, desde)])


@ruta("POST", "/clubes/<slug>/chat")
@requiere_sesion
def enviar(p, slug):
    club = club_o_404(p, slug)
    exigir_miembro(p, club)
    errores = frm.Errores()
    contenido = frm.texto(p.formulario, errores, "contenido", "El mensaje", 1, 1000)
    if errores:
        if p.es_ajax:
            return Respuesta.json({"ok": False, "error": errores["contenido"]}, 400)
        return Respuesta.redirigir(f"/clubes/{slug}/chat").con_aviso("error", errores["contenido"])
    chat.enviar(p.bd, club.id, p.usuario.id, contenido)
    if p.es_ajax:
        return Respuesta.json({"ok": True})
    return Respuesta.redirigir(f"/clubes/{slug}/chat")
