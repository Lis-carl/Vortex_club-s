# 2. Determinación de requerimientos

> Fase 2 del CVDS: *Determinación de los requerimientos de información* (Kendall, cap. 4 y 5).

## 2.1 Interesados y actores

| Actor | Descripción | Ejemplo |
|-------|-------------|---------|
| **Visitante** | Persona sin sesión iniciada. Solo puede ver la pantalla de acceso y registrarse. | Estudiante de nuevo ingreso |
| **Estudiante** | Usuario registrado. Explora clubes, se une, publica, comenta, reacciona, chatea y propone eventos en los clubes donde es miembro. | Cualquier alumno con CIF |
| **Capitán** | Miembro con responsabilidades dentro de un club. Publica anuncios del club, revisa propuestas de eventos, aprueba solicitudes de ingreso y modera el foro. | Coordinador de logística del club de robótica |
| **Líder** | Responsable principal del club (uno por club). Tiene los permisos del capitán y además asigna o quita capitanes y edita la información del club. | Presidente del club |
| **Administrador** | Personal de la universidad (Dirección de Vida Estudiantil). Aprueba la creación de clubes, publica anuncios generales y gestiona cuentas. | Oficina de Asuntos Estudiantiles |

> "Estudiante", "Capitán" y "Líder" son el mismo tipo de usuario: el rol de capitán o líder se tiene
> **dentro de un club específico**. Una persona puede ser líder de un club y miembro simple de otro.

## 2.2 Técnicas de recopilación de información

Siguiendo los métodos interactivos (cap. 4) y discretos (cap. 5) se proponen los siguientes
instrumentos. Las respuestas se anexan al repositorio cuando se apliquen.

### Guía de entrevista (líderes de club actuales)
Estructura de pirámide invertida: de preguntas específicas a generales.

1. ¿Cuántos miembros tiene su club y cómo lleva el registro hoy?
2. ¿Por qué medio publica los anuncios? ¿Qué tan seguido?
3. ¿Cómo proponen y aprueban eventos los miembros? ¿Quién decide?
4. ¿Qué información le gustaría que los nuevos estudiantes vean del club?
5. ¿Qué problemas ha tenido con los grupos de chat actuales?
6. Si pudiera cambiar una sola cosa de cómo funciona su club, ¿cuál sería?

### Cuestionario (estudiantes en general)
Escala de Likert 1 (muy en desacuerdo) a 5 (muy de acuerdo), más preguntas abiertas.

| # | Afirmación | 1 | 2 | 3 | 4 | 5 |
|---|-----------|---|---|---|---|---|
| 1 | Conozco los clubes que existen en la universidad. | | | | | |
| 2 | Me entero a tiempo de los eventos de los clubes. | | | | | |
| 3 | Me gustaría ver todos los clubes en una sola plataforma. | | | | | |
| 4 | Usaría un foro para discutir temas del club. | | | | | |
| 5 | Me gustaría proponer eventos a un club aunque no sea líder. | | | | | |

Preguntas abiertas: ¿Qué te impide unirte a un club? ¿Qué función te parecería más útil?

### Métodos discretos
- **Muestreo de documentos:** carteles, publicaciones de Instagram y conversaciones de WhatsApp
  de tres clubes, para identificar qué datos se comunican (fecha, lugar, cupo, responsable).
- **Observación:** cómo se inscribe un estudiante a un club durante la feria de clubes.
- **Análisis de la plataforma UAM Virtual:** los estudiantes ya inician sesión con **CIF y PIN**;
  se adopta el mismo esquema (usuario = CIF) y el mismo estilo visual.

## 2.3 Requerimientos funcionales

Prioridad según MoSCoW: **A** = indispensable, **M** = importante, **B** = deseable.

### Cuentas y acceso
| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-01 | El sistema debe permitir registrarse con CIF, nombre completo, correo, carrera y contraseña. | A |
| RF-02 | El sistema debe permitir iniciar sesión con CIF y contraseña, y cerrar sesión. | A |
| RF-03 | El sistema debe mostrar un perfil con los clubes y publicaciones del usuario. | M |

### Clubes y membresías
| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-04 | El sistema debe mostrar el catálogo de clubes activos con búsqueda por nombre y filtro por categoría. | A |
| RF-05 | Un estudiante debe poder **solicitar la creación** de un club; el administrador la aprueba o rechaza, y quien la pidió queda como líder. | A |
| RF-06 | Un estudiante debe poder **unirse** a un club. Si el club es abierto entra de inmediato; si requiere aprobación queda pendiente. | A |
| RF-07 | Líder y capitanes deben poder aceptar o rechazar solicitudes de ingreso pendientes. | A |
| RF-08 | Un miembro debe poder salir de un club (el líder no puede salir sin transferir el liderazgo). | M |
| RF-09 | El sistema debe mostrar los integrantes del club agrupados en **líder, capitanes y miembros**. | A |
| RF-10 | El líder debe poder nombrar o quitar capitanes, expulsar miembros y transferir el liderazgo. | A |
| RF-11 | El líder debe poder editar la descripción, categoría y modo de ingreso del club. | M |

### Anuncios
| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-12 | El administrador debe poder publicar **anuncios generales** visibles para todos. | A |
| RF-13 | Líder y capitanes deben poder publicar **anuncios del club** en su apartado propio. | A |
| RF-14 | Los anuncios se pueden **fijar** para que aparezcan primero, y eliminar por su autor o un responsable. | M |

### Foro estilo Reddit
| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-15 | Un miembro debe poder crear publicaciones con título, texto y una imagen opcional en el foro del club. | A |
| RF-16 | Los usuarios deben poder comentar publicaciones y responder comentarios (hilos anidados). | A |
| RF-17 | Los usuarios deben poder votar a favor o en contra de publicaciones y comentarios. | M |
| RF-18 | Los usuarios deben poder **reaccionar** a publicaciones con emojis (👍 ❤️ 😂 😮 😢 🔥) y ver el conteo de cada reacción. | A |
| RF-19 | El foro debe poder ordenarse por **Nuevos** o **Populares**. | M |
| RF-20 | El autor puede eliminar su publicación o comentario; líder y capitanes pueden eliminar cualquiera de su club. | A |
| RF-21 | La página de inicio debe mostrar un feed con publicaciones de los clubes del usuario y los anuncios generales. | A |

### Chat
| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-22 | Cada club debe tener una sala de chat para sus miembros activos. | A |
| RF-23 | El chat debe actualizarse automáticamente con los mensajes nuevos sin recargar la página. | M |

### Eventos
| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-24 | Un miembro debe poder llenar un **formulario de propuesta de evento** (título, descripción, fecha y hora, lugar, cupo, recursos). | A |
| RF-25 | Líder y capitanes deben poder aprobar o rechazar propuestas con un comentario. | A |
| RF-26 | El proponente debe poder ver el estado de sus propuestas. | M |
| RF-27 | El sistema debe mostrar los eventos aprobados en el club y en una lista general de **próximos eventos**. | A |

### Administración
| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-28 | El administrador debe ver un panel con solicitudes de club pendientes, usuarios y estadísticas. | A |
| RF-29 | El administrador debe poder desactivar o reactivar cuentas de usuario. | M |
| RF-30 | El administrador debe poder desactivar un club. | B |

## 2.4 Requerimientos no funcionales

| ID | Tipo | Requerimiento |
|----|------|---------------|
| RNF-01 | Restricción tecnológica | El servidor debe programarse en **Python 3.10+ usando solo la biblioteca estándar** (sin `pip install`). |
| RNF-02 | Restricción tecnológica | La única base de datos permitida es **SQLite** mediante el módulo estándar `sqlite3`. |
| RNF-03 | Restricción tecnológica | El navegador no debe depender de librerías externas (sin frameworks CSS/JS ni CDN). |
| RNF-04 | Usabilidad | La interfaz debe ser minimalista y similar a UAM Virtual: color verde azulado, tarjetas blancas, tipografía sin serifa. Un usuario nuevo debe poder unirse a un club en menos de 3 clics desde el inicio. |
| RNF-05 | Usabilidad | El diseño debe adaptarse a pantallas de celular (ancho ≥ 360 px). |
| RNF-06 | Seguridad | Las contraseñas se guardan con **PBKDF2-HMAC-SHA256** con sal aleatoria y 200 000 iteraciones; nunca en texto plano. |
| RNF-07 | Seguridad | Todo formulario que modifique datos debe llevar un **token CSRF** ligado a la sesión. |
| RNF-08 | Seguridad | Todo texto escrito por usuarios se **escapa** al mostrarse (prevención de XSS) y todas las consultas SQL usan **parámetros** (prevención de inyección SQL). |
| RNF-09 | Seguridad | La cookie de sesión debe ser `HttpOnly` y `SameSite=Lax`; la sesión expira a los 7 días. |
| RNF-10 | Seguridad | Las imágenes subidas se limitan a PNG, JPG, GIF o WEBP de máximo 2 MB, verificando su firma binaria. |
| RNF-11 | Rendimiento | Las páginas deben responder en menos de 500 ms con 50 usuarios simultáneos en una computadora de laboratorio. |
| RNF-12 | Disponibilidad | El sistema debe iniciar con un solo comando (`python app.py`) y crear la base de datos automáticamente si no existe. |
| RNF-13 | Mantenibilidad | El código se organiza por capas (servidor, controladores, repositorios de datos, plantillas) y se documenta en español. |
| RNF-14 | Integridad | La base de datos debe activar claves foráneas (`PRAGMA foreign_keys = ON`) y restricciones `CHECK`/`UNIQUE`. |
| RNF-15 | Portabilidad | Debe funcionar en Windows, Linux y macOS sin cambios. |
| RNF-16 | Idioma | Toda la interfaz está en español. |

## 2.5 Reglas de negocio

| ID | Regla |
|----|-------|
| RN-01 | El CIF es único y numérico (8 dígitos); el correo es único. |
| RN-02 | Cada club tiene **exactamente un líder** activo. |
| RN-03 | Solo los **miembros activos** de un club pueden publicar, comentar, chatear y proponer eventos en él. |
| RN-04 | Cualquier usuario con sesión puede leer el foro y los anuncios de un club, aunque no sea miembro. El chat solo lo ven los miembros. |
| RN-05 | Un usuario tiene como máximo una reacción de cada tipo por publicación (al volver a pulsarla se quita). |
| RN-06 | Un usuario tiene como máximo un voto por publicación o comentario (+1 o −1). |
| RN-07 | La fecha de una propuesta de evento debe ser posterior al momento en que se envía. |
| RN-08 | El nombre de un club es único. |
| RN-09 | Una cuenta desactivada no puede iniciar sesión. |

## 2.6 Matriz de permisos por rol

| Acción | Visitante | Estudiante | Miembro | Capitán | Líder | Admin |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|
| Registrarse / iniciar sesión | ✔ | | | | | |
| Ver catálogo, foro y anuncios | | ✔ | ✔ | ✔ | ✔ | ✔ |
| Solicitar creación de club | | ✔ | ✔ | ✔ | ✔ | ✔ |
| Unirse a un club | | ✔ | | | | ✔ |
| Votar y reaccionar | | ✔ | ✔ | ✔ | ✔ | ✔ |
| Publicar y comentar en el foro | | | ✔ | ✔ | ✔ | |
| Usar el chat del club | | | ✔ | ✔ | ✔ | |
| Proponer evento | | | ✔ | ✔ | ✔ | |
| Publicar anuncio del club | | | | ✔ | ✔ | |
| Aprobar ingresos y propuestas | | | | ✔ | ✔ | |
| Eliminar contenido del club | | | | ✔ | ✔ | |
| Nombrar capitanes, expulsar, editar club | | | | | ✔ | |
| Aprobar clubes, anuncios generales, gestionar cuentas | | | | | | ✔ |

> Votar y reaccionar se permite a cualquier usuario con sesión (no solo miembros), para que el
> foro sea abierto a la lectura y la participación ligera, como en Reddit.
