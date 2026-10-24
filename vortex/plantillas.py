"""Motor de plantillas propio (sin librerías externas).

Sintaxis:
  {{ expresion }}            imprime el valor escapado (XSS); {{ x | seguro }} lo imprime tal cual
  {{ x | filtro | otro }}    filtros: seguro, saltos, rel, fecha, fecha_corta, dia, mes, hora,
                             iniciales, color, extracto
  {% if c %}..{% elif c %}..{% else %}..{% endif %}
  {% for x in lista %}..{% else %}..{% endfor %}   (dentro: bucle.indice, bucle.primero, bucle.ultimo)
  {% set nombre = expresion %}
  {% extends "base.html" %} / {% block nombre %}..{% endblock %}
  {% include "parciales/x.html" %}
  {# comentario #}
"""
import html as _html
import re

from . import config, utilidades
from .nucleo import Fila


class ErrorPlantilla(Exception):
    pass


class Seguro(str):
    """Texto que ya es HTML confiable y no se vuelve a escapar."""


def escapar(valor):
    if valor is None:
        return ""
    if isinstance(valor, Seguro):
        return valor
    return _html.escape(str(valor), quote=True)


def _saltos(valor):
    texto = _html.escape(str(valor or ""), quote=True)
    return Seguro(texto.replace("\n", "<br>\n"))


FILTROS = {
    "seguro": lambda v: Seguro("" if v is None else str(v)),
    "saltos": _saltos,
    "rel": utilidades.tiempo_relativo,
    "fecha": utilidades.fecha_larga,
    "fecha_corta": utilidades.fecha_corta,
    "dia": utilidades.dia,
    "mes": utilidades.mes,
    "hora": utilidades.hora,
    "iniciales": utilidades.iniciales,
    "color": utilidades.color,
    "extracto": utilidades.extracto,
}

_RE_FOTO = re.compile(r"^[0-9a-f]{32}\.(png|jpg|gif|webp)$")


def avatar(nombre, foto="", clase=""):
    """Foto de perfil si existe; si no, las iniciales sobre un color estable."""
    clases = escapar(("avatar " + (clase or "")).strip())
    if foto and _RE_FOTO.match(str(foto)):
        return Seguro(f'<img class="{clases} avatar-foto" src="/subidas/{foto}" alt="Foto de {escapar(nombre)}">')
    return Seguro(f'<span class="{clases}" style="background:{utilidades.color(nombre)}" aria-hidden="true">'
                  f'{escapar(utilidades.iniciales(nombre))}</span>')


# Entorno restringido para evaluar expresiones: sin open, __import__, eval, etc.
_GLOBALES = {"__builtins__": {"len": len, "str": str, "int": int, "min": min, "max": max,
                              "abs": abs, "sum": sum, "range": range, "bool": bool, "avatar": avatar}}

_PATRON = re.compile(r"(\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\})", re.S)
_PATRON_FOR = re.compile(r"^for\s+(\w+(?:\s*,\s*\w+)*)\s+in\s+(.+)$", re.S)


def _compilar(expresion):
    try:
        return compile(expresion.strip(), "<plantilla>", "eval")
    except SyntaxError as e:
        raise ErrorPlantilla(f"Expresión inválida «{expresion.strip()}»: {e}")


def _evaluar(codigo, contexto):
    try:
        return eval(codigo, _GLOBALES, contexto)
    except (NameError, AttributeError, TypeError):
        return None


def _parsear(texto, nombre):
    partes = _PATRON.split(texto)
    pos = [0]

    def bloque(terminadores):
        nodos = []
        while pos[0] < len(partes):
            parte = partes[pos[0]]
            pos[0] += 1
            if parte.startswith("{{"):
                piezas = parte[2:-2].split("|")
                filtros = [f.strip() for f in piezas[1:]]
                for f in filtros:
                    if f not in FILTROS:
                        raise ErrorPlantilla(f"{nombre}: filtro desconocido «{f}»")
                nodos.append(("expr", _compilar(piezas[0]), filtros))
            elif parte.startswith("{%"):
                interior = parte[2:-2].strip()
                palabra = interior.split(None, 1)[0] if interior else ""
                if palabra in terminadores:
                    return nodos, palabra, interior
                if palabra == "if":
                    ramas, condicion = [], interior[2:].strip()
                    while True:
                        cuerpo, fin, interior_fin = bloque({"elif", "else", "endif"})
                        ramas.append((_compilar(condicion), cuerpo))
                        if fin == "elif":
                            condicion = interior_fin[4:].strip()
                            continue
                        if fin == "else":
                            cuerpo, _, _ = bloque({"endif"})
                            ramas.append((None, cuerpo))
                        break
                    nodos.append(("if", ramas))
                elif palabra == "for":
                    m = _PATRON_FOR.match(interior)
                    if not m:
                        raise ErrorPlantilla(f"{nombre}: «for» mal escrito: {interior}")
                    variables = [v.strip() for v in m.group(1).split(",")]
                    cuerpo, fin, _ = bloque({"else", "endfor"})
                    vacio = []
                    if fin == "else":
                        vacio, _, _ = bloque({"endfor"})
                    nodos.append(("for", variables, _compilar(m.group(2)), cuerpo, vacio))
                elif palabra == "block":
                    cuerpo, _, _ = bloque({"endblock"})
                    nodos.append(("bloque", interior.split(None, 1)[1].strip(), cuerpo))
                elif palabra in ("extends", "include"):
                    archivo = re.search(r"[\"']([^\"']+)[\"']", interior)
                    if not archivo:
                        raise ErrorPlantilla(f"{nombre}: {palabra} sin nombre de archivo")
                    nodos.append(("extiende" if palabra == "extends" else "incluir", archivo.group(1)))
                elif palabra == "set":
                    destino, _, valor = interior[3:].partition("=")
                    nodos.append(("set", destino.strip(), _compilar(valor)))
                else:
                    raise ErrorPlantilla(f"{nombre}: etiqueta desconocida «{interior}»")
            elif parte.startswith("{#"):
                continue
            elif parte:
                nodos.append(("texto", parte))
        if terminadores:
            raise ErrorPlantilla(f"{nombre}: falta cerrar {sorted(terminadores)}")
        return nodos, None, None

    nodos, _, _ = bloque(set())
    extiende = None
    if nodos and nodos[0][0] == "extiende":
        extiende = nodos[0][1]
        nodos = nodos[1:]
    return extiende, nodos


def _recolectar_bloques(nodos, destino):
    for nodo in nodos:
        if nodo[0] == "bloque":
            destino.setdefault(nodo[1], nodo[2])
            _recolectar_bloques(nodo[2], destino)
        elif nodo[0] == "if":
            for _, cuerpo in nodo[1]:
                _recolectar_bloques(cuerpo, destino)
        elif nodo[0] == "for":
            _recolectar_bloques(nodo[3], destino)
            _recolectar_bloques(nodo[4], destino)


class MotorPlantillas:
    def __init__(self, carpeta):
        self.carpeta = carpeta
        self._cache = {}

    def _cargar(self, nombre):
        ruta = (self.carpeta / nombre).resolve()
        if not ruta.is_relative_to(self.carpeta.resolve()) or not ruta.is_file():
            raise ErrorPlantilla(f"No existe la plantilla «{nombre}»")
        marca = ruta.stat().st_mtime_ns
        guardada = self._cache.get(nombre)
        if guardada and guardada[0] == marca:
            return guardada[1], guardada[2]
        extiende, nodos = _parsear(ruta.read_text(encoding="utf-8"), nombre)
        self._cache[nombre] = (marca, extiende, nodos)
        return extiende, nodos

    def renderizar(self, nombre, contexto):
        salida = []
        self._plantilla(nombre, dict(contexto), {}, salida)
        return "".join(salida)

    def _plantilla(self, nombre, contexto, bloques, salida):
        extiende, nodos = self._cargar(nombre)
        if extiende:
            propios = {}
            _recolectar_bloques(nodos, propios)
            for clave, valor in propios.items():
                bloques.setdefault(clave, valor)   # gana la plantilla más derivada
            return self._plantilla(extiende, contexto, bloques, salida)
        self._nodos(nodos, contexto, bloques, salida)

    def _nodos(self, nodos, ctx, bloques, salida):
        for nodo in nodos:
            tipo = nodo[0]
            if tipo == "texto":
                salida.append(nodo[1])
            elif tipo == "expr":
                valor = _evaluar(nodo[1], ctx)
                for filtro in nodo[2]:
                    valor = FILTROS[filtro](valor)
                salida.append(escapar(valor))
            elif tipo == "if":
                for condicion, cuerpo in nodo[1]:
                    if condicion is None or _evaluar(condicion, ctx):
                        self._nodos(cuerpo, ctx, bloques, salida)
                        break
            elif tipo == "for":
                _, variables, codigo, cuerpo, vacio = nodo
                elementos = list(_evaluar(codigo, ctx) or [])
                if not elementos:
                    self._nodos(vacio, ctx, bloques, salida)
                for i, elemento in enumerate(elementos):
                    sub = dict(ctx)
                    if len(variables) == 1:
                        sub[variables[0]] = elemento
                    else:
                        sub.update(zip(variables, elemento))
                    sub["bucle"] = Fila(indice=i + 1, primero=i == 0, ultimo=i == len(elementos) - 1)
                    self._nodos(cuerpo, sub, bloques, salida)
            elif tipo == "bloque":
                self._nodos(bloques.get(nodo[1], nodo[2]), ctx, bloques, salida)
            elif tipo == "incluir":
                self._plantilla(nodo[1], ctx, {}, salida)
            elif tipo == "set":
                ctx[nodo[1]] = _evaluar(nodo[2], ctx)


motor = MotorPlantillas(config.DIR_PLANTILLAS)
