"""Propuestas de evento y eventos aprobados."""
from ..utilidades import ahora_iso


def _ahora():
    return ahora_iso()[:16]   # 'AAAA-MM-DD HH:MM', mismo formato que fecha_inicio


def proponer(bd, club_id, proponente_id, titulo, descripcion, fecha_inicio, lugar, cupo, recursos):
    return bd.execute(
        """INSERT INTO propuestas_evento (club_id, proponente_id, titulo, descripcion, fecha_inicio, lugar, cupo, recursos)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (club_id, proponente_id, titulo, descripcion, fecha_inicio, lugar, cupo, recursos)).lastrowid


def por_id(bd, propuesta_id):
    return bd.execute("SELECT * FROM propuestas_evento WHERE id = ?", (propuesta_id,)).fetchone()


def pendientes(bd, club_id):
    return bd.execute(
        """SELECT e.*, u.nombre AS proponente_nombre, u.cif AS proponente_cif
           FROM propuestas_evento e JOIN usuarios u ON u.id = e.proponente_id
           WHERE e.club_id = ? AND e.estado = 'pendiente' ORDER BY e.fecha_inicio""", (club_id,)).fetchall()


def contar_pendientes(bd, club_id):
    return bd.execute("SELECT COUNT(*) AS n FROM propuestas_evento WHERE club_id = ? AND estado = 'pendiente'",
                      (club_id,)).fetchone().n


def mias(bd, club_id, usuario_id):
    return bd.execute(
        "SELECT * FROM propuestas_evento WHERE club_id = ? AND proponente_id = ? ORDER BY id DESC",
        (club_id, usuario_id)).fetchall()


def del_club(bd, club_id):
    """Devuelve (proximos, pasados) del club."""
    ahora = _ahora()
    proximos = bd.execute("SELECT * FROM v_eventos WHERE club_id = ? AND fecha_inicio >= ? ORDER BY fecha_inicio",
                          (club_id, ahora)).fetchall()
    pasados = bd.execute("SELECT * FROM v_eventos WHERE club_id = ? AND fecha_inicio < ? "
                         "ORDER BY fecha_inicio DESC LIMIT 10", (club_id, ahora)).fetchall()
    return proximos, pasados


def proximos(bd, limite=50):
    return bd.execute("SELECT * FROM v_eventos WHERE fecha_inicio >= ? ORDER BY fecha_inicio LIMIT ?",
                      (_ahora(), limite)).fetchall()


def revisar(bd, propuesta_id, revisor_id, aprobar, comentario):
    bd.execute(
        """UPDATE propuestas_evento SET estado = ?, revisado_por = ?, comentario_revision = ?, revisado_en = ?
           WHERE id = ? AND estado = 'pendiente'""",
        ("aprobada" if aprobar else "rechazada", revisor_id, comentario, ahora_iso(), propuesta_id))
