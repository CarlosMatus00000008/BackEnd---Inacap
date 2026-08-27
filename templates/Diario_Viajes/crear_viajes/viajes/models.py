from django.db import models


class Viaje(models.Model):
    ESTADO_CHOICES = [
        ('completado', 'Completado ✓'),
        ('en_progreso', 'En progreso 🔄'),
        ('planificado', 'Planificado 📋'),
    ]

    destino = models.CharField(max_length=100)
    pais = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    duracion_dias = models.PositiveIntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='planificado')
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f'{self.destino}, {self.pais}'
