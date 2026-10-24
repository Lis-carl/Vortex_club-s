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


def puntaje(publicacion_id):
    return consulta("SELECT COALESCE(SUM(valor), 0) FROM votos_publicacion WHERE publicacion_id=?", publicacion_id)[0][0]


def mi_voto(tabla, columna, objetivo_id, cif):
    fila = consulta(f"SELECT v.valor FROM {tabla} v JOIN usuarios u ON u.id=v.usuario_id WHERE v.{columna}=? AND u.cif=?",
                    objetivo_id, cif)
    return fila[0][0] if fila else None


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
    def test_catalogo_sin_buscador_ni_filtro(self):
        r = self.cliente(ANA).get("/clubes")
        for club in ("Robótica", "Ajedrez", "Voluntariado Solidario", "Fotografía", "Club de Esports"):
            self.assertIn(club, r.cuerpo)
        self.assertNotIn('name="q"', r.cuerpo)
        self.assertNotIn('name="cat"', r.cuerpo)

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

    def test_editar_club_lider_y_capitan(self):
        self.assertEqual(self.cliente(LUIS).get("/clubes/robotica/editar").estado, 200)    # el capitán también edita
        self.assertEqual(self.cliente(MARIA).get("/clubes/robotica/editar").estado, 403)   # miembro simple de Robótica
        ana = self.cliente(ANA)
        self.assertEqual(ana.get("/clubes/robotica/editar").estado, 200)
        r = ana.post("/clubes/robotica/editar", {"descripcion": "corta"}, desde="/clubes/robotica/editar")
        self.assertEqual(r.estado, 400)
        r = ana.post("/clubes/robotica/editar", {"descripcion": "Nueva descripción del club de robótica.",
                                                 "con_aprobacion": "1"}, desde="/clubes/robotica/editar")
        self.assertIn("Cambios guardados", r.cuerpo)
        self.assertIn("Ingreso con aprobación", r.cuerpo)

    def test_solicitar_club_y_aprobacion_del_admin(self):
        u = self.cliente(MARIA)
        r = u.post("/clubes/solicitar", {"nombre": "Ajedrez", "descripcion": "Duplicado de nombre"},
                   desde="/clubes/solicitar")
        self.assertIn("Ya existe un club", r.cuerpo)
        r = u.post("/clubes/solicitar", {"nombre": "Cine Club", "descripcion": "Proyecciones y debates de cine.",
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
                                    {"imagen": ("x.png", PNG + b"0" * (5 * 1024 * 1024))}, desde="/clubes/robotica/publicar")
        self.assertIn("5 MB", enorme.cuerpo)

    def test_no_miembro_no_publica_ni_comenta_pero_si_lee_y_vota(self):
        carlos = self.cliente(CARLOS)         # no es miembro de Robótica
        self.assertEqual(carlos.get("/clubes/robotica").estado, 200)
        self.assertEqual(carlos.get("/clubes/robotica/publicar").estado, 403)
        self.assertEqual(carlos.post_multipart("/clubes/robotica/publicar", {"titulo": "Intruso"}, {}).estado, 403)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE 'Taller de Arduino%'")[0][0]
        self.assertEqual(carlos.get(f"/publicaciones/{pid}").estado, 200)
        self.assertEqual(carlos.post(f"/publicaciones/{pid}/comentar", {"contenido": "hola"}, desde=f"/publicaciones/{pid}").estado, 403)
        r = carlos.post(f"/publicaciones/{pid}/votar", {"valor": "1", "siguiente": f"/publicaciones/{pid}#pub-{pid}"},
                        desde=f"/publicaciones/{pid}")
        self.assertEqual(r.estado, 200)
        self.assertTrue(r.url.endswith(f"/publicaciones/{pid}#pub-{pid}") or r.url.endswith(f"/publicaciones/{pid}"))
        self.assertEqual(mi_voto("votos_publicacion", "publicacion_id", pid, CARLOS), 1)

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

    def test_inyeccion_sql_en_parametros(self):
        r = self.cliente(ANA).get("/?ver=%27%20OR%201%3D1%20--&orden=x%3BDROP%20TABLE%20usuarios")
        self.assertEqual(r.estado, 200)
        self.assertEqual(self.cliente(ANA).get("/eventos?mes=1%3BDROP%20TABLE%20usuarios").estado, 200)
        self.assertTrue(consulta("SELECT COUNT(*) FROM usuarios")[0][0] > 0)

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
        luis.post(f"/comentarios/{raiz}/votar", {"valor": "1"}, desde=pag)
        self.assertEqual(mi_voto("votos_comentario", "comentario_id", raiz, LUIS), 1)
        # eliminar: el autor sí; un miembro ajeno no
        self.assertEqual(self.cliente(MARIA).post(f"/comentarios/{raiz}/eliminar", desde=pag).estado, 403)
        self.assertIn("Comentario eliminado", ana.post(f"/comentarios/{raiz}/eliminar", desde=pag).cuerpo)
        self.assertIn('class="comentario-texto eliminado"', ana.get(pag).cuerpo)

    def test_votos(self):
        luis = self.cliente(LUIS)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE 'Apertura recomendada%'")[0][0]
        pag = f"/publicaciones/{pid}"
        base_puntaje = puntaje(pid)
        r = luis.post(f"{pag}/votar", {"valor": "1", "siguiente": pag + f"#pub-{pid}"}, desde=pag)
        self.assertEqual(r.estado, 200)                                   # vuelve a la misma página
        self.assertEqual((puntaje(pid), mi_voto("votos_publicacion", "publicacion_id", pid, LUIS)), (base_puntaje + 1, 1))
        self.assertIn('voto voto-arriba', r.cuerpo)                       # el botón queda marcado
        luis.post(f"{pag}/votar", {"valor": "1"}, desde=pag)              # repetir lo quita
        self.assertEqual((puntaje(pid), mi_voto("votos_publicacion", "publicacion_id", pid, LUIS)), (base_puntaje, None))
        luis.post(f"{pag}/votar", {"valor": "-1"}, desde=pag)
        self.assertEqual((puntaje(pid), mi_voto("votos_publicacion", "publicacion_id", pid, LUIS)), (base_puntaje - 1, -1))
        luis.post(f"{pag}/votar", {"valor": "1"}, desde=pag)              # cambiar el sentido: un solo voto por persona
        self.assertEqual((puntaje(pid), mi_voto("votos_publicacion", "publicacion_id", pid, LUIS)), (base_puntaje + 1, 1))
        self.assertEqual(luis.post(f"{pag}/votar", {"valor": "5"}, desde=pag).estado, 400)

    def test_reacciones(self):
        maria = self.cliente(MARIA)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE 'Taller de Arduino%'")[0][0]
        pag = f"/publicaciones/{pid}"
        conteo = lambda tipo: consulta("SELECT COUNT(*) FROM reacciones WHERE publicacion_id=? AND tipo=?", pid, tipo)[0][0]
        r = maria.post(f"{pag}/reaccion", {"tipo": "😂", "siguiente": pag}, desde=pag)
        self.assertEqual(conteo("😂"), 1)
        self.assertIn("ficha ficha-activa", r.cuerpo)                     # su reacción se ve resaltada
        maria.post(f"{pag}/reaccion", {"tipo": "😂"}, desde=pag)          # alternar: se quita
        self.assertEqual(conteo("😂"), 0)
        self.assertEqual(maria.post(f"{pag}/reaccion", {"tipo": "💩"}, desde=pag).estado, 400)
        # varios tipos a la vez, y el mismo emoji de otra persona suma
        maria.post(f"{pag}/reaccion", {"tipo": "🔥"}, desde=pag)
        self.cliente(LUIS).post(f"{pag}/reaccion", {"tipo": "🔥"}, desde=pag)
        self.assertEqual(conteo("🔥"), 3)   # Jorge (datos de prueba) + María + Luis

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
        pagina = ana.get("/clubes/robotica/chat").cuerpo
        self.assertIn('<iframe class="chat-marco" src="/clubes/robotica/chat/mensajes"', pagina)
        marco = ana.get("/clubes/robotica/chat/mensajes").cuerpo
        self.assertIn('<meta http-equiv="refresh" content="5">', marco)   # se actualiza solo, sin JavaScript
        self.assertIn("cautín", marco)
        r = luis.post("/clubes/robotica/chat", {"contenido": "Mensaje <b>nuevo</b>"}, desde="/clubes/robotica/chat")
        self.assertTrue(r.url.endswith("/clubes/robotica/chat"))
        marco = ana.get("/clubes/robotica/chat/mensajes").cuerpo
        self.assertIn("Mensaje &lt;b&gt;nuevo&lt;/b&gt;", marco)           # escapado
        self.assertLess(marco.index("Mensaje &lt;b&gt;nuevo"), marco.index("cautín"))   # el más nuevo primero (column-reverse)
        self.assertIn('class="mensaje propio"', luis.get("/clubes/robotica/chat/mensajes").cuerpo)
        self.assertIn("El mensaje es obligatorio", luis.post("/clubes/robotica/chat", {"contenido": "   "}, desde="/clubes/robotica/chat").cuerpo)
        self.assertIn("no puede superar 1000", luis.post("/clubes/robotica/chat", {"contenido": "x" * 1001}, desde="/clubes/robotica/chat").cuerpo)
        # el chat solo es para miembros
        sofia = self.cliente(SOFIA)
        self.assertEqual(sofia.get("/clubes/robotica/chat").estado, 403)
        self.assertEqual(sofia.get("/clubes/robotica/chat/mensajes").estado, 403)
        self.assertEqual(sofia.post("/clubes/robotica/chat", {"contenido": "hola"}, desde="/").estado, 403)

    def test_carrusel_inicio(self):
        inicio = self.cliente(MARIA).get("/").cuerpo
        self.assertIn('class="carrusel"', inicio)
        self.assertIn('id="slide-0" class="carrusel-radio" checked', inicio)   # la primera diapositiva es la general
        self.assertIn("Hackatón de robots", inicio)
        self.assertIn("Unirme al evento", inicio)
        self.assertRegex(inicio, r'href="/eventos/\d+">Ver completo</a>')      # abre la página del evento

    def test_publicar_desde_inicio(self):
        maria = self.cliente(MARIA)
        inicio = maria.get("/").cuerpo
        self.assertIn('action="/publicar"', inicio)
        self.assertIn('<option value="robotica">', inicio)
        r = maria.post("/publicar", {"club": "robotica", "titulo": "Busco equipo para la feria", "contenido": "Somos dos."}, desde="/")
        self.assertIn("Publicado en Robótica", r.cuerpo)
        self.assertIn("Busco equipo para la feria", self.cliente(ANA).get("/clubes/robotica").cuerpo)
        self.assertIn("al menos 3", maria.post("/publicar", {"club": "robotica", "titulo": "ab"}, desde="/").cuerpo)
        self.assertEqual(maria.post("/publicar", {"club": "ajedrez", "titulo": "No soy miembro"}, desde="/").estado, 403)

    def test_editar_contenido(self):
        ana, luis, maria = self.cliente(ANA), self.cliente(LUIS), self.cliente(MARIA)
        # publicación: solo su autor la edita y queda marcada como editada
        pid = consulta("SELECT id FROM publicaciones WHERE titulo='Taller de Arduino este viernes'")[0][0]
        self.assertIn(f'href="/publicaciones/{pid}/editar"', ana.get(f"/publicaciones/{pid}").cuerpo)
        self.assertNotIn(f'href="/publicaciones/{pid}/editar"', luis.get(f"/publicaciones/{pid}").cuerpo)
        self.assertEqual(luis.get(f"/publicaciones/{pid}/editar").estado, 403)
        r = ana.post(f"/publicaciones/{pid}/editar", {"titulo": "Taller de Arduino el sábado", "contenido": "Cambio de día."},
                     desde=f"/publicaciones/{pid}/editar")
        self.assertIn("Taller de Arduino el sábado", r.cuerpo)
        self.assertIn("· editado", r.cuerpo)
        self.assertIn("al menos 3", ana.post(f"/publicaciones/{pid}/editar", {"titulo": "x"}, desde=f"/publicaciones/{pid}/editar").cuerpo)
        # comentario propio
        luis.post(f"/publicaciones/{pid}/comentar", {"contenido": "Ahí estaré"}, desde=f"/publicaciones/{pid}")
        cid = consulta("SELECT id FROM comentarios WHERE contenido='Ahí estaré'")[0][0]
        self.assertEqual(ana.post(f"/comentarios/{cid}/editar", {"contenido": "hackeado"}, desde=f"/publicaciones/{pid}").estado, 403)
        self.assertIn("Ahí estaré sin falta", luis.post(f"/comentarios/{cid}/editar", {"contenido": "Ahí estaré sin falta"},
                                                         desde=f"/publicaciones/{pid}").cuerpo)
        # anuncio del club: lo editan la líder o el capitán, no un miembro
        aid = consulta("SELECT id FROM anuncios WHERE titulo='Reunión de bienvenida'")[0][0]
        self.assertEqual(maria.post(f"/anuncios/{aid}/editar", {"titulo": "Otro", "contenido": "x"}, desde="/").estado, 403)
        r = luis.post(f"/anuncios/{aid}/editar", {"titulo": "Reunión de bienvenida (aula 5)", "contenido": "Jueves 4 pm.",
                                                 "siguiente": "/clubes/robotica/anuncios"}, desde="/clubes/robotica/anuncios")
        self.assertIn("Reunión de bienvenida (aula 5)", r.cuerpo)
        # mensaje del chat del club y mensaje privado
        luis.post("/clubes/robotica/chat", {"contenido": "Llego tarde"}, desde="/clubes/robotica/chat")
        mid = consulta("SELECT id FROM mensajes_chat WHERE contenido='Llego tarde'")[0][0]
        self.assertIn(f'href="/clubes/robotica/chat/{mid}/editar" target="_top"', luis.get("/clubes/robotica/chat/mensajes").cuerpo)
        self.assertEqual(ana.get(f"/clubes/robotica/chat/{mid}/editar").estado, 403)
        luis.post(f"/clubes/robotica/chat/{mid}/editar", {"contenido": "Llego en 10 minutos"}, desde=f"/clubes/robotica/chat/{mid}/editar")
        self.assertIn("Llego en 10 minutos", ana.get("/clubes/robotica/chat/mensajes").cuerpo)
        ana.post(f"/mensajes/{LUIS}", {"contenido": "Hola Luis"}, desde=f"/mensajes/{LUIS}")
        pm = consulta("SELECT id FROM mensajes_privados WHERE contenido='Hola Luis'")[0][0]
        self.assertEqual(luis.post(f"/mensajes/{LUIS}/{pm}/editar", {"contenido": "x"}, desde="/").estado, 403)
        ana.post(f"/mensajes/{LUIS}/{pm}/editar", {"contenido": "Hola Luis, ¿cómo vas?"}, desde=f"/mensajes/{LUIS}/{pm}/editar")
        self.assertIn("Hola Luis, ¿cómo vas?", luis.get(f"/mensajes/{ANA}/marco").cuerpo)

    def test_panel_de_chats(self):
        ana, luis = self.cliente(ANA), self.cliente(LUIS)
        ana.post(f"/mensajes/{LUIS}", {"contenido": "¿Traes el cautín?"}, desde=f"/mensajes/{LUIS}")
        panel = luis.get("/eventos").cuerpo.split('aria-label="Chats"')[1]
        self.assertIn("¿Traes el cautín?", panel)                         # mensaje reciente en el panel
        self.assertNotIn('action="/clubes/robotica/chat"', panel)         # solo chats privados
        # contestar desde el panel deja al usuario en la misma página
        r = luis.post(f"/mensajes/{ANA}", {"contenido": "Sí, lo llevo", "siguiente": "/eventos"}, desde="/eventos")
        self.assertTrue(r.url.endswith("/eventos"))
        self.assertIn("Mensaje enviado a Ana López", r.cuerpo)
        self.assertIn("Sí, lo llevo", ana.get(f"/mensajes/{LUIS}/marco").cuerpo)
        # limpiar el panel quita los chats de ahí, pero siguen en Mensajes
        r = luis.post("/mensajes/limpiar-panel", {"siguiente": "/eventos"}, desde="/eventos")
        self.assertIn("No hay chats recientes", r.cuerpo.split('aria-label="Chats"')[1])
        self.assertIn(f'href="/mensajes/{ANA}"', luis.get("/mensajes").cuerpo)
        ana.post(f"/mensajes/{LUIS}", {"contenido": "Nuevo mensaje"}, desde=f"/mensajes/{LUIS}")
        self.assertIn("Nuevo mensaje", luis.get("/eventos").cuerpo.split('aria-label="Chats"')[1])   # vuelve con mensajes nuevos

    def test_filtro_del_inicio(self):
        ana = self.cliente(ANA)
        inicio = ana.get("/").cuerpo
        self.assertIn('class="feed-filtro"', inicio)
        self.assertNotIn(">Recientes</a>", inicio)                                   # ya no hay pestañas de orden
        self.assertIn("Taller de Arduino", inicio)
        filtrado = ana.get("/?ver=mis&club=voluntariado-solidario&fecha=todo&orden=nuevos").cuerpo
        self.assertNotIn("Taller de Arduino", filtrado.split('class="lista-publicaciones"')[1])   # solo publicaciones de ese club
        self.assertIn("Filtrando:", filtrado)
        self.assertIn("Taller de Arduino", ana.get("/?ver=mis&club=robotica&fecha=mes").cuerpo)

    def test_pestana_agenda(self):
        ana = self.cliente(ANA)
        self.assertIn('href="/?ver=agenda">Agenda</a>', ana.get("/").cuerpo)
        agenda = ana.get("/?ver=agenda").cuerpo.split('class="feed"')[1]
        self.assertIn('class="feed-agenda"', agenda)
        self.assertIn("Próximos eventos", agenda)
        self.assertIn("Anuncios generales", agenda)
        self.assertNotIn('class="lista-publicaciones"', agenda)

    def test_comentarios_en_el_feed(self):
        maria = self.cliente(MARIA)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE 'Taller de Arduino%'")[0][0]
        inicio = maria.get("/").cuerpo
        bloque = inicio.split(f'id="pub-{pid}"')[1].split('</article>')[0]
        self.assertIn('class="pub-comentarios"', bloque)
        self.assertIn("Únete a la conversación", bloque)
        self.assertIn(f'href="/publicaciones/{pid}#comentarios"', bloque)              # ver todos en el foro
        r = maria.post(f"/publicaciones/{pid}/comentar", {"contenido": "Desde el feed", "siguiente": f"/#pub-{pid}"}, desde="/")
        self.assertIn("Comentario publicado", r.cuerpo)
        self.assertIn("Desde el feed", r.cuerpo.split(f'id="pub-{pid}"')[1].split('</article>')[0])

    def test_pagina_de_evento(self):
        eid = consulta("SELECT id FROM propuestas_evento WHERE titulo='Hackatón de robots'")[0][0]
        maria, ana = self.cliente(MARIA), self.cliente(ANA)
        pagina = maria.get(f"/eventos/{eid}").cuerpo
        self.assertIn("<h1>Hackatón de robots</h1>", pagina)
        self.assertIn("Competencia interna de robots.", pagina)
        self.assertIn("Quiénes asistirán", pagina)
        self.assertNotIn(f'action="/eventos/{eid}/imagen"', pagina)             # María no puede cambiar la portada
        self.assertEqual(maria.post(f"/eventos/{eid}/imagen", {}, desde=f"/eventos/{eid}").estado, 403)
        # la líder sube una portada y aparece en la página
        r = ana.post_multipart(f"/eventos/{eid}/imagen", {}, {"imagen": ("portada.png", PNG)}, desde=f"/eventos/{eid}")
        self.assertIn("Imagen del evento actualizada", r.cuerpo)
        self.assertRegex(ana.get(f"/eventos/{eid}").cuerpo, r'<img src="/subidas/[0-9a-f]{32}\.png"')
        self.assertEqual(maria.get("/eventos/99999").estado, 404)

    def test_chat_privado(self):
        ana, luis = self.cliente(ANA), self.cliente(LUIS)
        bandeja = ana.get("/mensajes").cuerpo
        self.assertIn(f'href="/mensajes/{LUIS}"', bandeja)          # Luis comparte Robótica con Ana
        self.assertNotIn(f'href="/mensajes/{CARLOS}"', bandeja)     # Carlos no comparte clubes con Ana
        self.assertIn('href="/clubes/robotica/chat"', bandeja)       # acceso a los chats de sus clubes
        self.assertIn(f'href="/mensajes/{LUIS}"', ana.get("/clubes/robotica/miembros").cuerpo)   # botón «Mensaje»
        r = ana.post(f"/mensajes/{LUIS}", {"contenido": "Hola <b>Luis</b>"}, desde=f"/mensajes/{LUIS}")
        self.assertTrue(r.url.endswith(f"/mensajes/{LUIS}"))
        self.assertIn('<span class="contador">1</span>', luis.get("/mensajes").cuerpo)   # sin leer
        marco = luis.get(f"/mensajes/{ANA}/marco").cuerpo
        self.assertIn("Hola &lt;b&gt;Luis&lt;/b&gt;", marco)
        self.assertNotIn('<span class="contador">1</span>', luis.get("/mensajes").cuerpo)   # quedó leído
        self.assertIn('class="mensaje propio"', ana.get(f"/mensajes/{LUIS}/marco").cuerpo)
        # nadie más ve la conversación ni puede escribir a alguien fuera de sus clubes
        self.assertNotIn("Hola &lt;b&gt;Luis", self.cliente(MARIA).get("/mensajes").cuerpo)
        self.assertEqual(ana.get(f"/mensajes/{CARLOS}").estado, 403)
        self.assertEqual(ana.post(f"/mensajes/{CARLOS}", {"contenido": "hola"}, desde="/mensajes").estado, 403)
        self.assertEqual(ana.get(f"/mensajes/{ANA}").estado, 404)
        self.assertIn("El mensaje es obligatorio", ana.post(f"/mensajes/{LUIS}", {"contenido": "  "}, desde=f"/mensajes/{LUIS}").cuerpo)

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
        self.assertNotIn("Evento para aprobar</h3>", self.cliente(JORGE).get("/clubes/robotica/eventos").cuerpo.split("Próximos eventos")[1].split("Propuestas en votación")[0])
        # un miembro sin rol no puede revisar
        self.assertEqual(maria.post(f"/propuestas/{pid}/revisar", {"decision": "aprobar"}, desde="/").estado, 403)
        self.assertIn("Evento para aprobar", luis.get("/clubes/robotica/eventos").cuerpo)   # bandeja de pendientes
        self.assertEqual(luis.post(f"/propuestas/{pid}/revisar", {"decision": "quizas"}, desde="/").estado, 400)
        r = luis.post(f"/propuestas/{pid}/revisar", {"decision": "aprobar", "comentario": "Adelante"}, desde="/clubes/robotica/eventos")
        self.assertIn("Propuesta aprobada", r.cuerpo)
        self.assertEqual(consulta("SELECT estado, comentario_revision FROM propuestas_evento WHERE id=?", pid), [("aprobada", "Adelante")])
        self.assertIn("Evento para aprobar", self.cliente(CARLOS).get(f"/eventos?mes={FUTURO[:7]}").cuerpo)   # calendario
        self.assertIn("Tu propuesta «Evento para aprobar» fue aprobada", maria.get("/notificaciones").cuerpo)
        self.assertIn("Nuevo evento en Robótica: Evento para aprobar", self.cliente(JORGE).get("/notificaciones").cuerpo)
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
        self.assertNotIn("Evento para rechazar", self.cliente(CARLOS).get(f"/eventos?mes={FUTURO[:7]}").cuerpo)

    def test_no_se_aprueba_evento_pasado(self):
        con = sqlite3.connect(os.environ["VORTEX_BD"])
        con.execute("INSERT INTO propuestas_evento (club_id, proponente_id, titulo, descripcion, fecha_inicio, lugar) "
                    "VALUES ((SELECT id FROM clubes WHERE slug='robotica'), (SELECT id FROM usuarios WHERE cif=?), "
                    "'Evento vencido', 'Descripción larga', ?, 'Aula')", (MARIA, PASADO.replace("T", " ")))
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
        self.assertIn('<div class="estadistica"><b>7</b><span>Usuarios</span></div>', r.cuerpo)   # admin + 6 de prueba
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


class PruebasInstalacionLimpia(PruebaServidor):
    """La aplicación real arranca vacía: sin usuarios de ejemplo y con el catálogo oficial de 15 clubes."""
    con_datos_prueba = False

    CLUBES_OFICIALES = [
        "Club Empresarial", "Club de Debate", "Voluntariado por el Autismo", "Voluntariado Aldeas Infantiles SOS",
        "Club de Cine", "Club de Modelos", "Club de Lectura", "Club de Maestros de Ceremonias", "Club de Edecanes",
        "Club Conanca", "Club de Traductores", "Voluntariado por la Niñez", "Club de Maquillaje", "Proyección Juvenil UNEN-UAM",
        "Club de Esports",
    ]

    def _registrar(self, cif, nombre):
        c = self.cliente()
        r = c.post("/registro", {"cif": cif, "nombre": nombre, "correo": f"{cif}@vortex.local",
                                 "contrasena": "clave123", "confirmar": "clave123"}, desde="/registro")
        self.assertEqual(r.estado, 200)
        return c

    def test_a_base_vacia_con_los_clubes_oficiales(self):   # «a»: corre primero en su clase
        self.assertEqual(sorted(n for (n,) in consulta("SELECT nombre FROM clubes")), sorted(self.CLUBES_OFICIALES))
        self.assertEqual(consulta("SELECT COUNT(*) FROM usuarios"), [(1,)])          # solo la administración
        for tabla in ("membresias", "publicaciones", "comentarios", "anuncios", "propuestas_evento", "mensajes_chat"):
            self.assertEqual(consulta(f"SELECT COUNT(*) FROM {tabla}"), [(0,)], tabla)
        c = self._registrar("27100001", "Estudiante Nuevo")
        catalogo = c.get("/clubes").cuerpo
        for nombre in self.CLUBES_OFICIALES:
            self.assertIn(nombre, catalogo)
        self.assertIn("15 clubes disponibles", catalogo)
        self.assertIn("Aún no perteneces a ningún club", c.get("/").cuerpo)
        self.assertIn("Sin asignar", c.get("/clubes/club-de-debate").cuerpo)        # sin líder hasta que la administración lo asigne

    def test_sin_javascript(self):
        c = self._registrar("27100002", "Sin Script")
        for ruta in ("/", "/clubes", "/anuncios", "/eventos", "/clubes/solicitar", "/clubes/club-de-cine",
                     "/clubes/club-de-cine/miembros", "/clubes/club-de-cine/eventos", "/perfil/27100002"):
            cuerpo = c.get(ruta).cuerpo
            self.assertNotIn("<script", cuerpo.lower(), ruta)
            self.assertNotRegex(cuerpo, r"\son[a-z]+=", ruta)                     # sin atributos onclick, onsubmit...
        self.assertNotIn("<script", self.cliente().get("/acceder").cuerpo.lower())
        self.assertEqual(c.get("/estatico/js/app.js").estado, 404)
        from urllib.request import urlopen
        with urlopen(self.base + "/acceder") as r:
            self.assertIn("script-src 'none'", r.headers["Content-Security-Policy"])
        self.assertEqual(c.get("/estatico/img/logo.svg").estado, 200)

    def test_administracion_asigna_lider(self):
        lider1 = self._registrar("27100003", "Primera Líder")
        self._registrar("27100004", "Segundo Líder")
        admin = self.cliente(ADMIN)
        cid = consulta("SELECT id FROM clubes WHERE slug='club-de-debate'")[0][0]
        self.assertIn("No existe una cuenta activa", admin.post(f"/admin/clubes/{cid}/lider", {"cif": "99999999"}, desde="/admin").cuerpo)
        self.assertEqual(lider1.post(f"/admin/clubes/{cid}/lider", {"cif": "27100003"}, desde="/").estado, 403)
        r = admin.post(f"/admin/clubes/{cid}/lider", {"cif": "27100003"}, desde="/admin")
        self.assertIn("Primera Líder es ahora líder de Club de Debate", r.cuerpo)
        self.assertIn(">Configuración<", lider1.get("/clubes/club-de-debate").cuerpo)     # el rol se aplica de inmediato
        self.assertIn("te asignó como líder de Club de Debate", lider1.get("/notificaciones").cuerpo)
        admin.post(f"/admin/clubes/{cid}/lider", {"cif": "27100004"}, desde="/admin")
        roles = dict(consulta("SELECT u.cif, m.rol FROM membresias m JOIN usuarios u ON u.id=m.usuario_id WHERE m.club_id=?", cid))
        self.assertEqual(roles, {"27100003": "miembro", "27100004": "lider"})      # siempre un solo líder


class PruebasRolesYFuncionesEncuesta(PruebaServidor):
    """Rol elegido al iniciar sesión, permisos, solicitudes de capitán y funciones pedidas en la encuesta."""

    def test_rol_determinado_por_la_cuenta(self):
        self.assertNotIn('name="rol"', Cliente(self.base).get("/acceder").cuerpo)   # no se elige el rol
        luis = Cliente(self.base)
        r = luis.entrar(LUIS)
        self.assertTrue(r.url.endswith("/gestion"))                                   # capitán de Robótica
        self.assertIn("Capitán", r.cuerpo)
        self.assertTrue(Cliente(self.base).entrar(ANA).url.endswith("/gestion"))      # líder
        self.assertTrue(Cliente(self.base).entrar(ADMIN).url.endswith("/admin"))      # administración
        jorge = Cliente(self.base)                                                    # estudiante nuevo
        jorge.post("/registro", {"cif": "27200001", "nombre": "Estudiante Común", "correo": "comun@vortex.local",
                                 "contrasena": "clave123", "confirmar": "clave123"}, desde="/registro")
        self.assertEqual(jorge.get("/gestion").estado, 403)
        jorge.post("/clubes/robotica/unirse", desde="/clubes/robotica")
        # Al ser nombrado capitán, el rol cambia sin volver a iniciar sesión.
        mid = consulta("SELECT m.id FROM membresias m JOIN usuarios u ON u.id=m.usuario_id JOIN clubes c ON c.id=m.club_id "
                       "WHERE u.cif='27200001' AND c.slug='robotica'")[0][0]
        self.cliente(ANA).post(f"/clubes/robotica/miembros/{mid}", {"accion": "hacer_capitan"}, desde="/clubes/robotica/miembros")
        self.assertEqual(jorge.get("/gestion").estado, 200)
        self.assertEqual(jorge.get("/clubes/robotica/editar").estado, 200)

    def test_estudiante_no_borra_lo_ajeno(self):
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE '¿Qué sensor%'")[0][0]   # de Luis
        maria = self.cliente(MARIA)                       # líder de Fotografía, miembro simple de Robótica
        self.assertEqual(maria.post(f"/publicaciones/{pid}/eliminar", desde="/").estado, 403)
        self.assertEqual(maria.post("/clubes/robotica/anuncios", {"titulo": "Prueba", "contenido": "x"}, desde="/").estado, 403)
        self.assertNotIn(">Eliminar<", maria.get(f"/publicaciones/{pid}").cuerpo.split('id="comentarios"')[0])

    def test_administracion_tiene_permiso_total(self):
        admin = self.cliente(ADMIN)
        r = admin.post("/clubes/robotica/anuncios", {"titulo": "Aviso de la administración", "contenido": "Hola"},
                       desde="/clubes/robotica/anuncios")
        self.assertIn("Aviso de la administración", r.cuerpo)
        self.assertEqual(admin.get("/clubes/robotica/editar").estado, 200)
        self.assertEqual(admin.get("/clubes/robotica/chat").estado, 200)
        mid = consulta("SELECT m.id FROM membresias m JOIN usuarios u ON u.id=m.usuario_id JOIN clubes c ON c.id=m.club_id "
                       "WHERE u.cif=? AND c.slug='robotica'", JORGE)[0][0]
        self.assertIn("Ahora es capitán", admin.post(f"/clubes/robotica/miembros/{mid}", {"accion": "hacer_capitan"},
                                                     desde="/clubes/robotica/miembros").cuerpo)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE 'Apertura%'")[0][0]
        self.assertIn("Publicación eliminada", admin.post(f"/publicaciones/{pid}/eliminar", desde="/").cuerpo)

    def test_solicitud_de_capitan_aprobada_por_la_administracion(self):
        maria = self.cliente(MARIA)                       # miembro simple de Robótica
        self.assertIn("Solicitar ser capitán", maria.get("/clubes/robotica").cuerpo)
        r = maria.post("/clubes/robotica/solicitar-capitan", {"motivo": "Organizo los talleres"}, desde="/clubes/robotica")
        self.assertIn("La administración la revisará", r.cuerpo)
        self.assertIn("Solicitud de capitán en revisión", r.cuerpo)
        self.assertIn("Ya tienes una solicitud pendiente",
                      maria.post("/clubes/robotica/solicitar-capitan", {}, desde="/clubes/robotica").cuerpo)
        self.assertEqual(self.cliente(SOFIA).post("/clubes/robotica/solicitar-capitan", {}, desde="/").estado, 403)
        admin = self.cliente(ADMIN)
        panel = admin.get("/admin").cuerpo
        self.assertIn("quiere ser capitán de", panel)
        self.assertIn("Organizo los talleres", panel)
        sid = consulta("SELECT id FROM solicitudes_capitan WHERE estado='pendiente'")[0][0]
        self.assertEqual(self.cliente(ANA).post(f"/admin/capitanes/{sid}", {"decision": "aprobar"}, desde="/").estado, 403)
        self.assertIn("Nuevo capitán asignado en Robótica",
                      admin.post(f"/admin/capitanes/{sid}", {"decision": "aprobar"}, desde="/admin").cuerpo)
        self.assertEqual(consulta("SELECT m.rol FROM membresias m JOIN usuarios u ON u.id=m.usuario_id JOIN clubes c "
                                  "ON c.id=m.club_id WHERE u.cif=? AND c.slug='robotica'", MARIA), [("capitan",)])
        self.assertIn("ahora eres capitán de Robótica", maria.get("/notificaciones").cuerpo)

    def test_confirmacion_de_asistencia_y_cupo(self):
        eid = consulta("SELECT id FROM propuestas_evento WHERE titulo='Torneo relámpago de ajedrez'")[0][0]
        con = sqlite3.connect(os.environ["VORTEX_BD"])
        con.execute("UPDATE propuestas_evento SET cupo = 1 WHERE id = ?", (eid,))
        con.commit()
        con.close()
        sofia, luis = self.cliente(SOFIA), self.cliente(LUIS)
        r = sofia.post(f"/eventos/{eid}/asistencia", {"siguiente": "/clubes/ajedrez/eventos"}, desde="/clubes/ajedrez/eventos")
        self.assertIn("Asistencia confirmada", r.cuerpo)
        self.assertIn("Asistirás", r.cuerpo)
        self.assertIn("1 confirmado de 1", r.cuerpo)
        self.assertIn("alcanzó su cupo", luis.post(f"/eventos/{eid}/asistencia", {}, desde="/").cuerpo)
        self.assertIn("Cupo lleno", luis.get("/clubes/ajedrez/eventos").cuerpo)
        lider = self.cliente(CARLOS)
        self.assertIn("Ver asistentes (1)", lider.get("/clubes/ajedrez/eventos").cuerpo)   # el líder ve la lista
        self.assertIn("Cancelaste tu asistencia", sofia.post(f"/eventos/{eid}/asistencia", {}, desde="/").cuerpo)
        self.assertEqual(consulta("SELECT COUNT(*) FROM asistencias WHERE evento_id=?", eid), [(0,)])
        self.assertEqual(sofia.post("/eventos/99999/asistencia", {}, desde="/").estado, 404)

    def test_recordatorio_de_eventos_proximos(self):
        con = sqlite3.connect(os.environ["VORTEX_BD"])
        manana = (datetime.now() + timedelta(hours=20)).strftime("%Y-%m-%d %H:%M")
        con.execute("UPDATE propuestas_evento SET fecha_inicio = ? WHERE titulo='Hackatón de robots'", (manana,))
        con.commit()
        con.close()
        eid = consulta("SELECT id FROM propuestas_evento WHERE titulo='Hackatón de robots'")[0][0]
        maria = self.cliente(MARIA)
        self.assertNotIn('class="recordatorio"', maria.get("/").cuerpo)
        maria.post(f"/eventos/{eid}/asistencia", {}, desde="/")
        inicio = maria.get("/").cuerpo
        self.assertIn('class="recordatorio"', inicio)
        self.assertIn("Hackatón de robots", inicio.split('class="recordatorio"')[1][:600])
        # queda guardado una sola vez en Notificaciones; al leerlo, la franja del inicio desaparece
        self.assertIn("Recordatorio: «Hackatón de robots»", maria.get("/notificaciones").cuerpo)
        self.assertNotIn('class="recordatorio"', maria.get("/").cuerpo)
        self.assertEqual(consulta("SELECT COUNT(*) FROM notificaciones WHERE texto LIKE 'Recordatorio: «Hackatón%'"), [(1,)])

    def test_notificaciones(self):
        maria = self.cliente(MARIA)
        maria.get("/notificaciones")                      # deja todo leído
        self.cliente(ANA).post("/clubes/robotica/anuncios", {"titulo": "Cambio de aula", "contenido": "Ahora en el lab 5"},
                               desde="/clubes/robotica/anuncios")
        inicio = maria.get("/").cuerpo
        self.assertIn('class="campana-numero">1<', inicio)
        # el panel de la campana muestra la notificación y permite marcarlas como leídas sin abrir la bandeja
        panel = inicio.split('class="notif-panel"')[1]
        self.assertIn("Nuevo anuncio en Robótica: Cambio de aula", panel)
        self.assertIn("Ver notificación completa", panel)
        self.assertNotIn("campana-numero", maria.post("/notificaciones/leidas", {"siguiente": "/"}, desde="/").cuerpo)
        self.cliente(ANA).post("/clubes/robotica/anuncios", {"titulo": "Otro cambio", "contenido": "Lab 6"}, desde="/clubes/robotica/anuncios")
        nid = consulta("SELECT id FROM notificaciones WHERE texto LIKE '%Otro cambio' AND usuario_id=(SELECT id FROM usuarios WHERE cif=?)", MARIA)[0][0]
        self.assertIn(f'action="/notificaciones/{nid}/quitar"', maria.get("/").cuerpo)
        bandeja = maria.get("/notificaciones").cuerpo
        self.assertIn("Nuevo anuncio en Robótica: Otro cambio", bandeja)
        self.assertIn('class="nueva"', bandeja)
        self.assertNotIn("campana-numero", maria.get("/").cuerpo)   # al abrir la bandeja quedan leídas
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE 'Taller de Arduino%'")[0][0]
        self.cliente(JORGE).post(f"/publicaciones/{pid}/comentar", {"contenido": "Me apunto también"}, desde="/")
        self.assertIn("Jorge Díaz comentó tu publicación", self.cliente(ANA).get("/notificaciones").cuerpo)
        # quitar una notificación y luego todas desde el panel
        ana = self.cliente(ANA)
        nid = consulta("SELECT id FROM notificaciones WHERE texto LIKE 'Jorge Díaz comentó%'")[0][0]
        r = ana.post(f"/notificaciones/{nid}/quitar", {"siguiente": "/"}, desde="/")
        self.assertNotIn(f'/notificaciones/{nid}/quitar', r.cuerpo)                      # ya no está en el panel
        self.assertIn("Jorge Díaz comentó tu publicación", ana.get("/notificaciones").cuerpo)   # pero sí en la página
        r = ana.post("/notificaciones/limpiar", {"siguiente": "/"}, desde="/")
        self.assertIn("No hay notificaciones nuevas en el panel", r.cuerpo.split('class="notif-panel"')[1])
        self.assertIn("Jorge Díaz comentó tu publicación", ana.get("/notificaciones").cuerpo)

    def test_calendario_y_sin_puntos(self):
        mes = consulta("SELECT substr(fecha_inicio, 1, 7) FROM propuestas_evento WHERE titulo='Torneo relámpago de ajedrez'")[0][0]
        r = self.cliente(SOFIA).get(f"/eventos?mes={mes}")
        self.assertIn('class="calendario-rejilla"', r.cuerpo)
        self.assertIn("Torneo relámpago de ajedrez", r.cuerpo)
        self.assertEqual(self.cliente(SOFIA).get("/eventos?mes=2026-99").estado, 200)   # mes inválido: usa el actual
        perfil = self.cliente(SOFIA).get(f"/perfil/{ANA}").cuerpo
        self.assertNotIn("puntos", perfil)                          # se retiró el sistema de puntos y niveles
        self.assertNotIn("Más participativos", self.cliente(SOFIA).get("/").cuerpo)

    def test_sin_buscador_en_la_cabecera(self):
        inicio = self.cliente(ANA).get("/").cuerpo
        self.assertNotIn('class="buscador"', inicio)
        self.assertNotIn('name="q"', inicio)
        self.assertNotIn("lema-cabecera", inicio)            # sin texto en cursiva en la barra superior
        self.assertIn("Universidad Americana (UAM)", inicio)


class PruebasFotoDePerfil(PruebaServidor):
    def test_cambiar_y_quitar_foto(self):
        luis = self.cliente(LUIS)
        self.assertIn("Cambiar foto", luis.get(f"/perfil/{LUIS}").cuerpo)
        self.assertNotIn("Cambiar foto", luis.get(f"/perfil/{ANA}").cuerpo)          # solo en tu propio perfil
        malo = luis.post_multipart("/perfil/foto", {}, {"foto": ("x.png", b"<html>no es imagen</html>")}, desde=f"/perfil/{LUIS}")
        self.assertIn("PNG, JPG, GIF o WEBP", malo.cuerpo)
        r = luis.post_multipart("/perfil/foto", {}, {"foto": ("yo.png", PNG)}, desde=f"/perfil/{LUIS}")
        self.assertIn("Foto de perfil actualizada", r.cuerpo)
        foto = consulta("SELECT foto FROM usuarios WHERE cif=?", LUIS)[0][0]
        self.assertRegex(foto, r"^[0-9a-f]{32}\.png$")
        self.assertIn(f'src="/subidas/{foto}"', r.cuerpo)
        self.assertEqual(luis.get(f"/subidas/{foto}").estado, 200)
        pid = consulta("SELECT id FROM publicaciones WHERE titulo LIKE '¿Qué sensor%'")[0][0]      # publicación de Luis
        self.assertIn(f'src="/subidas/{foto}"', self.cliente(ANA).get(f"/publicaciones/{pid}").cuerpo)
        r = luis.post_multipart("/perfil/foto", {}, {"foto": ("otra.png", PNG)}, desde=f"/perfil/{LUIS}")
        nueva = consulta("SELECT foto FROM usuarios WHERE cif=?", LUIS)[0][0]
        self.assertNotEqual(nueva, foto)
        self.assertEqual(luis.get(f"/subidas/{foto}").estado, 404)                # la anterior se borra
        r = luis.post("/perfil/foto/quitar", desde=f"/perfil/{LUIS}")
        self.assertIn("Quitaste tu foto de perfil", r.cuerpo)
        self.assertEqual(consulta("SELECT foto FROM usuarios WHERE cif=?", LUIS), [("",)])


class PruebasVotacionDePropuestas(PruebaServidor):
    def test_propuesta_aprobada_por_votacion(self):
        maria, jorge, luis = self.cliente(MARIA), self.cliente(JORGE), self.cliente(LUIS)
        url = "/clubes/robotica/eventos/proponer"
        futuro = (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%dT%H:%M")
        maria.post(url, {"titulo": "Feria de robots", "descripcion": "Exhibición abierta de robots del club.",
                         "fecha_inicio": futuro, "lugar": "Patio central"}, desde=url)
        pid = consulta("SELECT id FROM propuestas_evento WHERE titulo='Feria de robots'")[0][0]
        pagina = jorge.get("/clubes/robotica/eventos").cuerpo
        self.assertIn("Propuestas en votación", pagina)
        self.assertIn("0</b> de 2 apoyos", pagina)                      # 4 miembros: la mitad son 2
        self.assertIn("No puedes votar tu propia propuesta", maria.post(f"/propuestas/{pid}/votar", {"valor": "1"}, desde="/").cuerpo)
        self.assertEqual(self.cliente(CARLOS).post(f"/propuestas/{pid}/votar", {"valor": "1"}, desde="/").estado, 403)
        r = jorge.post(f"/propuestas/{pid}/votar", {"valor": "1"}, desde="/clubes/robotica/eventos")
        self.assertIn("Faltan 1 apoyo para aprobarla", r.cuerpo)
        self.assertIn("1</b> de 2 apoyos", r.cuerpo)
        self.assertEqual(consulta("SELECT estado FROM propuestas_evento WHERE id=?", pid), [("pendiente",)])
        jorge.post(f"/propuestas/{pid}/votar", {"valor": "1"}, desde="/")   # repetir retira el voto
        self.assertEqual(consulta("SELECT COUNT(*) FROM votos_propuesta WHERE propuesta_id=?", pid), [(0,)])
        jorge.post(f"/propuestas/{pid}/votar", {"valor": "1"}, desde="/")
        r = luis.post(f"/propuestas/{pid}/votar", {"valor": "1"}, desde="/clubes/robotica/eventos")
        self.assertIn("quedó aprobada", r.cuerpo)
        self.assertEqual(consulta("SELECT estado FROM propuestas_evento WHERE id=?", pid), [("aprobada",)])
        self.assertIn("aprobada por votación de los miembros", maria.get("/notificaciones").cuerpo)
        # Ya aprobada, el voto sigue contando para posicionar el evento entre los de todos los clubes.
        self.assertNotIn("ya fue revisada", jorge.post(f"/propuestas/{pid}/votar", {"valor": "1"}, desde="/").cuerpo)

    def test_votos_en_contra_impiden_aprobar(self):
        maria, jorge, luis, ana = self.cliente(MARIA), self.cliente(JORGE), self.cliente(LUIS), self.cliente(ANA)
        url = "/clubes/robotica/eventos/proponer"
        futuro = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%dT%H:%M")
        maria.post(url, {"titulo": "Evento discutido", "descripcion": "Una propuesta con opiniones divididas.",
                         "fecha_inicio": futuro, "lugar": "Aula 1"}, desde=url)
        pid = consulta("SELECT id FROM propuestas_evento WHERE titulo='Evento discutido'")[0][0]
        jorge.post(f"/propuestas/{pid}/votar", {"valor": "-1"}, desde="/")
        ana.post(f"/propuestas/{pid}/votar", {"valor": "-1"}, desde="/")
        luis.post(f"/propuestas/{pid}/votar", {"valor": "1"}, desde="/")
        self.assertEqual(consulta("SELECT estado FROM propuestas_evento WHERE id=?", pid), [("pendiente",)])


class PruebasPosicionDeEventos(PruebaServidor):
    def test_votos_posicionan_los_eventos_de_todos_los_clubes(self):
        hack = consulta("SELECT id, substr(fecha_inicio,1,7) FROM propuestas_evento WHERE titulo='Hackatón de robots'")[0]
        torneo = consulta("SELECT id FROM propuestas_evento WHERE titulo='Torneo relámpago de ajedrez'")[0][0]
        sofia, jorge, maria = self.cliente(SOFIA), self.cliente(JORGE), self.cliente(MARIA)
        # Cualquier estudiante (aunque no sea del club) vota «Me interesa» en un evento aprobado.
        for c in (sofia, jorge, maria):
            r = c.post(f"/propuestas/{hack[0]}/votar", {"valor": "1", "siguiente": "/eventos"}, desde="/eventos")
            self.assertEqual(r.estado, 200)
        jorge.post(f"/propuestas/{torneo}/votar", {"valor": "1"}, desde="/eventos")
        self.assertIn("No puedes votar el evento que tú propusiste",
                      self.cliente(ANA).post(f"/propuestas/{hack[0]}/votar", {"valor": "1"}, desde="/eventos").cuerpo)
        pagina = sofia.get("/eventos").cuerpo
        self.assertIn('class="destacados"', pagina)
        destacados = pagina.split('class="destacados"')[1].split("</section>")[0]
        self.assertLess(destacados.index("Hackatón de robots"), destacados.index("Torneo relámpago"))   # 3 votos > 1
        mes = sofia.get(f"/eventos?mes={hack[1]}&orden=votos").cuerpo
        self.assertIn("Me interesa", mes)
        self.assertIn('class="activo" href="/eventos?mes=', mes)


class PruebasFotoDelClub(PruebaServidor):
    def test_lider_y_capitan_cambian_la_foto_del_club(self):
        luis = self.cliente(LUIS)                                      # capitán de Robótica
        self.assertIn("Foto del club", luis.get("/clubes/robotica/editar").cuerpo)
        self.assertEqual(self.cliente(MARIA).post_multipart("/clubes/robotica/foto", {}, {"foto": ("c.png", PNG)}).estado, 403)
        malo = luis.post_multipart("/clubes/robotica/foto", {}, {"foto": ("c.png", b"texto")}, desde="/clubes/robotica/editar")
        self.assertIn("PNG, JPG, GIF o WEBP", malo.cuerpo)
        r = luis.post_multipart("/clubes/robotica/foto", {}, {"foto": ("club.png", PNG)}, desde="/clubes/robotica/editar")
        self.assertIn("Foto del club actualizada", r.cuerpo)
        foto = consulta("SELECT foto FROM clubes WHERE slug='robotica'")[0][0]
        self.assertRegex(foto, r"^[0-9a-f]{32}\.png$")
        self.assertIn(f'src="/subidas/{foto}"', self.cliente(JORGE).get("/clubes").cuerpo)      # en el catálogo
        self.assertIn("Quitaste la foto del club", self.cliente(ANA).post("/clubes/robotica/foto/quitar", desde="/clubes/robotica/editar").cuerpo)
        self.assertEqual(consulta("SELECT foto FROM clubes WHERE slug='robotica'"), [("",)])
        self.assertEqual(luis.get(f"/subidas/{foto}").estado, 404)                             # el archivo se borra


if __name__ == "__main__":
    unittest.main()
