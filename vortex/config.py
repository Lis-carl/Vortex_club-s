"""Configuración central. Se puede ajustar con variables de entorno (útil para pruebas)."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

RUTA_BD = Path(os.environ.get("VORTEX_BD") or RAIZ / "datos" / "vortex.db")
DIR_SUBIDAS = Path(os.environ.get("VORTEX_SUBIDAS") or RAIZ / "subidas")
DIR_ESTATICO = RAIZ / "estatico"
DIR_PLANTILLAS = RAIZ / "plantillas"
RUTA_ESQUEMA = RAIZ / "sql" / "esquema.sql"

DURACION_SESION_DIAS = 7
# Iteraciones de PBKDF2. Solo las pruebas automáticas lo reducen para ir más rápido.
ITERACIONES_PBKDF2 = int(os.environ.get("VORTEX_ITERACIONES") or 200_000)

LIMITE_CUERPO = 3 * 1024 * 1024    # bytes por petición
LIMITE_IMAGEN = 2 * 1024 * 1024    # bytes por imagen subida

# Contraseña inicial del administrador (se puede cambiar con VORTEX_ADMIN_CLAVE antes del primer arranque).
ADMIN_CIF = "00000001"
ADMIN_CLAVE = os.environ.get("VORTEX_ADMIN_CLAVE") or "admin123"
