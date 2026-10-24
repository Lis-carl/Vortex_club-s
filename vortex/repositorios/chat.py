"""Mensajes del chat de cada club."""


def enviar(bd, club_id, autor_id, contenido):
    return bd.execute("INSERT INTO mensajes_chat (club_id, autor_id, contenido) VALUES (?, ?, ?)",
                      (club_id, autor_id, contenido)).lastrowid


def mensaje(bd, mensaje_id):
    return bd.execute("SELECT * FROM mensajes_chat WHERE id = ?", (mensaje_id,)).fetchone()


def editar(bd, mensaje_id, contenido):
    bd.execute("UPDATE mensajes_chat SET contenido = ?, editado_en = datetime('now', 'localtime') WHERE id = ?", (contenido, mensaje_id))


def resumen_de_mis_clubes(bd, usuario_id):
    """Clubes activos del usuario con el último mensaje de su chat (para el panel de chats)."""
    return bd.execute(
        """SELECT c.nombre, c.slug, c.foto, m.contenido AS ultimo, m.creado_en AS ultimo_en, u.nombre AS ultimo_autor
           FROM membresias me JOIN clubes c ON c.id = me.club_id
           LEFT JOIN mensajes_chat m ON m.id = (SELECT MAX(id) FROM mensajes_chat WHERE club_id = c.id)
           LEFT JOIN usuarios u ON u.id = m.autor_id
           WHERE me.usuario_id = ? AND me.estado = 'activa' AND c.estado = 'activo'
           ORDER BY COALESCE(m.id, 0) DESC, c.nombre""", (usuario_id,)).fetchall()


def ultimos(bd, club_id, cantidad=60):
    filas = bd.execute(
        """SELECT m.id, m.contenido, m.creado_en, m.editado_en, m.autor_id, u.nombre AS autor_nombre, u.cif AS autor_cif
           FROM mensajes_chat m JOIN usuarios u ON u.id = m.autor_id
           WHERE m.club_id = ? ORDER BY m.id DESC LIMIT ?""", (club_id, cantidad)).fetchall()
    return list(reversed(filas))

