"""Mensajes privados entre dos personas que comparten al menos un club."""


def comparten_club(bd, a, b):
    return bd.execute(
        """SELECT 1 FROM membresias m1
           JOIN membresias m2 ON m2.club_id = m1.club_id
           JOIN clubes c ON c.id = m1.club_id
           WHERE m1.usuario_id = ? AND m2.usuario_id = ? AND m1.estado = 'activa' AND m2.estado = 'activa'
             AND c.estado = 'activo' LIMIT 1""", (a, b)).fetchone() is not None


def clubes_en_comun(bd, a, b):
    return bd.execute(
        """SELECT c.nombre, c.slug FROM membresias m1
           JOIN membresias m2 ON m2.club_id = m1.club_id
           JOIN clubes c ON c.id = m1.club_id
           WHERE m1.usuario_id = ? AND m2.usuario_id = ? AND m1.estado = 'activa' AND m2.estado = 'activa'
             AND c.estado = 'activo' ORDER BY c.nombre""", (a, b)).fetchall()


def contactos(bd, usuario_id):
    """Personas con las que se puede abrir un chat: integrantes activos de mis clubes."""
    return bd.execute(
        """SELECT u.id, u.cif, u.nombre, u.foto, group_concat(c.nombre, ' · ') AS clubes
           FROM membresias yo
           JOIN membresias otro ON otro.club_id = yo.club_id AND otro.usuario_id <> yo.usuario_id
           JOIN clubes c ON c.id = yo.club_id
           JOIN usuarios u ON u.id = otro.usuario_id
           WHERE yo.usuario_id = ? AND yo.estado = 'activa' AND otro.estado = 'activa'
             AND c.estado = 'activo' AND u.activo = 1
           GROUP BY u.id ORDER BY u.nombre""", (usuario_id,)).fetchall()


def conversaciones(bd, usuario_id):
    """Una fila por persona con la que hay mensajes: el último mensaje y cuántos faltan por leer."""
    return bd.execute(
        """SELECT u.id, u.cif, u.nombre, u.foto, m.contenido AS ultimo, m.creado_en, m.emisor_id,
                  (SELECT COUNT(*) FROM mensajes_privados x
                   WHERE x.emisor_id = u.id AND x.receptor_id = ? AND x.leido = 0) AS sin_leer
           FROM (SELECT CASE WHEN emisor_id = ? THEN receptor_id ELSE emisor_id END AS otro, MAX(id) AS ultimo_id
                 FROM mensajes_privados WHERE ? IN (emisor_id, receptor_id) GROUP BY otro) c
           JOIN mensajes_privados m ON m.id = c.ultimo_id
           JOIN usuarios u ON u.id = c.otro
           ORDER BY m.id DESC""", (usuario_id, usuario_id, usuario_id)).fetchall()


def hay_conversacion(bd, a, b):
    return bd.execute(
        """SELECT 1 FROM mensajes_privados
           WHERE (emisor_id = ? AND receptor_id = ?) OR (emisor_id = ? AND receptor_id = ?) LIMIT 1""",
        (a, b, b, a)).fetchone() is not None


def enviar(bd, emisor_id, receptor_id, contenido):
    return bd.execute("INSERT INTO mensajes_privados (emisor_id, receptor_id, contenido) VALUES (?, ?, ?)",
                      (emisor_id, receptor_id, contenido)).lastrowid


def ultimos(bd, a, b, cantidad=60):
    """Mismas columnas que el chat del club, para reutilizar su marco."""
    filas = bd.execute(
        """SELECT m.id, m.contenido, m.creado_en, m.emisor_id AS autor_id, u.nombre AS autor_nombre
           FROM mensajes_privados m JOIN usuarios u ON u.id = m.emisor_id
           WHERE (m.emisor_id = ? AND m.receptor_id = ?) OR (m.emisor_id = ? AND m.receptor_id = ?)
           ORDER BY m.id DESC LIMIT ?""", (a, b, b, a, cantidad)).fetchall()
    return list(reversed(filas))


def marcar_leidos(bd, receptor_id, emisor_id):
    bd.execute("UPDATE mensajes_privados SET leido = 1 WHERE receptor_id = ? AND emisor_id = ? AND leido = 0",
               (receptor_id, emisor_id))


def no_leidos(bd, usuario_id):
    return bd.execute("SELECT COUNT(*) AS n FROM mensajes_privados WHERE receptor_id = ? AND leido = 0",
                      (usuario_id,)).fetchone().n
