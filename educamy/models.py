from django.db import models
from django.contrib.auth.models import User
import datetime
from django.utils import timezone

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    photo = models.ImageField(upload_to='user_photos/', blank=True, null=True)  # Carpeta donde se guardan las fotos

    def __str__(self):
        return f"Perfil de {self.user.username}"
    


class SchoolSubject(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='school_subjects')

    def __str__(self):
        return self.name

class GeneratedContent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    school_subject = models.ForeignKey(SchoolSubject, on_delete=models.CASCADE)
    objetives = models.JSONField(default=list)
    start_date = models.DateField()
    end_date = models.DateField()
    grade = models.CharField(max_length=200)  # Ej: "Primero, Segundo, Tercero"
    topic = models.JSONField(default=list)
    pdf_file = models.FileField(upload_to='contenidos_pdf/', null=True, blank=True)
    generated_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Contenido de {self.user.username} - {self.school_subject.name}"






