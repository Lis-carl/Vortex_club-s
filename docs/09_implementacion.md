# 9. Implementación y evaluación

> Fase 7 del CVDS (Kendall, cap. 16): puesta en marcha, capacitación, respaldo y evaluación.

## 9.1 Requisitos del equipo servidor

| Elemento | Requisito |
|----------|-----------|
| Sistema operativo | Windows, Linux o macOS |
| Python | 3.10 o superior (se probó con 3.14) |
| Librerías | **Ninguna.** Solo biblioteca estándar |
| Navegador de los usuarios | Cualquiera moderno; **no necesita JavaScript** |
| Disco | ~50 MB + espacio para imágenes subidas |
| Red | Puerto 8000 libre (configurable) |

## 9.2 Instalación

```bash
git clone https://github.com/Lis-carl/Vortex_club-s.git
cd Vortex_club-s
python app.py
```

La primera vez se crea `datos/vortex.db` **vacía**, solo con:

- la cuenta de administración;
- los 15 clubes oficiales (los 14 del afiche de la Dirección de Vida Estudiantil y el Club de Esports), sin miembros ni líder.

No hay usuarios, publicaciones, anuncios ni eventos de ejemplo. Abre <http://127.0.0.1:8000>.

| Opción | Efecto |
|--------|--------|
| `--puerto 8080` | Cambia el puerto |
| `--host 0.0.0.0` | Permite que otros equipos de la red local entren con la IP del servidor |

### Cuenta inicial

| Rol | CIF | Contraseña |
|-----|-----|-----------|
| Administración | `00000001` | `admin123` |

> **Para un uso real:** define la variable de entorno `VORTEX_ADMIN_CLAVE` **antes del primer
> arranque** para que la cuenta de administración nazca con otra contraseña.

```bash
# Linux / macOS
VORTEX_ADMIN_CLAVE='una-clave-larga' python app.py
```

```powershell
# Windows (PowerShell)
$env:VORTEX_ADMIN_CLAVE = 'una-clave-larga'; python app.py
```

### Primeros pasos después de instalar

1. Cada líder de club crea su cuenta en **Crear cuenta** con su CIF.
2. La administración inicia sesión, entra a **Administración → Clubes**,
   escribe el CIF del líder en la fila de su club y pulsa **Asignar**.
3. El líder inicia sesión (la plataforma lo reconoce como líder), entra a su club → **Configuración** y escribe la
   descripción. Puede nombrar capitanes desde **Miembros**.
4. Los estudiantes se registran, se unen a los clubes y pueden **solicitar ser capitán**; la
   administración aprueba esas solicitudes desde su panel.

### Variables de entorno

| Variable | Para qué sirve |
|----------|----------------|
| `VORTEX_BD` | Ruta alternativa del archivo SQLite |
| `VORTEX_SUBIDAS` | Carpeta alternativa para las imágenes |
| `VORTEX_ADMIN_CLAVE` | Contraseña inicial de la administración |
| `VORTEX_ITERACIONES` | Iteraciones de PBKDF2 (**solo pruebas**; por omisión 600 000) |

## 9.3 Estrategia de conversión

Es un sistema nuevo (no reemplaza a otro), por lo que se usa **conversión piloto**:

1. **Semana 1:** dos o tres clubes del catálogo usan la plataforma; el resto sigue como hoy.
2. **Semana 2:** se suman más clubes y se corrigen los problemas detectados.
3. **Semana 3:** feria de clubes; se anuncia la plataforma a toda la universidad.

## 9.4 Capacitación

| Público | Material | Duración |
|---------|----------|----------|
| Estudiantes | [Manual de usuario](manual_usuario.md), secciones 1 a 4 | 10 min (autoguiado) |
| Líderes y capitanes | Manual de usuario, secciones 5 y 6 | 30 min (taller) |
| Administración | Manual de usuario, sección 7 | 20 min |

## 9.5 Respaldo y recuperación

| Tarea | Cómo |
|-------|------|
| Respaldo | Detener el servidor y copiar la carpeta `datos/` y la carpeta `subidas/` |
| Respaldo en caliente | `sqlite3 datos/vortex.db ".backup respaldo.db"` (si se tiene la herramienta `sqlite3`) o copiar `vortex.db` junto con `vortex.db-wal` |
| Recuperación | Detener el servidor, reemplazar `datos/vortex.db` y `subidas/` por el respaldo, volver a iniciar |
| Reiniciar de cero | Borrar la carpeta `datos/` y arrancar de nuevo |

## 9.6 Mantenimiento

- **Correctivo:** los errores inesperados se imprimen con su traza en la consola del servidor y el
  usuario ve una página de error con el diseño de la plataforma.
- **Evolutivo:** cada función nueva sigue el mismo camino: tabla en `sql/esquema.sql` →
  repositorio → controlador → plantilla → prueba. Las tablas nuevas se agregan con
  `CREATE TABLE IF NOT EXISTS`, por lo que el esquema se puede volver a ejecutar sin perder datos.
  Para columnas nuevas en tablas existentes se necesita un `ALTER TABLE` manual.
- **Catálogo de clubes:** los clubes nuevos se crean con la solicitud de club (o agregándolos a
  `vortex/semilla.py` antes de crear la base de datos).
- **Limpieza de sesiones vencidas:** se borran automáticamente en cada inicio de sesión.

## 9.7 Evaluación del sistema (después del piloto)

Criterios para decidir si el sistema cumple sus objetivos (sección 1.4):

| Objetivo | Indicador | Meta |
|----------|-----------|------|
| Descubrir clubes | % de estudiantes del piloto que se unen al menos a un club | ≥ 50 % |
| Comunicación | % de anuncios vistos (comentados o reaccionados) | ≥ 30 % |
| Estructura del club | Clubes con líder asignado y al menos un capitán | 100 % |
| Eventos | Propuestas revisadas en menos de 3 días | ≥ 80 % |
| Usabilidad | Encuesta de satisfacción (escala 1 a 5) | ≥ 4 |
| Disponibilidad | Interrupciones del servidor durante el piloto | 0 |

Instrumento: la misma encuesta tipo Likert de la sección 2.2, más las estadísticas del panel de
administración (usuarios, clubes, publicaciones y eventos).
