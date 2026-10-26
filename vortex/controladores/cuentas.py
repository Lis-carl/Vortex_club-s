"""Registro, acceso, cierre de sesión, perfil y foto de perfil."""
import secrets
from .. import config, seguridad, formularios as frm
from ..acceso import requiere_sesion, destino_seguro
from ..enrutador import ruta
from ..nucleo import ErrorHttp, Respuesta
from ..repositorios import usuarios, clubes, foro
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
    return render(p, "acceder.html", cif="", error="", siguiente=destino_seguro(p.consulta.get("siguiente"), ""))


@ruta("POST", "/acceder")
def acceder(p):
    cif = (p.formulario.get("cif") or "").strip()
    contrasena = (p.formulario.get("contrasena") or "")[:1024]
    siguiente = destino_seguro(p.formulario.get("siguiente"), "")
    clave = f"{p.ip}|{cif}"

    def fallo(mensaje):
        return render(p, "acceder.html", 401, cif=cif, error=mensaje, siguiente=siguiente)

    if seguridad.limite_acceso.bloqueado(clave) or seguridad.limite_ip.bloqueado(p.ip):
        return fallo("Demasiados intentos fallidos. Espera unos minutos e inténtalo de nuevo.")
    usuario = usuarios.por_cif(p.bd, cif) if frm.RE_CIF.match(cif) else None
    if usuario:
        correcta = seguridad.verificar_contrasena(contrasena, usuario.hash_contrasena, usuario.sal)
    else:   # mismo costo de cálculo para no revelar si el CIF existe
        seguridad.verificar_contrasena(contrasena, *_HASH_FALSO)
        correcta = False
    if not correcta:
        seguridad.limite_acceso.fallo(clave)
        seguridad.limite_ip.fallo(p.ip)
        return fallo("CIF o contraseña incorrectos.")
    if not usuario.activo:
        return fallo("Tu cuenta está desactivada. Comunícate con Vida Estudiantil.")
    seguridad.limite_acceso.reiniciar(clave)
    if seguridad.necesita_actualizar(usuario.hash_contrasena):   # contraseñas antiguas pasan al cifrado actual
        usuarios.actualizar_hash(p.bd, usuario.id, contrasena)
    # El tipo de usuario lo determina la cuenta (administración, líder, capitán o estudiante).
    rol = seguridad.rol_de_cuenta(p.bd, usuario.id, usuario.rol_global)
    return _iniciar_sesion(p, usuario.id, siguiente or _INICIO_POR_ROL[rol], rol)


@ruta("GET", "/registro")
def registro_formulario(p):
    if p.usuario:
        return Respuesta.redirigir("/")
    return render(p, "registro.html", valores={}, errores=frm.Errores(), carreras=CARRERAS)


@ruta("POST", "/registro")
def registro(p):
    f, errores = p.formulario, frm.Errores()
    if seguridad.limite_registro.bloqueado(p.ip):
        raise ErrorHttp(429, "Se crearon demasiadas cuentas desde este equipo. Inténtalo más tarde.")
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
    frm.contrasena_segura(contrasena, f.get("confirmar") or "", errores, cif)
    if errores:
        return render(p, "registro.html", 400, valores={"cif": cif, "nombre": nombre, "correo": correo,
                                                         "carrera": carrera}, errores=errores, carreras=CARRERAS)
    usuario_id = usuarios.crear(p.bd, cif, nombre, correo, carrera, contrasena)
    seguridad.limite_registro.fallo(p.ip)   # cuenta las cuentas creadas desde esta IP
    return _iniciar_sesion(p, usuario_id, "/clubes").con_aviso("ok", f"¡Bienvenido/a, {nombre}! Explora los clubes y únete.")


@ruta("POST", "/salir")
def salir(p):
    seguridad.cerrar_sesion(p.bd, p.cookies.get("sesion"))
    return Respuesta.redirigir("/acceder").borrar_cookie("sesion")


@ruta("GET", "/perfil/contrasena")
@requiere_sesion
def contrasena_formulario(p):
    return render(p, "cambiar_contrasena.html", errores=frm.Errores())


@ruta("POST", "/perfil/contrasena")
@requiere_sesion
def cambiar_contrasena(p):
    """Pide la contraseña actual, valida la nueva y cierra la sesión en los demás dispositivos."""
    f, errores = p.formulario, frm.Errores()
    yo = usuarios.por_id(p.bd, p.usuario.id)
    clave = f"{p.ip}|{yo.cif}"
    nueva = f.get("contrasena") or ""
    if seguridad.limite_acceso.bloqueado(clave):
        errores["actual"] = "Demasiados intentos fallidos. Espera unos minutos e inténtalo de nuevo."
    elif not seguridad.verificar_contrasena((f.get("actual") or "")[:1024], yo.hash_contrasena, yo.sal):
        seguridad.limite_acceso.fallo(clave)
        errores["actual"] = "La contraseña actual no es correcta."
    frm.contrasena_segura(nueva, f.get("confirmar") or "", errores, yo.cif)
    if not errores and seguridad.verificar_contrasena(nueva, yo.hash_contrasena, yo.sal):
        errores["contrasena"] = "La nueva contraseña debe ser distinta de la actual."
    if errores:
        return render(p, "cambiar_contrasena.html", 400, errores=errores)
    usuarios.cambiar_contrasena(p.bd, yo.id, nueva)
    seguridad.cerrar_todas(p.bd, yo.id)
    return _iniciar_sesion(p, yo.id, f"/perfil/{yo.cif}", p.usuario.rol_acceso).con_aviso(
        "ok", "Contraseña actualizada. Cerramos tu sesión en los demás dispositivos.")


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
                  solicitudes=solicitudes, es_yo=persona.id == p.usuario.id)


def _borrar_foto(nombre):
    if nombre:
        ruta = config.DIR_SUBIDAS / nombre
        if ruta.is_file():
            ruta.unlink()


@ruta("POST", "/perfil/foto")
@requiere_sesion
def cambiar_foto(p):
    """Sube una nueva foto de perfil (misma validación que las imágenes del foro)."""
    volver = Respuesta.redirigir(f"/perfil/{p.usuario.cif}")
    archivo = p.archivos.get("foto")
    errores = frm.Errores()
    extension = frm.validar_imagen(archivo, errores, "foto")
    if not archivo or not archivo.datos:
        return volver.con_aviso("error", "Elige una imagen para tu foto de perfil.")
    if errores:
        return volver.con_aviso("error", errores["foto"])
    nombre = f"{secrets.token_hex(16)}.{extension}"
    (config.DIR_SUBIDAS / nombre).write_bytes(archivo.datos)
    _borrar_foto(usuarios.cambiar_foto(p.bd, p.usuario.id, nombre))
    return volver.con_aviso("ok", "Foto de perfil actualizada.")


@ruta("POST", "/perfil/foto/quitar")
@requiere_sesion
def quitar_foto(p):
    _borrar_foto(usuarios.cambiar_foto(p.bd, p.usuario.id, ""))
    return Respuesta.redirigir(f"/perfil/{p.usuario.cif}").con_aviso("ok", "Quitaste tu foto de perfil.")
