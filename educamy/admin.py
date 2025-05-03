from django.contrib import admin
from .models import SchoolSubject, GeneratedContent

# Register your models here.
admin.site.register(SchoolSubject)
admin.site.register(GeneratedContent)