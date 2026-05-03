"""
test_engine.py — Casos de Prueba del Motor de Inferencia SEHSA
==============================================================
Componente: Suite de tests del motor de inferencia
Rol en la arquitectura:
  - Valida que el motor de inferencia (engine.py) produzca los resultados correctos
    para los 6 casos de prueba definidos en la especificación del sistema.
  - Cada test verifica: hechos → nivel de riesgo esperado + reglas esperadas.
  - Imprime un reporte detallado con PASS/FAIL para cada caso.

Ejecutar con: python tests/test_engine.py  (desde la carpeta sehsa/)
            o: python -m tests.test_engine  (desde sehsa/)
"""

import sys
import os
import json

# Forzar UTF-8 en la salida estándar (necesario en Windows con consola cp1252)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Agregar el directorio raíz del proyecto al path para importar engine.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import InferenceEngine
from explanation import ExplanationSystem

# -----------------------------------------------------------------------
# Constantes de formato para la salida
# -----------------------------------------------------------------------
SEP = "=" * 70
SEP_CASO = "-" * 70
VERDE  = "\033[92m"
ROJO   = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

# Usar colores solo en terminals que los soportan
if sys.platform == 'win32' and 'TERM' not in os.environ:
    VERDE = ROJO = CYAN = RESET = BOLD = ''


def formato_pass():
    return f"{VERDE}[PASS]{RESET}"

def formato_fail():
    return f"{ROJO}[FAIL]{RESET}"


# -----------------------------------------------------------------------
# Definición de los 6 casos de prueba
# -----------------------------------------------------------------------
# Cada caso tiene: nombre, hechos (input), nivel_riesgo_esperado, reglas_esperadas
# La lista reglas_esperadas no tiene que ser exacta en orden, pero todas
# las reglas listadas deben estar en el resultado.

CASOS_PRUEBA = [
    {
        # Caso 1: Valida el encadenamiento RI-01 → R01 + activación independiente de R03
        # RI-01 deriva riesgo_prolongado=True al detectar tiempo desconocido + perecedero
        # R03 actúa sobre heladera no funcionando + tiempo desconocido
        # R01 actúa sobre temp > 5°C + perecedero + riesgo_prolongado (derivado por RI-01)
        "id": 1,
        "nombre": "Fallo de cadena de frío — heladera sin funcionar",
        "descripcion": (
            "Valida el encadenamiento: RI-01 deriva 'riesgo_prolongado=True' que habilita R01. "
            "R03 detecta heladera sin funcionar por tiempo desconocido. "
            "Temperatura 14°C confirma alimento en zona de peligro."
        ),
        "hechos": {
            "alimento":    {"tipo": "carne_cruda", "es_perecedero": True, "vencimiento_vigente": True},
            "temperatura": {"valor_celsius": 14, "medida": True},
            "equipo":      {"tipo": "heladera", "funcionando": False},
            "exposicion":  {"tiempo_conocido": False}
        },
        "nivel_riesgo_esperado": "CRÍTICO",
        "reglas_esperadas": ["RI-01", "R03", "R01"],
        "aspecto_validado": "Encadenamiento hacia adelante: RI-01 genera hecho derivado que activa R01 en ciclo posterior."
    },
    {
        # Caso 2: Valida el módulo de seguridad laboral (EPP)
        # Todas las condiciones de R12 se cumplen: sin EPP + área limpieza + hipoclorito
        # No debe activarse ninguna regla de mayor riesgo
        "id": 2,
        "nombre": "Operario con hipoclorito sin EPP",
        "descripcion": (
            "Valida R12: las tres condiciones (sin EPP + área limpieza + químico hipoclorito) "
            "se cumplen simultáneamente. El nivel de riesgo debe ser ALTO."
        ),
        "hechos": {
            "personal":        {"usa_epp": False},
            "establecimiento": {"area": "limpieza"},
            "quimico":         {"tipo": "hipoclorito", "concentracion": 500},
            "incidente":       {"accidente_laboral": False}
        },
        "nivel_riesgo_esperado": "ALTO",
        "reglas_esperadas": ["R12"],
        "aspecto_validado": "Módulo EPP: R12 actúa con las 3 condiciones completas. No se activa ninguna regla CRÍTICA."
    },
    {
        # Caso 3: Valida el módulo de plagas
        # R16: indicios + envase hermético + sin excrementos sobre productos → ALTO
        # R18: dias > 30 + indicios → ALTO (NOTA: se usan 35 días, no 21, para superar el umbral)
        "id": 3,
        "nombre": "Plaga en depósito con envases herméticos",
        "descripcion": (
            "Valida R16 (indicios + envase íntegro) y R18 (control vencido + indicios). "
            "Se usan 35 días de control (no 21) para superar el umbral de R18 (> 30 días). "
            "Ambas reglas son ALTO, por lo que el nivel final es ALTO."
        ),
        "hechos": {
            "plaga":   {"indicios": True, "excrementos_sobre_productos": False, "dias_ultimo_control": 35},
            "alimento": {"envase_hermetico": True, "envase_dañado": False}
        },
        "nivel_riesgo_esperado": "ALTO",
        "reglas_esperadas": ["R16", "R18"],
        "aspecto_validado": "Módulo plagas: R16 y R18 se activan de forma independiente sobre los mismos indicios."
    },
    {
        # Caso 4: Valida contaminación cruzada con múltiples reglas encadenadas
        # R09: sin lavado + va a manipular listo → ALTO
        # R10: utensilio compartido sin lavar → ALTO
        # R07: contacto crudo-cocido + sin lavado + tipo cocido_listo → CRÍTICO
        "id": 4,
        "nombre": "Contaminación cruzada por utensilios y sin lavado de manos",
        "descripcion": (
            "Valida que se activen R09, R10 y R07 en el mismo caso. "
            "R07 tiene prioridad 10 (CRÍTICO) y domina el nivel de riesgo final. "
            "Prueba múltiples reglas del mismo módulo activadas simultáneamente."
        ),
        "hechos": {
            "personal": {
                "contacto_crudo_cocido": True,
                "lavo_manos": False,
                "va_a_manipular_listo": True
            },
            "utensilio": {"compartido_sin_lavar": True},
            "alimento":  {"tipo": "cocido_listo", "estado_organo": "normal"}
        },
        "nivel_riesgo_esperado": "CRÍTICO",
        "reglas_esperadas": ["R09", "R10", "R07"],
        "aspecto_validado": "Múltiples reglas del módulo contaminación: R07 (CRÍTICO) eleva el nivel máximo final."
    },
    {
        # Caso 5: Valida zona de peligro en caliente (exhibidora caliente por debajo de 60°C)
        # R02: tipo exhibidora_caliente + temp < 60 + alimento cocido_listo → ALTO
        # El equipo funciona (funcionando=True), no se activa R03
        "id": 5,
        "nombre": "Exhibidora caliente por debajo de temperatura",
        "descripcion": (
            "Valida R02: exhibidora caliente con temperatura 52°C < 60°C con alimento cocido. "
            "El equipo funciona (no se activa R03). Solo R02 debe activarse."
        ),
        "hechos": {
            "equipo":      {"tipo": "exhibidora_caliente", "funcionando": True},
            "temperatura": {"valor_celsius": 52, "medida": True},
            "alimento":    {"tipo": "cocido_listo", "estado_organo": "normal"}
        },
        "nivel_riesgo_esperado": "ALTO",
        "reglas_esperadas": ["R02"],
        "aspecto_validado": "Módulo cadena de frío: R02 detecta zona de peligro en caliente. El funcionamiento del equipo evita R03."
    },
    {
        # Caso 6: CASO LÍMITE CRÍTICO
        # Temperatura correcta (4°C), vencimiento vigente, pero olor anormal
        # R08 actúa sobre el estado organoléptico ignorando los datos numéricos correctos
        # Este caso verifica que el motor no es "engañado" por datos numéricos favorables
        # cuando hay una señal organoléptica negativa que es indicador directo de deterioro
        "id": 6,
        "nombre": "CASO LÍMITE — Olor anormal con temperatura y fecha correctas",
        "descripcion": (
            "Valida que R08 se active por olor anormal aunque la temperatura sea 4°C (correcta) "
            "y el vencimiento esté vigente. Los datos numéricos NO compensan una señal organoléptica "
            "negativa. Este es el caso más importante para demostrar la robustez del sistema."
        ),
        "hechos": {
            "alimento":    {
                "tipo": "cocido_listo",
                "vencimiento_vigente": True,
                "estado_organo": "olor_anormal",
                "es_perecedero": True
            },
            "temperatura": {"valor_celsius": 4, "medida": True}
        },
        "nivel_riesgo_esperado": "CRÍTICO",
        "reglas_esperadas": ["R08"],
        "aspecto_validado": (
            "CASO LÍMITE: R08 actúa sobre estado_organo='olor_anormal' independientemente "
            "de temperatura=4°C y vencimiento vigente. La señal organoléptica tiene prioridad absoluta."
        )
    }
]


# -----------------------------------------------------------------------
# Lógica de ejecución de tests
# -----------------------------------------------------------------------

def ejecutar_tests():
    """
    Ejecuta los 6 casos de prueba y reporta PASS/FAIL para cada uno.

    Para cada caso imprime:
      - Los hechos ingresados
      - Las reglas activadas (ID + nombre)
      - El nivel de riesgo obtenido
      - Si coincide con el esperado (PASS/FAIL)
      - La explicación generada

    Returns:
        tuple: (pasados, fallados) — conteo de resultados
    """
    # Inicializar el motor con la ruta correcta relativa a este archivo
    ruta_knowledge = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'knowledge')
    motor = InferenceEngine(ruta_conocimiento=ruta_knowledge)

    pasados = 0
    fallados = 0

    print(f"\n{BOLD}{SEP}")
    print("  SEHSA — SUITE DE TESTS DEL MOTOR DE INFERENCIA")
    print(f"  {len(CASOS_PRUEBA)} casos de prueba")
    print(f"{SEP}{RESET}\n")

    for caso in CASOS_PRUEBA:
        print(f"{BOLD}Caso {caso['id']}: {caso['nombre']}{RESET}")
        print(f"{CYAN}{caso['descripcion']}{RESET}")
        print(f"Valida: {caso['aspecto_validado']}")
        print(SEP_CASO)

        # ---- Mostrar hechos ingresados ----
        print(f"{BOLD}Hechos ingresados:{RESET}")
        for obj, attrs in caso['hechos'].items():
            for attr, val in attrs.items():
                print(f"  {obj}.{attr} = {val}")

        # ---- Ejecutar el motor ----
        resultado = motor.inferir(caso['hechos'], perfil='profesional')

        # ---- Mostrar reglas activadas ----
        reglas_ids_obtenidas = [r['id'] for r in resultado['reglas_activadas']]
        print(f"\n{BOLD}Reglas activadas:{RESET}")
        if resultado['reglas_activadas']:
            for regla in resultado['reglas_activadas']:
                nivel = regla.get('nivel_riesgo', '?')
                print(f"  [{regla['id']}] {regla['nombre']}  =>  {nivel}")
        else:
            print("  (Ninguna regla se activó)")

        # ---- Nivel de riesgo obtenido ----
        nivel_obtenido = resultado['nivel_riesgo_final']
        nivel_esperado = caso['nivel_riesgo_esperado']
        reglas_esperadas = caso['reglas_esperadas']

        print(f"\n{BOLD}Nivel de riesgo:{RESET}")
        print(f"  Esperado : {nivel_esperado}")
        print(f"  Obtenido : {nivel_obtenido}")

        # ---- Verificar reglas esperadas ----
        reglas_presentes = all(r in reglas_ids_obtenidas for r in reglas_esperadas)
        print(f"\n{BOLD}Reglas esperadas:{RESET}")
        for r in reglas_esperadas:
            ok = r in reglas_ids_obtenidas
            simbolo = "✅" if ok else "❌"
            print(f"  {simbolo} {r}")

        # ---- PASS / FAIL ----
        nivel_ok = (nivel_obtenido == nivel_esperado)
        caso_ok  = nivel_ok and reglas_presentes

        if caso_ok:
            pasados += 1
            print(f"\n{formato_pass()} Caso {caso['id']}: {caso['nombre']}")
        else:
            fallados += 1
            print(f"\n{formato_fail()} Caso {caso['id']}: {caso['nombre']}")
            if not nivel_ok:
                print(f"  ⚠  Nivel de riesgo: esperado '{nivel_esperado}', obtenido '{nivel_obtenido}'")
            if not reglas_presentes:
                faltantes = [r for r in reglas_esperadas if r not in reglas_ids_obtenidas]
                print(f"  ⚠  Reglas faltantes: {faltantes}")

        # ---- Explicación generada (perfil profesional) ----
        print(f"\n{BOLD}Diagnóstico:{RESET}")
        print(f"  {resultado['diagnostico']}")

        if resultado['advertencias']:
            print(f"\n{BOLD}Advertencias:{RESET}")
            for adv in resultado['advertencias']:
                print(f"  ⚠  {adv}")

        # Generar explicación completa del ExplanationSystem
        exp = ExplanationSystem(resultado, caso['hechos'], 'profesional')
        reporte = exp.generar_reporte_dict()
        justif = reporte.get('justificacion', '')
        if justif:
            print(f"\n{BOLD}Justificación:{RESET}")
            print(f"  {justif}")

        print(f"\n{SEP}\n")

    # ---- Resumen final ----
    print(f"{BOLD}{'='*40}")
    print(f"  RESULTADOS FINALES")
    print(f"{'='*40}{RESET}")
    print(f"  Pasados : {VERDE}{pasados}/{len(CASOS_PRUEBA)}{RESET}")
    print(f"  Fallados: {ROJO if fallados > 0 else ''}{fallados}/{len(CASOS_PRUEBA)}{RESET}")

    if fallados == 0:
        print(f"\n  {VERDE}{BOLD}✅ Todos los casos pasaron correctamente.{RESET}")
    else:
        print(f"\n  {ROJO}{BOLD}❌ {fallados} caso(s) fallaron. Revisar el motor o la base de conocimiento.{RESET}")

    print()
    return pasados, fallados


def ejecutar_caso_individual(caso_id: int):
    """
    Ejecuta un único caso de prueba identificado por su ID.

    Útil para debugging de una regla específica.

    Args:
        caso_id (int): ID del caso de prueba (1-6).
    """
    caso = next((c for c in CASOS_PRUEBA if c['id'] == caso_id), None)
    if not caso:
        print(f"Caso {caso_id} no encontrado. IDs disponibles: 1-{len(CASOS_PRUEBA)}")
        return

    ruta_knowledge = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'knowledge')
    motor = InferenceEngine(ruta_conocimiento=ruta_knowledge)

    # Activar modo debug para ver el ciclo paso a paso
    import engine as engine_module
    engine_module.DEBUG = True
    motor_debug = InferenceEngine(ruta_conocimiento=ruta_knowledge)

    print(f"\n{BOLD}Ejecutando Caso {caso_id} en modo DEBUG:{RESET}")
    resultado = motor_debug.inferir(caso['hechos'], perfil='profesional')
    print(f"\nNivel de riesgo obtenido: {resultado['nivel_riesgo_final']}")


# -----------------------------------------------------------------------
# Punto de entrada del script
# -----------------------------------------------------------------------

if __name__ == '__main__':
    # Si se pasa un número como argumento, ejecutar solo ese caso
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        ejecutar_caso_individual(int(sys.argv[1]))
    else:
        # Sin argumentos: ejecutar todos los casos
        pasados, fallados = ejecutar_tests()
        # Salir con código 1 si algún test falló (útil para CI)
        sys.exit(1 if fallados > 0 else 0)
