# SEHSA — Sistema Experto en Higiene y Seguridad Alimentaria

Sistema experto basado en encadenamiento hacia adelante para diagnóstico de riesgos en establecimientos de alimentos (supermercados, rotiserías). Desarrollado como proyecto académico de Sistemas Inteligentes.

---


## Descripción

SEHSA evalúa condiciones de higiene y seguridad alimentaria ingresadas por el usuario y genera un diagnóstico con nivel de riesgo, acciones correctivas y normativa aplicable. Utiliza una base de conocimiento de 26 reglas de producción organizadas en 6 módulos temáticos, con motor de inferencia por encadenamiento hacia adelante.

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

## Reglas del experto

Las reglas están definidas en archivos JSON dentro de `sehsa/knowledge/`. Cada regla combina condiciones sobre hechos de la memoria de trabajo, una conclusión diagnóstica, un nivel de riesgo, prioridad, acciones recomendadas y normativa asociada.

### Incertidumbre

| ID | Regla | Condiciones principales | Riesgo |
|----|-------|-------------------------|--------|
| RI-01 | Tiempo de exposición desconocido en alimento perecedero | Tiempo de exposición desconocido y alimento perecedero | CRÍTICO |
| RI-02 | Temperatura no medida con estado organoléptico alterado | No se midió temperatura y el alimento presenta olor, color o textura anormal | CRÍTICO |
| RI-03 | Temperatura no medida con estado organoléptico normal | No se midió temperatura y el alimento parece normal | MEDIO |
| RI-04 | Sospecha de Enfermedad Transmitida por Alimentos (ETA) | Existe sospecha de personas enfermas por consumo de alimentos | CRÍTICO |
| RI-05 | Datos opcionales faltantes en el caso | Faltan datos opcionales como lote, cantidad o historial | BAJO |

### Cadena de frío

| ID | Regla | Condiciones principales | Riesgo |
|----|-------|-------------------------|--------|
| R01 | Rotura de cadena de frío en alimento perecedero | Temperatura mayor a 5°C, alimento perecedero y exposición prolongada o desconocida | CRÍTICO |
| R02 | Temperatura insuficiente en exhibidora caliente | Exhibidora caliente por debajo de 60°C con alimento cocido listo para consumo | ALTO |
| R03 | Heladera sin funcionar por tiempo desconocido | Heladera apagada o fallando y tiempo de falla desconocido | CRÍTICO |
| R04 | Temperatura de cocción insuficiente | Cocción menor a 60°C en alimento de origen animal | ALTO |
| R05 | Reutilización segura de alimento cocido no vendido | Alimento cocido no vendido, conservación correcta y consumo el mismo día | BAJO |
| R06 | Rechazo de lote por cadena de frío comprometida | Temperatura fuera de rango en recepción y proveedor sin justificación | CRÍTICO |

### Contaminación

| ID | Regla | Condiciones principales | Riesgo |
|----|-------|-------------------------|--------|
| R07 | Contaminación cruzada de alimento cocido listo | Contacto crudo-cocido, sin lavado de manos y alimento listo para consumo | CRÍTICO |
| R08 | Deterioro organoléptico del alimento | Olor anormal, color alterado o textura anormal | CRÍTICO |
| R09 | Manipulación de alimento listo sin lavado de manos | El operario no se lavó las manos antes de manipular alimento listo | ALTO |
| R10 | Uso compartido de utensilios sin limpieza | Utensilios usados para crudo y cocido sin lavado y desinfección | ALTO |
| R11 | Cuerpo extraño detectado en alimento en venta | Cuerpo extraño presente en alimento disponible para venta | CRÍTICO |

### EPP y seguridad laboral

| ID | Regla | Condiciones principales | Riesgo |
|----|-------|-------------------------|--------|
| R12 | Trabajo con hipoclorito sin EPP | Limpieza con hipoclorito sin guantes, antiparras o protección correspondiente | ALTO |
| R13 | Levantamiento manual de cargas sin técnica | Manipulación manual de cargas sin técnica ergonómica | MEDIO |
| R14 | Piso húmedo sin señalización | Piso húmedo en área de circulación sin cartel o barrera preventiva | ALTO |
| R15 | Accidente laboral ocurrido | Se registró un accidente laboral en el establecimiento | ALTO |

### Plagas

| ID | Regla | Condiciones principales | Riesgo |
|----|-------|-------------------------|--------|
| R16 | Indicios de plagas con envases herméticos intactos | Indicios de plaga, envases herméticos y sin excrementos sobre productos | ALTO |
| R17 | Indicios de plagas con envases comprometidos | Indicios de plaga y envases dañados, perforados o no herméticos | CRÍTICO |
| R18 | Control de plagas vencido con indicios activos | Más de 30 días desde el último control e indicios activos de plaga | ALTO |

### Documentación

| ID | Regla | Condiciones principales | Riesgo |
|----|-------|-------------------------|--------|
| R19 | Ausencia de registros de temperatura | No hay registros periódicos y existen perecederos almacenados | ALTO |
| R20 | Rotulación incorrecta o ausente | Producto en exhibición con etiqueta ausente, ilegible o incompleta | MEDIO |
| R21 | Sospecha de ETA fuera de alcance | Personas con síntomas atribuibles al consumo de alimentos | CRÍTICO |

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
git clone https://github.com/StivenAlexis/SistemaExperto
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

### Ejemplo de uso

Caso: al iniciar el turno se detecta una heladera apagada con carne cruda. La temperatura medida es de 14°C y no se sabe cuánto tiempo estuvo sin funcionar.

Hechos ingresados:

```json
{
  "alimento": {
    "tipo": "carne_cruda",
    "es_perecedero": true,
    "vencimiento_vigente": true
  },
  "temperatura": {
    "valor_celsius": 14,
    "medida": true
  },
  "equipo": {
    "tipo": "heladera",
    "funcionando": false
  },
  "exposicion": {
    "tiempo_conocido": false
  }
}
```

Resultado esperado:

- **Nivel de riesgo:** CRÍTICO.
- **Reglas activadas:** RI-01, R03 y R01.
- **Diagnóstico:** rotura de cadena de frío y heladera sin funcionar por tiempo desconocido.
- **Acciones principales:** retirar y descartar los alimentos perecederos afectados, registrar el incidente, avisar al responsable y no volver a usar el equipo hasta su reparación.

Este ejemplo muestra el encadenamiento hacia adelante: RI-01 aplica el principio de precaución ante tiempo desconocido y deriva `exposicion.riesgo_prolongado = true`; ese nuevo hecho permite activar R01 junto con la temperatura mayor a 5°C y el carácter perecedero del alimento. En paralelo, R03 se activa porque la heladera no funciona y no se conoce el tiempo de falla.

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
