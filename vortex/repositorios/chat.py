"""Mensajes del chat de cada club."""


def enviar(bd, club_id, autor_id, contenido):
    return bd.execute("INSERT INTO mensajes_chat (club_id, autor_id, contenido) VALUES (?, ?, ?)",
                      (club_id, autor_id, contenido)).lastrowid


def ultimos(bd, club_id, cantidad=60):
    filas = bd.execute(
        """SELECT m.id, m.contenido, m.creado_en, m.autor_id, u.nombre AS autor_nombre, u.cif AS autor_cif
           FROM mensajes_chat m JOIN usuarios u ON u.id = m.autor_id
           WHERE m.club_id = ? ORDER BY m.id DESC LIMIT ?""", (club_id, cantidad)).fetchall()
    return list(reversed(filas))

