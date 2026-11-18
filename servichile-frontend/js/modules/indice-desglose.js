const IndiceDesglose = {
  FILTROS: Object.freeze([
    { id: 'documentos', etiqueta: 'Documentos legales' },
    { id: 'ciber', etiqueta: 'Ciberseguridad' },
    { id: 'contractual', etiqueta: 'Privacidad y condiciones' },
    { id: 'operativa', etiqueta: 'Local, teléfono y reseñas' },
    { id: 'legal', etiqueta: 'Compras públicas' }
  ]),

  factoresDesdeObservables(rep) {
    const obs = (rep && Array.isArray(rep.observables) && rep.observables) || [];
    return obs.map((o) => ({
      id: o.id,
      grupo: o.grupo || 'operativa',
      etiqueta: o.etiqueta || o.id,
      pct: o.score != null ? Math.max(0, Math.min(100, Number(o.score))) : 0
    }));
  },

  indiceGlobal(n, rep, indiceValor) {
    if (Number.isFinite(Number(indiceValor))) return Number(indiceValor);
    if (rep && rep.indice_transparencia != null) return Number(rep.indice_transparencia);
    if (n && n.indice_transparencia != null) return Number(n.indice_transparencia);
    const items = IndiceDesglose.factoresDesdeObservables(rep);
    if (!items.length) return 0;
    const avg = items.reduce((a, f) => a + (Number(f.pct) || 0), 0) / items.length;
    return Math.round((avg / 10) * 10) / 10;
  },

  factoresIndice(n, rep, indiceValor, verificado) {
    const items = IndiceDesglose.factoresDesdeObservables(rep);
    const indice = IndiceDesglose.indiceGlobal(n, rep, indiceValor);
    const pct =
      rep && rep.indice_pct != null
        ? Math.round(Number(rep.indice_pct))
        : n && n.indice_pct != null
          ? Math.round(Number(n.indice_pct))
          : Math.max(0, Math.min(100, Math.round(indice * 10)));

    return [
      {
        id: 'rating-global',
        grupo: 'resumen',
        etiqueta: 'Índice de transparencia',
        pct: pct,
        barras: [
          {
            id: 'indice',
            etiqueta: pct + ' / 100',
            pct: pct,
            clase: 'indice-desglose__barra--nucleo'
          }
        ]
      }
    ].concat(items);
  },

  filtrosIndiceGrupos() {
    return IndiceDesglose.FILTROS.slice();
  },

  bloqueDesgloseIndice(n, rep, indiceValor, verificado) {
    const factores = IndiceDesglose.factoresIndice(n, rep, indiceValor, verificado);
    const detalleFactores = factores.filter((f) => f.grupo !== 'resumen');
    const estado = {
      todos: true,
      activos: {
        documentos: false,
        ciber: false,
        contractual: false,
        operativa: false,
        legal: false
      }
    };

    const sec = document.createElement('section');
    sec.className = 'indice-desglose';
    sec.setAttribute('aria-label', 'Desglose del índice global');

    const titulo = document.createElement('h3');
    titulo.className = 'reporte-doc__h indice-desglose__titulo';
    titulo.textContent = 'Por qué este índice';

    const cabecera = document.createElement('div');
    cabecera.className = 'indice-desglose__cabecera';
    factores
      .filter((f) => f.grupo === 'resumen')
      .forEach((f) => {
        const item = IndiceDesglose.itemFactorIndice(f);
        item.classList.add('indice-desglose__item--cabecera');
        cabecera.appendChild(item);
      });

    const lead = document.createElement('p');
    lead.className = 'indice-desglose__lead';
    lead.textContent =
      'Un solo índice: señales públicas y documentos legales verificados.';

    const filtros = document.createElement('div');
    filtros.className = 'indice-desglose__filtros';
    filtros.setAttribute('role', 'group');
    filtros.setAttribute('aria-label', 'Filtros del desglose');

    const lista = document.createElement('ul');
    lista.className = 'indice-desglose__lista';

    const vacio = document.createElement('p');
    vacio.className = 'indice-desglose__vacio';
    vacio.hidden = true;
    vacio.textContent = 'Ningún indicador con los filtros actuales.';

    function gruposActivos() {
      if (estado.todos) return null;
      return Object.keys(estado.activos).filter((k) => estado.activos[k]);
    }

    function limpiar(el) {
      if (typeof Market !== 'undefined' && Market.limpiar) {
        Market.limpiar(el);
        return;
      }
      while (el.firstChild) el.removeChild(el.firstChild);
    }

    function pintarFiltros() {
      limpiar(filtros);
      IndiceDesglose.filtrosIndiceGrupos().forEach((g) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'indice-desglose__filtro';
        btn.textContent = g.etiqueta;
        const on = !estado.todos && !!estado.activos[g.id];
        btn.classList.toggle('indice-desglose__filtro--on', on);
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        btn.addEventListener('click', () => {
          estado.todos = false;
          Object.keys(estado.activos).forEach((k) => {
            estado.activos[k] = false;
          });
          estado.activos[g.id] = true;
          pintarFiltros();
          pintarLista();
        });
        filtros.appendChild(btn);
      });

      const todos = document.createElement('button');
      todos.type = 'button';
      todos.className = 'indice-desglose__filtro indice-desglose__filtro--todos';
      todos.textContent = 'Ver todos';
      todos.classList.toggle('indice-desglose__filtro--on', estado.todos);
      todos.setAttribute('aria-pressed', estado.todos ? 'true' : 'false');
      todos.addEventListener('click', () => {
        estado.todos = true;
        Object.keys(estado.activos).forEach((k) => {
          estado.activos[k] = false;
        });
        pintarFiltros();
        pintarLista();
      });
      filtros.appendChild(todos);
    }

    function pintarLista() {
      limpiar(lista);
      const activos = gruposActivos();
      const visibles = detalleFactores.filter(
        (f) => !activos || activos.indexOf(f.grupo) !== -1
      );
      vacio.hidden = visibles.length > 0;
      visibles.forEach((f) => lista.appendChild(IndiceDesglose.itemFactorIndice(f)));
    }

    pintarFiltros();
    pintarLista();
    sec.append(titulo, cabecera, lead, filtros, vacio, lista);
    return sec;
  },

  itemFactorIndice(f) {
    const li = document.createElement('li');
    li.className = 'indice-desglose__item';

    const cabezal = document.createElement('div');
    cabezal.className = 'indice-desglose__cabezal';
    const nombre = document.createElement('span');
    nombre.className = 'indice-desglose__nombre';
    nombre.textContent = f.etiqueta;
    cabezal.appendChild(nombre);
    if (f.valor) {
      const meta = document.createElement('span');
      meta.className = 'indice-desglose__meta';
      meta.textContent = f.valor + (f.peso ? ' · ' + f.peso : '');
      cabezal.appendChild(meta);
    }
    li.appendChild(cabezal);

    const barras = Array.isArray(f.barras) && f.barras.length ? f.barras : null;
    if (barras) {
      const wrap = document.createElement('div');
      wrap.className = 'indice-desglose__barras';
      barras.forEach((b) => {
        const fila = document.createElement('div');
        fila.className = 'indice-desglose__barra-fila';
        const lab = document.createElement('span');
        lab.className = 'indice-desglose__barra-lab';
        lab.textContent = b.etiqueta || '';
        const pista = document.createElement('div');
        pista.className = 'indice-desglose__pista';
        pista.setAttribute('role', 'meter');
        pista.setAttribute('aria-valuemin', '0');
        pista.setAttribute('aria-valuemax', '100');
        pista.setAttribute('aria-valuenow', String(b.pct || 0));
        pista.setAttribute(
          'aria-label',
          (b.etiqueta || f.etiqueta) + ': ' + (b.pct || 0) + ' por ciento'
        );
        const barra = document.createElement('span');
        barra.className = 'indice-desglose__barra';
        if (b.clase) barra.classList.add(b.clase);
        barra.style.width = Math.max(0, Math.min(100, Number(b.pct) || 0)) + '%';
        pista.appendChild(barra);
        fila.append(lab, pista);
        wrap.appendChild(fila);
      });
      li.appendChild(wrap);
    } else {
      const pista = document.createElement('div');
      pista.className = 'indice-desglose__pista';
      pista.setAttribute('role', 'meter');
      pista.setAttribute('aria-valuemin', '0');
      pista.setAttribute('aria-valuemax', '100');
      pista.setAttribute('aria-valuenow', String(f.pct || 0));
      pista.setAttribute('aria-label', f.etiqueta + ': ' + (f.pct || 0) + ' por ciento');
      const barra = document.createElement('span');
      barra.className = 'indice-desglose__barra';
      if (f.grupo === 'resumen') barra.classList.add('indice-desglose__barra--nucleo');
      if (f.grupo === 'documentos') barra.classList.add('indice-desglose__barra--docs');
      if (f.grupo === 'ciber') barra.classList.add('indice-desglose__barra--ciber');
      if (f.grupo === 'contractual') barra.classList.add('indice-desglose__barra--contractual');
      if (f.grupo === 'operativa') barra.classList.add('indice-desglose__barra--operativa');
      if (f.grupo === 'legal') barra.classList.add('indice-desglose__barra--legal');
      barra.style.width = Math.max(0, Math.min(100, Number(f.pct) || 0)) + '%';
      pista.appendChild(barra);
      li.appendChild(pista);
    }

    if (f.detalle) {
      const detalle = document.createElement('p');
      detalle.className = 'indice-desglose__detalle';
      detalle.textContent = f.detalle;
      li.appendChild(detalle);
    }
    return li;
  }
};

Object.assign(typeof Market !== 'undefined' ? Market : window, IndiceDesglose);
