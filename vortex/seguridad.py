"""Contraseñas (PBKDF2), sesiones y protección CSRF."""
import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime, timedelta

from . import config
from .nucleo import Fila, ErrorHttp


# --- Contraseñas -------------------------------------------------------------------------
def hash_contrasena(contrasena, sal=None):
    """Devuelve (hash_hex, sal_hex). La sal es aleatoria si no se indica."""
    sal = sal if sal is not None else secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), sal, config.ITERACIONES_PBKDF2)
    return h.hex(), sal.hex()


def verificar_contrasena(contrasena, hash_hex, sal_hex):
    h, _ = hash_contrasena(contrasena, bytes.fromhex(sal_hex))
    return hmac.compare_digest(h, hash_hex)


# --- Sesiones ------------------------------------------------------------------------------
def _formato(fecha):
    return fecha.strftime("%Y-%m-%d %H:%M:%S")


def crear_sesion(bd, usuario_id, rol_acceso="estudiante"):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    expira = _formato(datetime.now() + timedelta(days=config.DURACION_SESION_DIAS))
    bd.execute("DELETE FROM sesiones WHERE expira_en < ?", (_formato(datetime.now()),))
    bd.execute("INSERT INTO sesiones (token, usuario_id, csrf, expira_en, rol_acceso) VALUES (?, ?, ?, ?, ?)",
               (token, usuario_id, csrf, expira, rol_acceso))
    return token


def obtener_sesion(bd, token):
    """Devuelve (sesion, usuario) o (None, None) si no hay sesión válida."""
    if not token:
        return None, None
    fila = bd.execute(
        """SELECT s.token, s.csrf, s.rol_acceso, u.id, u.cif, u.nombre, u.correo, u.carrera, u.rol_global
           FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id
           WHERE s.token = ? AND s.expira_en > ? AND u.activo = 1""",
        (token, _formato(datetime.now()))).fetchone()
    if not fila:
        return None, None
    sesion = Fila(token=fila.token, csrf=fila.csrf)
    usuario = Fila({k: v for k, v in fila.items() if k not in ("token", "csrf")})
    usuario["rol_acceso"] = rol_de_cuenta(bd, usuario.id, usuario.rol_global)
    return sesion, usuario


def rol_de_cuenta(bd, usuario_id, rol_global):
    """El tipo de usuario lo determina la cuenta: administración, o el rol más alto que tenga en algún
    club activo (líder > capitán > estudiante). Se recalcula en cada petición, así un nombramiento
    nuevo se aplica de inmediato sin volver a iniciar sesión."""
    if rol_global == "admin":
        return "admin"
    roles = {f.rol for f in bd.execute(
        """SELECT DISTINCT m.rol FROM membresias m JOIN clubes c ON c.id = m.club_id
           WHERE m.usuario_id = ? AND m.estado = 'activa' AND c.estado = 'activo'""", (usuario_id,)).fetchall()}
    return "lider" if "lider" in roles else "capitan" if "capitan" in roles else "estudiante"


def cerrar_sesion(bd, token):
    bd.execute("DELETE FROM sesiones WHERE token = ?", (token,))


# --- CSRF ----------------------------------------------------------------------------------
def validar_csrf(peticion):
    """Las peticiones POST deben traer en el campo oculto 'csrf' el token de la sesión."""
    esperado = peticion.sesion.csrf if peticion.sesion else peticion.cookies.get("csrf_anon")
    enviado = peticion.formulario.get("csrf") or ""
    if not esperado or not hmac.compare_digest(str(esperado), str(enviado)):
        raise ErrorHttp(403, "El token de seguridad no es válido. Recarga la página e inténtalo de nuevo.")


# --- Límite de intentos de acceso -----------------------------------------------------------
class LimiteIntentos:
    """Bloquea temporalmente una clave (ip + cif) tras varios fallos seguidos."""

    def __init__(self, maximo=5, ventana=300):
        self.maximo = maximo
        self.ventana = ventana
        self._fallos = {}
        self._cerrojo = threading.Lock()

    def bloqueado(self, clave):
        with self._cerrojo:
            ahora = time.time()
            recientes = [t for t in self._fallos.get(clave, []) if ahora - t < self.ventana]
            self._fallos[clave] = recientes
            return len(recientes) >= self.maximo

    def fallo(self, clave):
        with self._cerrojo:
            self._fallos.setdefault(clave, []).append(time.time())

    def reiniciar(self, clave):
        with self._cerrojo:
            self._fallos.pop(clave, None)


limite_acceso = LimiteIntentos()
