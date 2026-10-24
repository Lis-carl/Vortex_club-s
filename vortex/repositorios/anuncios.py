"""Anuncios generales (club_id NULL) y anuncios por club."""


def crear(bd, club_id, autor_id, titulo, contenido, fijado):
    bd.execute("INSERT INTO anuncios (club_id, autor_id, titulo, contenido, fijado) VALUES (?, ?, ?, ?, ?)",
               (club_id, autor_id, titulo, contenido, 1 if fijado else 0))


def listar(bd, club_id=None, limite=50):
    """club_id=None devuelve los anuncios generales."""
    filtro = "a.club_id IS NULL" if club_id is None else "a.club_id = :club"
    return bd.execute(
        f"""SELECT a.*, u.nombre AS autor_nombre, u.cif AS autor_cif, c.nombre AS club_nombre, c.slug AS club_slug
            FROM anuncios a JOIN usuarios u ON u.id = a.autor_id LEFT JOIN clubes c ON c.id = a.club_id
            WHERE {filtro} ORDER BY a.fijado DESC, a.id DESC LIMIT :limite""",
        {"club": club_id, "limite": limite}).fetchall()


def por_id(bd, anuncio_id):
    return bd.execute("SELECT * FROM anuncios WHERE id = ?", (anuncio_id,)).fetchone()


def editar(bd, anuncio_id, titulo, contenido):
    bd.execute("UPDATE anuncios SET titulo = ?, contenido = ?, editado_en = datetime('now', 'localtime') WHERE id = ?",
               (titulo, contenido, anuncio_id))


def eliminar(bd, anuncio_id):
    bd.execute("DELETE FROM anuncios WHERE id = ?", (anuncio_id,))
