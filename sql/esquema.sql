-- =====================================================================
-- Vortex Club - Esquema de la base de datos (SQLite 3)
-- Ver docs/05_diseno_base_datos.md para el diagrama entidad-relación.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- D1 Usuarios ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cif             TEXT    NOT NULL UNIQUE CHECK (length(cif) = 8 AND cif NOT GLOB '*[^0-9]*'),
    nombre          TEXT    NOT NULL CHECK (length(nombre) BETWEEN 3 AND 80),
    correo          TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    carrera         TEXT    NOT NULL DEFAULT '',
    hash_contrasena TEXT    NOT NULL,
    sal             TEXT    NOT NULL,
    rol_global      TEXT    NOT NULL DEFAULT 'estudiante' CHECK (rol_global IN ('estudiante', 'admin')),
    activo          INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- D2 Sesiones ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS sesiones (
    token       TEXT    PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    csrf        TEXT    NOT NULL,
    expira_en   TEXT    NOT NULL,
    rol_acceso  TEXT    NOT NULL DEFAULT 'estudiante' CHECK (rol_acceso IN ('estudiante', 'capitan', 'lider', 'admin'))
);

-- D3 Clubes -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS categorias (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS clubes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre              TEXT    NOT NULL UNIQUE COLLATE NOCASE CHECK (length(nombre) BETWEEN 3 AND 60),
    slug                TEXT    NOT NULL UNIQUE,
    descripcion         TEXT    NOT NULL DEFAULT '',
    categoria_id        INTEGER NOT NULL REFERENCES categorias(id),
    requiere_aprobacion INTEGER NOT NULL DEFAULT 0 CHECK (requiere_aprobacion IN (0, 1)),
    estado              TEXT    NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo')),
    creado_en           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- D4 Solicitudes de club ------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes_club (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nombre          TEXT    NOT NULL,
    descripcion     TEXT    NOT NULL,
    categoria_id    INTEGER NOT NULL REFERENCES categorias(id),
    justificacion   TEXT    NOT NULL DEFAULT '',
    requiere_aprobacion INTEGER NOT NULL DEFAULT 0 CHECK (requiere_aprobacion IN (0, 1)),
    estado          TEXT    NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
    revisado_por    INTEGER REFERENCES usuarios(id),
    comentario      TEXT    NOT NULL DEFAULT '',
    club_id         INTEGER REFERENCES clubes(id),
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    revisado_en     TEXT
);

-- D5 Membresías -------------------------------------------------------
CREATE TABLE IF NOT EXISTS membresias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    club_id     INTEGER NOT NULL REFERENCES clubes(id) ON DELETE CASCADE,
    rol         TEXT    NOT NULL DEFAULT 'miembro' CHECK (rol IN ('miembro', 'capitan', 'lider')),
    estado      TEXT    NOT NULL DEFAULT 'activa' CHECK (estado IN ('pendiente', 'activa')),
    unido_en    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (usuario_id, club_id)
);
-- RN-02: como máximo un líder por club.
CREATE UNIQUE INDEX IF NOT EXISTS ux_un_lider_por_club ON membresias(club_id) WHERE rol = 'lider';

-- D6 Anuncios (club_id NULL = anuncio general) --------------------------
CREATE TABLE IF NOT EXISTS anuncios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id     INTEGER REFERENCES clubes(id) ON DELETE CASCADE,
    autor_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo      TEXT    NOT NULL CHECK (length(titulo) BETWEEN 3 AND 150),
    contenido   TEXT    NOT NULL,
    fijado      INTEGER NOT NULL DEFAULT 0 CHECK (fijado IN (0, 1)),
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- D7 Publicaciones y comentarios ----------------------------------------
CREATE TABLE IF NOT EXISTS publicaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id     INTEGER NOT NULL REFERENCES clubes(id) ON DELETE CASCADE,
    autor_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo      TEXT    NOT NULL CHECK (length(titulo) BETWEEN 3 AND 150),
    contenido   TEXT    NOT NULL DEFAULT '',
    imagen      TEXT    NOT NULL DEFAULT '',
    eliminado   INTEGER NOT NULL DEFAULT 0 CHECK (eliminado IN (0, 1)),
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS comentarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    publicacion_id  INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    autor_id        INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    padre_id        INTEGER REFERENCES comentarios(id) ON DELETE CASCADE,
    contenido       TEXT    NOT NULL CHECK (length(contenido) BETWEEN 1 AND 5000),
    eliminado       INTEGER NOT NULL DEFAULT 0 CHECK (eliminado IN (0, 1)),
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- D8 Votos y reacciones ------------------------------------------------
CREATE TABLE IF NOT EXISTS votos_publicacion (
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    publicacion_id  INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    valor           INTEGER NOT NULL CHECK (valor IN (-1, 1)),
    PRIMARY KEY (usuario_id, publicacion_id)
);

CREATE TABLE IF NOT EXISTS votos_comentario (
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    comentario_id   INTEGER NOT NULL REFERENCES comentarios(id) ON DELETE CASCADE,
    valor           INTEGER NOT NULL CHECK (valor IN (-1, 1)),
    PRIMARY KEY (usuario_id, comentario_id)
);

CREATE TABLE IF NOT EXISTS reacciones (
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    publicacion_id  INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    tipo            TEXT    NOT NULL CHECK (tipo IN ('👍', '❤️', '😂', '😮', '😢', '🔥')),
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (usuario_id, publicacion_id, tipo)
);

-- D9 Mensajes de chat ----------------------------------------------------
CREATE TABLE IF NOT EXISTS mensajes_chat (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id     INTEGER NOT NULL REFERENCES clubes(id) ON DELETE CASCADE,
    autor_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    contenido   TEXT    NOT NULL CHECK (length(contenido) BETWEEN 1 AND 1000),
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- D10 Propuestas de evento -----------------------------------------------
CREATE TABLE IF NOT EXISTS propuestas_evento (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id             INTEGER NOT NULL REFERENCES clubes(id) ON DELETE CASCADE,
    proponente_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo              TEXT    NOT NULL CHECK (length(titulo) BETWEEN 3 AND 150),
    descripcion         TEXT    NOT NULL,
    fecha_inicio        TEXT    NOT NULL,
    lugar               TEXT    NOT NULL,
    cupo                INTEGER CHECK (cupo IS NULL OR cupo BETWEEN 1 AND 10000),
    recursos            TEXT    NOT NULL DEFAULT '',
    estado              TEXT    NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
    revisado_por        INTEGER REFERENCES usuarios(id),
    comentario_revision TEXT    NOT NULL DEFAULT '',
    creado_en           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    revisado_en         TEXT
);

-- D11 Asistencias a eventos (confirmación de asistencia) -------------------
CREATE TABLE IF NOT EXISTS asistencias (
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    evento_id   INTEGER NOT NULL REFERENCES propuestas_evento(id) ON DELETE CASCADE,
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (usuario_id, evento_id)
);

-- D12 Notificaciones ------------------------------------------------------
CREATE TABLE IF NOT EXISTS notificaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    texto       TEXT    NOT NULL,
    enlace      TEXT    NOT NULL DEFAULT '/',
    leida       INTEGER NOT NULL DEFAULT 0 CHECK (leida IN (0, 1)),
    creado_en   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- D13 Solicitudes para ser capitán (las aprueba la administración) --------
CREATE TABLE IF NOT EXISTS solicitudes_capitan (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    club_id      INTEGER NOT NULL REFERENCES clubes(id) ON DELETE CASCADE,
    motivo       TEXT    NOT NULL DEFAULT '',
    estado       TEXT    NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
    revisado_por INTEGER REFERENCES usuarios(id),
    comentario   TEXT    NOT NULL DEFAULT '',
    creado_en    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    revisado_en  TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_capitan_pendiente ON solicitudes_capitan(usuario_id, club_id) WHERE estado = 'pendiente';

-- Índices para las consultas más frecuentes -----------------------------
CREATE INDEX IF NOT EXISTS ix_membresias_club     ON membresias(club_id, estado);
CREATE INDEX IF NOT EXISTS ix_anuncios_club       ON anuncios(club_id, fijado, creado_en);
CREATE INDEX IF NOT EXISTS ix_publicaciones_club  ON publicaciones(club_id, creado_en);
CREATE INDEX IF NOT EXISTS ix_comentarios_pub     ON comentarios(publicacion_id);
CREATE INDEX IF NOT EXISTS ix_mensajes_club       ON mensajes_chat(club_id, id);
CREATE INDEX IF NOT EXISTS ix_propuestas_club     ON propuestas_evento(club_id, estado, fecha_inicio);
CREATE INDEX IF NOT EXISTS ix_sesiones_usuario    ON sesiones(usuario_id);
CREATE INDEX IF NOT EXISTS ix_notificaciones      ON notificaciones(usuario_id, leida, id);
CREATE INDEX IF NOT EXISTS ix_asistencias_evento  ON asistencias(evento_id);

-- Vistas ----------------------------------------------------------------
-- Eventos = propuestas aprobadas.
CREATE VIEW IF NOT EXISTS v_eventos AS
    SELECT p.id, p.club_id, c.nombre AS club_nombre, c.slug AS club_slug,
           p.titulo, p.descripcion, p.fecha_inicio, p.lugar, p.cupo
    FROM propuestas_evento p
    JOIN clubes c ON c.id = p.club_id
    WHERE p.estado = 'aprobada' AND c.estado = 'activo';

-- Puntaje de cada publicación (suma de votos).
CREATE VIEW IF NOT EXISTS v_puntaje_publicacion AS
    SELECT p.id AS publicacion_id, COALESCE(SUM(v.valor), 0) AS puntaje
    FROM publicaciones p
    LEFT JOIN votos_publicacion v ON v.publicacion_id = p.id
    GROUP BY p.id;
