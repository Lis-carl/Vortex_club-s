# 3. Análisis de procesos

> Fase 3 del CVDS: *Análisis de las necesidades del sistema*. Diagramas de flujo de datos
> (Kendall, cap. 7), diccionario de datos (cap. 8) y especificación de procesos (cap. 9).

## 3.1 Simbología

Los diagramas se escriben en Mermaid (GitHub los dibuja automáticamente). Se usa la notación de
**Gane y Sarson** adaptada a las figuras disponibles:

| Símbolo Gane & Sarson | Figura en el diagrama | Significado |
|---|---|---|
| Cuadrado doble | Rectángulo `[ ]` | Entidad externa |
| Rectángulo redondeado | Rectángulo redondeado `( )` con número | Proceso |
| Rectángulo abierto | Cilindro `[( )]` con prefijo `D` | Almacén de datos |
| Flecha | Flecha con texto | Flujo de datos |

## 3.2 Diagrama de contexto (nivel superior)

```mermaid
flowchart LR
    EST[Estudiante]
    RES["Responsable del club<br/>(Líder / Capitán)"]
    ADM[Administrador]
    SYS(("0<br/>Sistema<br/>Vortex Club"))

    EST -- "datos de registro, credenciales" --> SYS
    EST -- "solicitud de ingreso, publicación, comentario,<br/>voto, reacción, mensaje, propuesta de evento" --> SYS
    EST -- "solicitud de creación de club" --> SYS
    SYS -- "catálogo de clubes, feed, anuncios,<br/>integrantes, mensajes, eventos" --> EST
    SYS -- "estado de solicitudes y propuestas" --> EST

    RES -- "anuncio del club, decisión de ingreso,<br/>decisión sobre propuesta, cambio de rol" --> SYS
    SYS -- "solicitudes de ingreso pendientes,<br/>propuestas pendientes" --> RES

    ADM -- "anuncio general, decisión sobre club,<br/>asignación de líder, estado de cuenta" --> SYS
    SYS -- "solicitudes de club pendientes,<br/>estadísticas, lista de usuarios" --> ADM
```

## 3.3 Diagrama de nivel 0

```mermaid
flowchart TB
    EST[Estudiante]
    RES[Responsable del club]
    ADM[Administrador]

    P1("1.0<br/>Gestionar cuentas")
    P2("2.0<br/>Gestionar clubes")
    P3("3.0<br/>Gestionar membresías")
    P4("4.0<br/>Publicar anuncios")
    P5("5.0<br/>Gestionar foro")
    P6("6.0<br/>Gestionar chat")
    P7("7.0<br/>Gestionar eventos")
    P8("8.0<br/>Notificar y<br/>recordar")

    D1[("D1 Usuarios")]
    D2[("D2 Sesiones")]
    D3[("D3 Clubes")]
    D4[("D4 Solicitudes de club")]
    D5[("D5 Membresías")]
    D6[("D6 Anuncios")]
    D7[("D7 Publicaciones y comentarios")]
    D8[("D8 Votos y reacciones")]
    D9[("D9 Mensajes de chat")]
    D10[("D10 Propuestas de evento")]
    D11[("D11 Asistencias")]
    D12[("D12 Notificaciones")]
    D13[("D13 Solicitudes de capitán")]

    EST -- "registro, credenciales" --> P1
    P1 -- "usuario nuevo / estado" --> D1
    D1 -- "hash de contraseña" --> P1
    P1 -- "token de sesión" --> D2
    P1 -- "sesión iniciada" --> EST
    ADM -- "estado de cuenta" --> P1

    EST -- "solicitud de club" --> P2
    P2 -- "solicitud" --> D4
    D4 -- "solicitudes pendientes" --> P2
    P2 -- "solicitudes pendientes" --> ADM
    ADM -- "decisión" --> P2
    P2 -- "club aprobado" --> D3
    P2 -- "líder inicial" --> D5
    D3 -- "catálogo" --> P2
    P2 -- "catálogo" --> EST

    EST -- "solicitud de ingreso / salida" --> P3
    D3 -- "modo de ingreso" --> P3
    P3 -- "membresía" --> D5
    D5 -- "pendientes, integrantes" --> P3
    P3 -- "pendientes" --> RES
    RES -- "decisión, cambio de rol" --> P3
    ADM -- "asignación de líder (CIF)" --> P3
    P3 -- "integrantes" --> EST

    RES -- "anuncio del club" --> P4
    ADM -- "anuncio general" --> P4
    D5 -- "rol del autor" --> P4
    P4 -- "anuncio" --> D6
    D6 -- "anuncios" --> P4
    P4 -- "anuncios" --> EST

    EST -- "publicación, comentario" --> P5
    EST -- "voto, reacción" --> P5
    D5 -- "membresía" --> P5
    P5 -- "contenido" --> D7
    P5 -- "voto / reacción" --> D8
    D7 -- "contenido" --> P5
    D8 -- "conteos" --> P5
    P5 -- "feed, hilo" --> EST
    RES -- "eliminación" --> P5

    EST -- "mensaje" --> P6
    D5 -- "membresía" --> P6
    P6 -- "mensaje" --> D9
    D9 -- "mensajes nuevos" --> P6
    P6 -- "mensajes" --> EST

    EST -- "propuesta de evento" --> P7
    D5 -- "membresía" --> P7
    P7 -- "propuesta" --> D10
    D10 -- "pendientes / aprobadas" --> P7
    P7 -- "pendientes" --> RES
    RES -- "decisión y comentario" --> P7
    P7 -- "estado, próximos eventos" --> EST
    EST -- "confirmación de asistencia" --> P7
    P7 -- "asistencia" --> D11
    D11 -- "asistentes, cupo" --> P7
    EST -- "solicitud de capitán" --> P3
    P3 -- "solicitud" --> D13
    D13 -- "solicitudes pendientes" --> P3
    ADM -- "aprobación de capitán" --> P3
    P3 -- "aviso" --> P8
    P4 -- "aviso" --> P8
    P5 -- "aviso" --> P8
    P7 -- "aviso" --> P8
    P8 -- "notificación" --> D12
    D12 -- "no leídas" --> P8
    D11 -- "eventos confirmados" --> P8
    P8 -- "notificaciones y recordatorios" --> EST
```

## 3.4 Diagramas hijo (nivel 1)

### 3.4.1 Proceso 3.0, Gestionar membresías

```mermaid
flowchart TB
    EST[Estudiante]
    RES[Responsable del club]
    ADM[Administrador]
    D1[("D1 Usuarios")]
    D3[("D3 Clubes")]
    D5[("D5 Membresías")]

    P31("3.1<br/>Validar solicitud<br/>de ingreso")
    P32("3.2<br/>Registrar<br/>membresía")
    P33("3.3<br/>Resolver solicitud<br/>pendiente")
    P34("3.4<br/>Cambiar rol, asignar<br/>líder o expulsar")
    P35("3.5<br/>Listar<br/>integrantes")

    EST -- "solicitud de ingreso" --> P31
    D3 -- "club activo, requiere aprobación" --> P31
    D5 -- "membresía existente" --> P31
    P31 -- "solicitud válida + estado inicial" --> P32
    P32 -- "membresía (activa o pendiente)" --> D5
    D5 -- "pendientes" --> P33
    P33 -- "pendientes" --> RES
    RES -- "aceptar / rechazar" --> P33
    P33 -- "membresía actualizada" --> D5
    RES -- "nuevo rol / expulsión" --> P34
    ADM -- "CIF del nuevo líder" --> P34
    D1 -- "cuenta activa" --> P34
    P34 -- "rol actualizado" --> D5
    D5 -- "integrantes por rol" --> P35
    P35 -- "líder, capitanes, miembros" --> EST
```

### 3.4.2 Proceso 5.0, Gestionar foro

```mermaid
flowchart TB
    EST[Estudiante]
    RES[Responsable del club]
    D5[("D5 Membresías")]
    D7[("D7 Publicaciones y comentarios")]
    D8[("D8 Votos y reacciones")]

    P51("5.1<br/>Crear<br/>publicación")
    P52("5.2<br/>Comentar")
    P53("5.3<br/>Votar")
    P54("5.4<br/>Alternar<br/>reacción")
    P55("5.5<br/>Armar feed<br/>y ordenar")
    P56("5.6<br/>Eliminar<br/>contenido")

    EST -- "título, texto, imagen" --> P51
    D5 -- "es miembro activo" --> P51
    P51 -- "publicación" --> D7
    EST -- "comentario, comentario padre" --> P52
    D5 -- "es miembro activo" --> P52
    P52 -- "comentario" --> D7
    EST -- "valor +1/−1" --> P53
    P53 -- "voto" --> D8
    EST -- "tipo de reacción" --> P54
    D8 -- "reacción existente" --> P54
    P54 -- "insertar / borrar reacción" --> D8
    D7 -- "publicaciones" --> P55
    D8 -- "puntaje y conteos" --> P55
    P55 -- "feed ordenado" --> EST
    RES -- "solicitud de eliminación" --> P56
    D5 -- "rol del solicitante" --> P56
    P56 -- "marca eliminado" --> D7
```

### 3.4.3 Proceso 7.0, Gestionar eventos

```mermaid
flowchart TB
    EST[Estudiante miembro]
    RES[Responsable del club]
    D5[("D5 Membresías")]
    D10[("D10 Propuestas de evento")]
    D11[("D11 Asistencias")]
    D12[("D12 Notificaciones")]
    D13[("D13 Solicitudes de capitán")]

    P71("7.1<br/>Validar formulario<br/>de propuesta")
    P72("7.2<br/>Registrar<br/>propuesta")
    P73("7.3<br/>Revisar<br/>propuesta")
    P74("7.4<br/>Publicar eventos<br/>aprobados")

    EST -- "formulario de propuesta" --> P71
    D5 -- "es miembro activo" --> P71
    P71 -- "errores de validación" --> EST
    P71 -- "propuesta válida" --> P72
    P72 -- "propuesta pendiente" --> D10
    D10 -- "pendientes" --> P73
    P73 -- "pendientes" --> RES
    RES -- "aprobar / rechazar + comentario" --> P73
    P73 -- "estado y comentario" --> D10
    D10 -- "aprobadas futuras" --> P74
    P74 -- "próximos eventos" --> EST
```

## 3.5 Diccionario de datos

Notación de Kendall (cap. 8): `=` está compuesto de, `+` y, `{ }` repetición, `[ | ]` uno de,
`( )` opcional, `* *` comentario.

### 3.5.1 Flujos de datos

| Nombre | Descripción | Origen | Destino | Estructura |
|--------|-------------|--------|---------|-----------|
| Datos de registro | Datos que escribe un visitante para crear su cuenta | Estudiante | 1.0 | Registro de usuario |
| Credenciales | CIF y contraseña | Estudiante | 1.0 | `CIF + Contraseña` |
| Solicitud de club | Petición para fundar un club | Estudiante | 2.0 | Solicitud de club |
| Solicitud de ingreso | Petición de unirse a un club | Estudiante | 3.0 | `ID usuario + ID club` |
| Publicación | Entrada nueva en el foro | Estudiante | 5.0 | Publicación |
| Reacción | Emoji sobre una publicación | Estudiante | 5.4 | `ID usuario + ID publicación + Tipo reacción` |
| Mensaje | Texto en el chat del club | Estudiante | 6.0 | Mensaje de chat |
| Formulario de propuesta | Datos de un evento propuesto | Estudiante | 7.1 | Propuesta de evento |
| Decisión sobre propuesta | Aprobación o rechazo | Responsable | 7.3 | `ID propuesta + [Aprobada \| Rechazada] + (Comentario)` |
| Anuncio general | Comunicado institucional | Administrador | 4.0 | Anuncio |
| Próximos eventos | Eventos aprobados con fecha futura | 7.4 | Estudiante | `{Evento}` |

### 3.5.2 Almacenes de datos

| ID | Nombre | Descripción | Estructura | Tabla SQLite |
|----|--------|-------------|-----------|--------------|
| D1 | Usuarios | Cuentas registradas | Registro de usuario | `usuarios` |
| D2 | Sesiones | Sesiones abiertas | `Token + ID usuario + Token CSRF + Expira en + Rol de acceso` | `sesiones` |
| D3 | Clubes | Clubes aprobados | Club | `clubes` |
| D4 | Solicitudes de club | Peticiones de nuevos clubes | Solicitud de club | `solicitudes_club` |
| D5 | Membresías | Relación usuario-club con rol | Membresía | `membresias` |
| D6 | Anuncios | Anuncios generales y por club | Anuncio | `anuncios` |
| D7 | Publicaciones y comentarios | Contenido del foro | Publicación, Comentario | `publicaciones`, `comentarios` |
| D8 | Votos y reacciones | Interacciones sobre el contenido | Voto, Reacción | `votos_publicacion`, `votos_comentario`, `reacciones` |
| D9 | Mensajes de chat | Mensajes por club | Mensaje de chat | `mensajes_chat` |
| D10 | Propuestas de evento | Propuestas y su revisión | Propuesta de evento | `propuestas_evento` |
| D11 | Asistencias | Confirmaciones de asistencia a eventos | `ID usuario + ID evento + Fecha` | `asistencias` |
| D12 | Notificaciones | Avisos para cada usuario | `ID usuario + Texto + Enlace + Leída + Fecha` | `notificaciones` |
| D14 | Mensajes privados | Chat entre dos integrantes de un mismo club | `ID emisor + ID receptor + Contenido + Leído + Fecha` | `mensajes_privados` |
| D13 | Solicitudes de capitán | Peticiones de miembros para ser capitán | `ID usuario + ID club + Motivo + Estado + (Revisor + Comentario)` | `solicitudes_capitan` |

### 3.5.3 Estructuras de datos

```text
Registro de usuario = CIF + Nombre completo + Correo + Carrera + Contraseña
                      + (Rol global) + (Activo) + (Fecha de creación)
Club                = ID club + Nombre club + Slug + Descripción + (Foto)
                      + Requiere aprobación + Estado club + Fecha de creación
Solicitud de club   = Nombre club + Descripción + Justificación
                      + Estado solicitud + (Comentario de revisión)
Membresía           = ID usuario + ID club + [Miembro | Capitán | Líder]
                      + [Pendiente | Activa] + Fecha de ingreso
Anuncio             = (ID club) + ID autor + Título + Contenido + Fijado + Fecha
                      * ID club vacío = anuncio general *
Publicación         = ID club + ID autor + Título + Contenido + (Imagen) + Fecha
Comentario          = ID publicación + ID autor + (ID comentario padre) + Contenido + Fecha
Voto                = ID usuario + [ID publicación | ID comentario] + [+1 | −1]
Reacción            = ID usuario + ID publicación + [👍 | ❤️ | 😂 | 😮 | 😢 | 🔥]
Mensaje de chat     = ID club + ID autor + Contenido + Fecha
Propuesta de evento = ID club + ID proponente + Título + Descripción + Fecha inicio
                      + Lugar + (Cupo) + (Recursos) + Estado propuesta
                      + (ID revisor + Comentario de revisión + Fecha de revisión)
```

### 3.5.4 Elementos de datos (selección)

| Elemento | Tipo | Longitud | Formato / validación | Valor por omisión |
|----------|------|---------|---------------------|-------------------|
| CIF | Texto numérico | 8 | Exactamente 8 dígitos; único | — |
| Nombre completo | Texto | 3–80 | Letras y espacios | — |
| Correo | Texto | ≤ 120 | Contiene `@` y un punto en el dominio; único | — |
| Carrera | Texto | ≤ 80 | Lista sugerida | — |
| Contraseña | Texto | 6–128 | Mínimo 6 caracteres; se guarda solo su hash | — |
| Rol global | Texto | — | `estudiante` \| `admin` | `estudiante` |
| Nombre club | Texto | 3–60 | Único | — |
| Slug | Texto | ≤ 70 | Minúsculas, dígitos y guiones, derivado del nombre | — |
| Requiere aprobación | Entero | 1 | 0 = abierto, 1 = con aprobación | 0 |
| Rol en club | Texto | — | `miembro` \| `capitan` \| `lider` | `miembro` |
| Estado membresía | Texto | — | `pendiente` \| `activa` | — |
| Título | Texto | 3–150 | — | — |
| Contenido | Texto | 1–10 000 | — | — |
| Imagen | Texto (ruta) | ≤ 100 | PNG/JPG/GIF/WEBP ≤ 5 MB | vacío |
| Tipo reacción | Texto | — | uno de los 6 emojis permitidos | — |
| Valor voto | Entero | 1 | `1` \| `-1` | — |
| Fecha inicio | Fecha-hora ISO | 16 | `AAAA-MM-DDTHH:MM`, posterior a ahora | — |
| Cupo | Entero | — | 1 – 10 000 | vacío |
| Estado propuesta | Texto | — | `pendiente` \| `aprobada` \| `rechazada` | `pendiente` |

## 3.6 Especificación de procesos (cap. 9)

### 3.6.1 Proceso 3.1/3.2, Unirse a un club (español estructurado)

```text
OBTENER usuario de la sesión
OBTENER club por su slug
SI el club no existe O el club no está activo
    ENTONCES mostrar "Club no encontrado"
DE OTRO MODO
    SI el usuario ya tiene una membresía en el club
        ENTONCES mostrar "Ya eres miembro o tu solicitud está pendiente"
    DE OTRO MODO
        SI el club requiere aprobación
            ENTONCES registrar membresía con rol = miembro, estado = pendiente
                     mostrar "Solicitud enviada; un responsable la revisará"
            DE OTRO MODO registrar membresía con rol = miembro, estado = activa
                     mostrar "Te uniste al club"
        FIN SI
    FIN SI
FIN SI
```

### 3.6.2 Tabla de decisión: ¿quién puede eliminar una publicación?

| Condiciones / Acciones | R1 | R2 | R3 | R4 |
|---|:-:|:-:|:-:|:-:|
| Es el autor de la publicación | S | N | N | N |
| Es líder o capitán activo del club | – | S | N | N |
| Es administrador | – | – | S | N |
| **Permitir eliminar** | X | X | X | |
| **Denegar (error 403)** | | | | X |

### 3.6.3 Árbol de decisión: revisar propuesta de evento

```mermaid
flowchart LR
    A{"¿Revisor es líder<br/>o capitán activo?"} -- No --> X["Denegar"]
    A -- Sí --> B{"¿Propuesta<br/>pendiente?"}
    B -- No --> Y["Mostrar 'ya fue revisada'"]
    B -- Sí --> C{"Decisión"}
    C -- Aprobar --> D{"¿Fecha aún<br/>futura?"}
    D -- Sí --> E["Estado = aprobada<br/>aparece en próximos eventos"]
    D -- No --> F["No aprobar<br/>avisar 'la fecha ya pasó'"]
    C -- Rechazar --> G["Estado = rechazada<br/>guardar comentario"]
```

### 3.6.4 Proceso 5.4, Alternar reacción (español estructurado)

```text
OBTENER usuario, publicación y tipo de reacción
SI el tipo no pertenece a {👍, ❤️, 😂, 😮, 😢, 🔥}
    ENTONCES responder error 400
DE OTRO MODO
    SI existe reacción (usuario, publicación, tipo)
        ENTONCES borrarla
        DE OTRO MODO insertarla
    FIN SI
    CALCULAR conteo por tipo para la publicación
    DEVOLVER conteos en formato JSON
FIN SI
```
