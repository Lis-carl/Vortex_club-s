"""Mensajes del chat de cada club."""


def enviar(bd, club_id, autor_id, contenido):
    return bd.execute("INSERT INTO mensajes_chat (club_id, autor_id, contenido) VALUES (?, ?, ?)",
                      (club_id, autor_id, contenido)).lastrowid


def mensaje(bd, mensaje_id):
    return bd.execute("SELECT * FROM mensajes_chat WHERE id = ?", (mensaje_id,)).fetchone()


def editar(bd, mensaje_id, contenido):
    bd.execute("UPDATE mensajes_chat SET contenido = ?, editado_en = datetime('now', 'localtime') WHERE id = ?", (contenido, mensaje_id))


def ultimos(bd, club_id, cantidad=60):
    filas = bd.execute(
        """SELECT m.id, m.contenido, m.creado_en, m.editado_en, m.autor_id, u.nombre AS autor_nombre, u.cif AS autor_cif
           FROM mensajes_chat m JOIN usuarios u ON u.id = m.autor_id
           WHERE m.club_id = ? ORDER BY m.id DESC LIMIT ?""", (club_id, cantidad)).fetchall()
    return list(reversed(filas))

