# SEHSA — Sistema Experto en Higiene y Seguridad Alimentaria

Sistema experto basado en encadenamiento hacia adelante para diagnóstico de riesgos en establecimientos de alimentos (supermercados, rotiserías). Desarrollado como proyecto académico de Sistemas Inteligentes.

---

## Descripción

SEHSA evalúa condiciones de higiene y seguridad alimentaria ingresadas por el usuario y genera un diagnóstico con nivel de riesgo, acciones correctivas y normativa aplicable. Utiliza una base de conocimiento de ~30 reglas de producción organizadas en 6 módulos temáticos, con motor de inferencia por encadenamiento hacia adelante.

**Dominio:** Seguridad alimentaria e higiene ocupacional en establecimientos de venta y elaboración de alimentos.  
**Experta de dominio:** Ing. Carolina G. Marturet (Encargada de Rotisería, Supermercado Parada Canga).  
**Normativa base:** CAA (Código Alimentario Argentino), BPM (Buenas Prácticas de Manufactura), Ley 19587, Decreto 351/79.

---

## Características principales

- Motor de inferencia con encadenamiento hacia adelante (ciclos Reconocer-Actuar)
- Manejo de incertidumbre con principio de precaución (5 reglas específicas)
- Detección de sospecha de ETA con derivación inmediata a autoridad sanitaria
- Resolución de conflictos por prioridad numérica
- **Salida adaptada al perfil:** operario recibe lenguaje observable e imperativo en voseo; perfiles técnicos reciben terminología HACCP completa con normativa
- **Preguntas observables para operarios:** el formulario traduce conceptos técnicos a hechos observables ("¿Usaste el mismo cuchillo sin lavar?" en lugar de "¿Hubo contaminación cruzada?")
- **Detección de patrones recurrentes:** si una causa raíz se repite N veces (configurable) en una ventana de X días, el sistema sugiere una medida correctiva estructural
- **Tarjetas visuales de selección** para inputs subjetivos (color y estado organoléptico), con swatch de color, descripción siempre visible y accesibilidad ARIA
- Interfaz web SPA de 7 pantallas (sin frameworks externos)
- Panel de alertas de patrones en el historial, con opción de marcar como atendida
- Historial de casos persistente
- Generación de reportes HTML imprimibles
- Suite de pruebas con 12 casos de validación (6 de motor + 6 de detector de patrones)

---

## Módulos de conocimiento

| Módulo | Reglas | Dominio |
|--------|--------|---------|
| Incertidumbre | RI-01 a RI-05 | Datos faltantes, sospecha de ETA |
| Cadena de frío | R01 a R06 | Temperaturas, refrigeración, cocción |
| Contaminación | R07 a R11 | Contaminación cruzada, estado organoléptico |
| EPP | R12 a R15 | Equipos de protección, ergonomía, accidentes |
| Plagas | R16 a R18 | Indicios, integridad de envases |
| Documentación | R19 a R21 | Registros, rotulación, trazabilidad |

---

## Niveles de riesgo

| Nivel | Color | Urgencia |
|-------|-------|----------|
| CRÍTICO | Rojo | Acción inmediata obligatoria |
| ALTO | Naranja | Urgente antes de continuar operaciones |
| MEDIO | Amarillo | Corregir en el corto plazo |
| BAJO | Verde | Monitorear y prevenir |

---

## Tecnologías

**Backend:** Python 3.x, Flask, Gunicorn  
**Frontend:** HTML5, CSS3, JavaScript ES6+ (sin frameworks)  
**Datos:** JSON (reglas e historial), filesystem

---

## Estructura del proyecto

```
SistemaExperto/
└── sehsa/
    ├── app.py                      # Servidor Flask + endpoints REST
    ├── engine.py                   # Motor de inferencia (encadenamiento hacia adelante)
    ├── working_memory.py           # Memoria de trabajo OAV
    ├── explanation.py              # Sistema de explicación adaptativo por perfil
    ├── pattern_detector.py         # Detección de patrones recurrentes en historial
    ├── config.json                 # Parámetros configurables (umbral, ventana de días)
    ├── requirements.txt            # Dependencias Python
    ├── knowledge/
    │   ├── rules_incertidumbre.json
    │   ├── rules_cadena_frio.json
    │   ├── rules_contaminacion.json
    │   ├── rules_epp.json
    │   ├── rules_plagas.json
    │   └── rules_documentacion.json
    ├── static/
    │   ├── index.html              # SPA de 7 pantallas
    │   ├── style.css               # Estilos responsivos
    │   └── app.js                  # Lógica frontend
    ├── data/
    │   └── historial_casos.json    # Historial (se crea automáticamente)
    └── tests/
        ├── test_engine.py          # Pruebas del motor de inferencia (TC-01 a TC-06)
        ├── test_pattern_detector.py# Pruebas del detector de patrones (TC-P01 a TC-P06)
        └── casos_prueba.json       # Definiciones de casos de prueba
```

---

## Instalación y ejecución

### Requisitos previos

- Python 3.8 o superior
- pip

### Instalación local

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd SistemaExperto/sehsa

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar en modo desarrollo
python app.py
```

El servidor quedará disponible en `http://localhost:5000`.

### Producción (Render / Railway)

```bash
gunicorn --bind 0.0.0.0:$PORT app:app
```

La variable de entorno `PORT` es leída automáticamente por la aplicación.

---

## Uso

1. Abrir `http://localhost:5000` en el navegador.
2. Seleccionar el **perfil de usuario** (operario, supervisor, profesional, gerente).
3. Elegir el **módulo de diagnóstico** (o "general" para evaluación completa).
4. Completar el **formulario** con las condiciones del establecimiento.
5. Ver el **diagnóstico** con nivel de riesgo y acciones recomendadas.
6. Consultar la **explicación detallada** con reglas activadas y normativa.
7. Guardar el caso en el **historial** si se desea.

---

## Ejecutar pruebas

```bash
cd sehsa/

# Motor de inferencia (6 casos)
python tests/test_engine.py

# Detector de patrones (6 casos)
# En Windows usar -X utf8 para evitar error de codificación en consola
python -X utf8 tests/test_pattern_detector.py
```

**Motor de inferencia (TC-01 a TC-06):** rotura de cadena de frío, violación de EPP con químicos, contaminación cruzada, deterioro organoléptico, indicios de plagas y sospecha de ETA con parada inmediata.

**Detector de patrones (TC-P01 a TC-P06):** historial vacío, patrón detectado en ventana, patrón fuera de ventana ignorado, regla informativa excluida, ordenamiento por riesgo y frecuencia, diferenciación de recomendación estructural vs. proceso.

---

## API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Sirve la interfaz web |
| POST | `/consulta` | Ejecuta la inferencia |
| GET | `/modulos?perfil=<perfil>` | Lista módulos y preguntas; adapta texto al perfil |
| POST | `/guardar_caso` | Persiste un caso en historial |
| GET | `/historial` | Obtiene todos los casos guardados |
| GET | `/analisis_historial?n=<n>&dias=<dias>` | Detecta patrones recurrentes en el historial |
| POST | `/reporte_html` | Genera reporte HTML imprimible |

**Ejemplo de llamada a `/consulta`:**

```json
POST /consulta
{
  "hechos": {
    "alimento": {"tipo": "carne_cruda", "es_perecedero": true},
    "temperatura": {"valor_celsius": 14, "medida": true},
    "equipo": {"tipo": "heladera", "funcionando": false},
    "exposicion": {"tiempo_conocido": false}
  },
  "perfil": "supervisor",
  "modulo": "cadena_frio"
}
```

---

## Autores

Proyecto académico — Materia: Sistemas Inteligentes  
Universidad de la Cuenca del Plata (UCP) — 5° Año  
2025
