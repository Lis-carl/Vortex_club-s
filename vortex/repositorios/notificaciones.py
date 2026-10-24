"""Notificaciones dentro de la plataforma (pedidas en la encuesta: «los avisos llegan tarde»)."""


def crear(bd, usuario_id, texto, enlace="/"):
    bd.execute("INSERT INTO notificaciones (usuario_id, texto, enlace) VALUES (?, ?, ?)", (usuario_id, texto[:300], enlace))


def crear_para_varios(bd, usuarios_ids, texto, enlace="/", excepto=None):
    for usuario_id in set(usuarios_ids):
        if usuario_id != excepto:
            crear(bd, usuario_id, texto, enlace)


def crear_para_club(bd, club_id, texto, enlace="/", excepto=None):
    filas = bd.execute("SELECT usuario_id FROM membresias WHERE club_id = ? AND estado = 'activa'", (club_id,)).fetchall()
    crear_para_varios(bd, [f.usuario_id for f in filas], texto, enlace, excepto)


def crear_para_todos(bd, texto, enlace="/", excepto=None):
    filas = bd.execute("SELECT id FROM usuarios WHERE activo = 1").fetchall()
    crear_para_varios(bd, [f.id for f in filas], texto, enlace, excepto)


def crear_para_admins(bd, texto, enlace="/admin"):
    filas = bd.execute("SELECT id FROM usuarios WHERE activo = 1 AND rol_global = 'admin'").fetchall()
    crear_para_varios(bd, [f.id for f in filas], texto, enlace)


def listar(bd, usuario_id, limite=60):
    return bd.execute("SELECT * FROM notificaciones WHERE usuario_id = ? ORDER BY id DESC LIMIT ?",
                      (usuario_id, limite)).fetchall()


def no_leidas(bd, usuario_id):
    return bd.execute("SELECT COUNT(*) AS n FROM notificaciones WHERE usuario_id = ? AND leida = 0",
                      (usuario_id,)).fetchone().n


def marcar_leidas(bd, usuario_id):
    bd.execute("UPDATE notificaciones SET leida = 1 WHERE usuario_id = ? AND leida = 0", (usuario_id,))
