"""Pruebas unitarias de las piezas hechas a mano: plantillas, enrutador, seguridad, formularios, utilidades."""
import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import mkdtemp
import atexit
import shutil

from pruebas import base  # noqa: F401  (ajusta el entorno antes de importar vortex)
from vortex import formularios, seguridad, utilidades
from vortex.enrutador import Enrutador
from vortex.nucleo import ErrorHttp
from vortex.plantillas import MotorPlantillas, ErrorPlantilla


def motor_con(archivos):
    carpeta = mkdtemp(prefix="vortex_plantillas_")
    atexit.register(shutil.rmtree, carpeta, ignore_errors=True)
    for nombre, texto in archivos.items():
        ruta = Path(carpeta) / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8")
    return MotorPlantillas(Path(carpeta))


class PruebasPlantillas(unittest.TestCase):
    def test_variable_se_escapa(self):
        m = motor_con({"a.html": "Hola {{ nombre }}"})
        self.assertEqual(m.renderizar("a.html", {"nombre": "<b>x</b> & \"y\""}),
                         "Hola &lt;b&gt;x&lt;/b&gt; &amp; &quot;y&quot;")

    def test_filtro_seguro_no_escapa(self):
        m = motor_con({"a.html": "{{ x | seguro }}"})
        self.assertEqual(m.renderizar("a.html", {"x": "<i>ok</i>"}), "<i>ok</i>")

    def test_saltos_escapa_y_convierte(self):
        m = motor_con({"a.html": "{{ x | saltos }}"})
        self.assertEqual(m.renderizar("a.html", {"x": "<a>\nb"}), "&lt;a&gt;<br>\nb")

    def test_condicionales(self):
        m = motor_con({"a.html": "{% if n > 5 %}grande{% elif n > 2 %}medio{% else %}chico{% endif %}"})
        self.assertEqual([m.renderizar("a.html", {"n": n}) for n in (9, 3, 0)], ["grande", "medio", "chico"])

    def test_for_con_else_y_bucle(self):
        m = motor_con({"a.html": "{% for x in xs %}{{ bucle.indice }}:{{ x }}{% if not bucle.ultimo %},{% endif %}{% else %}vacío{% endfor %}"})
        self.assertEqual(m.renderizar("a.html", {"xs": ["a", "b"]}), "1:a,2:b")
        self.assertEqual(m.renderizar("a.html", {"xs": []}), "vacío")

    def test_herencia_e_include(self):
        m = motor_con({
            "base.html": "[{% block a %}base-a{% endblock %}|{% block b %}base-b{% endblock %}]",
            "hijo.html": '{% extends "base.html" %}{% block a %}hijo-a {% include "p.html" %}{% endblock %}',
            "p.html": "parcial {{ v }}"})
        self.assertEqual(m.renderizar("hijo.html", {"v": 7}), "[hijo-a parcial 7|base-b]")

    def test_set_y_atributos_faltantes(self):
        m = motor_con({"a.html": "{% set y = x + 1 %}{{ y }}-{{ nada.otra }}-{{ d.k }}"})
        from vortex.nucleo import Fila
        self.assertEqual(m.renderizar("a.html", {"x": 1, "d": Fila(k="v")}), "2--v")

    def test_no_permite_funciones_peligrosas(self):
        m = motor_con({"a.html": "{{ open('x') }}{{ __import__('os') }}"})
        self.assertEqual(m.renderizar("a.html", {}), "")   # NameError -> vacío, nunca se ejecuta

    def test_errores_de_sintaxis(self):
        for texto in ("{% if x %}sin cierre", "{% foo %}", "{{ x | inexistente }}", "{{ 1 + }}"):
            m = motor_con({"a.html": texto})
            with self.assertRaises(ErrorPlantilla, msg=texto):
                m.renderizar("a.html", {})

    def test_no_sale_de_la_carpeta(self):
        m = motor_con({"a.html": '{% include "../../etc/passwd" %}'})
        with self.assertRaises(ErrorPlantilla):
            m.renderizar("a.html", {})


class PruebasEnrutador(unittest.TestCase):
    def setUp(self):
        self.e = Enrutador()
        self.e.ruta("GET", "/clubes/<slug>")(lambda p, slug: "club")
        self.e.ruta("GET", "/clubes/solicitar")(lambda p: "solicitar")
        self.e.ruta("POST", "/p/<id>/votar")(lambda p, id: id)

    def test_ruta_fija_gana_a_parametro(self):
        self.assertEqual(self.e.resolver("GET", "/clubes/solicitar")[0](None), "solicitar")
        self.assertEqual(self.e.resolver("GET", "/clubes/ajedrez")[1], {"slug": "ajedrez"})

    def test_id_es_entero(self):
        self.assertEqual(self.e.resolver("POST", "/p/12/votar")[1], {"id": 12})

    def test_404_y_405(self):
        with self.assertRaises(ErrorHttp) as c:
            self.e.resolver("GET", "/nada")
        self.assertEqual(c.exception.estado, 404)
        with self.assertRaises(ErrorHttp) as c:
            self.e.resolver("GET", "/p/1/votar")
        self.assertEqual(c.exception.estado, 405)
        with self.assertRaises(ErrorHttp):
            self.e.resolver("POST", "/p/abc/votar")   # id no numérico


class PruebasSeguridad(unittest.TestCase):
    def test_hash_y_verificacion(self):
        h, sal = seguridad.hash_contrasena("secreto1")
        self.assertTrue(seguridad.verificar_contrasena("secreto1", h, sal))
        self.assertFalse(seguridad.verificar_contrasena("secreto2", h, sal))
        h2, sal2 = seguridad.hash_contrasena("secreto1")
        self.assertNotEqual((h, sal), (h2, sal2))   # sal aleatoria
        self.assertNotIn("secreto1", h)

    def test_limite_de_intentos(self):
        lim = seguridad.LimiteIntentos(maximo=3, ventana=60)
        for _ in range(3):
            self.assertFalse(lim.bloqueado("x"))
            lim.fallo("x")
        self.assertTrue(lim.bloqueado("x"))
        lim.reiniciar("x")
        self.assertFalse(lim.bloqueado("x"))


class PruebasFormularios(unittest.TestCase):
    def test_urlencoded(self):
        self.assertEqual(formularios.leer_urlencoded("a=1&b=h%C3%B3la&c=".encode()), {"a": "1", "b": "hóla", "c": ""})

    def test_multipart(self):
        cuerpo = (b'--X\r\nContent-Disposition: form-data; name="titulo"\r\n\r\nHola\r\n'
                  b'--X\r\nContent-Disposition: form-data; name="imagen"; filename="a.png"\r\n'
                  b'Content-Type: image/png\r\n\r\n\x89PNG\r\n\x1a\n123\r\n--X--\r\n')
        campos, archivos = formularios.leer_multipart("multipart/form-data; boundary=X", cuerpo)
        self.assertEqual(campos, {"titulo": "Hola"})
        self.assertEqual(archivos["imagen"].nombre, "a.png")
        self.assertTrue(archivos["imagen"].datos.startswith(b"\x89PNG"))

    def test_texto_y_entero(self):
        e = formularios.Errores()
        self.assertEqual(formularios.texto({"t": "  hola   mundo "}, e, "t", "El t", 3, 20), "hola mundo")
        formularios.texto({"t": "ab"}, e, "t2", "T", 3, 20)
        formularios.texto({"x": ""}, e, "x", "X")
        self.assertEqual(sorted(e), ["t2", "x"])
        e = formularios.Errores()
        self.assertEqual(formularios.entero({"c": "50"}, e, "c", "C", 1, 100), 50)
        self.assertIsNone(formularios.entero({"c": "0"}, e, "c", "C", 1, 100))
        self.assertIn("c", e)

    def test_firmas_de_imagen(self):
        self.assertEqual(formularios.tipo_imagen(b"\x89PNG\r\n\x1a\nxx"), "png")
        self.assertEqual(formularios.tipo_imagen(b"\xff\xd8\xffxx"), "jpg")
        self.assertEqual(formularios.tipo_imagen(b"GIF89a.."), "gif")
        self.assertEqual(formularios.tipo_imagen(b"RIFF\x00\x00\x00\x00WEBPxx"), "webp")
        self.assertIsNone(formularios.tipo_imagen(b"<script>alert(1)</script>"))


class PruebasUtilidades(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(utilidades.slugify("Club de Ajedrez Ñandú"), "club-de-ajedrez-nandu")
        self.assertEqual(utilidades.slugify("Robótica!!"), "robotica")
        self.assertEqual(utilidades.slugify("solicitar"), "solicitar-club")   # reservado por una ruta
        self.assertEqual(utilidades.slugify("¡¡¡"), "club")

    def test_tiempo_relativo(self):
        f = lambda **k: (datetime.now() - timedelta(**k)).strftime("%Y-%m-%d %H:%M:%S")
        self.assertEqual(utilidades.tiempo_relativo(f(seconds=5)), "hace un momento")
        self.assertEqual(utilidades.tiempo_relativo(f(minutes=5)), "hace 5 min")
        self.assertEqual(utilidades.tiempo_relativo(f(hours=3)), "hace 3 h")
        self.assertEqual(utilidades.tiempo_relativo(f(days=2)), "hace 2 d")

    def test_iniciales_y_fechas(self):
        self.assertEqual(utilidades.iniciales("ana lópez gómez"), "AL")
        self.assertEqual(utilidades.dia("2026-11-08 09:00"), "08")
        self.assertEqual(utilidades.mes("2026-11-08 09:00"), "NOV")
        self.assertEqual(utilidades.fecha_larga("2026-11-08 09:30"), "8 nov 2026, 09:30")


if __name__ == "__main__":
    unittest.main()
