from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    photo = models.ImageField(upload_to='user_photos/', blank=True, null=True)  # Carpeta donde se guardan las fotos

    def __str__(self):
        return f"Perfil de {self.user.username}"
    


class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class ContenidoGenerado(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    grados = models.CharField(max_length=200)  # Ej: "Primero, Segundo, Tercero"
    tema = models.CharField(max_length=255, blank=True, null=True)
    archivo_pdf = models.FileField(upload_to='contenidos_pdf/', null=True, blank=True)
    contenido_generado = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contenido de {self.usuario.username} - {self.materia.nombre}"



