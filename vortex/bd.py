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
        bd.executescript(config.RUTA_ESQUEMA.read_text(encoding="utf-8"))
        _migrar(bd)
        if bd.execute("SELECT COUNT(*) AS n FROM categorias").fetchone().n == 0:
            from . import semilla
            semilla.datos_base(bd)
            bd.commit()
    finally:
        bd.close()


def _migrar(bd):
    """Agrega columnas nuevas a bases de datos creadas con versiones anteriores."""
    columnas = {c.name for c in bd.execute("PRAGMA table_info(sesiones)").fetchall()}
    if "rol_acceso" not in columnas:
        bd.execute("ALTER TABLE sesiones ADD COLUMN rol_acceso TEXT NOT NULL DEFAULT 'estudiante' "
                   "CHECK (rol_acceso IN ('estudiante', 'capitan', 'lider', 'admin'))")
        bd.commit()
