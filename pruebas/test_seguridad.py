"""Pruebas de seguridad: cifrado de contraseñas, sesiones, política de contraseñas, cabeceras y redirecciones."""
import os
import sqlite3
from http.client import HTTPConnection
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, urlopen

from pruebas.base import PruebaServidor, Cliente
from vortex import config, seguridad
from vortex.acceso import destino_seguro

ANA, LUIS = "26010001", "26010002"


def consulta(sql, *params):
    con = sqlite3.connect(os.environ["VORTEX_BD"])
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def ejecutar(sql, *params):
    con = sqlite3.connect(os.environ["VORTEX_BD"])
    try:
        con.execute(sql, params)
        con.commit()
    finally:
        con.close()


def cookie_sesion(cliente):
    jarra = next(h.cookiejar for h in cliente.abridor.handlers if isinstance(h, HTTPCookieProcessor))
    return next(c.value for c in jarra if c.name == "sesion")


class PruebasContrasenas(PruebaServidor):
    def test_hash_con_algoritmo_iteraciones_y_sal(self):
        h, sal = seguridad.hash_contrasena("clave123")
        self.assertTrue(h.startswith(f"pbkdf2_sha256${config.ITERACIONES_PBKDF2}$"))
        self.assertTrue(seguridad.verificar_contrasena("clave123", h, sal))
        self.assertFalse(seguridad.verificar_contrasena("clave124", h, sal))
        self.assertNotEqual(h, seguridad.hash_contrasena("clave123")[0])   # la sal aleatoria cambia el resultado
        self.assertFalse(seguridad.verificar_contrasena("clave123", "basura$x", "zz"))   # datos dañados no truenan

    def test_contrasena_antigua_se_actualiza_al_entrar(self):
        h, sal = seguridad.hash_contrasena("demo1234", iteraciones=config.ITERACIONES_LEGADO)
        ejecutar("UPDATE usuarios SET hash_contrasena=?, sal=? WHERE cif=?", h.split("$")[2], sal, LUIS)   # formato viejo
        Cliente(self.base).entrar(LUIS)
        nuevo = consulta("SELECT hash_contrasena FROM usuarios WHERE cif=?", LUIS)[0][0]
        self.assertTrue(nuevo.startswith("pbkdf2_sha256$"))
        Cliente(self.base).entrar(LUIS)   # y la contraseña sigue funcionando

    def test_politica_de_contrasenas(self):
        c = self.cliente()
        datos = {"cif": "27000009", "nombre": "Persona Nueva", "correo": "nueva@vortex.local"}
        for clave, mensaje in (("abcdefgh", "letras y números"), ("12345678", "letras y números"),
                               ("abc12345", "fácil de adivinar"), ("x27000009", "fácil de adivinar"),
                               ("corta1", "entre 8 y 128")):
            r = c.post("/registro", dict(datos, contrasena=clave, confirmar=clave), desde="/registro")
            self.assertEqual(r.estado, 400, clave)
            self.assertIn(mensaje, r.cuerpo, clave)
        r = c.post("/registro", dict(datos, contrasena="Robot2026", confirmar="Robot2026"), desde="/registro")
        self.assertTrue(r.url.endswith("/clubes"))

    def test_cambiar_contrasena(self):
        ana, otra = self.cliente(ANA), self.cliente(ANA)
        self.assertIn("Cambiar contraseña", ana.get("/").cuerpo)
        mala = ana.post("/perfil/contrasena", {"actual": "equivocada1", "contrasena": "Nueva2026", "confirmar": "Nueva2026"},
                        desde="/perfil/contrasena")
        self.assertEqual(mala.estado, 400)
        self.assertIn("La contraseña actual no es correcta", mala.cuerpo)
        igual = ana.post("/perfil/contrasena", {"actual": "demo1234", "contrasena": "demo1234", "confirmar": "demo1234"},
                         desde="/perfil/contrasena")
        self.assertIn("distinta de la actual", igual.cuerpo)
        ok = ana.post("/perfil/contrasena", {"actual": "demo1234", "contrasena": "Nueva2026", "confirmar": "Nueva2026"},
                      desde="/perfil/contrasena")
        self.assertIn("Contraseña actualizada", ok.cuerpo)
        self.assertIn("Cambiar contraseña", ana.get("/").cuerpo)             # quien la cambió sigue dentro
        self.assertIn("/acceder", otra.get("/").url)                       # el otro dispositivo quedó fuera
        vieja = Cliente(self.base).post("/acceder", {"cif": ANA, "contrasena": "demo1234"}, desde="/acceder")
        self.assertEqual(vieja.estado, 401)
        Cliente(self.base).entrar(ANA, "Nueva2026")

    def test_aviso_de_contrasena_inicial_del_admin(self):
        admin = self.cliente("00000001")
        self.assertIn("aviso-clave", admin.get("/admin").cuerpo)
        admin.post("/perfil/contrasena", {"actual": "admin123", "contrasena": "VidaUam2026", "confirmar": "VidaUam2026"},
                   desde="/perfil/contrasena")
        self.assertNotIn("aviso-clave", admin.get("/admin").cuerpo)


class PruebasSesionesYCabeceras(PruebaServidor):
    def test_la_base_no_guarda_el_token_de_sesion(self):
        ana = self.cliente(ANA)
        token = cookie_sesion(ana)
        guardados = [f[0] for f in consulta("SELECT token FROM sesiones")]
        self.assertNotIn(token, guardados)
        self.assertIn(seguridad._huella(token), guardados)
        ana.post("/salir")
        self.assertNotIn(seguridad._huella(token), [f[0] for f in consulta("SELECT token FROM sesiones")])

    def test_cabeceras_de_seguridad(self):
        r = urlopen(self.base + "/acceder")
        cabeceras = {k.lower(): v for k, v in r.headers.items()}
        self.assertEqual(cabeceras["x-content-type-options"], "nosniff")
        self.assertIn("script-src 'none'", cabeceras["content-security-policy"])
        self.assertIn("form-action 'self'", cabeceras["content-security-policy"])
        self.assertEqual(cabeceras["cache-control"], "no-store")
        self.assertIn("camera=()", cabeceras["permissions-policy"])
        self.assertNotIn("Python", cabeceras["server"])
        self.assertIn("HttpOnly", cabeceras["set-cookie"])
        self.assertIn("SameSite=Lax", cabeceras["set-cookie"])

    def test_peticion_con_largo_invalido(self):
        partes = urlsplit(self.base)
        con = HTTPConnection(partes.hostname, partes.port)
        con.putrequest("POST", "/acceder")
        con.putheader("Content-Length", "-5")
        con.endheaders()
        self.assertEqual(con.getresponse().status, 400)
        con.close()

    def test_limite_por_ip(self):
        try:
            for i in range(seguridad.limite_ip.maximo):
                Cliente(self.base).post("/acceder", {"cif": f"2701{i:04d}", "contrasena": "x"}, desde="/acceder")
            r = Cliente(self.base).post("/acceder", {"cif": ANA, "contrasena": "demo1234"}, desde="/acceder")
            self.assertIn("Demasiados intentos", r.cuerpo)   # bloqueado aunque la contraseña sea correcta
        finally:
            seguridad.limite_ip.limpiar()

    def test_redirecciones_solo_internas(self):
        for malo in ("//sitio.com", "/\\sitio.com", "/\t/sitio.com", "/\n/sitio.com", "https://sitio.com", "/ /x"):
            self.assertEqual(destino_seguro(malo), "/", repr(malo))
        self.assertEqual(destino_seguro("/clubes/robotica?orden=nuevos#pub-1"), "/clubes/robotica?orden=nuevos#pub-1")
