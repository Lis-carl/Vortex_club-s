"""Punto de entrada de Vortex Club.

    python app.py                       # inicia en http://127.0.0.1:8000
    python app.py --puerto 8080         # otro puerto
    python app.py --host 0.0.0.0        # visible para otros equipos de la red local
    python app.py --sin-demo            # primera vez: solo categorías y administrador, sin datos de ejemplo
"""
import argparse
import sys

from vortex import bd, config, servidor


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    analizador = argparse.ArgumentParser(description="Vortex Club - plataforma de clubes universitarios")
    analizador.add_argument("--host", default="127.0.0.1", help="dirección donde escucha (por omisión 127.0.0.1)")
    analizador.add_argument("--puerto", type=int, default=8000, help="puerto (por omisión 8000)")
    analizador.add_argument("--sin-demo", action="store_true", help="no crear datos de ejemplo al crear la base de datos")
    args = analizador.parse_args()

    primera_vez = not config.RUTA_BD.exists()
    bd.inicializar(con_demo=not args.sin_demo)
    if primera_vez:
        print(f"Base de datos creada en {config.RUTA_BD}")
        print(f"Administrador: CIF {config.ADMIN_CIF}  /  clave: {config.ADMIN_CLAVE}")
        if not args.sin_demo:
            print(f"Cuentas de ejemplo: 26010001 a 26010006  /  clave: {config.CLAVE_DEMO}")
    servidor.iniciar(args.host, args.puerto)


if __name__ == "__main__":
    main()
