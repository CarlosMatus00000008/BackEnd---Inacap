from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RegistroForm, ViajeForm
from .models import FotoViaje, Mg, PerfilUsuario, Viaje


def _refrescar_estados():
    """
    El estado de un viaje se calcula por fecha (ver Viaje.calcular_estado).
    Como el tiempo avanza aunque nadie edite el viaje (un viaje "en
    progreso" hoy puede pasar a "completado" mañana solo porque cambió la
    fecha), recalculamos y guardamos el estado de todos los viajes cada
    vez que se carga la lista, para que siempre quede al día.
    """
    for viaje in Viaje.objects.all():
        nuevo_estado = viaje.calcular_estado()
        if nuevo_estado != viaje.estado:
            Viaje.objects.filter(pk=viaje.pk).update(estado=nuevo_estado)


def _perfil_de(usuario):
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    return perfil


# ---------------------------------------------------------------------
# Autenticación / registro
# ---------------------------------------------------------------------

def registro(request):
    """Registro público: cualquiera crea usuario + contraseña, pero sin
    permisos. Un superusuario debe habilitarlos después (panel /usuarios/)."""
    if request.user.is_authenticated:
        return redirect("lista_viajes")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()  # la señal post_save crea el PerfilUsuario
            auth_login(request, usuario)
            messages.success(
                request,
                "¡Cuenta creada! Ya puedes ver el diario de viajes. "
                "Para poder crear tus propios viajes o ver los de otros, "
                "un administrador debe habilitarte esos permisos.",
            )
            return redirect("lista_viajes")
    else:
        form = RegistroForm()
    return render(request, "viajes/registro.html", {"form": form})


# ---------------------------------------------------------------------
# Viajes: listado (timeline general) y detalle
# ---------------------------------------------------------------------

@login_required
def lista_viajes(request):
    """
    Vista principal: la línea de tiempo de viajes.

    - Si el usuario tiene permiso 'puede_ver_otros', ve el diario de TODOS
      los usuarios (como un feed tipo Instagram), del más reciente al más
      antiguo.
    - Si no, solo ve sus propios viajes.
    """
    _refrescar_estados()
    perfil = _perfil_de(request.user)

    if perfil.puede_ver_otros:
        viajes = Viaje.objects.select_related("propietario").prefetch_related("mg", "fotos").all()
    else:
        viajes = (
            Viaje.objects.select_related("propietario")
            .prefetch_related("mg", "fotos")
            .filter(propietario=request.user)
        )

    filtro_estado = request.GET.get("estado")
    if filtro_estado in dict(Viaje.ESTADO_CHOICES):
        viajes = viajes.filter(estado=filtro_estado)

    # IDs de los viajes a los que el usuario actual ya les dio "mg", para
    # poder pintar el corazón activo sin llamar a un método con argumentos
    # desde el template (los templates de Django no lo permiten).
    mis_mg_ids = set(Mg.objects.filter(usuario=request.user).values_list("viaje_id", flat=True))

    contexto = {
        "viajes": viajes,
        "perfil": perfil,
        "filtro_estado": filtro_estado,
        "estados": Viaje.ESTADO_CHOICES,
        "mis_mg_ids": mis_mg_ids,
    }
    return render(request, "viajes/lista_viajes.html", contexto)


@login_required
def detalle_viaje(request, pk):
    viaje = get_object_or_404(Viaje.objects.select_related("propietario"), pk=pk)
    perfil = _perfil_de(request.user)

    es_propietario = viaje.propietario_id == request.user.id
    if not es_propietario and not perfil.puede_ver_otros:
        messages.warning(request, "No tienes permiso para ver los viajes de otros usuarios.")
        return redirect("lista_viajes")

    return render(
        request,
        "viajes/detalle_viaje.html",
        {
            "viaje": viaje,
            "es_propietario": es_propietario,
            "tiene_mg": viaje.con_mg_de(request.user),
        },
    )


# ---------------------------------------------------------------------
# Crear / editar / eliminar viajes (requiere permiso)
# ---------------------------------------------------------------------

@login_required
def crear_viaje(request):
    perfil = _perfil_de(request.user)
    if not perfil.puede_crear_viajes:
        messages.warning(request, "No tienes permiso para crear viajes. Pídele a un administrador que te lo habilite.")
        return redirect("lista_viajes")

    if request.method == "POST":
        form = ViajeForm(request.POST, request.FILES)
        if form.is_valid():
            viaje = form.save(commit=False)
            viaje.propietario = request.user
            viaje.save()
            for foto in form.fotos_nuevas()[: FotoViaje.MAX_FOTOS_POR_VIAJE]:
                FotoViaje.objects.create(viaje=viaje, imagen=foto)
            messages.success(request, f"Viaje a {viaje.destino} creado correctamente.")
            return redirect("detalle_viaje", pk=viaje.pk)
    else:
        form = ViajeForm()
    contexto = {"form": form, "modo": "crear", "fotos_restantes": FotoViaje.MAX_FOTOS_POR_VIAJE}
    return render(request, "viajes/form_viaje.html", contexto)


@login_required
def editar_viaje(request, pk):
    viaje = get_object_or_404(Viaje, pk=pk)
    perfil = _perfil_de(request.user)

    if viaje.propietario_id != request.user.id:
        messages.warning(request, "Solo puedes editar tus propios viajes.")
        return redirect("lista_viajes")
    if not perfil.puede_crear_viajes:
        messages.warning(request, "No tienes permiso para editar viajes. Pídele a un administrador que te lo habilite.")
        return redirect("detalle_viaje", pk=viaje.pk)

    if request.method == "POST":
        form = ViajeForm(request.POST, request.FILES, instance=viaje)
        if form.is_valid():
            fotos_nuevas = form.fotos_nuevas()
            cupo = viaje.fotos_restantes
            if len(fotos_nuevas) > cupo:
                messages.warning(
                    request,
                    f"Este viaje ya tiene {FotoViaje.MAX_FOTOS_POR_VIAJE - cupo} foto(s). "
                    f"Solo se guardaron {cupo} de las que subiste (máximo {FotoViaje.MAX_FOTOS_POR_VIAJE} por viaje).",
                )
            form.save()
            for foto in fotos_nuevas[:cupo]:
                FotoViaje.objects.create(viaje=viaje, imagen=foto)
            messages.success(request, f"Viaje a {viaje.destino} actualizado.")
            return redirect("detalle_viaje", pk=viaje.pk)
    else:
        form = ViajeForm(instance=viaje)
    contexto = {"form": form, "modo": "editar", "viaje": viaje, "fotos_restantes": viaje.fotos_restantes}
    return render(request, "viajes/form_viaje.html", contexto)


@login_required
def eliminar_foto(request, foto_id):
    """Borra una foto de un viaje. Solo el propietario del viaje puede hacerlo."""
    foto = get_object_or_404(FotoViaje, pk=foto_id)
    if foto.viaje.propietario_id != request.user.id:
        messages.warning(request, "Solo puedes eliminar fotos de tus propios viajes.")
        return redirect("lista_viajes")

    if request.method == "POST":
        viaje_pk = foto.viaje_id
        foto.imagen.delete(save=False)  # borra el archivo del disco
        foto.delete()
        messages.success(request, "Foto eliminada.")
        return redirect("editar_viaje", pk=viaje_pk)

    return redirect("editar_viaje", pk=foto.viaje_id)


@login_required
def eliminar_viaje(request, pk):
    viaje = get_object_or_404(Viaje, pk=pk)
    if viaje.propietario_id != request.user.id and not request.user.is_superuser:
        messages.warning(request, "Solo puedes eliminar tus propios viajes.")
        return redirect("lista_viajes")

    if request.method == "POST":
        destino = viaje.destino
        viaje.delete()
        messages.success(request, f"Viaje a {destino} eliminado.")
        return redirect("lista_viajes")

    return render(request, "viajes/confirmar_eliminar.html", {"viaje": viaje})


# ---------------------------------------------------------------------
# "Mg": el me-gusta tipo Instagram (solo mg, sin comentarios)
# ---------------------------------------------------------------------

@login_required
def toggle_mg(request, pk):
    """Le da (o quita) 'mg' a un viaje. Responde JSON si es fetch/AJAX,
    o redirige de vuelta si es un envío de formulario normal (sin JS)."""
    if request.method != "POST":
        return redirect("lista_viajes")

    viaje = get_object_or_404(Viaje, pk=pk)
    perfil = _perfil_de(request.user)

    es_propietario = viaje.propietario_id == request.user.id
    if not es_propietario and not perfil.puede_ver_otros:
        messages.warning(request, "No tienes permiso para interactuar con viajes de otros usuarios.")
        return redirect("lista_viajes")

    mg, creado = Mg.objects.get_or_create(viaje=viaje, usuario=request.user)
    if not creado:
        mg.delete()
        tiene_mg = False
    else:
        tiene_mg = True

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"tiene_mg": tiene_mg, "total_mg": viaje.total_mg})

    return redirect("detalle_viaje", pk=viaje.pk)


# ---------------------------------------------------------------------
# Perfil de usuario: timeline personal de sus viajes
# ---------------------------------------------------------------------

@login_required
def perfil_usuario(request, username=None):
    usuario_visto = request.user if username is None else get_object_or_404(User, username=username)
    perfil_solicitante = _perfil_de(request.user)
    perfil_visto = _perfil_de(usuario_visto)

    es_propio = usuario_visto.id == request.user.id
    if not es_propio and not perfil_solicitante.puede_ver_otros:
        messages.warning(request, "No tienes permiso para ver el perfil de otros usuarios.")
        return redirect("lista_viajes")

    _refrescar_estados()
    viajes = Viaje.objects.filter(propietario=usuario_visto)

    contexto = {
        "usuario_visto": usuario_visto,
        "perfil_visto": perfil_visto,
        "es_propio": es_propio,
        "viajes": viajes,
        "total_completados": viajes.filter(estado=Viaje.COMPLETADO).count(),
        "total_en_progreso": viajes.filter(estado=Viaje.EN_PROGRESO).count(),
        "total_planificados": viajes.filter(estado=Viaje.PLANIFICADO).count(),
    }
    return render(request, "viajes/perfil.html", contexto)


# ---------------------------------------------------------------------
# Panel de superusuario: gestión de permisos de usuarios nuevos
# ---------------------------------------------------------------------

def _es_superusuario(usuario):
    return usuario.is_authenticated and usuario.is_superuser


@user_passes_test(_es_superusuario, login_url="login")
def gestion_usuarios(request):
    """Panel del superusuario: aquí se le otorga a cada usuario nuevo el
    permiso para crear viajes y/o ver los viajes de los demás."""
    if request.method == "POST":
        usuario_id = request.POST.get("usuario_id")
        usuario = get_object_or_404(User, pk=usuario_id)
        perfil = _perfil_de(usuario)
        perfil.puede_crear_viajes = "puede_crear_viajes" in request.POST
        perfil.puede_ver_otros = "puede_ver_otros" in request.POST
        perfil.save()
        messages.success(request, f"Permisos de {usuario.username} actualizados.")
        return redirect("gestion_usuarios")

    usuarios = User.objects.select_related("perfil").order_by("-date_joined")
    return render(request, "viajes/gestion_usuarios.html", {"usuarios": usuarios})
