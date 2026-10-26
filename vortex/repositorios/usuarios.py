from ..nucleo import Fila
from ..seguridad import hash_contrasena


def crear(bd, cif, nombre, correo, carrera, contrasena, rol="estudiante", hash_previo=None):
    h, sal = hash_previo or hash_contrasena(contrasena)
    cur = bd.execute(
        "INSERT INTO usuarios (cif, nombre, correo, carrera, hash_contrasena, sal, rol_global) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", (cif, nombre, correo, carrera, h, sal, rol))
    return cur.lastrowid


def cambiar_contrasena(bd, usuario_id, contrasena):
    h, sal = hash_contrasena(contrasena)
    bd.execute("UPDATE usuarios SET hash_contrasena = ?, sal = ?, clave_temporal = 0 WHERE id = ?", (h, sal, usuario_id))


def actualizar_hash(bd, usuario_id, contrasena):
    """Vuelve a guardar la contraseña con el formato y las iteraciones actuales (sin tocar nada más)."""
    h, sal = hash_contrasena(contrasena)
    bd.execute("UPDATE usuarios SET hash_contrasena = ?, sal = ? WHERE id = ?", (h, sal, usuario_id))


def por_cif(bd, cif):
    return bd.execute("SELECT * FROM usuarios WHERE cif = ?", (cif,)).fetchone()


def por_id(bd, usuario_id):
    return bd.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()


def correo_existe(bd, correo):
    return bd.execute("SELECT 1 FROM usuarios WHERE correo = ?", (correo,)).fetchone() is not None


def listar(bd):
    return bd.execute(
        "SELECT id, cif, nombre, correo, carrera, rol_global, activo, creado_en "
        "FROM usuarios ORDER BY id DESC").fetchall()


def cambiar_activo(bd, usuario_id, activo):
    bd.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (1 if activo else 0, usuario_id))
    if not activo:
        bd.execute("DELETE FROM sesiones WHERE usuario_id = ?", (usuario_id,))


def estadisticas(bd):
    consulta = lambda sql: bd.execute(sql).fetchone().n
    return Fila({
        "usuarios": consulta("SELECT COUNT(*) AS n FROM usuarios"),
        "clubes": consulta("SELECT COUNT(*) AS n FROM clubes WHERE estado = 'activo'"),
        "publicaciones": consulta("SELECT COUNT(*) AS n FROM publicaciones WHERE eliminado = 0"),
        "eventos": consulta("SELECT COUNT(*) AS n FROM propuestas_evento WHERE estado = 'aprobada'"),
    })


def cambiar_foto(bd, usuario_id, foto):
    """Guarda el nombre del archivo de la foto de perfil ('' = sin foto) y devuelve el anterior."""
    anterior = bd.execute("SELECT foto FROM usuarios WHERE id = ?", (usuario_id,)).fetchone().foto
    bd.execute("UPDATE usuarios SET foto = ? WHERE id = ?", (foto, usuario_id))
    return anterior
