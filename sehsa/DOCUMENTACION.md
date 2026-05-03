# Documentación Técnica — SEHSA

## Índice

1. [Arquitectura general](#1-arquitectura-general)
2. [Motor de inferencia](#2-motor-de-inferencia)
3. [Memoria de trabajo](#3-memoria-de-trabajo)
4. [Base de conocimiento](#4-base-de-conocimiento)
5. [Sistema de explicación](#5-sistema-de-explicación)
6. [Interfaz web](#6-interfaz-web)
7. [Flujo completo de ejecución](#7-flujo-completo-de-ejecución)
8. [Manejo de incertidumbre](#8-manejo-de-incertidumbre)

---

## 1. Arquitectura general

SEHSA sigue la arquitectura clásica de un sistema experto con tres capas:

```
┌─────────────────────────────────────────┐
│   INTERFAZ WEB (SPA 7 pantallas)        │
│   index.html · style.css · app.js       │
└──────────────────┬──────────────────────┘
                   │ HTTP / JSON (fetch)
┌──────────────────▼──────────────────────┐
│   SERVIDOR REST (app.py)                │
│   Flask · endpoints /consulta /modulos  │
└──────────────────┬──────────────────────┘
                   │ Python
┌──────────────────▼──────────────────────┐
│   MOTOR DE INFERENCIA (engine.py)       │
│   ┌─────────────────┐ ┌──────────────┐  │
│   │ working_memory  │ │explanation   │  │
│   │ .py (hechos OAV)│ │.py (reportes)│  │
│   └─────────────────┘ └──────────────┘  │
└──────────────────┬──────────────────────┘
                   │ JSON
┌──────────────────▼──────────────────────┐
│   BASE DE CONOCIMIENTO (knowledge/)     │
│   6 archivos JSON · ~30 reglas          │
└─────────────────────────────────────────┘
```

**Flujo de datos:**

1. El usuario completa un formulario en la interfaz web.
2. El frontend envía los hechos al endpoint `/consulta` vía POST JSON.
3. El servidor carga los hechos en la memoria de trabajo y ejecuta el motor.
4. El motor aplica ciclos de encadenamiento hacia adelante hasta llegar a un punto fijo.
5. El sistema de explicación genera el reporte según el perfil del usuario.
6. La respuesta JSON vuelve al frontend y se muestran los resultados.

---

## 2. Motor de inferencia

**Archivo:** `sehsa/engine.py`

### Algoritmo: Encadenamiento hacia adelante (Forward Chaining)

El motor implementa el ciclo **Reconocer–Actuar** con las siguientes fases:

```
1. Cargar hechos del usuario en WorkingMemory
2. Pre-procesar hechos derivados (lógica OR implícita)
3. Evaluar módulo de incertidumbre (RI-01 a RI-05)
   └── Si RI-04 activa → PARADA TOTAL (derivar a autoridad sanitaria)
4. Ciclo principal (repetir hasta punto fijo):
   a. RECONOCER: hallar todas las reglas con condiciones satisfechas y no ejecutadas
   b. CONFLICTO: ordenar por prioridad descendente
   c. ACTUAR: disparar la regla de mayor prioridad, aplicar conclusión a memoria
   d. REPETIR mientras haya candidatas
5. Consolidar nivel de riesgo máximo
6. Retornar diagnóstico + reglas activadas + evidencia
```

### Resolución de conflictos

Cuando múltiples reglas son candidatas simultáneamente, se selecciona la de mayor valor en el campo `"prioridad"` (número entero). Las reglas de riesgo CRÍTICO tienen prioridad 8–10; las de riesgo BAJO, 1–3.

### Prevención de ciclos

Cada regla se marca como ejecutada (`_ejecutadas: set`) al dispararse. Una regla no puede activarse dos veces en la misma sesión de consulta.

### Pre-procesamiento de hechos derivados

Antes del ciclo principal, el motor deriva hechos intermedios para simplificar las condiciones de las reglas. Por ejemplo:

```python
# Si el envase NO es hermético O está dañado → marcar como comprometido
if not hermetico or dañado:
    memoria.agregar("envase", "comprometido", True, derivado=True)

# Si el tiempo de exposición es desconocido → asumir riesgo prolongado (precaución)
if not tiempo_conocido:
    memoria.agregar("exposicion", "riesgo_prolongado", True, derivado=True)
```

---

## 3. Memoria de trabajo

**Archivo:** `sehsa/working_memory.py`

### Formato OAV (Objeto–Atributo–Valor)

Todos los hechos se almacenan en el formato OAV:

```python
{
  "alimento":    {"tipo": "carne_cruda", "es_perecedero": True},
  "temperatura": {"valor_celsius": 14, "medida": True},
  "equipo":      {"tipo": "heladera", "funcionando": False},
  "exposicion":  {"tiempo_conocido": False, "riesgo_prolongado": True}  # derivado
}
```

### Métodos principales

| Método | Descripción |
|--------|-------------|
| `agregar(obj, attr, val, derivado)` | Agrega o actualiza un hecho |
| `obtener(obj, attr)` | Retorna el valor de un hecho |
| `existe(obj, attr)` | Verifica si un hecho existe |
| `evaluar_condicion(cond)` | Evalúa una condición de regla contra los hechos actuales |
| `como_dict()` | Serializa todos los hechos a diccionario |
| `hechos_iniciales` | Propiedad: devuelve sólo los hechos ingresados por el usuario |

### Operadores de condición soportados

`=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not_in`

---

## 4. Base de conocimiento

**Directorio:** `sehsa/knowledge/`

Todas las reglas están almacenadas en archivos JSON. El motor las carga dinámicamente al inicio de cada consulta.

### Estructura de una regla

```json
{
  "id": "R01",
  "nombre": "Rotura de cadena de frío en alimento perecedero",
  "modulo": "cadena_frio",
  "condiciones": [
    {"objeto": "temperatura", "atributo": "valor_celsius", "operador": ">", "valor": 5},
    {"objeto": "alimento", "atributo": "es_perecedero", "operador": "=", "valor": true},
    {"objeto": "exposicion", "atributo": "riesgo_prolongado", "operador": "=", "valor": true}
  ],
  "conclusion": {
    "diagnostico": {"rotura_cadena_frio": true}
  },
  "nivel_riesgo": "CRÍTICO",
  "prioridad": 10,
  "acciones": [
    "Descartar de inmediato todo el lote afectado",
    "Registrar el incidente con fecha, hora y temperatura medida",
    "Reparar o reemplazar el equipo de refrigeración"
  ],
  "normativa": ["CAA Art. 154", "BPM Sección 5.3"],
  "explicacion": "Se detectó rotura de cadena de frío ...",
  "comentario": "Zona de peligro: 5°C–60°C. Límite de 2 horas de exposición."
}
```

### Reglas por módulo

**Incertidumbre (RI-01 a RI-05):**

| Regla | Nombre | Efecto |
|-------|--------|--------|
| RI-01 | Tiempo de exposición desconocido | Deriva `riesgo_prolongado = true` |
| RI-02 | Sin termómetro con señales de deterioro | Diagnóstico CRÍTICO por evidencia sensorial |
| RI-03 | Sin termómetro y apariencia normal | Solicita dato (bloquea conclusión) |
| RI-04 | Sospecha de ETA | PARADA TOTAL — derivar a médico y autoridad sanitaria |
| RI-05 | Datos opcionales faltantes | Advertencia (no bloquea diagnóstico) |

**Cadena de frío (R01 a R06):**

| Regla | Nombre | Riesgo |
|-------|--------|--------|
| R01 | Rotura de cadena de frío | CRÍTICO |
| R02 | Temperatura de cocción insuficiente | ALTO |
| R03 | Equipo de refrigeración sin funcionar | CRÍTICO |
| R04 | Recepción de mercadería en temperatura inadecuada | ALTO |
| R05 | Temperatura en zona de peligro sin medición | MEDIO |
| R06 | Tiempo excedido en zona de peligro | CRÍTICO |

**Contaminación (R07 a R11):**

| Regla | Nombre | Riesgo |
|-------|--------|--------|
| R07 | Contaminación cruzada crudo-cocido | CRÍTICO |
| R08 | Deterioro organoléptico | ALTO |
| R09 | Higiene de manos deficiente | ALTO |
| R10 | Utensilios compartidos sin higienizar | MEDIO |
| R11 | Cuerpo extraño en alimento | CRÍTICO |

**EPP — Equipo de Protección Personal (R12 a R15):**

| Regla | Nombre | Riesgo |
|-------|--------|--------|
| R12 | Sin EPP manipulando químicos | CRÍTICO |
| R13 | Ergonomía deficiente en tareas repetitivas | MEDIO |
| R14 | Área de alto riesgo sin señalización | ALTO |
| R15 | Accidente laboral sin registro | ALTO |

**Plagas (R16 a R18):**

| Regla | Nombre | Riesgo |
|-------|--------|--------|
| R16 | Indicios de roedores o insectos | CRÍTICO |
| R17 | Envase comprometido con producto expuesto | ALTO |
| R18 | Control de plagas sin frecuencia establecida | MEDIO |

**Documentación (R19 a R21):**

| Regla | Nombre | Riesgo |
|-------|--------|--------|
| R19 | Sin registro de temperaturas | MEDIO |
| R20 | Rotulación incorrecta o faltante | ALTO |
| R21 | Sin trazabilidad del lote | MEDIO |

---

## 5. Sistema de explicación

**Archivo:** `sehsa/explanation.py`

El sistema genera reportes adaptados al perfil del usuario:

| Perfil | Detalle | Contenido |
|--------|---------|-----------|
| **operario** | Mínimo | Solo acciones concretas a tomar |
| **supervisor** | Básico | Acciones + razón principal |
| **profesional** | Completo | Traza técnica + normativa + condiciones evaluadas |
| **gerente** | Ejecutivo | Resumen de riesgo + impacto de negocio |

### Estructura del reporte

```python
{
  "perfil": "supervisor",
  "nivel_riesgo": "CRÍTICO",
  "descripcion_riesgo": "Riesgo CRÍTICO — Acción inmediata obligatoria.",
  "diagnostico": "Narrativa del diagnóstico en español",
  "hechos_ingresados": [...],       # Hechos del usuario formateados
  "reglas_activadas": [...],        # Con condiciones cumplidas y valores reales
  "todas_las_acciones": [...],      # Acciones correctivas consolidadas
  "normativa_aplicada": [...],      # Normativa aplicada
  "advertencias": [...],            # Advertencias de incertidumbre
  "datos_faltantes": [...],         # Datos opcionales no provistos
  "justificacion": [...],           # Razonamiento
  "resumen_ejecutivo": [...]        # Solo si perfil == 'gerente'
}
```

### Formatos de salida

- `generar_reporte_dict()` → Diccionario Python serializable a JSON (para el frontend)
- `generar_reporte_html()` → HTML standalone imprimible con CSS inline

---

## 6. Interfaz web

**Archivos:** `sehsa/static/`

La interfaz es una SPA (Single Page Application) de 7 pantallas implementada en HTML/CSS/JS vanilla.

### Flujo de pantallas

```
[1. Inicio] → [2. Perfil] → [3. Módulo] → [4. Formulario] → [5. Resultado] → [6. Explicación]
                                                                                      ↓
                                                                              [7. Historial]
```

### Pantalla 4 — Formulario dinámico

El formulario se genera dinámicamente según el módulo seleccionado. Las preguntas se cargan desde el endpoint `GET /modulos` y soportan:

- **bool** → Checkbox Sí/No
- **select** → Lista desplegable con opciones predefinidas
- **number** → Entrada numérica (temperatura, horas, concentración)
- **Dependencias** → Una pregunta puede depender de la respuesta a otra (ej: mostrar "valor en °C" solo si "¿Se midió temperatura?" = Sí)

### Pantalla 5 — Resultado

Muestra:
- Nivel de riesgo con color correspondiente
- Resumen del diagnóstico
- Lista de reglas activadas
- Acciones inmediatas prioritarias

### Pantalla 6 — Explicación detallada

Muestra:
- Todos los hechos ingresados (formateados en lenguaje natural)
- Reglas disparadas con sus condiciones y valores
- Acciones correctivas completas
- Normativa aplicada
- Datos que faltaron (opcionales)

---

## 7. Flujo completo de ejecución

**Ejemplo práctico: Heladera sin funcionar con carne cruda**

**Hechos ingresados por el usuario:**
```json
{
  "alimento": {"tipo": "carne_cruda", "es_perecedero": true},
  "temperatura": {"valor_celsius": 14, "medida": true},
  "equipo": {"tipo": "heladera", "funcionando": false},
  "exposicion": {"tiempo_conocido": false}
}
```

**Ejecución del motor:**

```
Paso 1: Cargar hechos → WorkingMemory

Paso 2: Pre-procesamiento
  exposicion.tiempo_conocido = false → derivar exposicion.riesgo_prolongado = true

Paso 3: Módulo incertidumbre
  RI-01: tiempo desconocido + perecedero → condiciones ✓ → actuar
    → ya procesado en pre-proc, ningún hecho nuevo
  RI-04: síntomas_eta = false → condición NOT cumplida → no actuar
  Resultado: SIN sospecha de ETA, continuar

Paso 4: Ciclo principal
  Iteración 1:
    Candidatas: R03 (heladera sin funcionar, prio=10), R01 (rotura cadena, prio=10)
    Empate → R03 primero por orden de carga
    Actuar R03 → conclusion: diagnostico.heladera_sin_funcionar = true, nivel = CRÍTICO
  
  Iteración 2:
    Candidatas: R01 (condiciones aún cumplidas, no ejecutada)
    Actuar R01 → conclusion: diagnostico.rotura_cadena_frio = true, nivel = CRÍTICO

  Iteración 3:
    Sin más candidatas → PUNTO FIJO → detener

Paso 5: Consolidar
  nivel_riesgo_final = "CRÍTICO"
  reglas_activadas = [RI-01, R03, R01]
```

**Reporte generado (perfil supervisor):**
```
NIVEL: CRÍTICO

Diagnóstico:
  Se detectó equipo de refrigeración sin funcionar con alimento perecedero a 14°C
  (zona de peligro > 5°C). Exposición de tiempo desconocido (asumida prolongada
  por principio de precaución).

Acciones:
  1. Descartar TODO el lote afectado de inmediato
  2. Registrar incidente con fecha, hora y temperatura medida
  3. Reparar o reemplazar el equipo de refrigeración
  4. Notificar al responsable y autoridad de habilitación

Normativa: CAA Art. 154, BPM Sección 5.3

Hechos evaluados:
  - Alimento: carne cruda (perecedero)
  - Temperatura: 14°C (medida)
  - Equipo: heladera, sin funcionar
  - Tiempo de exposición: desconocido
```

---

## 8. Manejo de incertidumbre

SEHSA implementa un módulo específico para situaciones donde los datos son incompletos o contradictorios. Las reglas RI-01 a RI-05 se evalúan **antes** del ciclo principal y pueden:

1. **Derivar hechos** (RI-01): Si el tiempo de exposición es desconocido y el alimento es perecedero, se asume riesgo prolongado por precaución.

2. **Diagnosticar por evidencia sensorial** (RI-02): Si no hay termómetro pero hay señales de deterioro (olor, color, textura), el diagnóstico es CRÍTICO. La evidencia organoléptica es suficiente.

3. **Solicitar datos** (RI-03): Si no hay termómetro y la apariencia es normal, el sistema no puede concluir y solicita la medición antes de continuar.

4. **Parada de emergencia** (RI-04): Si hay sospecha de ETA (Enfermedad Transmitida por Alimentos — síntomas en consumidores reportados), el motor detiene la inferencia inmediatamente y genera una alerta de derivación a médico y autoridad sanitaria.

5. **Advertencia suave** (RI-05): Si hay datos opcionales faltantes que podrían cambiar el diagnóstico, genera una advertencia sin bloquear.

### Principio de precaución

Ante datos faltantes que impliquen riesgo para la salud, el sistema siempre adopta la hipótesis más desfavorable. Esto asegura que ningún riesgo real quede sin diagnosticar por falta de información.

---

## Pruebas

**Archivos:** `sehsa/tests/`

| Caso | Descripción | Resultado esperado |
|------|-------------|-------------------|
| TC-01 | Heladera sin funcionar, carne cruda | CRÍTICO, R03 + R01 |
| TC-02 | Sin EPP manipulando hipoclorito | CRÍTICO, R12 |
| TC-03 | Contacto crudo-cocido, manos sin lavar | CRÍTICO, R07 + R09 |
| TC-04 | Deterioro organoléptico sin termómetro | CRÍTICO, RI-02 + R08 |
| TC-05 | Excrementos sobre productos, envase roto | CRÍTICO, R16 + R17 |
| TC-06 | Síntomas de ETA reportados | PARADA, RI-04 |

```bash
python tests/test_engine.py
```
