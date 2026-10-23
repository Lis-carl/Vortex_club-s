# Vortex Club's

Plataforma web de **clubes universitarios**: únete a clubes, consulta anuncios generales y por club,
conoce a líderes, capitanes y miembros, propón eventos, conversa en el chat del club y participa en
un foro estilo Reddit con votos y reacciones. Interfaz sobria e institucional, inspirada en **UAM Virtual**.

> Proyecto académico construido siguiendo la metodología de *Análisis y diseño de sistemas*
> (Kendall & Kendall, 8.ª ed.): **primero la documentación y diagramación del diseño, después el código.**

## Restricciones del proyecto (y cómo se cumplen)

| Restricción | Cumplimiento |
|-------------|--------------|
| Solo **Python**, **sin librerías externas**, todo manual | Biblioteca estándar únicamente: servidor con `http.server`, enrutador, motor de plantillas, sesiones, formularios multipart y seguridad programados a mano. No hay `requirements.txt` porque no hay dependencias. |
| **Sin JavaScript** | El navegador solo recibe HTML y CSS generados por Python. Votos y reacciones son formularios; las confirmaciones y menús usan `<details>`; el chat se actualiza con un marco que se recarga solo. La política de contenido bloquea scripts (`script-src 'none'`). |
| Base de datos **solo SQLite**, y diagramada | Módulo estándar `sqlite3`. Esquema en [`sql/esquema.sql`](sql/esquema.sql) y diagrama entidad-relación en [`docs/05_diseno_base_datos.md`](docs/05_diseno_base_datos.md). |
| Diagramación **antes** de programar | Documentos 01 a 07 de [`docs/`](docs/). |
| Interfaz profesional, similar a UAM Virtual | Ver [`docs/06_diseno_interfaz.md`](docs/06_diseno_interfaz.md). |

## Ejecutar

Requiere **Python 3.10 o superior**. No hay nada que instalar.

```bash
python app.py
```

Abre <http://127.0.0.1:8000>. La primera vez se crea la base de datos **vacía**, con los 14 clubes
oficiales de la Dirección de Vida Estudiantil (sin miembros) y una cuenta de administración:

| Cuenta | CIF | Contraseña |
|--------|-----|-----------|
| Administración | `00000001` | `admin123` |

Los estudiantes crean su propia cuenta con su CIF. La administración asigna el líder de cada club
desde su panel. Para un uso real cambia la clave inicial: ver [`docs/09_implementacion.md`](docs/09_implementacion.md).

Opciones: `--puerto 8080`, `--host 0.0.0.0` (visible en la red local).

## Probar

```bash
python -m unittest discover -s pruebas -t .
```

58 pruebas (unidad + integración con un servidor real y SQLite temporal). No tocan tu base de datos.

## Funciones

| Función | Dónde |
|---------|-------|
| Registro e inicio de sesión con CIF | `/registro`, `/acceder` |
| Catálogo de clubes con búsqueda y categorías; unirse (abierto o con aprobación) | `/clubes` |
| Anuncios **generales** (administración) y **por club** (líder/capitanes) | `/anuncios`, `/clubes/<club>/anuncios` |
| Ver **líder, capitanes y miembros**; nombrar capitanes, expulsar, transferir liderazgo | `/clubes/<club>/miembros` |
| Foro estilo Reddit: publicaciones con imagen, comentarios anidados, votos ▲▼ | `/clubes/<club>` |
| **Reacciones** (👍 ❤️ 😂 😮 😢 🔥) en cada publicación | en cada publicación |
| **Chat** por club, solo miembros, actualizado cada 5 segundos | `/clubes/<club>/chat` |
| **Formulario de propuesta de evento** y flujo de aprobación; calendario de eventos | `/clubes/<club>/eventos`, `/eventos` |
| Solicitar la creación de un club | `/clubes/solicitar` |
| Panel de administración: solicitudes, **asignación de líderes**, clubes, cuentas, estadísticas | `/admin` |

## Documentación

| # | Documento | Contenido (capítulo de Kendall) |
|---|-----------|--------------------------------|
| 1 | [Planeación](docs/01_planeacion.md) | Problema, objetivos, alcance, viabilidad, cronograma Gantt, riesgos (cap. 1 y 3) |
| 2 | [Requerimientos](docs/02_requerimientos.md) | Actores, técnicas de recopilación, **requerimientos funcionales y no funcionales**, reglas de negocio, matriz de permisos, datos iniciales (cap. 4 y 5) |
| 3 | [Análisis de procesos](docs/03_analisis_procesos.md) | **Diagramas de flujo de datos** (contexto, nivel 0 y 1), **diccionario de datos**, español estructurado, tabla y árbol de decisión (cap. 7 a 9) |
| 4 | [Modelado UML](docs/04_modelado_uml.md) | **Casos de uso** con escenarios, actividades, secuencia, **clases**, estados (cap. 2 y 10) |
| 5 | [Base de datos](docs/05_diseno_base_datos.md) | **Diagrama entidad-relación de SQLite**, normalización a 3FN, diccionario de tablas (cap. 13) |
| 6 | [Interfaz](docs/06_diseno_interfaz.md) | Referentes, guía de estilo, logotipo VC, mapa de navegación, prototipos, formularios y validaciones (cap. 11, 12, 14, 15) |
| 7 | [Arquitectura](docs/07_arquitectura.md) | Capas, módulos de la biblioteca estándar, interfaz sin JavaScript, rutas, seguridad |
| 8 | [Pruebas](docs/08_pruebas.md) | Estrategia, trazabilidad requerimiento → prueba, pruebas de seguridad (cap. 16) |
| 9 | [Implementación](docs/09_implementacion.md) | Instalación, primeros pasos, conversión piloto, respaldo, evaluación |
| — | [Manual de usuario](docs/manual_usuario.md) | Guía por rol: estudiante, capitán, líder, administración |

Los diagramas están escritos en [Mermaid](https://mermaid.js.org/): GitHub los dibuja directamente al abrir los `.md`.
El libro base (Kendall) y las capturas usadas como referente visual se guardan localmente en
`referencias/` y **no se suben** al repositorio (el libro tiene derechos de autor y una captura muestra un CIF real).

## Estructura

```text
app.py            punto de entrada
vortex/           servidor, enrutador, plantillas, seguridad, repositorios (SQL) y controladores
plantillas/       HTML        estatico/   CSS y logotipo VC
sql/esquema.sql   base de datos pruebas/    unittest      docs/   documentación
```

La explicación de cada módulo está en [`docs/07_arquitectura.md`](docs/07_arquitectura.md).

## Seguridad en breve

Contraseñas con PBKDF2-HMAC-SHA256 y sal; sesiones con cookie `HttpOnly` + `SameSite=Lax`; token CSRF en
todos los formularios; escapado automático contra XSS; SQL siempre con parámetros; subida de imágenes
validada por firma binaria; límite de intentos de acceso; sin JavaScript y con cabeceras CSP y `X-Frame-Options`.
