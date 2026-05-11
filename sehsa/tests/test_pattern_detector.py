"""
test_pattern_detector.py — Tests del Detector de Patrones SEHSA
================================================================
Valida los seis comportamientos clave del PatternDetector:
  TC-P01: Historial vacío → sin patrones
  TC-P02: 3 casos con misma regla en ventana → patrón detectado
  TC-P03: 3 casos con misma regla fuera de ventana → sin patrón
  TC-P04: Regla tipo "informativo" repetida 5 veces → sin recomendación
  TC-P05: Múltiples patrones activos → orden correcto (riesgo > frecuencia > recencia)
  TC-P06: Patrón estructural vs proceso → recomendaciones distintas

Ejecutar:
    cd sehsa/
    python tests/test_pattern_detector.py
"""

import sys
import os
import json
from datetime import datetime, timedelta, timezone

# Agregar el directorio sehsa/ al path para importar los módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pattern_detector import PatternDetector


# -----------------------------------------------------------------------
# Helpers para construir historial de prueba
# -----------------------------------------------------------------------

def _caso(regla_ids: list, dias_atras: int, nivel_riesgo: str = 'CRÍTICO') -> dict:
    """Construye un caso de historial de prueba."""
    ts = (datetime.now(timezone.utc) - timedelta(days=dias_atras)).isoformat()
    return {
        'id':          1,
        'timestamp':   ts,
        'reglas_ids':  regla_ids,
        'nivel_riesgo': nivel_riesgo,
        'modulo':      'test',
        'perfil':      'operario',
    }


def _detector_con_mapa(mapa_reglas_override: dict = None) -> PatternDetector:
    """
    Crea un PatternDetector con mapa de reglas inyectado directamente,
    sin depender de los archivos JSON del proyecto.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'config.json')
    knowledge_path = os.path.join(base_dir, 'knowledge')

    detector = PatternDetector(
        ruta_conocimiento=knowledge_path,
        ruta_config=config_path
    )

    if mapa_reglas_override:
        detector.mapa_reglas.update(mapa_reglas_override)

    return detector


# -----------------------------------------------------------------------
# Casos de prueba
# -----------------------------------------------------------------------

def tc_p01_historial_vacio():
    """TC-P01: Historial vacío → sin patrones."""
    detector = _detector_con_mapa()
    resultado = detector.analizar([])

    assert resultado['patrones'] == [], \
        f"TC-P01 FALLÓ: se esperaba lista vacía, se obtuvo {resultado['patrones']}"
    assert resultado['total_casos_analizados'] == 0
    print("TC-P01 OK — historial vacío → sin patrones")


def tc_p02_patron_detectado():
    """TC-P02: 3 casos con misma regla en ventana → patrón detectado."""
    mapa = {
        'R03': {
            'nombre':      'Heladera sin funcionar',
            'nivel_riesgo': 'CRÍTICO',
            'tipo_patron': 'estructural',
            'modulo':      'cadena_frio',
        }
    }
    detector = _detector_con_mapa(mapa)
    historial = [
        _caso(['R03'], dias_atras=5),
        _caso(['R03'], dias_atras=10),
        _caso(['R03'], dias_atras=20),
    ]
    resultado = detector.analizar(historial)

    assert len(resultado['patrones']) == 1, \
        f"TC-P02 FALLÓ: se esperaba 1 patrón, se obtuvo {len(resultado['patrones'])}"
    patron = resultado['patrones'][0]
    assert patron['regla_id'] == 'R03'
    assert patron['frecuencia'] == 3
    assert patron['tipo_patron'] == 'estructural'
    assert 'recomendacion_estructural' in patron
    assert len(patron['recomendacion_estructural']) > 0
    print("TC-P02 OK — 3 casos en ventana → patrón estructural detectado")


def tc_p03_casos_fuera_de_ventana():
    """TC-P03: 3 casos con misma regla fuera de ventana → sin patrón."""
    mapa = {
        'R03': {
            'nombre':      'Heladera sin funcionar',
            'nivel_riesgo': 'CRÍTICO',
            'tipo_patron': 'estructural',
            'modulo':      'cadena_frio',
        }
    }
    detector = _detector_con_mapa(mapa)
    # Casos a 35, 40 y 50 días → fuera de la ventana de 30 días
    historial = [
        _caso(['R03'], dias_atras=35),
        _caso(['R03'], dias_atras=40),
        _caso(['R03'], dias_atras=50),
    ]
    resultado = detector.analizar(historial)

    assert resultado['patrones'] == [], \
        f"TC-P03 FALLÓ: casos fuera de ventana no deben generar patrón, se obtuvo {resultado['patrones']}"
    assert resultado['total_casos_analizados'] == 0
    print("TC-P03 OK — casos fuera de ventana → sin patrón")


def tc_p04_tipo_informativo_sin_recomendacion():
    """TC-P04: Regla tipo 'informativo' repetida 5 veces → sin recomendación."""
    mapa = {
        'RI-04': {
            'nombre':      'Sospecha de ETA',
            'nivel_riesgo': 'CRÍTICO',
            'tipo_patron': 'informativo',
            'modulo':      'incertidumbre',
        }
    }
    detector = _detector_con_mapa(mapa)
    historial = [_caso(['RI-04'], dias_atras=i) for i in range(1, 6)]
    resultado = detector.analizar(historial)

    assert resultado['patrones'] == [], \
        f"TC-P04 FALLÓ: tipo informativo no debe generar patrón, se obtuvo {resultado['patrones']}"
    print("TC-P04 OK — tipo 'informativo' repetido 5 veces → sin recomendación")


def tc_p05_orden_patrones():
    """TC-P05: Múltiples patrones → ordenados por nivel_riesgo desc > frecuencia desc."""
    mapa = {
        'R03': {
            'nombre':      'Heladera sin funcionar',
            'nivel_riesgo': 'CRÍTICO',
            'tipo_patron': 'estructural',
            'modulo':      'cadena_frio',
        },
        'R12': {
            'nombre':      'Sin EPP con químicos',
            'nivel_riesgo': 'ALTO',
            'tipo_patron': 'proceso',
            'modulo':      'epp',
        },
        'R19': {
            'nombre':      'Sin registros de temperatura',
            'nivel_riesgo': 'ALTO',
            'tipo_patron': 'proceso',
            'modulo':      'documentacion',
        },
    }
    detector = _detector_con_mapa(mapa)
    historial = (
        [_caso(['R03'], dias_atras=i) for i in range(1, 4)] +   # R03: 3 veces, CRÍTICO
        [_caso(['R12'], dias_atras=i) for i in range(1, 6)] +   # R12: 5 veces, ALTO
        [_caso(['R19'], dias_atras=i) for i in range(1, 4)]     # R19: 3 veces, ALTO
    )
    resultado = detector.analizar(historial)

    assert len(resultado['patrones']) == 3, \
        f"TC-P05 FALLÓ: se esperaban 3 patrones, se obtuvieron {len(resultado['patrones'])}"

    # R03 (CRÍTICO) debe ir primero, aunque tenga menos frecuencia que R12
    assert resultado['patrones'][0]['regla_id'] == 'R03', \
        f"TC-P05 FALLÓ: primer patrón debe ser R03 (CRÍTICO), fue {resultado['patrones'][0]['regla_id']}"

    # Entre R12 (5 veces) y R19 (3 veces), ambos ALTO → R12 va primero por frecuencia
    assert resultado['patrones'][1]['regla_id'] == 'R12', \
        f"TC-P05 FALLÓ: segundo patrón debe ser R12 (mayor frecuencia), fue {resultado['patrones'][1]['regla_id']}"
    assert resultado['patrones'][2]['regla_id'] == 'R19'

    print("TC-P05 OK — orden correcto: CRÍTICO > ALTO/mayor frecuencia > ALTO/menor frecuencia")


def tc_p06_recomendaciones_distintas_por_tipo():
    """TC-P06: Patrón estructural vs proceso → texto de recomendación distinto."""
    mapa = {
        'R03': {
            'nombre':      'Heladera sin funcionar',
            'nivel_riesgo': 'CRÍTICO',
            'tipo_patron': 'estructural',
            'modulo':      'cadena_frio',
        },
        'R09': {
            'nombre':      'Sin higiene de manos',
            'nivel_riesgo': 'ALTO',
            'tipo_patron': 'proceso',
            'modulo':      'contaminacion',
        },
    }
    detector = _detector_con_mapa(mapa)
    historial = (
        [_caso(['R03'], dias_atras=i) for i in range(1, 4)] +
        [_caso(['R09'], dias_atras=i) for i in range(1, 4)]
    )
    resultado = detector.analizar(historial)

    assert len(resultado['patrones']) == 2
    r03_patron = next(p for p in resultado['patrones'] if p['regla_id'] == 'R03')
    r09_patron = next(p for p in resultado['patrones'] if p['regla_id'] == 'R09')

    assert 'reparación' in r03_patron['recomendacion_estructural'].lower() or \
           'infraestructura' in r03_patron['recomendacion_estructural'].lower(), \
        "TC-P06 FALLÓ: recomendación estructural debe mencionar reparación o infraestructura"

    assert 'capacitación' in r09_patron['recomendacion_estructural'].lower() or \
           'proceso' in r09_patron['recomendacion_estructural'].lower(), \
        "TC-P06 FALLÓ: recomendación de proceso debe mencionar capacitación"

    assert r03_patron['recomendacion_estructural'] != r09_patron['recomendacion_estructural'], \
        "TC-P06 FALLÓ: las recomendaciones de distintos tipos deben ser diferentes"

    assert r03_patron['icono'] == 'gear'
    assert r09_patron['icono'] == 'person'

    print("TC-P06 OK — estructural vs proceso → recomendaciones y íconos distintos")


# -----------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------

if __name__ == '__main__':
    print("=" * 60)
    print("  SEHSA — Tests del Detector de Patrones")
    print("=" * 60)

    tests = [
        tc_p01_historial_vacio,
        tc_p02_patron_detectado,
        tc_p03_casos_fuera_de_ventana,
        tc_p04_tipo_informativo_sin_recomendacion,
        tc_p05_orden_patrones,
        tc_p06_recomendaciones_distintas_por_tipo,
    ]

    ok = 0
    fail = 0
    for test in tests:
        try:
            test()
            ok += 1
        except AssertionError as e:
            print(f"  FALLO: {e}")
            fail += 1
        except Exception as e:
            print(f"  ERROR inesperado en {test.__name__}: {e}")
            fail += 1

    print("=" * 60)
    print(f"  Resultado: {ok} OK / {fail} FALLO(S)")
    print("=" * 60)

    if fail > 0:
        sys.exit(1)
