"""Clubes, categorías, membresías y solicitudes de creación de club."""
from ..utilidades import slugify, ahora_iso

_ORDEN_ROL = "CASE m.rol WHEN 'lider' THEN 0 WHEN 'capitan' THEN 1 ELSE 2 END"


# --- Clubes ----------------------------------------------------------------------------------
def categorias(bd):
    return bd.execute("SELECT id, nombre FROM categorias ORDER BY nombre").fetchall()


def categoria_existe(bd, categoria_id):
    return bd.execute("SELECT 1 FROM categorias WHERE id = ?", (categoria_id,)).fetchone() is not None


def catalogo(bd, usuario_id, texto="", categoria_id=None):
    sql = """
        SELECT c.*, cat.nombre AS categoria,
          (SELECT COUNT(*) FROM membresias m WHERE m.club_id = c.id AND m.estado = 'activa') AS n_miembros,
          (SELECT m.rol FROM membresias m WHERE m.club_id = c.id AND m.usuario_id = :uid
             AND m.estado = 'activa') AS mi_rol,
          (SELECT 1 FROM membresias m WHERE m.club_id = c.id AND m.usuario_id = :uid
             AND m.estado = 'pendiente') AS mi_pendiente
        FROM clubes c JOIN categorias cat ON cat.id = c.categoria_id
        WHERE c.estado = 'activo'"""
    params = {"uid": usuario_id}
    if texto:
        sql += r" AND (c.nombre LIKE :q ESCAPE '\' OR c.descripcion LIKE :q ESCAPE '\')"
        escapado = texto.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        params["q"] = f"%{escapado}%"
    if categoria_id:
        sql += " AND c.categoria_id = :cat"
        params["cat"] = categoria_id
    sql += " ORDER BY n_miembros DESC, c.nombre"
    return bd.execute(sql, params).fetchall()


def por_slug(bd, slug):
    return bd.execute(
        """SELECT c.*, cat.nombre AS categoria,
             (SELECT COUNT(*) FROM membresias m WHERE m.club_id = c.id AND m.estado = 'activa') AS n_miembros
           FROM clubes c JOIN categorias cat ON cat.id = c.categoria_id WHERE c.slug = ?""",
        (slug,)).fetchone()


def por_id_simple(bd, club_id):
    return bd.execute("SELECT * FROM clubes WHERE id = ?", (club_id,)).fetchone()


def lider(bd, club_id):
    return bd.execute(
        """SELECT u.id, u.cif, u.nombre FROM membresias m JOIN usuarios u ON u.id = m.usuario_id
           WHERE m.club_id = ? AND m.rol = 'lider'""", (club_id,)).fetchone()


def slug_libre(bd, nombre):
    base = slugify(nombre)
    slug, n = base, 2
    while bd.execute("SELECT 1 FROM clubes WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base}-{n}"
        n += 1
    return slug


def nombre_ocupado(bd, nombre):
    en_clubes = bd.execute("SELECT 1 FROM clubes WHERE nombre = ?", (nombre,)).fetchone()
    en_solicitudes = bd.execute(
        "SELECT 1 FROM solicitudes_club WHERE nombre = ? COLLATE NOCASE AND estado = 'pendiente'",
        (nombre,)).fetchone()
    return bool(en_clubes or en_solicitudes)


def crear(bd, nombre, descripcion, categoria_id, requiere_aprobacion):
    cur = bd.execute(
        "INSERT INTO clubes (nombre, slug, descripcion, categoria_id, requiere_aprobacion) VALUES (?, ?, ?, ?, ?)",
        (nombre, slug_libre(bd, nombre), descripcion, categoria_id, 1 if requiere_aprobacion else 0))
    return cur.lastrowid


def actualizar(bd, club_id, descripcion, categoria_id, requiere_aprobacion):
    bd.execute("UPDATE clubes SET descripcion = ?, categoria_id = ?, requiere_aprobacion = ? WHERE id = ?",
               (descripcion, categoria_id, 1 if requiere_aprobacion else 0, club_id))


def cambiar_estado(bd, club_id, estado):
    bd.execute("UPDATE clubes SET estado = ? WHERE id = ?", (estado, club_id))


def todos(bd):
    return bd.execute(
        """SELECT c.id, c.nombre, c.slug, c.estado,
             (SELECT COUNT(*) FROM membresias m WHERE m.club_id = c.id AND m.estado = 'activa') AS n_miembros,
             (SELECT u.nombre FROM membresias m JOIN usuarios u ON u.id = m.usuario_id
                WHERE m.club_id = c.id AND m.rol = 'lider') AS lider_nombre
           FROM clubes c ORDER BY c.nombre""").fetchall()


# --- Membresías ------------------------------------------------------------------------------
def membresia(bd, usuario_id, club_id):
    return bd.execute("SELECT * FROM membresias WHERE usuario_id = ? AND club_id = ?",
                      (usuario_id, club_id)).fetchone()


def membresia_por_id(bd, membresia_id):
    return bd.execute("SELECT * FROM membresias WHERE id = ?", (membresia_id,)).fetchone()


def mis_clubes(bd, usuario_id):
    return bd.execute(
        """SELECT c.id, c.nombre, c.slug, m.rol FROM membresias m JOIN clubes c ON c.id = m.club_id
           WHERE m.usuario_id = ? AND m.estado = 'activa' AND c.estado = 'activo' ORDER BY c.nombre""",
        (usuario_id,)).fetchall()


def integrantes(bd, club_id):
    return bd.execute(
        f"""SELECT m.id AS membresia_id, m.rol, m.unido_en, u.id AS usuario_id, u.cif, u.nombre, u.carrera
            FROM membresias m JOIN usuarios u ON u.id = m.usuario_id
            WHERE m.club_id = ? AND m.estado = 'activa' ORDER BY {_ORDEN_ROL}, u.nombre""",
        (club_id,)).fetchall()


def pendientes(bd, club_id):
    return bd.execute(
        """SELECT m.id AS membresia_id, m.unido_en, u.id AS usuario_id, u.cif, u.nombre, u.carrera
           FROM membresias m JOIN usuarios u ON u.id = m.usuario_id
           WHERE m.club_id = ? AND m.estado = 'pendiente' ORDER BY m.id""", (club_id,)).fetchall()


def contar_pendientes(bd, club_id):
    return bd.execute("SELECT COUNT(*) AS n FROM membresias WHERE club_id = ? AND estado = 'pendiente'",
                      (club_id,)).fetchone().n


def unirse(bd, usuario_id, club_id, pendiente):
    bd.execute("INSERT INTO membresias (usuario_id, club_id, rol, estado) VALUES (?, ?, 'miembro', ?)",
               (usuario_id, club_id, "pendiente" if pendiente else "activa"))


def aceptar(bd, membresia_id):
    bd.execute("UPDATE membresias SET estado = 'activa', unido_en = ? WHERE id = ?",
               (ahora_iso(), membresia_id))


def quitar(bd, membresia_id):
    bd.execute("DELETE FROM membresias WHERE id = ?", (membresia_id,))


def cambiar_rol(bd, membresia_id, rol):
    bd.execute("UPDATE membresias SET rol = ? WHERE id = ?", (rol, membresia_id))


def asignar_lider(bd, club_id, usuario_id):
    """La administración asigna el líder. El líder anterior (si lo hay) pasa a miembro."""
    actual = bd.execute("SELECT id, usuario_id FROM membresias WHERE club_id = ? AND rol = 'lider'",
                        (club_id,)).fetchone()
    if actual and actual.usuario_id == usuario_id:
        return
    if actual:
        bd.execute("UPDATE membresias SET rol = 'miembro' WHERE id = ?", (actual.id,))
    existente = membresia(bd, usuario_id, club_id)
    if existente:
        bd.execute("UPDATE membresias SET rol = 'lider', estado = 'activa' WHERE id = ?", (existente.id,))
    else:
        bd.execute("INSERT INTO membresias (usuario_id, club_id, rol, estado) VALUES (?, ?, 'lider', 'activa')",
                   (usuario_id, club_id))


def transferir_liderazgo(bd, club_id, membresia_nueva_id):
    """El líder actual pasa a capitán y el indicado pasa a líder (índice único: primero se degrada)."""
    bd.execute("UPDATE membresias SET rol = 'capitan' WHERE club_id = ? AND rol = 'lider'", (club_id,))
    bd.execute("UPDATE membresias SET rol = 'lider' WHERE id = ?", (membresia_nueva_id,))


# --- Solicitudes de creación de club -----------------------------------------------------------
def crear_solicitud(bd, usuario_id, nombre, descripcion, categoria_id, justificacion, requiere_aprobacion):
    bd.execute(
        """INSERT INTO solicitudes_club (usuario_id, nombre, descripcion, categoria_id, justificacion,
                                         requiere_aprobacion) VALUES (?, ?, ?, ?, ?, ?)""",
        (usuario_id, nombre, descripcion, categoria_id, justificacion, 1 if requiere_aprobacion else 0))


def solicitudes_pendientes(bd):
    return bd.execute(
        """SELECT s.*, u.nombre AS solicitante, u.cif AS solicitante_cif, cat.nombre AS categoria
           FROM solicitudes_club s JOIN usuarios u ON u.id = s.usuario_id
           JOIN categorias cat ON cat.id = s.categoria_id
           WHERE s.estado = 'pendiente' ORDER BY s.id""").fetchall()


def solicitudes_de(bd, usuario_id):
    return bd.execute(
        "SELECT * FROM solicitudes_club WHERE usuario_id = ? ORDER BY id DESC", (usuario_id,)).fetchall()


def resolver_solicitud(bd, solicitud_id, admin_id, aprobar, comentario):
    """Aprueba (crea club y líder) o rechaza. Devuelve el slug del club creado o None.

    Todo ocurre dentro de la transacción de la petición: si algo falla se deshace completo.
    """
    s = bd.execute("SELECT * FROM solicitudes_club WHERE id = ? AND estado = 'pendiente'",
                   (solicitud_id,)).fetchone()
    if not s:
        return None
    club_id = None
    if aprobar:
        club_id = crear(bd, s.nombre, s.descripcion, s.categoria_id, s.requiere_aprobacion)
        bd.execute("INSERT INTO membresias (usuario_id, club_id, rol, estado) VALUES (?, ?, 'lider', 'activa')",
                   (s.usuario_id, club_id))
    bd.execute(
        """UPDATE solicitudes_club SET estado = ?, revisado_por = ?, comentario = ?, club_id = ?,
           revisado_en = ? WHERE id = ?""",
        ("aprobada" if aprobar else "rechazada", admin_id, comentario, club_id, ahora_iso(), solicitud_id))
    return bd.execute("SELECT slug FROM clubes WHERE id = ?", (club_id,)).fetchone().slug if club_id else None
