"""
working_memory.py — Memoria de Trabajo del Sistema Experto SEHSA
================================================================
Componente: Memoria de Trabajo (Working Memory)
Rol en la arquitectura:
  - Almacena todos los hechos conocidos sobre el caso actual en formato OAV
    (Objeto - Atributo - Valor), tanto los ingresados por el usuario como los
    derivados por el motor durante el ciclo Recognize-Act.
  - Es utilizado por engine.py para leer y escribir hechos durante la inferencia.
  - Es leído por explanation.py para generar el reporte de explicación.
"""


class WorkingMemory:
    """
    Memoria de trabajo del sistema experto SEHSA.

    Implementa el almacén de hechos en formato OAV (Objeto-Atributo-Valor).
    En un sistema experto basado en reglas, la memoria de trabajo contiene
    el estado completo del caso en evaluación:
      - Hechos del usuario: datos que ingresó el operario/supervisor.
      - Hechos derivados: conclusiones que el motor dedujo al activar reglas.

    Responsabilidad:
      Proveer lectura, escritura y evaluación de condiciones sobre los hechos,
      de forma que el motor de inferencia pueda trabajar de manera desacoplada
      de la representación interna.

    Métodos principales:
      agregar(objeto, atributo, valor)  — escribe o actualiza un hecho
      obtener(objeto, atributo)         — lee el valor de un hecho
      existe(objeto, atributo)          — comprueba si el hecho existe
      evaluar_condicion(condicion)      — evalúa una condición JSON contra los hechos
      como_dict()                       — serializa todos los hechos a diccionario
      hechos_iniciales                  — propiedad: solo los hechos del usuario
    """

    def __init__(self):
        """Inicializa la memoria de trabajo con los almacenes internos vacíos."""
        # Almacén principal: {objeto: {atributo: valor}} — contiene TODOS los hechos
        self._hechos: dict = {}
        # Almacén separado solo con los hechos del usuario (para la explicación)
        self._hechos_usuario: dict = {}

    # ------------------------------------------------------------------
    # Escritura de hechos
    # ------------------------------------------------------------------

    def agregar(self, objeto: str, atributo: str, valor, derivado: bool = False):
        """
        Agrega o actualiza un hecho en la memoria de trabajo.

        Si el hecho ya existe, su valor se sobreescribe con el nuevo valor.
        Los hechos ingresados por el usuario (derivado=False) también se guardan
        en _hechos_usuario para que la explicación pueda identificarlos.

        Args:
            objeto   (str):  Entidad a la que pertenece el hecho (ej: 'alimento').
            atributo (str):  Propiedad del objeto (ej: 'es_perecedero').
            valor:           Valor de la propiedad (str, int, float, bool).
            derivado (bool): True si fue deducido por el motor; False si lo ingresó
                             el usuario. Default False.

        Ejemplo:
            wm = WorkingMemory()
            wm.agregar('temperatura', 'valor_celsius', 14)
            wm.agregar('alimento', 'es_perecedero', True)
            wm.agregar('exposicion', 'riesgo_prolongado', True, derivado=True)
        """
        if objeto not in self._hechos:
            self._hechos[objeto] = {}
        self._hechos[objeto][atributo] = valor

        # Registrar aparte solo los hechos del usuario (no los derivados por el motor)
        if not derivado:
            if objeto not in self._hechos_usuario:
                self._hechos_usuario[objeto] = {}
            self._hechos_usuario[objeto][atributo] = valor

    # ------------------------------------------------------------------
    # Lectura de hechos
    # ------------------------------------------------------------------

    def obtener(self, objeto: str, atributo: str):
        """
        Retorna el valor de un hecho o None si no existe.

        Args:
            objeto   (str): Entidad a consultar.
            atributo (str): Atributo a consultar.

        Returns:
            El valor almacenado, o None si el hecho no existe.

        Ejemplo:
            temp = wm.obtener('temperatura', 'valor_celsius')  # 14 o None
        """
        return self._hechos.get(objeto, {}).get(atributo, None)

    def existe(self, objeto: str, atributo: str) -> bool:
        """
        Verifica si un hecho existe en la memoria de trabajo.

        Args:
            objeto   (str): Entidad a verificar.
            atributo (str): Atributo a verificar.

        Returns:
            bool: True si el hecho existe (incluso si su valor es None o False).
        """
        return objeto in self._hechos and atributo in self._hechos[objeto]

    # ------------------------------------------------------------------
    # Evaluación de condiciones
    # ------------------------------------------------------------------

    def evaluar_condicion(self, condicion: dict) -> bool:
        """
        Evalúa una condición JSON contra los hechos actuales de la memoria.

        Una condición tiene la estructura:
            {
                "objeto":   "temperatura",
                "atributo": "valor_celsius",
                "operador": ">",
                "valor":    5
            }

        Operadores soportados:
            =        igualdad exacta
            !=       desigualdad
            >        mayor que (numérico)
            <        menor que (numérico)
            >=       mayor o igual (numérico)
            <=       menor o igual (numérico)
            in       el valor actual está en la lista de valores esperados
            not_in   el valor actual NO está en la lista

        Si el hecho no existe en la memoria, la condición siempre retorna False.
        Si hay error de tipo (ej: comparar string con número), retorna False.

        Args:
            condicion (dict): Diccionario con objeto, atributo, operador y valor.

        Returns:
            bool: True si la condición se cumple con los hechos actuales.

        Ejemplo:
            cond = {"objeto": "temperatura", "atributo": "valor_celsius",
                    "operador": ">", "valor": 5}
            ok = wm.evaluar_condicion(cond)  # True si temperatura > 5
        """
        objeto = condicion.get('objeto')
        atributo = condicion.get('atributo')
        operador = condicion.get('operador')
        valor_esperado = condicion.get('valor')

        # Si el hecho no existe, la condición no puede cumplirse
        valor_actual = self.obtener(objeto, atributo)
        if valor_actual is None:
            return False

        try:
            # Paso: Evaluar según el operador especificado en la condición
            if operador == '=':
                return valor_actual == valor_esperado
            elif operador == '!=':
                return valor_actual != valor_esperado
            elif operador == '>':
                return float(valor_actual) > float(valor_esperado)
            elif operador == '<':
                return float(valor_actual) < float(valor_esperado)
            elif operador == '>=':
                return float(valor_actual) >= float(valor_esperado)
            elif operador == '<=':
                return float(valor_actual) <= float(valor_esperado)
            elif operador == 'in':
                # valor_esperado debe ser una lista de valores admisibles
                return valor_actual in valor_esperado
            elif operador == 'not_in':
                return valor_actual not in valor_esperado
            else:
                # Operador desconocido — no se puede evaluar la condición
                return False
        except (TypeError, ValueError):
            # Error de conversión de tipos al comparar → condición no cumplida
            return False

    # ------------------------------------------------------------------
    # Serialización
    # ------------------------------------------------------------------

    def como_dict(self) -> dict:
        """
        Retorna todos los hechos de la memoria como diccionario.

        Returns:
            dict: Copia de los hechos en formato {objeto: {atributo: valor}}.

        Ejemplo:
            d = wm.como_dict()
            # {'temperatura': {'valor_celsius': 14}, 'alimento': {'tipo': 'carne_cruda'}}
        """
        return {obj: dict(attrs) for obj, attrs in self._hechos.items()}

    @property
    def hechos_iniciales(self) -> dict:
        """
        Retorna solo los hechos ingresados por el usuario (no los derivados).

        Returns:
            dict: Hechos del usuario en formato {objeto: {atributo: valor}}.
        """
        return {obj: dict(attrs) for obj, attrs in self._hechos_usuario.items()}

    # ------------------------------------------------------------------
    # Carga masiva (desde el frontend)
    # ------------------------------------------------------------------

    def cargar_desde_dict(self, hechos: dict):
        """
        Carga hechos masivamente desde un diccionario anidado.

        Formato esperado: {objeto: {atributo: valor, ...}, ...}
        Todos los hechos cargados por este método se marcan como 'usuario' (no derivados).

        Args:
            hechos (dict): Diccionario anidado {objeto: {atributo: valor}}.

        Ejemplo:
            wm.cargar_desde_dict({
                'temperatura': {'valor_celsius': 14, 'medida': True},
                'alimento': {'tipo': 'carne_cruda', 'es_perecedero': True}
            })
        """
        for objeto, atributos in hechos.items():
            if isinstance(atributos, dict):
                for atributo, valor in atributos.items():
                    self.agregar(objeto, atributo, valor, derivado=False)
