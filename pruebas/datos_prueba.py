"""Datos ficticios SOLO para las pruebas automáticas (nunca se cargan en la aplicación real).

Crea seis estudiantes (clave demo1234) y cuatro clubes de prueba con líderes, capitanes,
publicaciones, comentarios, votos, reacciones, chat y eventos, para poder ejercitar cada caso de uso.
"""
from datetime import datetime, timedelta

from vortex import config
from vortex.seguridad import hash_contrasena
from vortex.repositorios import usuarios, clubes, anuncios, foro, chat, eventos

CLAVE = "demo1234"


def _hace(**delta):
    return (datetime.now() - timedelta(**delta)).strftime("%Y-%m-%d %H:%M:%S")


def _en(dias, hora):
    return (datetime.now() + timedelta(days=dias)).strftime(f"%Y-%m-%d {hora}")


def cargar(bd):
    clave = hash_contrasena(CLAVE)
    gente = [
        ("26010001", "Ana López", "ana@vortex.local", "Ingeniería en Sistemas"),
        ("26010002", "Luis Pérez", "luis@vortex.local", "Ingeniería en Sistemas"),
        ("26010003", "María Ruiz", "maria@vortex.local", "Diseño Gráfico"),
        ("26010004", "Jorge Díaz", "jorge@vortex.local", "Administración"),
        ("26010005", "Sofía Torres", "sofia@vortex.local", "Psicología"),
        ("26010006", "Carlos Mena", "carlos@vortex.local", "Derecho"),
    ]
    u = {c: usuarios.crear(bd, c, n, e, ca, CLAVE, hash_previo=clave) for c, n, e, ca in gente}
    ana, luis, maria, jorge, sofia, carlos = (u[c] for c in sorted(u))

    robotica = clubes.crear(bd, "Robótica", "Construimos robots y competimos en torneos.", False)
    ajedrez = clubes.crear(bd, "Ajedrez", "Partidas semanales y torneos relámpago.", False)
    voluntariado = clubes.crear(bd, "Voluntariado Solidario", "Jornadas de ayuda comunitaria.", True)
    foto = clubes.crear(bd, "Fotografía", "Salidas fotográficas y exposiciones.", False)

    def unir(usuario, club, rol="miembro", estado="activa"):
        bd.execute("INSERT INTO membresias (usuario_id, club_id, rol, estado) VALUES (?, ?, ?, ?)",
                   (usuario, club, rol, estado))

    for usuario, club, rol, estado in [
        (ana, robotica, "lider", "activa"), (luis, robotica, "capitan", "activa"), (maria, robotica, "miembro", "activa"),
        (jorge, robotica, "miembro", "activa"), (carlos, ajedrez, "lider", "activa"), (luis, ajedrez, "miembro", "activa"),
        (sofia, ajedrez, "miembro", "activa"), (sofia, voluntariado, "lider", "activa"), (ana, voluntariado, "miembro", "activa"),
        (jorge, voluntariado, "miembro", "pendiente"), (maria, foto, "lider", "activa"), (sofia, foto, "capitan", "activa"),
        (carlos, foto, "miembro", "activa"),
    ]:
        unir(usuario, club, rol, estado)

    admin = usuarios.por_cif(bd, config.ADMIN_CIF).id
    anuncios.crear(bd, None, admin, "Feria de clubes estudiantiles", "El 15 de noviembre en el patio central.", True)
    anuncios.crear(bd, robotica, ana, "Reunión de bienvenida", "Jueves a las 4 pm en el laboratorio 3.", True)

    p1 = foro.crear_publicacion(bd, robotica, ana, "Taller de Arduino este viernes", "Armaremos un seguidor de línea.", "")
    p2 = foro.crear_publicacion(bd, robotica, luis, "¿Qué sensor recomiendan para detectar obstáculos?", "Ultrasónico o infrarrojo.", "")
    p3 = foro.crear_publicacion(bd, ajedrez, carlos, "Apertura recomendada para principiantes", "Italiana, Española y Londres.", "")
    p4 = foro.crear_publicacion(bd, foto, maria, "Salida fotográfica al centro histórico", "El sábado temprano.", "")
    for pid, hace in ((p1, {"hours": 5}), (p2, {"hours": 3}), (p3, {"days": 1}), (p4, {"hours": 1})):
        bd.execute("UPDATE publicaciones SET creado_en = ? WHERE id = ?", (_hace(**hace), pid))

    foro.crear_comentario(bd, p2, ana, None, "El ultrasónico es más fácil de programar.")
    foro.crear_comentario(bd, p2, luis, 1, "Gracias, pido el HC-SR04.")
    foro.crear_comentario(bd, p1, maria, None, "Yo me apunto.")
    foro.crear_comentario(bd, p3, luis, None, "La Londres es muy cómoda.")
    for votante in (luis, maria, jorge):
        foro.votar(bd, "publicacion", votante, p1, 1)
    foro.votar(bd, "publicacion", ana, p2, 1)
    foro.votar(bd, "publicacion", sofia, p3, 1)
    foro.votar(bd, "comentario", luis, 1, 1)
    for votante, tipo in ((luis, foro.TIPOS_REACCION[0]), (maria, foro.TIPOS_REACCION[1]), (jorge, foro.TIPOS_REACCION[5])):
        foro.alternar_reaccion(bd, votante, p1, tipo)

    for autor, texto in ((ana, "¿Quién trae el cautín mañana?"), (luis, "Yo lo llevo."), (maria, "Yo llevo las baterías.")):
        chat.enviar(bd, robotica, autor, texto)

    e1 = eventos.proponer(bd, robotica, ana, "Hackatón de robots", "Competencia interna de robots.", _en(14, "09:00"),
                          "Laboratorio 3", 40, "Kits de Arduino")
    eventos.revisar(bd, e1, ana, True, "Aprobado")
    e2 = eventos.proponer(bd, ajedrez, carlos, "Torneo relámpago de ajedrez", "Partidas de 5 minutos.", _en(6, "15:30"),
                          "Sala de estudiantes", 32, "Tableros")
    eventos.revisar(bd, e2, carlos, True, "")
