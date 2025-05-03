from django.urls import path
from .views import loginView, registerView, DashboardView, generar_contenido, logoutApp

app_name = 'educamy'

urlpatterns = [
    path('', loginView, name='login'),
    path('register/', registerView, name='register'),
    path('logout/', logoutApp, name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('generate_content/', generar_contenido, name='generate_content'),

]
