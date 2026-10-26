# 10. Seguridad

Este documento resume cómo Vortex Clubs protege las cuentas y los datos. Todo está hecho con la
biblioteca estándar de Python y SQLite, sin dependencias externas ni JavaScript.

## 10.1 Contraseñas

| Medida | Detalle |
|--------|---------|
| Cifrado de una sola vía | Las contraseñas nunca se guardan en claro. Se derivan con **PBKDF2-HMAC-SHA256** con **600 000 iteraciones** (recomendación de OWASP) y una **sal aleatoria de 16 bytes** por usuario (`vortex/seguridad.py`). |
| Formato con versión | El hash guarda el algoritmo y las iteraciones (`pbkdf2_sha256$600000$…`). Las contraseñas guardadas con el formato anterior (200 000 iteraciones) se vuelven a cifrar con el formato actual la próxima vez que la persona inicia sesión. |
| Comparación en tiempo constante | `hmac.compare_digest` evita que el tiempo de respuesta revele cuántos caracteres coinciden. |
| Mismo costo si el CIF no existe | Al fallar el acceso se calcula igual un hash falso: el tiempo de respuesta no revela qué CIF están registrados, y el mensaje es siempre «CIF o contraseña incorrectos». |
| Política de contraseñas | De 8 a 128 caracteres, con letras y números, sin incluir el CIF y fuera de una lista de claves comunes (`formularios.contrasena_segura`). |
| Cambio de contraseña | En **Mi perfil → Cambiar contraseña**. Pide la contraseña actual y, al guardar, cierra la sesión en todos los demás dispositivos. |
| Contraseña inicial del administrador | Si la cuenta de administración sigue con la clave inicial, todas sus páginas muestran un aviso para cambiarla. La clave inicial se puede definir antes del primer arranque con `VORTEX_ADMIN_CLAVE`. |

## 10.2 Sesiones y cookies

- El token de sesión es aleatorio (`secrets.token_urlsafe(32)`, 256 bits). En la base de datos **solo se
  guarda su huella SHA-256**: si alguien copiara el archivo de la base, no podría entrar con esas sesiones.
- Se crea un token nuevo en cada inicio de sesión (evita la fijación de sesión) y se borra al salir.
- Las sesiones vencen a los 7 días y se invalidan si la cuenta se desactiva.
- Cookies con `HttpOnly` (no accesibles desde scripts) y `SameSite=Lax`. Con `VORTEX_HTTPS=1` además
  llevan `Secure` y se envía `Strict-Transport-Security`.

## 10.3 Ataques de adivinación y abuso

| Límite | Valor |
|--------|-------|
| Intentos fallidos por IP + CIF | 5 en 5 minutos |
| Intentos fallidos por IP (probar muchas cuentas) | 20 en 15 minutos |
| Cuentas nuevas por IP | 10 por hora |
| Tamaño máximo de una petición | 6 MB (imágenes de hasta 5 MB) |
| Conexiones colgadas | se cortan a los 30 segundos |

## 10.4 Vulnerabilidades web (OWASP Top 10)

| Riesgo | Cómo se evita |
|--------|---------------|
| Inyección SQL | Todas las consultas usan parámetros `?` / `:nombre`. Los únicos nombres de tabla armados en el código salen de diccionarios fijos, nunca del usuario. |
| XSS (código malicioso en textos) | El motor de plantillas **escapa todo** por omisión. Además, la política de contenido (`Content-Security-Policy: script-src 'none'`) impide ejecutar cualquier script, porque el sitio no usa JavaScript. |
| CSRF (formularios falsos desde otro sitio) | Cada formulario POST lleva un token secreto de la sesión, que se compara en tiempo constante. `SameSite=Lax` y `form-action 'self'` refuerzan la protección. |
| Clickjacking | `X-Frame-Options: SAMEORIGIN` y `frame-ancestors 'self'`: solo el propio sitio puede mostrar sus páginas en marcos (lo usan el chat y los votos). |
| Redirecciones abiertas | El campo `siguiente` solo acepta rutas internas; se rechazan `//sitio`, barras invertidas, espacios y caracteres de control (`acceso.destino_seguro`). |
| Control de acceso | Cada ruta comprueba la sesión y el rol (`requiere_sesion`, `requiere_admin`, permisos por club). Un estudiante solo puede editar o eliminar lo suyo. |
| Archivos subidos | Solo PNG, JPG, GIF o WEBP, comprobados por su **firma binaria** (no por el nombre), de hasta 5 MB, guardados con un nombre aleatorio. Las rutas de archivos se validan para impedir salir de su carpeta. |
| Datos sensibles en caché | Las páginas dinámicas se envían con `Cache-Control: no-store`: el botón «atrás» no muestra datos de otra sesión en computadoras compartidas. |
| Información del servidor | No se revelan la versión de Python ni errores internos: el usuario ve un mensaje genérico y el detalle queda en la consola. |

## 10.5 Cabeceras de seguridad

`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`,
`Referrer-Policy: same-origin`, `Permissions-Policy` (sin cámara, micrófono ni ubicación),
`Cross-Origin-Opener-Policy` y `Cross-Origin-Resource-Policy: same-origin`.

## 10.6 Pruebas

`pruebas/test_seguridad.py` comprueba el formato del hash, la actualización de contraseñas antiguas,
la política de contraseñas, el cambio de contraseña (con cierre de las demás sesiones), que la base no
guarde el token de sesión, las cabeceras, el rechazo de peticiones malformadas, el límite por IP y las
redirecciones internas.
