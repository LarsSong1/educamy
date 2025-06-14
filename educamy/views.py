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
from .models import GeneratedContent, SchoolSubject, MicroPlan, AnualPlan
from .forms import itinerarieForm, AddSchoolSubjectForm
from django.shortcuts import get_object_or_404
from math import ceil
from django.contrib.auth.models import User
import json
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

        if request.user.is_superuser:
            users = User.objects.all()
            print("users", users)
            usersCount = len(users)
            context = {
                'users': users,
                'usersCount': usersCount
            }
            return render(request, 'adminDashboard.html', context)
        else:
            annualItineraries = AnualPlan.objects.filter(generatedContentId__user=request.user).order_by('-created_at')
            microItineraries = MicroPlan.objects.filter(generatedContentId__user=request.user).order_by('-created_at')
            itinerariesCount = annualItineraries.count()
            itinerariesCount += microItineraries.count()
            context = {
                'user': request.user,
                'annualItineraries': annualItineraries,
                'microItineraries': microItineraries,
                'itinerariesCount': itinerariesCount,
            }
            return render(request, 'dashboard.html', context)
    


class ItinerariesView(View):
    def get(self, request, *args, **kwargs):
        annualItineraries = AnualPlan.objects.filter(generatedContentId__user=request.user).order_by('-created_at')
        microItineraries = MicroPlan.objects.filter(generatedContentId__user=request.user).order_by('-created_at')
        itinerariesCount = annualItineraries.count()
        itinerariesCount += microItineraries.count()
     

        print(microItineraries)
     
        context = {
                'user': request.user,
                'annualItineraries': annualItineraries,
                'microItineraries': microItineraries,
                'itinerariesCount': itinerariesCount,
        }
        return render(request, 'itineraries.html', context)
    

class AnnualPlanDeleteView(View):
    def post(self, request, pk):
        annualItineraries = get_object_or_404(AnualPlan, pk=pk, generatedContentId__user=request.user)
        annualItineraries.delete()
        messages.success(request, 'Plan anual eliminado correctamente.')
        return redirect('educamy:itineraries')
        

class MicroPlanDeleteView(View):
    def post(self, request, pk):
        microItineraries = get_object_or_404(MicroPlan, pk=pk, generatedContentId__user=request.user)
        microItineraries.delete()
        messages.success(request, 'Plan microcurricular eliminado correctamente.')
        return redirect('educamy:itineraries')


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




class AnnualItinerarieDetailView(View):
    def get(self, request, pk):
        annualItinerarie = get_object_or_404(AnualPlan, pk=pk, generatedContentId__user=request.user)
        duration = (annualItinerarie.end_date - annualItinerarie.start_date).days
        context = {
             'annualItinerarie': annualItinerarie,
             'duration': duration,
        }
        return render(request, 'annualItinerarieDetail.html', context)


def extractTObjetivePerUnit(html_string):
    soup = BeautifulSoup(html_string, 'html.parser')
    unidades = []

    tablas = soup.find_all('table')

    for tabla in tablas:
        contenido = []
        filas = tabla.find_all('tr')

        for fila in filas:
            celdas = fila.find_all('td')
            if len(celdas) >= 2:
                titulo = celdas[0].get_text(strip=True).lower()
                if "objetivos" in titulo:
                    contenido_html = celdas[1]
                    items = contenido_html.find_all('li')
                    if items:
                        contenido = [li.get_text(strip=True) for li in items]
                    else:
                        texto = contenido_html.get_text(separator='\n').strip()
                        contenido = [line.strip() for line in texto.split('\n') if line.strip()]
                    break

        unidades.append(contenido)

    return unidades



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
    # Evitamos división por cero:
    if units_number < 1:
        raise ValueError("Units_number debe ser al menos 1")
    # Calculamos los días hábiles:
    index_days = [0,1,2,3,4]
    available_days = []
    current = start_date
    while current <= end_date:
        if current.weekday() in index_days:
            available_days.append(current)
        current += timedelta(days=1)

    total_days = len(available_days)
    # Si no hay días hábiles, devolvemos lista vacía
    if total_days == 0:
        return []

    # Si el número de unidades supera días disponibles, ajustamos
    if units_number > total_days:
        units_number = total_days

    hop = ceil(total_days / units_number)
    units = [ available_days[i:i+hop] for i in range(0, total_days, hop) ]

    # Si por el redondeo obtenemos más trozos que unidades, juntamos los dos últimos
    if len(units) > units_number:
        units[-2].extend(units[-1])
        units.pop()

    return units




# models = genai.list_models()

# for model in models:
#     print(model.name)
modelName = 'gemini-1.5-flash-002'


def generateContent(request):
    user = request.user
    if request.method == 'POST':
        form = itinerarieForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            units_number = form.cleaned_data['units_number']
            itinearieType = form.cleaned_data['itinerarieType']
            level = form.cleaned_data['level']
            school_subject = form.cleaned_data['school_subject']
            units = splitDatesInUnits(start_date, end_date, units_number)

            # Inicializar Gemini
            model = genai.GenerativeModel(modelName)
            chat = model.start_chat(history=[])


            if itinearieType == 'micro':
                # Generar un solo PROMPT grande
                generarPlanMicrocurricular(start_date, end_date, units_number, level, school_subject, chat, user)
                return redirect('educamy:dashboard')
            elif itinearieType == 'annual':
                # Generar un solo PROMPT grande
                generarPlanAnual(start_date, end_date, units_number, level, school_subject, chat, user)
                return redirect('educamy:dashboard')
            elif itinearieType == 'quiz':
                generarPreguntasMateria()

    else:
        form = itinerarieForm()

    return render(request, 'generateContent.html', {'form': form})
            



def generarPlanMicrocurricular(start_date, end_date, units_number, level, school_subject, chat, user):
    print("API Key configurada correctamente. ", os.getenv('GEMINI_API_KEY'))
    

           
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
  <h1>Plan Microcurricular de Clase</h1>
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


    gen = GeneratedContent.objects.create(user=user, school_subject=school_subject)

    topics = extractTopicContentPerUnit(html_string)
    objetives = extractTObjetivePerUnit(html_string)
    content = MicroPlan.objects.create(
                    generatedContentId = gen,
                    school_subject=school_subject,
                    start_date=start_date,
                    end_date=end_date,
                    grade=level,
                    topic=topics if isinstance(topics, list) else [],
                    goals=objetives if isinstance(objetives, list) else [],
                    generated_content=html_string,  
                )

    with open(output.name, 'rb') as pdf_file:
        content.pdf_file.save(f"plan_micro_{content.pk}.pdf", pdf_file)


    


def generarPlanAnual(start_date, end_date, units_number, level, school_subject, chat, user):
    prompt = f"""
                Eres un asistente educativo profesional. Genera la planificación completa curricular anual de {units_number} unidades para la materia "{school_subject.name}", 
                Define los objetivos de aprendizaje para una lección sobre la resolución la materia {school_subject}
                nivel "{level}", usando **exactamente** este formato (sin añadir nada más) y priorizando añadir minimo 7 items por literal:

                Unidad 1:
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
                Duracion Unidad {{Duración en semanas sugerida en base a la fecha inicio y fin establecida}} 
                - Duracion
           

                Repite para Unidad 2, Unidad 3, …, Unidad {units_number}.
                Detalles:
                - Fecha de inicio: {start_date}
                - Fecha de fin:    {end_date}
            """
    # 1) Llamada a Gemini
    try:
        resp = chat.send_message(prompt)
        generated_schema = resp.text
    except Exception as e:
        print("Error gemini:", e)
        return

    # 2) Parsear en unidades
    unidades = parse_gemini_response_to_units(generated_schema)
    if not unidades:
        print("Sigue sin parsear unidades:", generated_schema)
        return

    styleForHtml = """
        <style>
            h1 {
                font-size: 30px;
                color: 
            }
        </style>

    """

    # 3) Generar PDF completo
    html_string = f"""
                    <html>
                        <head>
                            {styleForHtml}
                        </head>
                        <body>
                            <h1>Plan Anual: {school_subject.name}</h1>
                            <p>Nivel: {level}</p>
                            <p>Desde {start_date} hasta {end_date}</p>
                            {format_units_to_boxes(generated_schema)}
                        </body>
                    </html>
    """



    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        html = HTML(string=html_string)
        html.write_pdf(output.name)
    
    gen = GeneratedContent.objects.create(user=user, school_subject=school_subject)

    # 5) Acumular en listas cada campo JSON
    titles       = [u["titulo"]      for u in unidades]
    objectives   = [u["objetivos"]   for u in unidades]
    contents     = [u["contenidos"]  for u in unidades]
    metodologias = [u["metodologias"]for u in unidades]
    criterios    = [u["criterios"]   for u in unidades]
    indicadores  = [u["indicadores"] for u in unidades]

    
        # 5) Crear un AnualPlan por unidad
    plan = AnualPlan.objects.create(
        generatedContentId    = gen,
        school_subject        = school_subject,
        unit_title            = titles,
        goals       = objectives,
        grade = level,
        start_date = start_date,
        end_date   = end_date,
        unit_contents         = contents,
        methodologies         = metodologias,
        evaluation_criteria   = criterios,
        evaluation_indicators = indicadores,
        
    )

    with open(output.name, "rb") as f:
        plan.pdf_file.save(f"plan_anual_{plan.pk}.pdf", f)

    



  



def generarPreguntasMateria(request, school_subject, start_date, end_date, level):
    # Iniciar conversación con Gemini para generar preguntas
    model = genai.GenerativeModel('gemini-1.5-flash-002')
    chat = model.start_chat(history=[])

    # Crear el prompt para generar preguntas basadas en la materia seleccionada
    prompt = f"""
    Eres un asistente educativo. Genera un conjunto de preguntas relacionadas con la materia '{school_subject.name}'.
    Las preguntas deben ser adecuadas para un nivel '{level}' y deben cubrir los siguientes aspectos:
    - Definiciones clave
    - Aplicación práctica de conceptos
    - Preguntas de reflexión
    - Preguntas para evaluar comprensión

    Utiliza un estilo claro y profesional.
    """

    generated_questions = "⚠️ Error al generar preguntas."
    try:
        response = chat.send_message(prompt)
        generated_questions = response.text
    except Exception as e:
        print(f"Error generando preguntas: {e}")

    # Generar HTML para las preguntas
    html_string = f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; font-size: 14px; line-height: 1.6; }}
        h1 {{ color: #333; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 10px; }}
      </style>
    </head>
    <body>
      <h1>Preguntas sobre la materia: {school_subject.name}</h1>
      <p><strong>Fecha de inicio:</strong> {start_date}</p>
      <p><strong>Fecha de fin:</strong> {end_date}</p>
      <h2>Preguntas generadas:</h2>
      <ul>
        {''.join(f'<li>{question}</li>' for question in generated_questions.splitlines())}
      </ul>
    </body>
    </html>
    """

    # Crear PDF para las preguntas
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
        html = HTML(string=html_string)
        html.write_pdf(output.name)

        content = GeneratedContent.objects.create(
            user=request.user,
            school_subject=school_subject,
            start_date=start_date,
            end_date=end_date,
            grade=level,
            generated_content=html_string,
        )

        # Guardar el PDF generado
        with open(output.name, 'rb') as pdf_file:
            content.pdf_file.save(f"preguntas_{content.pk}.pdf", pdf_file)

    return redirect('educamy:dashboard')  # Redirigir al dashboard






