"""
app.py — Servidor Flask del Sistema Experto SEHSA
==================================================
Componente: Servidor Web (API Bridge)
Rol en la arquitectura:
  - Sirve la interfaz de usuario (static/index.html) en la ruta raíz.
  - Expone los endpoints REST que el frontend (app.js) consume via fetch().
  - Actúa como puente mínimo entre el motor de inferencia (engine.py) y la UI.
  - Gestiona el historial de casos en data/historial_casos.json.

Dependencia externa: solo Flask (pip install flask).
Ejecutar con: python app.py
URL del sistema: http://localhost:5000
"""

import json
import os
from datetime import datetime
from flask import Flask, request, jsonify
from engine import InferenceEngine
from explanation import ExplanationSystem

# -----------------------------------------------------------------------
# Configuración de Flask — carpeta static para index.html, style.css, app.js
# -----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))

# Inicializar el motor de inferencia una sola vez al levantar el servidor
engine = InferenceEngine(ruta_conocimiento=os.path.join(BASE_DIR, 'knowledge'))

# Ruta al historial de casos guardados
HISTORIAL_PATH = os.path.join(BASE_DIR, 'data', 'historial_casos.json')


# -----------------------------------------------------------------------
# Endpoint: raíz — sirve la interfaz de usuario
# -----------------------------------------------------------------------

@app.route('/')
def index():
    """
    Sirve el archivo index.html de la carpeta static/.

    Returns:
        Response: Contenido del archivo index.html.
    """
    return app.send_static_file('index.html')


# -----------------------------------------------------------------------
# Endpoint: /consulta — núcleo de la API, ejecuta el motor de inferencia
# -----------------------------------------------------------------------

@app.route('/consulta', methods=['POST'])
def consulta():
    """
    Recibe los hechos del caso y el perfil del usuario, ejecuta la inferencia
    y devuelve el diagnóstico completo con la explicación.

    Body JSON esperado:
        {
            "hechos": {
                "alimento": {"tipo": "carne_cruda", "es_perecedero": true},
                "temperatura": {"valor_celsius": 14, "medida": true},
                ...
            },
            "perfil": "supervisor"
        }

    Returns:
        JSON: Resultado del motor + explicación generada por ExplanationSystem.
    """
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'Se esperaba un JSON con hechos del caso'}), 400

    hechos = datos.get('hechos', {})
    perfil = datos.get('perfil', 'supervisor')
    modulo_seleccionado = datos.get('modulo', 'general')

    # Validar que se recibieron hechos
    if not hechos:
        return jsonify({'error': 'No se proporcionaron hechos para evaluar'}), 400

    # Ejecutar el motor de inferencia con los hechos del usuario
    resultado = engine.inferir(hechos, perfil)

    # Generar la explicación adaptada al perfil del usuario
    exp = ExplanationSystem(resultado, hechos, perfil)
    resultado['explicacion'] = exp.generar_reporte_dict()
    resultado['modulo_consultado'] = modulo_seleccionado

    return jsonify(resultado)


# -----------------------------------------------------------------------
# Endpoint: /historial — retorna los casos guardados
# -----------------------------------------------------------------------

@app.route('/historial', methods=['GET'])
def historial():
    """
    Retorna el historial completo de casos guardados.

    Returns:
        JSON: Lista de casos guardados ordenados del más reciente al más antiguo.
    """
    casos = _leer_historial()
    # Retornar del más reciente al más antiguo
    return jsonify(list(reversed(casos)))


# -----------------------------------------------------------------------
# Endpoint: /guardar_caso — persiste el caso actual en el historial
# -----------------------------------------------------------------------

@app.route('/guardar_caso', methods=['POST'])
def guardar_caso():
    """
    Guarda el caso actual (hechos + resultado + timestamp) en historial_casos.json.

    Body JSON esperado:
        {
            "hechos":    {...},
            "resultado": {...},
            "perfil":    "supervisor",
            "modulo":    "cadena_frio"
        }

    Returns:
        JSON: {'ok': True, 'id': <id del caso guardado>}
    """
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'Se esperaba un JSON con el caso a guardar'}), 400

    casos = _leer_historial()

    # Construir el objeto de caso con metadata
    nuevo_caso = {
        'id':             len(casos) + 1,
        'timestamp':      datetime.now().isoformat(),
        'fecha_legible':  datetime.now().strftime('%d/%m/%Y %H:%M'),
        'perfil':         datos.get('perfil', 'supervisor'),
        'modulo':         datos.get('modulo', ''),
        'nivel_riesgo':   datos.get('resultado', {}).get('nivel_riesgo_final', 'BAJO'),
        'diagnostico':    datos.get('resultado', {}).get('diagnostico', '')[:200],
        'reglas_ids':     [r['id'] for r in datos.get('resultado', {}).get('reglas_activadas', [])],
        'hechos':         datos.get('hechos', {}),
        'resultado':      datos.get('resultado', {})
    }

    casos.append(nuevo_caso)
    _escribir_historial(casos)

    return jsonify({'ok': True, 'id': nuevo_caso['id']})


# -----------------------------------------------------------------------
# Endpoint: /modulos — retorna los módulos con sus preguntas
# -----------------------------------------------------------------------

@app.route('/modulos', methods=['GET'])
def modulos():
    """
    Retorna la lista de módulos disponibles con sus preguntas asociadas.

    Las preguntas guían al usuario en la carga de hechos según el módulo seleccionado.
    Cada pregunta tiene: id (objeto.atributo), texto, tipo, opciones (si aplica),
    requerido (bool) y dependencia (si aplica).

    Returns:
        JSON: Lista de módulos con metadatos y preguntas.
    """
    modulos_info = [
        {
            'id':          'cadena_frio',
            'nombre':      'Cadena de frío y temperaturas',
            'descripcion': 'Temperatura de almacenamiento, equipos de refrigeración, recepción de mercadería y cocción',
            'icono':       'thermometer',
            'preguntas':   _preguntas_cadena_frio()
        },
        {
            'id':          'contaminacion',
            'nombre':      'Contaminación cruzada e higiene',
            'descripcion': 'Higiene del personal, manejo de utensilios, estado del alimento, cuerpos extraños',
            'icono':       'shield-x',
            'preguntas':   _preguntas_contaminacion()
        },
        {
            'id':          'epp',
            'nombre':      'Seguridad laboral y EPP',
            'descripcion': 'Equipos de protección personal, ergonomía, condiciones del área y accidentes',
            'icono':       'hard-hat',
            'preguntas':   _preguntas_epp()
        },
        {
            'id':          'plagas',
            'nombre':      'Control de plagas',
            'descripcion': 'Presencia de vectores, estado de envases y programa de control de plagas',
            'icono':       'bug',
            'preguntas':   _preguntas_plagas()
        },
        {
            'id':          'documentacion',
            'nombre':      'Documentación y normativa',
            'descripcion': 'Registros de temperatura, rotulación de productos y trazabilidad',
            'icono':       'file-text',
            'preguntas':   _preguntas_documentacion()
        }
    ]

    # Pregunta global sobre ETA — se agrega a todos los módulos
    pregunta_eta = {
        'id':         'incidente.sospecha_ETA',
        'texto':      '¿Hay alguna persona con síntomas que podrían deberse al consumo de alimentos del establecimiento?',
        'tipo':       'bool',
        'requerido':  True,
        'alerta':     'Si responde Sí, el sistema derivará INMEDIATAMENTE a médico y autoridad sanitaria.'
    }

    for m in modulos_info:
        m['preguntas'].insert(0, pregunta_eta)

    return jsonify(modulos_info)


# -----------------------------------------------------------------------
# Endpoint: /reporte_html — genera HTML imprimible del último caso
# -----------------------------------------------------------------------

@app.route('/reporte_html', methods=['POST'])
def reporte_html():
    """
    Genera el reporte HTML imprimible para un caso dado.

    Body JSON esperado: mismo formato que /consulta.

    Returns:
        HTML: Reporte completo como documento HTML.
    """
    datos = request.get_json()
    if not datos:
        return 'Error: se esperaba JSON', 400

    hechos = datos.get('hechos', {})
    perfil = datos.get('perfil', 'supervisor')

    resultado = engine.inferir(hechos, perfil)
    exp = ExplanationSystem(resultado, hechos, perfil)
    html = exp.generar_reporte_html()

    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


# -----------------------------------------------------------------------
# Helpers internos para el historial
# -----------------------------------------------------------------------

def _leer_historial() -> list:
    """
    Lee el historial de casos desde el archivo JSON.

    Returns:
        list: Lista de casos guardados, o lista vacía si el archivo no existe.
    """
    if not os.path.exists(HISTORIAL_PATH):
        return []
    try:
        with open(HISTORIAL_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _escribir_historial(casos: list):
    """
    Escribe el historial de casos en el archivo JSON.

    Args:
        casos (list): Lista de casos a guardar.
    """
    os.makedirs(os.path.dirname(HISTORIAL_PATH), exist_ok=True)
    with open(HISTORIAL_PATH, 'w', encoding='utf-8') as f:
        json.dump(casos, f, ensure_ascii=False, indent=2, default=str)


# -----------------------------------------------------------------------
# Helpers de preguntas por módulo (usados en /modulos)
# -----------------------------------------------------------------------

def _preguntas_cadena_frio() -> list:
    return [
        {'id': 'alimento.es_perecedero',        'texto': '¿El alimento involucrado es perecedero (requiere refrigeración)?', 'tipo': 'bool', 'requerido': True},
        {'id': 'alimento.tipo',                  'texto': '¿Qué tipo de alimento es?', 'tipo': 'select', 'requerido': False,
         'opciones': [{'valor': 'carne_cruda', 'etiqueta': 'Carne cruda (res, cerdo, ave, pescado)'},
                      {'valor': 'cocido_listo', 'etiqueta': 'Cocido listo para consumo (pollo, milanesas, empanadas)'},
                      {'valor': 'cocido_no_vendido', 'etiqueta': 'Cocido del día anterior no vendido'},
                      {'valor': 'lacteo', 'etiqueta': 'Lácteo (queso, yogur, leche)'},
                      {'valor': 'otro_perecedero', 'etiqueta': 'Otro perecedero'}]},
        {'id': 'temperatura.medida',             'texto': '¿Se realizó medición de temperatura con termómetro?', 'tipo': 'bool', 'requerido': True},
        {'id': 'temperatura.valor_celsius',      'texto': '¿Cuál es la temperatura medida en °C?', 'tipo': 'number', 'requerido': False, 'depende_de': 'temperatura.medida=true'},
        {'id': 'equipo.tipo',                    'texto': '¿Qué equipo está involucrado?', 'tipo': 'select', 'requerido': False,
         'opciones': [{'valor': 'heladera', 'etiqueta': 'Heladera / Refrigerador'},
                      {'valor': 'exhibidora_caliente', 'etiqueta': 'Exhibidora caliente (rotissería)'},
                      {'valor': 'camara_frigorifica', 'etiqueta': 'Cámara frigorífica'},
                      {'valor': 'ninguno', 'etiqueta': 'Sin equipo / Ambiente'}]},
        {'id': 'equipo.funcionando',             'texto': '¿El equipo está funcionando correctamente?', 'tipo': 'bool', 'requerido': False},
        {'id': 'exposicion.tiempo_conocido',     'texto': '¿Se conoce el tiempo de exposición del alimento fuera de temperatura segura?', 'tipo': 'bool', 'requerido': True},
        {'id': 'exposicion.horas',               'texto': '¿Cuántas horas lleva el alimento expuesto?', 'tipo': 'number', 'requerido': False, 'depende_de': 'exposicion.tiempo_conocido=true'},
        {'id': 'alimento.origen',                'texto': '¿El alimento es de origen animal (carnes, aves, huevos, lácteos)?', 'tipo': 'select', 'requerido': False,
         'opciones': [{'valor': 'animal', 'etiqueta': 'Sí, es de origen animal'},
                      {'valor': 'vegetal', 'etiqueta': 'No, es de origen vegetal'}]},
        {'id': 'coccion.temperatura',            'texto': '¿A qué temperatura se está cocinando el alimento (°C)?', 'tipo': 'number', 'requerido': False},
        {'id': 'recepcion.temperatura_fuera_rango', 'texto': '¿La temperatura del producto al momento de recibirlo del proveedor estaba fuera del rango admisible?', 'tipo': 'bool', 'requerido': False},
        {'id': 'proveedor.justifica_cadena',     'texto': '¿El proveedor puede justificar documentalmente el mantenimiento de la cadena de frío durante el transporte?', 'tipo': 'bool', 'requerido': False, 'depende_de': 'recepcion.temperatura_fuera_rango=true'},
        {'id': 'conservacion.correcta',          'texto': '(Para cocido del día anterior) ¿La conservación posterior a la cocción fue correcta?', 'tipo': 'bool', 'requerido': False},
        {'id': 'consumo.mismo_dia',              'texto': '(Para cocido no vendido) ¿Se va a consumir o vender el mismo día?', 'tipo': 'bool', 'requerido': False},
    ]


def _preguntas_contaminacion() -> list:
    return [
        {'id': 'alimento.estado_organo', 'texto': '¿Cuál es el estado organoléptico del alimento?', 'tipo': 'select', 'requerido': True,
         'opciones': [{'valor': 'normal', 'etiqueta': 'Normal (apariencia, olor y textura correctos)'},
                      {'valor': 'olor_anormal', 'etiqueta': 'Olor anormal o putrefacto'},
                      {'valor': 'color_alterado', 'etiqueta': 'Color alterado (verdoso, negruzco, iridiscente)'},
                      {'valor': 'textura_anormal', 'etiqueta': 'Textura anormal (viscoso, desintegrado, blando)'}]},
        {'id': 'alimento.tipo',                    'texto': '¿Qué tipo de alimento es?', 'tipo': 'select', 'requerido': False,
         'opciones': [{'valor': 'cocido_listo', 'etiqueta': 'Cocido listo para consumo'},
                      {'valor': 'carne_cruda', 'etiqueta': 'Carne cruda'},
                      {'valor': 'otro', 'etiqueta': 'Otro tipo de alimento'}]},
        {'id': 'personal.contacto_crudo_cocido',   'texto': '¿Hubo contacto entre alimento crudo y cocido listo para consumo (directo o vía utensilios)?', 'tipo': 'bool', 'requerido': True},
        {'id': 'personal.lavo_manos',              'texto': '¿El operario se lavó correctamente las manos antes de manipular el alimento?', 'tipo': 'bool', 'requerido': True},
        {'id': 'personal.va_a_manipular_listo',    'texto': '¿El operario va a manipular alimento listo para consumo sin cocción adicional?', 'tipo': 'bool', 'requerido': False},
        {'id': 'utensilio.compartido_sin_lavar',   'texto': '¿Se utilizaron utensilios (tablas, cuchillos, bandejas) para alimentos crudos y cocidos sin lavarlos entre usos?', 'tipo': 'bool', 'requerido': True},
        {'id': 'alimento.cuerpo_extrano',          'texto': '¿Se detectó algún cuerpo extraño en el alimento (vidrio, metal, plástico, insecto)?', 'tipo': 'bool', 'requerido': True},
        {'id': 'alimento.en_venta',                'texto': '¿El alimento está disponible para la venta al público en este momento?', 'tipo': 'bool', 'requerido': False},
    ]


def _preguntas_epp() -> list:
    return [
        {'id': 'personal.usa_epp',               'texto': '¿El operario está usando los Equipos de Protección Personal (EPP) requeridos para la tarea?', 'tipo': 'bool', 'requerido': True},
        {'id': 'establecimiento.area',            'texto': '¿En qué área del establecimiento se realiza la tarea?', 'tipo': 'select', 'requerido': True,
         'opciones': [{'valor': 'limpieza', 'etiqueta': 'Área de limpieza / saneamiento'},
                      {'valor': 'produccion', 'etiqueta': 'Área de producción / elaboración'},
                      {'valor': 'deposito', 'etiqueta': 'Depósito / almacenamiento'},
                      {'valor': 'circulacion', 'etiqueta': 'Pasillo / área de circulación'},
                      {'valor': 'frigorifico', 'etiqueta': 'Cámara frigorífica'},
                      {'valor': 'otro', 'etiqueta': 'Otra área'}]},
        {'id': 'quimico.tipo',                   'texto': '¿Qué producto químico se está utilizando?', 'tipo': 'select', 'requerido': False,
         'opciones': [{'valor': 'hipoclorito', 'etiqueta': 'Hipoclorito de sodio (lavandina / cloro)'},
                      {'valor': 'detergente', 'etiqueta': 'Detergente'},
                      {'valor': 'desinfectante', 'etiqueta': 'Otro desinfectante'},
                      {'valor': 'ninguno', 'etiqueta': 'No se usa químico'}]},
        {'id': 'personal.levanta_cargas_sin_tecnica', 'texto': '¿El operario levanta cargas manualmente sin aplicar la técnica ergonómica correcta (sin doblar rodillas, espalda recta)?', 'tipo': 'bool', 'requerido': False},
        {'id': 'piso.humedo',                    'texto': '¿El piso del área está húmedo (por limpieza, derrame u otra causa)?', 'tipo': 'bool', 'requerido': False},
        {'id': 'senalizacion.presente',          'texto': '¿El área húmeda está correctamente señalizada con cartel de "Piso Mojado"?', 'tipo': 'bool', 'requerido': False, 'depende_de': 'piso.humedo=true'},
        {'id': 'incidente.accidente_laboral',    'texto': '¿Ocurrió un accidente laboral que afectó a algún trabajador del establecimiento?', 'tipo': 'bool', 'requerido': True},
    ]


def _preguntas_plagas() -> list:
    return [
        {'id': 'plaga.indicios',                    'texto': '¿Hay indicios de presencia de plagas (rastros, excrementos en área, avistamiento de insectos o roedores)?', 'tipo': 'bool', 'requerido': True},
        {'id': 'alimento.envase_hermetico',         'texto': '¿Los productos potencialmente afectados están en envases herméticos (cerrados al vacío, lata, frasco con tapa)?', 'tipo': 'bool', 'requerido': False, 'depende_de': 'plaga.indicios=true'},
        {'id': 'alimento.envase_dañado',            'texto': '¿Alguno de los envases está visiblemente dañado, roído, perforado o roto?', 'tipo': 'bool', 'requerido': False, 'depende_de': 'plaga.indicios=true'},
        {'id': 'plaga.excrementos_sobre_productos', 'texto': '¿Se detectaron excrementos directamente sobre los productos o sus envases?', 'tipo': 'bool', 'requerido': False, 'depende_de': 'plaga.indicios=true'},
        {'id': 'plaga.dias_ultimo_control',         'texto': '¿Hace cuántos días fue la última visita del servicio de control de plagas?', 'tipo': 'number', 'requerido': False},
    ]


def _preguntas_documentacion() -> list:
    return [
        {'id': 'documentacion.registros_temperatura', 'texto': '¿Se registra la temperatura de los equipos de frío de forma periódica (planilla de control)?', 'tipo': 'bool', 'requerido': True},
        {'id': 'alimento.perecedero_almacenado',      'texto': '¿Hay alimentos perecederos almacenados en equipos de refrigeración sin registro de temperatura?', 'tipo': 'bool', 'requerido': False},
        {'id': 'documentacion.rotulacion_correcta',   'texto': '¿El producto tiene rotulación correcta y completa (nombre, ingredientes, vencimiento, condiciones de conservación)?', 'tipo': 'bool', 'requerido': True},
        {'id': 'alimento.en_exhibicion',              'texto': '¿El producto con rotulación incorrecta está actualmente en exhibición para la venta?', 'tipo': 'bool', 'requerido': False, 'depende_de': 'documentacion.rotulacion_correcta=false'},
    ]


# -----------------------------------------------------------------------
# Punto de entrada
# -----------------------------------------------------------------------

if __name__ == '__main__':
    print("=" * 60)
    print("  SEHSA — Sistema Experto en Higiene y Seguridad Alimentaria")
    print("  Ing. Carolina G. Marturet — Supermercado Parada Canga")
    print("=" * 60)
    print(f"  Motor cargado con {len(engine.todas_las_reglas)} reglas de conocimiento")
    print(f"  Servidor: http://localhost:5000")
    print("=" * 60)
    # debug=False en producción; PORT viene de la variable de entorno en Render/Railway
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
