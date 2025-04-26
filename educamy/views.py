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
from .models import ContenidoGenerado
import google.generativeai as genai
from bs4 import BeautifulSoup
import time
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from .forms import PlanAnualForm


load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Create your views here.

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
                return redirect('educamy:generate_content')
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





models = genai.list_models()

for model in models:
    print(model.name)




def extraer_temas_de_tabla(html_string):
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




def dividir_fechas_en_unidades(start_date, end_date, numero_unidades, dias_clase):
    from math import ceil
    dias_validos = {
        'lunes': 0,
        'martes': 1,
        'miércoles': 2,
        'jueves': 3,
        'viernes': 4
    }
    dias_indices = [dias_validos[d] for d in dias_clase]

    dias_disponibles = []
    fecha_actual = start_date
    while fecha_actual <= end_date:
        if fecha_actual.weekday() in dias_indices:
            dias_disponibles.append(fecha_actual)
        fecha_actual += timedelta(days=1)

    total_dias = len(dias_disponibles)

    if numero_unidades > total_dias:
        numero_unidades = total_dias  # 🔥 No puedes tener más unidades que días

    unidades = []
    salto = ceil(total_dias / numero_unidades)

    for i in range(0, total_dias, salto):
        unidades.append(dias_disponibles[i:i+salto])

    # 🔥 Si sobran bloques extra, los ajustamos al final
    if len(unidades) > numero_unidades:
        # Fusionar el último bloque extra en el anterior
        unidades[-2].extend(unidades[-1])
        unidades = unidades[:-1]

    return unidades



# Configura la API de Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))



def formatear_texto_a_html(texto):
    """
    Formatea el texto generado por Gemini a HTML elegante.
    """
    html_result = ""
    lineas = texto.splitlines()

    for linea in lineas:
        linea = linea.strip()

        if linea.startswith("Unidad"):
            html_result += f"<h2 style='margin-top: 40px; font-size: 24px;'>{linea}</h2>\n"
        elif linea.startswith("Título:"):
            html_result += f"<p><strong>{linea}</strong></p>\n"
        elif any(titulo in linea for titulo in ["Objetivos específicos:", "Contenidos:", "Orientaciones metodológicas:", "Criterios de evaluación:", "Indicadores de evaluación:"]):
            html_result += f"<h3 style='margin-top: 20px; font-size: 20px;'>{linea}</h3>\n"
            html_result += "<ul>\n"  # Empezar lista para los bullets
        elif linea.startswith("- "):
            html_result += f"<li>{linea[2:]}</li>\n"
        elif linea == "":
            html_result += "</ul>\n"  # Cerrar lista cuando hay línea vacía
        else:
            html_result += f"<p>{linea}</p>\n"

    if not html_result.endswith("</ul>\n"):
        html_result += "</ul>\n"

    return html_result



def generar_contenido(request):
    if request.method == 'POST':
        form = PlanAnualForm(request.POST)
        if form.is_valid():
            fecha_inicio = form.cleaned_data['fecha_inicio']
            fecha_fin = form.cleaned_data['fecha_fin']
            dias_clase = form.cleaned_data['dias_clase']
            numero_unidades = form.cleaned_data['numero_unidades']
            nivel = form.cleaned_data['nivel']
            materia = form.cleaned_data['materia']

            unidades = dividir_fechas_en_unidades(fecha_inicio, fecha_fin, numero_unidades, dias_clase)

            # Inicializar Gemini
            model = genai.GenerativeModel('gemini-1.5-pro-002')
            chat = model.start_chat(history=[])

            # Generar un solo PROMPT grande
            prompt = f"""
Eres un asistente educativo profesional. Genera la planificación completa de {numero_unidades} unidades didácticas para la materia "{materia.nombre}", nivel "{nivel}" de educación básica.

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

            esquema_generado = "⚠️ Error al generar contenido."

            try:
                response = chat.send_message(prompt)
                esquema_generado = response.text
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
  <p><strong>Fecha Inicio:</strong> {fecha_inicio}</p>
  <p><strong>Fecha Fin:</strong> {fecha_fin}</p>
  <p><strong>Días de clase:</strong> {', '.join(dias_clase)}</p>
  <p><strong>Nivel:</strong> {nivel}</p>
  <p><strong>Materia:</strong> {materia.nombre}</p>
  <p><strong>Número de unidades:</strong> {numero_unidades}</p>

  <div class="unidad">
    <h2>Planificación de Unidades</h2>
    <pre>{esquema_generado}</pre>
  </div>

</body>
</html>
"""

            # Crear PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
                html = HTML(string=html_string)
                html.write_pdf(output.name)

                contenido = ContenidoGenerado.objects.create(
                    usuario=request.user,
                    materia=materia,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    grados=nivel,
                    tema="Planificación Anual",
                    contenido_generado=html_string,
                )

                with open(output.name, 'rb') as pdf_file:
                    contenido.archivo_pdf.save(f"plan_anual_{contenido.pk}.pdf", pdf_file)

            return redirect('educamy:dashboard')

    else:
        form = PlanAnualForm()

    return render(request, 'generateContent.html', {'form': form})



# def generar_contenido(request):
#     if request.method == 'POST':
#         form = PlanAnualForm(request.POST)
#         if form.is_valid():
#             fecha_inicio = form.cleaned_data['fecha_inicio']
#             fecha_fin = form.cleaned_data['fecha_fin']
#             dias_clase = form.cleaned_data['dias_clase']
#             numero_unidades = form.cleaned_data['numero_unidades']
#             nivel = form.cleaned_data['nivel']
#             materia = form.cleaned_data['materia']

#             unidades = dividir_fechas_en_unidades(fecha_inicio, fecha_fin, numero_unidades, dias_clase)

#             # Inicializar Gemini
#             model = genai.GenerativeModel('gemini-1.5-pro-002')
#             chat = model.start_chat(history=[])

#             # Generar un solo PROMPT grande
#             prompt = f"""
# Eres un asistente educativo profesional. Genera la planificación completa de {numero_unidades} unidades didácticas para la materia "{materia.nombre}", nivel "{nivel}" de educación básica.

# Para cada unidad proporciona:

# - Título de la unidad
# - 2 objetivos específicos
# - 3 contenidos temáticos principales
# - 2 orientaciones metodológicas
# - 2 criterios de evaluación
# - 2 indicadores de evaluación

# Formato de salida para cada unidad:

# Unidad {{}}
# Título: {{Título sugerido}}

# Objetivos específicos:
# - Objetivo 1
# - Objetivo 2

# Contenidos:
# - Contenido 1
# - Contenido 2
# - Contenido 3

# Orientaciones metodológicas:
# - Metodología 1
# - Metodología 2

# Criterios de evaluación:
# - Criterio 1
# - Criterio 2

# Indicadores de evaluación:
# - Indicador 1
# - Indicador 2

# NO agregues introducciones, conclusiones ni mensajes extra. Solo las unidades en el formato claro y directo.
# """

#             esquema_generado = "⚠️ Error al generar contenido."

#             try:
#                 response = chat.send_message(prompt)
#                 esquema_generado = response.text
#             except Exception as e:
#                 print(f"Error generando contenido: {e}")
#                 esquema_generado = "⚠️ Error al generar el contenido."

#             # Crear contenido HTML para el PDF
#             esquema_formateado = formatear_texto_a_html(esquema_generado)

#             html_string = f"""
# <html>
# <head>
#   <style>
#     body {{ font-family: Arial, sans-serif; margin: 20px; font-size: 14px; line-height: 1.6; }}
#     h1, h2 {{ color: #333; }}
#     table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
#     th, td {{ border: 1px solid #999; padding: 8px; text-align: left; }}
#     th {{ background-color: #f2f2f2; }}
#     .unidad {{ page-break-before: always; margin-top: 50px; }}
#     pre {{ white-space: pre-wrap; word-wrap: break-word; }}
#   </style>
# </head>
# <body>
#   <h1>Plan Anual de Clase</h1>
#   <p><strong>Fecha Inicio:</strong> {fecha_inicio}</p>
#   <p><strong>Fecha Fin:</strong> {fecha_fin}</p>
#   <p><strong>Días de clase:</strong> {', '.join(dias_clase)}</p>
#   <p><strong>Nivel:</strong> {nivel}</p>
#   <p><strong>Materia:</strong> {materia.nombre}</p>
#   <p><strong>Número de unidades:</strong> {numero_unidades}</p>

#    {esquema_formateado}

# </body>
# </html>
# """

#             # Crear PDF
#             with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
#                 html = HTML(string=html_string)
#                 html.write_pdf(output.name)

#                 contenido = ContenidoGenerado.objects.create(
#                     usuario=request.user,
#                     materia=materia,
#                     fecha_inicio=fecha_inicio,
#                     fecha_fin=fecha_fin,
#                     grados=nivel,
#                     tema="Planificación Anual",
#                     contenido_generado=html_string,
#                 )

#                 with open(output.name, 'rb') as pdf_file:
#                     contenido.archivo_pdf.save(f"plan_anual_{contenido.pk}.pdf", pdf_file)

#             return redirect('educamy:dashboard')

#     else:
#         form = PlanAnualForm()

#     return render(request, 'generateContent.html', {'form': form})
