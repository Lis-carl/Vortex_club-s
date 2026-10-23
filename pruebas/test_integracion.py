"""Pruebas de integración: servidor real + SQLite temporal + cliente HTTP. Cubren los casos de uso del documento 04."""
import re
import sqlite3
import os
import unittest
from datetime import datetime, timedelta

from pruebas.base import PruebaServidor, PNG, Cliente

ANA, LUIS, MARIA, JORGE, SOFIA, CARLOS = (f"2601000{i}" for i in range(1, 7))
ADMIN = "00000001"
FUTURO = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
PASADO = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")


def consulta(sql, *params):
    con = sqlite3.connect(os.environ["VORTEX_BD"])
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


class PruebasAcceso(PruebaServidor):
    def test_paginas_publicas_y_redireccion(self):
        c = self.cliente()
        r = c.get("/")
        self.assertEqual(r.estado, 200)
        self.assertIn("/acceder", r.url)                     # visitante: redirige al acceso
        self.assertIn("Acceder", r.cuerpo)
        self.assertIn("siguiente=%2F", r.url)

    def test_login_correcto_y_cerrar_sesion(self):
        c = self.cliente()
        r = c.entrar(ANA)
        self.assertIn("Robótica", r.cuerpo)                  # menú «Mis clubes»
        r = c.post("/salir")
        self.assertIn("/acceder", r.url)
        self.assertIn("/acceder", c.get("/").url)

    def test_login_incorrecto(self):
        c = self.cliente()
        r = c.post("/acceder", {"cif": ANA, "contrasena": "mala"}, desde="/acceder")
        self.assertEqual(r.estado, 401)
        self.assertIn("CIF o contraseña incorrectos", r.cuerpo)
        r = c.post("/acceder", {"cif": "123", "contrasena": "x"}, desde="/acceder")
        self.assertEqual(r.estado, 401)

    def test_bloqueo_por_intentos_fallidos(self):
        c = self.cliente()
        for _ in range(5):
            c.post("/acceder", {"cif": "99999999", "contrasena": "x"}, desde="/acceder")
        r = c.post("/acceder", {"cif": "99999999", "contrasena": "x"}, desde="/acceder")
        self.assertIn("Demasiados intentos", r.cuerpo)

    def test_csrf_obligatorio(self):
        c = self.cliente(ANA)
        r = c.post("/clubes/ajedrez/unirse", {}, csrf=False)
        self.assertEqual(r.estado, 403)
        r = c.post("/clubes/ajedrez/unirse", {"csrf": "falso"}, csrf=False)
        self.assertEqual(r.estado, 403)
        v = self.cliente()
        r = v.post("/acceder", {"cif": ANA, "contrasena": "demo1234"}, csrf=False)   # sin token
        self.assertEqual(r.estado, 403)

    def test_registro(self):
        c = self.cliente()
        malo = c.post("/registro", {"cif": "12", "nombre": "A", "correo": "abcdef", "contrasena": "1", "confirmar": "2"},
                      desde="/registro")
        self.assertEqual(malo.estado, 400)
        for esperado in ("8 dígitos", "al menos 3", "correo válido", "entre 6 y 128"):
            self.assertIn(esperado, malo.cuerpo)
        ok = c.post("/registro", {"cif": "27000001", "nombre": "Nuevo Usuario", "correo": "NUEVO@vortex.local",
                                  "carrera": "Derecho", "contrasena": "clave123", "confirmar": "clave123"},
                    desde="/registro")
        self.assertEqual(ok.estado, 200)
        self.assertTrue(ok.url.endswith("/clubes"))
        self.assertIn("Bienvenido/a, Nuevo Usuario", ok.cuerpo)
        repetido = self.cliente().post("/registro", {"cif": "27000001", "nombre": "Otro Nombre", "correo": "otro@vortex.local",
                                                     "contrasena": "clave123", "confirmar": "clave123"}, desde="/registro")
        self.assertIn("Ya existe una cuenta con ese CIF", repetido.cuerpo)
        self.assertEqual(consulta("SELECT correo FROM usuarios WHERE cif='27000001'"), [("nuevo@vortex.local",)])
        # contraseña guardada como hash, nunca en claro
        self.assertNotIn("clave123", consulta("SELECT hash_contrasena FROM usuarios WHERE cif='27000001'")[0][0])

    def test_redireccion_abierta_bloqueada(self):
        c = self.cliente()
        r = c.post("/acceder", {"cif": ANA, "contrasena": "demo1234", "siguiente": "//evil.com"}, desde="/acceder")
        self.assertNotIn("evil.com", r.url)

    def test_404_405_y_archivos(self):
        c = self.cliente(ANA)
        self.assertEqual(c.get("/no-existe").estado, 404)
        self.assertEqual(c.get("/clubes/club-inexistente").estado, 404)
        self.assertEqual(self.cliente().get("/estatico/css/estilo.css").estado, 200)
        self.assertEqual(c.get("/estatico/../vortex/config.py").estado, 404)
        self.assertEqual(c.get("/estatico/%2e%2e/vortex/config.py").estado, 404)
        self.assertEqual(c.get("/subidas/../app.py").estado, 404)
        self.assertEqual(c.get("/subidas/nombre-no-valido.png").estado, 404)
        r = Cliente(self.base)
        self.assertEqual(r.post("/salir", {}, csrf=False).estado, 403)   # POST sin token


class PruebasClubes(PruebaServidor):
    def test_catalogo_y_busqueda(self):
        c = self.cliente(ANA)
        r = c.get("/clubes")
        for club in ("Robótica", "Ajedrez", "Voluntariado Solidario", "Fotografía"):
            self.assertIn(club, r.cuerpo)
        r = c.get("/clubes?q=ajedr")
        self.assertIn("Ajedrez", r.cuerpo)
        self.assertNotIn("Fotografía</a>", r.cuerpo.split("rejilla-clubes")[1])
        r = c.get("/clubes?q=%25")      # el comodín % se trata como texto
        self.assertIn("No encontramos clubes", r.cuerpo)

    def test_unirse_club_abierto_y_salir(self):
        c = self.cliente(JORGE)
        r = c.post("/clubes/ajedrez/unirse", desde="/clubes/ajedrez")
        self.assertIn("Te uniste al club", r.cuerpo)
        self.assertEqual(consulta("SELECT m.estado FROM membresias m JOIN usuarios u ON u.id=m.usuario_id "
                                  "JOIN clubes c ON c.id=m.club_id WHERE u.cif=? AND c.slug='ajedrez'", JORGE), [("activa",)])
        r = c.post("/clubes/ajedrez/unirse", desde="/clubes/ajedrez")
        self.assertIn("Ya eres miembro", r.cuerpo)
        r = c.post("/clubes/ajedrez/salir", desde="/clubes/ajedrez")
        self.assertIn("Saliste del club", r.cuerpo)

    def test_unirse_con_aprobacion(self):
        nuevo = self.cliente()
        nuevo.post("/registro", {"cif": "27000002", "nombre": "Pedro Pablo", "correo": "pedro@vortex.local",
                                 "contrasena": "clave123", "confirmar": "clave123"}, desde="/registro")
        r = nuevo.post("/clubes/fotografia/unirse", desde="/clubes/fotografia")   # abierto
        self.assertIn("Te uniste", r.cuerpo)
        r = nuevo.post("/clubes/voluntariado-solidario/unirse", desde="/clubes/voluntariado-solidario")
        self.assertIn("Solicitud enviada", r.cuerpo)
        self.assertIn("Solicitud pendiente", r.cuerpo)
        self.assertEqual(nuevo.get("/clubes/voluntariado-solidario/chat").estado, 403)   # aún no es miembro
        líder = self.cliente(SOFIA)
        r = líder.get("/clubes/voluntariado-solidario/miembros")
        self.assertIn("Pedro Pablo", r.cuerpo)
        mid = consulta("SELECT m.id FROM membresias m JOIN usuarios u ON u.id=m.usuario_id WHERE u.cif='27000002' "
                       "AND m.estado='pendiente'")[0][0]
        # un miembro sin rol no puede resolver solicitudes
        intruso = self.cliente(ANA)
        self.assertEqual(intruso.post(f"/clubes/voluntariado-solidario/miembros/{mid}", {"accion": "aceptar"},
                                      desde="/clubes/voluntariado-solidario/miembros").estado, 403)
        r = líder.post(f"/clubes/voluntariado-solidario/miembros/{mid}", {"accion": "aceptar"},
                       desde="/clubes/voluntariado-solidario/miembros")
        self.assertIn("Solicitud aceptada", r.cuerpo)
        self.assertEqual(nuevo.get("/clubes/voluntariado-solidario/chat").estado, 200)

    def test_gestion_de_roles_y_liderazgo(self):
        lider = self.cliente(CARLOS)         # líder de Ajedrez
        mid_sofia = consulta("SELECT m.id FROM membresias m JOIN usuarios u ON u.id=m.usuario_id JOIN clubes c ON c.id=m.club_id "
                             "WHERE u.cif=? AND c.slug='ajedrez'", SOFIA)[0][0]
        pagina = "/clubes/ajedrez/miembros"
        self.assertIn("Ahora es capitán", lider.post(f"{pagina}/{mid_sofia}", {"accion": "hacer_capitan"}, desde=pagina).cuerpo)
        self.assertIn("Ya no es capitán", lider.post(f"{pagina}/{mid_sofia}", {"accion": "quitar_capitan"}, desde=pagina).cuerpo)
        # el líder no puede salir ni ser modificado
        self.assertIn("transfiere el liderazgo", lider.post("/clubes/ajedrez/salir", desde=pagina).cuerpo)
        mid_carlos = consulta("SELECT m.id FROM membresias m JOIN usuarios u ON u.id=m.usuario_id JOIN clubes c ON c.id=m.club_id "
                              "WHERE u.cif=? AND c.slug='ajedrez'", CARLOS)[0][0]
        self.assertIn("No puedes modificar al líder", lider.post(f"{pagina}/{mid_carlos}", {"accion": "expulsar"}, desde=pagina).cuerpo)
        # un miembro simple no puede cambiar roles
        self.assertEqual(self.cliente(LUIS).post(f"{pagina}/{mid_sofia}", {"accion": "expulsar"}, desde=pagina).estado, 403)
        # transferir liderazgo: siempre queda exactamente un líder
        self.assertIn("Liderazgo transferido", lider.post(f"{pagina}/{mid_sofia}", {"accion": "transferir"}, desde=pagina).cuerpo)
        roles = dict(consulta("SELECT u.cif, m.rol FROM membresias m JOIN usuarios u ON u.id=m.usuario_id JOIN clubes c ON c.id=m.club_id "
                              "WHERE c.slug='ajedrez' AND m.rol IN ('lider','capitan')"))
        self.assertEqual(roles, {SOFIA: "lider", CARLOS: "capitan"})

    def test_editar_club_solo_lider(self):
        self.assertEqual(self.cliente(LUIS).get("/clubes/robotica/editar").estado, 403)   # capitán, no líder
        ana = self.cliente(ANA)
        self.assertEqual(ana.get("/clubes/robotica/editar").estado, 200)
        r = ana.post("/clubes/robotica/editar", {"descripcion": "corta", "categoria": "1"}, desde="/clubes/robotica/editar")
        self.assertEqual(r.estado, 400)
        r = ana.post("/clubes/robotica/editar", {"descripcion": "Nueva descripción del club de robótica.", "categoria": "1",
                                                 "con_aprobacion": "1"}, desde="/clubes/robotica/editar")
        self.assertIn("Cambios guardados", r.cuerpo)
        self.assertIn("Ingreso con aprobación", r.cuerpo)

    def test_solicitar_club_y_aprobacion_del_admin(self):
        u = self.cliente(MARIA)
        r = u.post("/clubes/solicitar", {"nombre": "Ajedrez", "descripcion": "Duplicado de nombre", "categoria": "1"},
                   desde="/clubes/solicitar")
        self.assertIn("Ya existe un club", r.cuerpo)
        r = u.post("/clubes/solicitar", {"nombre": "Cine Club", "descripcion": "Proyecciones y debates de cine.", "categoria": "3",
                                         "justificacion": "No existe uno", "con_aprobacion": "1"}, desde="/clubes/solicitar")
        self.assertIn("Solicitud enviada", r.cuerpo)
        self.assertEqual(u.get("/admin").estado, 403)                     # no es admin
        self.assertEqual(u.post("/admin/solicitudes/1", {"decision": "aprobar"}).estado, 403)
        admin = self.cliente(ADMIN)
        self.assertIn("Cine Club", admin.get("/admin").cuerpo)
        sid = consulta("SELECT id FROM solicitudes_club WHERE nombre='Cine Club'")[0][0]
        r = admin.post(f"/admin/solicitudes/{sid}", {"decision": "aprobar", "comentario": "Bienvenido"}, desde="/admin")
        self.assertIn("Club aprobado", r.cuerpo)
        self.assertEqual(consulta("SELECT m.rol FROM membresias m JOIN usuarios u ON u.id=m.usuario_id JOIN clubes c ON c.id=m.club_id "
                                  "WHERE c.slug='cine-club' AND u.cif=?", MARIA), [("lider",)])
        self.assertEqual(consulta("SELECT requiere_aprobacion FROM clubes WHERE slug='cine-club'"), [(1,)])
        r = admin.post(f"/admin/solicitudes/{sid}", {"decision": "aprobar"}, desde="/admin")   # ya resuelta
        self.assertIn("ya fue resuelta", r.cuerpo)
        self.assertEqual(consulta("SELECT COUNT(*) FROM clubes WHERE slug LIKE 'cine-club%'"), [(1,)])


class PruebasForoYAnuncios(PruebaServidor):
    def test_publicar_con_imagen_y_validaciones(self):
        ana = self.cliente(ANA)
        r = ana.post_multipart("/clubes/robotica/publicar", {"titulo": "ab", "contenido": ""}, {}, desde="/clubes/robotica/publicar")
        self.assertEqual(r.estado, 400)
        self.assertIn("al menos 3", r.cuerpo)
        r = ana.post_multipart("/clubes/robotica/publicar", {"titulo": "Foto del robot", "contenido": "Miren esto"},
                               {"imagen": ("robot.png", PNG)}, desde="/clubes/robotica/publicar")
        self.assertEqual(r.estado, 200)
        self.assertIn("Foto del robot", r.cuerpo)
        nombre = re.search(r'src="/subidas/([0-9a-f]{32}\.png)"', r.cuerpo).group(1)
        img = ana.get("/subidas/" + nombre)
        self.assertEqual(img.estado, 200)
        malo = ana.post_multipart("/clubes/robotica/publicar", {"titulo": "Archivo malo"},
                                  {"imagen": ("x.png", b"<script>alert(1)</script>")}, desde="/clubes/robotica/publicar")
        self.assertEqual(malo.estado, 400)
        self.assertIn("PNG, JPG, GIF o WEBP", malo.cuerpo)
        enorme = ana.post_multipart("/clubes/robotica/publicar", {"titulo": "Imagen enorme"},
                                    {"imagen": ("x.png", PNG + b"0" * (2 * 1024 * 1024))}, desde="/clubes/robotica/publicar")
        self.assertIn("2 MB", enorme.cuerpo)

    def test_no_miembro_no_publica_ni_comenta_pero_si_lee_y_vota(self):
        carlos = self.cliente(CARLOS)         # no es miembro de Robótica
        self.assertEqual(carlos.get("/clubes/robotica").estado, 200)
        self.assertEqual(carlos.get("/clubes/robotica/publicar").estado, 403)
        self.assertEqual(carlos.post_multipart("/clubes/robotica/publicar", {"titulo": "Intruso"}, {}).estado, 403)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE 'Taller de Arduino%'")[0][0]
        self.assertEqual(carlos.get(f"/publicaciones/{pid}").estado, 200)
        self.assertEqual(carlos.post(f"/publicaciones/{pid}/comentar", {"contenido": "hola"}, desde=f"/publicaciones/{pid}").estado, 403)
        r = carlos.post(f"/publicaciones/{pid}/votar", {"valor": "1"}, desde=f"/publicaciones/{pid}", ajax=True)
        self.assertEqual(r.estado, 200)

    def test_xss_se_escapa(self):
        ana = self.cliente(ANA)
        r = ana.post_multipart("/clubes/robotica/publicar", {"titulo": "<script>alert(1)</script>",
                                                              "contenido": "<img src=x onerror=alert(2)>"}, {},
                               desde="/clubes/robotica/publicar")
        self.assertNotIn("<script>alert(1)</script>", r.cuerpo)
        self.assertNotIn("<img src=x", r.cuerpo)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", r.cuerpo)
        self.assertIn("&lt;img src=x onerror=alert(2)&gt;", r.cuerpo)
        pid = int(re.search(r"/publicaciones/(\d+)", r.url).group(1))
        r = ana.post(f"/publicaciones/{pid}/comentar", {"contenido": "<b onmouseover=x>hola</b>"}, desde=f"/publicaciones/{pid}")
        self.assertNotIn("<b onmouseover", r.cuerpo)

    def test_inyeccion_sql_en_busqueda(self):
        r = self.cliente(ANA).get("/clubes?q=%27%20OR%201%3D1%20--")
        self.assertEqual(r.estado, 200)
        self.assertIn("No encontramos clubes", r.cuerpo)
        self.assertEqual(self.cliente(ANA).get("/clubes?cat=1%3BDROP%20TABLE%20usuarios").estado, 200)
        self.assertEqual(consulta("SELECT COUNT(*) FROM usuarios")[0][0] > 0, True)

    def test_comentarios_anidados_votos_y_eliminar(self):
        ana, luis = self.cliente(ANA), self.cliente(LUIS)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE '¿Qué sensor%'")[0][0]
        pag = f"/publicaciones/{pid}"
        r = ana.post(f"{pag}/comentar", {"contenido": "Comentario raíz de prueba"}, desde=pag)
        self.assertIn("Comentario publicado", r.cuerpo)
        raiz = consulta("SELECT id FROM comentarios WHERE contenido='Comentario raíz de prueba'")[0][0]
        luis.post(f"{pag}/comentar", {"contenido": "Respuesta anidada de prueba", "padre_id": str(raiz)}, desde=pag)
        html = luis.get(pag).cuerpo
        self.assertLess(html.index("Comentario raíz de prueba"), html.index("Respuesta anidada de prueba"))
        self.assertRegex(html, r'nivel-1" id="comentario-\d+"')
        # responder a un comentario de otra publicación se rechaza
        otro = consulta("SELECT id FROM comentarios WHERE publicacion_id != ? LIMIT 1", pid)[0][0]
        self.assertEqual(luis.post(f"{pag}/comentar", {"contenido": "x", "padre_id": str(otro)}, desde=pag).estado, 400)
        # votos de comentario
        r = luis.post(f"/comentarios/{raiz}/votar", {"valor": "1"}, desde=pag, ajax=True).json()
        self.assertEqual((r["puntaje"], r["mi_voto"]), (1, 1))
        # eliminar: el autor sí; un miembro ajeno no
        self.assertEqual(self.cliente(MARIA).post(f"/comentarios/{raiz}/eliminar", desde=pag).estado, 403)
        self.assertIn("Comentario eliminado", ana.post(f"/comentarios/{raiz}/eliminar", desde=pag).cuerpo)
        self.assertIn("[comentario eliminado]", ana.get(pag).cuerpo)

    def test_votos_ajax(self):
        luis = self.cliente(LUIS)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE 'Apertura recomendada%'")[0][0]
        pag = f"/publicaciones/{pid}"
        base_puntaje = consulta("SELECT COALESCE(SUM(valor),0) FROM votos_publicacion WHERE publicacion_id=?", pid)[0][0]
        r = luis.post(f"{pag}/votar", {"valor": "1"}, desde=pag, ajax=True).json()
        self.assertEqual((r["puntaje"], r["mi_voto"]), (base_puntaje + 1, 1))
        self.assertIn('id="votos-p-%d"' % pid, r["html"])
        r = luis.post(f"{pag}/votar", {"valor": "1"}, desde=pag, ajax=True).json()          # repetir lo quita
        self.assertEqual((r["puntaje"], r["mi_voto"]), (base_puntaje, None))
        r = luis.post(f"{pag}/votar", {"valor": "-1"}, desde=pag, ajax=True).json()
        self.assertEqual((r["puntaje"], r["mi_voto"]), (base_puntaje - 1, -1))
        r = luis.post(f"{pag}/votar", {"valor": "1"}, desde=pag, ajax=True).json()          # cambiar el sentido
        self.assertEqual((r["puntaje"], r["mi_voto"]), (base_puntaje + 1, 1))               # un solo voto por persona
        self.assertEqual(luis.post(f"{pag}/votar", {"valor": "5"}, desde=pag, ajax=True).estado, 400)

    def test_reacciones(self):
        maria = self.cliente(MARIA)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE 'Taller de Arduino%'")[0][0]
        pag = f"/publicaciones/{pid}"
        r = maria.post(f"{pag}/reaccion", {"tipo": "😂"}, desde=pag, ajax=True).json()
        self.assertEqual(r["conteos"]["😂"], 1)
        self.assertIn("😂", r["mias"])
        r = maria.post(f"{pag}/reaccion", {"tipo": "😂"}, desde=pag, ajax=True).json()      # alternar: se quita
        self.assertEqual(r["conteos"]["😂"], 0)
        self.assertNotIn("😂", r["mias"])
        self.assertEqual(maria.post(f"{pag}/reaccion", {"tipo": "💩"}, desde=pag, ajax=True).estado, 400)
        # varios tipos a la vez, y el mismo emoji de otra persona suma
        maria.post(f"{pag}/reaccion", {"tipo": "🔥"}, desde=pag, ajax=True)
        r = self.cliente(LUIS).post(f"{pag}/reaccion", {"tipo": "🔥"}, desde=pag, ajax=True).json()
        self.assertEqual(r["conteos"]["🔥"], 3)   # Jorge (semilla) + María + Luis

    def test_moderacion_de_publicaciones(self):
        maria = self.cliente(MARIA)
        r = maria.post_multipart("/clubes/robotica/publicar", {"titulo": "Publicación de María"}, {}, desde="/clubes/robotica/publicar")
        pid = int(re.search(r"/publicaciones/(\d+)", r.url).group(1))
        self.assertEqual(self.cliente(JORGE).post(f"/publicaciones/{pid}/eliminar", desde=f"/publicaciones/{pid}").estado, 403)
        self.assertEqual(self.cliente(CARLOS).post(f"/publicaciones/{pid}/eliminar", desde=f"/publicaciones/{pid}").estado, 403)
        self.assertIn("Publicación eliminada", self.cliente(LUIS).post(f"/publicaciones/{pid}/eliminar", desde=f"/publicaciones/{pid}").cuerpo)  # capitán
        self.assertEqual(maria.get(f"/publicaciones/{pid}").estado, 404)

    def test_anuncios_generales_y_de_club(self):
        ana, admin = self.cliente(ANA), self.cliente(ADMIN)
        self.assertIn("Feria de clubes estudiantiles", ana.get("/anuncios").cuerpo)
        self.assertNotIn('action="/anuncios" class="formulario"', ana.get("/anuncios").cuerpo)   # sin formulario
        self.assertEqual(ana.post("/anuncios", {"titulo": "Falso anuncio", "contenido": "x"}, desde="/anuncios").estado, 403)
        r = admin.post("/anuncios", {"titulo": "Mantenimiento programado", "contenido": "El sábado.", "fijado": "1"}, desde="/anuncios")
        self.assertIn("Anuncio publicado", r.cuerpo)
        self.assertIn("Mantenimiento programado", ana.get("/").cuerpo)    # aparece en la barra lateral del inicio
        # anuncios del club: responsables sí, miembro simple no
        self.assertEqual(self.cliente(MARIA).post("/clubes/robotica/anuncios", {"titulo": "Intento", "contenido": "x"},
                                                  desde="/clubes/robotica/anuncios").estado, 403)
        r = self.cliente(LUIS).post("/clubes/robotica/anuncios", {"titulo": "Anuncio del capitán", "contenido": "Hola club"},
                                    desde="/clubes/robotica/anuncios")
        self.assertIn("Anuncio del capitán", r.cuerpo)
        aid = consulta("SELECT id FROM anuncios WHERE titulo='Anuncio del capitán'")[0][0]
        self.assertEqual(self.cliente(MARIA).post(f"/anuncios/{aid}/eliminar").estado, 403)
        self.assertIn("Anuncio eliminado", ana.post(f"/anuncios/{aid}/eliminar", desde="/clubes/robotica/anuncios").cuerpo)

    def test_feed_inicio(self):
        r = self.cliente(ANA).get("/")
        self.assertIn("Taller de Arduino", r.cuerpo)
        self.assertNotIn("Apertura recomendada", r.cuerpo)        # publicación de un club al que Ana no pertenece
        r = self.cliente(ANA).get("/?ver=todos&orden=populares")
        self.assertIn("Apertura recomendada", r.cuerpo)


class PruebasChatYEventos(PruebaServidor):
    def test_chat(self):
        ana, luis = self.cliente(ANA), self.cliente(LUIS)
        self.assertIn("cautín", ana.get("/clubes/robotica/chat").cuerpo)
        ultimo = consulta("SELECT MAX(id) FROM mensajes_chat")[0][0]
        r = luis.post("/clubes/robotica/chat", {"contenido": "Mensaje <b>nuevo</b>"}, desde="/clubes/robotica/chat", ajax=True)
        self.assertEqual(r.json(), {"ok": True})
        mensajes = ana.get(f"/clubes/robotica/chat/mensajes?desde={ultimo}", ajax=True).json()
        self.assertEqual(len(mensajes), 1)
        self.assertEqual((mensajes[0]["autor"], mensajes[0]["contenido"], mensajes[0]["mio"]), ("Luis Pérez", "Mensaje <b>nuevo</b>", False))
        self.assertEqual(ana.get(f"/clubes/robotica/chat/mensajes?desde={mensajes[0]['id']}", ajax=True).json(), [])
        self.assertEqual(luis.post("/clubes/robotica/chat", {"contenido": "   "}, desde="/clubes/robotica/chat", ajax=True).estado, 400)
        self.assertEqual(luis.post("/clubes/robotica/chat", {"contenido": "x" * 1001}, desde="/clubes/robotica/chat", ajax=True).estado, 400)
        # el chat solo es para miembros
        sofia = self.cliente(SOFIA)
        self.assertEqual(sofia.get("/clubes/robotica/chat").estado, 403)
        self.assertEqual(sofia.get("/clubes/robotica/chat/mensajes", ajax=True).estado, 403)
        self.assertEqual(sofia.post("/clubes/robotica/chat", {"contenido": "hola"}, desde="/", ajax=True).estado, 403)
        # el HTML del chat inicial escapa el contenido
        self.assertIn("Mensaje &lt;b&gt;nuevo&lt;/b&gt;", ana.get("/clubes/robotica/chat").cuerpo)

    def _form(self, **extra):
        datos = {"titulo": "Taller de soldadura", "descripcion": "Aprenderemos a soldar componentes.", "fecha_inicio": FUTURO,
                 "lugar": "Laboratorio 2", "cupo": "20", "recursos": "Cautines"}
        datos.update(extra)
        return datos

    def test_proponer_evento_validaciones(self):
        maria = self.cliente(MARIA)
        url = "/clubes/robotica/eventos/proponer"
        r = maria.post(url, self._form(fecha_inicio=PASADO), desde=url)
        self.assertEqual(r.estado, 400)
        self.assertIn("posterior", r.cuerpo)
        self.assertIn("Taller de soldadura", r.cuerpo)         # conserva lo escrito
        for campo, valor in (("cupo", "0"), ("cupo", "abc"), ("titulo", ""), ("lugar", ""), ("fecha_inicio", "mañana")):
            self.assertEqual(maria.post(url, self._form(**{campo: valor}), desde=url).estado, 400, (campo, valor))
        self.assertEqual(self.cliente(SOFIA).post(url, self._form(), desde="/").estado, 403)   # no es miembro de Robótica

    def test_flujo_de_propuesta_y_aprobacion(self):
        maria, luis = self.cliente(MARIA), self.cliente(LUIS)
        url = "/clubes/robotica/eventos/proponer"
        r = maria.post(url, self._form(titulo="Evento para aprobar"), desde=url)
        self.assertIn("Propuesta enviada", r.cuerpo)
        self.assertIn("pendiente", r.cuerpo)                                   # en «Mis propuestas»
        pid = consulta("SELECT id FROM propuestas_evento WHERE titulo='Evento para aprobar'")[0][0]
        self.assertNotIn("Evento para aprobar</h3>", self.cliente(JORGE).get("/clubes/robotica/eventos").cuerpo.split("Próximos eventos")[1].split("Propuestas pendientes")[0])
        # un miembro sin rol no puede revisar
        self.assertEqual(maria.post(f"/propuestas/{pid}/revisar", {"decision": "aprobar"}, desde="/").estado, 403)
        self.assertIn("Evento para aprobar", luis.get("/clubes/robotica/eventos").cuerpo)   # bandeja de pendientes
        self.assertEqual(luis.post(f"/propuestas/{pid}/revisar", {"decision": "quizas"}, desde="/").estado, 400)
        r = luis.post(f"/propuestas/{pid}/revisar", {"decision": "aprobar", "comentario": "Adelante"}, desde="/clubes/robotica/eventos")
        self.assertIn("Propuesta aprobada", r.cuerpo)
        self.assertEqual(consulta("SELECT estado, comentario_revision FROM propuestas_evento WHERE id=?", pid), [("aprobada", "Adelante")])
        self.assertIn("Evento para aprobar", self.cliente(CARLOS).get("/eventos").cuerpo)   # calendario general
        self.assertIn("ya fue revisada", luis.post(f"/propuestas/{pid}/revisar", {"decision": "rechazar"}, desde="/").cuerpo)

    def test_rechazar_propuesta(self):
        maria, ana = self.cliente(MARIA), self.cliente(ANA)
        url = "/clubes/robotica/eventos/proponer"
        maria.post(url, self._form(titulo="Evento para rechazar"), desde=url)
        pid = consulta("SELECT id FROM propuestas_evento WHERE titulo='Evento para rechazar'")[0][0]
        ana.post(f"/propuestas/{pid}/revisar", {"decision": "rechazar", "comentario": "Sin presupuesto"}, desde="/")
        r = maria.get("/clubes/robotica/eventos")
        self.assertIn("rechazada", r.cuerpo)
        self.assertIn("Sin presupuesto", r.cuerpo)
        self.assertNotIn("Evento para rechazar", self.cliente(CARLOS).get("/eventos").cuerpo)

    def test_no_se_aprueba_evento_pasado(self):
        con = sqlite3.connect(os.environ["VORTEX_BD"])
        con.execute("INSERT INTO propuestas_evento (club_id, proponente_id, titulo, descripcion, fecha_inicio, lugar) "
                    "VALUES (1, 3, 'Evento vencido', 'Descripción larga', ?, 'Aula')", (PASADO.replace("T", " "),))
        con.commit()
        pid = con.execute("SELECT id FROM propuestas_evento WHERE titulo='Evento vencido'").fetchone()[0]
        con.close()
        r = self.cliente(ANA).post(f"/propuestas/{pid}/revisar", {"decision": "aprobar"}, desde="/")
        self.assertIn("la fecha del evento ya pasó", r.cuerpo)
        self.assertEqual(consulta("SELECT estado FROM propuestas_evento WHERE id=?", pid), [("pendiente",)])


class PruebasAdmin(PruebaServidor):
    def test_panel_y_cuentas(self):
        admin = self.cliente(ADMIN)
        r = admin.get("/admin")
        self.assertIn("Usuarios", r.cuerpo)
        self.assertIn("Ana López", r.cuerpo)
        uid = consulta("SELECT id FROM usuarios WHERE cif=?", JORGE)[0][0]
        self.assertIn("Cuenta desactivada", admin.post(f"/admin/usuarios/{uid}", {"activo": "0"}, desde="/admin").cuerpo)
        c = self.cliente()
        r = c.post("/acceder", {"cif": JORGE, "contrasena": "demo1234"}, desde="/acceder")
        self.assertIn("desactivada", r.cuerpo)
        self.assertIn("Cuenta reactivada", admin.post(f"/admin/usuarios/{uid}", {"activo": "1"}, desde="/admin").cuerpo)
        self.cliente(JORGE)
        mi_id = consulta("SELECT id FROM usuarios WHERE cif=?", ADMIN)[0][0]
        self.assertIn("No puedes desactivar tu propia cuenta", admin.post(f"/admin/usuarios/{mi_id}", {"activo": "0"}, desde="/admin").cuerpo)

    def test_sesion_se_invalida_al_desactivar(self):
        jorge, admin = self.cliente(JORGE), self.cliente(ADMIN)
        self.assertEqual(jorge.get("/clubes").estado, 200)
        uid = consulta("SELECT id FROM usuarios WHERE cif=?", JORGE)[0][0]
        admin.post(f"/admin/usuarios/{uid}", {"activo": "0"}, desde="/admin")
        self.assertIn("/acceder", jorge.get("/clubes").url)
        admin.post(f"/admin/usuarios/{uid}", {"activo": "1"}, desde="/admin")

    def test_desactivar_club(self):
        admin = self.cliente(ADMIN)
        cid = consulta("SELECT id FROM clubes WHERE slug='fotografia'")[0][0]
        admin.post(f"/admin/clubes/{cid}", {"activo": "0"}, desde="/admin")
        self.assertEqual(self.cliente(MARIA).get("/clubes/fotografia").estado, 404)
        self.assertNotIn("Fotografía</a></h2>", self.cliente(MARIA).get("/clubes").cuerpo)
        admin.post(f"/admin/clubes/{cid}", {"activo": "1"}, desde="/admin")
        self.assertEqual(self.cliente(MARIA).get("/clubes/fotografia").estado, 200)

    def test_perfil(self):
        r = self.cliente(ANA).get(f"/perfil/{LUIS}")
        self.assertIn("Luis Pérez", r.cuerpo)
        self.assertIn("Robótica", r.cuerpo)
        self.assertEqual(self.cliente(ANA).get("/perfil/55555555").estado, 404)


if __name__ == "__main__":
    unittest.main()
