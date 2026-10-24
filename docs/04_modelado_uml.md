# 4. Modelado orientado a objetos con UML

> Kendall, cap. 2 (modelado de casos de uso) y cap. 10 (análisis y diseño orientado a objetos con UML).

## 4.1 Diagrama de casos de uso

UML dibuja actores como monigotes; en Mermaid se representan como rectángulos con 👤 y los casos
de uso como óvalos dentro del límite del sistema. La flecha punteada `«include»` indica que un caso
de uso siempre usa a otro; `«extend»` indica un comportamiento opcional.

```mermaid
flowchart LR
    V["👤 Visitante"]
    E["👤 Estudiante"]
    C["👤 Capitán"]
    L["👤 Líder"]
    A["👤 Administrador"]

    subgraph S["Sistema Vortex Club"]
        CU01(["CU-01 Registrarse"])
        CU02(["CU-02 Iniciar sesión"])
        CU03(["CU-03 Explorar clubes"])
        CU04(["CU-04 Solicitar creación de club"])
        CU05(["CU-05 Unirse a un club"])
        CU06(["CU-06 Ver integrantes"])
        CU07(["CU-07 Ver anuncios"])
        CU08(["CU-08 Publicar en el foro"])
        CU09(["CU-09 Comentar"])
        CU10(["CU-10 Votar y reaccionar"])
        CU11(["CU-11 Chatear en el club"])
        CU12(["CU-12 Proponer evento"])
        CU13(["CU-13 Publicar anuncio del club"])
        CU14(["CU-14 Resolver solicitudes de ingreso"])
        CU15(["CU-15 Revisar propuesta de evento"])
        CU16(["CU-16 Moderar contenido"])
        CU17(["CU-17 Gestionar roles del club"])
        CU18(["CU-18 Aprobar creación de club"])
        CU19(["CU-19 Publicar anuncio general"])
        CU20(["CU-20 Gestionar cuentas"])
        CU21(["CU-21 Subir imagen"])
        CU22(["CU-22 Asignar líder de club"])
        CU23(["CU-23 Confirmar asistencia"])
        CU24(["CU-24 Ver notificaciones y recordatorios"])
        CU25(["CU-25 Consultar calendario"])
        CU26(["CU-26 Solicitar ser capitán"])
        CU27(["CU-27 Aprobar solicitud de capitán"])
        CU28(["CU-28 Editar configuración del club"])
    end

    V --- CU01
    V --- CU02
    E --- CU03
    E --- CU04
    E --- CU05
    E --- CU06
    E --- CU07
    E --- CU08
    E --- CU09
    E --- CU10
    E --- CU11
    E --- CU12
    C --- CU13
    C --- CU14
    C --- CU15
    C --- CU16
    L --- CU17
    A --- CU18
    A --- CU19
    A --- CU20
    A --- CU22
    A --- CU27
    E --- CU23
    E --- CU24
    E --- CU25
    E --- CU26
    C --- CU28
    CU26 -. "«include» CU-27" .-> CU27

    C -. "es un" .-> E
    L -. "es un" .-> C

    CU05 -. "«include» CU-02" .-> CU02
    CU08 -. "«extend»" .-> CU21
    CU18 -. "«include»" .-> CU17
```

> Generalización: el **Líder** hereda los casos de uso del **Capitán**, y el Capitán los del
> **Estudiante**. CU-18 incluye asignar el rol de líder a quien solicitó el club.

## 4.2 Escenarios de casos de uso

Formato de Kendall (cap. 2): área, actor, interesados, descripción, evento activador, pasos,
precondiciones, postcondiciones, suposiciones, garantías, requerimientos cubiertos.

### CU-05 Unirse a un club

| Campo | Detalle |
|-------|---------|
| **ID** | CU-05 |
| **Prioridad** | Alta |
| **Actor principal** | Estudiante |
| **Interesados** | Estudiante: participar en el club. Líder/capitanes: controlar quién entra. |
| **Descripción** | El estudiante se une a un club abierto o envía una solicitud a un club con aprobación. |
| **Evento activador** | El estudiante pulsa **Unirme** en la página del club. Tipo: externo. |
| **Precondiciones** | Sesión iniciada; el club está activo; el estudiante no tiene membresía en ese club. |

| Pasos | Información para los pasos |
|-------|---------------------------|
| 1. El estudiante abre el catálogo y elige un club. | Lista de clubes (D3) |
| 2. El sistema muestra la página del club con el botón **Unirme**. | Club, conteo de miembros |
| 3. El estudiante pulsa **Unirme**. | Token CSRF |
| 4. El sistema valida que no exista membresía previa. | Membresías (D5) |
| 5a. Si el club es abierto, crea la membresía activa y muestra "Te uniste al club". | Membresía |
| 5b. Si requiere aprobación, crea la membresía pendiente y muestra "Solicitud enviada". | Membresía |

| Campo | Detalle |
|-------|---------|
| **Postcondiciones** | Existe una membresía (activa o pendiente) del estudiante en el club. |
| **Suposiciones** | El estudiante tiene una cuenta activa. |
| **Garantía de éxito** | El estudiante ve el club con su nuevo estado. |
| **Garantía mínima** | Si falla, no se crea ninguna membresía duplicada (restricción `UNIQUE`). |
| **Requerimientos cubiertos** | RF-06, RN-03 |

### CU-08 Publicar en el foro

| Campo | Detalle |
|-------|---------|
| **ID / Prioridad** | CU-08 / Alta |
| **Actor principal** | Miembro activo |
| **Descripción** | El miembro crea una publicación con título, texto e imagen opcional. |
| **Evento activador** | Pulsa **Crear publicación** en el foro del club. |
| **Precondiciones** | Sesión iniciada; membresía activa en el club. |

| Pasos | Información |
|-------|------------|
| 1. El miembro abre el formulario **Crear publicación**. | — |
| 2. Escribe título y contenido; opcionalmente adjunta una imagen. | Formulario multipart |
| 3. El sistema valida longitudes y, si hay imagen, tipo y tamaño. | Reglas RNF-10 |
| 4. Si hay errores, vuelve a mostrar el formulario con los mensajes y lo escrito. | — |
| 5. Si es válido, guarda la imagen en `subidas/` y la publicación en D7. | Publicación |
| 6. Redirige al hilo de la publicación. | — |

| Campo | Detalle |
|-------|---------|
| **Postcondiciones** | La publicación aparece en el foro del club y en el feed de los miembros. |
| **Garantía mínima** | No se guarda una imagen sin su publicación. |
| **Requerimientos cubiertos** | RF-15, RF-21, RNF-08, RNF-10 |

### CU-10 Votar y reaccionar

| Campo | Detalle |
|-------|---------|
| **ID / Prioridad** | CU-10 / Media |
| **Actor principal** | Estudiante |
| **Descripción** | El estudiante vota (+1/−1) o alterna una de las seis reacciones de una publicación. |
| **Evento activador** | Pulsa una flecha de voto, o «Reaccionar» y una reacción. |
| **Precondiciones** | Sesión iniciada; la publicación existe y no está eliminada. |

| Pasos | Información |
|-------|------------|
| 1. El estudiante pulsa ▲, ▼ o una reacción. | Tipo, ID publicación |
| 2. El navegador envía un formulario `POST` normal con el token CSRF y la página de origen. | Formulario |
| 3. El sistema inserta, cambia o elimina el voto o la reacción. | D8 |
| 4. El sistema redirige a la misma página, anclada en la publicación (`#pub-ID`). | Redirección 303 |
| 5. La página se vuelve a generar con Python mostrando los conteos actualizados. | HTML |

| Campo | Detalle |
|-------|---------|
| **Postcondiciones** | Hay como máximo un voto y una reacción de cada tipo por usuario y publicación. |
| **Garantía mínima** | Funciona en cualquier navegador: no usa JavaScript. |
| **Requerimientos cubiertos** | RF-17, RF-18, RN-05, RN-06 |

### CU-12 Proponer evento

| Campo | Detalle |
|-------|---------|
| **ID / Prioridad** | CU-12 / Alta |
| **Actor principal** | Miembro activo |
| **Otros participantes** | Líder o capitán (revisa en CU-15) |
| **Descripción** | El miembro llena el formulario de propuesta de evento. |
| **Evento activador** | Pulsa **Proponer evento** en la pestaña Eventos del club. |
| **Precondiciones** | Membresía activa. |

| Pasos | Información |
|-------|------------|
| 1. El miembro abre el formulario. | — |
| 2. Llena título, descripción, fecha y hora, lugar, cupo y recursos. | Propuesta |
| 3. El sistema valida campos obligatorios, que la fecha sea futura y el cupo numérico. | RN-07 |
| 4. Guarda la propuesta con estado **pendiente**. | D10 |
| 5. Muestra la propuesta en "Mis propuestas" y en la bandeja de los responsables. | — |

| Campo | Detalle |
|-------|---------|
| **Postcondiciones** | Existe una propuesta pendiente asociada al club. |
| **Requerimientos cubiertos** | RF-24, RF-26 |

### CU-15 Revisar propuesta de evento

| Campo | Detalle |
|-------|---------|
| **ID / Prioridad** | CU-15 / Alta |
| **Actor principal** | Capitán o Líder |
| **Descripción** | El responsable aprueba o rechaza una propuesta, con un comentario. |
| **Evento activador** | Abre la bandeja de propuestas pendientes del club. |
| **Precondiciones** | Rol líder o capitán activo; propuesta pendiente. |

| Pasos | Información |
|-------|------------|
| 1. El responsable ve la lista de propuestas pendientes. | D10 |
| 2. Elige **Aprobar** o **Rechazar** y escribe un comentario opcional. | Decisión |
| 3. El sistema verifica permisos y estado (árbol de decisión 3.6.3). | D5, D10 |
| 4. Guarda estado, revisor, comentario y fecha. | D10 |
| 5. Si se aprueba, el evento aparece en el club y en **Próximos eventos**. | — |

| Campo | Detalle |
|-------|---------|
| **Postcondiciones** | La propuesta ya no está pendiente. |
| **Requerimientos cubiertos** | RF-25, RF-27 |

### CU-18 Aprobar creación de club

| Campo | Detalle |
|-------|---------|
| **ID / Prioridad** | CU-18 / Alta |
| **Actor principal** | Administrador |
| **Descripción** | El administrador revisa una solicitud de club y la aprueba o rechaza. |
| **Precondiciones** | Solicitud pendiente; el nombre del club no existe todavía. |

| Pasos | Información |
|-------|------------|
| 1. El administrador abre el panel y ve las solicitudes pendientes. | D4 |
| 2. Pulsa **Aprobar** o **Rechazar** con un comentario. | — |
| 3. Si aprueba: crea el club en D3 y la membresía del solicitante como **líder activo** en D5, en una sola transacción. | D3, D5 |
| 4. Marca la solicitud como revisada. | D4 |

| Campo | Detalle |
|-------|---------|
| **Garantía mínima** | Si falla cualquier paso se deshace todo (transacción). |
| **Requerimientos cubiertos** | RF-05, RN-02, RN-08 |

### CU-23 Confirmar asistencia

| Campo | Detalle |
|-------|---------|
| **ID / Prioridad** | CU-23 / Alta (pedido en la encuesta) |
| **Actor principal** | Estudiante |
| **Descripción** | El estudiante confirma o cancela su asistencia a un evento aprobado. |
| **Precondiciones** | Sesión iniciada; evento aprobado y futuro. |

| Pasos | Información |
|-------|------------|
| 1. Abre el calendario o los eventos del club y pulsa **Confirmar asistencia**. | Evento |
| 2. El sistema verifica que el evento sea futuro y que haya cupo. | D10, D11 |
| 3. Registra la asistencia y vuelve al mismo evento con «Asistirás» y el conteo actualizado. | D11 |
| 4. Si faltan 48 h o menos, el evento aparece como recordatorio en el inicio y en Notificaciones. | — |

| Campo | Detalle |
|-------|---------|
| **Extensión** | 2a. Sin cupo: muestra «El evento ya alcanzó su cupo». 1a. Si ya había confirmado, el botón cancela la asistencia. |
| **Requerimientos cubiertos** | RF-32, RF-34, RN-12 |

### CU-26 / CU-27 Solicitar ser capitán y aprobarlo

| Campo | Detalle |
|-------|---------|
| **Actores** | Miembro (solicita) y Administración (aprueba) |
| **Descripción** | Un miembro pide ser capitán de su club; la administración aprueba o rechaza la petición. |
| **Precondiciones** | Membresía activa con rol miembro; sin otra solicitud pendiente en ese club. |

| Pasos | Información |
|-------|------------|
| 1. En la cabecera del club, el miembro pulsa **Solicitar ser capitán** y escribe un motivo opcional. | Motivo |
| 2. El sistema guarda la solicitud pendiente y notifica a la administración. | D13, D12 |
| 3. La administración revisa la solicitud en su panel y pulsa **Aprobar** o **Rechazar**. | D13 |
| 4. Si aprueba, la membresía pasa a rol capitán; en ambos casos se notifica al miembro. | D5, D12 |

| Campo | Detalle |
|-------|---------|
| **Alternativa** | El líder del club puede nombrar capitanes directamente desde la pestaña Miembros (CU-17). |
| **Requerimientos cubiertos** | RF-37, RN-13 |

## 4.3 Diagramas de actividades

### Unirse a un club

```mermaid
flowchart TD
    I((Inicio)) --> A["Abrir página del club"]
    A --> B{"¿Ya es miembro?"}
    B -- Sí --> M["Mostrar estado actual"] --> F((Fin))
    B -- No --> C["Pulsar Unirme"]
    C --> D{"¿Requiere aprobación?"}
    D -- No --> E["Crear membresía activa"] --> G["Ver foro, chat y eventos"] --> F
    D -- Sí --> H["Crear membresía pendiente"]
    H --> J["Capitán / Líder revisa"]
    J --> K{"¿Acepta?"}
    K -- Sí --> L["Activar membresía"] --> G
    K -- No --> N["Eliminar solicitud"] --> F
```

### Proponer y revisar un evento (con carriles)

```mermaid
flowchart LR
    subgraph Miembro
        a1((Inicio)) --> a2["Llenar formulario"] --> a3["Enviar"]
        a6["Corregir datos"] --> a3
        a9["Ver estado de la propuesta"] --> a10((Fin))
    end
    subgraph Sistema
        b1{"¿Datos válidos?"}
        b2["Guardar como pendiente"]
        b5["Guardar decisión"]
        b6["Publicar en próximos eventos"]
    end
    subgraph Responsable
        c1["Revisar propuesta"] --> c2{"¿Aprobar?"}
    end
    a3 --> b1
    b1 -- No --> a6
    b1 -- Sí --> b2 --> c1
    c2 -- Sí --> b5
    c2 -- No --> b5
    b5 -- "aprobada" --> b6 --> a9
    b5 -- "rechazada" --> a9
```

## 4.4 Diagramas de secuencia

### Iniciar sesión

```mermaid
sequenceDiagram
    actor U as Estudiante
    participant N as Navegador
    participant S as Servidor (Manejador)
    participant R as Enrutador
    participant C as controladores.cuentas
    participant Sg as seguridad
    participant BD as SQLite

    U->>N: Escribe CIF y contraseña
    N->>S: POST /acceder (cif, contrasena, csrf)
    S->>R: resolver("POST", "/acceder")
    R-->>S: cuentas.acceder
    S->>C: acceder(peticion)
    C->>BD: SELECT usuario WHERE cif = ?
    BD-->>C: fila (hash, sal, activo)
    C->>Sg: verificar_contrasena(contrasena, sal, hash)
    Sg-->>C: verdadero
    C->>BD: rol de la cuenta (rol_global y membresías: líder > capitán > estudiante)
    C->>Sg: crear_sesion(usuario_id, rol)
    Sg->>BD: INSERT INTO sesiones
    Sg-->>C: token
    C-->>S: Respuesta 303 → /  + Set-Cookie: sesion=token
    S-->>N: 303 See Other
    N->>S: GET / (cookie)
    S-->>N: 200 Feed de inicio
```

### Alternar una reacción

```mermaid
sequenceDiagram
    actor U as Estudiante
    participant N as Navegador
    participant S as Servidor
    participant F as controladores.foro
    participant Rp as repositorios.foro
    participant BD as SQLite

    U->>N: Pulsa «Reaccionar» y elige ❤️
    N->>S: POST /publicaciones/42/reaccion (tipo, csrf, siguiente)
    S->>F: reaccionar(peticion, id=42)
    F->>Rp: alternar_reaccion(usuario, 42, tipo)
    Rp->>BD: SELECT reacción existente
    alt ya existe
        Rp->>BD: DELETE
    else no existe
        Rp->>BD: INSERT
    end
    F-->>S: Respuesta 303 hacia la página de origen + ancla de la publicación
    S-->>N: 303 See Other
    N->>S: GET de la página de origen
    S-->>N: 200 HTML con los conteos nuevos (generado con Python)
    N-->>U: Muestra la misma publicación actualizada
```

### Chat del club (marco con recarga automática, sin JavaScript)

```mermaid
sequenceDiagram
    actor U as Miembro
    participant N as Navegador
    participant S as Servidor
    participant Ch as controladores.chat
    participant BD as SQLite

    U->>N: Abre la pestaña Chat
    N->>S: GET /clubes/club-de-cine/chat
    S-->>N: Página con un marco (iframe) de mensajes y el formulario
    loop cada 5 segundos (meta refresh dentro del marco)
        N->>S: GET /clubes/club-de-cine/chat/mensajes
        S->>Ch: mensajes(peticion)
        Ch->>BD: SELECT últimos 60 mensajes del club
        Ch-->>N: HTML del marco
    end
    U->>N: Escribe y pulsa Enviar
    N->>S: POST /clubes/club-de-cine/chat (contenido, csrf)
    S->>Ch: enviar(peticion)
    Ch->>BD: INSERT INTO mensajes_chat
    Ch-->>N: 303 hacia /clubes/club-de-cine/chat
```

## 4.5 Diagrama de clases

### Clases del dominio (entidades)

```mermaid
classDiagram
    direction LR
    class Usuario {
        +int id
        +str cif
        +str nombre
        +str correo
        +str carrera
        +str rol_global
        +bool activo
        +es_admin() bool
    }
    class Club {
        +int id
        +str nombre
        +str slug
        +str descripcion
        +bool requiere_aprobacion
        +str estado
    }
    class SolicitudClub {
        +int id
        +str nombre
        +str justificacion
        +str estado
        +aprobar(admin)
        +rechazar(admin, comentario)
    }
    class Membresia {
        +str rol
        +str estado
        +datetime unido_en
        +es_responsable() bool
    }
    class Anuncio {
        +int id
        +str titulo
        +str contenido
        +bool fijado
        +es_general() bool
    }
    class Publicacion {
        +int id
        +str titulo
        +str contenido
        +str imagen
        +int puntaje
    }
    class Comentario {
        +int id
        +str contenido
    }
    class Voto {
        +int valor
    }
    class Reaccion {
        +str tipo
    }
    class MensajeChat {
        +int id
        +str contenido
    }
    class PropuestaEvento {
        +int id
        +str titulo
        +datetime fecha_inicio
        +str lugar
        +int cupo
        +str estado
        +aprobar(revisor, comentario)
        +rechazar(revisor, comentario)
    }

    Usuario "1" -- "0..*" Membresia
    Club "1" -- "1..*" Membresia
    Usuario "1" -- "0..*" SolicitudClub : solicita
    Club "0..1" -- "0..*" Anuncio : "vacío = general"
    Usuario "1" -- "0..*" Anuncio : publica
    Club "1" -- "0..*" Publicacion
    Usuario "1" -- "0..*" Publicacion : escribe
    Publicacion "1" *-- "0..*" Comentario
    Comentario "0..1" -- "0..*" Comentario : responde a
    Publicacion "1" *-- "0..*" Voto
    Publicacion "1" *-- "0..*" Reaccion
    Club "1" *-- "0..*" MensajeChat
    Club "1" -- "0..*" PropuestaEvento
    Usuario "1" -- "0..*" PropuestaEvento : propone
```

### Clases de la arquitectura (código)

```mermaid
classDiagram
    direction TB
    class Manejador {
        <<BaseHTTPRequestHandler>>
        +do_GET()
        +do_POST()
        -atender(metodo)
        -servir_estatico(ruta)
    }
    class Peticion {
        +str metodo
        +str ruta
        +dict consulta
        +dict formulario
        +dict archivos
        +dict cookies
        +Fila usuario
        +Fila sesion
    }
    class Respuesta {
        +int estado
        +list cabeceras
        +bytes cuerpo
        +html(texto)$
        +redirigir(url)$
    }
    class Enrutador {
        -list rutas
        +ruta(metodo, patron)
        +resolver(metodo, ruta) tuple
    }
    class MotorPlantillas {
        -str carpeta
        -dict cache
        +renderizar(nombre, contexto) str
        -compilar(texto) Nodo
    }
    class BaseDatos {
        +conectar() Connection
        +inicializar(ruta)
        +sembrar_datos()
    }
    class Seguridad {
        +hash_contrasena(texto)$
        +verificar_contrasena(texto, sal, hash)$
        +crear_sesion(usuario_id)$
        +validar_csrf(peticion)$
    }
    class Controlador {
        <<módulo>>
        +funcion(peticion, **params) Respuesta
    }
    class Repositorio {
        <<módulo>>
        +consultas SQL parametrizadas
    }

    Manejador ..> Peticion : crea
    Manejador ..> Enrutador : consulta
    Enrutador ..> Controlador : despacha
    Controlador ..> Repositorio : usa
    Controlador ..> MotorPlantillas : usa
    Controlador ..> Respuesta : devuelve
    Controlador ..> Seguridad : usa
    Repositorio ..> BaseDatos : usa
```

## 4.6 Diagramas de estados

### Membresía

```mermaid
stateDiagram-v2
    [*] --> Pendiente : unirse (club con aprobación)
    [*] --> Activa : unirse (club abierto)
    Pendiente --> Activa : responsable acepta
    Pendiente --> [*] : responsable rechaza
    Activa --> Activa : cambio de rol (miembro ⇄ capitán, transferir liderazgo)
    Activa --> [*] : salir / expulsión
```

### Propuesta de evento

```mermaid
stateDiagram-v2
    [*] --> Pendiente : miembro envía formulario
    Pendiente --> Aprobada : responsable aprueba (fecha futura)
    Pendiente --> Rechazada : responsable rechaza
    Aprobada --> Realizado : pasa la fecha del evento
    Rechazada --> [*]
    Realizado --> [*]
```

### Solicitud para ser capitán

```mermaid
stateDiagram-v2
    [*] --> Pendiente : miembro solicita (una por club)
    Pendiente --> Aprobada : administración aprueba / el miembro pasa a capitán
    Pendiente --> Rechazada : administración rechaza
    Aprobada --> [*]
    Rechazada --> [*]
```

### Asistencia a un evento

```mermaid
stateDiagram-v2
    [*] --> SinConfirmar
    SinConfirmar --> Confirmada : confirmar (si hay cupo y el evento es futuro)
    Confirmada --> SinConfirmar : cancelar
    Confirmada --> Recordatorio : faltan 48 h o menos
    Recordatorio --> [*] : el evento ocurre
```

### Solicitud de creación de club

```mermaid
stateDiagram-v2
    [*] --> Pendiente : estudiante solicita
    Pendiente --> Aprobada : administrador aprueba / crea club y líder
    Pendiente --> Rechazada : administrador rechaza
    Aprobada --> [*]
    Rechazada --> [*]
```
