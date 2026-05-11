# Documentación Técnica — SEHSA

## Índice

1. [Arquitectura general](#1-arquitectura-general)
2. [Motor de inferencia](#2-motor-de-inferencia)
3. [Memoria de trabajo](#3-memoria-de-trabajo)
4. [Base de conocimiento](#4-base-de-conocimiento)
5. [Sistema de explicación](#5-sistema-de-explicación)
6. [Detector de patrones recurrentes](#6-detector-de-patrones-recurrentes)
7. [Interfaz web](#7-interfaz-web)
8. [Flujo completo de ejecución](#8-flujo-completo-de-ejecución)
9. [Manejo de incertidumbre](#9-manejo-de-incertidumbre)
10. [Pruebas](#10-pruebas)

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
│   Flask · /consulta /modulos            │
│   /historial /analisis_historial        │
└───────┬──────────────────────┬──────────┘
        │ Python                │ Python
┌───────▼──────────┐   ┌───────▼──────────┐
│ MOTOR (engine.py)│   │ DETECTOR PATRONES│
│ working_memory   │   │ pattern_detector  │
│ explanation.py   │   │ .py + config.json │
└───────┬──────────┘   └───────┬──────────┘
        │ JSON                  │ JSON
┌───────▼──────────────────────▼──────────┐
│   BASE DE CONOCIMIENTO (knowledge/)     │
│   6 archivos JSON · 30 reglas           │
│   + tipo_patron + acciones_operario     │
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
  "tipo_patron": "proceso",
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
  "acciones_operario": [
    "Sacá toda la mercadería de esa heladera ahora.",
    "Tirá todo lo que estaba adentro — no sabés cuánto tiempo estuvo mal.",
    "Avisale urgente al encargado."
  ],
  "normativa": ["CAA Art. 154", "BPM Sección 5.3"],
  "explicacion": "Se detectó rotura de cadena de frío ...",
  "comentario": "Zona de peligro: 5°C–60°C. Límite de 2 horas de exposición.",
  "revisar": true
}
```

**Campos destacados:**

| Campo | Descripción |
|-------|-------------|
| `tipo_patron` | Clasificación para el detector: `"estructural"` (falla de equipo), `"proceso"` (error humano), `"informativo"` (evento puntual, no genera recomendación estructural) |
| `acciones_operario` | Versión en voseo argentino, lenguaje observable, sin terminología técnica. El motor usa este campo cuando el perfil es `"operario"`. |
| `revisar` | Flag para marcar contenido que requiere validación del experto de dominio. El motor lo ignora. |

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

| Regla | Nombre | Riesgo | Tipo |
|-------|--------|--------|------|
| R01 | Rotura de cadena de frío | CRÍTICO | proceso |
| R02 | Temperatura de cocción insuficiente | ALTO | proceso |
| R03 | Equipo de refrigeración sin funcionar | CRÍTICO | estructural |
| R04 | Recepción de mercadería en temperatura inadecuada | ALTO | proceso |
| R05 | Temperatura en zona de peligro sin medición | MEDIO | proceso |
| R06 | Tiempo excedido en zona de peligro | CRÍTICO | proceso |

**Contaminación (R07 a R11):**

| Regla | Nombre | Riesgo | Tipo |
|-------|--------|--------|------|
| R07 | Contaminación cruzada crudo-cocido | CRÍTICO | proceso |
| R08 | Deterioro organoléptico | ALTO | proceso |
| R09 | Higiene de manos deficiente | ALTO | proceso |
| R10 | Utensilios compartidos sin higienizar | MEDIO | proceso |
| R11 | Cuerpo extraño en alimento | CRÍTICO | informativo |

**EPP — Equipo de Protección Personal (R12 a R15):**

| Regla | Nombre | Riesgo | Tipo |
|-------|--------|--------|------|
| R12 | Sin EPP manipulando químicos | CRÍTICO | proceso |
| R13 | Ergonomía deficiente en tareas repetitivas | MEDIO | proceso |
| R14 | Área de alto riesgo sin señalización | ALTO | proceso |
| R15 | Accidente laboral sin registro | ALTO | informativo |

**Plagas (R16 a R18):**

| Regla | Nombre | Riesgo | Tipo |
|-------|--------|--------|------|
| R16 | Indicios de plagas con envases herméticos intactos | ALTO | estructural |
| R17 | Indicios de plagas con envases comprometidos (dañados) | CRÍTICO | estructural |
| R18 | Control de plagas vencido (+30 días) con indicios activos | ALTO | proceso |

**Documentación (R19 a R21):**

| Regla | Nombre | Riesgo | Tipo |
|-------|--------|--------|------|
| R19 | Ausencia de registros de temperatura con perecederos almacenados | ALTO | proceso |
| R20 | Rotulación incorrecta o ausente en producto en exhibición | MEDIO | proceso |
| R21 | Sospecha de ETA — fuera de alcance del sistema | CRÍTICO | informativo |

---

## 5. Sistema de explicación

**Archivo:** `sehsa/explanation.py`

El sistema genera reportes completamente adaptados al perfil del usuario. El mismo diagnóstico produce salidas radicalmente diferentes según quién lo consulta.

### Diferencias por perfil

| Perfil | Diagnóstico | Justificación | Acciones |
|--------|-------------|---------------|----------|
| **operario** | Observable: "Hay N problemas..." | Enumeración de lo observado, sin siglas | `acciones_operario` del JSON (voseo, imperativo) |
| **supervisor** | Técnico básico | Reglas activadas + módulos | `acciones` del JSON |
| **profesional** | HACCP completo | Traza con IDs de regla, normativa, condiciones exactas | `acciones` con normativa |
| **gerente** | Ejecutivo | Solo nivel de riesgo y reglas de máxima prioridad | `acciones` + resumen ejecutivo |

### Descripción de riesgo por perfil (operario)

Para operario, los niveles usan lenguaje imperativo directo:

| Nivel | Texto operario |
|-------|----------------|
| CRÍTICO | `PELIGRO ALTO — Actuá ahora mismo. No esperes.` |
| ALTO | `Problema serio — Avisale al encargado y actuá pronto.` |
| MEDIO | `Hay cosas para corregir — Avisale al encargado.` |
| BAJO | `Está bien por ahora — Pero prestale atención.` |

### Selección de acciones

Cuando el perfil es `"operario"`:
1. El sistema busca el campo `acciones_operario` en la regla.
2. Si existe, lo usa (lenguaje observable, voseo argentino).
3. Si no existe, cae al campo `acciones` estándar como respaldo.

### Estructura del reporte

```python
{
  "perfil": "operario",
  "nivel_riesgo": "CRÍTICO",
  "descripcion_riesgo": "PELIGRO ALTO — Actuá ahora mismo. No esperes.",
  "diagnostico": "Encontré 2 problemas. Hay un equipo de frío que no funciona y ...",
  "hechos_ingresados": [...],
  "reglas_activadas": [...],
  "todas_las_acciones": [...],   # acciones_operario si existen
  "normativa_aplicada": [...],
  "advertencias": [...],
  "datos_faltantes": [...],
  "justificacion": [...],
  "resumen_ejecutivo": [...]     # Solo si perfil == 'gerente'
}
```

### Formatos de salida

- `generar_reporte_dict()` → Diccionario Python serializable a JSON (para el frontend)
- `generar_reporte_html()` → HTML standalone imprimible con CSS inline

---

## 6. Detector de patrones recurrentes

**Archivo:** `sehsa/pattern_detector.py`  
**Configuración:** `sehsa/config.json`

### Propósito

Mientras el motor de inferencia diagnostica un caso individual, el detector analiza el **historial completo** buscando causas raíz que se repiten. Si una regla se dispara N veces en los últimos X días, el sistema sugiere una medida correctiva **estructural** (no puntual).

### Configuración (`config.json`)

```json
{
  "pattern_detector": {
    "n_umbral": 3,
    "ventana_dias": 30
  }
}
```

| Parámetro | Descripción |
|-----------|-------------|
| `n_umbral` | Cantidad mínima de repeticiones para considerar un patrón |
| `ventana_dias` | Días hacia atrás que se analizan (ventana deslizante desde hoy) |

Ambos parámetros pueden sobreescribirse por consulta vía query params: `GET /analisis_historial?n=2&dias=60`.

### Algoritmo

```
1. Filtrar casos del historial dentro de la ventana de días
2. Para cada caso, extraer las reglas activadas (lista de IDs)
3. Contar frecuencia de cada rule_id en toda la ventana
4. Seleccionar reglas con frecuencia >= n_umbral
5. Excluir reglas con tipo_patron == "informativo"
6. Ordenar: nivel_riesgo desc > frecuencia desc > ultima_ocurrencia desc
7. Generar recomendación según tipo_patron de cada regla
```

### Clasificación `tipo_patron`

| Valor | Significado | Recomendación generada |
|-------|-------------|------------------------|
| `"estructural"` | Falla repetida de equipo o instalación | Reparación o reemplazo del equipo; revisión de mantenimiento preventivo |
| `"proceso"` | Error humano recurrente | Capacitación del personal; revisión del procedimiento (POES/BPM) |
| `"informativo"` | Evento puntual (ETA, accidente) | **No genera recomendación** — son eventos no recurribles por diseño |

### Respuesta del endpoint `/analisis_historial`

```json
{
  "patrones": [
    {
      "regla_id": "R03",
      "regla_nombre": "Equipo de refrigeración sin funcionar",
      "modulo": "cadena_frio",
      "tipo_patron": "estructural",
      "icono": "gear",
      "frecuencia": 4,
      "ventana_dias": 30,
      "nivel_riesgo_patron": "CRÍTICO",
      "ultima_ocurrencia": "2026-05-08",
      "recomendacion_estructural": "Este equipo falló 4 veces en 30 días. Evaluá reparación definitiva o reemplazo."
    }
  ],
  "total_casos_analizados": 12,
  "ventana_dias": 30,
  "n_umbral": 3
}

---

## 7. Interfaz web

**Archivos:** `sehsa/static/`

La interfaz es una SPA (Single Page Application) de 7 pantallas implementada en HTML/CSS/JS vanilla.

### Flujo de pantallas

```
[1. Inicio] → [2. Perfil] → [3. Módulo] → [4. Formulario] → [5. Resultado] → [6. Explicación]
                                                                                      ↓
                                                                              [7. Historial]
```

### Pantalla 2 — Selección de perfil

El perfil seleccionado se almacena en la variable global `perfil` y se envía en todas las consultas posteriores. Controla el lenguaje del formulario y del reporte.

### Pantalla 4 — Formulario dinámico

El formulario se genera dinámicamente con `GET /modulos?perfil=<perfil>`. Los tipos de pregunta soportados:

| Tipo | Descripción | Componente |
|------|-------------|------------|
| `bool` | Sí / No | Dos botones toggle |
| `select` | Opción de lista | Dropdown `<select>` |
| `number` | Valor numérico | Input con unidad |
| `visual_card` | Selección visual | Grid de tarjetas con swatch de color |

**Preguntas adaptadas al perfil:** cuando el perfil es `"operario"`, el servidor reemplaza el campo `texto` de cada pregunta con `texto_operario` (lenguaje observable, sin siglas). El frontend recibe el texto ya adaptado y no necesita lógica de perfil.

**Tarjetas visuales (`visual_card`):** usadas para el estado organoléptico del alimento. Cada opción muestra:
- Swatch circular de color (siempre visible)
- Etiqueta del estado (ej: "Bueno", "Deteriorado")
- Descripción observable siempre visible debajo (no tooltip)
- `role="radio"` y `aria-label` para accesibilidad

**Dependencias:** una pregunta puede depender de la respuesta a otra. El frontend evalúa las dependencias en tiempo real y muestra/oculta preguntas según corresponda.

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
- Acciones correctivas completas (en lenguaje de perfil)
- Normativa aplicada
- Datos que faltaron (opcionales)

### Pantalla 7 — Historial

El historial carga en paralelo los casos guardados y el análisis de patrones:

```javascript
Promise.all([fetch('/historial'), fetch('/analisis_historial')])
```

**Panel de patrones (`#panel-patrones`):** si el detector encuentra patrones recurrentes, se muestra un panel con tarjetas de alerta antes de la tabla de casos. Cada tarjeta incluye:
- Icono según tipo: engranaje (estructural), persona (proceso)
- Nombre de la regla y badge con nivel de riesgo
- Recomendación estructural
- Botón "Marcar como atendida" — oculta la tarjeta con transición CSS sin eliminarla del servidor

El estado "atendida" se persiste en `sessionStorage` (clave `sehsa_patrones_atendidos`) y se restablece al cerrar el navegador.

---

## 8. Flujo completo de ejecución

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

## 9. Manejo de incertidumbre

SEHSA implementa un módulo específico para situaciones donde los datos son incompletos o contradictorios. Las reglas RI-01 a RI-05 se evalúan **antes** del ciclo principal y pueden:

1. **Derivar hechos** (RI-01): Si el tiempo de exposición es desconocido y el alimento es perecedero, se asume riesgo prolongado por precaución.

2. **Diagnosticar por evidencia sensorial** (RI-02): Si no hay termómetro pero hay señales de deterioro (olor, color, textura), el diagnóstico es CRÍTICO. La evidencia organoléptica es suficiente.

3. **Solicitar datos** (RI-03): Si no hay termómetro y la apariencia es normal, el sistema no puede concluir y solicita la medición antes de continuar.

4. **Parada de emergencia** (RI-04): Si hay sospecha de ETA (Enfermedad Transmitida por Alimentos — síntomas en consumidores reportados), el motor detiene la inferencia inmediatamente y genera una alerta de derivación a médico y autoridad sanitaria.

5. **Advertencia suave** (RI-05): Si hay datos opcionales faltantes que podrían cambiar el diagnóstico, genera una advertencia sin bloquear.

### Principio de precaución

Ante datos faltantes que impliquen riesgo para la salud, el sistema siempre adopta la hipótesis más desfavorable. Esto asegura que ningún riesgo real quede sin diagnosticar por falta de información.

---

## 10. Pruebas

**Archivos:** `sehsa/tests/`

### Motor de inferencia (`test_engine.py`)

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

### Detector de patrones (`test_pattern_detector.py`)

| Caso | Descripción | Resultado esperado |
|------|-------------|-------------------|
| TC-P01 | Historial vacío | Sin patrones |
| TC-P02 | Misma regla 3 veces dentro de la ventana | Patrón detectado |
| TC-P03 | 3 casos de la misma regla, todos fuera de la ventana (35-50 días) | Sin patrones |
| TC-P04 | Regla `"informativo"` repetida 5 veces | Sin patrones (excluidas por diseño) |
| TC-P05 | Múltiples patrones mixtos | Ordenamiento CRÍTICO > ALTO (mayor frecuencia) > ALTO (menor frecuencia) |
| TC-P06 | Patrón estructural vs. patrón proceso | Textos e iconos diferentes |

```bash
# En Windows usar -X utf8 por el carácter → en los mensajes de test
python -X utf8 tests/test_pattern_detector.py
```
