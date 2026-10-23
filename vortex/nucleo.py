"""Objetos básicos compartidos: Fila, ErrorHttp, Peticion y Respuesta."""
import secrets
from urllib.parse import quote


class Fila(dict):
    """Diccionario con acceso por atributo (fila.nombre o fila['nombre']).

    Las claves inexistentes devuelven None al leerlas como atributo, lo que simplifica las plantillas.
    """
    __slots__ = ()

    def __getattr__(self, nombre):
        if nombre.startswith("__"):
            raise AttributeError(nombre)
        return self.get(nombre)


def fabrica_filas(cursor, fila):
    """row_factory de sqlite3: cada fila es una Fila."""
    return Fila(zip([c[0] for c in cursor.description], fila))


class ErrorHttp(Exception):
    """Se lanza desde cualquier capa para responder con un código de error."""

    def __init__(self, estado, mensaje=""):
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje


class Respuesta:
    def __init__(self, cuerpo=b"", estado=200, tipo="text/html; charset=utf-8"):
        self.estado = estado
        self.cuerpo = cuerpo
        self.cabeceras = [("Content-Type", tipo)]

    @classmethod
    def html(cls, texto, estado=200):
        return cls(texto.encode("utf-8"), estado)

    @classmethod
    def redirigir(cls, url, estado=303):
        r = cls(b"", estado)
        r.cabeceras.append(("Location", url))
        return r

    def cookie(self, nombre, valor, max_age=None):
        texto = f"{nombre}={valor}; Path=/; HttpOnly; SameSite=Lax"
        if max_age is not None:
            texto += f"; Max-Age={max_age}"
        self.cabeceras.append(("Set-Cookie", texto))
        return self

    def borrar_cookie(self, nombre):
        return self.cookie(nombre, "", max_age=0)

    def con_aviso(self, nivel, texto):
        """Mensaje que se muestra una sola vez en la página siguiente (nivel: ok | error)."""
        return self.cookie("aviso", quote(f"{nivel}|{texto}", safe=""), max_age=60)


class Peticion:
    def __init__(self, metodo, ruta, consulta, cookies, ip, encabezados):
        self.metodo = metodo
        self.ruta = ruta
        self.consulta = consulta
        self.cookies = cookies
        self.ip = ip
        self.encabezados = encabezados
        self.formulario = {}
        self.archivos = {}
        self.usuario = None      # Fila del usuario con sesión (o None)
        self.sesion = None       # Fila(token, csrf)
        self.bd = None
        self.aviso = None        # Fila(nivel, texto) leído de la cookie "aviso"
        self.csrf_nuevo = None   # token CSRF anónimo generado en esta petición

    @property
    def ruta_completa(self):
        if self.consulta:
            from urllib.parse import urlencode
            return self.ruta + "?" + urlencode(self.consulta)
        return self.ruta

    def token_csrf(self):
        """Token CSRF esperado: el de la sesión o, para visitantes, el de la cookie anónima."""
        if self.sesion:
            return self.sesion.csrf
        token = self.cookies.get("csrf_anon")
        if not token:
            if not self.csrf_nuevo:
                self.csrf_nuevo = secrets.token_urlsafe(24)
            token = self.csrf_nuevo
        return token
