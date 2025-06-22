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
from educamy.services.genai import GENAI_API_KEY, model













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
     

        for micro in microItineraries:
            print("temas", micro.topic)
     
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
        counter = len(annualItinerarie.unit_title)
        print(counter)
        context = {
             'annualItinerarie': annualItinerarie,
             'duration': duration,
             'counter': counter,
             
            
        }
        return render(request, 'annualItinerarieDetail.html', context)


class MicroItinerarieDetailView(View):
    def get(self, request, pk):
        microItinerarie = get_object_or_404(MicroPlan, pk=pk, generatedContentId__user=request.user)
        duration = (microItinerarie.end_date - microItinerarie.start_date).days
        counter = len(microItinerarie.unit_title)
        print(counter, "counter")
        
        context = {
            'microItinerarie': microItinerarie,
            'duration': duration,
            'counter': counter,
        }
        
        return render(request, 'microItinerarieDetail.html', context)






def extractTObjetivePerUnit(html_string):
    """
    Extrae, por cada tabla (unidad), la lista de 'Objetivos específicos' 
    buscando el encabezado en la segunda fila y el contenido en la tercera.
    Devuelve una lista de listas (una por unidad).
    """
    soup = BeautifulSoup(html_string, 'html.parser')
    resultados = []

    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        # Necesitamos al menos 3 filas: título, encabezados y datos
        if len(rows) < 3:
            continue

        # Segunda fila: encabezados
        header_cells = rows[1].find_all(['th','td'])
        # Tercera fila: contenidos
        data_cells   = rows[2].find_all('td')

        # Buscar la columna cuyos encabezados incluyen "objetivos"
        for idx, th in enumerate(header_cells):
            if 'objetivos' in th.get_text(strip=True).lower():
                cell = data_cells[idx]
                items = cell.find_all('li')
                if items:
                    resultados.append([li.get_text(strip=True) for li in items])
                else:
                    # Texto plano separado por líneas
                    texto = cell.get_text(separator='\n').strip()
                    resultados.append([l for l in (line.strip() for line in texto.split('\n')) if l])
                break  # pasamos a la siguiente tabla

    return resultados


def extractTopicContentPerUnit(html_string):
    """
    Extrae, por cada tabla (unidad), la lista de 'Contenidos' 
    buscando el encabezado en la segunda fila y el contenido en la tercera.
    Devuelve una lista de listas (una por unidad).
    """
    soup = BeautifulSoup(html_string, 'html.parser')
    resultados = []

    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 3:
            continue

        header_cells = rows[1].find_all(['th','td'])
        data_cells   = rows[2].find_all('td')

        for idx, th in enumerate(header_cells):
            if 'contenidos' in th.get_text(strip=True).lower():
                cell = data_cells[idx]
                items = cell.find_all('li')
                if items:
                    resultados.append([li.get_text(strip=True) for li in items])
                else:
                    texto = cell.get_text(separator='\n').strip()
                    resultados.append([l for l in (line.strip() for line in texto.split('\n')) if l])
                break

    return resultados





def parse_gemini_response_to_units(text):
    unidades = []
    bloque = {'titulo': '', 'objetivos': [], 'contenidos': [], 'metodologias': [], 'criterios': [], 'indicadores': []}
    current_key = None

    for line in text.splitlines():
        line = line.strip()

        if line.startswith("Unidad"):
            # Antes de agregar el bloque, verificar si alguna clave contiene datos
            if any(bloque[key] for key in bloque):  # Verificamos si el bloque tiene contenido antes de añadirlo
                unidades.append(bloque)
            # Reiniciamos el bloque para la siguiente unidad
            bloque = {'titulo': '', 'objetivos': [], 'contenidos': [], 'metodologias': [], 'criterios': [], 'indicadores': []}
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
            # Si la línea empieza con un guion, la agregamos a la lista del current_key
            bloque[current_key].append(line[2:].strip())
        elif not line:
            current_key = None  # Cuando encontramos una línea vacía, limpiamos el current_key

    # Añadir el último bloque si contiene datos
    if any(bloque[key] for key in bloque):
        unidades.append(bloque)

    return unidades



def parse_gemini_response_to_micro_units(text):
    """
    Parsea el texto generado por Gemini para crear un listado de unidades microcurriculares,
    extrayendo títulos, objetivos, contenidos y otros campos relevantes.
    """
    unidades = []
    bloque = {'titulo': '', 'goals': [], 'unit_contents': [], 'criterios': [], 'indicadores': []}
    current_key = None

    for line in text.splitlines():
        line = line.strip()

        if line.startswith("Unidad"):
            # Antes de agregar el bloque, verificar si alguna clave contiene datos
            if any(bloque[key] for key in bloque):  # Verificamos si el bloque tiene contenido antes de añadirlo
                unidades.append(bloque)
            # Reiniciamos el bloque para la siguiente unidad
            bloque = {'titulo': '', 'goals': [], 'unit_contents': [], 'criterios': [], 'indicadores': []}
            current_key = None
        elif line.startswith("Título:"):
            bloque['titulo'] = line.replace("Título:", "").strip()
        elif "Objetivos específicos:" in line:
            current_key = 'goals'
        elif "Contenidos:" in line:
            current_key = 'unit_contents'
        elif "Criterios de evaluación:" in line:
            current_key = 'criterios'
        elif "Indicadores de evaluación:" in line:
            current_key = 'indicadores'
        elif line.startswith("- ") and current_key:
            # Si la línea empieza con un guion, la agregamos a la lista del current_key
            bloque[current_key].append(line[2:].strip())
        elif not line:
            current_key = None  # Cuando encontramos una línea vacía, limpiamos el current_key

    # Añadir el último bloque si contiene datos
    if any(bloque[key] for key in bloque):
        unidades.append(bloque)

    return unidades





def format_micro_units_to_boxes(text):
    # Usamos el parseador adecuado para MicroPlan
    unidades = parse_gemini_response_to_micro_units(text)
    html = ""

    # Definimos los títulos de las columnas y las claves correspondientes
    sections = [
        ("Objetivos específicos", "goals"),
        ("Contenidos", "unit_contents"),
        ("Criterios de evaluación", "criterios"),
        ("Indicadores de evaluación", "indicadores"),
    ]
    n_cols = len(sections)

    for index, unidad in enumerate(unidades, start=1):
        # 1) Título que ocupa TODO el ancho
        html += f"""
        <table style="
            width: 100%;
            border: 1px solid #000;
            border-collapse: collapse;
            margin-bottom: 30px;
            font-family: Arial, sans-serif;
            font-size: 14px;
        ">
          <tr>
            <th colspan="{n_cols}" style="
                padding: 10px;
                font-size: 16px;
                text-align: left;
                border: 1px solid #000;
            ">
              Unidad {index}: {unidad['titulo']}
            </th>
          </tr>
          
          <!-- 2) Fila de encabezados de sección -->
          <tr>
        """
        
        for title, _key in sections:
            html += f"""
            <th style="
                padding: 8px;
                text-align: left;
                border: 1px solid #000;
            ">{title}</th>
            """
        html += "</tr>"

        # 3) Fila con los contenidos de cada sección
        html += "<tr>"
        for _title, key in sections:
            items = unidad.get(key, [])
            html += f"""
            <td style="
                padding: 8px;
                vertical-align: top;
                border: 1px solid #000;
            ">
              <ul style="margin:0; padding-left:20px; list-style: disc inside;">
                {''.join(f'<li style="margin-bottom:6px;">{item}</li>' for item in items)}
              </ul>
            </td>
            """
        html += "</tr>"

        html += "</table>"

    return html




def format_units_to_boxes(text):
    unidades = parse_gemini_response_to_units(text)
    html = ""

    # Definimos los títulos de las columnas y la clave en el dict
    sections = [
        ("Objetivos específicos", "objetivos"),
        ("Contenidos",              "contenidos"),
        ("Orientaciones metodológicas", "metodologias"),
        ("Criterios de evaluación", "criterios"),
        ("Indicadores de evaluación", "indicadores"),
    ]
    n_cols = len(sections)

    for index, unidad in enumerate(unidades, start=1):
        # 1) Título que ocupa TODO el ancho
        html += f"""
        <table style="
            width: 100%;
            border: 1px solid #000;
            border-collapse: collapse;
            margin-bottom: 30px;
            font-family: Arial, sans-serif;
            font-size: 14px;
        ">
          <tr>
            <th colspan="{n_cols}" style="
                padding: 10px;
                font-size: 16px;
                text-align: left;
                border: 1px solid #000;
            ">
              Unidad {index}: {unidad['titulo']}
            </th>
          </tr>
          
          <!-- 2) Fila de encabezados de sección -->
          <tr>
        """
        for title, _key in sections:
            html += f"""
            <th style="
                padding: 8px;
                text-align: left;
                border: 1px solid #000;
            ">{title}</th>
            """
        html += "</tr>"

        # 3) Fila con los contenidos de cada sección
        html += "<tr>"
        for _title, key in sections:
            items = unidad.get(key, [])
            html += f"""
            <td style="
                padding: 8px;
                vertical-align: top;
                border: 1px solid #000;
            ">
              <ul style="margin:0; padding-left:20px; list-style: disc inside;">
                {''.join(f'<li style="margin-bottom:6px;">{item}</li>' for item in items)}
              </ul>
            </td>
            """
        html += "</tr>"

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
            college_name = form.cleaned_data['college_name']
            teacher_name = form.cleaned_data['teacher_name']

            # Inicializar Gemini
            
            chat = model.start_chat(history=[])


            if itinearieType == 'micro':
                # Generar un solo PROMPT grande
                generarPlanMicrocurricular(start_date, end_date, units_number, level, school_subject, chat, user, college_name, teacher_name)
                return redirect('educamy:dashboard')
            elif itinearieType == 'annual':
                # Generar un solo PROMPT grande
                generarPlanAnual(start_date, end_date, units_number, level, school_subject, chat, user, college_name, teacher_name, teacher_name)
                return redirect('educamy:dashboard')
          

    else:
        form = itinerarieForm()

    return render(request, 'generateContent.html', {'form': form})
            




def generarPlanMicrocurricular(start_date, end_date, units_number, level, school_subject, chat, user, college_name):
    prompt = f"""
        Eres un asistente educativo profesional. Genera la planificación completa de {units_number} unidades didácticas para la materia "{school_subject.name}", nivel "{level}" de educación básica.

        Para cada unidad proporciona:

        - Título de la unidad
        - 2 objetivos específicos
        - 3 contenidos temáticos principales
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

    # 2) Parsear en unidades
    unidades = parse_gemini_response_to_micro_units(generated_schema)
    if not unidades:
        print("Sigue sin parsear unidades:", generated_schema)
        return

    # Generar PDF
    html_string = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                margin: 25px;
                font-size: 12.5px;
                color: #000;
            }}
            h1 {{
                font-size: 16px;
                text-align: center;
                font-weight: bold;
            }}
            .header {{
                text-align: center;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th, td {{
                border: 1px solid black;
                padding: 5px;
                text-align: left;
                vertical-align: top;
            }}
            .section-title {{
                background-color: #D9D9D9;
                font-weight: bold;
                text-align: left;
                padding: 6px;
            }}
        </style>
    </head>
    <body>

    <table class="sin-borde">
            <tr>
                <td style="width: 20%; text-align: left;"></td>
                <td style="width: 60%; text-align: center;">
                    <div class="encabezado">ESCUELA FISCAL<br>“{college_name.upper()}”</div>
                    <div style="text-align: center; font-weight: bold; font-size: 14px;">PLANIFICACIÓN MICROCURRICULAR DE UNIDAD DIDÁCTICA O PARCIAL</div>
                </td>
                <td style="width: 20%; text-align: right;">
                    <strong>AÑO LECTIVO<br>{start_date.year}-{end_date.year}</strong>
                </td>
            </tr>
    </table>

    <table>
        <tr class="sub-header">
            <td>Asignatura:</td>
            <td>{school_subject.name}</td>
        </tr>
        <tr>
            <td>N° Unidades: </td>
            <td>{units_number}</td>
            <td>Título:</td>
            <td colspan="3">Planificación Microcurricular Generada</td>
        </tr>
        <tr>
        <td>Curso:</td>
        <td>{level}</td>
        <td>N° Semanas:</td>
        <td>{(end_date - start_date).days // 7}</td>
        <td>Fecha de Inicio:</td>
        <td>{start_date}</td>
        </tr>
        <tr>
        <td>Paralelo:</td>
        <td>A</td>
        <td>Fecha de Finalización:</td>
        <td colspan="3">{end_date}</td>
        </tr>
    </table>

    <div class="section-title">1) CONTENIDO CURRICULAR POR UNIDAD</div>
    {format_micro_units_to_boxes(generated_schema)}

    </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        html = HTML(string=html_string)
        html.write_pdf(output.name)
    
    gen = GeneratedContent.objects.create(user=user, school_subject=school_subject)

    # 5) Acumular en listas cada campo JSON
    titles       = [u["titulo"]      for u in unidades]
    objectives   = [u["goals"]       for u in unidades]
    contents     = [u["unit_contents"] for u in unidades]
    criterios    = [u["criterios"]   for u in unidades]
    indicadores  = [u["indicadores"] for u in unidades]

    # 6) Crear un MicroPlan por unidad
    micro_plan = MicroPlan.objects.create(
        generatedContentId = gen,
        school_subject = school_subject,
        unit_title = titles,
        goals = objectives,
        grade = level,
        start_date = start_date,
        end_date = end_date,
        topic = contents,
        evaluation_criteria = criterios,
        evaluation_indicators = indicadores,
    )

    with open(output.name, "rb") as f:
        micro_plan.pdf_file.save(f"plan_micro_{micro_plan.pk}.pdf", f)



def generarPlanAnual(start_date, end_date, units_number, level, school_subject, chat, user):
    prompt = f"""
                Eres un asistente educativo profesional. Genera la planificación completa curricular anual de {units_number} unidades para la materia "{school_subject.name}", 
                Define los objetivos de aprendizaje para una lección sobre la resolución la materia {school_subject}
                nivel "{level}", usando **exactamente** este formato (sin añadir nada más) y priorizando añadir minimo 7 items por literal:

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
                    <style>
                        body {{
                        font-family: 'Arial', sans-serif;
                        margin: 25px;
                        font-size: 12.5px;
                        color: #000;
                        }}
                        h1 {{
                        font-size: 16px;
                        text-align: center;
                        font-weight: bold;
                        }}
                        .header {{
                        text-align: center;
                        font-weight: bold;
                        font-size: 14px;
                        margin-bottom: 10px;
                        }}
                        table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 20px;
                        }}
                        th, td {{
                        border: 1px solid black;
                        padding: 5px;
                        text-align: left;
                        vertical-align: top;
                        }}
                        .section-title {{
                        background-color: #D9D9D9;
                        font-weight: bold;
                        text-align: left;
                        padding: 6px;
                        }}
                        .sub-header td {{
                        background-color: #f2f2f2;
                        font-weight: bold;
                        }}
                    </style>
                    </head>
                    <body>

                    <h1>Plan Microcurricular para {school_subject}</h1>
                    <div class="header">PLANIFICACIÓN MICROCURRICULAR DE UNIDAD DIDÁCTICA O PARCIAL</div>

                    <table>
                        <tr class="sub-header">
                        <td>Asignatura:</td>
                        <td>{school_subject.name}</td>
                        </tr>
                        <tr>
                        <td>N° Unidades: </td>
                        <td>{units_number}</td>
                        <td>Título:</td>
                        <td colspan="3">Planificación Microcurricular Generada</td>
                        </tr>
                        <tr>
                        <td>Curso:</td>
                        <td>{level}</td>
                        <td>N° Semanas:</td>
                        <td>{(end_date - start_date).days // 7}</td>
                        <td>Fecha de Inicio:</td>
                        <td>{start_date}</td>
                        </tr>
                        <tr>
                        <td>Paralelo:</td>
                        <td>A</td>
                        <td>Fecha de Finalización:</td>
                        <td colspan="3">{end_date}</td>
                        </tr>
                    </table>

                    

                    <div class="section-title">1) CONTENIDO CURRICULAR POR UNIDAD</div>

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

    



  





