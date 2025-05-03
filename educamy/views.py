from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils.translation import activate
from .forms import CreateUser
from django.views.generic import View

from dotenv import load_dotenv
import os
import tempfile
from weasyprint import HTML
from .models import GeneratedContent
import google.generativeai as genai
from bs4 import BeautifulSoup
import time
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from .forms import AnnualPlanForm

# Cargar variables de entorno
load_dotenv()
# Configurar la API de Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))





class DashboardView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'dashboard.html')



# Registro de usuarios

def registerView(request):
    activate('es')
    if request.method == 'POST':
        form = CreateUser(request.POST)
        if form.is_valid():
            form.save()
            return redirect('educamy:login')
    else: 
        form = CreateUser()
    return render(request, 'register.html', {'formulario': form})


def loginView(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username= username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido {username}')
                return redirect('educamy:dashboard')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')


    form = AuthenticationForm()   

    form.fields['username'].label = 'Nombre de usuario'
    form.fields['password'].label = 'Contraseña'
    return render(request, 'login.html', {"form": form})



def logoutApp(request):
    logout(request)
    return redirect('educamy:login')



def extractTopicsTable(html_string):
    """
    Extrae los temas desde una tabla HTML.
    Asume que el tema está en la última columna de cada fila (<td>).
    """
    temas = []
    try:
        soup = BeautifulSoup(html_string, 'html.parser')
        filas = soup.find_all('tr')

        # Saltar el encabezado si existe (thead o primera fila)
        for fila in filas[1:]:  # Empezamos en 1 para saltar encabezado
            columnas = fila.find_all('td')
            if columnas:
                tema = columnas[-1].get_text(strip=True)  # Última columna = Tema
                temas.append(tema)
    except Exception as e:
        print(f"Error extrayendo temas de la tabla: {e}")
    
    return temas




def splitDatesInUnits(start_date, end_date, units_number, class_days):
    from math import ceil
    valid_days = {
        'lunes': 0,
        'martes': 1,
        'miércoles': 2,
        'jueves': 3,
        'viernes': 4
    }
    index_days = [valid_days[d] for d in class_days]

    available_days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() in index_days:
            available_days.append(current_date)
        current_date += timedelta(days=1)

    total_days = len(available_days)

    if units_number > total_days:
        units_number = total_days  # 🔥 No puedes tener más unidades que días

    units = []
    hop = ceil(total_days / units_number)

    for i in range(0, total_days, hop):
        units.append(available_days[i:i+hop])

    # 🔥 Si sobran bloques extra, los ajustamos al final
    if len(units) > units_number:
        # Fusionar el último bloque extra en el anterior
        units[-2].extend(units[-1])
        units = units[:-1]

    return units



def formatTextToHtml(text):
    """
    Formatea el texto generado por Gemini a HTML elegante.
    """
    html_result = ""
    lines = text.splitlines()

    for line in lines:
        line = line.strip()

        if line.startswith("Unidad"):
            html_result += f"<h2 style='margin-top: 40px; font-size: 24px;'>{line}</h2>\n"
        elif line.startswith("Título:"):
            html_result += f"<p><strong>{line}</strong></p>\n"
        elif any(titulo in line for titulo in ["Objetivos específicos:", "Contenidos:", "Orientaciones metodológicas:", "Criterios de evaluación:", "Indicadores de evaluación:"]):
            html_result += f"<h3 style='margin-top: 20px; font-size: 20px;'>{line}</h3>\n"
            html_result += "<ul>\n"  # Empezar lista para los bullets
        elif line.startswith("- "):
            html_result += f"<li>{line[2:]}</li>\n"
        elif line == "":
            html_result += "</ul>\n"  # Cerrar lista cuando hay línea vacía
        else:
            html_result += f"<p>{line}</p>\n"

    if not html_result.endswith("</ul>\n"):
        html_result += "</ul>\n"

    return html_result

models = genai.list_models()

for model in models:
    print(model.name)

def generar_contenido(request):
    if request.method == 'POST':
        form = AnnualPlanForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            days_class = form.cleaned_data['days_class']
            units_number = form.cleaned_data['units_number']
            level = form.cleaned_data['level']
            school_subject = form.cleaned_data['school_subject']

            units = splitDatesInUnits(start_date, end_date, units_number, days_class)
            # Inicializar Gemini
            model = genai.GenerativeModel('gemini-1.5-flash')
            chat = model.start_chat(history=[])

            # Generar un solo PROMPT grande
            prompt = f"""
Eres un asistente educativo profesional. Genera la planificación completa de {units_number} unidades didácticas para la materia "{school_subject.name}", nivel "{level}" de educación básica.

Para cada unidad proporciona:

- Título de la unidad
- 2 objetivos específicos
- 3 contenidos temáticos principales
- 2 orientaciones metodológicas
- 2 criterios de evaluación
- 2 indicadores de evaluación

Formato de salida para cada unidad:

Unidad {{}}
Título: {{Título sugerido}}

Objetivos específicos:
- Objetivo 1
- Objetivo 2

Contenidos:
- Contenido 1
- Contenido 2
- Contenido 3

Orientaciones metodológicas:
- Metodología 1
- Metodología 2

Criterios de evaluación:
- Criterio 1
- Criterio 2

Indicadores de evaluación:
- Indicador 1
- Indicador 2

NO agregues introducciones, conclusiones ni mensajes extra. Solo las unidades en el formato claro y directo.
"""

            generated_schema = "⚠️ Error al generar contenido."

            try:
                response = chat.send_message(prompt)
                generated_schema = response.text
            except Exception as e:
                print(f"Error generando contenido: {e}")

            # Crear contenido HTML para el PDF
            html_string = f"""
<html>
<head>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; font-size: 14px; line-height: 1.6; }}
    h1, h2 {{ color: #333; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #999; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
    .unidad {{ page-break-before: always; margin-top: 50px; }}
    pre {{ white-space: pre-wrap; word-wrap: break-word; }}
  </style>
</head>
<body>
  <h1>Plan Anual de Clase</h1>
  <p><strong>Fecha Inicio:</strong> {start_date}</p>
  <p><strong>Fecha Fin:</strong> {end_date}</p>
  <p><strong>Días de clase:</strong> {', '.join(days_class)}</p>
  <p><strong>Nivel:</strong> {level}</p>
  <p><strong>Materia:</strong> {school_subject.name}</p>
  <p><strong>Número de unidades:</strong> {units_number}</p>

  <div class="unidad">
    <h2>Planificación de Unidades</h2>
    <pre>{generated_schema}</pre>
  </div>

</body>
</html>
"""

            # Crear PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
                html = HTML(string=html_string)
                html.write_pdf(output.name)

                content = GeneratedContent.objects.create(
                    user=request.user,
                    school_subject=school_subject,
                    start_date=start_date,
                    end_date=end_date,
                    grade=level,
                    topic="Planificación Anual",
                    generated_content=html_string,
                )

                with open(output.name, 'rb') as pdf_file:
                    content.pdf_file.save(f"plan_anual_{content.pk}.pdf", pdf_file)

            return redirect('educamy:dashboard')

    else:
        form = AnnualPlanForm()

    return render(request, 'generateContent.html', {'form': form})


