from django.urls import path
from .views import loginView, registerView, DashboardView, generar_contenido, logoutApp, ItinerariesView, SchoolSubjectsView, SchoolSubjectEditView, SchoolSubjectDeleteView

app_name = 'educamy'

urlpatterns = [
    path('', loginView, name='login'),
    path('register/', registerView, name='register'),
    path('logout/', logoutApp, name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('generate_content/', generar_contenido, name='generate_content'),
    path('itineraries/', ItinerariesView.as_view(), name='itineraries'),
    path('school_subjects/', SchoolSubjectsView.as_view(), name='school_subjects'),
    path('school_subjects/edit/<int:pk>/', SchoolSubjectEditView.as_view(), name='edit_school_subject'),
    path('school_subjects/delete/<int:pk>/', SchoolSubjectDeleteView.as_view(), name='delete_school_subject'),


]
