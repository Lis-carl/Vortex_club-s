"""Puntos de participación e insignias (sugerencia de la encuesta: «algo que incentive el uso»).

Puntos: publicación 5 · comentario 2 · asistencia confirmada 3 · reacción recibida de otra persona 1.
"""
from ..nucleo import Fila

INSIGNIAS = [(60, "Destacado"), (30, "Activo"), (10, "Participante"), (0, "Nuevo")]

_PUNTOS = """
    5 * (SELECT COUNT(*) FROM publicaciones p WHERE p.autor_id = u.id AND p.eliminado = 0)
  + 2 * (SELECT COUNT(*) FROM comentarios c WHERE c.autor_id = u.id AND c.eliminado = 0)
  + 3 * (SELECT COUNT(*) FROM asistencias a WHERE a.usuario_id = u.id)
  + (SELECT COUNT(*) FROM reacciones r JOIN publicaciones p ON p.id = r.publicacion_id
       WHERE p.autor_id = u.id AND r.usuario_id <> u.id AND p.eliminado = 0)"""


def insignia(puntos):
    return next(nombre for minimo, nombre in INSIGNIAS if puntos >= minimo)


def de_usuario(bd, usuario_id):
    puntos = bd.execute(f"SELECT {_PUNTOS} AS n FROM usuarios u WHERE u.id = ?", (usuario_id,)).fetchone().n
    siguiente = min((m for m, _ in INSIGNIAS if m > puntos), default=None)
    return Fila(puntos=puntos, insignia=insignia(puntos), siguiente=siguiente,
                faltan=(siguiente - puntos) if siguiente is not None else 0)

