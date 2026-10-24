"""Registro, acceso, cierre de sesión y perfil."""
from .. import config, seguridad, formularios as frm
from ..acceso import requiere_sesion, destino_seguro, ROLES_ACCESO
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import usuarios, clubes, foro, participacion
from ..vistas import render

# Carreras de la Universidad Americana (UAM) que aparecen en la oferta de clubes.
CARRERAS = ["Ingeniería Industrial", "Ingeniería en Sistemas de Información", "Negocios Internacionales",
            "Economía Empresarial", "Diplomacia y Relaciones Internacionales", "Derecho", "Psicología",
            "Medicina", "Diseño y Comunicación Visual", "Comunicación y Relaciones Públicas",
            "Marketing y Publicidad", "Administración de Empresas"]
_INICIO_POR_ROL = {"estudiante": "/", "capitan": "/gestion", "lider": "/gestion", "admin": "/admin"}
_HASH_FALSO = seguridad.hash_contrasena("contraseña-inexistente")


def _iniciar_sesion(p, usuario_id, destino, rol_acceso="estudiante"):
    token = seguridad.crear_sesion(p.bd, usuario_id, rol_acceso)
    r = Respuesta.redirigir(destino)
    r.cookie("sesion", token, max_age=config.DURACION_SESION_DIAS * 86400)
    return r


@ruta("GET", "/acceder")
def acceder_formulario(p):
    if p.usuario:
        return Respuesta.redirigir("/")
    return render(p, "acceder.html", cif="", error="", rol="estudiante", roles=ROLES_ACCESO,
                  siguiente=destino_seguro(p.consulta.get("siguiente"), ""))


@ruta("POST", "/acceder")
def acceder(p):
    cif = (p.formulario.get("cif") or "").strip()
    contrasena = p.formulario.get("contrasena") or ""
    siguiente = destino_seguro(p.formulario.get("siguiente"), "")
    rol = p.formulario.get("rol") or "estudiante"
    clave = f"{p.ip}|{cif}"

    def fallo(mensaje):
        return render(p, "acceder.html", 401, cif=cif, error=mensaje, siguiente=siguiente,
                      rol=rol if rol in ROLES_ACCESO else "estudiante", roles=ROLES_ACCESO)

    if rol not in ROLES_ACCESO:
        return fallo("Elige un rol válido para ingresar.")

    if seguridad.limite_acceso.bloqueado(clave):
        return fallo("Demasiados intentos fallidos. Espera unos minutos e inténtalo de nuevo.")
    usuario = usuarios.por_cif(p.bd, cif) if frm.RE_CIF.match(cif) else None
    if usuario:
        correcta = seguridad.verificar_contrasena(contrasena, usuario.hash_contrasena, usuario.sal)
    else:   # mismo costo de cálculo para no revelar si el CIF existe
        seguridad.verificar_contrasena(contrasena, *_HASH_FALSO)
        correcta = False
    if not correcta:
        seguridad.limite_acceso.fallo(clave)
        return fallo("CIF o contraseña incorrectos.")
    if not usuario.activo:
        return fallo("Tu cuenta está desactivada. Comunícate con Vida Estudiantil.")
    seguridad.limite_acceso.reiniciar(clave)
    # El rol elegido debe corresponder a la cuenta.
    if rol == "admin" and usuario.rol_global != "admin":
        return fallo("Tu cuenta no tiene permisos de administración. Elige otro rol.")
    if rol in ("capitan", "lider"):
        roles = clubes.roles_de(p.bd, usuario.id)
        if rol not in roles:
            nombre = "capitán" if rol == "capitan" else "líder"
            return fallo(f"Tu cuenta no es {nombre} de ningún club. Ingresa con otro rol.")
    return _iniciar_sesion(p, usuario.id, siguiente or _INICIO_POR_ROL[rol], rol)


@ruta("GET", "/registro")
def registro_formulario(p):
    if p.usuario:
        return Respuesta.redirigir("/")
    return render(p, "registro.html", valores={}, errores=frm.Errores(), carreras=CARRERAS)


@ruta("POST", "/registro")
def registro(p):
    f, errores = p.formulario, frm.Errores()
    cif = (f.get("cif") or "").strip()
    if not frm.RE_CIF.match(cif):
        errores["cif"] = "El CIF debe tener exactamente 8 dígitos."
    elif usuarios.por_cif(p.bd, cif):
        errores["cif"] = "Ya existe una cuenta con ese CIF."
    nombre = frm.texto(f, errores, "nombre", "El nombre", 3, 80)
    correo = frm.texto(f, errores, "correo", "El correo", 5, 120).lower()
    if "correo" not in errores:
        if not frm.RE_CORREO.match(correo):
            errores["correo"] = "Escribe un correo válido."
        elif usuarios.correo_existe(p.bd, correo):
            errores["correo"] = "Ese correo ya está registrado."
    carrera = frm.texto(f, errores, "carrera", "La carrera", 2, 80, obligatorio=False)
    contrasena = f.get("contrasena") or ""
    if len(contrasena) < 6 or len(contrasena) > 128:
        errores["contrasena"] = "La contraseña debe tener entre 6 y 128 caracteres."
    elif contrasena != (f.get("confirmar") or ""):
        errores["confirmar"] = "Las contraseñas no coinciden."
    if errores:
        return render(p, "registro.html", 400, valores={"cif": cif, "nombre": nombre, "correo": correo,
                                                         "carrera": carrera}, errores=errores, carreras=CARRERAS)
    usuario_id = usuarios.crear(p.bd, cif, nombre, correo, carrera, contrasena)
    return _iniciar_sesion(p, usuario_id, "/clubes").con_aviso("ok", f"¡Bienvenido/a, {nombre}! Explora los clubes y únete.")


@ruta("POST", "/salir")
def salir(p):
    if p.sesion:
        seguridad.cerrar_sesion(p.bd, p.sesion.token)
    return Respuesta.redirigir("/acceder").borrar_cookie("sesion")


@ruta("GET", "/perfil/<cif>")
@requiere_sesion
def perfil(p, cif):
    persona = usuarios.por_cif(p.bd, cif)
    if not persona or not persona.activo:
        raise ErrorHttp(404, "No encontramos a esa persona.")
    mis = clubes.mis_clubes(p.bd, persona.id)
    publicaciones = foro.listar(p.bd, p.usuario.id, autor_id=persona.id, limite=10)
    solicitudes = clubes.solicitudes_de(p.bd, persona.id) if persona.id == p.usuario.id else []
    return render(p, "perfil.html", persona=persona, clubes_persona=mis, publicaciones=publicaciones,
                  participacion=participacion.de_usuario(p.bd, persona.id),
                  solicitudes=solicitudes, es_yo=persona.id == p.usuario.id)
