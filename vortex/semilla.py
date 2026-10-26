"""Datos iniciales: cuenta de administración y catálogo oficial de clubes.

No se crean usuarios, publicaciones, anuncios ni eventos de ejemplo: la plataforma arranca vacía
y los clubes quedan sin miembros hasta que los estudiantes se unan y la administración asigne líderes.
"""
from . import config
from .repositorios import usuarios, clubes

# Clubes del afiche «Contactos de clubes, I semestre 2026» (Dirección de Vida Estudiantil).
CLUBES = [
    "Club Empresarial",
    "Club de Debate",
    "Voluntariado por el Autismo",
    "Voluntariado Aldeas Infantiles SOS",
    "Club de Cine",
    "Club de Modelos",
    "Club de Lectura",
    "Club de Maestros de Ceremonias",
    "Club de Edecanes",
    "Club Conanca",
    "Club de Traductores",
    "Voluntariado por la Niñez",
    "Club de Maquillaje",
    "Proyección Juvenil UNEN-UAM",
    # Agregado a pedido del equipo del proyecto.
    "Club de Esports",
]


def datos_base(bd):
    admin = usuarios.crear(bd, config.ADMIN_CIF, "Administración Vortex", "admin@vortex.local", "Vida Estudiantil",
                           config.ADMIN_CLAVE, rol="admin")
    if config.ADMIN_CLAVE == config.ADMIN_CLAVE_INICIAL:   # se le pedirá cambiarla al entrar
        bd.execute("UPDATE usuarios SET clave_temporal = 1 WHERE id = ?", (admin,))
    asegurar_catalogo(bd)


def asegurar_catalogo(bd):
    """Agrega los clubes oficiales que falten (también en bases creadas antes)."""
    for nombre in CLUBES:
        if not bd.execute("SELECT 1 FROM clubes WHERE nombre = ?", (nombre,)).fetchone():
            clubes.crear(bd, nombre, "", requiere_aprobacion=False)
