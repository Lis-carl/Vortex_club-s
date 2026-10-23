# 8. Pruebas y aseguramiento de la calidad

> Kendall, cap. 16: *Aseguramiento e implementación de la calidad* (pruebas de unidad, de
> integración y de aceptación; trazabilidad con los requerimientos).

## 8.1 Estrategia

| Nivel | Qué se prueba | Herramienta | Archivo |
|-------|---------------|-------------|---------|
| Unidad | Motor de plantillas, enrutador, hash de contraseñas, límite de intentos, lectura de formularios, validación de imágenes, utilidades | `unittest` | [`pruebas/test_unidades.py`](../pruebas/test_unidades.py) |
| Integración | Servidor real en un hilo + base SQLite temporal + cliente HTTP con cookies que recorre cada caso de uso | `unittest` + `urllib` | [`pruebas/test_integracion.py`](../pruebas/test_integracion.py) |
| Aceptación | Recorrido manual del manual de usuario en el navegador (escritorio y celular) | Navegador | [`manual_usuario.md`](manual_usuario.md) |

Todo se ejecuta sin instalar nada (solo biblioteca estándar):

```bash
python -m unittest discover -s pruebas -t .
```

Cada clase de integración crea su propia base de datos temporal (con datos de ejemplo), por lo que
las pruebas **nunca tocan** `datos/vortex.db`. Se baja PBKDF2 a 1 000 iteraciones **solo** en las
pruebas (`VORTEX_ITERACIONES`) para que corran en segundos.

## 8.2 Resultado de la última ejecución

```text
Ran 55 tests in ~11 s
OK
```

22 pruebas de unidad y 33 de integración.

## 8.3 Matriz de trazabilidad (requerimiento → prueba)

| Requerimiento | Prueba que lo cubre |
|---------------|--------------------|
| RF-01 Registro | `PruebasAcceso.test_registro` (validaciones, duplicados, hash) |
| RF-02 Acceso y salida | `test_login_correcto_y_cerrar_sesion`, `test_login_incorrecto`, `test_paginas_publicas_y_redireccion` |
| RF-03 Perfil | `PruebasAdmin.test_perfil` |
| RF-04 Catálogo y búsqueda | `PruebasClubes.test_catalogo_y_busqueda` |
| RF-05 Solicitar creación de club | `test_solicitar_club_y_aprobacion_del_admin` |
| RF-06 Unirse (abierto / con aprobación) | `test_unirse_club_abierto_y_salir`, `test_unirse_con_aprobacion` |
| RF-07 Resolver solicitudes de ingreso | `test_unirse_con_aprobacion` |
| RF-08 Salir del club | `test_unirse_club_abierto_y_salir`, `test_gestion_de_roles_y_liderazgo` (el líder no puede salir) |
| RF-09 Ver líder, capitanes y miembros | revisión manual en el navegador y `test_gestion_de_roles_y_liderazgo` |
| RF-10 Roles y liderazgo | `test_gestion_de_roles_y_liderazgo` |
| RF-11 Editar club | `test_editar_club_solo_lider` |
| RF-12 Anuncios generales | `test_anuncios_generales_y_de_club` |
| RF-13 Anuncios del club | `test_anuncios_generales_y_de_club` |
| RF-14 Fijar y eliminar anuncios | `test_anuncios_generales_y_de_club` |
| RF-15 Publicar en el foro | `test_publicar_con_imagen_y_validaciones` |
| RF-16 Comentarios anidados | `test_comentarios_anidados_votos_y_eliminar` |
| RF-17 Votos | `test_votos_ajax`, `test_comentarios_anidados_votos_y_eliminar` |
| RF-18 Reacciones | `test_reacciones` |
| RF-19 Orden Nuevos / Populares | `test_feed_inicio` |
| RF-20 Eliminar contenido (autor / responsable) | `test_moderacion_de_publicaciones`, `test_comentarios_anidados_votos_y_eliminar` |
| RF-21 Feed de inicio | `test_feed_inicio` |
| RF-22 / RF-23 Chat | `PruebasChatYEventos.test_chat` |
| RF-24 Proponer evento | `test_proponer_evento_validaciones` |
| RF-25 Aprobar o rechazar | `test_flujo_de_propuesta_y_aprobacion`, `test_rechazar_propuesta`, `test_no_se_aprueba_evento_pasado` |
| RF-26 Estado de mis propuestas | `test_flujo_de_propuesta_y_aprobacion`, `test_rechazar_propuesta` |
| RF-27 Próximos eventos | `test_flujo_de_propuesta_y_aprobacion` |
| RF-28 / RF-29 / RF-30 Panel de administración | `PruebasAdmin.test_panel_y_cuentas`, `test_sesion_se_invalida_al_desactivar`, `test_desactivar_club` |
| RNF-01, RNF-02, RNF-03 Solo biblioteca estándar y SQLite | Las pruebas corren sin dependencias; revisión de imports (`grep -R "^import\|^from" vortex`) |
| RNF-06 Contraseñas con PBKDF2 | `PruebasSeguridad.test_hash_y_verificacion`, `test_registro` (no se guarda en claro) |
| RNF-07 CSRF | `PruebasAcceso.test_csrf_obligatorio` |
| RNF-08 XSS e inyección SQL | `test_xss_se_escapa`, `test_inyeccion_sql_en_busqueda`, `PruebasPlantillas.test_variable_se_escapa` |
| RNF-09 Cookies y sesión | `test_login_correcto_y_cerrar_sesion`, `test_sesion_se_invalida_al_desactivar` |
| RNF-10 Imágenes | `test_publicar_con_imagen_y_validaciones`, `PruebasFormularios.test_firmas_de_imagen` |
| RNF-12 Arranque con un comando | Verificación manual: `python app.py` crea la base de datos |
| RNF-14 Integridad (índices y claves foráneas) | `test_gestion_de_roles_y_liderazgo` (un solo líder), `test_solicitar_club_y_aprobacion_del_admin` (sin club duplicado) |
| RN-02, RN-03, RN-04, RN-05, RN-06 | Pruebas de roles, chat solo para miembros, reacciones y votos únicos |
| RN-07 Fecha futura | `test_proponer_evento_validaciones` |
| RN-09 Cuenta desactivada no entra | `test_panel_y_cuentas` |

## 8.4 Pruebas de seguridad realizadas

| Amenaza | Intento | Resultado esperado y obtenido |
|---------|---------|-------------------------------|
| CSRF | POST sin token o con token falso | 403 |
| XSS almacenado | Título `<script>alert(1)</script>` y contenido `<img onerror=…>` en publicaciones, comentarios y chat | Se muestra como texto (`&lt;script&gt;`) |
| Inyección SQL | `q=' OR 1=1 --` y `cat=1;DROP TABLE usuarios` | Sin resultados / sin efecto; la tabla sigue existiendo |
| Recorrido de carpetas | `/estatico/../vortex/config.py`, `/estatico/%2e%2e/…`, `/subidas/../app.py` | 404 |
| Archivo malicioso | Subir HTML con extensión `.png`, o una imagen de más de 2 MB | Rechazado con mensaje |
| Fuerza bruta | 5 intentos fallidos seguidos | Bloqueo temporal con mensaje |
| Redirección abierta | `siguiente=//evil.com` al iniciar sesión | Se ignora, redirige a `/` |
| Escalada de privilegios | Miembro intenta aprobar propuestas, publicar anuncios del club, cambiar roles, abrir `/admin` | 403 |
| Enumeración de usuarios | CIF inexistente vs contraseña incorrecta | Mismo mensaje y mismo costo de cálculo |
| Sesión de cuenta desactivada | El administrador desactiva una cuenta con sesión abierta | La siguiente petición vuelve al acceso |

## 8.5 Casos de prueba de aceptación (manuales)

| # | Pasos | Resultado esperado |
|---|-------|--------------------|
| A1 | Abrir `/acceder` en el celular (375 px) | La tarjeta se ve completa, sin desplazamiento horizontal |
| A2 | Iniciar sesión como `26010001` | Se ve el feed con las publicaciones de Robótica y Voluntariado |
| A3 | Pulsar 👍 en una publicación | El contador cambia sin recargar la página; pulsar otra vez lo quita |
| A4 | Abrir el chat de Robótica en dos navegadores con distintos usuarios | El mensaje enviado en uno aparece en el otro en menos de 4 segundos |
| A5 | Cambiar el sistema operativo a modo oscuro | La interfaz se oscurece automáticamente |
| A6 | Navegar solo con el teclado (Tab/Enter) | Todos los botones y enlaces son alcanzables con foco visible |

Estado: **A2, A3 y A5 se ejecutaron** durante el desarrollo (navegador de escritorio, modo oscuro) y
**A1 se ejecutó con el feed de inicio** en 375 px. **A4 y A6 quedan pendientes** para la revisión
final del equipo antes de la entrega.

## 8.6 Limitaciones conocidas

- La consulta periódica del chat (cada 3 s) no es tiempo real puro: se eligió por simplicidad y
  porque `http.server` de la biblioteca estándar no ofrece WebSockets.
- SQLite admite una sola escritura a la vez; para el tamaño de un piloto universitario es suficiente.
- No hay recuperación de contraseña por correo (fuera de alcance de la versión 1).
- No hay cifrado HTTPS en el servidor propio: para producción se recomienda ponerlo detrás de un
  proxy inverso con TLS.
