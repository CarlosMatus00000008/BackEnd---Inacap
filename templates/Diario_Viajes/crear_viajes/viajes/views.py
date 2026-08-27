from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import ViajeForm


def crear_viaje(request):
    if request.method == 'POST':
        form = ViajeForm(request.POST)
        if form.is_valid():
            viaje = form.save()
            messages.success(request, f'¡Viaje a {viaje.destino}, {viaje.pais} guardado con éxito!')
            return redirect('crear_viaje')
    else:
        form = ViajeForm()

    return render(request, 'viajes/crear_viaje.html', {'form': form})
