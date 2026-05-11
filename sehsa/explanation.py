"""
explanation.py — Subsistema de Explicación del Sistema Experto SEHSA
=====================================================================
Componente: Subsistema de Explicación (Explanation System)
Rol en la arquitectura:
  - Recibe el resultado del motor de inferencia (engine.py) y los hechos del usuario.
  - Genera el reporte de explicación adaptado al perfil del usuario.
  - Produce el reporte en dos formatos: diccionario Python (para JSON) y HTML (para imprimir).
  - Es invocado por app.py después de que engine.py completa la inferencia.

Los reportes varían según el perfil:
  - operario    : acción directa y simple, sin tecnicismos.
  - supervisor  : acción + motivo principal, jerga técnica básica.
  - profesional : detalle técnico completo + normativa.
  - gerente     : resumen ejecutivo + impacto sobre el negocio.
"""

from datetime import datetime


# Descripciones de los niveles de riesgo para el reporte
DESCRIPCIONES_RIESGO = {
    'CRÍTICO': 'Riesgo CRÍTICO — Acción inmediata obligatoria. Peligro directo para la salud.',
    'ALTO':    'Riesgo ALTO — Acción urgente requerida antes de continuar operaciones.',
    'MEDIO':   'Riesgo MEDIO — Acción correctiva en el corto plazo.',
    'BAJO':    'Riesgo BAJO — Monitorear y aplicar medidas preventivas.',
}

# Colores CSS por nivel de riesgo
COLORES_RIESGO = {
    'CRÍTICO': '#C0392B',
    'ALTO':    '#E67E22',
    'MEDIO':   '#F1C40F',
    'BAJO':    '#27AE60',
}

# Etiquetas legibles para objetos y atributos de la memoria de trabajo
ETIQUETAS_OAV = {
    'alimento.tipo':                 'Tipo de alimento',
    'alimento.estado_organo':        'Estado organoléptico',
    'alimento.es_perecedero':        'Es perecedero',
    'alimento.vencimiento_vigente':  'Vencimiento vigente',
    'alimento.cuerpo_extrano':       'Cuerpo extraño detectado',
    'alimento.envase_hermetico':     'Envase hermético',
    'alimento.envase_dañado':        'Envase dañado',
    'alimento.origen':               'Origen del alimento',
    'alimento.en_venta':             'En venta al público',
    'alimento.en_exhibicion':        'En exhibición',
    'temperatura.valor_celsius':     'Temperatura medida (°C)',
    'temperatura.medida':            'Se midió la temperatura',
    'equipo.tipo':                   'Tipo de equipo',
    'equipo.funcionando':            'Equipo funcionando',
    'exposicion.tiempo_conocido':    'Tiempo de exposición conocido',
    'exposicion.horas':              'Horas de exposición',
    'personal.lavo_manos':           'Operario lavó las manos',
    'personal.usa_epp':              'Usa EPP correctamente',
    'personal.contacto_crudo_cocido':'Contacto crudo-cocido',
    'personal.va_a_manipular_listo': 'Va a manipular listo para consumo',
    'personal.levanta_cargas_sin_tecnica': 'Levanta cargas sin técnica',
    'establecimiento.area':          'Área del establecimiento',
    'plaga.indicios':                'Indicios de plaga',
    'plaga.excrementos_sobre_productos': 'Excrementos sobre productos',
    'plaga.dias_ultimo_control':     'Días desde último control de plagas',
    'documentacion.registros_temperatura': 'Registra temperaturas periódicamente',
    'documentacion.rotulacion_correcta':   'Rotulación correcta',
    'incidente.sospecha_ETA':        'Sospecha de ETA',
    'incidente.accidente_laboral':   'Accidente laboral',
    'quimico.tipo':                  'Tipo de químico',
    'coccion.temperatura':           'Temperatura de cocción (°C)',
    'conservacion.correcta':         'Conservación correcta',
    'consumo.mismo_dia':             'Se consume el mismo día',
    'recepcion.temperatura_fuera_rango': 'Temperatura de recepción fuera de rango',
    'proveedor.justifica_cadena':    'Proveedor justifica cadena de frío',
    'utensilio.compartido_sin_lavar':'Utensilios compartidos sin lavar',
    'piso.humedo':                   'Piso húmedo',
    'senalizacion.presente':         'Señalización presente',
}

# Etiquetas legibles para módulos
ETIQUETAS_MODULO = {
    'incertidumbre': 'Manejo de Incertidumbre',
    'cadena_frio':   'Cadena de Frío y Temperaturas',
    'contaminacion': 'Contaminación Cruzada e Higiene',
    'epp':           'Seguridad Laboral y EPP',
    'plagas':        'Control de Plagas',
    'documentacion': 'Documentación y Normativa',
}


class ExplanationSystem:
    """
    Subsistema de explicación del sistema experto SEHSA.

    Transforma el resultado técnico del motor de inferencia en un reporte
    comprensible adaptado al perfil del usuario que realiza la consulta.

    El nivel de detalle del reporte varía según el perfil:
      - operario    : ¿Qué hago ahora? (sin tecnicismos)
      - supervisor  : ¿Qué hago y por qué? (motivo principal)
      - profesional : Detalle técnico completo con normativa
      - gerente     : Resumen ejecutivo con impacto sobre el negocio

    Responsabilidad:
      Tomar el resultado del motor (diagnóstico, reglas activadas, hechos) y
      producir un reporte estructurado que sea útil para el perfil específico.

    Métodos principales:
      generar_reporte_dict() — retorna el reporte como diccionario Python
      generar_reporte_html() — retorna el reporte como HTML estilizado para imprimir
    """

    def __init__(self, resultado: dict, hechos_usuario: dict, perfil: str = 'supervisor'):
        """
        Inicializa el subsistema de explicación con los datos del caso.

        Args:
            resultado      (dict): Resultado completo del motor de inferencia.
            hechos_usuario (dict): Hechos originales ingresados por el usuario.
            perfil         (str):  Perfil del usuario ('operario', 'supervisor',
                                   'profesional', 'gerente').
        """
        self.resultado = resultado
        self.hechos_usuario = hechos_usuario
        self.perfil = perfil
        self.nivel_riesgo = resultado.get('nivel_riesgo_final', 'BAJO')
        self.reglas_activadas = resultado.get('reglas_activadas', [])
        self.diagnostico = resultado.get('diagnostico', '')
        self.advertencias = resultado.get('advertencias', [])
        self.derivacion_urgente = resultado.get('derivacion_urgente', False)
        self.datos_faltantes = resultado.get('datos_faltantes', [])
        self.timestamp = datetime.now().isoformat()

    # ------------------------------------------------------------------
    # Reporte como diccionario (para guardar en JSON / enviar al frontend)
    # ------------------------------------------------------------------

    def generar_reporte_dict(self) -> dict:
        """
        Genera el reporte de explicación como diccionario Python.

        El reporte contiene todos los elementos necesarios para que el frontend
        pueda mostrar la explicación completa al usuario.

        Returns:
            dict: Reporte con hechos, reglas, diagnóstico, acciones y justificación.
        """
        return {
            'perfil':              self.perfil,
            'timestamp':           self.timestamp,
            'nivel_riesgo':        self.nivel_riesgo,
            'descripcion_riesgo':  self._descripcion_riesgo_por_perfil(),
            'derivacion_urgente':  self.derivacion_urgente,
            'diagnostico':         self._diagnostico_por_perfil(),
            'hechos_ingresados':   self._formatear_hechos_usuario(),
            'reglas_activadas':    self._formatear_reglas_por_perfil(),
            'todas_las_acciones':  self._consolidar_acciones(),
            'normativa_aplicada':  self._consolidar_normativa(),
            'advertencias':        self.advertencias,
            'datos_faltantes':     self.datos_faltantes,
            'justificacion':       self._generar_justificacion(),
            'resumen_ejecutivo':   self._generar_resumen_ejecutivo() if self.perfil == 'gerente' else None,
        }

    # ------------------------------------------------------------------
    # Reporte como HTML (para imprimir)
    # ------------------------------------------------------------------

    def generar_reporte_html(self) -> str:
        """
        Genera el reporte de explicación como HTML estilizado listo para imprimir.

        Produce un documento HTML completo con estilos inline que puede abrirse
        directamente en el navegador y usar la función de impresión del sistema.

        Returns:
            str: HTML completo del reporte, incluye estilos CSS inline.
        """
        color = COLORES_RIESGO.get(self.nivel_riesgo, '#888')
        hechos = self._formatear_hechos_usuario()
        reglas = self._formatear_reglas_por_perfil()
        acciones = self._consolidar_acciones()
        normativa = self._consolidar_normativa()
        justificacion = self._generar_justificacion()
        fecha_legible = datetime.now().strftime('%d/%m/%Y %H:%M')

        # Sección de alerta de derivación urgente (solo para ETA)
        alerta_eta = ''
        if self.derivacion_urgente:
            alerta_eta = f"""
            <div style="background:#C0392B;color:white;padding:20px;border-radius:8px;
                        margin:20px 0;font-size:16px;font-weight:bold;text-align:center;">
                ⚠️ DERIVACIÓN URGENTE — SOSPECHA DE ETA<br>
                Derivar INMEDIATAMENTE a médico y autoridad sanitaria competente.<br>
                Este sistema NO emite diagnóstico para este caso.
            </div>
            """

        # Sección de hechos ingresados
        hechos_html = ''.join([
            f'<tr><td style="padding:6px 10px;border-bottom:1px solid #eee;">{h["etiqueta"]}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #eee;font-weight:bold;">{h["valor_legible"]}</td></tr>'
            for h in hechos
        ])

        # Sección de reglas activadas
        reglas_html = ''
        for r in reglas:
            condiciones_html = ''.join([
                f'<li>{c["descripcion"]}: <strong>{c["valor_real"]}</strong></li>'
                for c in r.get('condiciones_cumplidas', [])
            ])
            acciones_html = ''.join([f'<li>{a}</li>' for a in r.get('acciones', [])])
            normativa_r = ', '.join(r.get('normativa', []))
            reglas_html += f"""
            <div style="border:1px solid #ddd;border-radius:6px;padding:14px;margin:10px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <strong style="color:#1A3A5C;">[{r['id']}] {r['nombre']}</strong>
                    <span style="background:{COLORES_RIESGO.get(r.get('nivel_riesgo','BAJO'),'#888')};
                                color:white;padding:3px 10px;border-radius:12px;font-size:12px;">
                        {r.get('nivel_riesgo','BAJO')}
                    </span>
                </div>
                <p style="color:#555;font-style:italic;margin:8px 0 4px;">{r.get('explicacion','')}</p>
                <p style="margin:4px 0;"><strong>Condiciones detectadas:</strong></p>
                <ul style="margin:4px 0 8px 20px;">{condiciones_html}</ul>
                <p style="margin:4px 0;"><strong>Acciones recomendadas:</strong></p>
                <ul style="margin:4px 0 8px 20px;">{acciones_html}</ul>
                {f'<p style="color:#666;font-size:12px;margin:4px 0;">Normativa: {normativa_r}</p>' if normativa_r else ''}
            </div>
            """

        # Sección de acciones consolidadas
        acciones_todas_html = ''.join([
            f'<li style="margin:6px 0;">{a}</li>' for a in acciones
        ])

        # Advertencias
        advertencias_html = ''
        if self.advertencias:
            items = ''.join([f'<li style="margin:4px 0;">{adv}</li>' for adv in self.advertencias])
            advertencias_html = f"""
            <div style="background:#FFF3CD;border:1px solid #F1C40F;border-radius:6px;padding:14px;margin:10px 0;">
                <strong>⚠️ Advertencias:</strong>
                <ul style="margin:8px 0 0 20px;">{items}</ul>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>SEHSA — Reporte de Diagnóstico</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }}
        @media print {{ .no-print {{ display: none; }} }}
        table {{ border-collapse: collapse; width: 100%; }}
    </style>
</head>
<body>
    <div style="border-top:6px solid {color};padding:20px 0 10px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <h1 style="color:#1A3A5C;margin:0;">SEHSA</h1>
                <p style="color:#555;margin:4px 0;">Sistema Experto en Higiene y Seguridad Alimentaria</p>
                <p style="color:#888;font-size:12px;margin:2px 0;">Responsable de Rotisería — Supermercado Parada Canga</p>
            </div>
            <div style="text-align:right;">
                <p style="font-size:12px;color:#888;margin:0;">Generado: {fecha_legible}</p>
                <p style="font-size:12px;color:#888;margin:0;">Perfil: {self.perfil.capitalize()}</p>
            </div>
        </div>
        <hr style="border:none;border-top:1px solid #ddd;margin:10px 0;">
    </div>

    {alerta_eta}

    <!-- Nivel de riesgo -->
    <div style="background:{color};color:white;padding:20px;border-radius:8px;
                text-align:center;margin:15px 0;">
        <div style="font-size:28px;font-weight:bold;">{self.nivel_riesgo}</div>
        <div style="font-size:14px;margin-top:4px;">{DESCRIPCIONES_RIESGO.get(self.nivel_riesgo,'')}</div>
    </div>

    <!-- Diagnóstico -->
    <div style="background:#F8F9FA;border-left:4px solid {color};padding:14px;
                border-radius:0 6px 6px 0;margin:10px 0;">
        <strong>Diagnóstico:</strong>
        <p style="margin:6px 0 0;">{self.diagnostico}</p>
    </div>

    <!-- Hechos ingresados -->
    <h3 style="color:#1A3A5C;border-bottom:2px solid #1A3A5C;padding-bottom:6px;">
        Datos del Caso Evaluado
    </h3>
    <table>
        <thead>
            <tr style="background:#1A3A5C;color:white;">
                <th style="padding:8px 10px;text-align:left;">Dato</th>
                <th style="padding:8px 10px;text-align:left;">Valor</th>
            </tr>
        </thead>
        <tbody>{hechos_html}</tbody>
    </table>

    <!-- Reglas activadas -->
    <h3 style="color:#1A3A5C;border-bottom:2px solid #1A3A5C;padding-bottom:6px;margin-top:20px;">
        Reglas Activadas ({len(reglas)})
    </h3>
    {reglas_html if reglas_html else '<p style="color:#888;">Ninguna regla se activó.</p>'}

    <!-- Acciones consolidadas -->
    <h3 style="color:#1A3A5C;border-bottom:2px solid #1A3A5C;padding-bottom:6px;margin-top:20px;">
        Acciones Recomendadas
    </h3>
    <ol style="padding-left:20px;">{acciones_todas_html}</ol>

    <!-- Normativa aplicada -->
    {f'<h3 style="color:#1A3A5C;border-bottom:2px solid #1A3A5C;padding-bottom:6px;margin-top:20px;">Normativa Aplicada</h3><p>{chr(10).join(normativa)}</p>' if normativa else ''}

    {advertencias_html}

    <!-- Justificación -->
    <h3 style="color:#1A3A5C;border-bottom:2px solid #1A3A5C;padding-bottom:6px;margin-top:20px;">
        Justificación del Diagnóstico
    </h3>
    <p style="color:#555;">{justificacion}</p>

    <!-- Pie de página -->
    <div style="margin-top:30px;padding-top:10px;border-top:1px solid #ddd;
                font-size:11px;color:#999;text-align:center;">
        SEHSA — Sistema Experto en Higiene y Seguridad Alimentaria |
        Ing. Carolina G. Marturet — Ingeniera en Alimentos |
        Generado automáticamente — {fecha_legible}
    </div>
</body>
</html>"""

    # ------------------------------------------------------------------
    # Métodos internos de formateo
    # ------------------------------------------------------------------

    def _formatear_hechos_usuario(self) -> list:
        """
        Convierte los hechos del usuario a una lista de dicts legibles.

        Returns:
            list: Lista de {objeto, atributo, etiqueta, valor, valor_legible}.
        """
        items = []
        for objeto, atributos in self.hechos_usuario.items():
            if isinstance(atributos, dict):
                for atributo, valor in atributos.items():
                    clave = f"{objeto}.{atributo}"
                    etiqueta = ETIQUETAS_OAV.get(clave, f"{objeto} — {atributo}")
                    valor_legible = self._valor_legible(valor)
                    items.append({
                        'objeto':        objeto,
                        'atributo':      atributo,
                        'etiqueta':      etiqueta,
                        'valor':         valor,
                        'valor_legible': valor_legible
                    })
        return items

    def _descripcion_riesgo_por_perfil(self) -> str:
        """
        Devuelve la descripción del nivel de riesgo adaptada al perfil.

        Para operario: lenguaje imperativo y directo ("¡Actuá ahora!").
        Para técnicos: terminología de inocuidad alimentaria / HACCP.

        Returns:
            str: Descripción del nivel de riesgo.
        """
        if self.perfil == 'operario':
            return {
                'CRÍTICO': 'PELIGRO ALTO — Actuá ahora mismo. No esperes.',
                'ALTO':    'ATENCIÓN — Tomá medidas antes de seguir trabajando.',
                'MEDIO':   'PRECAUCIÓN — Corregilo en las próximas horas.',
                'BAJO':    'AVISO — Monitoreá y aplicá las medidas que indica el sistema.',
            }.get(self.nivel_riesgo, '')
        return DESCRIPCIONES_RIESGO.get(self.nivel_riesgo, '')

    def _diagnostico_por_perfil(self) -> str:
        """
        Adapta el texto del diagnóstico al perfil del usuario.

        Para operario: descripción observable, sin términos HACCP.
        Para supervisor/profesional/gerente: terminología técnica completa.

        Returns:
            str: Texto del diagnóstico adaptado.
        """
        if not self.reglas_activadas:
            if self.perfil == 'operario':
                return (
                    "No encontramos problemas con los datos que ingresaste. "
                    "Seguí trabajando con las buenas prácticas de siempre."
                )
            return self.diagnostico

        if self.perfil == 'operario':
            nombres_simples = [r['nombre'] for r in self.reglas_activadas
                               if r.get('modulo') != 'incertidumbre']
            n = len(nombres_simples)
            if n == 0:
                return "El sistema detectó una situación que requiere atención."
            lista = ', '.join(nombres_simples[:2]) + ('...' if n > 2 else '')
            if self.nivel_riesgo == 'CRÍTICO':
                return (
                    f"Encontramos {n} problema(s) que necesitan atención inmediata: {lista}. "
                    "Seguí las instrucciones de abajo ahora mismo."
                )
            if self.nivel_riesgo == 'ALTO':
                return (
                    f"Encontramos {n} problema(s) que hay que resolver antes de seguir: {lista}. "
                    "Seguí las instrucciones de abajo."
                )
            return (
                f"Encontramos {n} situación(es) a corregir en el corto plazo: {lista}."
            )

        # Perfiles técnicos: diagnóstico original del motor
        return self.diagnostico

    def _formatear_reglas_por_perfil(self) -> list:
        """
        Filtra y formatea las reglas activadas según el perfil del usuario.

        El nivel de detalle varía:
          - operario    : solo id, nombre y acciones (sin condiciones técnicas)
          - supervisor  : id, nombre, acciones y explicación breve
          - profesional : todo el detalle técnico + normativa
          - gerente     : id, nombre y nivel de riesgo (sin detalle técnico)

        Returns:
            list: Lista de reglas formateadas según el perfil.
        """
        reglas = []
        for regla in self.reglas_activadas:
            if self.perfil == 'operario':
                acciones = (regla.get('acciones_operario') or regla.get('acciones', []))
                reglas.append({
                    'id':                 regla['id'],
                    'nombre':             regla['nombre'],
                    'nivel_riesgo':       regla.get('nivel_riesgo', ''),
                    'acciones':           acciones,
                    'condiciones_cumplidas': [],
                    'normativa':          [],
                    'explicacion':        ''
                })
            elif self.perfil == 'supervisor':
                reglas.append({
                    'id':                 regla['id'],
                    'nombre':             regla['nombre'],
                    'nivel_riesgo':       regla.get('nivel_riesgo', ''),
                    'acciones':           regla.get('acciones', []),
                    'condiciones_cumplidas': self._simplificar_condiciones(regla.get('condiciones_cumplidas', [])),
                    'normativa':          [],
                    'explicacion':        self._resumen_explicacion(regla.get('explicacion', ''))
                })
            elif self.perfil == 'profesional':
                reglas.append({
                    'id':                 regla['id'],
                    'nombre':             regla['nombre'],
                    'nivel_riesgo':       regla.get('nivel_riesgo', ''),
                    'modulo':             ETIQUETAS_MODULO.get(regla.get('modulo', ''), regla.get('modulo', '')),
                    'acciones':           regla.get('acciones', []),
                    'condiciones_cumplidas': self._condiciones_completas(regla.get('condiciones_cumplidas', [])),
                    'normativa':          regla.get('normativa', []),
                    'explicacion':        regla.get('explicacion', ''),
                    'origen':             regla.get('origen', '')
                })
            elif self.perfil == 'gerente':
                reglas.append({
                    'id':          regla['id'],
                    'nombre':      regla['nombre'],
                    'nivel_riesgo': regla.get('nivel_riesgo', ''),
                    'acciones':    regla.get('acciones', [])[:2],  # Solo las 2 primeras acciones
                    'condiciones_cumplidas': [],
                    'normativa':   [],
                    'explicacion': ''
                })
            else:
                reglas.append(regla)

        return reglas

    def _simplificar_condiciones(self, condiciones: list) -> list:
        """
        Genera una versión simplificada de las condiciones para el perfil supervisor.

        Args:
            condiciones (list): Condiciones cumplidas en formato técnico.

        Returns:
            list: Condiciones con descripción legible y valor real.
        """
        simplificadas = []
        for c in condiciones:
            clave = f"{c['objeto']}.{c['atributo']}"
            etiqueta = ETIQUETAS_OAV.get(clave, f"{c['objeto']} — {c['atributo']}")
            simplificadas.append({
                'descripcion': etiqueta,
                'valor_real':  self._valor_legible(c.get('valor_real'))
            })
        return simplificadas

    def _condiciones_completas(self, condiciones: list) -> list:
        """
        Genera la representación completa de condiciones para el perfil profesional.

        Args:
            condiciones (list): Condiciones cumplidas.

        Returns:
            list: Condiciones con todos los campos técnicos + etiqueta legible.
        """
        completas = []
        for c in condiciones:
            clave = f"{c['objeto']}.{c['atributo']}"
            etiqueta = ETIQUETAS_OAV.get(clave, f"{c['objeto']}.{c['atributo']}")
            completas.append({
                'descripcion':    etiqueta,
                'objeto':         c['objeto'],
                'atributo':       c['atributo'],
                'operador':       c['operador'],
                'valor_esperado': c.get('valor_esperado'),
                'valor_real':     self._valor_legible(c.get('valor_real'))
            })
        return completas

    def _consolidar_acciones(self) -> list:
        """
        Consolida todas las acciones de todas las reglas activadas en una lista única.

        Para perfil 'operario' usa acciones_operario si están disponibles en la regla.
        Para el resto de perfiles usa acciones (lenguaje técnico HACCP).

        Elimina duplicados manteniendo el orden de aparición (regla de mayor prioridad primero).

        Returns:
            list: Lista de strings de acciones únicas y ordenadas.
        """
        acciones_vistas = set()
        acciones_unicas = []
        for regla in self.reglas_activadas:
            if self.perfil == 'operario' and regla.get('acciones_operario'):
                fuente = regla.get('acciones_operario', [])
            else:
                fuente = regla.get('acciones', [])
            for accion in fuente:
                if accion not in acciones_vistas:
                    acciones_vistas.add(accion)
                    acciones_unicas.append(accion)
        return acciones_unicas

    def _consolidar_normativa(self) -> list:
        """
        Consolida toda la normativa de todas las reglas activadas en una lista única.

        Returns:
            list: Lista de strings de normativa única.
        """
        normativa_vista = set()
        normativa_unica = []
        for regla in self.reglas_activadas:
            for norma in regla.get('normativa', []):
                if norma not in normativa_vista:
                    normativa_vista.add(norma)
                    normativa_unica.append(norma)
        return normativa_unica

    def _generar_justificacion(self) -> str:
        """
        Genera el texto de justificación explicando por qué el sistema llegó a la conclusión.

        Para perfil 'operario': lenguaje simple, centrado en lo que el operario observó.
        Para perfiles técnicos: terminología HACCP, IDs de reglas, módulos y normativa.

        Returns:
            str: Texto de justificación en lenguaje natural adaptado al perfil.
        """
        if self.derivacion_urgente:
            if self.perfil == 'operario':
                return (
                    "El sistema detectó que hay personas enfermas. "
                    "Esto está fuera de lo que puede diagnosticar esta herramienta. "
                    "Necesitás un médico y las autoridades sanitarias."
                )
            return (
                "El sistema detectó sospecha de Enfermedad Transmitida por Alimentos (ETA). "
                "Este caso está fuera del alcance del sistema experto SEHSA, que trabaja sobre "
                "condiciones del establecimiento y los alimentos, no sobre diagnósticos médicos. "
                "La derivación a médico y autoridad sanitaria es la única respuesta adecuada."
            )

        if not self.reglas_activadas:
            if self.perfil == 'operario':
                return (
                    "Con los datos que ingresaste no se detectaron problemas. "
                    "Seguí trabajando con las buenas prácticas de siempre."
                )
            return (
                "Ninguna regla de la base de conocimiento se activó con los datos proporcionados. "
                "Esto puede indicar que las condiciones evaluadas están dentro de los parámetros "
                "normales, o que faltan datos relevantes para evaluar alguna situación de riesgo."
            )

        # Perfil operario: justificación en lenguaje observable
        if self.perfil == 'operario':
            observaciones = []
            for regla in self.reglas_activadas:
                expl = regla.get('explicacion', '')
                if expl:
                    # Solo la primera oración, sin jerga técnica en el resumen
                    observaciones.append(expl.split('.')[0].strip() + '.')
            if observaciones:
                return (
                    "Lo que observaste activó las siguientes alertas del sistema: "
                    + ' '.join(observaciones[:2])
                )
            return "El sistema detectó situaciones de riesgo en base a lo que ingresaste."

        # Perfiles técnicos: justificación con detalle HACCP
        ids_reglas = [r['id'] for r in self.reglas_activadas]
        modulos = list({ETIQUETAS_MODULO.get(r.get('modulo', ''), r.get('modulo', ''))
                        for r in self.reglas_activadas if r.get('modulo', '') != 'incertidumbre'})

        justif = (
            f"El motor de inferencia evaluó los datos del caso y activó {len(self.reglas_activadas)} "
            f"regla(s) de la base de conocimiento: {', '.join(ids_reglas)}. "
        )

        if modulos:
            justif += f"Las áreas de riesgo identificadas corresponden a: {', '.join(modulos)}. "

        reglas_criticas = [r for r in self.reglas_activadas if r.get('nivel_riesgo') == 'CRÍTICO']
        if reglas_criticas:
            justif += (
                f"Las {len(reglas_criticas)} regla(s) de nivel CRÍTICO determinaron el nivel de "
                f"riesgo final: {', '.join([r['id'] for r in reglas_criticas])}. "
                "El nivel de riesgo final del caso es el máximo entre todas las reglas activadas."
            )

        return justif

    def _generar_resumen_ejecutivo(self) -> str:
        """
        Genera el resumen ejecutivo para el perfil gerente.

        Focalizado en impacto sobre el negocio: riesgo legal, económico y reputacional.

        Returns:
            str: Texto del resumen ejecutivo.
        """
        n = len(self.reglas_activadas)
        nivel = self.nivel_riesgo

        impactos = {
            'CRÍTICO': (
                "IMPACTO CRÍTICO: La situación identificada requiere suspensión inmediata de "
                "operaciones en el área afectada hasta resolver las no conformidades. "
                "El riesgo legal por incumplimiento del CAA y las consecuencias de una ETA "
                "(retiro de habilitación, multas, daño reputacional) superan ampliamente el "
                "costo de las acciones correctivas inmediatas."
            ),
            'ALTO': (
                "IMPACTO ALTO: Las situaciones identificadas requieren acción urgente y "
                "pueden derivar en sanciones regulatorias si no se resuelven antes de la "
                "próxima inspección sanitaria. Se recomienda implementar las acciones correctivas "
                "en las próximas horas."
            ),
            'MEDIO': (
                "IMPACTO MEDIO: Las situaciones identificadas representan no conformidades "
                "que deben resolverse en el corto plazo (próximos días). No hay riesgo "
                "inmediato para el consumidor pero sí exposición regulatoria."
            ),
            'BAJO': (
                "IMPACTO BAJO: Las situaciones identificadas son oportunidades de mejora "
                "que deben incluirse en el plan de acción del responsable de calidad."
            )
        }

        return (
            f"El sistema identificó {n} situación(es) de riesgo. Nivel consolidado: {nivel}. "
            f"{impactos.get(nivel, '')} "
            f"Reglas activadas: {', '.join([r['id'] for r in self.reglas_activadas])}."
        )

    def _resumen_explicacion(self, explicacion: str) -> str:
        """
        Retorna la primera oración de la explicación (para el perfil supervisor).

        Args:
            explicacion (str): Explicación completa de la regla.

        Returns:
            str: Primera oración de la explicación.
        """
        if not explicacion:
            return ''
        # Tomar hasta el primer punto como resumen
        partes = explicacion.split('.')
        return partes[0].strip() + '.' if partes else explicacion

    @staticmethod
    def _valor_legible(valor) -> str:
        """
        Convierte un valor Python a su representación legible en español.

        Args:
            valor: Valor a convertir (bool, int, float, str, None).

        Returns:
            str: Representación legible del valor.
        """
        if valor is True:
            return 'Sí'
        if valor is False:
            return 'No'
        if valor is None:
            return 'No especificado'
        return str(valor)
