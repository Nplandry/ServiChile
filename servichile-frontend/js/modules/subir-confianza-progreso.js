/* Parte de SubirConfianza */
(function () {
  const T = (window.SubirConfianza = window.SubirConfianza || {});
  Object.assign(T, {
    scoreConfiabilidad() {
    const score = SubirConfianza.perfil().score_confiabilidad;
    if (score == null || score === '') return null;
    const n = Number(score);
    return Number.isFinite(n) ? n : null;
  },

    tasaNoConcretados() {
    const score = SubirConfianza.scoreConfiabilidad();
    if (score == null) return null;
    return Math.round((100 - score) * 10) / 10;
  },

    edadNumerica() {
    const n = Number(SubirConfianza.perfil().edad);
    return Number.isFinite(n) ? n : null;
  },

    telefonoOk() {
    const tel = SubirConfianza.perfil().telefono;
    return !!(tel && String(tel).trim());
  },

    estaHecha(tareaId) {
    return SubirConfianza.estadoPunto(tareaId) === 'ok';
  },

    estadoPunto(tareaId) {
    const perfil = SubirConfianza.perfil();
    const score = SubirConfianza.scoreConfiabilidad();
    const tasa = SubirConfianza.tasaNoConcretados();

    switch (tareaId) {
      case 'n1-registro':
        return typeof Auth !== 'undefined' && Auth.isAuthenticated() ? 'ok' : 'pendiente';
      case 'n1-cedula':
        if (perfil.rut_verificado || perfil.cedula_verificada) return 'ok';
        return 'pendiente';
      case 'n1-perfil': {
        const edad = SubirConfianza.edadNumerica();
        const edadOk = edad != null && edad >= 18;
        const telOk = SubirConfianza.telefonoOk();
        if (edadOk && telOk) return 'ok';
        if (edad != null || telOk) return 'progreso';
        return 'pendiente';
      }
      case 'n2-concretados':

        return score != null ? 'ok' : 'pendiente';
      case 'n2-puntualidad':
        if (score != null && score >= 85) return 'ok';
        if (score != null) return 'progreso';
        return 'pendiente';
      case 'n2-no-concretados':
        if (tasa != null && tasa < 15) return 'ok';
        if (tasa != null) return 'progreso';
        return 'pendiente';
      case 'n3-antecedentes':

        return SubirConfianza.perfil().antecedentes_verificados ? 'ok' : 'pendiente';
      case 'n3-biometria':
        return SubirConfianza.biometriaHecha() ? 'ok' : 'pendiente';
      case 'n3-aval':
        if (SubirConfianza.perfil().aval_verificado) return 'ok';
        return SubirConfianza.tieneDoc('aval') ? 'ok' : 'pendiente';
      default:
        return 'pendiente';
    }
  },

    etiquetaPunto(estado) {
    if (estado === 'ok') return 'Cumplido';
    if (estado === 'progreso') return 'En progreso';
    return 'Pendiente';
  },

    detallePunto(tareaId) {
    const perfil = SubirConfianza.perfil();
    const score = SubirConfianza.scoreConfiabilidad();
    const tasa = SubirConfianza.tasaNoConcretados();
    const estado = SubirConfianza.estadoPunto(tareaId);

    switch (tareaId) {
      case 'n1-registro':
        return estado === 'ok'
          ? 'Cuenta activa e inició sesión correctamente.'
          : 'Debe crear una cuenta e iniciar sesión.';
      case 'n1-cedula':
        if (perfil.cedula_verificada) return 'Carnet validado (foto frontal).';
        if (perfil.rut_verificado) return 'Identidad verificada con RUT.';
        return 'Falta verificar el RUT o validar la foto frontal del carnet.';
      case 'n1-perfil': {
        const edad = SubirConfianza.edadNumerica();
        const telOk = SubirConfianza.telefonoOk();
        const edadOk = edad != null && edad >= 18;
        if (edadOk && telOk) return 'Teléfono y mayoría de edad completados.';
        if (edad != null && edad < 18) return 'Debe declarar 18 años o más.';
        if (edadOk) return 'Edad completa. Falta el teléfono móvil.';
        if (telOk) return 'Teléfono completo. Falta declarar la edad.';
        return 'Complete el teléfono móvil y la edad (18 o más).';
      }
      case 'n2-concretados':
        return estado === 'ok'
          ? 'Ya registra al menos un trabajo concretado.'
          : 'Aún no hay trabajos concretados con un proveedor.';
      case 'n2-puntualidad':
        if (score == null) return 'Sin puntaje aún: se calcula con su historial.';
        if (score >= 85) return 'Puntaje de confiabilidad ' + score + '% (meta 85% alcanzada).';
        return 'Puntaje actual ' + score + '%. Debe llegar a 85% o más.';
      case 'n2-no-concretados':
        if (tasa == null) return 'Sin historial aún para medir no concretados.';
        if (tasa < 15) return 'Tasa de no concretados ' + tasa + '% (bajo el 15% exigido).';
        return 'Tasa de no concretados ' + tasa + '%. Debe bajar del 15%.';
      case 'n3-antecedentes': {
        if (perfil.antecedentes_verificados) {
          const anot =
            perfil.antecedentes_anotaciones === true
              ? 'Anotaciones: Sí'
              : perfil.antecedentes_anotaciones === false
                ? 'Anotaciones: No'
                : 'Anotaciones: -';
          return 'Certificado verificado. ' + anot + ' (no afecta el puntaje).';
        }
        return estado === 'ok'
          ? 'Certificado de antecedentes cargado.'
          : 'Debe cargar el certificado de antecedentes.';
      }
      case 'n3-biometria':
        return estado === 'ok'
          ? 'Verificación facial completada.'
          : 'Complete la verificación facial más abajo.';
      case 'n3-aval': {
        if (perfil.aval_verificado) {
          const partes = ['Aval/garantía verificado'];
          if (perfil.aval_tipo) partes.push(perfil.aval_tipo);
          if (perfil.aval_score != null) partes.push('score ' + perfil.aval_score);
          return partes.join(' ') + '.';
        }
        return estado === 'ok'
          ? 'Aval o garantía registrado.'
          : 'Debe cargar un aval, boleta o póliza.';
      }
      default:
        return SubirConfianza.etiquetaPunto(estado);
    }
  },

    totalTareas() {
    return SubirConfianza.NIVELES.reduce((n, nivel) => n + nivel.tareas.length, 0);
  },

    tareasHechas() {
    return SubirConfianza.NIVELES.reduce(
      (n, nivel) => n + nivel.tareas.filter(t => SubirConfianza.estaHecha(t.id)).length,
      0
    );
  },

    progresoPct() {
    const total = SubirConfianza.totalTareas();
    if (!total) return 0;
    return Math.round((SubirConfianza.tareasHechas() / total) * 100);
  },

    nivelSugerido() {
    let nivel = 0;
    for (const n of SubirConfianza.NIVELES) {
      if (n.tareas.every(t => SubirConfianza.estaHecha(t.id))) nivel = n.id;
      else break;
    }
    return Math.max(1, nivel || (SubirConfianza.estaHecha('n1-registro') ? 1 : 0));
  },

    xpActual() {
    const perfil = SubirConfianza.perfil();
    const n = Number(perfil && perfil.xp);
    return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
  },

    nivelXp() {
    const perfil = SubirConfianza.perfil();
    const n = Number(perfil && perfil.nivel_xp);
    if (Number.isFinite(n) && n >= 1) return Math.min(3, Math.floor(n));
    return SubirConfianza.nivelSugerido();
  },

    resumenProgreso() {
    const snap = ProgresoCuenta.actual().snapshot();
    const x = snap.extras || {};
    return {
      tipo: snap.tipo,
      hechas: x.hechas != null ? x.hechas : 0,
      total: x.total != null ? x.total : 0,
      pct: snap.pct,
      nivel: x.nivel != null ? x.nivel : 1,
      xp: x.xp != null ? x.xp : 0,
      meta: snap.meta,
      valor: snap.valor,
      titulo: snap.titulo
    };
  },

    montarIndicador(contenedor, opts) {
    return ProgresoCuenta.actual().montarIndicador(contenedor, opts || {});
  },

    bloqueIndicador(opts) {
    return ProgresoCuenta.actual().crearIndicador(opts || {});
  },

    bloqueChecklist() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-todo';
    wrap.setAttribute('aria-label', 'Lista para subir de nivel');

    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = 'Qué desbloquea cada verificación';

    const lead = document.createElement('p');
    lead.className = 'section-lead';
    lead.textContent =
      'Cumpla solo lo necesario según el tipo de trato. Cada nivel refuerza identidad y cumplimiento.';

    const normales = SubirConfianza.NIVELES.filter(n => !n.especial);
    const especiales = SubirConfianza.NIVELES.filter(n => n.especial);

    wrap.append(
      titulo,
      lead,
      SubirConfianza.carruselNiveles(normales),
      ...especiales.map(n => SubirConfianza.renderGrupo(n))
    );
    return wrap;
  },

    carruselNiveles(niveles) {
    const max = Math.max(0, niveles.length - 1);
    if (SubirConfianza.carruselIdx > max) SubirConfianza.carruselIdx = max;
    if (SubirConfianza.carruselIdx < 0) SubirConfianza.carruselIdx = 0;

    const root = document.createElement('div');
    root.className = 'confianza-carrusel';
    root.setAttribute('aria-roledescription', 'carrusel');
    root.setAttribute('aria-label', 'Niveles 1 a 3');

    const cabecera = document.createElement('header');
    cabecera.className = 'confianza-carrusel__cabecera';

    const nav = document.createElement('div');
    nav.className = 'confianza-carrusel__nav';

    const prev = document.createElement('button');
    prev.type = 'button';
    prev.className = 'confianza-carrusel__btn';
    prev.setAttribute('aria-label', 'Nivel anterior');
    const prevIcon = document.createElement('span');
    prevIcon.setAttribute('aria-hidden', 'true');
    prevIcon.textContent = '‹';
    prev.appendChild(prevIcon);

    const tituloWrap = document.createElement('div');
    tituloWrap.className = 'confianza-carrusel__titulo-wrap';

    const badge = document.createElement('span');
    badge.className = 'confianza-carrusel__badge';
    badge.setAttribute('aria-hidden', 'true');

    const meta = document.createElement('h4');
    meta.className = 'confianza-carrusel__titulo';
    meta.setAttribute('aria-live', 'polite');

    const resumen = document.createElement('span');
    resumen.className = 'confianza-carrusel__resumen';

    tituloWrap.append(badge, meta, resumen);

    const next = document.createElement('button');
    next.type = 'button';
    next.className = 'confianza-carrusel__btn';
    next.setAttribute('aria-label', 'Nivel siguiente');
    const nextIcon = document.createElement('span');
    nextIcon.setAttribute('aria-hidden', 'true');
    nextIcon.textContent = '›';
    next.appendChild(nextIcon);

    nav.append(prev, tituloWrap, next);

    const regla = document.createElement('hr');
    regla.className = 'confianza-carrusel__hr';

    cabecera.append(nav, regla);

    const viewport = document.createElement('div');
    viewport.className = 'confianza-carrusel__viewport';

    const track = document.createElement('div');
    track.className = 'confianza-carrusel__track';

    const slides = niveles.map((nivel, i) => {
      const slide = document.createElement('div');
      slide.className = 'confianza-carrusel__slide';
      slide.setAttribute('aria-hidden', i === SubirConfianza.carruselIdx ? 'false' : 'true');
      slide.appendChild(SubirConfianza.renderGrupo(nivel, { sinCabecera: true }));
      track.appendChild(slide);
      return slide;
    });

    viewport.appendChild(track);

    const dots = document.createElement('div');
    dots.className = 'confianza-carrusel__dots';
    dots.setAttribute('role', 'tablist');
    dots.setAttribute('aria-label', 'Elegir nivel');

    const dotBtns = niveles.map((nivel, i) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'confianza-carrusel__dot';
      dot.setAttribute('role', 'tab');
      dot.setAttribute('aria-label', nivel.titulo);
      dot.addEventListener('click', () => irA(i));
      dots.appendChild(dot);
      return dot;
    });

    function pintar() {
      const idx = SubirConfianza.carruselIdx;
      track.style.transform = 'translateX(-' + idx * 100 + '%)';
      slides.forEach((slide, i) => {
        slide.setAttribute('aria-hidden', i === idx ? 'false' : 'true');
      });
      dotBtns.forEach((dot, i) => {
        const activo = i === idx;
        dot.classList.toggle('confianza-carrusel__dot--activo', activo);
        dot.setAttribute('aria-selected', activo ? 'true' : 'false');
      });
      prev.disabled = idx <= 0;
      next.disabled = idx >= max;
      const n = niveles[idx];
      if (n) {
        badge.textContent = String(n.id);
        meta.textContent = n.titulo + ' ' + n.evalua;
        const done = n.tareas.filter(t => SubirConfianza.estaHecha(t.id)).length;
        resumen.textContent = done + '/' + n.tareas.length + ' Tareas Completadas';
      } else {
        badge.textContent = '';
        meta.textContent = '';
        resumen.textContent = '';
      }
    }

    function irA(i) {
      SubirConfianza.carruselIdx = Math.max(0, Math.min(max, i));
      pintar();
    }

    prev.addEventListener('click', () => irA(SubirConfianza.carruselIdx - 1));
    next.addEventListener('click', () => irA(SubirConfianza.carruselIdx + 1));

    root.append(cabecera, viewport, dots);
    pintar();
    return root;
  },

    renderGrupo(nivel, opts) {
    const sinCabecera = !!(opts && opts.sinCabecera);
    const grupo = document.createElement('div');
    grupo.className =
      'confianza-todo__grupo' +
      (nivel.especial ? ' confianza-todo__grupo--especial' : '') +
      (sinCabecera ? ' confianza-todo__grupo--en-carrusel' : '');

    if (!sinCabecera) {
      const head = document.createElement('header');
      head.className = 'confianza-todo__grupo-head';

      const badge = document.createElement('span');
      badge.className = 'confianza-todo__badge';
      badge.textContent = String(nivel.id);

      const nombre = document.createElement('h4');
      nombre.className = 'confianza-todo__grupo-titulo';
      nombre.textContent = nivel.titulo + ' ' + nivel.evalua;

      const doneCount = nivel.tareas.filter(t => SubirConfianza.estaHecha(t.id)).length;
      const resumen = document.createElement('span');
      resumen.className = 'confianza-todo__resumen';
      resumen.textContent = doneCount + '/' + nivel.tareas.length + ' Tareas Completadas';

      head.append(badge, nombre, resumen);
      grupo.appendChild(head);
    }

    const ul = document.createElement('ul');
    ul.className = 'confianza-todo__items';

    nivel.tareas.forEach(tarea => {
      const punto = SubirConfianza.estadoPunto(tarea.id);
      const detalle = SubirConfianza.detallePunto(tarea.id);
      const li = document.createElement('li');
      li.className = 'confianza-todo__item confianza-todo__item--' + punto;

      const estadoWrap = document.createElement('div');
      estadoWrap.className = 'confianza-todo__estado';

      const estado = document.createElement('span');
      estado.className = 'confianza-todo__punto confianza-todo__punto--' + punto;
      estado.setAttribute('aria-hidden', 'true');

      const estadoTxt = document.createElement('span');
      estadoTxt.className = 'confianza-todo__estado-txt confianza-todo__estado-txt--' + punto;
      estadoTxt.textContent = SubirConfianza.etiquetaPunto(punto);

      estadoWrap.append(estado, estadoTxt);

      const cuerpo = document.createElement('div');
      cuerpo.className = 'confianza-todo__cuerpo';

      const label = document.createElement('p');
      label.className = 'confianza-todo__label';
      label.textContent = tarea.label;

      const detalleEl = document.createElement('p');
      detalleEl.className = 'confianza-todo__detalle';
      detalleEl.textContent = detalle;

      const como = document.createElement('p');
      como.className = 'confianza-todo__como';
      como.textContent = tarea.como;

      cuerpo.append(label, detalleEl, como);
      li.append(estadoWrap, cuerpo);
      li.setAttribute(
        'aria-label',
        SubirConfianza.etiquetaPunto(punto) + ': ' + tarea.label + '. ' + detalle
      );
      ul.appendChild(li);
    });

    grupo.appendChild(ul);
    return grupo;
  },

    bloqueTablaNiveles() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-tabla';
    wrap.setAttribute('aria-label', 'Referencia de niveles');

    const details = document.createElement('details');
    details.className = 'confianza-tabla__details';
    details.open = !!SubirConfianza.tablaAbierta;
    details.addEventListener('toggle', () => {
      SubirConfianza.tablaAbierta = details.open;
    });

    const summary = document.createElement('summary');
    summary.className = 'confianza-tabla__summary';

    const summaryTitulo = document.createElement('span');
    summaryTitulo.className = 'confianza-tabla__summary-titulo';
    summaryTitulo.textContent = 'Referencia de niveles';

    const summaryLead = document.createElement('span');
    summaryLead.className = 'confianza-tabla__summary-lead';
    summaryLead.textContent = 'Qué evalúa cada nivel, qué pide y para qué sirve.';

    const chevron = document.createElement('span');
    chevron.className = 'confianza-tabla__chevron';
    chevron.setAttribute('aria-hidden', 'true');
    chevron.textContent = '▾';

    summary.append(summaryTitulo, summaryLead, chevron);

    const panel = document.createElement('div');
    panel.className = 'confianza-tabla__panel';

    const scroll = document.createElement('div');
    scroll.className = 'confianza-tabla__scroll';

    const table = document.createElement('table');
    table.className = 'confianza-tabla__grid';

    const thead = document.createElement('thead');
    const trHead = document.createElement('tr');
    ['Nivel', 'Qué evalúa', 'Requisito o métrica', 'Casos de uso', '¿Discriminatorio por dinero?'].forEach(
      t => {
        const th = document.createElement('th');
        th.scope = 'col';
        th.textContent = t;
        trHead.appendChild(th);
      }
    );
    thead.appendChild(trHead);

    const tbody = document.createElement('tbody');
    SubirConfianza.NIVELES.forEach(n => {
      const tr = document.createElement('tr');
      if (n.especial) tr.className = 'confianza-tabla__row--especial';
      [n.titulo, n.evalua, n.requisito, n.usos, n.discriminatorioNota].forEach((texto, i) => {
        const td = document.createElement('td');
        td.textContent = texto;
        if (i === 0) td.className = 'confianza-tabla__nivel';
        if (i === 4) {
          td.className = n.discriminatorio
            ? 'confianza-tabla__flag confianza-tabla__flag--si'
            : 'confianza-tabla__flag confianza-tabla__flag--no';
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.append(thead, tbody);
    scroll.appendChild(table);
    panel.appendChild(scroll);
    details.append(summary, panel);
    wrap.appendChild(details);
    return wrap;
  }
  });
})();
