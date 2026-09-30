"""
Carga de usuarios de demostración (comandos cargar_juanpablo y cargar_viajeros_demo).

Cada usuario demo se describe con datos (registro, viajes con gastos e itinerario, y fotos)
y CargadorDemo lo crea o, si ya existe, lo pone al día sin duplicar nada:

    CargadorDemo(comando, datos).cargar(contrasena)
    CargadorDemo(comando, datos).eliminar()

Formato de un viaje (clave = código ISO del país):
    destino, fechas (inicio, regreso), calificacion, favorito, presupuesto, notas,
    pasaje (en pesos, 0 si no hubo), moneda y cambio (pesos por unidad de la moneda local;
    moneda None si el viaje fue en Chile y todo se pagó en pesos),
    gastos: [(descripción, categoría, monto en moneda local, día del viaje)],
    itinerario (opcional): [(día del viaje, "HH:MM" o None, actividad, lugar)],
    estado (opcional, por defecto «completado»; «en_progreso» también lleva fotos).
Planificados: [(destino, código ISO, días desde hoy, duración en días, notas)].

Las fotos son de Wikimedia Commons (CC BY / CC BY-SA): se descargan en 1920 px y pasan por
el mismo proceso que las que suben los usuarios. El crédito queda guardado en cada foto.
"""

import time
import urllib.request
from datetime import datetime, timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone

from core.templatetags.diario import telefono
from cuentas.models import PerfilUsuario

from .forms import VariasFotosField
from .models import Actividad, CategoriaGasto, EstadoViaje, FotoViaje, Gasto, Pais, Viaje
from .senales import GRUPO_VIAJEROS

AGENTE = "DiarioDeViajes-demo/1.0 (proyecto educativo)"  # Wikimedia pide identificarse


def descargar(url):
    pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    for intento in range(3):
        try:
            with urllib.request.urlopen(pedido, timeout=60) as respuesta:
                return respuesta.read()
        except OSError:
            if intento == 2:
                raise
            time.sleep(3 * (intento + 1))


def credito(foto):
    """Crédito de la foto, como piden las licencias Creative Commons: autor, licencia y origen."""
    return f"{foto['autor'] or 'Autor en Commons'} · {foto['licencia']} · Wikimedia Commons"[:200]


def guardar(objeto):
    objeto.full_clean()  # los datos demo pasan por las mismas validaciones que la web
    objeto.save()
    return objeto


class CargadorDemo:
    """
    datos = {"usuario": "JuanPablo", "registro": {...}, "viajes": {...},
             "planificados": [...], "fotos": {código ISO: [fotos]}}
    """

    def __init__(self, comando, datos):
        self.comando = comando
        self.datos = datos
        self.nombre = datos["usuario"]

    def escribir(self, texto, estilo=None):
        self.comando.stdout.write(estilo(texto) if estilo else texto)

    # ------------------------------------------------------------------
    def cargar(self, contrasena):
        usuario = get_user_model().objects.filter(username=self.nombre).first()
        if usuario:
            self.escribir(f"«{self.nombre}» ya existe: se ponen al día su perfil, notas y fotos.")
            self.actualizar_notas(usuario)
        else:
            with transaction.atomic():
                usuario = get_user_model().objects.create_user(self.nombre, password=contrasena)
                usuario.groups.add(Group.objects.get_or_create(name=GRUPO_VIAJEROS)[0])
                self.crear_viajes(usuario)
            self.escribir(f"Usuario «{self.nombre}» creado con sus viajes y gastos.", self.comando.style.SUCCESS)
            self.escribir(f"  Contraseña: {contrasena}")
        self.completar_registro(usuario)
        self.cargar_fotos(usuario)
        return usuario

    def completar_registro(self, usuario):
        """Los datos que pide el registro (y el perfil), como si se hubiera registrado en el sitio."""
        registro = self.datos["registro"]
        alta = timezone.make_aware(registro["alta"])
        usuario.first_name = registro["first_name"]
        usuario.last_name = registro["last_name"]
        usuario.email = registro["email"]
        usuario.date_joined = alta
        usuario.last_login = usuario.last_login or timezone.now()
        usuario.full_clean(exclude=["password"])
        usuario.save()
        PerfilUsuario.objects.update_or_create(
            usuario=usuario,
            defaults={"telefono": registro["telefono"], "acepta_datos": True, "fecha_consentimiento": alta},
        )
        self.escribir(
            f"  Perfil: {usuario.get_full_name()} · {usuario.email} · {telefono(registro['telefono'])}"
            f" · alta {alta:%d-%m-%Y}"
        )

    def crear_viajes(self, usuario):
        paises = {pais.codigo_iso: pais for pais in Pais.objects.all()}
        hoy = timezone.localdate()
        for codigo, datos in self.datos["viajes"].items():
            inicio, regreso = datos["fechas"]
            viaje = guardar(
                Viaje(
                    usuario=usuario,
                    destino=datos["destino"],
                    pais=paises[codigo],
                    fecha_inicio=inicio,
                    fecha_fin=regreso,
                    estado=datos.get("estado", EstadoViaje.COMPLETADO),
                    favorito=datos["favorito"],
                    calificacion=datos["calificacion"],
                    presupuesto=datos["presupuesto"],
                    notas=datos["notas"],
                )
            )
            if datos["pasaje"]:
                guardar(
                    Gasto(
                        viaje=viaje,
                        descripcion="Pasajes de avión",
                        categoria=CategoriaGasto.TRANSPORTE,
                        monto=datos["pasaje"],
                        fecha=inicio,
                    )
                )
            moneda = datos["moneda"]
            for descripcion, categoria, monto_local, dia in datos["gastos"]:
                guardar(
                    Gasto(
                        viaje=viaje,
                        descripcion=descripcion,
                        categoria=categoria,
                        monto=round(monto_local * datos["cambio"]) if moneda else monto_local,
                        moneda=moneda or "",
                        monto_moneda=monto_local if moneda else None,
                        fecha=inicio + timedelta(days=dia),
                    )
                )
            for dia, hora, titulo, lugar in datos.get("itinerario", []):
                fecha = inicio + timedelta(days=dia)
                guardar(
                    Actividad(
                        viaje=viaje,
                        fecha=fecha,
                        hora=datetime.strptime(hora, "%H:%M").time() if hora else None,
                        titulo=titulo,
                        lugar=lugar,
                        realizada=fecha < hoy,  # en un viaje en curso, lo de hoy en adelante está pendiente
                    )
                )

        for destino, codigo, dias, duracion, notas in self.datos.get("planificados", []):
            inicio = hoy + timedelta(days=dias)
            guardar(
                Viaje(
                    usuario=usuario,
                    destino=destino,
                    pais=paises[codigo],
                    fecha_inicio=inicio,
                    fecha_fin=inicio + timedelta(days=duracion - 1),
                    estado=EstadoViaje.PLANIFICADO,
                    notas=notas,
                )
            )

    def actualizar_notas(self, usuario):
        for viaje in usuario.viajes.exclude(estado=EstadoViaje.PLANIFICADO).select_related("pais"):
            datos = self.datos["viajes"].get(viaje.pais.codigo_iso)
            if datos and viaje.notas != datos["notas"]:
                viaje.notas = datos["notas"]
                viaje.save(update_fields=["notas", "actualizado"])

    # ------------------------------------------------------------------
    def cargar_fotos(self, usuario):
        campo = VariasFotosField()  # el mismo proceso que las fotos subidas desde la web
        viajes = {viaje.pais.codigo_iso: viaje for viaje in usuario.viajes.select_related("pais")}
        subidas = fallidas = 0
        for codigo, fotos in self.datos["fotos"].items():
            viaje = viajes.get(codigo)
            if viaje is None:
                continue
            # Las fotos ya subidas están en el mismo orden que la lista: se les pone su crédito.
            existentes = list(viaje.fotos.all())
            for foto_viaje, foto in zip(existentes, fotos, strict=False):
                if foto_viaje.credito != credito(foto):
                    foto_viaje.credito = credito(foto)
                    foto_viaje.save(update_fields=["credito"])
            for foto in fotos[len(existentes) : FotoViaje.MAXIMO_POR_VIAJE]:
                try:
                    contenido = descargar(foto["thumb"])
                    [preparada] = campo.clean(SimpleUploadedFile("foto.jpg", contenido, "image/jpeg"))
                    FotoViaje.objects.create(viaje=viaje, imagen=preparada, credito=credito(foto))
                    subidas += 1
                except (OSError, forms.ValidationError) as error:
                    fallidas += 1
                    self.comando.stderr.write(f"  No se pudo cargar «{foto['titulo']}»: {error}")
            self.escribir(f"  {viaje.destino}: {viaje.fotos.count()} fotos")
        estilo = self.comando.style.SUCCESS if not fallidas else self.comando.style.WARNING
        self.escribir(f"Fotos subidas: {subidas} · con error: {fallidas}", estilo)
        if fallidas:
            self.escribir("Vuelve a ejecutar el comando para reintentar las que faltan.")

    def eliminar(self):
        usuario = get_user_model().objects.filter(username=self.nombre).first()
        if not usuario:
            self.escribir(f"No existe el usuario «{self.nombre}».")
            return
        fotos = FotoViaje.objects.filter(viaje__usuario=usuario).count()
        with transaction.atomic():
            usuario.delete()  # al borrar cada foto también se borra su archivo (viajes/senales.py)
        self.escribir(f"Usuario «{self.nombre}» eliminado con {fotos} fotos.", self.comando.style.SUCCESS)
