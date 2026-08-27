from datetime import date

from django import forms

from .models import Viaje


class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ['destino', 'pais', 'fecha_inicio', 'duracion_dias', 'estado', 'notas']
        widgets = {
            'destino': forms.TextInput(attrs={'placeholder': 'Ej: París, Bali, Cartagena'}),
            'pais': forms.TextInput(attrs={'placeholder': 'Ej: Francia'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'duracion_dias': forms.NumberInput(attrs={'min': 1, 'placeholder': 'Ej: 10'}),
            'notas': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notas del viaje (opcional)'}),
        }
        labels = {
            'destino': 'Destino',
            'pais': 'País',
            'fecha_inicio': 'Fecha de inicio',
            'duracion_dias': 'Duración aproximada (días)',
            'estado': 'Estado del viaje',
            'notas': 'Notas',
        }

    def clean_duracion_dias(self):
        duracion = self.cleaned_data['duracion_dias']
        if duracion <= 0:
            raise forms.ValidationError('La duración debe ser de al menos 1 día.')
        return duracion

    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get('estado')
        fecha_inicio = cleaned_data.get('fecha_inicio')

        if estado == 'planificado' and fecha_inicio and fecha_inicio < date.today():
            self.add_error('fecha_inicio', 'Un viaje planificado no puede tener una fecha de inicio en el pasado.')

        if estado == 'completado' and fecha_inicio and fecha_inicio > date.today():
            self.add_error('fecha_inicio', 'Un viaje completado no puede tener una fecha de inicio en el futuro.')

        return cleaned_data
