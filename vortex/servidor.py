"""Servidor HTTP construido sobre http.server (biblioteca estándar)."""
import re
import traceback
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from . import bd as modulo_bd, config, formularios, seguridad, vistas
from .nucleo import ErrorHttp, Fila, Peticion, Respuesta
from .enrutador import enrutador
from . import controladores  # noqa: F401  (al importarlo se registran todas las rutas)

_TIPOS_ESTATICOS = {
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".ico": "image/x-icon", ".txt": "text/plain; charset=utf-8",
}
_RE_SUBIDA = re.compile(r"^[0-9a-f]{32}\.(png|jpg|gif|webp)$")

_CABECERAS_SEGURIDAD = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "SAMEORIGIN"),   # el chat se muestra en un marco del mismo sitio
    ("Referrer-Policy", "same-origin"),
    ("Content-Security-Policy",
     "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'none'; "
     "object-src 'none'; base-uri 'none'; form-action 'self'; "
     "frame-src 'self'; frame-ancestors 'self'"),   # sin JavaScript: ningún script puede ejecutarse
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Cross-Origin-Resource-Policy", "same-origin"),
]
if config.HTTPS:   # el navegador recordará usar siempre HTTPS
    _CABECERAS_SEGURIDAD.append(("Strict-Transport-Security", "max-age=31536000; includeSubDomains"))


def _leer_cookies(cabecera):
    cookies = SimpleCookie()
    try:
        cookies.load(cabecera or "")
    except Exception:
        return {}
    return {nombre: morsel.value for nombre, morsel in cookies.items()}


class Manejador(BaseHTTPRequestHandler):
    server_version = "VortexClubs"   # sin versión de Python: no se revela qué software exacto corre
    sys_version = ""
    timeout = 30                     # corta conexiones que se quedan colgadas (ataques de conexión lenta)

    def do_GET(self):
        self._atender("GET")

    def do_POST(self):
        self._atender("POST")

    def log_message(self, formato, *args):
        print("[%s] %s" % (self.log_date_time_string(), formato % args))

    # ------------------------------------------------------------------------------------
    def _atender(self, metodo):
        try:
            respuesta = self._procesar(metodo)
        except Exception:   # último recurso: nunca dejar la conexión sin respuesta
            traceback.print_exc()
            respuesta = Respuesta.html("<h1>Error interno del servidor</h1>", 500)
        self._enviar(respuesta)

    def _construir_peticion(self, metodo):
        partes = urlsplit(self.path)
        consulta = {k: v[0] for k, v in parse_qs(partes.query, keep_blank_values=True).items()}
        encabezados = {k.lower(): v for k, v in self.headers.items()}
        p = Peticion(metodo, unquote(partes.path), consulta, _leer_cookies(self.headers.get("Cookie")),
                     self.client_address[0], encabezados)
        if metodo == "POST":
            try:
                largo = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise ErrorHttp(400, "La petición no es válida.")
            if largo < 0:
                raise ErrorHttp(400, "La petición no es válida.")
            if largo > config.LIMITE_CUERPO:
                raise ErrorHttp(413, "El archivo es demasiado grande. Las imágenes pueden pesar hasta 5 MB.")
            cuerpo = self.rfile.read(largo) if largo else b""
            tipo = self.headers.get("Content-Type", "")
            if tipo.startswith("multipart/form-data"):
                p.formulario, p.archivos = formularios.leer_multipart(tipo, cuerpo)
            else:
                p.formulario = formularios.leer_urlencoded(cuerpo)
        crudo = p.cookies.get("aviso")
        if crudo:
            nivel, _, texto = unquote(crudo).partition("|")
            if nivel in ("ok", "error") and texto:
                p.aviso = Fila(nivel=nivel, texto=texto)
        return p

    def _procesar(self, metodo):
        p = None
        try:
            p = self._construir_peticion(metodo)
            if metodo == "GET" and p.ruta.startswith("/estatico/"):
                return self._archivo(config.DIR_ESTATICO, p.ruta[len("/estatico/"):])
            if metodo == "GET" and p.ruta.startswith("/subidas/"):
                nombre = p.ruta[len("/subidas/"):]
                if not _RE_SUBIDA.match(nombre):
                    raise ErrorHttp(404, "No encontramos esa imagen.")
                return self._archivo(config.DIR_SUBIDAS, nombre)

            p.bd = modulo_bd.conectar()
            try:
                p.sesion, p.usuario = seguridad.obtener_sesion(p.bd, p.cookies.get("sesion"))
                if metodo == "POST":
                    seguridad.validar_csrf(p)
                funcion, parametros = enrutador.resolver(metodo, p.ruta)
                respuesta = funcion(p, **parametros)
                p.bd.commit()
                return respuesta
            except ErrorHttp as e:
                p.bd.rollback()
                return self._pagina_error(p, e.estado, e.mensaje)   # con la base de datos aún abierta
            except Exception:
                p.bd.rollback()
                traceback.print_exc()
                return self._pagina_error(p, 500, "Ocurrió un error inesperado. Inténtalo de nuevo.")
            finally:
                p.bd.close()
        except ErrorHttp as e:   # errores antes de abrir la base de datos (cuerpo enorme, archivo inexistente)
            return self._pagina_error(p, e.estado, e.mensaje)
        except Exception:
            traceback.print_exc()
            return self._pagina_error(p, 500, "Ocurrió un error inesperado. Inténtalo de nuevo.")

    def _pagina_error(self, p, estado, mensaje):
        if p is None:
            return Respuesta.html(f"<h1>Error {estado}</h1>", estado)
        try:
            return vistas.error(p, estado, mensaje)
        except Exception:
            traceback.print_exc()
            return Respuesta.html(f"<h1>Error {estado}</h1><p>{estado}</p>", estado)

    def _archivo(self, carpeta, relativa):
        if "\x00" in relativa:
            raise ErrorHttp(404)
        base = carpeta.resolve()
        destino = (base / relativa).resolve()
        if not destino.is_relative_to(base) or not destino.is_file():
            raise ErrorHttp(404, "No encontramos ese archivo.")
        tipo = _TIPOS_ESTATICOS.get(destino.suffix.lower(), "application/octet-stream")
        r = Respuesta(destino.read_bytes(), 200, tipo)
        r.cabeceras.append(("Cache-Control", "public, max-age=300"))
        return r

    def _enviar(self, r):
        try:
            self.send_response(r.estado)
            cabeceras = r.cabeceras + _CABECERAS_SEGURIDAD
            if not any(n.lower() == "cache-control" for n, _ in r.cabeceras):
                cabeceras.append(("Cache-Control", "no-store"))   # páginas con datos personales: no se guardan en caché
            for nombre, valor in cabeceras:
                self.send_header(nombre, valor)
            self.send_header("Content-Length", str(len(r.cuerpo)))
            self.end_headers()
            self.wfile.write(r.cuerpo)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


def crear_servidor(host="127.0.0.1", puerto=8000):
    return ThreadingHTTPServer((host, puerto), Manejador)


def iniciar(host="127.0.0.1", puerto=8000):
    servidor = crear_servidor(host, puerto)
    print(f"Vortex Club en http://{host}:{puerto}  (Ctrl+C para detener)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()
