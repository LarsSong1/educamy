from django.urls import path
from .views import loginView, registerView, DashboardView

app_name = 'educamy'

urlpatterns = [
    path('', loginView, name='login'),
    path('register/', registerView, name='register'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

]
