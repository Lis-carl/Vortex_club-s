"""Datos iniciales: categorías, cuenta de administración y catálogo oficial de clubes.

No se crean usuarios, publicaciones, anuncios ni eventos de ejemplo: la plataforma arranca vacía
y los clubes quedan sin miembros hasta que los estudiantes se unan y la administración asigne líderes.
"""
from . import config
from .repositorios import usuarios, clubes

CATEGORIAS = [
    "Negocios y emprendimiento", "Académico y debate", "Arte y cultura", "Comunicación y protocolo",
    "Idiomas", "Voluntariado", "Moda e imagen", "Liderazgo estudiantil",
]

# Clubes del afiche «Contactos de clubes, I semestre 2026» (Dirección de Vida Estudiantil).
CLUBES = [
    ("Club Empresarial", "Negocios y emprendimiento"),
    ("Club de Debate", "Académico y debate"),
    ("Voluntariado por el Autismo", "Voluntariado"),
    ("Voluntariado Aldeas Infantiles SOS", "Voluntariado"),
    ("Club de Cine", "Arte y cultura"),
    ("Club de Modelos", "Moda e imagen"),
    ("Club de Lectura", "Arte y cultura"),
    ("Club de Maestros de Ceremonias", "Comunicación y protocolo"),
    ("Club de Edecanes", "Comunicación y protocolo"),
    ("Club Conanca", "Liderazgo estudiantil"),
    ("Club de Traductores", "Idiomas"),
    ("Voluntariado por la Niñez", "Voluntariado"),
    ("Club de Maquillaje", "Moda e imagen"),
    ("Proyección Juvenil UNEN-UAM", "Liderazgo estudiantil"),
]


def datos_base(bd):
    for nombre in CATEGORIAS:
        bd.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
    usuarios.crear(bd, config.ADMIN_CIF, "Administración Vortex", "admin@vortex.local", "Vida Estudiantil",
                   config.ADMIN_CLAVE, rol="admin")
    categoria = {c.nombre: c.id for c in clubes.categorias(bd)}
    for nombre, nombre_categoria in CLUBES:
        clubes.crear(bd, nombre, "", categoria[nombre_categoria], requiere_aprobacion=False)
