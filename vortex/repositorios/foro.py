"""Publicaciones, comentarios, votos y reacciones (estilo Reddit)."""
from ..nucleo import Fila

# Reacciones permitidas: (emoji, clave para estilos, nombre visible). El emoji coincide con el CHECK de sql/esquema.sql.
REACCIONES = [
    ("\U0001F44D", "apoyo", "Apoyo"),
    ("\u2764\ufe0f", "encanta", "Me encanta"),
    ("\U0001F602", "divierte", "Me divierte"),
    ("\U0001F62E", "sorprende", "Me sorprende"),
    ("\U0001F622", "entristece", "Me entristece"),
    ("\U0001F525", "increible", "Increíble"),
]
TIPOS_REACCION = [emoji for emoji, _, _ in REACCIONES]

_BASE = """
SELECT p.id, p.club_id, p.autor_id, p.titulo, p.contenido, p.imagen, p.creado_en, p.editado_en,
       c.nombre AS club_nombre, c.slug AS club_slug,
       u.nombre AS autor_nombre, u.cif AS autor_cif, u.foto AS autor_foto,
       COALESCE((SELECT SUM(v.valor) FROM votos_publicacion v WHERE v.publicacion_id = p.id), 0) AS puntaje,
       (SELECT v.valor FROM votos_publicacion v WHERE v.publicacion_id = p.id AND v.usuario_id = :uid) AS mi_voto,
       (SELECT COUNT(*) FROM comentarios k WHERE k.publicacion_id = p.id AND k.eliminado = 0) AS n_comentarios,
       (SELECT COUNT(*) FROM reacciones r WHERE r.publicacion_id = p.id) AS n_reacciones
FROM publicaciones p
JOIN clubes c ON c.id = p.club_id
JOIN usuarios u ON u.id = p.autor_id
WHERE p.eliminado = 0 AND c.estado = 'activo'
"""


def _con_reacciones(bd, publicaciones, usuario_id):
    if not publicaciones:
        return publicaciones
    ids = [p.id for p in publicaciones]
    marcas = ",".join("?" * len(ids))
    filas = bd.execute(
        f"""SELECT publicacion_id, tipo, COUNT(*) AS n, MAX(usuario_id = ?) AS mia
            FROM reacciones WHERE publicacion_id IN ({marcas}) GROUP BY publicacion_id, tipo""",
        [usuario_id] + ids).fetchall()
    por_pub = {}
    for f in filas:
        por_pub.setdefault(f.publicacion_id, {})[f.tipo] = f
    for p in publicaciones:
        datos = por_pub.get(p.id, {})
        p["reacciones"] = [Fila(tipo=t, clave=clave, nombre=nombre, n=datos[t].n if t in datos else 0,
                                mia=bool(t in datos and datos[t].mia))
                           for t, clave, nombre in REACCIONES]
    return publicaciones


def listar(bd, usuario_id, club_id=None, solo_mis_clubes=False, autor_id=None, orden="nuevos",
           limite=20, pagina=1, desde=None):
    sql, params = _BASE, {"uid": usuario_id, "limite": limite, "desp": (max(pagina, 1) - 1) * limite}
    if club_id:
        sql += " AND p.club_id = :club"
        params["club"] = club_id
    if solo_mis_clubes:
        sql += " AND p.club_id IN (SELECT club_id FROM membresias WHERE usuario_id = :uid AND estado = 'activa')"
    if autor_id:
        sql += " AND p.autor_id = :autor"
        params["autor"] = autor_id
    if desde:
        sql += " AND p.creado_en >= :desde"
        params["desde"] = desde
    sql += (" ORDER BY (puntaje + n_reacciones + n_comentarios) DESC, p.id DESC" if orden == "populares"
            else " ORDER BY p.id DESC")
    sql += " LIMIT :limite OFFSET :desp"
    return _con_reacciones(bd, bd.execute(sql, params).fetchall(), usuario_id)


def publicacion(bd, publicacion_id, usuario_id):
    filas = bd.execute(_BASE + " AND p.id = :id", {"uid": usuario_id, "id": publicacion_id}).fetchall()
    return _con_reacciones(bd, filas, usuario_id)[0] if filas else None


def crear_publicacion(bd, club_id, autor_id, titulo, contenido, imagen):
    cur = bd.execute(
        "INSERT INTO publicaciones (club_id, autor_id, titulo, contenido, imagen) VALUES (?, ?, ?, ?, ?)",
        (club_id, autor_id, titulo, contenido, imagen))
    return cur.lastrowid


def eliminar_publicacion(bd, publicacion_id):
    bd.execute("UPDATE publicaciones SET eliminado = 1 WHERE id = ?", (publicacion_id,))


# --- Comentarios --------------------------------------------------------------------------------
def comentarios(bd, publicacion_id, usuario_id):
    """Comentarios en orden de árbol (cada respuesta justo debajo de su comentario padre)."""
    filas = bd.execute(
        """SELECT k.id, k.publicacion_id, k.autor_id, k.padre_id, k.contenido, k.eliminado, k.creado_en, k.editado_en,
                  u.nombre AS autor_nombre, u.cif AS autor_cif, u.foto AS autor_foto,
                  COALESCE((SELECT SUM(v.valor) FROM votos_comentario v WHERE v.comentario_id = k.id), 0) AS puntaje,
                  (SELECT v.valor FROM votos_comentario v WHERE v.comentario_id = k.id AND v.usuario_id = ?) AS mi_voto
           FROM comentarios k JOIN usuarios u ON u.id = k.autor_id
           WHERE k.publicacion_id = ? ORDER BY k.id""", (usuario_id, publicacion_id)).fetchall()
    hijos = {}
    for f in filas:
        hijos.setdefault(f.padre_id, []).append(f)
    salida, pila = [], [(h, 0) for h in reversed(hijos.get(None, []))]
    while pila:   # recorrido en profundidad sin recursión
        fila, nivel = pila.pop()
        fila["nivel"] = min(nivel, 5)
        salida.append(fila)
        pila.extend((h, nivel + 1) for h in reversed(hijos.get(fila.id, [])))
    return salida


def comentario(bd, comentario_id):
    return bd.execute(
        """SELECT k.*, p.club_id FROM comentarios k JOIN publicaciones p ON p.id = k.publicacion_id
           WHERE k.id = ?""", (comentario_id,)).fetchone()


def crear_comentario(bd, publicacion_id, autor_id, padre_id, contenido):
    bd.execute("INSERT INTO comentarios (publicacion_id, autor_id, padre_id, contenido) VALUES (?, ?, ?, ?)",
               (publicacion_id, autor_id, padre_id, contenido))


def editar_publicacion(bd, publicacion_id, titulo, contenido):
    bd.execute("UPDATE publicaciones SET titulo = ?, contenido = ?, editado_en = datetime('now', 'localtime') WHERE id = ?",
               (titulo, contenido, publicacion_id))


def editar_comentario(bd, comentario_id, contenido):
    bd.execute("UPDATE comentarios SET contenido = ?, editado_en = datetime('now', 'localtime') WHERE id = ?", (contenido, comentario_id))


def eliminar_comentario(bd, comentario_id):
    bd.execute("UPDATE comentarios SET eliminado = 1, contenido = '[eliminado]' WHERE id = ?", (comentario_id,))


# --- Votos ---------------------------------------------------------------------------------------
_VOTOS = {"publicacion": ("votos_publicacion", "publicacion_id"), "comentario": ("votos_comentario", "comentario_id")}


def votar(bd, tipo, usuario_id, objetivo_id, valor):
    """Alterna el voto (+1/-1). Devuelve (puntaje, mi_voto). Repetir el mismo voto lo retira."""
    tabla, columna = _VOTOS[tipo]
    actual = bd.execute(f"SELECT valor FROM {tabla} WHERE usuario_id = ? AND {columna} = ?",
                        (usuario_id, objetivo_id)).fetchone()
    if actual and actual.valor == valor:
        bd.execute(f"DELETE FROM {tabla} WHERE usuario_id = ? AND {columna} = ?", (usuario_id, objetivo_id))
        mi_voto = None
    elif actual:
        bd.execute(f"UPDATE {tabla} SET valor = ? WHERE usuario_id = ? AND {columna} = ?",
                   (valor, usuario_id, objetivo_id))
        mi_voto = valor
    else:
        bd.execute(f"INSERT INTO {tabla} (usuario_id, {columna}, valor) VALUES (?, ?, ?)",
                   (usuario_id, objetivo_id, valor))
        mi_voto = valor
    puntaje = bd.execute(f"SELECT COALESCE(SUM(valor), 0) AS n FROM {tabla} WHERE {columna} = ?",
                         (objetivo_id,)).fetchone().n
    return puntaje, mi_voto


# --- Reacciones ----------------------------------------------------------------------------------
def alternar_reaccion(bd, usuario_id, publicacion_id, tipo):
    existe = bd.execute("SELECT 1 FROM reacciones WHERE usuario_id = ? AND publicacion_id = ? AND tipo = ?",
                        (usuario_id, publicacion_id, tipo)).fetchone()
    if existe:
        bd.execute("DELETE FROM reacciones WHERE usuario_id = ? AND publicacion_id = ? AND tipo = ?",
                   (usuario_id, publicacion_id, tipo))
    else:
        bd.execute("INSERT INTO reacciones (usuario_id, publicacion_id, tipo) VALUES (?, ?, ?)",
                   (usuario_id, publicacion_id, tipo))
    return not existe
