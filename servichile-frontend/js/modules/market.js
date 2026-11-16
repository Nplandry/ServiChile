

const Market = {
  CATEGORIAS: [
    { id: 'tecnologia', label: 'Tecnología y datos' },
    { id: 'industria', label: 'Minería e industria' },
    { id: 'construccion', label: 'Construcción' },
    { id: 'servicios-profesionales', label: 'Servicios profesionales' },
    {
      id: 'logistica',
      label: 'Transporte, Logística y Última Milla'
    },
    { id: 'all', label: 'Todos' }
  ],
  JOBS: [
    {
      id: 'tecnologia',
      label: 'Tecnología',
      hint: 'SaaS · TI · agencias',
      categoria: 'tecnologia'
    },
    {
      id: 'industria',
      label: 'Industria',
      hint: 'Minería · faenas',
      categoria: 'industria'
    },
    {
      id: 'construccion',
      label: 'Construcción',
      hint: 'Obras · montaje',
      categoria: 'construccion'
    },
    {
      id: 'profesionales',
      label: 'Profesionales',
      hint: 'RR.HH. · legal',
      categoria: 'servicios-profesionales'
    },
    {
      id: 'logistica',
      label: 'Logística',
      hint: 'Flotas · courier · bodega',
      categoria: 'logistica'
    }
  ],
  REF_DEFECTO: { lat: -33.4265, lng: -70.6190 },

  negocios: [],
  categoria: 'tecnologia',
  job: 'tecnologia',
  busqueda: '',
  ref: null,
  timer: null,
  seleccionado: null,
  _reps: Object.create(null),
  _detalleGen: 0,
  _cargaTicket: 0,

  init() {
    Market.el = {
      list: document.getElementById('marketList'),
      detail: document.getElementById('marketDetail'),
      search: document.getElementById('marketSearch'),
      count: document.getElementById('marketCount'),
      grid: document.getElementById('marketGrid'),
      status: document.getElementById('marketStatus'),
      progreso: document.getElementById('marketProgreso'),
      jobs: document.getElementById('marketJobs')
    };
    if (!Market.el.grid) return;
    if (!Market.el.bound) {
      Market.el.search.addEventListener('input', Market.onBuscar);
      Market.el.grid.addEventListener('click', Market.onGridClick);
      Market.el.grid.addEventListener('keydown', Market.onGridKey);
      Market.el.bound = true;
    }
    Market.cerrarDetalle();
    Market.renderJobs();
    Market.renderProgreso();
    Market.pedirUbicacion();
    Market.cargar();
  },

  renderJobs() {
    if (!Market.el.jobs) return;
    Market.limpiar(Market.el.jobs);

    Market.JOBS.forEach((job) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className =
        'market__job' + (Market.job === job.id ? ' market__job--activo' : '');
      const titulo = document.createElement('span');
      titulo.className = 'market__job-label';
      titulo.textContent = job.label;
      const hint = document.createElement('span');
      hint.className = 'market__job-hint';
      hint.textContent = job.hint;
      btn.append(titulo, hint);
      btn.addEventListener('click', () => {
        Market.job = job.id;
        Market.categoria = job.categoria;
        Market.renderJobs();
        Market.renderAccionEmpresa();
        Market.cargar();
      });
      Market.el.jobs.appendChild(btn);
    });
    Market.renderAccionEmpresa();
  },

  esProveedor() {
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.esProveedor()
      : false;
  },

  esEmpresa() {
    return Market.esProveedor();
  },

  async asegurarEmpresas() {
    if (!Market.esProveedor()) return false;
    if (typeof SubirConfianza === 'undefined' && typeof Carga !== 'undefined') {
      await Carga.script('js/modules/subir-confianza.js?v=88');
    }
    if (typeof SubirConfianza === 'undefined') return false;
    if (!Array.isArray(SubirConfianza.empresas)) {
      await SubirConfianza.cargarEmpresas();
    }
    return SubirConfianza.tieneEmpresa();
  },

  async renderAccionEmpresa() {
    if (!Market.el.list) return;
    let barra = document.getElementById('marketEmpresaAccion');
    if (!Market.esProveedor()) {
      if (barra) barra.remove();
      return;
    }

    const tieneEmpresa = await Market.asegurarEmpresas();
    const sinFicha = !tieneEmpresa;

    if (!barra) {
      barra = document.createElement('div');
      barra.id = 'marketEmpresaAccion';
      barra.className = 'market__empresa-accion';

      const texto = document.createElement('p');
      texto.className = 'market__empresa-accion-texto';

      const cta = document.createElement('button');
      cta.type = 'button';
      cta.className = 'submit-btn market__empresa-accion-cta';

      barra.append(texto, cta);

      const search = Market.el.search && Market.el.search.closest
        ? Market.el.search.closest('.market__search') || Market.el.search
        : Market.el.search;
      const head = Market.el.list.querySelector('.market__head');
      if (head && search && search.parentNode === head) {
        head.insertBefore(barra, search);
      } else if (head) {
        head.appendChild(barra);
      } else {
        Market.el.list.insertBefore(barra, Market.el.list.firstChild);
      }
    }

    const texto = barra.querySelector('.market__empresa-accion-texto');
    const cta = barra.querySelector('.market__empresa-accion-cta');
    if (!texto || !cta) return;

    const ctaNuevo = cta.cloneNode(true);
    cta.parentNode.replaceChild(ctaNuevo, cta);

    if (sinFicha) {
      barra.classList.add('market__empresa-accion--crear');
      texto.textContent =
        'Aún no tiene una empresa publicada. Créela en Perfil para aparecer en Explorar y obtener su índice de transparencia.';
      ctaNuevo.textContent = 'Crear mi empresa';
      ctaNuevo.addEventListener('click', () => {
        if (typeof App !== 'undefined' && App.openSection) App.openSection('perfil');
        setTimeout(() => {
          const el = document.getElementById('perfilEmpresaRaiz');
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 80);
      });
      return;
    }

    barra.classList.remove('market__empresa-accion--crear');
    texto.textContent =
      '¿Es proveedor B2B? Mejore su índice de transparencia para no quedar fuera del filtro.';
    ctaNuevo.textContent = 'Mejorar mi nota';
    ctaNuevo.addEventListener('click', () => {
      if (typeof App !== 'undefined' && App.openSection) App.openSection('subir-confianza');
    });
  },

  async renderProgreso() {
    if (!Market.el.progreso || typeof ProgresoCuenta === 'undefined') return;
    if (Market.esProveedor()) {
      const tieneEmpresa = await Market.asegurarEmpresas();
      if (!tieneEmpresa) {
        Market.el.progreso.hidden = true;
        while (Market.el.progreso.firstChild) {
          Market.el.progreso.removeChild(Market.el.progreso.firstChild);
        }
        return;
      }
    }
    ProgresoCuenta.actual().montarIndicador(Market.el.progreso, {
      onAbrir: () => {
        if (typeof App !== 'undefined' && App.openSection) App.openSection('subir-confianza');
      }
    });
  },

  pedirUbicacion() {
    if (Market.ref || !navigator.geolocation) {
      Market.ref = Market.ref || Market.REF_DEFECTO;
      return;
    }
    Market.ref = Market.REF_DEFECTO;
    navigator.geolocation.getCurrentPosition(
      pos => {
        Market.ref = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        if (Market.negocios.length) Market.render();
      },
      () => {}
    );
  },

  onBuscar() {
    Market.busqueda = Market.el.search.value.trim();
    clearTimeout(Market.timer);
    Market.timer = setTimeout(Market.cargar, 250);
  },

  jobActual() {
    return Market.JOBS.find((j) => j.id === Market.job) || null;
  },

  filtrarPorJob(lista) {
    const job = Market.jobActual();
    const excluir = job && Array.isArray(job.excluir) ? job.excluir : [];
    if (!excluir.length) return lista;
    return lista.filter((n) => excluir.indexOf(n.categoria) === -1);
  },

  onGridClick(e) {
    const card = e.target.closest('[data-business-id]');
    if (!card) return;
    const n = Market.porId(card.dataset.businessId);
    if (n) Market.abrirDetalle(n);
  },

  onGridKey(e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const card = e.target.closest('[data-business-id]');
    if (!card) return;
    e.preventDefault();
    const n = Market.porId(card.dataset.businessId);
    if (n) Market.abrirDetalle(n);
  },

  porId(id) {
    return Market._porId ? Market._porId[String(id)] || null : null;
  },

  async cargar() {
    const params = new URLSearchParams();
    if (Market.categoria !== 'all') params.set('categoria', Market.categoria);
    if (Market.busqueda) params.set('q', Market.busqueda);
    const clave = params.toString();
    const ticket = ++Market._cargaTicket;
    const previa = Market._cache && Market._cache.clave === clave ? Market._cache.lista : null;
    if (previa) {
      Market.negocios = previa;
      Market.el.status.textContent = '';
      Market.render();
    } else {
      Market.el.status.textContent = 'Cargando...';
    }
    const res = await Auth.request('/v1/businesses' + (clave ? '?' + clave : ''));
    if (ticket !== Market._cargaTicket) return;
    if (!res.ok) {
      if (!previa) {
        Market.el.status.textContent = 'No se pudieron cargar los lugares. Intente de nuevo.';
      }
      return;
    }
    Market.el.status.textContent = '';
    Market.negocios = Market.filtrarPorJob(Array.isArray(res.data) ? res.data : []);
    Market._cache = { clave: clave, lista: Market.negocios };
    Market._firma = '';
    Market.render();
  },

  render() {
    const lista = Market.ordenarPorCercania(Market.negocios);
    const ref = Market.ref || Market.REF_DEFECTO;
    const firma =
      lista.map((n) => n.id).join('|') +
      '@' +
      ref.lat.toFixed(3) +
      ',' +
      ref.lng.toFixed(3);
    Market.el.count.textContent =
      lista.length + ' proveedor' + (lista.length === 1 ? '' : 'es');
    if (firma === Market._firma && Market.el.grid.childElementCount) return;
    Market._firma = firma;
    Market._porId = Object.create(null);
    const frag = document.createDocumentFragment();
    if (lista.length === 0) {
      const vacio = document.createElement('p');
      vacio.className = 'market__vacio';
      vacio.textContent = 'No se encontraron resultados para esta búsqueda.';
      frag.appendChild(vacio);
    } else {
      for (let i = 0; i < lista.length; i++) {
        Market._porId[String(lista[i].id)] = lista[i];
        frag.appendChild(Market.tarjeta(lista[i]));
      }
    }
    Market.limpiar(Market.el.grid);
    Market.el.grid.appendChild(frag);
  },

  tarjeta(n) {
    const bloqueado = Market.estaBloqueado(n);
    const card = document.createElement('article');
    card.className = 'market__card market__card--click' + (bloqueado ? ' market__card--nivel' : '');
    card.dataset.businessId = String(n.id);
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute(
      'aria-label',
      bloqueado
        ? n.nombre + '. Pide nivel ' + (n.requiere_nivel || 1)
        : 'Ver detalle de ' + n.nombre
    );
    const media = document.createElement('div');
    media.className = 'market__media';

    const foto = document.createElement('img');
    foto.className = 'market__foto';
    if (n.imagen_url) {
      foto.src = n.imagen_url;
      foto.width = 480;
      foto.height = 300;
    }
    foto.alt = '';
    foto.loading = 'lazy';
    foto.decoding = 'async';
    foto.fetchPriority = 'low';

    const top = document.createElement('div');
    top.className = 'market__card-top';
    top.append(Market.chipCategoria(n), Market.logoMarca(n));
    media.append(foto, top);

    const cuerpo = document.createElement('div');
    cuerpo.className = 'market__card-body';

    const nombre = document.createElement('h3');
    nombre.className = 'market__card-nombre';
    nombre.textContent = n.nombre;

    const dir = document.createElement('p');
    dir.className = 'market__card-dir';
    dir.textContent = Market.textoDireccion(n);

    const desc = document.createElement('p');
    desc.className = 'market__card-desc';
    desc.textContent = n.descripcion || '';

    const pie = document.createElement('div');
    pie.className = 'market__card-pie';
    pie.append(
      Market.bloqueIndice(n),
      ...(bloqueado ? [Market.avisoNivel(n)] : [])
    );

    cuerpo.append(nombre, dir, desc, pie);
    card.append(media, cuerpo);
    return card;
  },

  async abrirDetalle(n) {
    const id = String(n.id);
    const gen = ++Market._detalleGen;
    const previa = Market._reps[id];
    if (previa) Market.pintarDetalle(n, previa);
    const res = await Auth.request('/v1/businesses/' + encodeURIComponent(n.id) + '/reputation');
    if (gen !== Market._detalleGen) return;
    if (!res.ok) return;
    Market._reps[id] = res.data;
    if (previa && JSON.stringify(previa) === JSON.stringify(res.data)) return;
    Market.pintarDetalle(n, res.data);
  },

  pintarDetalle(n, reputacion) {
    Market.seleccionado = n;
    if (Market.el.list) Market.el.list.hidden = true;
    if (Market.el.detail) {
      Market.el.detail.hidden = false;
      Market.renderDetalle(n, { reputacion: reputacion });
    }
    window.scrollTo(0, 0);
  },

  cerrarDetalle() {
    Market._detalleGen += 1;
    Market.seleccionado = null;
    if (Market.el.list) Market.el.list.hidden = false;
    if (Market.el.detail) {
      Market.el.detail.hidden = true;
      Market.limpiar(Market.el.detail);
    }
  },

  renderDetalle(n, extras) {
    const raiz = Market.el.detail;
    Market.limpiar(raiz);
    const bloqueado = Market.estaBloqueado(n);
    const pide = n.requiere_nivel || 1;
    const rep = extras && extras.reputacion ? extras.reputacion : null;
    const indiceValor = rep && rep.indice_transparencia != null
      ? rep.indice_transparencia
      : n.indice_transparencia;

    const volver = document.createElement('button');
    volver.type = 'button';
    volver.className = 'market-detalle__volver';
    volver.textContent = 'Volver al marketplace';
    volver.addEventListener('click', Market.cerrarDetalle);

    const media = document.createElement('div');
    media.className = 'market-detalle__media';
    const foto = document.createElement('img');
    foto.className = 'market-detalle__foto';
    foto.src = n.imagen_url || '';
    foto.alt = n.nombre;
    media.appendChild(foto);

    const chips = document.createElement('div');
    chips.className = 'market-detalle__chips';
    if (bloqueado) {
      chips.append(Market.logoMarca(n), Market.chipCategoria(n), Market.avisoNivel(n));
    } else {
      chips.append(Market.logoMarca(n), Market.chipCategoria(n));
    }

    const nombre = document.createElement('h2');
    nombre.className = 'section-heading';
    nombre.textContent = n.nombre;

    const dir = document.createElement('p');
    dir.className = 'market-detalle__dir';
    dir.textContent = Market.textoDireccion(n);

    raiz.append(volver, media, chips, nombre, dir);

    if (bloqueado) {
      const aviso = document.createElement('p');
      aviso.className = 'market-detalle__aviso-nivel';
      aviso.textContent = Market.textoAvisoNivel(n, pide);
      raiz.appendChild(aviso);
    }

    if (extras && extras.error) {
      const err = document.createElement('p');
      err.className = 'error-text';
      err.textContent = extras.error;
      raiz.appendChild(err);
    }

    const pctValor =
      rep && rep.indice_pct != null
        ? Number(rep.indice_pct)
        : n.indice_pct != null
          ? Number(n.indice_pct)
          : Math.round((Number(indiceValor) / 10) * 100);
    const negocioIndice = Object.assign({}, n, {
      indice_transparencia: indiceValor,
      indice_pct: pctValor
    });

    const cuerpo = document.createElement('div');
    cuerpo.className = 'market-detalle__cuerpo';

    const colIzq = document.createElement('div');
    colIzq.className = 'market-detalle__col';

    const filas = [
      ['Descripción', n.descripcion || 'Sin descripción por ahora.'],
      ['Categoría', Market.etiquetaDe(n.categoria)],
      ['Dirección', n.direccion || 'Sin dirección'],
      ['Distancia', Market.distanciaTexto(n) || 'No disponible'],
      ['Nivel pedido', 'Nivel ' + pide]
    ];
    if (rep) {
      filas.push(
        [
          'Nota Google',
          rep.google_rating_avg != null
            ? Number(rep.google_rating_avg).toFixed(1) + ' de 5'
            : 'Sin nota'
        ],
        ['Reseñas', String(rep.google_reviews_count || 0)]
      );
    }

    const datos = document.createElement('dl');
    datos.className = 'market-detalle__datos';
    filas.forEach(([k, v]) => {
      const fila = document.createElement('div');
      fila.className = 'market-detalle__fila';
      const dt = document.createElement('dt');
      dt.textContent = k;
      const dd = document.createElement('dd');
      dd.textContent = v;
      fila.append(dt, dd);
      datos.appendChild(fila);
    });
    colIzq.appendChild(datos);

    colIzq.appendChild(Market.bloqueIndice(negocioIndice, true));
    const nDocs = Object.assign({}, n, {
      indice_pct: pctValor,
      docs_empresa:
        (rep && rep.docs_empresa) || n.docs_empresa || null
    });
    const desglose = Market.bloqueDesgloseIndice(nDocs, rep, indiceValor, false);
    if (desglose) colIzq.appendChild(desglose);

    const colDer = document.createElement('div');
    colDer.className = 'market-detalle__col market-detalle__col--paywall';
    const sticky = document.createElement('div');
    sticky.className = 'market-detalle__sticky';
    if (typeof MarketMonetizacion !== 'undefined') {
      sticky.appendChild(MarketMonetizacion.panel(n));
    }

    const estado = document.createElement('p');
    estado.id = 'marketDetalleStatus';
    estado.className = 'status-text market-detalle__cta-status';
    estado.setAttribute('aria-live', 'polite');

    const cta = document.createElement('button');
    cta.type = 'button';
    cta.id = 'marketDetalleCta';
    cta.className =
      'market-detalle__cta-contacto' + (bloqueado ? ' market-detalle__cta-contacto--bloqueado' : '');
    if (bloqueado) {
      cta.textContent = Market.textoCtaBloqueado(n, pide);
    } else {
      const ctaLabel = document.createElement('span');
      ctaLabel.className = 'market-detalle__cta-label';
      ctaLabel.textContent = 'Contactar a esta empresa';
      const ctaHint = document.createElement('span');
      ctaHint.className = 'market-detalle__cta-hint';
      ctaHint.textContent = 'Pedir cotización · respuesta rápida';
      cta.append(ctaLabel, ctaHint);
    }
    cta.addEventListener('click', () => Market.accion(n, bloqueado, cta, estado));

    const tipQr = document.createElement('p');
    tipQr.className = 'market-detalle__tip-qr';
    tipQr.textContent =
      'Use el QR del reporte para verificar identidad en terreno, entregas o reuniones de due diligence.';

    sticky.append(cta, estado, tipQr);
    colDer.appendChild(sticky);
    cuerpo.append(colIzq, colDer);
    raiz.appendChild(cuerpo);
  },

  textoAvisoNivel(n, pide) {
    return (
      'Este proveedor pide verificación nivel ' +
      pide +
      '. Complete su verificación y vuelva a la ficha.'
    );
  },

  textoCtaBloqueado(n, pide) {
    return 'Completar verificación (nivel ' + pide + ')';
  },

  estaBloqueado(n) {
    return (n.requiere_nivel || 1) > Market.nivelUsuario();
  },

  avisoNivel(n) {
    const aviso = document.createElement('span');
    aviso.className = 'market__nivel';
    aviso.textContent = 'Pide nivel ' + (n.requiere_nivel || 1);
    return aviso;
  },

  chipCategoria(n) {
    const cat = document.createElement('span');
    cat.className = 'market__chip';
    const icono = document.createElement('span');
    icono.className = 'market__icono';
    icono.innerHTML = ICONOS_SVG[ICONO_NEGOCIO[n.categoria] || 'pin'];
    const catLbl = document.createElement('span');
    catLbl.textContent = Market.etiquetaDe(n.categoria);
    cat.append(icono, catLbl);
    return cat;
  },

  logoMarca(n) {
    if (n.logo_url) {
      const img = document.createElement('img');
      img.className = 'market__logo market__logo--img';
      img.src = n.logo_url;
      img.alt = n.nombre;
      img.loading = 'lazy';
      return img;
    }
    const logo = document.createElement('span');
    logo.className = 'market__logo';
    logo.setAttribute('aria-hidden', 'true');
    logo.textContent = n.logo_texto || 'S';
    logo.title = n.nombre;
    return logo;
  },

  bloqueIndice(n, grande) {
    const score = document.createElement('div');
    score.className = 'market__card-score' + (grande ? ' market__card-score--detalle' : '');
    const num = document.createElement('strong');
    const indice = Number(n.indice_transparencia);
    num.textContent = '★ ' + (Number.isFinite(indice) ? indice.toFixed(1) : '0.0');
    const lbl = document.createElement('span');
    lbl.className = 'market__card-score-lbl';
    lbl.textContent = ' Índice global';
    score.append(num, lbl);
    return score;
  },

  textoDireccion(n) {
    const dist = Market.distanciaTexto(n);
    return n.direccion + (dist ? ' · ' + dist : '');
  },

  ordenarPorCercania(negocios) {
    const ref = Market.ref || Market.REF_DEFECTO;
    return negocios
      .map(n => ({ n, d: Market.distanciaKm(n, ref) }))
      .sort((a, b) => (a.d ?? Infinity) - (b.d ?? Infinity))
      .map(x => x.n);
  },

  distanciaKm(n, ref) {
    if (n.latitud == null || n.longitud == null) return null;
    const R = 6371;
    const dLat = (n.latitud - ref.lat) * Math.PI / 180;
    const dLng = (n.longitud - ref.lng) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
      Math.cos(ref.lat * Math.PI / 180) * Math.cos(n.latitud * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  },

  distanciaTexto(n) {
    const d = Market.distanciaKm(n, Market.ref || Market.REF_DEFECTO);
    if (d == null) return '';
    return d < 1 ? Math.round(d * 1000) + ' m' : d.toFixed(1) + ' km';
  },

  async accion(n, bloqueado, boton, estadoEl) {
    if (bloqueado) {
      App.openSection('subir-confianza');
      return;
    }
    if (typeof MarketMonetizacion !== 'undefined') {
      MarketMonetizacion.interceptarContacto(n, estadoEl);
      return;
    }
    if (estadoEl) estadoEl.textContent = 'Módulo de contacto no disponible.';
  },

  nivelUsuario() {
    const sesion = Auth.getCurrentUser();
    return sesion && sesion.perfil ? (sesion.perfil.nivel_pasaporte || 1) : 1;
  },

  etiquetaDe(cat) {
    const c = Market.CATEGORIAS.find(x => x.id === cat);
    return c ? c.label : cat;
  },

  textoCta(n) {
    if (n.cta_texto) return n.cta_texto;
    return 'Ver ficha';
  },

  limpiar(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }
};
