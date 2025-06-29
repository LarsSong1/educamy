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
from .models import GeneratedContent, SchoolSubject, MicroPlan, AnualPlan, Quiz
from .forms import itinerarieForm, AddSchoolSubjectForm
from django.shortcuts import get_object_or_404
from math import ceil
from django.contrib.auth.models import User
import json
# Cargar variables de entorno
load_dotenv()
from educamy.services.genai import GENAI_API_KEY, model
from django.utils.decorators import method_decorator
import qrcode
import base64
from io import BytesIO










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


@method_decorator(login_required, name='dispatch')
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
    

@method_decorator(login_required, name='dispatch')
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
    
@method_decorator(login_required, name='dispatch')
class AnnualPlanDeleteView(View):
    def post(self, request, pk):
        annualItineraries = get_object_or_404(AnualPlan, pk=pk, generatedContentId__user=request.user)
        annualItineraries.delete()
        messages.success(request, 'Plan anual eliminado correctamente.')
        return redirect('educamy:itineraries')
        
@method_decorator(login_required, name='dispatch')
class MicroPlanDeleteView(View):
    def post(self, request, pk):
        microItineraries = get_object_or_404(MicroPlan, pk=pk, generatedContentId__user=request.user)
        microItineraries.delete()
        messages.success(request, 'Plan microcurricular eliminado correctamente.')
        return redirect('educamy:itineraries')

@method_decorator(login_required, name='dispatch')
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
    

@method_decorator(login_required, name='dispatch')
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

@method_decorator(login_required, name='dispatch')
class SchoolSubjectDeleteView(View):
    def post(self, request, pk):
        subject = get_object_or_404(SchoolSubject, pk=pk, user=request.user)
        subject.delete()
        return redirect('educamy:school_subjects')


def generate_questions_html(preguntas_texto):
    """Función auxiliar para generar HTML de las preguntas con mejor formato"""
    preguntas = [preg.strip() for preg in preguntas_texto.splitlines() if preg.strip()]
    html_preguntas = ""
    
    for i, pregunta in enumerate(preguntas, 1):
        html_preguntas += f"""
        <div class="question-item">
            <div class="question-number">Pregunta {i}:</div>
            <div style="margin-bottom: 10px;">{pregunta}</div>
            <div class="answer-space">
                <em style="color: #666; font-size: 10px;">Espacio para respuesta:</em>
                <div style="height: 60px; border: 1px dashed #ccc; margin-top: 5px; background-color: white;"></div>
            </div>
        </div>
        """
    
    return html_preguntas



@method_decorator(login_required, name='dispatch')
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


    def post(self, request, pk):
        annualItinerarie = get_object_or_404(AnualPlan, pk=pk, generatedContentId__user=request.user)
        duration = (annualItinerarie.end_date - annualItinerarie.start_date).days
        counter = len(annualItinerarie.unit_title)
        context = {
            'annualItinerarie': annualItinerarie,
            'duration': duration,
            'counter': counter,
        }
        content = request.POST.get('content')
        unit_number = request.POST.get('unit_number')
        annual_plan_id = request.POST.get('annual_plan_id')

        # Llama a Gemini para generar las preguntas
        preguntas = generar_preguntas_quiz(content)

        titulo = f"Quiz Unidad {unit_number}"

        # 1. Crea el quiz sin el PDF (el campo pdf_file puede quedar vacío por ahora)
        quiz = Quiz.objects.create(
            title=titulo,
            unit_number=unit_number,
            content_topic=content,
            anual_plan_id=annual_plan_id,
            created_by=request.user,
            status='Completada'
        )

        # 2. Ahora sí genera el PDF y lo asocia al quiz
        generar_pdf_quiz(titulo, preguntas, unit_number, content, quiz)
        # (Tu función genera y guarda el PDF en quiz.pdf_file)

        # 3. Listo, ahora puedes renderizar la página de detalle
        return render(request, 'annualItinerarieDetail.html', context)
    



def generar_pdf_quiz(titulo, preguntas_texto, unidad, tema, quiz):
    html_string = f"""
    <html>
        <head>
            <style>
                @page {{
                    size: A4 portrait;
                    margin: 15mm;
                }}
                body {{
                    font-family: 'Arial', sans-serif;
                    font-size: 11px;
                    margin: 0;
                    color: #000;
                    line-height: 1.4;
                }}
                .header-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 15px;
                    border: 2px solid #000;
                }}
                .header-table td {{
                    padding: 10px;
                    vertical-align: middle;
                    border-right: 1px solid #000;
                }}
                .header-table td:last-child {{
                    border-right: none;
                }}
                .logo-cell {{
                    width: 20%;
                    text-align: center;
                    background-color: #f5f5f5;
                }}
                .title-cell {{
                    width: 60%;
                    text-align: center;
                    font-weight: bold;
                    font-size: 16px;
                    background-color: #333;
                    color: white;
                }}
                .unit-cell {{
                    width: 20%;
                    text-align: center;
                    font-weight: bold;
                    font-size: 14px;
                    background-color: #f5f5f5;
                    color: #000;
                }}
                .tema-section {{
                    text-align: center;
                    margin-bottom: 15px;
                    padding: 8px;
                    background-color: #f0f0f0;
                    border: 1px solid #999;
                    font-weight: bold;
                    color: #000;
                }}
                .student-info {{
                    margin-bottom: 15px;
                    font-size: 10px;
                }}
                .info-grid {{
                    display: table;
                    width: 100%;
                    border-collapse: separate;
                    border-spacing: 15px 0;
                }}
                .info-left {{
                    display: table-cell;
                    width: 50%;
                    vertical-align: top;
                }}
                .info-right {{
                    display: table-cell;
                    width: 50%;
                    vertical-align: top;
                }}
                .info-row {{
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                }}
                .info-label {{
                    font-weight: bold;
                    min-width: 50px;
                    margin-right: 8px;
                    color: #000;
                }}
                .info-line {{
                    border-bottom: 1px solid #000;
                    flex-grow: 1;
                    height: 18px;
                }}
                .grade-section {{
                    float: right;
                    width: 120px;
                    border: 2px solid #000;
                    padding: 10px;
                    text-align: center;
                    background-color: white;
                    margin-left: 20px;
                    margin-bottom: 15px;
                }}
                .grade-title {{
                    font-weight: bold;
                    margin-bottom: 8px;
                    color: #000;
                    font-size: 11px;
                    text-transform: uppercase;
                }}
                .grade-box {{
                    border: 2px solid #000;
                    width: 50px;
                    height: 50px;
                    margin: 8px auto;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    font-weight: bold;
                    background: white;
                }}
                .grade-text {{
                    font-size: 9px;
                    margin: 5px 0;
                    color: #000;
                    font-weight: normal;
                }}
                .signature-section {{
                    margin-top: 10px;
                    font-size: 9px;
                    color: #000;
                }}
                .signature-line {{
                    border-bottom: 1px solid #000;
                    margin-top: 8px;
                    height: 20px;
                }}
                .instructions {{
                    background-color: #f8f8f8;
                    border: 1px solid #ccc;
                    padding: 12px;
                    margin-bottom: 20px;
                    font-size: 10px;
                }}
                .instructions-icon {{
                    color: #000;
                    font-weight: bold;
                    font-size: 11px;
                }}
                .questions-container {{
                    background-color: white;
                    border: 1px solid #dee2e6;
                    padding: 15px;
                    border-radius: 5px;
                }}
                .question-item {{
                    margin-bottom: 20px;
                    padding: 10px;
                    border-left: 4px solid #007bff;
                    background-color: #f8f9fa;
                }}
                .question-number {{
                    font-weight: bold;
                    color: #007bff;
                    margin-bottom: 5px;
                }}
                .answer-space {{
                    margin-top: 10px;
                    border-top: 1px dashed #ccc;
                    padding-top: 10px;
                    min-height: 40px;
                }}
                .footer {{
                    position: fixed;
                    bottom: 10mm;
                    left: 15mm;
                    right: 15mm;
                    text-align: center;
                    font-size: 10px;
                    color: #666;
                    border-top: 1px solid #ccc;
                    padding-top: 5px;
                }}
            </style>
        </head>
        <body>
            <!-- Header con logo y título -->
            <table class="header-table">
                <tr>
                    <td class="logo-cell">
                        <img src="https://educacion.gob.ec/wp-content/uploads/2024/03/Footer-1.png" 
                             style="max-height: 50px; max-width: 100%;" alt="Logo Ministerio" />
                    </td>
                    <td class="title-cell">
                        {titulo}
                    </td>
                    <td class="unit-cell">
                        Calificación<br>
                        <span style="font-size: 18px; font-weight: bold;">_____</span>
                    </td>
                </tr>
            </table>

            <!-- Tema -->
            <div class="tema-section">
                <strong>TEMA:</strong> {tema}
            </div>

            <div class="student-info">
                <div class="info-grid">
                    <div class="info-left">
                        <div class="info-row">
                            <span class="info-label">Nombre:</span>
                            <div class="info-line"></div>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Curso:</span>
                            <div class="info-line"></div>
                        </div>
                    </div>
                    <div class="info-right">
                        <div class="info-row">
                            <span class="info-label">Fecha:</span>
                            <div class="info-line"></div>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Paralelo:</span>
                            <div class="info-line"></div>
                        </div>
                    </div>
                </div>
            </div>

            
            
            <div style="clear: both;"></div>

            <!-- Instrucciones -->
            <div class="instructions">
                <span class="instructions-icon">📋 INSTRUCCIONES:</span> Lee cuidadosamente cada pregunta y responde de manera completa y clara. 
                Utiliza el espacio proporcionado para cada respuesta. Si necesitas más espacio, continúa en el reverso de la hoja.
            </div>

            <!-- Preguntas -->
            <div class="questions-container">
                <h3 style="margin-top: 0; color: #007bff; text-align: center;">PREGUNTAS</h3>
                {generate_questions_html(preguntas_texto)}
            </div>

            <!-- Footer -->
            <div class="footer">
                Evaluación Académica - Ministerio de Educación del Ecuador
            </div>
        </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        html = HTML(string=html_string)
        html.write_pdf(output.name)
    
    with open(output.name, "rb") as f:
        quiz.pdf_file.save(f"quiz_{quiz.pk}_{unidad}.pdf", f)




@method_decorator(login_required, name='dispatch')
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


def get_unit_date_ranges(start_date, end_date, units_number):
    total_days = (end_date - start_date).days + 1  # Incluye ambos extremos
    days_per_unit = total_days // units_number
    extra_days = total_days % units_number  # Será 0 si es exacto, como tu ejemplo

    ranges = []
    current_start = start_date

    for i in range(units_number):
        # Si hay días extra, añade uno a las primeras unidades (no aplica aquí porque 30/5=6 exacto)
        days = days_per_unit + (1 if i < extra_days else 0)
        current_end = current_start + timedelta(days=days-1)
        ranges.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)
    return ranges



def format_micro_units_to_boxes(text, school_subject, start_date, end_date, units_number):
    # Usamos el parseador adecuado para MicroPlan
    unidades = parse_gemini_response_to_micro_units(text)
    html = ""

    fechas = get_unit_date_ranges(start_date, end_date, units_number)


    # Derive the subject prefix (e.g., "EF" from "Educación Física")
    subject_initials = "".join([word[0] for word in school_subject.name.split() if word[0].isalpha()]).upper()
    
    # Define column headers and their corresponding keys

    section_prefix_map = {
        "Objetivos específicos": "OB",
        "Contenidos": "CO",
        "Criterios de evaluación": "CE",
        "Indicadores de evaluación": "IE",
        # Add lowercase keys if your 'title' variable might come in lowercase from the schema
        "objetivos": "OB",
        "contenidos": "CO",
        "criterios": "CE",
        "indicadores": "IE",    
        
    }
   
    sections = [
            ("Objetivos específicos", "goals"),
            ("Contenidos", "unit_contents"),
            ("Criterios de evaluación", "criterios"),
            ("Indicadores de evaluación", "indicadores"),
    ]
   
    
    n_cols = len(sections)

    for unit_index, unidad in enumerate(unidades, start=1):
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
                    Unidad {unit_index}: {unidad['titulo']}
                    
                    <div style="display:flex; gap:10px;">
                        <p style="float:right; font-size:13px; font-weight:bold; color:#444;">Desde: {fechas[unit_index-1][0].strftime('%d/%m/%Y')}</p>
                        <p style="float:right; font-size:13px; font-weight:bold; color:#444;">Hasta: {fechas[unit_index-1][1].strftime('%d/%m/%Y')}</p>
                    </div>


                </th>
            </tr>
            
            <tr>
        """


        
        for title, _key in sections:
            html += f"""
            <th style="
                padding: 8px;
                text-align: left;
                border: 1px solid #000;
                font: bold;
            ">{title}</th>
            """
        html += "</tr>"

        # 3) Fila con los contenidos de cada sección
        html += "<tr>"
        for title, key in sections:
            items = unidad.get(key, [])
            html_list_items = ""


            section_prefix = section_prefix_map.get(title, "") 
            
            
            if not section_prefix:
                words = title.split()
                section_prefix = "".join([word[0] for word in words if word[0].isalpha()]).upper()
            
            
            for item_idx, item in enumerate(items, start=1):
                    # Objectives get the O.SUBJECT_INITIALS.UNIT_INDEX.ITEM_INDEX. prefix
                html_list_items += f'<li style="margin-bottom:6px;">{section_prefix}.{subject_initials}.{unit_index}.{item_idx}. {item}</li>'
            

            html += f"""
            <td style="
                padding: 8px;
                vertical-align: top;
                border: 1px solid #000;
            ">
              <ul style="margin:0; padding-left:20px; list-style: disc inside;">
                {html_list_items}
              </ul>
            </td>
            """
        html += "</tr>"

        html += "</table>"

    return html



def format_annual_units_to_boxes(text, school_subject, start_date, end_date, units_number):
    unidades = parse_gemini_response_to_units(text)
    html = ""
    subject_initials = "".join([word[0] for word in school_subject.name.split() if word[0].isalpha()]).upper()

    fechas = get_unit_date_ranges(start_date, end_date, units_number)


    section_prefix_map = {
        "Objetivos específicos": "OB",
        "Contenidos": "CO",
        "Criterios de evaluación": "CE",
        "Indicadores de evaluación": "IE",
        "Orientaciones metodológicas": "OM",
        # Add lowercase keys if your 'title' variable might come in lowercase from the schema
        "objetivos": "OB",
        "contenidos": "CO",
        "criterios": "CE",
        "indicadores": "IE",
        "metodologias": "OM",
    }

    # Definimos los títulos de las columnas y la clave en el dict
    sections = [
        ("Objetivos específicos", "objetivos"),
        ("Contenidos",              "contenidos"),
        ("Orientaciones metodológicas", "metodologias"),
        ("Criterios de evaluación", "criterios"),
        ("Indicadores de evaluación", "indicadores"),
    ]
    n_cols = len(sections)

    for unit_index, unidad in enumerate(unidades, start=1):
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
                    Unidad {unit_index}: {unidad['titulo']}
                    <div style="display:flex; gap:10px;">
                        <p style="float:right; font-size:13px; font-weight:bold; color:#444;">Desde: {fechas[unit_index-1][0].strftime('%d/%m/%Y')}</p>
                        <p style="float:right; font-size:13px; font-weight:bold; color:#444;">Hasta: {fechas[unit_index-1][1].strftime('%d/%m/%Y')}</p>
                    </div>
                </th>
            </tr>
            
            <tr>
        """
        
        for title, _key in sections:
            html += f"""
            <th style="
                padding: 8px;
                text-align: left;
                border: 1px solid #000;
                font: bold;
            ">{title}</th>
            """
        html += "</tr>"

        # 3) Fila con los contenidos de cada sección
        html += "<tr>"
        for title, key in sections:
            items = unidad.get(key, [])
            html_list_items = ""

            section_prefix = section_prefix_map.get(title, "") 
            
            
            if not section_prefix:
                words = title.split()
                section_prefix = "".join([word[0] for word in words if word[0].isalpha()]).upper()
            
            
            for item_idx, item in enumerate(items, start=1):
                    # Objectives get the O.SUBJECT_INITIALS.UNIT_INDEX.ITEM_INDEX. prefix
                html_list_items += f'<li style="margin-bottom:6px;">{section_prefix}.{subject_initials}.{unit_index}.{item_idx}. {item}</li>'
            

            html += f"""
            <td style="
                padding: 8px;
                vertical-align: top;
                border: 1px solid #000;
            ">
              <ul style="margin:0; padding-left:20px; list-style: disc inside;">
                {html_list_items}
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
            parallel = form.cleaned_data['parallel']

            if school_subject.name == 'Lengua y Literatura':
                area = "Comunicacional, Literario, Creativo"
                transversal_values = "Lectura crítica, Expresión oral y escrita"
            elif school_subject.name == 'Matemática':
                area = "Científica, Resolutiva, Lógica"
                transversal_values = "Razonamiento lógico, Resolución de problemas"
            elif school_subject.name == 'Ciencias Naturales':
                area = "Científica, Ambiental, Experimental"
                transversal_values = "Investigación científica, Conciencia ambiental"
            elif school_subject.name == 'Estudios Sociales':
                area = "Geográfico, Histórico, Cultural"
                transversal_values = "Ciudadanía, Diversidad cultural"
            elif school_subject.name == 'Educación Física':
                area = "Corporal, Física, Recreativa"
                transversal_values = "Salud, Bienestar físico, Trabajo en equipo"
            elif school_subject.name == 'Educación Cultural y Artística':
                area = "Creativa, Expresiva, Artística"
                transversal_values = "Creatividad, Expresión artística, Valoración cultural"
            elif school_subject.name == 'Inglés':
                area = "Lingüístico, Comunicacional, Cultural"
                transversal_values = "Competencia lingüística, Diversidad cultural"
            else:
                area = "General, Diversificada"  # Por defecto
                transversal_values = "Desarrollo integral, Pensamiento crítico"

            # Inicializar Gemini
            
            chat = model.start_chat(history=[])


            if itinearieType == 'micro':
                # Generar un solo PROMPT grande
                generarPlanMicrocurricular(start_date, end_date, units_number, level, school_subject, chat, user, college_name, teacher_name, area, transversal_values, parallel)
                return redirect('educamy:dashboard')
            elif itinearieType == 'annual':
                # Generar un solo PROMPT grande
                generarPlanAnual(start_date, end_date, units_number, level, school_subject, chat, user, college_name, teacher_name, area, transversal_values, parallel)
                return redirect('educamy:dashboard')
          

    else:
        form = itinerarieForm()

    return render(request, 'generateContent.html', {'form': form})
            




def generarPlanMicrocurricular(start_date, end_date, units_number, level, school_subject, chat, user, college_name, teacher_name, area, transversal_values, parallel):

    delta_days = (end_date - start_date).days
    num_weeks = max(1, (delta_days + 6) // 7)
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
    
    # 3) Generar QR
    qr = qrcode.make(f"Plan Microcurricular - {college_name} - {teacher_name} - {school_subject.name}")
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Generar PDF
    html_string = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4 landscape;
                margin: 20mm;
            }}
            body {{
                font-family: 'Arial', sans-serif;
                font-size: 12px;
                margin: 30px;
                color: #000;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                border: 1px solid black;
                padding: 6px;
                vertical-align: top;
                text-align: left;
            }}
            .sin-borde td {{
                border: none;
            }}
            .encabezado {{
                text-align: center;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .subtitulo {{
                font-weight: bold;
                background-color: #D9D9D9;
            }}
            .seccion {{
                margin-top: 20px;
                margin-bottom: 10px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>

    <table class="sin-borde">
            <tr>
                <td style="width: 20%; text-align: left;">
                    <img src="https://educacion.gob.ec/wp-content/uploads/2024/03/Footer-1.png" style="max-height: 80px;" />
                </td>   
                <td style="width: 60%; text-align: center;">
                    <div class="encabezado">ESCUELA FISCAL<br>“{college_name.upper()}”</div>
                    <div style="text-align: center; font-weight: bold; font-size: 14px;">PLANIFICACIÓN MICROCURRICULAR DE UNIDAD DIDÁCTICA O PARCIAL</div>
                </td>
                <td style="width: 20%; text-align: right;">
                    <strong>AÑO LECTIVO<br>{start_date.year}-{end_date.year}</strong>
                </td>
            </tr>
    </table>
    <div class="seccion">1)Datos informativos</div>
    <table>
        <tr>
            <td style="width: 10%;"><strong>Docente:</strong></td>
            <td style="width: 40%;">{teacher_name}</td>
            <td style="width: 10%;"><strong>Área:</strong></td>
            <td style="width: 40%;">{area}</td>
        </tr>
        <tr class="sub-header">
            <td style="width: 10%;"><strong>Asignatura:</strong></td>
            <td style="width: 40%;">{school_subject.name}</td>
            <td style="width: 10%;"><strong>Grado:</strong></td>
            <td style="width: 40%;">{level}</td>
        </tr>
        <tr>
            <td style="width: 10%;"><strong>N° Unidades:</strong> </td>
            <td style="width: 40%;">{units_number}</td>
            <td style="width: 10%;"><strong>Evaluado:</strong> </td>
            <td style="width: 40%;"> </td>
        </tr>
        <tr>
            <td style="width: 10%;"><strong>N° Semanas:</strong></td>
            <td style="width: 40%;">{ num_weeks }</td>
            <td style="width: 10%;"><strong>Paralelo:</strong></td>
            <td style="width: 40%;">{parallel}</td>
        </tr>
        <tr>
            <td style="width: 10%;"><strong>Fecha de Inicio:</strong></td>
            <td style="width: 40%;">{start_date.strftime("%d/%m/%Y")}</td>
            <td style="width: 10%;"><strong>Fecha de Finalización:</strong></td>
            <td style="width: 40%;" colspan="3">{end_date.strftime("%d/%m/%Y")}</td>
        </tr>
    </table>

    <div class="seccion">2) CONTENIDO CURRICULAR POR UNIDAD</div>
    {format_micro_units_to_boxes(generated_schema, school_subject, start_date, end_date, units_number)}


    <!-- Firmas -->
    <div style="page-break-before: always;"></div>
    <div style="margin-top: 50px; text-align: center;">
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
            <tr style="font-weight: bold;">
                <td style="width: 33.33%;">ELABORADO</td>
                <td style="width: 33.33%;">REVISADO</td>
                <td style="width: 33.33%;">APROBADO</td>
            </tr>
            <tr>
                <td>Docente(s): {teacher_name}</td>
                <td>Director(a):</td>
                <td>Vicerrector:</td>
            </tr>
            <tr style="height: 100px;">
                <td style="vertical-align: bottom;">
                    ___________________________<br>
                    Firma
                </td>
                <td style="vertical-align: bottom;">
                    ___________________________<br>
                    Firma
                </td>
                <td style="vertical-align: bottom;">
                    ___________________________<br>
                    Firma
                </td>
            </tr>
            <tr>
                <td>Fecha: {end_date.strftime('%d-%m-%Y')}</td>
                <td>Fecha: {end_date.strftime('%d-%m-%Y')}</td>
                <td>Fecha: {end_date.strftime('%d-%m-%Y')}</td>
            </tr>
        </table><br>
        <td style="text-align: center;">
            <img src="data:image/png;base64,{qr_base64}" alt="QR code" style="height: 100px;" />
        </td>
    </div>

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
        teacher_name = teacher_name,
        college_name = college_name,
        area = area,
        parallel = parallel,
    )

    with open(output.name, "rb") as f:
        micro_plan.pdf_file.save(f"plan_micro_{micro_plan.pk}.pdf", f)



def generarPlanAnual(start_date, end_date, units_number, level, school_subject, chat, user, college_name, teacher_name, area, transversal_values, parallel):

    delta_days = (end_date - start_date).days
    num_weeks = max(1, (delta_days + 6) // 7)

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
    

    # 3) Generar QR
    qr = qrcode.make(f"Plan Microcurricular - {college_name} - {teacher_name} - {school_subject.name}")
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

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
                        @page {{
                            size: A4 landscape;
                            margin: 20mm;
                        }}
                        body {{
                            font-family: 'Arial', sans-serif;
                            font-size: 12px;
                            margin: 30px;
                            color: #000;
                        }}
                        table {{
                            width: 100%;
                            border-collapse: collapse;
                        }}
                        th, td {{
                            border: 1px solid black;
                            padding: 6px;
                            vertical-align: top;
                            text-align: left;
                        }}
                        .sin-borde td {{
                            border: none;
                        }}
                        .encabezado {{
                            text-align: center;
                            font-size: 16px;
                            font-weight: bold;
                            margin-bottom: 10px;
                        }}
                        .subtitulo {{
                            font-weight: bold;
                            background-color: #D9D9D9;
                        }}
                        .seccion {{
                            margin-top: 20px;
                            margin-bottom: 10px;
                            font-weight: bold;
                        }}
                    </style>
                </head>
                    <body>

                        <table class="sin-borde">
                            <tr>
                                <td style="width: 20%; text-align: left;">
                                    <img src="https://educacion.gob.ec/wp-content/uploads/2024/03/Footer-1.png" style="max-height: 80px;" />
                                </td>    
                            
                                <td style="width: 60%; text-align: center;">
                                    <div class="encabezado">ESCUELA FISCAL<br>“{college_name.upper()}”</div>
                                    <div style="text-align: center; font-weight: bold; font-size: 14px;">PLANIFICACIÓN CURRICULAR ANNUAL DE UNIDAD DIDÁCTICA O PARCIAL</div>
                                </td>
                                <td style="width: 20%; text-align: right;">
                                    <strong>AÑO LECTIVO<br>{start_date.year}-{end_date.year}</strong>
                                </td>
                            </tr>
                        </table>
                        <div class="seccion">1)Datos informativos</div>

                        <table class="seccion">
                            <tr>
                                <td style="width: 10%;"><strong>Docente:</strong></td>
                                <td style="width: 40%;">{teacher_name}</td>
                                <td style="width: 10%;"><strong>Área:</strong></td>
                                <td style="width: 40%;">{area}</td>
                            </tr>
                            <tr class="sub-header">
                                <td style="width: 10%;"><strong>Asignatura:</strong></td>
                                <td style="width: 40%;">{school_subject.name}</td>
                                <td style="width: 10%;"><strong>Grado:</strong></td>
                                <td style="width: 40%;">{level}</td>
                            </tr>
                            <tr>
                                <td style="width: 10%;"><strong>N° Unidades:</strong> </td>
                                <td style="width: 40%;">{units_number}</td>
                                <td style="width: 10%;"><strong>Evaluado:</strong> </td>
                                <td style="width: 40%;"> </td>
                            </tr>
                            <tr>
                                <td style="width: 10%;"><strong>N° Semanas:</strong></td>
                                <td style="width: 40%;">{ num_weeks }</td>
                                <td style="width: 10%;"><strong>Paralelo:</strong></td>
                                <td style="width: 40%;">{parallel}</td>
                            </tr>
                            <tr>
                                <td style="width: 10%;"><strong>Fecha de Inicio:</strong></td>
                                <td style="width: 40%;">{start_date.strftime("%d/%m/%Y")}</td>
                                <td style="width: 40%;" colspan="3">{end_date.strftime("%d/%m/%Y")}</td>
                            </tr>
                        </table>

                        

                        <div class="seccion">2) CONTENIDO CURRICULAR POR UNIDAD</div>

                        {format_annual_units_to_boxes(generated_schema, school_subject, start_date, end_date, units_number)}


                        <!-- Firmas -->
                        <div style="page-break-before: always;"></div>
                        <div style="margin-top: 50px; text-align: center;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                                <tr style="font-weight: bold;">
                                    <td style="width: 33.33%;">ELABORADO</td>
                                    <td style="width: 33.33%;">REVISADO</td>
                                    <td style="width: 33.33%;">APROBADO</td>
                                </tr>
                                <tr>
                                    <td>Docente(s): {teacher_name}</td>
                                    <td>Director(a):</td>
                                    <td>Vicerrector:</td>
                                </tr>
                                <tr style="height: 100px;">
                                    <td style="vertical-align: bottom;">
                                        ___________________________<br>
                                        Firma
                                    </td>
                                    <td style="vertical-align: bottom;">
                                        ___________________________<br>
                                        Firma
                                    </td>
                                    <td style="vertical-align: bottom;">
                                        ___________________________<br>
                                        Firma
                                    </td>
                                </tr>
                                <tr>
                                    <td>Fecha: {end_date.strftime('%d-%m-%Y')}</td>
                                    <td>Fecha: {end_date.strftime('%d-%m-%Y')}</td>
                                    <td>Fecha: {end_date.strftime('%d-%m-%Y')}</td>
                                </tr>
                            </table><br>
                            <td style="text-align: center;">
                                <img src="data:image/png;base64,{qr_base64}" alt="QR code" style="height: 100px;" />
                            </td>
                        </div>


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
        parallel = parallel,
        area = area,
        teacher_name = teacher_name,
        college_name = college_name,
        
    )

    with open(output.name, "rb") as f:
        plan.pdf_file.save(f"plan_anual_{plan.pk}.pdf", f)

    






def generar_preguntas_quiz(content):
    prompt = f"""
    Eres un generador de quizzes para profesores.
    Redacta 10 preguntas para un quiz sobre: "{content}".
    Solo preguntas, sin respuestas.
    """
    try:
        chat = model.start_chat(history=[])
        resp = chat.send_message(prompt)
        # Puedes devolver como lista o como texto, según tu modelo Quiz
        preguntas = resp.text
        return preguntas
    except Exception as e:
        print("Error generando quiz:", e)
        return "No se pudo generar el quiz automáticamente."
