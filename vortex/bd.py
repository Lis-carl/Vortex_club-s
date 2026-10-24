"""Conexión a SQLite y creación del esquema."""
import sqlite3

from . import config
from .nucleo import fabrica_filas


def conectar():
    """Una conexión nueva por petición (SQLite es ligero y así cada hilo tiene la suya)."""
    con = sqlite3.connect(config.RUTA_BD, timeout=15)
    con.row_factory = fabrica_filas
    con.execute("PRAGMA foreign_keys = ON")
    return con


def inicializar():
    """Crea la base de datos si no existe y carga los datos iniciales la primera vez."""
    config.RUTA_BD.parent.mkdir(parents=True, exist_ok=True)
    config.DIR_SUBIDAS.mkdir(parents=True, exist_ok=True)
    bd = conectar()
    try:
        bd.execute("PRAGMA journal_mode = WAL")
        esquema = config.RUTA_ESQUEMA.read_text(encoding="utf-8")
        bd.executescript(esquema)
        if _migrar(bd):
            bd.executescript(esquema)   # vuelve a crear las vistas quitadas durante la migración
        from . import semilla
        if bd.execute("SELECT COUNT(*) AS n FROM usuarios WHERE rol_global = 'admin'").fetchone().n == 0:
            semilla.datos_base(bd)
        else:
            semilla.asegurar_catalogo(bd)
        bd.commit()
    finally:
        bd.close()


def _migrar(bd):
    """Agrega columnas nuevas a bases de datos creadas con versiones anteriores."""
    columnas = {c.name for c in bd.execute("PRAGMA table_info(sesiones)").fetchall()}
    if "rol_acceso" not in columnas:
        bd.execute("ALTER TABLE sesiones ADD COLUMN rol_acceso TEXT NOT NULL DEFAULT 'estudiante' "
                   "CHECK (rol_acceso IN ('estudiante', 'capitan', 'lider', 'admin'))")
    columnas = {c.name for c in bd.execute("PRAGMA table_info(usuarios)").fetchall()}
    if "foto" not in columnas:
        bd.execute("ALTER TABLE usuarios ADD COLUMN foto TEXT NOT NULL DEFAULT ''")
    columnas = {c.name for c in bd.execute("PRAGMA table_info(clubes)").fetchall()}
    if "foto" not in columnas:
        bd.execute("ALTER TABLE clubes ADD COLUMN foto TEXT NOT NULL DEFAULT ''")
    bd.commit()
    if "categoria_id" in columnas:
        _quitar_categorias(bd)
        return True
    return False


def _quitar_categorias(bd):
    """Las categorías se retiraron del sistema: se reconstruyen clubes y solicitudes_club sin la
    columna categoria_id (SQLite no permite borrar una columna con clave foránea) y se borra la tabla."""
    bd.executescript("""
        PRAGMA foreign_keys = OFF;
        BEGIN;
        DROP VIEW IF EXISTS v_eventos;
        DROP VIEW IF EXISTS v_puntaje_publicacion;
        CREATE TABLE clubes_nueva (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre              TEXT    NOT NULL UNIQUE COLLATE NOCASE CHECK (length(nombre) BETWEEN 3 AND 60),
            slug                TEXT    NOT NULL UNIQUE,
            descripcion         TEXT    NOT NULL DEFAULT '',
            foto                TEXT    NOT NULL DEFAULT '',
            requiere_aprobacion INTEGER NOT NULL DEFAULT 0 CHECK (requiere_aprobacion IN (0, 1)),
            estado              TEXT    NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo')),
            creado_en           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        INSERT INTO clubes_nueva (id, nombre, slug, descripcion, foto, requiere_aprobacion, estado, creado_en)
            SELECT id, nombre, slug, descripcion, foto, requiere_aprobacion, estado, creado_en FROM clubes;
        DROP TABLE clubes;
        ALTER TABLE clubes_nueva RENAME TO clubes;
        CREATE TABLE solicitudes_club_nueva (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            nombre          TEXT    NOT NULL,
            descripcion     TEXT    NOT NULL,
            justificacion   TEXT    NOT NULL DEFAULT '',
            requiere_aprobacion INTEGER NOT NULL DEFAULT 0 CHECK (requiere_aprobacion IN (0, 1)),
            estado          TEXT    NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
            revisado_por    INTEGER REFERENCES usuarios(id),
            comentario      TEXT    NOT NULL DEFAULT '',
            club_id         INTEGER REFERENCES clubes(id),
            creado_en       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            revisado_en     TEXT
        );
        INSERT INTO solicitudes_club_nueva (id, usuario_id, nombre, descripcion, justificacion, requiere_aprobacion,
                                            estado, revisado_por, comentario, club_id, creado_en, revisado_en)
            SELECT id, usuario_id, nombre, descripcion, justificacion, requiere_aprobacion,
                   estado, revisado_por, comentario, club_id, creado_en, revisado_en FROM solicitudes_club;
        DROP TABLE solicitudes_club;
        ALTER TABLE solicitudes_club_nueva RENAME TO solicitudes_club;
        DROP TABLE IF EXISTS categorias;
        COMMIT;
        PRAGMA foreign_keys = ON;
    """)
