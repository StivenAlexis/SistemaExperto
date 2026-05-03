/**
 * app.js — Lógica del frontend del Sistema Experto SEHSA
 * ========================================================
 * Gestiona las 7 pantallas de la aplicación como secciones que se muestran/ocultan
 * sin recargar la página (SPA — Single Page Application).
 * Se comunica con el servidor Flask mediante fetch() para consultas e historial.
 *
 * Flujo de uso:
 *   Inicio → Selección de perfil → Selección de módulo →
 *   Formulario de hechos → Resultado → Explicación detallada
 *   (desde cualquier pantalla se puede acceder al historial)
 */

// -----------------------------------------------------------------------
// Estado global de la sesión
// -----------------------------------------------------------------------
const estado = {
  perfil: null,           // 'operario' | 'supervisor' | 'profesional' | 'gerente'
  modulo: null,           // id del módulo seleccionado
  hechos: {},             // hechos acumulados del formulario
  resultado: null,        // último resultado del motor
  modulosData: [],        // datos de módulos cargados desde /modulos
};

// -----------------------------------------------------------------------
// Utilidades de navegación entre pantallas
// -----------------------------------------------------------------------

/** Muestra la pantalla con el id dado y oculta las demás. */
function mostrarPantalla(id) {
  document.querySelectorAll('.pantalla').forEach(p => p.classList.remove('activa'));
  const pantalla = document.getElementById(id);
  if (pantalla) {
    pantalla.classList.add('activa');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

// -----------------------------------------------------------------------
// Pantalla 1 — Inicio
// -----------------------------------------------------------------------

function irAInicio() {
  mostrarPantalla('pantalla-inicio');
}

document.getElementById('btn-iniciar-consulta').addEventListener('click', () => {
  mostrarPantalla('pantalla-perfil');
});

document.getElementById('btn-ver-historial').addEventListener('click', () => {
  cargarHistorial();
  mostrarPantalla('pantalla-historial');
});

// -----------------------------------------------------------------------
// Pantalla 2 — Selección de perfil
// -----------------------------------------------------------------------

const PERFILES = [
  { id: 'operario',    nombre: 'Operario',    icono: '👷', desc: 'Acciones directas y simples, sin tecnicismos' },
  { id: 'supervisor',  nombre: 'Supervisor',  icono: '👔', desc: 'Acción + motivo principal, jerga técnica básica' },
  { id: 'profesional', nombre: 'Profesional', icono: '🔬', desc: 'Detalle técnico completo con normativa' },
  { id: 'gerente',     nombre: 'Gerente',     icono: '📊', desc: 'Resumen ejecutivo con impacto sobre el negocio' },
];

(function renderizarPerfiles() {
  const contenedor = document.getElementById('grid-perfiles');
  PERFILES.forEach(p => {
    const div = document.createElement('div');
    div.className = 'tarjeta-opcion';
    div.id = `perfil-${p.id}`;
    div.innerHTML = `
      <div class="icono">${p.icono}</div>
      <div class="nombre">${p.nombre}</div>
      <div class="desc">${p.desc}</div>
    `;
    div.addEventListener('click', () => seleccionarPerfil(p.id));
    contenedor.appendChild(div);
  });
})();

function seleccionarPerfil(id) {
  estado.perfil = id;
  document.querySelectorAll('.tarjeta-opcion[id^="perfil-"]').forEach(el => el.classList.remove('seleccionada'));
  document.getElementById(`perfil-${id}`).classList.add('seleccionada');
  // Avanzar al módulo después de un momento visual
  setTimeout(() => {
    cargarModulosYMostrar();
  }, 250);
}

// -----------------------------------------------------------------------
// Pantalla 3 — Selección de módulo
// -----------------------------------------------------------------------

const ICONOS_MODULO = {
  cadena_frio:   '🌡️',
  contaminacion: '🦠',
  epp:           '🦺',
  plagas:        '🐀',
  documentacion: '📋',
};

async function cargarModulosYMostrar() {
  mostrarPantalla('pantalla-modulo');
  try {
    const resp = await fetch('/modulos');
    const modulos = await resp.json();
    estado.modulosData = modulos;
    renderizarModulos(modulos);
  } catch (e) {
    mostrarError('No se pudieron cargar los módulos. Verifique que el servidor esté activo.');
  }
}

function renderizarModulos(modulos) {
  const contenedor = document.getElementById('grid-modulos');
  contenedor.innerHTML = '';

  modulos.forEach(m => {
    const div = document.createElement('div');
    div.className = 'tarjeta-opcion';
    div.innerHTML = `
      <div class="icono">${ICONOS_MODULO[m.id] || '📁'}</div>
      <div class="nombre">${m.nombre}</div>
      <div class="desc">${m.descripcion}</div>
    `;
    div.addEventListener('click', () => seleccionarModulo(m.id));
    contenedor.appendChild(div);
  });

  // Opción evaluación general
  const divGeneral = document.createElement('div');
  divGeneral.className = 'tarjeta-opcion';
  divGeneral.innerHTML = `
    <div class="icono">🔍</div>
    <div class="nombre">Evaluación general</div>
    <div class="desc">No sé el módulo — evaluar todas las áreas</div>
  `;
  divGeneral.addEventListener('click', () => seleccionarModulo('general'));
  contenedor.appendChild(divGeneral);
}

function seleccionarModulo(id) {
  estado.modulo = id;
  estado.hechos = {};
  renderizarFormulario(id);
  mostrarPantalla('pantalla-formulario');
}

// -----------------------------------------------------------------------
// Pantalla 4 — Formulario de carga de hechos
// -----------------------------------------------------------------------

function renderizarFormulario(moduloId) {
  let preguntas = [];

  if (moduloId === 'general') {
    // Evaluación general: todas las preguntas de todos los módulos (sin duplicar ETA)
    const vistas = new Set();
    estado.modulosData.forEach(m => {
      m.preguntas.forEach(p => {
        if (!vistas.has(p.id)) {
          vistas.add(p.id);
          preguntas.push(p);
        }
      });
    });
    document.getElementById('titulo-formulario').textContent = 'Evaluación General — Todos los Módulos';
  } else {
    const moduloData = estado.modulosData.find(m => m.id === moduloId);
    if (moduloData) {
      preguntas = moduloData.preguntas;
      document.getElementById('titulo-formulario').textContent = moduloData.nombre;
    }
  }

  const contenedor = document.getElementById('contenedor-preguntas');
  contenedor.innerHTML = '';

  // Actualizar barra de progreso
  actualizarProgreso(0, preguntas.length);

  preguntas.forEach((pregunta, idx) => {
    const grupo = crearGrupoPregunta(pregunta, idx, preguntas.length);
    contenedor.appendChild(grupo);
  });

  // Botón de envío al final
  const btnEnviar = document.getElementById('btn-consultar');
  btnEnviar.style.display = 'inline-flex';
}

function crearGrupoPregunta(pregunta, idx, total) {
  const div = document.createElement('div');
  div.className = 'pregunta-grupo';
  div.id = `grupo-${pregunta.id}`;

  const requeridoBadge = pregunta.requerido ? '<span class="badge-req">Requerido</span>' : '';
  const alertaHtml = pregunta.alerta
    ? `<div class="bloque-advertencia" style="margin-top:8px;font-size:.82rem;">
         <span class="adv-titulo">⚠️ Atención:</span> ${pregunta.alerta}
       </div>`
    : '';

  let inputHtml = '';

  if (pregunta.tipo === 'bool') {
    inputHtml = `
      <div class="opciones-bool">
        <button class="opcion-btn" data-id="${pregunta.id}" data-val="true" onclick="responderBool('${pregunta.id}', true, this)">✅ Sí</button>
        <button class="opcion-btn" data-id="${pregunta.id}" data-val="false" onclick="responderBool('${pregunta.id}', false, this)">❌ No</button>
        <button class="opcion-btn" data-id="${pregunta.id}" data-val="ns" onclick="responderBool('${pregunta.id}', null, this)">— No sé / No aplica</button>
      </div>
    `;
  } else if (pregunta.tipo === 'number') {
    inputHtml = `
      <input type="number" id="input-${pregunta.id}"
             placeholder="Ingrese valor numérico"
             onchange="responderNumero('${pregunta.id}', this.value)"
             step="0.1" min="0">
    `;
  } else if (pregunta.tipo === 'select' && pregunta.opciones) {
    const options = pregunta.opciones.map(o =>
      `<option value="${o.valor}">${o.etiqueta}</option>`
    ).join('');
    inputHtml = `
      <select id="select-${pregunta.id}" onchange="responderSelect('${pregunta.id}', this.value)">
        <option value="">-- Seleccione una opción --</option>
        ${options}
      </select>
    `;
  }

  div.innerHTML = `
    <label class="pregunta-label">
      ${idx + 1}. ${pregunta.texto} ${requeridoBadge}
    </label>
    ${inputHtml}
    ${alertaHtml}
  `;

  // Si la pregunta tiene dependencia, ocultarla inicialmente
  if (pregunta.depende_de) {
    div.style.display = 'none';
    div.dataset.dependeDe = pregunta.depende_de;
  }

  return div;
}

/** Guarda la respuesta booleana y actualiza el estado visual del botón. */
function responderBool(id, valor, boton) {
  // Limpiar selección previa
  document.querySelectorAll(`.opcion-btn[data-id="${id}"]`).forEach(b => {
    b.classList.remove('activo-si', 'activo-no', 'activo-ns');
  });

  if (valor === true) {
    boton.classList.add('activo-si');
    setHecho(id, true);
  } else if (valor === false) {
    boton.classList.add('activo-no');
    setHecho(id, false);
  } else {
    boton.classList.add('activo-ns');
    eliminarHecho(id);
  }

  // Verificar si hay preguntas dependientes que mostrar/ocultar
  actualizarDependencias();
  contarRespuestas();
}

/** Guarda la respuesta numérica. */
function responderNumero(id, valor) {
  if (valor !== '' && !isNaN(valor)) {
    setHecho(id, parseFloat(valor));
  } else {
    eliminarHecho(id);
  }
  contarRespuestas();
}

/** Guarda la respuesta de selección. */
function responderSelect(id, valor) {
  if (valor) {
    setHecho(id, valor);
  } else {
    eliminarHecho(id);
  }
  contarRespuestas();
}

/**
 * Convierte el id plano "objeto.atributo" en el formato anidado de hechos.
 * ej: "temperatura.valor_celsius" → hechos.temperatura.valor_celsius = valor
 */
function setHecho(id, valor) {
  const [objeto, ...attrs] = id.split('.');
  const atributo = attrs.join('.');
  if (!estado.hechos[objeto]) estado.hechos[objeto] = {};
  estado.hechos[objeto][atributo] = valor;
}

function eliminarHecho(id) {
  const [objeto, ...attrs] = id.split('.');
  const atributo = attrs.join('.');
  if (estado.hechos[objeto]) {
    delete estado.hechos[objeto][atributo];
    if (Object.keys(estado.hechos[objeto]).length === 0) {
      delete estado.hechos[objeto];
    }
  }
}

/** Muestra/oculta preguntas dependientes según los hechos actuales. */
function actualizarDependencias() {
  document.querySelectorAll('[data-depende-de]').forEach(grupo => {
    const dep = grupo.dataset.dependeDe; // ej: "temperatura.medida=true"
    const [idPregunta, valorEsperado] = dep.split('=');
    const [obj, ...attrs] = idPregunta.split('.');
    const attr = attrs.join('.');
    const valorActual = (estado.hechos[obj] || {})[attr];
    const valorParsed = valorEsperado === 'true' ? true
                      : valorEsperado === 'false' ? false
                      : valorEsperado;
    grupo.style.display = (valorActual === valorParsed) ? 'block' : 'none';
  });
}

/** Actualiza el contador y la barra de progreso. */
function contarRespuestas() {
  const total = document.querySelectorAll('.pregunta-grupo').length;
  const respondidas = Object.values(estado.hechos).reduce((acc, obj) =>
    acc + Object.keys(obj).length, 0);
  actualizarProgreso(Math.min(respondidas, total), total);
}

function actualizarProgreso(actual, total) {
  const pct = total > 0 ? Math.round((actual / total) * 100) : 0;
  const fill = document.getElementById('progreso-fill');
  const texto = document.getElementById('progreso-texto');
  if (fill) fill.style.width = pct + '%';
  if (texto) texto.textContent = `${actual} de ${total} preguntas respondidas`;
}

// -----------------------------------------------------------------------
// Enviar consulta al motor
// -----------------------------------------------------------------------

document.getElementById('btn-consultar').addEventListener('click', async () => {
  if (Object.keys(estado.hechos).length === 0) {
    mostrarError('Por favor, responda al menos una pregunta antes de consultar.');
    return;
  }

  const loader = document.getElementById('loader-consulta');
  const btnConsultar = document.getElementById('btn-consultar');
  loader.classList.add('activo');
  btnConsultar.disabled = true;
  btnConsultar.textContent = 'Consultando...';

  try {
    const resp = await fetch('/consulta', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hechos:  estado.hechos,
        perfil:  estado.perfil || 'supervisor',
        modulo:  estado.modulo || 'general'
      })
    });

    if (!resp.ok) throw new Error('Error en el servidor: ' + resp.status);

    estado.resultado = await resp.json();
    renderizarResultado(estado.resultado);
    mostrarPantalla('pantalla-resultado');

  } catch (e) {
    mostrarError('Error al consultar el sistema: ' + e.message);
  } finally {
    loader.classList.remove('activo');
    btnConsultar.disabled = false;
    btnConsultar.textContent = 'Consultar al sistema';
  }
});

// -----------------------------------------------------------------------
// Pantalla 5 — Resultado y diagnóstico
// -----------------------------------------------------------------------

function renderizarResultado(res) {
  const nivel = res.nivel_riesgo_final || 'BAJO';
  const derivacion = res.derivacion_urgente;

  // Panel de nivel de riesgo
  const panelRiesgo = document.getElementById('panel-nivel-riesgo');
  const mapClase = { 'CRÍTICO': 'critico', 'ALTO': 'alto', 'MEDIO': 'medio', 'BAJO': 'bajo' };
  panelRiesgo.className = `panel-riesgo ${mapClase[nivel] || 'bajo'}`;
  document.getElementById('nivel-riesgo-texto').textContent = nivel;
  document.getElementById('nivel-riesgo-desc').textContent =
    (res.explicacion && res.explicacion.descripcion_riesgo) || '';

  // Alerta ETA
  const alertaEta = document.getElementById('alerta-eta-resultado');
  alertaEta.style.display = derivacion ? 'block' : 'none';

  // Diagnóstico
  document.getElementById('texto-diagnostico').textContent = res.diagnostico || '';

  // Acciones consolidadas
  const listaAcciones = document.getElementById('lista-acciones-resultado');
  listaAcciones.innerHTML = '';
  const acciones = (res.explicacion && res.explicacion.todas_las_acciones) || [];
  if (acciones.length === 0) {
    listaAcciones.innerHTML = '<li class="lista-acciones"><div>No se requieren acciones inmediatas con los datos proporcionados.</div></li>';
  } else {
    acciones.forEach((accion, i) => {
      const li = document.createElement('li');
      li.innerHTML = `<span class="num">${i + 1}</span><span>${accion}</span>`;
      listaAcciones.appendChild(li);
    });
  }

  // Advertencias
  const contenedorAdv = document.getElementById('contenedor-advertencias-resultado');
  contenedorAdv.innerHTML = '';
  const advertencias = res.advertencias || [];
  advertencias.forEach(adv => {
    const div = document.createElement('div');
    div.className = 'bloque-advertencia';
    div.innerHTML = `<div class="adv-titulo">⚠️ Advertencia</div><div>${adv}</div>`;
    contenedorAdv.appendChild(div);
  });

  // Datos faltantes
  const contenedorFalt = document.getElementById('contenedor-datos-faltantes');
  const datos = res.datos_faltantes || [];
  if (datos.length > 0) {
    contenedorFalt.style.display = 'block';
    contenedorFalt.querySelector('span').textContent = datos.join(', ');
  } else {
    contenedorFalt.style.display = 'none';
  }
}

document.getElementById('btn-ver-explicacion').addEventListener('click', () => {
  if (estado.resultado) {
    renderizarExplicacion(estado.resultado);
    mostrarPantalla('pantalla-explicacion');
  }
});

document.getElementById('btn-nueva-consulta').addEventListener('click', () => {
  estado.hechos = {};
  estado.resultado = null;
  mostrarPantalla('pantalla-perfil');
});

document.getElementById('btn-guardar-caso').addEventListener('click', async () => {
  if (!estado.resultado) return;
  try {
    await fetch('/guardar_caso', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hechos:    estado.hechos,
        resultado: estado.resultado,
        perfil:    estado.perfil,
        modulo:    estado.modulo
      })
    });
    document.getElementById('btn-guardar-caso').textContent = '✅ Guardado';
    setTimeout(() => { document.getElementById('btn-guardar-caso').textContent = 'Guardar caso'; }, 2000);
  } catch (e) {
    mostrarError('Error al guardar el caso: ' + e.message);
  }
});

document.getElementById('btn-imprimir').addEventListener('click', async () => {
  if (!estado.resultado) return;
  try {
    const resp = await fetch('/reporte_html', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hechos: estado.hechos, perfil: estado.perfil })
    });
    const html = await resp.text();
    const ventana = window.open('', '_blank');
    ventana.document.write(html);
    ventana.document.close();
    ventana.focus();
    setTimeout(() => ventana.print(), 600);
  } catch (e) {
    mostrarError('Error al generar el reporte: ' + e.message);
  }
});

// -----------------------------------------------------------------------
// Pantalla 6 — Explicación detallada
// -----------------------------------------------------------------------

function renderizarExplicacion(res) {
  const exp = res.explicacion || {};

  // Hechos del usuario
  const tablaHechos = document.getElementById('tabla-hechos-explicacion').querySelector('tbody');
  tablaHechos.innerHTML = '';
  const hechos = exp.hechos_ingresados || [];
  if (hechos.length === 0) {
    tablaHechos.innerHTML = '<tr><td colspan="2" style="color:#888;text-align:center;">Sin hechos registrados</td></tr>';
  } else {
    hechos.forEach(h => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${h.etiqueta}</td><td><strong>${h.valor_legible}</strong></td>`;
      tablaHechos.appendChild(tr);
    });
  }

  // Reglas activadas
  const contenedorReglas = document.getElementById('contenedor-reglas-explicacion');
  contenedorReglas.innerHTML = '';
  const reglas = exp.reglas_activadas || [];
  if (reglas.length === 0) {
    contenedorReglas.innerHTML = '<p style="color:#888;">Ninguna regla se activó.</p>';
  } else {
    reglas.forEach(r => {
      contenedorReglas.appendChild(crearTarjetaRegla(r));
    });
  }

  // Normativa
  const normativa = exp.normativa_aplicada || [];
  document.getElementById('texto-normativa').textContent =
    normativa.length > 0 ? normativa.join(' • ') : 'No se identificó normativa específica.';

  // Justificación
  document.getElementById('texto-justificacion').textContent = exp.justificacion || '';

  // Resumen ejecutivo (solo para gerente)
  const bloque = document.getElementById('bloque-resumen-ejecutivo');
  if (estado.perfil === 'gerente' && exp.resumen_ejecutivo) {
    bloque.style.display = 'block';
    document.getElementById('texto-resumen-ejecutivo').textContent = exp.resumen_ejecutivo;
  } else {
    bloque.style.display = 'none';
  }
}

function crearTarjetaRegla(regla) {
  const div = document.createElement('div');
  div.className = `regla-card nivel-${regla.nivel_riesgo || 'BAJO'}`;

  const condicionesHtml = (regla.condiciones_cumplidas || []).length > 0
    ? `<details class="regla-condiciones">
        <summary>Ver condiciones detectadas (${regla.condiciones_cumplidas.length})</summary>
        <ul>
          ${regla.condiciones_cumplidas.map(c =>
            `<li>${c.descripcion || `${c.objeto}.${c.atributo}`}: <strong>${c.valor_real}</strong></li>`
          ).join('')}
        </ul>
       </details>`
    : '';

  const accionesHtml = (regla.acciones || []).map((a, i) =>
    `<li>${i + 1}. ${a}</li>`
  ).join('');

  const normativaHtml = (regla.normativa || []).length > 0
    ? `<p style="font-size:.8rem;color:#7F8C8D;margin-top:8px;">
         📜 Normativa: ${regla.normativa.join(', ')}
       </p>`
    : '';

  div.innerHTML = `
    <div class="regla-header">
      <div>
        <span class="regla-id">${regla.id}</span>
        <span class="regla-nombre"> — ${regla.nombre}</span>
      </div>
      <span class="badge-riesgo badge-${regla.nivel_riesgo || 'BAJO'}">${regla.nivel_riesgo || 'BAJO'}</span>
    </div>
    ${regla.explicacion ? `<p class="regla-explicacion">${regla.explicacion}</p>` : ''}
    ${condicionesHtml}
    ${accionesHtml ? `<ul style="margin:8px 0 0 18px;font-size:.88rem;">${accionesHtml}</ul>` : ''}
    ${normativaHtml}
  `;
  return div;
}

document.getElementById('btn-volver-resultado').addEventListener('click', () => {
  mostrarPantalla('pantalla-resultado');
});

// -----------------------------------------------------------------------
// Pantalla 7 — Historial de casos
// -----------------------------------------------------------------------

async function cargarHistorial() {
  const tbody = document.getElementById('tabla-historial-body');
  const vacio = document.getElementById('historial-vacio');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#888;">Cargando...</td></tr>';

  try {
    const resp = await fetch('/historial');
    const casos = await resp.json();

    tbody.innerHTML = '';
    if (casos.length === 0) {
      vacio.style.display = 'block';
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#888;">No hay casos guardados aún.</td></tr>';
      return;
    }
    vacio.style.display = 'none';

    casos.forEach(caso => {
      const tr = document.createElement('tr');
      const reglas = (caso.reglas_ids || []).join(', ') || '—';
      tr.innerHTML = `
        <td>${caso.id}</td>
        <td>${caso.fecha_legible || caso.timestamp?.substring(0,16).replace('T',' ')}</td>
        <td>${caso.modulo || '—'}</td>
        <td><span class="nivel-badge nivel-${caso.nivel_riesgo}">${caso.nivel_riesgo || '—'}</span></td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${caso.diagnostico || ''}">
          ${(caso.diagnostico || '').substring(0, 60)}${(caso.diagnostico || '').length > 60 ? '...' : ''}
        </td>
        <td>${reglas}</td>
      `;
      tbody.appendChild(tr);
    });

  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#C0392B;">Error al cargar el historial: ${e.message}</td></tr>`;
  }
}

document.getElementById('btn-historial-desde-menu').addEventListener('click', () => {
  cargarHistorial();
  mostrarPantalla('pantalla-historial');
});

document.getElementById('btn-volver-desde-historial').addEventListener('click', () => {
  mostrarPantalla('pantalla-inicio');
});

// -----------------------------------------------------------------------
// Navegación de volver desde el header
// -----------------------------------------------------------------------

document.getElementById('btn-header-inicio').addEventListener('click', irAInicio);

document.getElementById('btn-header-nueva').addEventListener('click', () => {
  estado.hechos = {};
  estado.resultado = null;
  mostrarPantalla('pantalla-perfil');
});

// -----------------------------------------------------------------------
// Utilidades
// -----------------------------------------------------------------------

function mostrarError(mensaje) {
  alert('⚠️ ' + mensaje);
}

// -----------------------------------------------------------------------
// Inicialización — mostrar pantalla de inicio al cargar
// -----------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  mostrarPantalla('pantalla-inicio');
});
