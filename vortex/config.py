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
# Iteraciones de PBKDF2-SHA256 (recomendación OWASP: 600 000). Solo las pruebas automáticas lo reducen
# para ir más rápido. Las contraseñas guardadas antes con 200 000 se actualizan solas al iniciar sesión.
ITERACIONES_PBKDF2 = int(os.environ.get("VORTEX_ITERACIONES") or 600_000)
ITERACIONES_LEGADO = int(os.environ.get("VORTEX_ITERACIONES") or 200_000)

# Con VORTEX_HTTPS=1 (cuando el sitio se publica con HTTPS) las cookies solo viajan cifradas.
HTTPS = os.environ.get("VORTEX_HTTPS") == "1"

LIMITE_CUERPO = 6 * 1024 * 1024    # bytes por petición (una imagen de 5 MB más el formulario)
LIMITE_IMAGEN = 5 * 1024 * 1024    # bytes por imagen subida (fotos de celular)

# Contraseña inicial del administrador (se puede cambiar con VORTEX_ADMIN_CLAVE antes del primer arranque).
ADMIN_CIF = "00000001"
ADMIN_CLAVE_INICIAL = "admin123"
ADMIN_CLAVE = os.environ.get("VORTEX_ADMIN_CLAVE") or ADMIN_CLAVE_INICIAL
