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
def hash_contrasena(contrasena, sal=None, iteraciones=None):
    """Devuelve (hash, sal_hex). La sal es aleatoria si no se indica.
    El hash guarda el algoritmo y las iteraciones («pbkdf2_sha256$600000$<hex>»): así se pueden subir
    las iteraciones más adelante sin invalidar las contraseñas que ya están guardadas."""
    iteraciones = iteraciones or config.ITERACIONES_PBKDF2
    sal = sal if sal is not None else secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), sal, iteraciones)
    return f"pbkdf2_sha256${iteraciones}${h.hex()}", sal.hex()


def _iteraciones(hash_guardado):
    if hash_guardado.startswith("pbkdf2_sha256$"):
        return int(hash_guardado.split("$")[1])
    return config.ITERACIONES_LEGADO   # formato antiguo: solo el hexadecimal


def verificar_contrasena(contrasena, hash_guardado, sal_hex):
    try:
        iteraciones = _iteraciones(hash_guardado)
        sal = bytes.fromhex(sal_hex)
    except (ValueError, IndexError):
        return False
    h, _ = hash_contrasena(contrasena, sal, iteraciones)
    esperado = hash_guardado if "$" in hash_guardado else f"pbkdf2_sha256${iteraciones}${hash_guardado}"
    return hmac.compare_digest(h, esperado)


def necesita_actualizar(hash_guardado):
    """True si la contraseña se guardó con el formato antiguo o con menos iteraciones de las actuales."""
    return "$" not in hash_guardado or _iteraciones(hash_guardado) < config.ITERACIONES_PBKDF2


# --- Sesiones ------------------------------------------------------------------------------
# En la base de datos solo se guarda la huella SHA-256 del token: si alguien llegara a copiar el
# archivo de la base, no podría usar esas sesiones (el token real solo lo tiene el navegador).
def _huella(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _formato(fecha):
    return fecha.strftime("%Y-%m-%d %H:%M:%S")


def crear_sesion(bd, usuario_id, rol_acceso="estudiante"):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    expira = _formato(datetime.now() + timedelta(days=config.DURACION_SESION_DIAS))
    bd.execute("DELETE FROM sesiones WHERE expira_en < ?", (_formato(datetime.now()),))
    bd.execute("INSERT INTO sesiones (token, usuario_id, csrf, expira_en, rol_acceso) VALUES (?, ?, ?, ?, ?)",
               (_huella(token), usuario_id, csrf, expira, rol_acceso))
    return token


def obtener_sesion(bd, token):
    """Devuelve (sesion, usuario) o (None, None) si no hay sesión válida."""
    if not token or len(token) > 100:
        return None, None
    fila = bd.execute(
        """SELECT s.token, s.csrf, s.rol_acceso, u.id, u.cif, u.nombre, u.correo, u.carrera, u.rol_global, u.foto,
                  u.clave_temporal
           FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id
           WHERE s.token = ? AND s.expira_en > ? AND u.activo = 1""",
        (_huella(token), _formato(datetime.now()))).fetchone()
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
    if token:
        bd.execute("DELETE FROM sesiones WHERE token = ?", (_huella(token),))


def cerrar_todas(bd, usuario_id):
    """Cierra la sesión de la persona en todos sus dispositivos (al cambiar la contraseña)."""
    bd.execute("DELETE FROM sesiones WHERE usuario_id = ?", (usuario_id,))


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

    def limpiar(self):
        with self._cerrojo:
            self._fallos.clear()


limite_acceso = LimiteIntentos()                          # por IP + CIF: adivinar la contraseña de una cuenta
limite_ip = LimiteIntentos(maximo=20, ventana=900)        # por IP: probar muchas cuentas desde un mismo equipo
limite_registro = LimiteIntentos(maximo=10, ventana=3600) # por IP: crear cuentas en masa
