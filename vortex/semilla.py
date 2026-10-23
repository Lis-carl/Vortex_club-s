"""Datos iniciales: categorías y administrador siempre; usuarios y contenido de ejemplo opcionales."""
from datetime import datetime, timedelta

from . import config
from .seguridad import hash_contrasena
from .repositorios import usuarios, clubes, anuncios, foro, chat, eventos

CATEGORIAS = ["Tecnología", "Deportes", "Arte y cultura", "Académico", "Música", "Voluntariado", "Idiomas", "Juegos"]


def datos_base(bd):
    for nombre in CATEGORIAS:
        bd.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
    usuarios.crear(bd, config.ADMIN_CIF, "Administración Vortex", "admin@vortex.local", "Vida Estudiantil",
                   config.ADMIN_CLAVE, rol="admin")


def _hace(**delta):
    return (datetime.now() - timedelta(**delta)).strftime("%Y-%m-%d %H:%M:%S")


def _en(dias, hora):
    return (datetime.now() + timedelta(days=dias)).strftime(f"%Y-%m-%d {hora}")


def datos_demo(bd):
    """Cuentas de ejemplo (clave: demo1234) con clubes, publicaciones, eventos y chat."""
    clave = hash_contrasena(config.CLAVE_DEMO)   # un solo hash reutilizado para acelerar el arranque
    gente = [
        ("26010001", "Ana López", "ana@vortex.local", "Ingeniería en Sistemas"),
        ("26010002", "Luis Pérez", "luis@vortex.local", "Ingeniería en Sistemas"),
        ("26010003", "María Ruiz", "maria@vortex.local", "Diseño Gráfico"),
        ("26010004", "Jorge Díaz", "jorge@vortex.local", "Administración"),
        ("26010005", "Sofía Torres", "sofia@vortex.local", "Psicología"),
        ("26010006", "Carlos Mena", "carlos@vortex.local", "Derecho"),
    ]
    u = {c: usuarios.crear(bd, c, n, e, ca, config.CLAVE_DEMO, hash_previo=clave) for c, n, e, ca in gente}
    ana, luis, maria, jorge, sofia, carlos = (u[c] for c in sorted(u))
    cat = {c.nombre: c.id for c in clubes.categorias(bd)}

    robotica = clubes.crear(bd, "Robótica", "Construimos robots, aprendemos electrónica y competimos en torneos universitarios.",
                            cat["Tecnología"], False)
    ajedrez = clubes.crear(bd, "Ajedrez", "Partidas semanales, análisis de jugadas y torneos relámpago para todos los niveles.",
                           cat["Juegos"], False)
    voluntariado = clubes.crear(bd, "Voluntariado Solidario", "Organizamos jornadas de ayuda comunitaria. Ingreso con aprobación.",
                                cat["Voluntariado"], True)
    foto = clubes.crear(bd, "Fotografía", "Salidas fotográficas, edición y exposiciones en el campus.", cat["Arte y cultura"], False)

    def unir(usuario, club, rol="miembro", estado="activa"):
        bd.execute("INSERT INTO membresias (usuario_id, club_id, rol, estado) VALUES (?, ?, ?, ?)",
                   (usuario, club, rol, estado))

    unir(ana, robotica, "lider"); unir(luis, robotica, "capitan"); unir(maria, robotica); unir(jorge, robotica)
    unir(carlos, ajedrez, "lider"); unir(luis, ajedrez); unir(sofia, ajedrez)
    unir(sofia, voluntariado, "lider"); unir(ana, voluntariado); unir(jorge, voluntariado, estado="pendiente")
    unir(maria, foto, "lider"); unir(sofia, foto, "capitan"); unir(carlos, foto)

    admin = usuarios.por_cif(bd, config.ADMIN_CIF).id
    anuncios.crear(bd, None, admin, "Feria de clubes estudiantiles",
                   "El 15 de noviembre se realizará la feria de clubes en el patio central. ¡Ven a conocer todos los clubes!", True)
    anuncios.crear(bd, None, admin, "Abierta la solicitud para crear nuevos clubes",
                   "Desde esta plataforma puedes pedir la creación de un club. El equipo de Vida Estudiantil la revisará.", False)
    anuncios.crear(bd, robotica, ana, "Reunión de bienvenida",
                   "Este jueves a las 4 pm en el laboratorio 3 presentamos los proyectos del semestre.", True)
    anuncios.crear(bd, ajedrez, carlos, "Torneo relámpago", "El viernes jugamos un torneo de partidas de 5 minutos. Trae tu tablero.", False)

    p1 = foro.crear_publicacion(bd, robotica, ana, "Taller de Arduino este viernes",
                                "Vamos a armar un robot seguidor de línea. Cada equipo recibirá un kit. ¿Quién se apunta?", "")
    p2 = foro.crear_publicacion(bd, robotica, luis, "¿Qué sensor recomiendan para detectar obstáculos?",
                                "Estoy entre el ultrasónico HC-SR04 y un sensor infrarrojo. Mi robot es pequeño.", "")
    p3 = foro.crear_publicacion(bd, ajedrez, carlos, "Apertura recomendada para principiantes",
                                "Les comparto mi lista de aperturas fáciles de recordar: Italiana, Española y Londres.", "")
    p4 = foro.crear_publicacion(bd, foto, maria, "Salida fotográfica al centro histórico",
                                "El sábado temprano para aprovechar la luz dorada. Lleven trípode si tienen.", "")
    bd.execute("UPDATE publicaciones SET creado_en = ? WHERE id = ?", (_hace(hours=5), p1))
    bd.execute("UPDATE publicaciones SET creado_en = ? WHERE id = ?", (_hace(hours=3), p2))
    bd.execute("UPDATE publicaciones SET creado_en = ? WHERE id = ?", (_hace(days=1), p3))
    bd.execute("UPDATE publicaciones SET creado_en = ? WHERE id = ?", (_hace(hours=1), p4))

    foro.crear_comentario(bd, p2, ana, None, "El ultrasónico es más fácil de programar y más preciso a media distancia.")
    foro.crear_comentario(bd, p2, luis, 1, "Gracias, entonces pido el HC-SR04 para el próximo taller.")
    foro.crear_comentario(bd, p1, maria, None, "¡Yo me apunto!")
    foro.crear_comentario(bd, p3, luis, None, "Excelente aporte, la Londres es muy cómoda.")
    for votante in (luis, maria, jorge):
        foro.votar(bd, "publicacion", votante, p1, 1)
    foro.votar(bd, "publicacion", ana, p2, 1)
    foro.votar(bd, "publicacion", sofia, p3, 1)
    foro.votar(bd, "comentario", luis, 1, 1)
    for votante, tipo in ((luis, foro.TIPOS_REACCION[0]), (maria, foro.TIPOS_REACCION[1]), (jorge, foro.TIPOS_REACCION[5])):
        foro.alternar_reaccion(bd, votante, p1, tipo)
    foro.alternar_reaccion(bd, carlos, p4, foro.TIPOS_REACCION[1])

    for autor, texto in ((ana, "Buenas tardes equipo, ¿quién trae el cautín mañana?"), (luis, "Yo lo llevo."),
                         (maria, "Yo llevo las baterías.")):
        chat.enviar(bd, robotica, autor, texto)

    e1 = eventos.proponer(bd, robotica, ana, "Hackatón de robots", "Competencia interna de robots seguidores de línea.",
                          _en(14, "09:00"), "Laboratorio 3", 40, "Kits de Arduino, mesas, cinta adhesiva")
    eventos.revisar(bd, e1, ana, True, "¡Aprobado!")
    e2 = eventos.proponer(bd, ajedrez, carlos, "Torneo relámpago de ajedrez", "Partidas de 5 minutos, sistema suizo.",
                          _en(6, "15:30"), "Sala de estudiantes", 32, "Tableros y relojes")
    eventos.revisar(bd, e2, carlos, True, "")
    eventos.proponer(bd, robotica, maria, "Exposición de proyectos", "Muestra abierta de los proyectos del semestre.",
                     _en(25, "10:00"), "Patio central", None, "Mesas y carteles")
