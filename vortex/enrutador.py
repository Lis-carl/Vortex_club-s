"""Enrutador: asocia (método, ruta) con una función controladora."""
import re

from .nucleo import ErrorHttp

# Tipo de cada parámetro <nombre> de una ruta.
_TIPOS = {"slug": r"[a-z0-9-]+", "id": r"\d+", "mid": r"\d+", "cif": r"\d{8}"}
_ENTEROS = {"id", "mid"}


class Enrutador:
    def __init__(self):
        self.rutas = []   # (metodo, patron, regex, funcion)

    def ruta(self, metodo, patron):
        """Decorador: @ruta("GET", "/clubes/<slug>")"""
        regex = re.compile("^" + re.sub(
            r"<(\w+)>", lambda m: f"(?P<{m.group(1)}>{_TIPOS.get(m.group(1), '[^/]+')})", patron) + "$")

        def decorador(funcion):
            self.rutas.append((metodo, patron, regex, funcion))
            # Las rutas fijas (sin parámetros) se prueban antes: /clubes/solicitar gana a /clubes/<slug>.
            self.rutas.sort(key=lambda r: "<" in r[1])
            return funcion
        return decorador

    def resolver(self, metodo, ruta):
        """Devuelve (funcion, parametros) o lanza ErrorHttp 404/405."""
        otro_metodo = False
        for m, _, regex, funcion in self.rutas:
            coincidencia = regex.match(ruta)
            if not coincidencia:
                continue
            if m != metodo:
                otro_metodo = True
                continue
            parametros = {k: (int(v) if k in _ENTEROS else v) for k, v in coincidencia.groupdict().items()}
            return funcion, parametros
        raise ErrorHttp(405 if otro_metodo else 404,
                        "Método no permitido." if otro_metodo else "No encontramos esa página.")


enrutador = Enrutador()
ruta = enrutador.ruta
