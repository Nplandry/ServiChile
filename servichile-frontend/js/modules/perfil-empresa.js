
const PerfilEmpresa = {
  modo: null,
  editandoId: null,
  PRECIO_PUBLICAR: 29990,

  esProveedor() {
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.esProveedor()
      : false;
  },

  esEmpresa() {
    return PerfilEmpresa.esProveedor();
  },

  formatoClp(n) {
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.formatoClp) {
      return MarketMonetizacion.formatoClp(n);
    }
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  },

  init() {
    try {
      localStorage.removeItem('servichile.rut_empresa_pendiente');
    } catch {}
    const host = document.getElementById('perfilEmpresaRaiz');
    if (!host) return;
    while (host.firstChild) host.removeChild(host.firstChild);
    if (!PerfilEmpresa.esProveedor()) {
      host.hidden = true;
      return;
    }
    host.hidden = false;
    host.appendChild(PerfilEmpresa.render());
    PerfilEmpresa.cargarMias();
  },

  categorias() {
    if (typeof Market !== 'undefined' && Array.isArray(Market.CATEGORIAS)) {
      return Market.CATEGORIAS.filter((c) => c.id !== 'all');
    }
    return [
      { id: 'tecnologia', label: 'Tecnología y datos' },
      { id: 'industria', label: 'Minería e industria' },
      { id: 'construccion', label: 'Construcción' },
      { id: 'servicios-profesionales', label: 'Servicios profesionales' },
      { id: 'logistica', label: 'Transporte, Logística y Última Milla' }
    ];
  },

  render() {
    const wrap = document.createElement('div');
    wrap.className = 'perfil-empresa';

    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = '¿Quiere crear una empresa?';

    const lead = document.createElement('p');
    lead.className = 'section-lead';
    lead.textContent =
      'Cree su ficha para aparecer ante compradores B2B que hacen due diligence.';

    const valor = document.createElement('div');
    valor.className = 'perfil-empresa__valor';
    const valorTitulo = document.createElement('p');
    valorTitulo.className = 'perfil-empresa__valor-titulo';
    valorTitulo.textContent = 'Publicar tiene valor: sin ficha activa no lo encuentran en Explorar.';
    const valorLista = document.createElement('ul');
    valorLista.className = 'perfil-empresa__valor-lista';
    [
      'Crear y publicar ficha: $' +
        PerfilEmpresa.formatoClp(PerfilEmpresa.PRECIO_PUBLICAR) +
        ' CLP / mes',
      'La ficha queda a su nombre. No hay directorio previo para reclamar.',
      'Si la quita del perfil, se elimina del marketplace.'
    ].forEach((t) => {
      const li = document.createElement('li');
      li.textContent = t;
      valorLista.appendChild(li);
    });
    valor.append(valorTitulo, valorLista);

    const acciones = document.createElement('div');
    acciones.className = 'perfil-empresa__acciones';

    const btnCrear = document.createElement('button');
    btnCrear.type = 'button';
    btnCrear.className = 'submit-btn';
    btnCrear.textContent =
      'Crear empresa · $' + PerfilEmpresa.formatoClp(PerfilEmpresa.PRECIO_PUBLICAR) + '/mes';
    btnCrear.addEventListener('click', () => PerfilEmpresa.mostrarModo('crear'));

    acciones.appendChild(btnCrear);

    const panel = document.createElement('div');
    panel.id = 'perfilEmpresaPanel';
    panel.className = 'perfil-empresa__panel';
    panel.hidden = true;

    const miasTitulo = document.createElement('h4');
    miasTitulo.className = 'perfil-empresa__subtitulo';
    miasTitulo.textContent = 'Sus empresas';

    const mias = document.createElement('div');
    mias.id = 'perfilEmpresaMias';
    mias.className = 'perfil-empresa__mias';
    mias.setAttribute('aria-live', 'polite');

    const box = document.createElement('div');
    box.className = 'perfil-empresa__carga';
    box.setAttribute('role', 'status');
    const spin = document.createElement('span');
    spin.className = 'perfil-empresa__spinner';
    spin.setAttribute('aria-hidden', 'true');
    const msg = document.createElement('p');
    msg.className = 'perfil-empresa__carga-texto';
    msg.textContent = 'Cargando sus empresas…';
    box.append(spin, msg);
    mias.appendChild(box);

    const status = document.createElement('p');
    status.id = 'perfilEmpresaStatus';
    status.className = 'status-text';
    status.setAttribute('role', 'status');

    wrap.append(titulo, lead, valor, acciones, panel, miasTitulo, mias, status);
    return wrap;
  },

  confirmarPago() {
    return window.confirm(
      'Activar publicación por $' +
        PerfilEmpresa.formatoClp(PerfilEmpresa.PRECIO_PUBLICAR) +
        ' CLP / mes?\n\nDemo: no se cobra de verdad. Su ficha quedará visible en Explorar.'
    );
  },

  mostrarModo(modo, negocio) {
    PerfilEmpresa.modo = modo;
    PerfilEmpresa.editandoId = modo === 'editar' && negocio ? negocio.id : null;
    const panel = document.getElementById('perfilEmpresaPanel');
    if (!panel) return;
    while (panel.firstChild) panel.removeChild(panel.firstChild);
    panel.hidden = false;
    panel.appendChild(PerfilEmpresa.formFicha(modo === 'editar' ? negocio : null));
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  },

  bindRutInput(input) {
    if (!input || typeof Security === 'undefined') return;
    input.addEventListener('input', () => {
      input.value = Security.formatRut(input.value);
    });
  },

  formFicha(negocio) {
    const editando = !!(negocio && negocio.id);
    const form = document.createElement('form');
    form.className = 'form perfil-empresa__form';
    form.noValidate = true;

    const intro = document.createElement('p');
    intro.className = 'field__hint';
    intro.textContent = editando
      ? 'Actualice los datos de la ficha. Al guardar se refrescan las consultas de transparencia (ChileCompra, cabeceras, etc.).'
      : 'Al publicar se activa el plan de ficha ($' +
        PerfilEmpresa.formatoClp(PerfilEmpresa.PRECIO_PUBLICAR) +
        ' CLP/mes, demo). Quedará asociada a su cuenta como titular.';

    const campoRut = PerfilEmpresa.campoTexto(
      'peRut',
      'RUT de la empresa',
      true,
      12,
      'text',
      'Necesario para ChileCompra y consultas de estado del proveedor.'
    );
    form.append(
      intro,
      PerfilEmpresa.campoTexto('peNombre', 'Nombre de la empresa', true, 160),
      campoRut,
      PerfilEmpresa.campoCategoria('peCategoria'),
      PerfilEmpresa.campoTexto(
        'peDireccion',
        'Dirección de oficina',
        true,
        200,
        'text',
        'Calle, número, comuna o ciudad donde opera la empresa.'
      ),
      PerfilEmpresa.campoTexto('peTelefono', 'Teléfono', false, 30, 'tel'),
      PerfilEmpresa.campoTexto('peWeb', 'Sitio web', false, 200),
      PerfilEmpresa.campoTexto(
        'peBanner',
        'URL del banner (opcional)',
        false,
        500,
        'url',
        'Enlace https a la imagen de fondo de la ficha. Si lo deja vacío, se usa una imagen por categoría.'
      ),
      PerfilEmpresa.campoTexto(
        'peLogo',
        'URL del logo (opcional)',
        false,
        500,
        'url',
        'Enlace https al logo. Si lo deja vacío, se muestran las iniciales.'
      ),
      PerfilEmpresa.campoTextoarea('peDesc', 'Descripción', 2000)
    );

    const peRut = campoRut.querySelector('#peRut');
    PerfilEmpresa.bindRutInput(peRut);

    if (editando) {
      PerfilEmpresa.rellenarForm(form, negocio);
    }

    const acciones = document.createElement('div');
    acciones.className = 'perfil-empresa__form-acciones';
    const enviar = document.createElement('button');
    enviar.type = 'submit';
    enviar.className = 'submit-btn';
    enviar.textContent = editando
      ? 'Guardar cambios'
      : 'Pagar y publicar · $' +
        PerfilEmpresa.formatoClp(PerfilEmpresa.PRECIO_PUBLICAR) +
        '/mes';
    const cancelar = document.createElement('button');
    cancelar.type = 'button';
    cancelar.className = 'history__clear';
    cancelar.textContent = 'Cancelar';
    cancelar.addEventListener('click', () => PerfilEmpresa.cerrarPanel());
    acciones.append(enviar, cancelar);
    form.appendChild(acciones);

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (editando) PerfilEmpresa.enviarActualizar();
      else PerfilEmpresa.enviarCrear();
    });
    return form;
  },

  rellenarForm(raiz, n) {
    const set = (id, val) => {
      const el = (raiz && raiz.querySelector('#' + id)) || document.getElementById(id);
      if (el) el.value = val != null ? String(val) : '';
    };
    set('peNombre', n.nombre || '');
    let rut = (n.rut_empresa || '').trim();
    if (rut && typeof Security !== 'undefined') rut = Security.formatRut(rut);
    set('peRut', rut);
    set('peCategoria', n.categoria || '');
    set('peDireccion', n.direccion || '');
    set('peTelefono', n.telefono || '');
    set('peWeb', n.sitio_web || '');
    set('peBanner', n.imagen_url || '');
    set('peLogo', n.logo_url || '');
    set('peDesc', n.descripcion || '');
  },

  leerForm() {
    const nombre = ((document.getElementById('peNombre') || {}).value || '').trim();
    let rut_empresa = (
      (document.getElementById('peRut') || {}).value || ''
    ).trim();
    const categoria = (document.getElementById('peCategoria') || {}).value || '';
    const direccion = ((document.getElementById('peDireccion') || {}).value || '').trim();
    let telefono = ((document.getElementById('peTelefono') || {}).value || '').trim();
    const sitio_web = ((document.getElementById('peWeb') || {}).value || '').trim();
    const imagen_url = ((document.getElementById('peBanner') || {}).value || '').trim();
    const logo_url = ((document.getElementById('peLogo') || {}).value || '').trim();
    const descripcion = ((document.getElementById('peDesc') || {}).value || '').trim();
    return {
      nombre,
      rut_empresa,
      categoria,
      direccion,
      telefono,
      sitio_web,
      imagen_url,
      logo_url,
      descripcion
    };
  },

  validarForm(datos) {
    if (datos.nombre.length < 2) {
      PerfilEmpresa.setStatus('Ingrese el nombre de la empresa.');
      return null;
    }
    let rut_empresa = datos.rut_empresa;
    if (
      !rut_empresa ||
      (typeof Security !== 'undefined' && !Security.validateRut(rut_empresa))
    ) {
      PerfilEmpresa.setStatus('Ingrese un RUT de empresa válido, p. ej. 12.345.678-9.');
      return null;
    }
    if (typeof Security !== 'undefined') {
      rut_empresa = Security.formatRut(rut_empresa);
      const peRut = document.getElementById('peRut');
      if (peRut) peRut.value = rut_empresa;
    }
    if (datos.direccion.length < 3) {
      PerfilEmpresa.setStatus('Ingrese la dirección de oficina.');
      return null;
    }
    let telefono = datos.telefono;
    if (telefono) {
      if (typeof Security !== 'undefined') {
        telefono = Security.formatTelefono(telefono);
        const peTel = document.getElementById('peTelefono');
        if (peTel) peTel.value = telefono;
        if (!Security.validateTelefono(telefono)) {
          PerfilEmpresa.setStatus(
            'Teléfono inválido. Debe comenzar con +56, p. ej. +56 9 1234 5678.'
          );
          return null;
        }
      } else if (!telefono.replace(/\s/g, '').startsWith('+56')) {
        PerfilEmpresa.setStatus('El teléfono debe comenzar con +56.');
        return null;
      }
    }
    if (datos.imagen_url && !/^https?:\/\//i.test(datos.imagen_url)) {
      PerfilEmpresa.setStatus('La URL del banner debe comenzar con http:// o https://');
      return null;
    }
    if (datos.logo_url && !/^https?:\/\//i.test(datos.logo_url)) {
      PerfilEmpresa.setStatus('La URL del logo debe comenzar con http:// o https://');
      return null;
    }
    return Object.assign({}, datos, {
      rut_empresa,
      telefono: telefono || ''
    });
  },

  cerrarPanel() {
    PerfilEmpresa.modo = null;
    PerfilEmpresa.editandoId = null;
    const panel = document.getElementById('perfilEmpresaPanel');
    if (panel) {
      panel.hidden = true;
      while (panel.firstChild) panel.removeChild(panel.firstChild);
    }
  },

  campoTexto(id, label, required, max, type, hint) {
    const field = document.createElement('div');
    field.className = 'field';
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = id;
    lab.textContent = label;
    const input = document.createElement('input');
    input.id = id;
    input.className = 'field__input';
    input.type = type || 'text';
    input.maxLength = max || 160;
    if (required) input.required = true;
    field.append(lab, input);
    if (hint) {
      const hintEl = document.createElement('p');
      hintEl.className = 'field__hint';
      hintEl.textContent = hint;
      field.appendChild(hintEl);
    }
    return field;
  },

  campoTextoarea(id, label, max) {
    const field = document.createElement('div');
    field.className = 'field';
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = id;
    lab.textContent = label;
    const ta = document.createElement('textarea');
    ta.id = id;
    ta.className = 'field__input';
    ta.rows = 3;
    ta.maxLength = max || 2000;
    field.append(lab, ta);
    return field;
  },

  campoCategoria(id) {
    const field = document.createElement('div');
    field.className = 'field';
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = id;
    lab.textContent = 'Categoría';
    const select = document.createElement('select');
    select.id = id;
    select.className = 'field__input';
    select.required = true;
    PerfilEmpresa.categorias().forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.label;
      select.appendChild(opt);
    });
    field.append(lab, select);
    return field;
  },

  setStatus(msg) {
    const el = document.getElementById('perfilEmpresaStatus');
    if (el) el.textContent = msg || '';
  },

  pintarCargaMias(host, texto) {
    while (host.firstChild) host.removeChild(host.firstChild);
    const box = document.createElement('div');
    box.className = 'perfil-empresa__carga';
    box.setAttribute('role', 'status');
    box.setAttribute('aria-live', 'polite');
    const spin = document.createElement('span');
    spin.className = 'perfil-empresa__spinner';
    spin.setAttribute('aria-hidden', 'true');
    const msg = document.createElement('p');
    msg.className = 'perfil-empresa__carga-texto';
    msg.textContent = texto || 'Cargando sus empresas…';
    box.append(spin, msg);
    host.appendChild(box);
  },

  async cargarMias() {
    const host = document.getElementById('perfilEmpresaMias');
    if (!host || !Auth.isAuthenticated()) return;
    PerfilEmpresa.pintarCargaMias(host, 'Cargando sus empresas…');
    const res = await Auth.request('/v1/businesses/mias', { token: Auth.sesion.token });
    if (!res.ok) {
      while (host.firstChild) host.removeChild(host.firstChild);
      const err = document.createElement('p');
      err.className = 'error-text';
      err.textContent = res.error || 'No se pudieron cargar sus empresas.';
      host.appendChild(err);
      return;
    }
    const lista = Array.isArray(res.data) ? res.data : [];
    if (!lista.length) {
      while (host.firstChild) host.removeChild(host.firstChild);
      const vacio = document.createElement('p');
      vacio.className = 'field__hint';
      vacio.textContent = 'Aún no tiene empresas asociadas a esta cuenta.';
      host.appendChild(vacio);
      return;
    }

    PerfilEmpresa.pintarCargaMias(
      host,
      lista.length === 1
        ? 'Preparando índice de «' + lista[0].nombre + '»…'
        : 'Preparando índices de ' + lista.length + ' empresas…'
    );
    await Promise.all(
      lista.map((n) =>
        Auth.request('/v1/businesses/' + encodeURIComponent(n.id) + '/reputation', {
          token: Auth.sesion.token
        }).then((r) => {
          if (r && r.ok && r.data && r.data.indice_transparencia != null) {
            n.indice_transparencia = r.data.indice_transparencia;
            n.indice_pct = r.data.indice_pct;
          }
        }).catch(() => null)
      )
    );

    while (host.firstChild) host.removeChild(host.firstChild);
    const ul = document.createElement('ul');
    ul.className = 'perfil-empresa__lista';
    lista.forEach((n) => {
      const li = document.createElement('li');
      li.className = 'perfil-empresa__item';
      const texto = document.createElement('div');
      texto.className = 'perfil-empresa__item-texto';
      const nombre = document.createElement('strong');
      nombre.textContent = n.nombre;
      const meta = document.createElement('span');
      meta.textContent =
        (n.categoria || '') +
        ' · ★ ' +
        (n.indice_transparencia != null ? Number(n.indice_transparencia).toFixed(1) : '—');
      const rutTxt = (n.rut_empresa || '').trim();
      meta.textContent =
        meta.textContent + (rutTxt ? ' · RUT ' + rutTxt : ' · Sin RUT');
      texto.append(nombre, meta);
      const accionesItem = document.createElement('div');
      accionesItem.className = 'perfil-empresa__item-acciones';
      const actualizar = document.createElement('button');
      actualizar.type = 'button';
      actualizar.className = 'perfil-empresa__btn perfil-empresa__btn--editar';
      actualizar.textContent = 'Actualizar datos';
      actualizar.addEventListener('click', () => PerfilEmpresa.mostrarModo('editar', n));
      const quitar = document.createElement('button');
      quitar.type = 'button';
      quitar.className = 'perfil-empresa__btn perfil-empresa__btn--eliminar';
      quitar.textContent = 'Eliminar';
      quitar.addEventListener('click', () => PerfilEmpresa.quitarEmpresa(n.id, n.nombre));
      accionesItem.append(actualizar, quitar);
      li.append(texto, accionesItem);
      ul.appendChild(li);
    });
    host.appendChild(ul);
  },

  async quitarEmpresa(id, nombre) {
    if (!Auth.isAuthenticated()) {
      PerfilEmpresa.setStatus('Inicie sesión para gestionar sus empresas.');
      return;
    }
    const ok = window.confirm(
      '¿Eliminar «' +
        (nombre || 'esta empresa') +
        '»? Deja de aparecer en Explorar y se borra de la base de datos.'
    );
    if (!ok) return;
    PerfilEmpresa.setStatus('Eliminando…');
    const res = await Auth.request(
      '/v1/businesses/' + encodeURIComponent(id),
      { method: 'DELETE', token: Auth.sesion.token }
    );
    if (!res.ok) {
      PerfilEmpresa.setStatus(res.error || 'No se pudo eliminar la empresa.');
      return;
    }
    if (typeof Market !== 'undefined') {
      Market._cache = null;
      Market._firma = '';
      if (Market._reps) delete Market._reps[String(id)];
      Market.negocios = (Market.negocios || []).filter((n) => String(n.id) !== String(id));
    }
    if (typeof SubirConfianza !== 'undefined') {
      SubirConfianza.empresas = null;
      SubirConfianza.reputacionMia = null;
    }
    PerfilEmpresa.setStatus('Empresa eliminada.');
    PerfilEmpresa.cargarMias();
  },

  async enviarCrear() {
    if (!PerfilEmpresa.esProveedor()) {
      PerfilEmpresa.setStatus('Solo una cuenta proveedor puede crear fichas.');
      return;
    }
    if (!Auth.isAuthenticated()) {
      PerfilEmpresa.setStatus('Inicie sesión para crear una empresa.');
      return;
    }
    const datos = PerfilEmpresa.validarForm(PerfilEmpresa.leerForm());
    if (!datos) return;
    if (!PerfilEmpresa.confirmarPago()) {
      PerfilEmpresa.setStatus('Publicación cancelada. Sin pago no se publica la ficha.');
      return;
    }
    PerfilEmpresa.setStatus('Activando plan (demo) y publicando…');
    const res = await Auth.request('/v1/businesses', {
      method: 'POST',
      body: {
        nombre: datos.nombre,
        categoria: datos.categoria,
        direccion: datos.direccion,
        telefono: datos.telefono || null,
        sitio_web: datos.sitio_web || null,
        imagen_url: datos.imagen_url || null,
        logo_url: datos.logo_url || null,
        descripcion: datos.descripcion || null,
        rut_empresa: datos.rut_empresa
      },
      token: Auth.sesion.token
    });
    if (!res.ok) {
      PerfilEmpresa.setStatus(res.error || 'No se pudo crear la empresa.');
      return;
    }
    PerfilEmpresa.setStatus(
      'Empresa publicada (demo · $' +
        PerfilEmpresa.formatoClp(PerfilEmpresa.PRECIO_PUBLICAR) +
        '/mes).'
    );
    PerfilEmpresa.cerrarPanel();
    if (typeof SubirConfianza !== 'undefined') {
      SubirConfianza.empresas = null;
      SubirConfianza.reputacionMia = null;
    }
    if (typeof Market !== 'undefined') {
      Market._cache = null;
      Market._firma = '';
    }
    PerfilEmpresa.cargarMias();
  },

  async enviarActualizar() {
    if (!PerfilEmpresa.esProveedor()) {
      PerfilEmpresa.setStatus('Solo una cuenta proveedor puede editar fichas.');
      return;
    }
    if (!Auth.isAuthenticated()) {
      PerfilEmpresa.setStatus('Inicie sesión para actualizar la empresa.');
      return;
    }
    const id = PerfilEmpresa.editandoId;
    if (!id) {
      PerfilEmpresa.setStatus('No hay empresa seleccionada para actualizar.');
      return;
    }
    const datos = PerfilEmpresa.validarForm(PerfilEmpresa.leerForm());
    if (!datos) return;
    PerfilEmpresa.setStatus('Guardando cambios y actualizando consultas…');
    const res = await Auth.request('/v1/businesses/' + encodeURIComponent(id), {
      method: 'PATCH',
      body: {
        nombre: datos.nombre,
        categoria: datos.categoria,
        direccion: datos.direccion,
        telefono: datos.telefono || null,
        sitio_web: datos.sitio_web || null,
        imagen_url: datos.imagen_url || null,
        logo_url: datos.logo_url || null,
        descripcion: datos.descripcion || null,
        rut_empresa: datos.rut_empresa
      },
      token: Auth.sesion.token
    });
    if (!res.ok) {
      PerfilEmpresa.setStatus(res.error || 'No se pudo actualizar la empresa.');
      return;
    }
    PerfilEmpresa.setStatus('Datos actualizados. Las consultas de transparencia se refrescaron.');
    PerfilEmpresa.cerrarPanel();
    if (typeof SubirConfianza !== 'undefined') {
      SubirConfianza.empresas = null;
      SubirConfianza.reputacionMia = null;
    }
    if (typeof Market !== 'undefined') {
      Market._cache = null;
      Market._firma = '';
      if (Market._reps) delete Market._reps[String(id)];
    }
    PerfilEmpresa.cargarMias();
  }
};
