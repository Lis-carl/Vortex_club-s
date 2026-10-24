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

### Resultados de la encuesta aplicada (octubre de 2026)

Se aplicó un cuestionario en Google Forms a la comunidad de la UAM. Se recibieron **15 respuestas**
(13 estudiantes y 4 líderes o capitanes; algunas personas marcaron ambos roles). Las respuestas
completas están en [`encuesta/respuestas_encuesta.csv`](encuesta/respuestas_encuesta.csv).

| Pregunta | Resultado principal |
|----------|--------------------|
| ¿Qué tan fácil es encontrar información de los clubes y cómo unirte? | **Regular 8 · Difícil 4 · Muy difícil 3** (nadie respondió «fácil») |
| ¿Por qué medio te enteraste de los clubes? | Amigos o compañeros 11 · Redes sociales 5 · Ferias 3 · Web oficial 1 |
| ¿Por dónde te informas de las actividades de tu club? | WhatsApp 8 · Instagram 4 · Presencial 2 |
| ¿Te has perdido actividades por no enterarte a tiempo? | **Sí, algunas veces 6 · Sí, frecuentemente 2** · Rara vez 3 · Nunca 4 |
| Principal dificultad al participar | **Información dispersa 6 · Horarios mal coordinados 6** · Demasiados mensajes en chats 3 · Avisos llegan tarde 2 · No sé qué clubs existen 1 · No sé cómo inscribirme 1 |
| ¿Usarías una aplicación que reúna todo? | **Definitivamente sí 8 · Probablemente sí 6** · No estoy seguro 1 |
| Función más útil | **Inscripción en línea 5** · Catálogo y buscador 3 · Confirmación de asistencia 2 · Notificaciones y recordatorios 2 · Calendario de actividades 2 · Tablón de anuncios por club 1 |
| Dispositivo principal | **Celular 13** · Ambos 2 |
| Frecuencia de uso | Varias veces por semana 8 · Diariamente 3 · Una vez por semana 2 · Solo con eventos 2 |
| Sugerencias | «Algo que incentive el uso de la web» · «Notificaciones y que sea fácil de usar» |

**Cómo se tradujeron las respuestas en funciones:**

| Hallazgo | Función de la plataforma |
|----------|-------------------------|
| Inscripción en línea (función más votada) | Botón «Unirme» / «Solicitar ingreso» en el catálogo y en cada club (RF-06) |
| Catálogo y buscador | Catálogo de todos los clubes con su categoría, descripción y miembros (RF-04). Por decisión del equipo se retiró el buscador y el filtro: con 15 clubes el catálogo completo cabe en una sola vista |
| Confirmación de asistencia | Botón «Confirmar asistencia» con cupo y lista de asistentes (RF-32) |
| Notificaciones, avisos que llegan tarde, eventos perdidos | Bandeja de notificaciones con contador (RF-33) y recordatorios de eventos confirmados en las próximas 48 h (RF-34) |
| Calendario y horarios mal coordinados | Calendario mensual de actividades de todos los clubes (RF-35) |
| Información dispersa, demasiados mensajes en chats | Tablón de anuncios por club y general, foro ordenado y chat por club, todo en un solo lugar |
| «Algo que incentive el uso» | Puntos de participación y niveles visibles en el perfil (RF-36) |
| No sé cómo inscribirme | Guía «Cómo unirte a un club» en 3 pasos en el inicio de quien aún no tiene clubes |
| 13 de 15 usarían el celular | Diseño adaptable a pantallas de 360 px (RNF-05) |

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
| RF-02 | El sistema debe permitir iniciar sesión con CIF y contraseña, y cerrar sesión. El **tipo de usuario lo determina la cuenta**: administración, líder o capitán si alguien lo nombró en un club, o estudiante. | A |
| RF-03 | El sistema debe mostrar un perfil con los clubes y publicaciones del usuario. Cada usuario puede **cambiar o quitar su foto de perfil** (PNG, JPG, GIF o WEBP de hasta 2 MB), que se muestra en la cabecera, sus publicaciones, comentarios y la lista de miembros. | M |

### Clubes y membresías
| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-04 | El sistema debe mostrar el catálogo completo de clubes activos con su categoría, descripción y número de miembros. | A |
| RF-05 | Un estudiante debe poder **solicitar la creación** de un club; el administrador la aprueba o rechaza, y quien la pidió queda como líder. | A |
| RF-06 | Un estudiante debe poder **unirse** a un club. Si el club es abierto entra de inmediato; si requiere aprobación queda pendiente. | A |
| RF-07 | Líder y capitanes deben poder aceptar o rechazar solicitudes de ingreso pendientes. | A |
| RF-08 | Un miembro debe poder salir de un club (el líder no puede salir sin transferir el liderazgo). | M |
| RF-09 | El sistema debe mostrar los integrantes del club agrupados en **líder, capitanes y miembros**. | A |
| RF-10 | El líder debe poder nombrar o quitar capitanes, expulsar miembros y transferir el liderazgo. | A |
| RF-11 | El líder **y los capitanes** deben poder editar la descripción, categoría y modo de ingreso de su club. | M |

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
| RF-23 | El panel de mensajes del chat debe actualizarse automáticamente (recarga HTML cada 5 segundos, sin JavaScript). | M |

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
| RF-31 | El administrador debe poder asignar o cambiar el líder de un club escribiendo el CIF del estudiante. | A |
| RF-37 | Un miembro debe poder **solicitar ser capitán** de su club; la administración aprueba o rechaza la petición. Los líderes también pueden nombrar capitanes directamente. | A |
| RF-38 | La administración debe tener permiso sobre **todo**: publicar y moderar en cualquier club, editarlo, revisar propuestas y gestionar sus miembros. | A |

### Funciones surgidas de la encuesta
| ID | Requerimiento | Prioridad |
|----|---------------|-----------|
| RF-32 | Un usuario debe poder **confirmar o cancelar su asistencia** a un evento aprobado y futuro, respetando el cupo. Líder y capitanes ven la lista de asistentes. | A |
| RF-33 | El sistema debe generar **notificaciones** (anuncio nuevo, evento aprobado, propuesta revisada, solicitud aceptada o rechazada, comentario o respuesta, asignación de rol) y mostrar el número de no leídas. | A |
| RF-34 | El sistema debe mostrar **recordatorios** de los eventos confirmados que empiezan en las próximas 48 horas. | M |
| RF-35 | El sistema debe ofrecer un **calendario mensual** de actividades, con filtro «mis clubes y confirmados». | A |
| RF-36 | El sistema debe calcular **puntos de participación** (publicación 5, comentario 2, asistencia 3, reacción recibida 1), y un nivel (Nuevo, Participante, Activo, Destacado), visibles en el perfil. | B |

## 2.4 Requerimientos no funcionales

| ID | Tipo | Requerimiento |
|----|------|---------------|
| RNF-01 | Restricción tecnológica | El servidor debe programarse en **Python 3.10+ usando solo la biblioteca estándar** (sin `pip install`). |
| RNF-02 | Restricción tecnológica | La única base de datos permitida es **SQLite** mediante el módulo estándar `sqlite3`. |
| RNF-03 | Restricción tecnológica | **Sin JavaScript.** Todas las páginas se generan en el servidor con Python; el navegador solo recibe HTML y CSS propios (sin frameworks ni CDN). La política de seguridad de contenido bloquea cualquier script (`script-src 'none'`). |
| RNF-04 | Usabilidad | La interfaz debe ser sobria, profesional y similar a UAM Virtual: color verde petróleo institucional, paneles blancos con bordes finos y esquinas casi rectas, una sola tipografía y **sin emojis en títulos ni menús**. Un usuario nuevo debe poder unirse a un club en menos de 3 clics desde el inicio. |
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
| RN-02 | Cada club tiene **como máximo un líder**. Lo asigna la administración (o el líder actual al transferir el liderazgo). |
| RN-03 | Solo los **miembros activos** de un club pueden publicar, comentar, chatear y proponer eventos en él. |
| RN-04 | Cualquier usuario con sesión puede leer el foro y los anuncios de un club, aunque no sea miembro. El chat solo lo ven los miembros. |
| RN-05 | Un usuario tiene como máximo una reacción de cada tipo por publicación (al volver a pulsarla se quita). |
| RN-06 | Un usuario tiene como máximo un voto por publicación o comentario (+1 o −1). |
| RN-07 | La fecha de una propuesta de evento debe ser posterior al momento en que se envía. |
| RN-08 | El nombre de un club es único. |
| RN-09 | Una cuenta desactivada no puede iniciar sesión. |
| RN-10 | El rol se calcula a partir de la cuenta en cada petición: si alguien es nombrado capitán o líder, obtiene esos permisos de inmediato en ese club, sin elegir nada al iniciar sesión. |
| RN-11 | Un estudiante solo puede eliminar sus propias publicaciones y comentarios. |
| RN-12 | No se puede confirmar asistencia a un evento lleno o que ya ocurrió. |
| RN-13 | Un miembro puede tener como máximo una solicitud de capitán pendiente por club. |

## 2.6 Matriz de permisos por rol

| Acción | Visitante | Estudiante | Miembro | Capitán | Líder | Admin |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|
| Registrarse / iniciar sesión | ✔ | | | | | |
| Ver catálogo, foro y anuncios | | ✔ | ✔ | ✔ | ✔ | ✔ |
| Solicitar creación de club | | ✔ | ✔ | ✔ | ✔ | ✔ |
| Unirse a un club | | ✔ | | | | ✔ |
| Votar y reaccionar | | ✔ | ✔ | ✔ | ✔ | ✔ |
| Publicar y comentar en el foro | | | ✔ | ✔ | ✔ | ✔ |
| Usar el chat del club | | | ✔ | ✔ | ✔ | ✔ |
| Confirmar asistencia a eventos | | ✔ | ✔ | ✔ | ✔ | ✔ |
| Solicitar ser capitán | | | ✔ | | | |
| Proponer evento | | | ✔ | ✔ | ✔ | ✔ |
| Publicar anuncio del club | | | | ✔ | ✔ | ✔ |
| Aprobar ingresos y propuestas | | | | ✔ | ✔ | ✔ |
| Eliminar contenido de otros en el club | | | | ✔ | ✔ | ✔ |
| Editar la configuración del club | | | | ✔ | ✔ | ✔ |
| Nombrar capitanes directamente, expulsar, transferir liderazgo | | | | | ✔ | ✔ |
| Aprobar solicitudes para ser capitán | | | | | | ✔ |
| Aprobar clubes, anuncios generales, gestionar cuentas | | | | | | ✔ |
| Asignar el líder de un club | | | | | | ✔ |

> Votar y reaccionar se permite a cualquier usuario con sesión (no solo miembros), para que el
> foro sea abierto a la lectura y la participación ligera, como en Reddit.
>
> Las columnas Capitán y Líder aplican en el club donde la persona tiene ese rol (RN-10).

## 2.7 Datos iniciales

La plataforma se entrega **vacía**: no trae usuarios, publicaciones, anuncios ni eventos de
ejemplo. Al crearse la base de datos solo se cargan:

- las 8 categorías de clubes;
- la cuenta de administración;
- el catálogo oficial de **15 clubes**: los 14 del afiche «Contactos de clubes, I semestre 2026» de la
  Dirección de Vida Estudiantil: Club Empresarial, Club de Debate, Voluntariado por el Autismo,
  Voluntariado Aldeas Infantiles SOS, Club de Cine, Club de Modelos, Club de Lectura, Club de
  Maestros de Ceremonias, Club de Edecanes, Club Conanca, Club de Traductores, Voluntariado por la
  Niñez, Club de Maquillaje y Proyección Juvenil UNEN-UAM, más el **Club de Esports** (agregado por el
  equipo del proyecto). Si falta alguno en una base ya creada, se agrega solo al iniciar.

Los clubes empiezan sin miembros y sin líder. Cuando cada líder crea su cuenta, la administración
lo asigna desde su panel (RF-31) y el líder completa la descripción del club. Los datos de
contacto del afiche (correos y teléfonos personales) no se cargan en la plataforma.
