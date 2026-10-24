"""Propuestas de evento, eventos aprobados, asistencias y recordatorios."""
from datetime import datetime, timedelta

from ..utilidades import ahora_iso


def _ahora():
    return ahora_iso()[:16]   # 'AAAA-MM-DD HH:MM', mismo formato que fecha_inicio


# Eventos aprobados con el conteo de asistentes y si el usuario confirmó.
_EVENTOS = """
SELECT e.*,
       (SELECT COUNT(*) FROM asistencias a WHERE a.evento_id = e.id) AS n_asistentes,
       (SELECT 1 FROM asistencias a WHERE a.evento_id = e.id AND a.usuario_id = :uid) AS mi_asistencia,
       COALESCE((SELECT SUM(v.valor) FROM votos_propuesta v WHERE v.propuesta_id = e.id), 0) AS puntaje,
       (SELECT v.valor FROM votos_propuesta v WHERE v.propuesta_id = e.id AND v.usuario_id = :uid) AS mi_voto,
       (SELECT p.proponente_id FROM propuestas_evento p WHERE p.id = e.id) AS proponente_id
FROM v_eventos e
"""


def proponer(bd, club_id, proponente_id, titulo, descripcion, fecha_inicio, lugar, cupo, recursos):
    return bd.execute(
        """INSERT INTO propuestas_evento (club_id, proponente_id, titulo, descripcion, fecha_inicio, lugar, cupo, recursos)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (club_id, proponente_id, titulo, descripcion, fecha_inicio, lugar, cupo, recursos)).lastrowid


def por_id(bd, propuesta_id):
    return bd.execute("SELECT * FROM propuestas_evento WHERE id = ?", (propuesta_id,)).fetchone()


def umbral_votacion(bd, club_id):
    """Apoyos necesarios para aprobar una propuesta por votación: la mitad de los miembros activos (mínimo 2)."""
    n = bd.execute("SELECT COUNT(*) AS n FROM membresias WHERE club_id = ? AND estado = 'activa'", (club_id,)).fetchone().n
    return max(2, -(-n // 2))


def pendientes(bd, club_id, usuario_id=None):
    filas = bd.execute(
        """SELECT e.*, u.nombre AS proponente_nombre, u.cif AS proponente_cif,
                  (SELECT COUNT(*) FROM votos_propuesta v WHERE v.propuesta_id = e.id AND v.valor = 1) AS apoyos,
                  (SELECT COUNT(*) FROM votos_propuesta v WHERE v.propuesta_id = e.id AND v.valor = -1) AS contras,
                  (SELECT v.valor FROM votos_propuesta v WHERE v.propuesta_id = e.id AND v.usuario_id = ?) AS mi_voto
           FROM propuestas_evento e JOIN usuarios u ON u.id = e.proponente_id
           WHERE e.club_id = ? AND e.estado = 'pendiente' ORDER BY e.fecha_inicio""", (usuario_id, club_id)).fetchall()
    umbral = umbral_votacion(bd, club_id)
    for f in filas:
        f["umbral"] = umbral
        f["avance"] = min(100, f.apoyos * 100 // umbral)
    return filas


def votar_propuesta(bd, usuario_id, propuesta_id, valor):
    """Alterna el voto (+1 apoyo / -1 en contra). Devuelve (apoyos, contras)."""
    actual = bd.execute("SELECT valor FROM votos_propuesta WHERE usuario_id = ? AND propuesta_id = ?",
                        (usuario_id, propuesta_id)).fetchone()
    if actual and actual.valor == valor:
        bd.execute("DELETE FROM votos_propuesta WHERE usuario_id = ? AND propuesta_id = ?", (usuario_id, propuesta_id))
    elif actual:
        bd.execute("UPDATE votos_propuesta SET valor = ? WHERE usuario_id = ? AND propuesta_id = ?",
                   (valor, usuario_id, propuesta_id))
    else:
        bd.execute("INSERT INTO votos_propuesta (usuario_id, propuesta_id, valor) VALUES (?, ?, ?)",
                   (usuario_id, propuesta_id, valor))
    fila = bd.execute("""SELECT COALESCE(SUM(valor = 1), 0) AS apoyos, COALESCE(SUM(valor = -1), 0) AS contras
                         FROM votos_propuesta WHERE propuesta_id = ?""", (propuesta_id,)).fetchone()
    return fila.apoyos, fila.contras


def contar_pendientes(bd, club_id):
    return bd.execute("SELECT COUNT(*) AS n FROM propuestas_evento WHERE club_id = ? AND estado = 'pendiente'",
                      (club_id,)).fetchone().n


def mias(bd, club_id, usuario_id):
    return bd.execute(
        "SELECT * FROM propuestas_evento WHERE club_id = ? AND proponente_id = ? ORDER BY id DESC",
        (club_id, usuario_id)).fetchall()


def del_club(bd, club_id, usuario_id):
    """Devuelve (proximos, pasados) del club."""
    p = {"uid": usuario_id, "club": club_id, "ahora": _ahora()}
    proximos = bd.execute(_EVENTOS + " WHERE e.club_id = :club AND e.fecha_inicio >= :ahora ORDER BY e.fecha_inicio",
                          p).fetchall()
    pasados = bd.execute(_EVENTOS + " WHERE e.club_id = :club AND e.fecha_inicio < :ahora "
                         "ORDER BY e.fecha_inicio DESC LIMIT 10", p).fetchall()
    return proximos, pasados


# Posición de los eventos de todos los clubes: primero los más votados; a igual puntaje, los que tienen
# más asistentes confirmados; después, el más cercano.
_ORDEN_VOTOS = " ORDER BY puntaje DESC, n_asistentes DESC, e.fecha_inicio"


def proximos(bd, usuario_id, limite=50, orden="fecha"):
    sql = _EVENTOS + " WHERE e.fecha_inicio >= :ahora"
    sql += _ORDEN_VOTOS if orden == "votos" else " ORDER BY e.fecha_inicio"
    return bd.execute(sql + " LIMIT :limite", {"uid": usuario_id, "ahora": _ahora(), "limite": limite}).fetchall()


def destacados(bd, usuario_id, limite=3):
    """Próximos eventos con más votos a favor (solo los que tienen puntaje positivo)."""
    return [e for e in proximos(bd, usuario_id, limite, orden="votos") if e.puntaje > 0]


def del_mes(bd, usuario_id, anio, mes, solo_mios=False, orden="fecha"):
    """Eventos aprobados de un mes. solo_mios: de mis clubes o a los que confirmé asistencia."""
    sql = _EVENTOS + " WHERE e.fecha_inicio LIKE :prefijo"
    if solo_mios:
        sql += (" AND (e.club_id IN (SELECT club_id FROM membresias WHERE usuario_id = :uid AND estado = 'activa')"
                " OR e.id IN (SELECT evento_id FROM asistencias WHERE usuario_id = :uid))")
    sql += _ORDEN_VOTOS if orden == "votos" else " ORDER BY e.fecha_inicio"
    return bd.execute(sql, {"uid": usuario_id, "prefijo": f"{anio:04d}-{mes:02d}-%"}).fetchall()


def evento(bd, evento_id, usuario_id):
    return bd.execute(_EVENTOS + " WHERE e.id = :id", {"uid": usuario_id, "id": evento_id}).fetchone()


def alternar_asistencia(bd, usuario_id, evento_id):
    """Confirma o cancela la asistencia. Devuelve True si quedó confirmada. Lanza ValueError si no hay cupo."""
    e = evento(bd, evento_id, usuario_id)
    if e.mi_asistencia:
        bd.execute("DELETE FROM asistencias WHERE usuario_id = ? AND evento_id = ?", (usuario_id, evento_id))
        return False
    if e.cupo and e.n_asistentes >= e.cupo:
        raise ValueError("El evento ya alcanzó su cupo.")
    bd.execute("INSERT INTO asistencias (usuario_id, evento_id) VALUES (?, ?)", (usuario_id, evento_id))
    return True


def asistentes(bd, evento_id):
    return bd.execute(
        """SELECT u.nombre, u.cif, a.creado_en FROM asistencias a JOIN usuarios u ON u.id = a.usuario_id
           WHERE a.evento_id = ? ORDER BY u.nombre""", (evento_id,)).fetchall()


def recordatorios(bd, usuario_id, horas=48):
    """Eventos confirmados por el usuario que empiezan en las próximas `horas`."""
    hasta = (datetime.now() + timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M")
    return bd.execute(_EVENTOS + " WHERE e.fecha_inicio >= :ahora AND e.fecha_inicio <= :hasta"
                      " AND e.id IN (SELECT evento_id FROM asistencias WHERE usuario_id = :uid) ORDER BY e.fecha_inicio",
                      {"uid": usuario_id, "ahora": _ahora(), "hasta": hasta}).fetchall()


def revisar(bd, propuesta_id, revisor_id, aprobar, comentario):
    bd.execute(
        """UPDATE propuestas_evento SET estado = ?, revisado_por = ?, comentario_revision = ?, revisado_en = ?
           WHERE id = ? AND estado = 'pendiente'""",
        ("aprobada" if aprobar else "rechazada", revisor_id, comentario, ahora_iso(), propuesta_id))
