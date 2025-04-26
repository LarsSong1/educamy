from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Profile
from django.contrib.auth.forms import UserChangeForm
from .models import Materia



class CreateUser(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(CreateUser, self).__init__(*args, **kwargs)
        self.fields['username'].label = 'Nombre de usuario'
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Confirmar contraseña'

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']
        help_texts = {
            'username': _('Solo se aceptan letras o estos caracteres @/./+/-/_ '),
            'password2': _('Vuelve a ingresar la misma contraseña'),
            'password1': _('Tu contraseña no debe ser similar a tu usuario.\n'
                           'Debe contener al menos 8 caracteres\n'
                           'No uses contraseñas habituales\n'
                           'No debe ser solo numeros'),
        }



class UpdateProfile(UserChangeForm):
    photo = forms.ImageField(required=False, label=_('Foto de perfil'))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        help_texts = {
            'username': _('Solo se aceptan letras o estos caracteres @/./+/-/_ '),
            'password2': _('Vuelve a ingresar la misma contraseña'),
            'password1': _('Tu contraseña no debe ser similar a tu usuario.\n'
                           'Debe contener al menos 8 caracteres\n'
                           'No uses contraseñas habituales\n'
                           'No debe ser solo números'),
        }

    def save(self, commit=True):
        user = super().save(commit=False)

        # Crear el perfil si no existe
        if not hasattr(user, 'profile'):
            profile = Profile(user=user)
            profile.save()
        else:
            profile = user.profile

        # Si la foto ha sido proporcionada, la actualizamos
        if 'photo' in self.cleaned_data:
            profile.photo = self.cleaned_data['photo']
            profile.save()

        if commit:
            user.save()

        return user
    






from .models import Materia  # Ya lo tienes arriba, perfecto

DIAS_CHOICES = [
    ('lunes', 'Lunes'),
    ('martes', 'Martes'),
    ('miércoles', 'Miércoles'),
    ('jueves', 'Jueves'),
    ('viernes', 'Viernes')
]

NIVELES = [
    ('Primero', 'Primero'),
    ('Segundo', 'Segundo'),
    ('Tercero', 'Tercero'),
    ('Cuarto', 'Cuarto'),
    ('Quinto', 'Quinto'),
    ('Sexto', 'Sexto'),
    ('Septimo', 'Septimo'),
]

class PlanAnualForm(forms.Form):
    fecha_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de inicio")
    fecha_fin = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de fin")
    dias_clase = forms.MultipleChoiceField(
        choices=DIAS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Días de clases (elige varios)"
    )
    numero_unidades = forms.IntegerField(min_value=1, label="Número de unidades")
    nivel = forms.ChoiceField(
        choices=NIVELES,
        label="Nivel"
    )
    materia = forms.ModelChoiceField(
        queryset=Materia.objects.all(),
        label="Materia"
    )
