"""Utilidades de prueba: servidor temporal y un cliente HTTP con cookies (solo biblioteca estándar)."""
import os
import re
import shutil
import tempfile
import threading
import unittest
import uuid
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

# La configuración se lee al importar vortex: se ajusta antes de cualquier import.
_TEMPORAL = tempfile.mkdtemp(prefix="vortex_pruebas_")
os.environ["VORTEX_BD"] = os.path.join(_TEMPORAL, "prueba.db")
os.environ["VORTEX_SUBIDAS"] = os.path.join(_TEMPORAL, "subidas")
os.environ["VORTEX_ITERACIONES"] = "1000"   # solo para pruebas: acelera PBKDF2

from vortex import bd, servidor  # noqa: E402
from pruebas import datos_prueba  # noqa: E402

servidor.Manejador.log_message = lambda *a, **k: None   # sin ruido en la consola de pruebas

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


class Respuesta:
    def __init__(self, estado, cuerpo, url):
        self.estado, self.cuerpo, self.url = estado, cuerpo, url


class Cliente:
    """Navegador mínimo: guarda cookies, sigue redirecciones y extrae el token CSRF de la página."""

    def __init__(self, base):
        self.base = base
        self.abridor = build_opener(HTTPCookieProcessor(CookieJar()))

    def _enviar(self, req):
        try:
            r = self.abridor.open(req)
            return Respuesta(r.status, r.read().decode("utf-8", "replace"), r.geturl())
        except HTTPError as e:
            try:
                return Respuesta(e.code, e.read().decode("utf-8", "replace"), e.url)
            finally:
                e.close()

    def get(self, ruta):
        return self._enviar(Request(self.base + ruta))

    def token(self, pagina="/acceder"):
        html = self.get(pagina).cuerpo
        m = re.search(r'name="csrf" value="([^"]+)"', html)
        return m.group(1) if m else ""

    def post(self, ruta, datos=None, desde="/", csrf=True):
        datos = dict(datos or {})
        if csrf and "csrf" not in datos:
            datos["csrf"] = self.token(desde)
        cabeceras = {"Content-Type": "application/x-www-form-urlencoded"}
        return self._enviar(Request(self.base + ruta, urlencode(datos).encode(), cabeceras))

    def post_multipart(self, ruta, campos, archivos, desde="/"):
        campos = dict(campos, csrf=self.token(desde))
        limite = "----vortex" + uuid.uuid4().hex
        partes = []
        for k, v in campos.items():
            partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (nombre, contenido) in archivos.items():
            partes.append((f'--{limite}\r\nContent-Disposition: form-data; name="{k}"; filename="{nombre}"\r\n'
                           f'Content-Type: application/octet-stream\r\n\r\n').encode() + contenido + b"\r\n")
        partes.append(f"--{limite}--\r\n".encode())
        return self._enviar(Request(self.base + ruta, b"".join(partes),
                                    {"Content-Type": f"multipart/form-data; boundary={limite}"}))

    def entrar(self, cif, clave=None, rol=None):
        """Inicia sesión. Sin rol explícito usa el más alto que tenga la cuenta (admin, líder, capitán, estudiante)."""
        clave = clave or ("admin123" if cif == "00000001" else "demo1234")
        roles = [rol] if rol else (["admin"] if cif == "00000001" else ["lider", "capitan", "estudiante"])
        for intento in roles:
            r = self.post("/acceder", {"cif": cif, "contrasena": clave, "rol": intento}, desde="/acceder")
            if r.estado == 200 and "/acceder" not in r.url:
                return r
        raise AssertionError(f"No se pudo entrar como {cif}: {r.estado}")


class PruebaServidor(unittest.TestCase):
    """Cada clase de prueba levanta su propio servidor con una base de datos nueva.

    Por omisión se cargan los datos ficticios de pruebas/datos_prueba.py; con_datos_prueba = False
    deja la base tal como la crea la aplicación real (vacía, solo con el catálogo oficial de clubes).
    """
    con_datos_prueba = True

    @classmethod
    def setUpClass(cls):
        ruta_bd = os.environ["VORTEX_BD"]
        for sufijo in ("", "-wal", "-shm"):
            if os.path.exists(ruta_bd + sufijo):
                os.remove(ruta_bd + sufijo)
        bd.inicializar()
        if cls.con_datos_prueba:
            con = bd.conectar()
            datos_prueba.cargar(con)
            con.commit()
            con.close()
        cls.servidor = servidor.crear_servidor("127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        cls.hilo = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.hilo.start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def cliente(self, cif=None):
        c = Cliente(self.base)
        if cif:
            c.entrar(cif)
        return c


def limpiar_temporales():
    shutil.rmtree(_TEMPORAL, ignore_errors=True)
