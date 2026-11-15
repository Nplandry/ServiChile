const IndiceDesglose = {
  definicionObservablesIndice() {
    if (IndiceDesglose._defs) return IndiceDesglose._defs;
    IndiceDesglose._defs = [
      {
        grupo: 'ciber',
        id: 'ssl-tls',
        etiqueta: 'Vigencia y calidad de certificados SSL/TLS'
      },
      {
        grupo: 'ciber',
        id: 'email-auth',
        etiqueta: 'Seguridad de correo y registros DNS'
      },
      {
        grupo: 'ciber',
        id: 'puertos',
        etiqueta: 'Exposición de puertos y servicios críticos'
      },
      {
        grupo: 'ciber',
        id: 'headers-http',
        etiqueta: 'Cabeceras de seguridad HTTP'
      },
      {
        grupo: 'ciber',
        id: 'stack-vulnerable',
        etiqueta: 'Tecnologías web obsoletas o vulnerables'
      },
      {
        grupo: 'ciber',
        id: 'blacklist',
        etiqueta: 'Reputación de IP y dominio en listas negras globales'
      },
      {
        grupo: 'ciber',
        id: 'dnssec',
        etiqueta: 'Protección de infraestructura DNS y secuestro de dominios'
      },
      {
        grupo: 'ciber',
        id: 'subdominios',
        etiqueta: 'Seguridad en subdominios expuestos'
      },
      {
        grupo: 'ciber',
        id: 'whois',
        etiqueta: 'Antigüedad, configuración y estabilidad del dominio'
      },
      {
        grupo: 'legal',
        id: 'persona-juridica',
        etiqueta: 'Vigencia y estado de la persona jurídica'
      },
      {
        grupo: 'legal',
        id: 'sii',
        etiqueta: 'Situación tributaria, cumplimiento y facturación electrónica'
      },
      {
        grupo: 'legal',
        id: 'mercado-publico',
        etiqueta: 'Historial y penalidades en compras públicas / Estado'
      },
      {
        grupo: 'legal',
        id: 'cmf',
        etiqueta: 'Supervisión CMF Bancos'
      },
      {
        grupo: 'contractual',
        id: 'politica-privacidad',
        etiqueta: 'Política de Privacidad accesible e información acerca de la Ley 21.719'
      },
      {
        grupo: 'contractual',
        id: 'cookies',
        etiqueta: 'Consentimiento de cookies y rastreadores'
      },
      {
        grupo: 'contractual',
        id: 'terminos',
        etiqueta: 'Términos y Condiciones públicos de la oferta comercial'
      },
      {
        grupo: 'contractual',
        id: 'sla',
        etiqueta: 'Cláusulas de servicio, SLA y DPA'
      },
      {
        grupo: 'operativa',
        id: 'domicilio',
        etiqueta: 'Verificación de domicilio operativo real y oficinas'
      },
      {
        grupo: 'operativa',
        id: 'huella-digital',
        etiqueta: 'Coherencia y solidez de huella digital y reputación corporativa'
      },
      {
        grupo: 'operativa',
        id: 'incidentes',
        etiqueta: 'Historial de incidentes físicos, brechas o escándalos públicos'
      },
      {
        grupo: 'operativa',
        id: 'uptime',
        etiqueta: 'Continuidad operativa y estabilidad de infraestructura'
      },
      {
        grupo: 'operativa',
        id: 'resenas-reclamos',
        etiqueta: 'Calificación y volumen de reseñas en Google'
      }
    ];
    return IndiceDesglose._defs;
  },

  factoresIndiceMock(n, rep, indiceValor, verificado) {
    const seed = Market.hashTexto(String(n.id || n.nombre || 'negocio'));
    const pct = (base, spread, offset) => {
      const t = ((seed + (offset || 0) * 9973) % 1000) / 1000;
      return Math.max(8, Math.min(98, Math.round(base + t * spread)));
    };
    const boostLegal = verificado ? 18 : 0;
    const boostContract = verificado ? 12 : 0;
    const defs = Market.definicionObservablesIndice();

    const ciberApi = Object.create(null);
    const ciberRazones = Object.create(null);
    const sinRazones = {
      'politica-privacidad': 1,
      cookies: 1,
      terminos: 1,
      sla: 1
    };
    const listaCiber = rep && Array.isArray(rep.observables_ciber) ? rep.observables_ciber : [];
    for (let i = 0; i < listaCiber.length; i++) {
      const o = listaCiber[i];
      if (o && o.id != null && o.score != null) ciberApi[o.id] = Number(o.score);
      if (
        o &&
        o.id != null &&
        !sinRazones[o.id] &&
        Array.isArray(o.razones) &&
        o.razones.length
      ) {
        ciberRazones[o.id] = o.razones.map((r) => String(r)).filter(Boolean);
      }
    }

    const factores = defs.map((d, i) => {
      let score;
      if (ciberApi[d.id] != null && Number.isFinite(ciberApi[d.id])) {
        score = Math.max(0, Math.min(100, Math.round(ciberApi[d.id])));
      } else if (d.id === 'domicilio' || d.id === 'huella-digital') {
        score = 50;
      } else if (d.id === 'persona-juridica') {
        score = 0;
      } else if (d.id === 'resenas-reclamos') {
        score = 20;
      } else {
        let base = 48;
        let spread = 36;
        if (d.grupo === 'ciber') {
          base = 52;
          spread = 38;
        } else if (d.grupo === 'legal') {
          base = 40 + boostLegal;
          spread = 30;
        } else if (d.grupo === 'contractual') {
          base = 42 + boostContract;
          spread = 34;
        } else if (d.grupo === 'operativa') {
          base = 50;
          spread = 32;
        }
        score = pct(base, spread, i + 1);
      }
      return {
        id: d.id,
        grupo: d.grupo,
        etiqueta: d.etiqueta,
        valor: score + ' / 100',
        pct: score,
        detalle: '',
        razones: ciberRazones[d.id] || null
      };
    });

    factores.push({
      id: 'indice',
      grupo: 'resumen',
      etiqueta: 'Índice resultante',
      valor: Number(indiceValor).toFixed(1) + ' / 10',
      pct: Math.round((Number(indiceValor) / 10) * 100)
    });
    return factores;
  },

  filtrosIndiceGrupos() {
    return [
      { id: 'ciber', etiqueta: 'Ciberseguridad (9)' },
      { id: 'legal', etiqueta: 'Legal y regulatoria (4)' },
      { id: 'contractual', etiqueta: 'Contractual y datos (4)' },
      { id: 'operativa', etiqueta: 'Física y reputacional (5)' }
    ];
  },

  hashTexto(texto) {
    let h = 2166136261;
    const s = String(texto || '');
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  },

  bloqueDesgloseIndice(n, rep, indiceValor, verificado, opts) {
    const opciones = opts && typeof opts === 'object' ? opts : {};
    const factores = Market.factoresIndiceMock(n, rep, indiceValor, verificado);
    const resumen = factores.find((f) => f.grupo === 'resumen');
    const detalleFactores = factores.filter((f) => f.grupo !== 'resumen');

    const estado = {
      todos: false,
      activos: { ciber: true, legal: false, contractual: false, operativa: false }
    };

    const sec = document.createElement('section');
    sec.className = 'indice-desglose';
    sec.setAttribute('aria-label', 'Desglose del índice de transparencia');

    const titulo = document.createElement('h3');
    titulo.className = 'market-detalle__subtitulo';
    titulo.textContent = 'Desglose del índice';

    const cabecera = document.createElement('div');
    cabecera.className = 'indice-desglose__cabecera';
    if (resumen) {
      const item = Market.itemFactorIndice(resumen, opciones);
      item.classList.add('indice-desglose__item--cabecera');
      cabecera.appendChild(item);
    }

    const filtros = document.createElement('div');
    filtros.className = 'indice-desglose__filtros';
    filtros.setAttribute('role', 'group');
    filtros.setAttribute('aria-label', 'Filtros del desglose');

    const lista = document.createElement('ul');
    lista.className = 'indice-desglose__lista';

    const vacio = document.createElement('p');
    vacio.className = 'indice-desglose__vacio';
    vacio.hidden = true;
    vacio.textContent = 'Ningún factor con los filtros actuales. Active un grupo o pulse Ver todos.';

    function gruposActivos() {
      if (estado.todos) return null;
      return Object.keys(estado.activos).filter((k) => estado.activos[k]);
    }

    function pintarFiltros() {
      Market.limpiar(filtros);
      Market.filtrosIndiceGrupos().forEach((g) => {
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
      Market.limpiar(lista);
      const activos = gruposActivos();
      const visibles = detalleFactores.filter((f) => !activos || activos.indexOf(f.grupo) !== -1);
      vacio.hidden = visibles.length > 0;
      visibles.forEach((f) => lista.appendChild(Market.itemFactorIndice(f, opciones)));
    }

    pintarFiltros();
    pintarLista();
    sec.append(titulo, cabecera, filtros, vacio, lista);
    return sec;
  },

  itemFactorIndice(f, opts) {
    const opciones = opts && typeof opts === 'object' ? opts : {};
    const li = document.createElement('li');
    li.className = 'indice-desglose__item';

    const cabezal = document.createElement('div');
    cabezal.className = 'indice-desglose__cabezal';
    const nombre = document.createElement('span');
    nombre.className = 'indice-desglose__nombre';
    nombre.textContent = f.etiqueta;
    const meta = document.createElement('span');
    meta.className = 'indice-desglose__meta';
    meta.textContent = f.valor;
    cabezal.append(nombre, meta);

    const pista = document.createElement('div');
    pista.className = 'indice-desglose__pista';
    pista.setAttribute('role', 'meter');
    pista.setAttribute('aria-valuemin', '0');
    pista.setAttribute('aria-valuemax', '100');
    pista.setAttribute('aria-valuenow', String(f.pct));
    pista.setAttribute('aria-label', f.etiqueta + ': ' + f.pct + ' por ciento');
    const barra = document.createElement('span');
    barra.className = 'indice-desglose__barra';
    if (f.grupo === 'ciber') barra.classList.add('indice-desglose__barra--ciber');
    if (f.grupo === 'legal') barra.classList.add('indice-desglose__barra--legal');
    if (f.grupo === 'contractual') barra.classList.add('indice-desglose__barra--contractual');
    if (f.grupo === 'operativa') barra.classList.add('indice-desglose__barra--operativa');
    if (f.grupo === 'resumen') barra.classList.add('indice-desglose__barra--nucleo');
    barra.style.width = f.pct + '%';
    pista.appendChild(barra);

    li.append(cabezal, pista);
    if (f.detalle) {
      const detalle = document.createElement('p');
      detalle.className = 'indice-desglose__detalle';
      detalle.textContent = f.detalle;
      li.appendChild(detalle);
    }

    if (opciones.mostrarRazones && Array.isArray(f.razones) && f.razones.length) {
      const ul = document.createElement('ul');
      ul.className = 'indice-desglose__razones';
      if (f.id === 'incidentes') ul.classList.add('indice-desglose__razones--incidentes');
      if (f.id === 'resenas-reclamos') ul.classList.add('indice-desglose__razones--resenas');
      for (let i = 0; i < f.razones.length; i++) {
        const texto = String(f.razones[i] || '');
        const liR = document.createElement('li');
        const bajo = texto.toLowerCase();
        if (bajo.indexOf('severo:') === 0) {
          liR.className = 'indice-desglose__razon indice-desglose__razon--severo';
          const tag = document.createElement('span');
          tag.className = 'indice-desglose__razon-tag';
          tag.textContent = 'Severo';
          const cuerpo = document.createElement('span');
          cuerpo.className = 'indice-desglose__razon-texto';
          cuerpo.textContent = texto.replace(/^Severo:\s*/i, '');
          liR.append(tag, cuerpo);
        } else if (bajo.indexOf('hallazgo:') === 0) {
          liR.className = 'indice-desglose__razon indice-desglose__razon--hallazgo';
          const tag = document.createElement('span');
          tag.className = 'indice-desglose__razon-tag';
          tag.textContent = 'Hallazgo';
          const cuerpo = document.createElement('span');
          cuerpo.className = 'indice-desglose__razon-texto';
          cuerpo.textContent = texto.replace(/^Hallazgo:\s*/i, '');
          liR.append(tag, cuerpo);
        } else if (f.id === 'resenas-reclamos') {
          liR.className = 'indice-desglose__razon indice-desglose__razon--dato';
          liR.textContent = texto;
        } else {
          liR.className = 'indice-desglose__razon indice-desglose__razon--ok';
          liR.textContent = texto;
        }
        ul.appendChild(liR);
      }
      li.appendChild(ul);
    }
    return li;
  },

};

Object.assign(Market, IndiceDesglose);
