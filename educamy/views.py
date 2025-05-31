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
import google.generativeai as genai
from bs4 import BeautifulSoup
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from .models import GeneratedContent, SchoolSubject
from .forms import AnnualPlanForm, AddSchoolSubjectForm
from django.shortcuts import get_object_or_404
from math import ceil
# Cargar variables de entorno
load_dotenv()





# Configurar la API de Gemini
# genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
genai.configure(api_key='AIzaSyDf0rm3_GvwCFX_Ae7pzIBNkALXWjhJmjk')
print("API Key configurada correctamente. ", os.getenv('GEMINI_API_KEY'))








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



class DashboardView(View):
    def get(self, request, *args, **kwargs):
        itineraries = GeneratedContent.objects.filter(user=request.user).order_by('-created_at')
        itinerariesCount = itineraries.count()
        context = {
            'user': request.user,
            'itineraries': itineraries,
            'itinerariesCount': itinerariesCount,
        }
        return render(request, 'dashboard.html', context)
    


class ItinerariesView(View):
    def get(self, request, *args, **kwargs):
        itineraries = GeneratedContent.objects.filter(user=request.user).order_by('-created_at')
        print(itineraries)
     
        context = {
            'user': request.user,
            'itineraries': itineraries,
                  
        }
        return render(request, 'itineraries.html', context)


class SchoolSubjectsView(View):
    def get(self, request, *args, **kwargs):
        form = AddSchoolSubjectForm()
        schoolSubjects = SchoolSubject.objects.filter(user=request.user)
        context = {
            'user': request.user,
            'form': form,   
            'schoolSubjects': schoolSubjects,
        }
        return render(request, 'schoolSubject.html', context)
    
    def post(self, request, *args, **kwargs):
        form = AddSchoolSubjectForm(request.POST)
        if form.is_valid():
            school_subject = form.save(commit=False)
            school_subject.user = request.user
            school_subject.save()
            return redirect('educamy:school_subjects')
        else:
            schoolSubjects = SchoolSubject.objects.filter(user=request.user)
            context = {
                'user': request.user,
                'form': form,
                'schoolSubjects': schoolSubjects,
            }
            return render(request, 'schoolSubject.html', context)
    


class SchoolSubjectEditView(View):
    def get(self, request, pk):
        subject = get_object_or_404(SchoolSubject, pk=pk, user=request.user)
        form = AddSchoolSubjectForm(instance=subject)
        return render(request, 'editSchoolSubject.html', {'form': form, 'subject': subject})

    def post(self, request, pk):
        subject = get_object_or_404(SchoolSubject, pk=pk, user=request.user)
        form = AddSchoolSubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            return redirect('educamy:school_subjects')
        return render(request, 'editSchoolSubject.html', {'form': form, 'subject': subject})


class SchoolSubjectDeleteView(View):
    def post(self, request, pk):
        subject = get_object_or_404(SchoolSubject, pk=pk, user=request.user)
        subject.delete()
        return redirect('educamy:school_subjects')





def extractTopicContentPerUnit(html_string):
    soup = BeautifulSoup(html_string, 'html.parser')
    unidades = []

    # Cada tabla representa una unidad
    tablas = soup.find_all('table')

    for tabla in tablas:
        contenido = []
        filas = tabla.find_all('tr')

        for fila in filas:
            celdas = fila.find_all('td')
            if len(celdas) >= 2:
                titulo = celdas[0].get_text(strip=True)
                if titulo.lower() == 'contenidos':
                    # Aquí extraemos el contenido, puede estar en <ul><li> o en texto plano separado
                    contenido_html = celdas[1]
                    # Si hay <li>, extraemos cada ítem
                    items = contenido_html.find_all('li')
                    if items:
                        contenido = [li.get_text(strip=True) for li in items]
                    else:
                        # Si no hay <li>, extraemos texto dividido por saltos de línea o puntos
                        texto = contenido_html.get_text(separator='\n').strip()
                        contenido = [line.strip() for line in texto.split('\n') if line.strip()]
                    break  # Ya encontramos contenidos en esta tabla, pasamos a la siguiente

        unidades.append(contenido)

    return unidades


def parse_gemini_response_to_units(text):
    unidades = []
    bloque = {}
    current_key = None

    for line in text.splitlines():
        line = line.strip()

        if line.startswith("Unidad"):
            if bloque:
                unidades.append(bloque)
            bloque = {'titulo': line, 'objetivos': [], 'contenidos': [], 'metodologias': [], 'criterios': [], 'indicadores': []}
            current_key = None
        elif line.startswith("Título:"):
            bloque['titulo'] = line.replace("Título:", "").strip()
        elif "Objetivos específicos:" in line:
            current_key = 'objetivos'
        elif "Contenidos:" in line:
            current_key = 'contenidos'
        elif "Orientaciones metodológicas:" in line:
            current_key = 'metodologias'
        elif "Criterios de evaluación:" in line:
            current_key = 'criterios'
        elif "Indicadores de evaluación:" in line:
            current_key = 'indicadores'
        elif line.startswith("- ") and current_key:
            bloque[current_key].append(line[2:])
        elif not line:
            current_key = None

    if bloque:
        unidades.append(bloque)

    return unidades


def format_units_to_boxes(text):
    unidades = parse_gemini_response_to_units(text)
    html = ""

    for index, unidad in enumerate(unidades, start=1):
        html += f"""
        <table style="width: 100%; border: 2px solid #4a148c; border-collapse: collapse; margin-bottom: 30px; font-family: Arial, sans-serif; font-size: 14px;">
            <tr>
                <th colspan="2" style="background-color: #f3e8ff; color: #4a148c; padding: 10px; font-size: 16px; text-align: left;">
                    Unidad {index}: {unidad['titulo']}
                </th>
            </tr>
        """

        def fila(titulo, items):
            if not items:
                return ""
            return f"""
            <tr>
                <td style="width: 30%; font-weight: bold; vertical-align: top; padding: 8px; background-color: #f9f9f9;">{titulo}</td>
                <td style="padding: 8px;">
                    <ul style="margin: 0; padding-left: 20px;">
                        {''.join(f'<li>{item}</li>' for item in items)}
                    </ul>
                </td>
            </tr>
            """

        html += fila("Objetivos específicos", unidad['objetivos'])
        html += fila("Contenidos", unidad['contenidos'])
        html += fila("Orientaciones metodológicas", unidad['metodologias'])
        html += fila("Criterios de evaluación", unidad['criterios'])
        html += fila("Indicadores de evaluación", unidad['indicadores'])

        html += "</table>"

    return html


def splitDatesInUnits(start_date, end_date, units_number):
    index_days = [0, 1, 2, 3, 4]  # lunes a viernes
    available_days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() in index_days:
            available_days.append(current_date)
        current_date += timedelta(days=1)

    total_days = len(available_days)

    if units_number > total_days:
        units_number = total_days

    units = []
    hop = ceil(total_days / units_number)
    for i in range(0, total_days, hop):
        units.append(available_days[i:i+hop])

    if len(units) > units_number:
        units[-2].extend(units[-1])
        units = units[:-1]

    return units





# models = genai.list_models()

# for model in models:
#     print(model.name)
modelName = 'gemini-1.5-flash-002'



def generar_contenido(request):
    print("API Key configurada correctamente. ", os.getenv('GEMINI_API_KEY'))
    if request.method == 'POST':
        form = AnnualPlanForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            # days_class = form.cleaned_data['days_class']
            units_number = form.cleaned_data['units_number']
            level = form.cleaned_data['level']
            school_subject = form.cleaned_data['school_subject']

            units = splitDatesInUnits(start_date, end_date, units_number)
            # Inicializar Gemini
            model = genai.GenerativeModel(modelName)
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

Unidad {units_number}:
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
  
  <p><strong>Nivel:</strong> {level}</p>
  <p><strong>Materia:</strong> {school_subject.name}</p>
  <p><strong>Número de unidades:</strong> {units_number}</p>

 <div class="unidad">
    <h2>Planificación de Unidades</h2>
    {format_units_to_boxes(generated_schema)}
</div>

</body>
</html>
"""

            # Crear PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
                html = HTML(string=html_string)
                html.write_pdf(output.name)

                topics = extractTopicContentPerUnit(html_string)
                content = GeneratedContent.objects.create(
                    user=request.user,
                    school_subject=school_subject,
                    start_date=start_date,
                    end_date=end_date,
                    grade=level,
                    topic=topics,
                    generated_content=html_string,  
                )

                with open(output.name, 'rb') as pdf_file:
                    content.pdf_file.save(f"plan_anual_{content.pk}.pdf", pdf_file)

            return redirect('educamy:dashboard')

    else:
        form = AnnualPlanForm()

    return render(request, 'generateContent.html', {'form': form})




