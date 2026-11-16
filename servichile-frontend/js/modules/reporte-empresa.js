
const ReporteEmpresa = {
  async init() {
    const raiz = document.getElementById('reporteRaiz');
    if (!raiz) return;
    if (typeof ReporteQr !== 'undefined') {
      if (ReporteQr.cerrarModalValidador) ReporteQr.cerrarModalValidador();
      if (ReporteQr.detenerCamara) ReporteQr.detenerCamara();
    }
    if (typeof SubirConfianza !== 'undefined' && SubirConfianza.cargar) {
      SubirConfianza.cargar();
    }
    const estado = await ReporteEmpresa.cargarEstadoNegocio();
    while (raiz.firstChild) raiz.removeChild(raiz.firstChild);
    raiz.appendChild(ReporteEmpresa.render(estado));
  },

  async cargarEstadoNegocio() {
    if (typeof Auth === 'undefined' || !Auth.isAuthenticated() || !Auth.request) {
      return { sinFicha: true, rep: null };
    }
    try {
      const mias = await Auth.request('/v1/businesses/mias', { token: Auth.sesion.token });
      const lista = mias && Array.isArray(mias.data) ? mias.data : [];
      if (!lista.length) return { sinFicha: true, rep: null };
      const negocio = lista[0];
      const res = await Auth.request(
        '/v1/businesses/' + encodeURIComponent(negocio.id) + '/reputation',
        { token: Auth.sesion.token }
      );
      if (typeof SubirConfianza !== 'undefined') {
        SubirConfianza.empresas = lista;
        if (res && res.ok && res.data) SubirConfianza.reputacionMia = res.data;
      }
      return {
        sinFicha: false,
        rep: res && res.data ? res.data : null,
        negocio: negocio
      };
    } catch (_e) {
      return { sinFicha: true, rep: null, negocio: null };
    }
  },

  etiquetaCategoria(id) {
    if (typeof Market !== 'undefined' && Array.isArray(Market.CATEGORIAS)) {
      const hit = Market.CATEGORIAS.find((c) => c.id === id);
      if (hit && hit.label) return hit.label;
    }
    return id || '—';
  },

  textoOpcional(valor, vacio) {
    const t = valor != null ? String(valor).trim() : '';
    return t || vacio || 'Sin registrar';
  },

  irAComprarFicha() {
    if (typeof App !== 'undefined' && App.openSection) {
      App.openSection('perfil');
    } else if (typeof App !== 'undefined' && App.showView) {
      if (typeof PerfilEmpresa !== 'undefined') PerfilEmpresa.init();
      App.showView('perfilView');
    }
    setTimeout(() => {
      const el = document.getElementById('perfilEmpresaRaiz');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  },

  usuario() {
    return typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
  },

  perfil() {
    const u = ReporteEmpresa.usuario();
    return (u && u.perfil) || {};
  },

  ficha() {
    if (typeof ProgresoCuenta !== 'undefined') {
      return ProgresoCuenta.de('proveedor').calcularFicha();
    }
    const user = ReporteEmpresa.usuario() || {};
    return {
      id: 'empresa:' + (user.email || 'local'),
      nombre: user.nombre || 'Mi empresa',
      indice_transparencia: 4.2,
      _docsCargados: 0
    };
  },

  render(estado) {
    const info = estado && typeof estado === 'object' ? estado : { sinFicha: !estado, rep: estado || null };
    const wrap = document.createElement('div');
    wrap.className = 'reporte';

    if (info.sinFicha) {
      wrap.append(
        ReporteEmpresa.renderAvisoSinFicha(),
        ReporteEmpresa.renderAccionesBasicas(),
        typeof ReporteQr !== 'undefined'
          ? ReporteQr.renderModalValidador()
          : document.createComment('sin-modal-qr')
      );
      return wrap;
    }

    const lead = document.createElement('p');
    lead.className = 'section-lead reporte__lead no-print';
    lead.textContent =
      'Consulte su índice de transparencia, muestre su QR y valide el de otra parte. Puede imprimir o guardar el informe en PDF.';

    const acciones = document.createElement('div');
    acciones.className = 'reporte__acciones no-print';

    const btnPdf = document.createElement('button');
    btnPdf.type = 'button';
    btnPdf.className = 'submit-btn';
    btnPdf.textContent = 'Imprimir o guardar PDF';
    btnPdf.addEventListener('click', () => ReporteEmpresa.imprimir());

    const btnQr = document.createElement('button');
    btnQr.type = 'button';
    btnQr.className = 'submit-btn submit-btn--secondary';
    btnQr.textContent = 'Validar QR';
    btnQr.addEventListener('click', () => {
      if (typeof ReporteQr !== 'undefined') ReporteQr.abrirModalValidador();
    });

    acciones.append(btnPdf, btnQr);

    const doc = ReporteEmpresa.renderDocumento(info.rep || null, info.negocio || null);

    const pieAcciones = document.createElement('div');
    pieAcciones.className = 'reporte__acciones reporte__acciones--pie no-print';
    const btnAct = document.createElement('button');
    btnAct.type = 'button';
    btnAct.className = 'history__clear';
    btnAct.textContent = 'Actualizar datos';
    btnAct.addEventListener('click', () => ReporteEmpresa.init());
    pieAcciones.appendChild(btnAct);

    const modal =
      typeof ReporteQr !== 'undefined'
        ? ReporteQr.renderModalValidador()
        : document.createComment('sin-modal-qr');

    wrap.append(lead, acciones, doc, pieAcciones, modal);
    setTimeout(() => ReporteEmpresa.cargarQrInforme(), 0);
    return wrap;
  },

  renderAvisoSinFicha() {
    const box = document.createElement('section');
    box.className = 'reporte-sin-ficha no-print';
    box.setAttribute('aria-label', 'Sin ficha de empresa');

    const titulo = document.createElement('h2');
    titulo.className = 'section-heading';
    titulo.textContent = 'Aún no tiene una ficha de empresa';

    const lead = document.createElement('p');
    lead.className = 'section-lead';
    lead.textContent =
      'Para generar su reporte de transparencia debe crear su empresa. En Perfil puede publicar una ficha nueva, asociada a su cuenta.';

    const lista = document.createElement('ul');
    lista.className = 'reporte-sin-ficha__lista';
    [
      'Crear y publicar ficha de empresa',
      'La ficha queda a nombre de quien la crea',
      'Sin ficha activa no aparece ante compradores en Explorar'
    ].forEach((t) => {
      const li = document.createElement('li');
      li.textContent = t;
      lista.appendChild(li);
    });

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'submit-btn';
    btn.textContent = 'Ir a Perfil a crear la empresa';
    btn.addEventListener('click', () => ReporteEmpresa.irAComprarFicha());

    box.append(titulo, lead, lista, btn);
    return box;
  },

  renderAccionesBasicas() {
    const acciones = document.createElement('div');
    acciones.className = 'reporte__acciones no-print';
    const btnQr = document.createElement('button');
    btnQr.type = 'button';
    btnQr.className = 'submit-btn submit-btn--secondary';
    btnQr.textContent = 'Validar QR de otra parte';
    btnQr.addEventListener('click', () => {
      if (typeof ReporteQr !== 'undefined') ReporteQr.abrirModalValidador();
    });
    acciones.appendChild(btnQr);
    return acciones;
  },

  renderDocumento(rep, negocio) {
    const user = ReporteEmpresa.usuario() || {};
    const ficha = ReporteEmpresa.ficha();
    const emp =
      negocio ||
      (typeof SubirConfianza !== 'undefined' && SubirConfianza.empresaActual
        ? SubirConfianza.empresaActual()
        : null) ||
      {};
    const indice =
      rep && rep.indice_transparencia != null
        ? Number(rep.indice_transparencia)
        : Number(ficha.indice_transparencia) || 0;

    const doc = document.createElement('article');
    doc.className = 'reporte-doc reporte-doc--empresa';
    doc.id = 'reporteDocumento';
    doc.setAttribute('aria-label', 'Reporte de transparencia ServiChile');

    const cabezal = document.createElement('header');
    cabezal.className = 'reporte-doc__cabezal';

    const marca = document.createElement('div');
    marca.className = 'reporte-doc__marca';
    const logo = document.createElement('span');
    logo.className = 'reporte-doc__logo';
    logo.textContent = 'S';
    const marcaTxt = document.createElement('div');
    const marcaNombre = document.createElement('p');
    marcaNombre.className = 'reporte-doc__brand';
    marcaNombre.textContent = 'ServiChile';
    const marcaSub = document.createElement('p');
    marcaSub.className = 'reporte-doc__brand-sub';
    marcaSub.textContent = 'Reporte de transparencia empresarial';
    marcaTxt.append(marcaNombre, marcaSub);
    marca.append(logo, marcaTxt);

    const meta = document.createElement('div');
    meta.className = 'reporte-doc__meta';
    const emitido = document.createElement('p');
    emitido.textContent = 'Emitido: ' + ReporteEmpresa.hoy();
    const tipo = document.createElement('p');
    tipo.textContent = 'Informe de empresa';
    meta.append(emitido, tipo);
    cabezal.append(marca, meta);

    const titular = document.createElement('section');
    titular.className = 'reporte-doc__titular';
    const nombre = document.createElement('h3');
    nombre.className = 'reporte-doc__nombre';
    nombre.textContent =
      emp.nombre || ficha.nombre || (rep && rep.nombre) || 'Empresa sin nombre';
    const rubro = document.createElement('p');
    rubro.className = 'reporte-doc__correo';
    rubro.textContent = ReporteEmpresa.etiquetaCategoria(
      emp.categoria || (rep && rep.categoria)
    );
    titular.append(nombre, rubro);

    const qrBloque = document.createElement('section');
    qrBloque.className = 'reporte-doc__qr';
    qrBloque.setAttribute('aria-label', 'Código QR de identidad');
    const qrTitulo = document.createElement('h3');
    qrTitulo.className = 'reporte-doc__h';
    qrTitulo.textContent = 'Código QR de identidad';
    const qrAyuda = document.createElement('p');
    qrAyuda.className = 'reporte-doc__qr-ayuda';
    qrAyuda.textContent =
      'Escanee este código para validar la identidad de la empresa en ServiChile.';
    const qrStatus = document.createElement('p');
    qrStatus.className = 'status-text reporte-doc__qr-status';
    qrStatus.id = 'reporteQrStatus';
    qrStatus.setAttribute('role', 'status');
    qrStatus.textContent = 'Cargando código QR…';
    const qrHost = document.createElement('div');
    qrHost.className = 'reporte-doc__qr-host';
    qrHost.id = 'reporteQrHost';
    qrBloque.append(qrTitulo, qrAyuda, qrStatus, qrHost);

    const resumen = document.createElement('section');
    resumen.className = 'reporte-doc__resumen';
    resumen.setAttribute('aria-label', 'Resumen de transparencia');

    const docs =
      (rep && rep.docs_total != null
        ? Number(rep.docs_total)
        : ficha._docsTotal != null
          ? Number(ficha._docsTotal)
          : typeof ProgresoCuenta !== 'undefined'
            ? ProgresoCuenta.de('proveedor').idsDocumento().length
            : 11) || 11;
    const cargados =
      rep && rep.docs_verificados != null
        ? Number(rep.docs_verificados)
        : ficha._docsCargados != null
          ? ficha._docsCargados
          : 0;
    const pct =
      rep && rep.indice_pct != null
        ? Math.round(Number(rep.indice_pct))
        : ficha.indice_pct != null
          ? Math.round(Number(ficha.indice_pct))
          : Math.round((indice / 10) * 100);

    const resumenTitulo = document.createElement('h3');
    resumenTitulo.className = 'reporte-doc__h';
    resumenTitulo.textContent = 'Resumen de transparencia';
    resumen.appendChild(resumenTitulo);

    const metricas = document.createElement('div');
    metricas.className = 'reporte-doc__metricas';
    [
      ['Índice global', '★ ' + indice.toFixed(1) + ' / 10'],
      ['Señales', pct + '%'],
      ['Documentos legales', cargados + ' de ' + docs]
    ].forEach(([k, v]) => {
      const chip = document.createElement('div');
      chip.className = 'reporte-doc__chip';
      const dt = document.createElement('span');
      dt.className = 'reporte-doc__chip-k';
      dt.textContent = k;
      const dd = document.createElement('strong');
      dd.className = 'reporte-doc__chip-v';
      dd.textContent = v;
      chip.append(dt, dd);
      metricas.appendChild(chip);
    });
    [
      [
        'Razón social / nombre',
        emp.nombre || ficha.nombre || (rep && rep.nombre) || '—'
      ],
      [
        'RUT empresa',
        ReporteEmpresa.textoOpcional(
          emp.rut_empresa || ficha.rut_empresa || (rep && rep.rut_empresa)
        )
      ],
      [
        'Categoría',
        ReporteEmpresa.etiquetaCategoria(emp.categoria || (rep && rep.categoria))
      ],
      ['Dirección', ReporteEmpresa.textoOpcional(emp.direccion || ficha.direccion)],
      ['Teléfono', ReporteEmpresa.textoOpcional(emp.telefono || ficha.telefono)],
      ['Sitio web', ReporteEmpresa.textoOpcional(emp.sitio_web || ficha.sitio_web)],
      ['Descripción', ReporteEmpresa.textoOpcional(emp.descripcion, 'Sin descripción')]
    ].forEach(([k, v]) => {
      const chip = document.createElement('div');
      chip.className = 'reporte-doc__chip';
      const dt = document.createElement('span');
      dt.className = 'reporte-doc__chip-k';
      dt.textContent = k;
      const dd = document.createElement('strong');
      dd.className = 'reporte-doc__chip-v';
      dd.textContent = v;
      chip.append(dt, dd);
      metricas.appendChild(chip);
    });
    resumen.appendChild(metricas);

    const desgloseWrap = document.createElement('section');
    desgloseWrap.className = 'reporte-doc__desglose';
    desgloseWrap.setAttribute('aria-label', 'Desglose del índice global');
    if (typeof Market !== 'undefined' && Market.bloqueDesgloseIndice) {
      const n = Object.assign(
        {
          id: emp.id || (rep && rep.business_id) || ficha.id,
          nombre:
            emp.nombre ||
            (rep && rep.nombre) ||
            ficha.nombre ||
            'Mi empresa',
          indice_pct: pct,
          docs_empresa: emp.docs_empresa || ficha.docs_empresa || null
        },
        emp
      );
      const desglose = Market.bloqueDesgloseIndice(n, rep || null, indice, false);
      if (desglose) {
        desglose.classList.add('reporte-doc__indice');
        desgloseWrap.appendChild(desglose);
      }
    }

    const pie = document.createElement('footer');
    pie.className = 'reporte-doc__pie';
    const aviso = document.createElement('p');
    aviso.textContent =
      'Documento informativo generado por ServiChile a solicitud de la empresa titular. El índice refleja la verificación documental del perfil y no sustituye auditorías oficiales.';
    const ref = document.createElement('p');
    ref.className = 'reporte-doc__ref';
    ref.textContent =
      'Referencia: ' +
      ReporteEmpresa.refId(user) +
      ' · ' +
      ReporteEmpresa.hoy();
    pie.append(aviso, ref);

    doc.append(cabezal, titular, qrBloque, resumen, desgloseWrap, pie);
    return doc;
  },

  async cargarQrInforme() {
    const status = document.getElementById('reporteQrStatus');
    const host = document.getElementById('reporteQrHost');
    if (!host) return;
    if (typeof Auth === 'undefined' || !Auth.isAuthenticated()) {
      if (status) status.textContent = 'Inicie sesión para incluir el QR en el informe.';
      return;
    }
    if (typeof ReporteQr === 'undefined') {
      if (status) status.textContent = 'No se pudo generar el código QR.';
      return;
    }
    const res = await ReporteQr.emitir();
    if (!res.ok) {
      if (status) status.textContent = res.error || 'No se pudo cargar el QR.';
      return;
    }
    if (status) status.textContent = '';
    while (host.firstChild) host.removeChild(host.firstChild);

    const frame = document.createElement('div');
    frame.className = 'reporte-doc__qr-frame';
    frame.id = 'reporteQrFrame';
    ReporteQr.dibujarQr(frame, res.data.payload);

    const expira = document.createElement('p');
    expira.className = 'reporte-doc__qr-expira';
    expira.textContent =
      'Válido hasta ' + ReporteQr.formatoFecha(res.data.expires_at);

    host.append(frame, expira);
    if (ReporteQr.programarRenovacion) {
      ReporteQr.programarRenovacion(res.data.expires_in);
    }
  },

  imprimir() {

    const todos = document.querySelector(
      '#reporteDocumento .indice-desglose__filtro--todos'
    );
    if (todos && todos.getAttribute('aria-pressed') !== 'true') todos.click();

    document.body.classList.add('reporte-print');
    const limpiar = () => {
      document.body.classList.remove('reporte-print');
      window.removeEventListener('afterprint', limpiar);
    };
    window.addEventListener('afterprint', limpiar);
    window.print();
    setTimeout(limpiar, 1500);
  },

  hoy() {
    try {
      return new Date().toLocaleString('es-CL', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return new Date().toISOString();
    }
  },

  refId(user) {
    const base = (user && (user.id || user.email)) || 'local';
    let h = 0;
    const s = String(base);
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return 'SC-E-' + h.toString(16).toUpperCase().padStart(8, '0');
  }
};
