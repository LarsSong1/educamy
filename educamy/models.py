from django.db import models
from django.contrib.auth.models import User
import datetime
from django.utils import timezone

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    photo = models.ImageField(upload_to='user_photos/', blank=True, null=True)  # Carpeta donde se guardan las fotos
    full_name = models.CharField(max_length=100),
    

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Contenido de {self.user.username} - {self.school_subject.name}"
    
    
class AnualPlan(models.Model):
    generatedContentId = models.ForeignKey(GeneratedContent, on_delete=models.CASCADE, related_name='generated_annualplans', null=True, blank=True)
    school_subject = models.ForeignKey(SchoolSubject, on_delete=models.CASCADE, null=True, blank=True)
    unit_title = models.JSONField(default=list)
    goals = models.JSONField(default=list)
    unit_contents = models.JSONField(default=list)
    methodologies = models.JSONField(default=list)
    pdf_file = models.FileField(upload_to='annualplan_pdf/', null=True, blank=True)
    start_date = models.DateField(default=timezone.now)
    end_date   = models.DateField(default=timezone.now)
    year = models.PositiveIntegerField(default=datetime.datetime.now().year)
    grade = models.CharField(max_length=200, default='Primero')
    evaluation_criteria = models.JSONField(default=list)
    evaluation_indicators = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Unidad: {self.unit_title} - {self.generatedContentId.school_subject.name}"






class MicroPlan(models.Model):
    generatedContentId = models.ForeignKey(GeneratedContent, on_delete=models.CASCADE, related_name='generated_microplans', null=True, blank=True)
    school_subject = models.ForeignKey(SchoolSubject, on_delete=models.CASCADE, null=True, blank=True)
    unit_title = models.JSONField(default=list)
    goals = models.JSONField(default=list)
    topic = models.JSONField(default=list) # unit_contents
    start_date = models.DateField()
    end_date = models.DateField()
    grade = models.CharField(max_length=200)
    pdf_file = models.FileField(upload_to='microplan_pdf/', null=True, blank=True)
    generated_content = models.TextField()
    year = models.PositiveIntegerField(default=datetime.datetime.now().year)
    content = models.TextField()
    evaluation_criteria = models.JSONField(default=list)
    evaluation_indicators = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plan Microcurricular de - {self.school_subject.name} ({self.year})"




class Questions(models.Model):
    generatedContentId = models.ForeignKey(GeneratedContent, on_delete=models.CASCADE, related_name='generated_questions', null=True, blank=True)
    question_text = models.TextField()
    pdf_file = models.FileField(upload_to='questions_pdf/', null=True, blank=True)
    answer_choices = models.JSONField(default=list)  
    correct_answer = models.CharField(max_length=200)  
    generated_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pregunta de {self.generatedContentId.school_subject.name}"







