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


def inicializar(con_demo=True):
    """Crea la base de datos si no existe y la llena con datos iniciales la primera vez."""
    config.RUTA_BD.parent.mkdir(parents=True, exist_ok=True)
    config.DIR_SUBIDAS.mkdir(parents=True, exist_ok=True)
    bd = conectar()
    try:
        bd.execute("PRAGMA journal_mode = WAL")
        bd.executescript(config.RUTA_ESQUEMA.read_text(encoding="utf-8"))
        from . import semilla
        if bd.execute("SELECT COUNT(*) AS n FROM categorias").fetchone().n == 0:
            semilla.datos_base(bd)
            if con_demo:
                semilla.datos_demo(bd)
            bd.commit()
    finally:
        bd.close()
