"""
pattern_detector.py — Detector de Patrones en Historial del Sistema Experto SEHSA
===================================================================================
Componente: Detector de Patrones (Pattern Detector)
Rol en la arquitectura:
  - Analiza el historial de casos guardados buscando reglas que se repiten.
  - Distingue entre patrones estructurales, de proceso e informativos.
  - Genera recomendaciones correctivas sistémicas (no diagnósticos puntuales).
  - Es invocado por app.py en el endpoint GET /analisis_historial.

Tipos de patrón (campo "tipo_patron" en cada regla JSON):
  - "estructural" : falla de equipo o infraestructura → "Evaluar reparación/reemplazo"
  - "proceso"     : error humano o procedimental repetido → "Reforzar capacitación"
  - "informativo" : evento puntual sin patrón sistémico posible → no genera recomendación

Configuración (config.json):
  - n_umbral    : mínimo de ocurrencias para considerar un patrón (default 3)
  - ventana_dias: ventana de tiempo hacia atrás en días (default 30)
"""

import json
import os
from datetime import datetime, timedelta, timezone


NIVEL_RIESGO_ORDEN = {
    'BAJO':    1,
    'MEDIO':   2,
    'ALTO':    3,
    'CRÍTICO': 4,
}

ICONOS_PATRON = {
    'estructural': 'gear',
    'proceso':     'person',
    'informativo': 'info',
}

RECOMENDACIONES_PATRON = {
    'estructural': (
        "Recomendación estructural: evaluá la reparación, reemplazo o adecuación "
        "de la infraestructura o equipo involucrado. La recurrencia indica una falla "
        "sistémica, no un incidente aislado."
    ),
    'proceso': (
        "Recomendación de proceso: reforzá la capacitación del personal en el "
        "procedimiento correspondiente y revisá los controles operativos para "
        "prevenir nuevas ocurrencias."
    ),
}


class PatternDetector:
    """
    Analiza el historial de casos del sistema experto buscando patrones de reglas
    que se repiten dentro de una ventana de tiempo configurable.

    Solo genera recomendaciones para patrones de tipo "estructural" o "proceso".
    Los patrones de tipo "informativo" se cuentan pero no generan recomendación.

    Ordenamiento de resultados: nivel_riesgo (desc) > frecuencia (desc) > recencia (asc).
    """

    def __init__(self, ruta_conocimiento: str = None, ruta_config: str = None):
        """
        Inicializa el detector cargando la configuración y el mapa de reglas.

        Args:
            ruta_conocimiento (str): Ruta a la carpeta knowledge/.
            ruta_config       (str): Ruta al archivo config.json.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))

        if ruta_config is None:
            ruta_config = os.path.join(base_dir, 'config.json')
        if ruta_conocimiento is None:
            ruta_conocimiento = os.path.join(base_dir, 'knowledge')

        self.config = self._cargar_config(ruta_config)
        self.n_umbral    = self.config.get('pattern_detector', {}).get('n_umbral', 3)
        self.ventana_dias = self.config.get('pattern_detector', {}).get('ventana_dias', 30)

        # Mapa {regla_id: {nombre, nivel_riesgo, tipo_patron, modulo}}
        self.mapa_reglas = self._cargar_mapa_reglas(ruta_conocimiento)

    # ------------------------------------------------------------------
    # Método principal
    # ------------------------------------------------------------------

    def analizar(self, historial: list) -> dict:
        """
        Analiza el historial y devuelve los patrones activos con recomendaciones.

        Args:
            historial (list): Lista de casos del historial (crudos del JSON).

        Returns:
            dict con las claves:
              patrones               (list): Patrones activos con recomendaciones.
              total_casos_analizados (int):  Casos dentro de la ventana de tiempo.
              ventana_dias           (int):  Ventana usada en el análisis.
              n_umbral               (int):  Umbral de ocurrencias usado.
        """
        ahora = datetime.now(timezone.utc)
        limite = ahora - timedelta(days=self.ventana_dias)

        # Filtrar casos dentro de la ventana de tiempo
        casos_en_ventana = []
        for caso in historial:
            ts = caso.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(ts)
                # Normalizar a UTC si no tiene zona horaria
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= limite:
                    casos_en_ventana.append((dt, caso))
            except (ValueError, TypeError):
                continue

        # Contar ocurrencias y registrar última aparición por regla
        conteo = {}     # {regla_id: {'frecuencia': int, 'ultima': datetime}}
        for dt, caso in casos_en_ventana:
            for regla_id in caso.get('reglas_ids', []):
                if regla_id not in conteo:
                    conteo[regla_id] = {'frecuencia': 0, 'ultima': dt}
                conteo[regla_id]['frecuencia'] += 1
                if dt > conteo[regla_id]['ultima']:
                    conteo[regla_id]['ultima'] = dt

        # Construir patrones activos
        patrones = []
        for regla_id, datos in conteo.items():
            if datos['frecuencia'] < self.n_umbral:
                continue

            info = self.mapa_reglas.get(regla_id, {})
            tipo_patron = info.get('tipo_patron', 'informativo')

            # Los patrones informativos nunca generan recomendación
            if tipo_patron == 'informativo':
                continue

            nivel_riesgo = info.get('nivel_riesgo', 'BAJO')
            nombre = info.get('nombre', regla_id)
            modulo = info.get('modulo', '')
            ultima_iso = datos['ultima'].isoformat()

            recomendacion = self._generar_recomendacion(
                nombre, tipo_patron, datos['frecuencia']
            )

            patrones.append({
                'regla_id':             regla_id,
                'regla_nombre':         nombre,
                'modulo':               modulo,
                'tipo_patron':          tipo_patron,
                'icono':                ICONOS_PATRON.get(tipo_patron, 'info'),
                'frecuencia':           datos['frecuencia'],
                'ventana_dias':         self.ventana_dias,
                'nivel_riesgo_patron':  nivel_riesgo,
                'ultima_ocurrencia':    ultima_iso,
                'recomendacion_estructural': recomendacion,
            })

        # Ordenar: nivel_riesgo (desc) > frecuencia (desc) > recencia (desc = más reciente primero)
        patrones.sort(key=lambda p: (
            -NIVEL_RIESGO_ORDEN.get(p['nivel_riesgo_patron'], 0),
            -p['frecuencia'],
            p['ultima_ocurrencia']   # ISO string, orden lexicográfico = cronológico
        ), reverse=False)
        # Corrección: para recencia queremos el más reciente primero (mayor timestamp = primero)
        # La clave de sorting ya gestiona desc para nivel y frecuencia.
        # Para ultima_ocurrencia queremos desc también → negamos implícitamente con reverse.
        # Re-sort con clave compuesta correcta:
        patrones.sort(key=lambda p: (
            NIVEL_RIESGO_ORDEN.get(p['nivel_riesgo_patron'], 0),
            p['frecuencia'],
            p['ultima_ocurrencia']
        ), reverse=True)

        return {
            'patrones':               patrones,
            'total_casos_analizados': len(casos_en_ventana),
            'ventana_dias':           self.ventana_dias,
            'n_umbral':               self.n_umbral,
        }

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _generar_recomendacion(self, nombre: str, tipo_patron: str, frecuencia: int) -> str:
        """
        Genera el texto de la recomendación estructural o de proceso.

        Args:
            nombre      (str): Nombre de la regla.
            tipo_patron (str): 'estructural' o 'proceso'.
            frecuencia  (int): Número de ocurrencias detectadas.

        Returns:
            str: Texto de la recomendación.
        """
        base = RECOMENDACIONES_PATRON.get(tipo_patron, '')
        return (
            f"Detectamos {frecuencia} incidentes de '{nombre}' "
            f"en los últimos {self.ventana_dias} días. "
            f"{base}"
        )

    def _cargar_config(self, ruta_config: str) -> dict:
        """
        Carga la configuración desde config.json.

        Returns:
            dict: Configuración, o dict vacío si el archivo no existe.
        """
        if not os.path.exists(ruta_config):
            return {}
        try:
            with open(ruta_config, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _cargar_mapa_reglas(self, ruta_conocimiento: str) -> dict:
        """
        Carga los archivos JSON de knowledge/ y construye el mapa de reglas.

        Returns:
            dict: {regla_id: {nombre, nivel_riesgo, tipo_patron, modulo}}
        """
        archivos = [
            'rules_incertidumbre.json',
            'rules_cadena_frio.json',
            'rules_contaminacion.json',
            'rules_epp.json',
            'rules_plagas.json',
            'rules_documentacion.json',
        ]
        mapa = {}
        for archivo in archivos:
            ruta = os.path.join(ruta_conocimiento, archivo)
            if not os.path.exists(ruta):
                continue
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                for regla in datos.get('reglas', []):
                    rid = regla.get('id')
                    if rid:
                        mapa[rid] = {
                            'nombre':      regla.get('nombre', rid),
                            'nivel_riesgo': regla.get('nivel_riesgo', 'BAJO'),
                            'tipo_patron': regla.get('tipo_patron', 'informativo'),
                            'modulo':      regla.get('modulo', ''),
                        }
            except (json.JSONDecodeError, IOError):
                continue
        return mapa
