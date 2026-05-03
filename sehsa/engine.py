"""
engine.py — Motor de Inferencia del Sistema Experto SEHSA
==========================================================
Componente: Motor de Inferencia (Inference Engine)
Rol en la arquitectura:
  - Carga la base de conocimiento desde los archivos JSON de knowledge/.
  - Utiliza WorkingMemory para gestionar el estado de los hechos del caso.
  - Ejecuta el ciclo Recognize-Act (encadenamiento hacia adelante).
  - Devuelve el diagnóstico, las reglas activadas y el nivel de riesgo final.
  - Es invocado por app.py en el endpoint /consulta.

Algoritmo central:
  El encadenamiento hacia adelante (forward chaining) parte de los hechos
  conocidos y aplica reglas de la forma SI condiciones ENTONCES conclusion
  hasta que no haya más reglas aplicables (punto fijo del sistema).
"""

import json
import os
from working_memory import WorkingMemory

# Activar DEBUG = True para ver cada paso del ciclo en la consola
DEBUG = False

# Orden numérico de los niveles de riesgo — se usa para calcular el máximo
NIVEL_RIESGO_ORDEN = {
    'BAJO': 1,
    'MEDIO': 2,
    'ALTO': 3,
    'CRÍTICO': 4
}


class InferenceEngine:
    """
    Motor de inferencia del sistema experto SEHSA.

    Implementa el algoritmo de encadenamiento hacia adelante (forward chaining)
    sobre reglas de producción del tipo SI <condiciones> ENTONCES <conclusión>.

    Ciclo Recognize-Act (Agenda):
        1. Recognize  — identificar las reglas con todas sus condiciones satisfechas.
        2. Conflict   — ordenar las candidatas por prioridad descendente.
        3. Act        — ejecutar la regla ganadora y agregar su conclusión a la memoria.
        4. Repetir    — hasta que no haya candidatas (punto fijo).

    Módulos de conocimiento (orden de evaluación obligatorio):
        1. incertidumbre  — siempre primero; puede detener la inferencia.
        2. cadena_frio    — temperatura, equipos, recepción.
        3. contaminacion  — higiene, manipulación, cuerpos extraños.
        4. epp            — seguridad laboral, equipos de protección.
        5. plagas         — control de vectores y roedores.
        6. documentacion  — registros, rotulación, trazabilidad.

    Métodos principales:
        cargar_conocimiento()          — carga los JSON de knowledge/.
        inferir(hechos, perfil)        — ejecuta el motor y devuelve el diagnóstico.
    """

    # Orden de evaluación de módulos — incertidumbre SIEMPRE primero
    MODULOS_ORDEN = [
        'incertidumbre',
        'cadena_frio',
        'contaminacion',
        'epp',
        'plagas',
        'documentacion'
    ]

    ARCHIVOS_REGLAS = {
        'incertidumbre': 'rules_incertidumbre.json',
        'cadena_frio':   'rules_cadena_frio.json',
        'contaminacion': 'rules_contaminacion.json',
        'epp':           'rules_epp.json',
        'plagas':        'rules_plagas.json',
        'documentacion': 'rules_documentacion.json'
    }

    def __init__(self, ruta_conocimiento: str = None):
        """
        Inicializa el motor de inferencia y carga la base de conocimiento.

        Args:
            ruta_conocimiento (str): Ruta a la carpeta knowledge/.
                                     Si es None, usa 'knowledge/' relativo al archivo.
        """
        if ruta_conocimiento is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ruta_conocimiento = os.path.join(base_dir, 'knowledge')

        self.ruta_conocimiento = ruta_conocimiento
        self.reglas: dict = {}       # {modulo: [lista de reglas]}
        self.todas_las_reglas: list = []  # Lista plana de todas las reglas cargadas

        self.cargar_conocimiento()

    # ------------------------------------------------------------------
    # Carga de la base de conocimiento
    # ------------------------------------------------------------------

    def cargar_conocimiento(self):
        """
        Carga todas las reglas desde los archivos JSON de la carpeta knowledge/.

        Las reglas se cargan en el orden definido por MODULOS_ORDEN para garantizar
        que incertidumbre siempre se evalúe primero en el ciclo principal.

        Raises:
            FileNotFoundError: Si algún archivo JSON de reglas no se encuentra.
            json.JSONDecodeError: Si algún archivo JSON tiene formato inválido.
        """
        self.reglas = {}
        self.todas_las_reglas = []

        for modulo in self.MODULOS_ORDEN:
            archivo = self.ARCHIVOS_REGLAS[modulo]
            ruta_archivo = os.path.join(self.ruta_conocimiento, archivo)

            if not os.path.exists(ruta_archivo):
                if DEBUG:
                    print(f"[DEBUG] Archivo no encontrado: {ruta_archivo}")
                self.reglas[modulo] = []
                continue

            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            # Cada archivo JSON contiene la clave "reglas" con la lista de objetos
            reglas_modulo = datos.get('reglas', [])
            self.reglas[modulo] = reglas_modulo
            self.todas_las_reglas.extend(reglas_modulo)

            if DEBUG:
                print(f"[DEBUG] Módulo '{modulo}': {len(reglas_modulo)} reglas cargadas.")

        if DEBUG:
            print(f"[DEBUG] Total reglas cargadas: {len(self.todas_las_reglas)}")

    # ------------------------------------------------------------------
    # Método principal: inferir
    # ------------------------------------------------------------------

    def inferir(self, hechos: dict, perfil: str = 'supervisor') -> dict:
        """
        Ejecuta el motor de inferencia sobre un conjunto de hechos del caso.

        Pasos del algoritmo:
            1. Cargar hechos del usuario en la memoria de trabajo.
            2. Pre-procesar hechos derivados simples (envase_comprometido, etc.).
            3. Evaluar el módulo de incertidumbre primero (puede hacer STOP).
            4. Ciclo Recognize-Act sobre los módulos de dominio.
            5. Consolidar nivel de riesgo final (máximo encontrado).
            6. Retornar diagnóstico completo.

        Args:
            hechos (dict): Hechos del caso en formato {objeto: {atributo: valor}}.
            perfil (str):  Perfil del usuario ('operario', 'supervisor',
                           'profesional', 'gerente'). Afecta el detalle del reporte.

        Returns:
            dict con las claves:
                nivel_riesgo_final  (str):  'CRÍTICO' | 'ALTO' | 'MEDIO' | 'BAJO'
                reglas_activadas    (list): Reglas ejecutadas con sus condiciones cumplidas.
                diagnostico         (str):  Texto del diagnóstico en lenguaje natural.
                advertencias        (list): Advertencias de incertidumbre.
                derivacion_urgente  (bool): True si hay sospecha ETA (R21/RI-04).
                datos_faltantes     (list): Campos opcionales no proporcionados.
                hechos_evaluados    (dict): Estado final de la memoria de trabajo.

        Ejemplo:
            engine = InferenceEngine()
            resultado = engine.inferir({
                'temperatura': {'valor_celsius': 14, 'medida': True},
                'alimento':    {'tipo': 'carne_cruda', 'es_perecedero': True},
                'equipo':      {'tipo': 'heladera', 'funcionando': False},
                'exposicion':  {'tiempo_conocido': False}
            })
        """
        # -----------------------------------------------------------
        # Paso 1: Inicializar la memoria de trabajo con los hechos del usuario
        # -----------------------------------------------------------
        wm = WorkingMemory()
        wm.cargar_desde_dict(hechos)

        # -----------------------------------------------------------
        # Paso 2: Pre-procesar hechos derivados antes del ciclo principal
        # Esto resuelve condiciones OR que no se pueden expresar en el JSON
        # -----------------------------------------------------------
        self._preprocesar_hechos(wm)

        # -----------------------------------------------------------
        # Estado de la sesión de inferencia
        # -----------------------------------------------------------
        reglas_activadas = []
        reglas_ejecutadas_ids = set()  # Evita re-activar reglas (ciclos infinitos)
        advertencias = []
        derivacion_urgente = False
        datos_faltantes = []
        nivel_riesgo_maximo = 'BAJO'

        if DEBUG:
            print("\n" + "=" * 65)
            print("INICIO DEL CICLO DE INFERENCIA — SEHSA")
            print("=" * 65)
            print(f"Hechos iniciales:\n{json.dumps(wm.como_dict(), indent=2, ensure_ascii=False, default=str)}")

        # -----------------------------------------------------------
        # Paso 3: Evaluar PRIMERO el módulo de incertidumbre (RI-01 a RI-05)
        # Puede modificar la memoria o detener la inferencia completamente
        # -----------------------------------------------------------
        resultado_inc = self._evaluar_modulo_incertidumbre(
            wm, reglas_activadas, reglas_ejecutadas_ids, advertencias
        )

        # Paso 3a: RI-04 activada — sospecha ETA — STOP TOTAL
        if resultado_inc.get('stop_eta'):
            derivacion_urgente = True
            if DEBUG:
                print("[DEBUG] RI-04 activada → DERIVACIÓN URGENTE. Motor detenido.")
            return self._construir_resultado_eta(reglas_activadas, wm)

        # Paso 3b: RI-03 activada — temperatura no medida, estado normal → pedir dato
        if resultado_inc.get('solicitar_temperatura'):
            datos_faltantes.append('temperatura.valor_celsius')
            advertencias.append(
                "DATO FALTANTE: No es posible completar el diagnóstico sin la "
                "medición de temperatura. Mida la temperatura con un termómetro "
                "calibrado y reingrese el caso."
            )
            if DEBUG:
                print("[DEBUG] RI-03 activada → se requiere medición de temperatura.")

        # -----------------------------------------------------------
        # Paso 4: Ciclo Recognize-Act principal
        # Continúa hasta alcanzar el punto fijo (no hay más candidatas)
        # -----------------------------------------------------------
        ciclo = 0
        while True:
            ciclo += 1
            if DEBUG:
                print(f"\n--- Ciclo Recognize-Act #{ciclo} ---")

            # Paso 4a: RECOGNIZE — encontrar reglas candidatas
            candidatas = self._encontrar_reglas_candidatas(wm, reglas_ejecutadas_ids)

            if DEBUG:
                print(f"[DEBUG] Candidatas: {[r['id'] for r in candidatas]}")

            # Si no hay más candidatas, el ciclo llega al punto fijo
            if not candidatas:
                if DEBUG:
                    print("[DEBUG] Sin más candidatas. Fin del ciclo Recognize-Act.")
                break

            # Paso 4b: CONFLICT RESOLUTION — ordenar por prioridad descendente
            # La regla de mayor prioridad gana el conflicto de activación
            candidatas_ordenadas = sorted(
                candidatas,
                key=lambda r: r.get('prioridad', 0),
                reverse=True
            )

            # Paso 4c: ACT — activar la regla ganadora
            regla_ganadora = candidatas_ordenadas[0]

            if DEBUG:
                print(f"[DEBUG] Regla ganadora: {regla_ganadora['id']} "
                      f"(prioridad {regla_ganadora.get('prioridad')})")
                descartadas = [r['id'] for r in candidatas_ordenadas[1:]]
                if descartadas:
                    print(f"[DEBUG] Descartadas por menor prioridad: {descartadas}")

            # Marcar como ejecutada para no volver a activarla
            reglas_ejecutadas_ids.add(regla_ganadora['id'])

            # Aplicar la conclusión: agregar hechos derivados a la memoria
            self._aplicar_conclusion(wm, regla_ganadora)

            # Registrar las condiciones que se cumplieron (para la explicación)
            condiciones_cumplidas = self._obtener_condiciones_cumplidas(wm, regla_ganadora)

            reglas_activadas.append({
                'id':                   regla_ganadora['id'],
                'nombre':               regla_ganadora['nombre'],
                'modulo':               regla_ganadora.get('modulo', ''),
                'condiciones_cumplidas': condiciones_cumplidas,
                'acciones':             regla_ganadora.get('acciones', []),
                'normativa':            regla_ganadora.get('normativa', []),
                'explicacion':          regla_ganadora.get('explicacion', ''),
                'nivel_riesgo':         regla_ganadora.get('nivel_riesgo', 'BAJO'),
                'origen':               regla_ganadora.get('origen', 'EXTRAIDA')
            })

            # Actualizar el nivel de riesgo máximo acumulado en la sesión
            nivel_regla = regla_ganadora.get('nivel_riesgo', 'BAJO')
            if NIVEL_RIESGO_ORDEN.get(nivel_regla, 0) > NIVEL_RIESGO_ORDEN.get(nivel_riesgo_maximo, 0):
                nivel_riesgo_maximo = nivel_regla
                if DEBUG:
                    print(f"[DEBUG] Nuevo nivel de riesgo máximo: {nivel_riesgo_maximo}")

        # -----------------------------------------------------------
        # Paso 5: Verificar datos opcionales faltantes (RI-05)
        # -----------------------------------------------------------
        datos_faltantes.extend(self._verificar_datos_opcionales(wm))

        # -----------------------------------------------------------
        # Paso 6: Consolidar y retornar el resultado final
        # -----------------------------------------------------------
        diagnostico = self._generar_diagnostico(reglas_activadas, nivel_riesgo_maximo)

        if DEBUG:
            print(f"\n[DEBUG] Inferencia completada. Nivel: {nivel_riesgo_maximo}")
            print(f"[DEBUG] Reglas activadas: {[r['id'] for r in reglas_activadas]}")

        return {
            'nivel_riesgo_final': nivel_riesgo_maximo,
            'reglas_activadas':   reglas_activadas,
            'diagnostico':        diagnostico,
            'advertencias':       advertencias,
            'derivacion_urgente': derivacion_urgente,
            'datos_faltantes':    datos_faltantes,
            'hechos_evaluados':   wm.como_dict()
        }

    # ------------------------------------------------------------------
    # Pre-procesamiento de hechos derivados simples
    # ------------------------------------------------------------------

    def _preprocesar_hechos(self, wm: WorkingMemory):
        """
        Deriva hechos compuestos antes del ciclo principal para resolver condiciones OR.

        El JSON de reglas solo soporta AND entre condiciones. Para condiciones OR
        (como en R17: envase_hermetico=False OR envase_dañado=True), se calculan
        hechos intermedios aquí antes de que empiece la inferencia.

        Args:
            wm (WorkingMemory): Memoria de trabajo a modificar.
        """
        # R17: Envase comprometido si NO es hermético O está dañado
        hermetico = wm.obtener('alimento', 'envase_hermetico')
        danado = wm.obtener('alimento', 'envase_dañado')
        if hermetico is False or danado is True:
            wm.agregar('alimento', 'envase_comprometido', True, derivado=True)
        elif hermetico is True and danado is False:
            wm.agregar('alimento', 'envase_comprometido', False, derivado=True)

        # R01: Exposición prolongada cuando las horas conocidas superan el límite
        horas = wm.obtener('exposicion', 'horas')
        if horas is not None and float(horas) > 2:
            wm.agregar('exposicion', 'riesgo_prolongado', True, derivado=True)

        if DEBUG:
            print(f"[DEBUG] Pre-procesamiento completado. "
                  f"envase_comprometido={wm.obtener('alimento','envase_comprometido')}, "
                  f"riesgo_prolongado={wm.obtener('exposicion','riesgo_prolongado')}")

    # ------------------------------------------------------------------
    # Evaluación del módulo de incertidumbre
    # ------------------------------------------------------------------

    def _evaluar_modulo_incertidumbre(self, wm, reglas_activadas, ejecutadas, advertencias) -> dict:
        """
        Evalúa las reglas RI-01 a RI-05 antes que cualquier otro módulo.

        Este módulo tiene prioridad absoluta. Sus reglas pueden:
          - Derivar hechos que habilitan reglas de dominio (RI-01 → R01, R03).
          - Señalar que falta un dato crítico (RI-03 → pedir temperatura).
          - Detener TODA la inferencia (RI-04 → sospecha ETA).

        Args:
            wm               (WorkingMemory): Memoria de trabajo.
            reglas_activadas (list):          Acumulador de reglas activadas.
            ejecutadas       (set):           IDs de reglas ya ejecutadas.
            advertencias     (list):          Acumulador de advertencias.

        Returns:
            dict: {'stop_eta': bool, 'solicitar_temperatura': bool}
        """
        resultado = {'stop_eta': False, 'solicitar_temperatura': False}
        reglas_inc = self.reglas.get('incertidumbre', [])

        # Ordenar por prioridad descendente (RI-04 tiene prioridad 10 → se evalúa primero)
        ordenadas = sorted(reglas_inc, key=lambda r: r.get('prioridad', 0), reverse=True)

        for regla in ordenadas:
            if regla['id'] in ejecutadas:
                continue

            if self._condiciones_satisfechas(wm, regla):
                ejecutadas.add(regla['id'])
                self._aplicar_conclusion(wm, regla)
                condiciones_cumplidas = self._obtener_condiciones_cumplidas(wm, regla)

                reglas_activadas.append({
                    'id':                    regla['id'],
                    'nombre':                regla['nombre'],
                    'modulo':                'incertidumbre',
                    'condiciones_cumplidas': condiciones_cumplidas,
                    'acciones':              regla.get('acciones', []),
                    'normativa':             regla.get('normativa', []),
                    'explicacion':           regla.get('explicacion', ''),
                    'nivel_riesgo':          regla.get('nivel_riesgo', 'BAJO'),
                    'origen':                'INCERTIDUMBRE'
                })

                if DEBUG:
                    print(f"[DEBUG] Módulo incertidumbre: activada {regla['id']} — {regla['nombre']}")

                # RI-04: Sospecha ETA → STOP total e inmediato
                if regla['id'] == 'RI-04':
                    resultado['stop_eta'] = True
                    return resultado

                # RI-03: Temperatura no medida con estado normal → pedir dato
                if regla['id'] == 'RI-03':
                    resultado['solicitar_temperatura'] = True

                # Registrar advertencia de incertidumbre para el reporte
                explicacion = regla.get('explicacion', '')
                if explicacion:
                    advertencias.append(f"[{regla['id']}] {explicacion}")

        return resultado

    # ------------------------------------------------------------------
    # Ciclo Recognize-Act: búsqueda de candidatas
    # ------------------------------------------------------------------

    def _encontrar_reglas_candidatas(self, wm: WorkingMemory, ejecutadas: set) -> list:
        """
        Encuentra todas las reglas de dominio con condiciones satisfechas aún no ejecutadas.

        Las reglas del módulo de incertidumbre se excluyen aquí porque ya se
        evaluaron en _evaluar_modulo_incertidumbre.

        Args:
            wm         (WorkingMemory): Estado actual de la memoria de trabajo.
            ejecutadas (set):           IDs de reglas que ya se ejecutaron.

        Returns:
            list: Lista de objetos de regla candidatos para activación.
        """
        candidatas = []
        for regla in self.todas_las_reglas:
            # Saltar reglas ya ejecutadas (evitar ciclos)
            if regla['id'] in ejecutadas:
                continue
            # Saltar módulo de incertidumbre (ya se evaluó aparte)
            if regla.get('modulo') == 'incertidumbre':
                continue
            # Verificar si TODAS las condiciones se cumplen (AND implícito)
            if self._condiciones_satisfechas(wm, regla):
                candidatas.append(regla)
        return candidatas

    def _condiciones_satisfechas(self, wm: WorkingMemory, regla: dict) -> bool:
        """
        Verifica si TODAS las condiciones de una regla se cumplen en la memoria.

        Las condiciones dentro de una regla tienen relación AND implícita:
        todas deben ser verdaderas para que la regla sea candidata.

        Args:
            wm    (WorkingMemory): Estado actual de la memoria de trabajo.
            regla (dict):          Objeto de regla con su lista 'condiciones'.

        Returns:
            bool: True si todas las condiciones se cumplen.
        """
        condiciones = regla.get('condiciones', [])
        # Sin condiciones → la regla aplica siempre (caso excepcional)
        if not condiciones:
            return True

        for condicion in condiciones:
            if not wm.evaluar_condicion(condicion):
                if DEBUG:
                    val = wm.obtener(condicion.get('objeto'), condicion.get('atributo'))
                    print(f"  [DEBUG] Condición NO cumplida en {regla['id']}: "
                          f"{condicion['objeto']}.{condicion['atributo']} "
                          f"{condicion['operador']} {condicion['valor']} "
                          f"(actual: {val})")
                return False
        return True

    # ------------------------------------------------------------------
    # Aplicar conclusión y registrar condiciones cumplidas
    # ------------------------------------------------------------------

    def _aplicar_conclusion(self, wm: WorkingMemory, regla: dict):
        """
        Aplica la conclusión de una regla activada escribiendo hechos derivados en la memoria.

        Los hechos derivados pueden activar nuevas reglas en el siguiente ciclo,
        lo que es el mecanismo central del encadenamiento hacia adelante.

        Args:
            wm    (WorkingMemory): Memoria de trabajo a modificar.
            regla (dict):          Regla activada con su campo 'conclusion'.
        """
        conclusion = regla.get('conclusion', {})
        if isinstance(conclusion, dict):
            for objeto, atributos in conclusion.items():
                if isinstance(atributos, dict):
                    for atributo, valor in atributos.items():
                        wm.agregar(objeto, atributo, valor, derivado=True)

    def _obtener_condiciones_cumplidas(self, wm: WorkingMemory, regla: dict) -> list:
        """
        Genera la lista de condiciones que se cumplieron, incluyendo el valor real del hecho.

        Esta información se usa en la explicación para mostrar exactamente por qué
        se activó cada regla con los valores concretos del caso.

        Args:
            wm    (WorkingMemory): Memoria de trabajo con los hechos actuales.
            regla (dict):          Regla activada.

        Returns:
            list: Lista de dicts con objeto, atributo, operador, valor_esperado, valor_real.
        """
        cumplidas = []
        for cond in regla.get('condiciones', []):
            valor_real = wm.obtener(cond.get('objeto'), cond.get('atributo'))
            cumplidas.append({
                'objeto':         cond.get('objeto'),
                'atributo':       cond.get('atributo'),
                'operador':       cond.get('operador'),
                'valor_esperado': cond.get('valor'),
                'valor_real':     valor_real,
                'descripcion':    cond.get('descripcion', '')
            })
        return cumplidas

    # ------------------------------------------------------------------
    # Verificación de datos opcionales (RI-05)
    # ------------------------------------------------------------------

    def _verificar_datos_opcionales(self, wm: WorkingMemory) -> list:
        """
        Verifica qué datos opcionales (lote, cantidad, historial) no fueron proporcionados.

        Según RI-05, la ausencia de datos opcionales no detiene el diagnóstico,
        pero se agrega una advertencia de completitud para el reporte.

        Args:
            wm (WorkingMemory): Memoria de trabajo al final del ciclo.

        Returns:
            list: Nombres de campos faltantes en formato 'objeto.atributo'.
        """
        datos_faltantes = []
        opcionales = [
            ('lote', 'numero'),
            ('lote', 'cantidad'),
            ('historial', 'incidentes_previos'),
        ]
        for objeto, atributo in opcionales:
            if not wm.existe(objeto, atributo):
                datos_faltantes.append(f"{objeto}.{atributo}")
        return datos_faltantes

    # ------------------------------------------------------------------
    # Generación del texto de diagnóstico
    # ------------------------------------------------------------------

    def _generar_diagnostico(self, reglas_activadas: list, nivel_riesgo: str) -> str:
        """
        Genera el texto del diagnóstico basado en las reglas activadas y el nivel de riesgo.

        Args:
            reglas_activadas (list): Reglas que se activaron durante la inferencia.
            nivel_riesgo     (str):  Nivel de riesgo final consolidado.

        Returns:
            str: Texto del diagnóstico en lenguaje natural.
        """
        if not reglas_activadas:
            return (
                "No se detectaron situaciones de riesgo con los datos proporcionados. "
                "El sistema recomienda continuar aplicando las Buenas Prácticas de "
                "Manufactura (BPM) y mantener el monitoreo habitual."
            )

        nombres = [r['nombre'] for r in reglas_activadas]
        n = len(reglas_activadas)
        lista_breve = ', '.join(nombres[:3]) + ('...' if n > 3 else '')

        plantillas = {
            'CRÍTICO': (
                f"Se detectaron {n} situación(es) de RIESGO CRÍTICO que requieren "
                f"acción inmediata: {lista_breve}. "
                "Es obligatorio actuar de inmediato para proteger la inocuidad "
                "alimentaria y la salud de los consumidores. No continuar operaciones "
                "hasta resolver las situaciones identificadas."
            ),
            'ALTO': (
                f"Se detectaron {n} situación(es) de RIESGO ALTO: {lista_breve}. "
                "Se requieren acciones correctivas urgentes antes de continuar "
                "las operaciones normales del establecimiento."
            ),
            'MEDIO': (
                f"Se detectaron {n} situación(es) de RIESGO MEDIO: {lista_breve}. "
                "Implementar las medidas correctivas indicadas en el corto plazo "
                "para prevenir la escalada del riesgo."
            ),
            'BAJO': (
                f"Se detectó {n} situación(es) de RIESGO BAJO: {lista_breve}. "
                "Monitorear y aplicar las medidas preventivas recomendadas."
            )
        }
        return plantillas.get(nivel_riesgo, "Diagnóstico no disponible.")

    # ------------------------------------------------------------------
    # Resultado especial para derivación urgente (ETA)
    # ------------------------------------------------------------------

    def _construir_resultado_eta(self, reglas_activadas: list, wm: WorkingMemory) -> dict:
        """
        Construye el resultado de STOP cuando se detecta sospecha de ETA.

        Este resultado especial indica que el sistema no puede emitir diagnóstico
        y debe derivar inmediatamente a médico y autoridad sanitaria.
        Corresponde a R21 / RI-04 del sistema.

        Args:
            reglas_activadas (list): Reglas activadas hasta el momento del STOP.
            wm               (WorkingMemory): Memoria de trabajo.

        Returns:
            dict: Resultado con derivacion_urgente=True y mensaje de derivación.
        """
        return {
            'nivel_riesgo_final': 'CRÍTICO',
            'reglas_activadas':   reglas_activadas,
            'diagnostico': (
                "CASO FUERA DEL ALCANCE DEL SISTEMA EXPERTO. "
                "Se detecta sospecha de Enfermedad Transmitida por Alimentos (ETA). "
                "El sistema NO emite diagnóstico para este caso. "
                "DERIVE INMEDIATAMENTE a médico y autoridad sanitaria competente."
            ),
            'advertencias': [
                "SOSPECHA DE ETA: Intervención médica y sanitaria URGENTE requerida.",
                "No consumir ningún alimento involucrado en el caso.",
                "Conservar muestras de alimentos para análisis oficial.",
                "Contactar al médico y a la autoridad sanitaria local de inmediato.",
                "Este sistema experto NO está diseñado para diagnosticar enfermedades en personas."
            ],
            'derivacion_urgente': True,
            'datos_faltantes':    [],
            'hechos_evaluados':   wm.como_dict()
        }
