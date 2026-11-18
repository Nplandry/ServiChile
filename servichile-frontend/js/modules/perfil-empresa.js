
const PerfilEmpresa = {
  modo: null,
  editandoId: null,
  PRECIO_PUBLICAR: 29990,
  PREFIJO_TEL: '+56 9 ',

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

  _cursorTrasPrefijoTel(input, forzarFinal) {
    if (!input) return;
    const min = PerfilEmpresa.PREFIJO_TEL.length;
    const colocar = () => {
      try {
        const len = input.value.length;
        if (forzarFinal || len <= min) {
          input.setSelectionRange(len, len);
          return;
        }
        const start = input.selectionStart == null ? min : input.selectionStart;
        const end = input.selectionEnd == null ? start : input.selectionEnd;
        if (start < min || end < min) {
          input.setSelectionRange(Math.max(min, start), Math.max(min, end));
        }
      } catch (_) {}
    };
    requestAnimationFrame(() => requestAnimationFrame(colocar));
    setTimeout(colocar, 0);
  },

  _aplicarFormatoInput(input, formateado, caretAntes, largoAntes) {
    if (formateado === input.value) return;
    input.value = formateado;
    const delta = formateado.length - largoAntes;
    const next = Math.max(0, (caretAntes || 0) + delta);
    try {
      input.setSelectionRange(next, next);
    } catch (_) {}
  },

  bindTelefonoInput(input) {
    if (!input) return;
    input.setAttribute('inputmode', 'tel');
    input.setAttribute('autocomplete', 'tel');
    input.placeholder = '+56 9 1234 5678';

    input.addEventListener('focus', () => {
      const vacio = !input.value.trim();
      if (vacio) input.value = PerfilEmpresa.PREFIJO_TEL;
      PerfilEmpresa._cursorTrasPrefijoTel(input, vacio);
    });

    input.addEventListener('click', () => {
      if (!input.value.startsWith('+56')) return;
      PerfilEmpresa._cursorTrasPrefijoTel(input, false);
    });

    input.addEventListener('keydown', (e) => {
      const min = PerfilEmpresa.PREFIJO_TEL.length;
      if (!input.value.startsWith(PerfilEmpresa.PREFIJO_TEL.slice(0, 3))) return;
      const start = input.selectionStart == null ? 0 : input.selectionStart;
      const end = input.selectionEnd == null ? start : input.selectionEnd;
      if (
        (e.key === 'Backspace' && start <= min && start === end) ||
        (e.key === 'ArrowLeft' && start <= min) ||
        e.key === 'Home'
      ) {
        e.preventDefault();
        try {
          input.setSelectionRange(min, min);
        } catch (_) {}
      }
    });

    input.addEventListener('input', () => {
      if (typeof Security === 'undefined') return;
      const valor = input.value;
      if (!valor.trim() || valor.trim() === '+56' || valor.trim() === '+56 9') {
        if (valor.trim() === '+56' || valor.trim() === '+56 9') {
          input.value = valor.trim() === '+56' ? '+56 ' : '+56 9 ';
        } else {
          input.setCustomValidity('');
          input.removeAttribute('aria-invalid');
        }
        return;
      }
      const caret = input.selectionStart;
      const formateado = Security.formatTelefono(valor);
      PerfilEmpresa._aplicarFormatoInput(input, formateado, caret, valor.length);
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
    });

    input.addEventListener('blur', () => {
      let valor = input.value.trim();
      if (!valor || valor === '+56' || valor === '+56 9') {
        input.value = '';
        input.setCustomValidity('');
        input.removeAttribute('aria-invalid');
        return;
      }
      if (typeof Security !== 'undefined') {
        valor = Security.formatTelefono(valor);
        input.value = valor;
        if (!Security.validateTelefono(valor)) {
          input.setCustomValidity(
            'El teléfono debe comenzar con +56, p. ej. +56 9 1234 5678'
          );
          input.setAttribute('aria-invalid', 'true');
        } else {
          input.setCustomValidity('');
          input.removeAttribute('aria-invalid');
        }
      }
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
      PerfilEmpresa.campoTexto(
        'peTelefono',
        'Teléfono',
        false,
        30,
        'tel',
        'Móvil chileno con +56, p. ej. +56 9 1234 5678.'
      ),
      PerfilEmpresa.campoTexto('peWeb', 'Sitio web', false, 200),
      PerfilEmpresa.campoRecurso(
        'peBanner',
        'peBannerPreview',
        'URL del banner',
        false
      ),
      PerfilEmpresa.campoRecurso(
        'peLogo',
        'peLogoPreview',
        'URL del logo',
        true
      ),
      PerfilEmpresa.campoTextoarea('peDesc', 'Descripción', 2000)
    );

    const peRut = campoRut.querySelector('#peRut');
    PerfilEmpresa.bindRutInput(peRut);
    const peTel = form.querySelector('#peTelefono');
    PerfilEmpresa.bindTelefonoInput(peTel);
    PerfilEmpresa.bindUrlPreview(form, 'peBanner', 'peBannerPreview', false);
    PerfilEmpresa.bindUrlPreview(form, 'peLogo', 'peLogoPreview', true);
    const peNombre = form.querySelector('#peNombre');
    if (peNombre) {
      peNombre.addEventListener('input', () => {
        const logoInput = form.querySelector('#peLogo');
        const url = PerfilEmpresa.normalizarUrlRecurso(
          (logoInput && logoInput.value) || ''
        );
        if (url) return;
        PerfilEmpresa.refrescarPreview(form, 'peLogo', 'peLogoPreview', true);
      });
    }

    if (editando) {
      PerfilEmpresa.rellenarForm(form, negocio);
    }
    PerfilEmpresa.refrescarPreview(form, 'peBanner', 'peBannerPreview', false);
    PerfilEmpresa.refrescarPreview(form, 'peLogo', 'peLogoPreview', true);

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
    let tel = (n.telefono || '').trim();
    if (tel && typeof Security !== 'undefined') tel = Security.formatTelefono(tel);
    set('peTelefono', tel);
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
    let telefono = (datos.telefono || '').trim();
    if (!telefono || telefono === '+56' || telefono === '+56 9') {
      telefono = '';
      const peTelVacio = document.getElementById('peTelefono');
      if (peTelVacio) {
        peTelVacio.value = '';
        peTelVacio.setCustomValidity('');
        peTelVacio.removeAttribute('aria-invalid');
      }
    } else if (typeof Security !== 'undefined') {
      telefono = Security.formatTelefono(telefono);
      const peTel = document.getElementById('peTelefono');
      if (peTel) peTel.value = telefono;
      if (!Security.validateTelefono(telefono)) {
        PerfilEmpresa.setStatus(
          'Teléfono inválido. Debe comenzar con +56, p. ej. +56 9 1234 5678.'
        );
        if (peTel) {
          peTel.setCustomValidity(
            'El teléfono debe comenzar con +56, p. ej. +56 9 1234 5678'
          );
          peTel.setAttribute('aria-invalid', 'true');
          peTel.focus();
        }
        return null;
      }
      if (peTel) {
        peTel.setCustomValidity('');
        peTel.removeAttribute('aria-invalid');
      }
    } else if (!telefono.replace(/\s/g, '').startsWith('+56')) {
      PerfilEmpresa.setStatus('El teléfono debe comenzar con +56.');
      return null;
    }
    const banner = PerfilEmpresa.normalizarUrlRecurso(datos.imagen_url);
    if (datos.imagen_url && !banner) {
      PerfilEmpresa.setStatus(
        'La URL del banner debe ser https:// (sin espacios ni esquemas peligrosos).'
      );
      return null;
    }
    const logo = PerfilEmpresa.normalizarUrlRecurso(datos.logo_url);
    if (datos.logo_url && !logo) {
      PerfilEmpresa.setStatus(
        'La URL del logo debe ser https:// (sin espacios ni esquemas peligrosos).'
      );
      return null;
    }
    if (banner) {
      const peBanner = document.getElementById('peBanner');
      if (peBanner) peBanner.value = banner;
    }
    if (logo) {
      const peLogo = document.getElementById('peLogo');
      if (peLogo) peLogo.value = logo;
    }
    return Object.assign({}, datos, {
      rut_empresa,
      telefono: telefono || '',
      imagen_url: banner || '',
      logo_url: logo || ''
    });
  },

  normalizarUrlRecurso(valor) {
    if (!valor) return '';
    let url = String(valor).trim();
    if (!url || url.length > 500 || /\s/.test(url)) return '';
    const bajo = url.toLowerCase();
    if (
      /^(javascript|data|vbscript|file|blob):/.test(bajo)
    ) {
      return '';
    }
    if (bajo.startsWith('http://')) {
      url = 'https://' + url.slice(7);
    } else if (!bajo.startsWith('https://')) {
      return '';
    }
    const host = url.slice(8).split('/')[0] || '';
    if (!host || host.startsWith('.') || host.endsWith('.')) return '';
    if (host.toLowerCase() !== 'localhost' && host.indexOf('.') < 0) return '';
    return url;
  },

  iconoImagen() {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('x', '3');
    rect.setAttribute('y', '5');
    rect.setAttribute('width', '18');
    rect.setAttribute('height', '14');
    rect.setAttribute('rx', '2');
    rect.setAttribute('fill', 'none');
    rect.setAttribute('stroke', 'currentColor');
    rect.setAttribute('stroke-width', '1.6');
    const circ = document.createElementNS(ns, 'circle');
    circ.setAttribute('cx', '9');
    circ.setAttribute('cy', '10');
    circ.setAttribute('r', '1.4');
    circ.setAttribute('fill', 'currentColor');
    const path = document.createElementNS(ns, 'path');
    path.setAttribute('d', 'M3 16l5-4 3 2.5 3-2.5 7 5');
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', 'currentColor');
    path.setAttribute('stroke-width', '1.6');
    path.setAttribute('stroke-linejoin', 'round');
    svg.append(rect, circ, path);
    return svg;
  },

  inicialesPreview() {
    const nombre = ((document.getElementById('peNombre') || {}).value || '').trim();
    const partes = nombre.split(/\s+/).filter(Boolean);
    if (!partes.length) return 'Logo';
    return partes
      .slice(0, 2)
      .map((parte) => parte.charAt(0))
      .join('')
      .toUpperCase();
  },

  campoPreview(id, logo) {
    const wrap = document.createElement('div');
    wrap.className =
      'perfil-empresa__preview' + (logo ? ' perfil-empresa__preview--logo' : '');
    wrap.id = id;
    wrap.setAttribute('aria-live', 'polite');
    const marco = document.createElement('div');
    marco.className = 'perfil-empresa__marco';
    const ph = document.createElement('div');
    ph.className = 'perfil-empresa__ph';
    ph.setAttribute('aria-hidden', 'true');
    if (!logo) ph.append(PerfilEmpresa.iconoImagen());
    const caption = document.createElement('span');
    caption.className = 'perfil-empresa__ph-texto';
    caption.textContent = logo ? 'Logo' : 'Banner';
    const sub = document.createElement('span');
    sub.className = 'perfil-empresa__ph-sub';
    sub.textContent = logo ? 'Iniciales del nombre' : 'Imagen de la ficha';
    ph.append(caption, sub);
    const img = document.createElement('img');
    img.alt = '';
    img.decoding = 'async';
    marco.append(ph, img);
    wrap.append(marco);
    return wrap;
  },

  campoRecurso(inputId, previewId, label, logo) {
    const field = document.createElement('div');
    field.className = 'field perfil-empresa__recurso';
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = inputId;
    lab.textContent = label;
    const input = document.createElement('input');
    input.id = inputId;
    input.className = 'field__input';
    input.type = 'url';
    input.maxLength = 500;
    input.placeholder = 'https://';
    field.append(lab, PerfilEmpresa.campoPreview(previewId, logo), input);
    return field;
  },

  bindUrlPreview(raiz, inputId, previewId, logo) {
    const input = raiz && raiz.querySelector('#' + inputId);
    if (!input) return;
    const pintar = () =>
      PerfilEmpresa.refrescarPreview(raiz, inputId, previewId, logo);
    input.addEventListener('input', pintar);
    input.addEventListener('change', pintar);
  },

  refrescarPreview(raiz, inputId, previewId, logo) {
    const scope = raiz || document;
    const input =
      (scope.querySelector && scope.querySelector('#' + inputId)) ||
      document.getElementById(inputId);
    const box =
      (scope.querySelector && scope.querySelector('#' + previewId)) ||
      document.getElementById(previewId);
    if (!input || !box) return;
    const img = box.querySelector('img');
    if (!img) return;
    const url = PerfilEmpresa.normalizarUrlRecurso(input.value || '');
    img.onload = null;
    img.onerror = null;
    if (!url) {
      PerfilEmpresa.pintarPlaceholder(box, logo);
      return;
    }
    box.classList.remove(
      'perfil-empresa__preview--lista',
      'perfil-empresa__preview--error'
    );
    img.onerror = () => {
      img.onerror = null;
      img.removeAttribute('src');
      box.classList.remove('perfil-empresa__preview--lista');
      box.classList.add('perfil-empresa__preview--error');
      const hint = box.querySelector('.field__hint');
      const sub = box.querySelector('.perfil-empresa__ph-sub');
      if (hint) {
        hint.textContent = logo
          ? 'No se pudo cargar el logo (revise la URL)'
          : 'No se pudo cargar el banner (revise la URL)';
      }
      if (sub) sub.textContent = 'Revisa el enlace https';
    };
    img.onload = () => {
      box.classList.remove('perfil-empresa__preview--error');
      box.classList.add('perfil-empresa__preview--lista');
      const hint = box.querySelector('.field__hint');
      if (hint) {
        hint.textContent = logo
          ? 'Vista previa del logo'
          : 'Vista previa del banner';
      }
    };
    img.src = url;
  },

  pintarPlaceholder(box, logo) {
    box.classList.remove(
      'perfil-empresa__preview--lista',
      'perfil-empresa__preview--error'
    );
    const img = box.querySelector('img');
    if (img) img.removeAttribute('src');
    const texto = box.querySelector('.perfil-empresa__ph-texto');
    const sub = box.querySelector('.perfil-empresa__ph-sub');
    const hint = box.querySelector('.field__hint');
    if (logo) {
      if (texto) texto.textContent = PerfilEmpresa.inicialesPreview();
      if (sub) sub.textContent = 'Iniciales del nombre';
      if (hint) hint.textContent = 'Vista previa del logo';
      return;
    }
    if (texto) texto.textContent = 'Banner';
    if (sub) sub.textContent = 'Imagen de la ficha';
    if (hint) hint.textContent = 'Vista previa del banner';
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

  etiquetaCategoria(id) {
    const cats = PerfilEmpresa.categorias();
    const hit = cats.find((c) => c.id === id);
    return (hit && hit.label) || id || '';
  },

  metaEmpresa(n) {
    const partes = [PerfilEmpresa.etiquetaCategoria(n.categoria || '')];
    if (n.rater_listo && n.indice_transparencia != null) {
      partes.push('★ ' + Number(n.indice_transparencia).toFixed(1));
    }
    const rutTxt = (n.rut_empresa || '').trim();
    partes.push(rutTxt ? 'RUT ' + rutTxt : 'Sin RUT');
    return partes.filter(Boolean).join(' · ');
  },

  pintarListaMias(host, lista) {
    while (host.firstChild) host.removeChild(host.firstChild);
    if (!lista.length) {
      const vacio = document.createElement('p');
      vacio.className = 'field__hint';
      vacio.textContent = 'Aún no tiene empresas asociadas a esta cuenta.';
      host.appendChild(vacio);
      return;
    }
    const ul = document.createElement('ul');
    ul.className = 'perfil-empresa__lista';
    lista.forEach((n) => {
      const li = document.createElement('li');
      li.className = 'perfil-empresa__item';
      if (n.id) li.dataset.businessId = String(n.id);
      const texto = document.createElement('div');
      texto.className = 'perfil-empresa__item-texto';
      const nombre = document.createElement('strong');
      nombre.textContent = n.nombre;
      const meta = document.createElement('span');
      meta.className = 'perfil-empresa__item-meta';
      meta.textContent = PerfilEmpresa.metaEmpresa(n);
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
      if (typeof Trabajos !== 'undefined' && n.id) {
        li.appendChild(Trabajos.panelConcretarTitular(n));
      }
      ul.appendChild(li);
    });
    host.appendChild(ul);
  },

  actualizarMetaEnLista(n) {
    const host = document.getElementById('perfilEmpresaMias');
    if (!host || !n || !n.id) return;
    const li = host.querySelector(
      '.perfil-empresa__item[data-business-id="' + String(n.id) + '"]'
    );
    if (!li) return;
    const meta = li.querySelector('.perfil-empresa__item-meta');
    if (meta) meta.textContent = PerfilEmpresa.metaEmpresa(n);
  },

  async completarIndicesMias(lista, intentos) {
    const max = intentos == null ? 8 : intentos;
    if (!lista || !lista.length || max <= 0) return;
    const pendientes = lista.filter((n) => n && n.id && !n.rater_listo);
    if (!pendientes.length) return;
    await Promise.all(
      pendientes.map((n) =>
        Auth.request('/v1/businesses/' + encodeURIComponent(n.id) + '/reputation', {
          token: Auth.sesion.token
        })
          .then((r) => {
            if (!r || !r.ok || !r.data) return;
            if (r.data.rater_listo) {
              n.rater_listo = true;
              n.indice_transparencia = r.data.indice_transparencia;
              n.indice_pct = r.data.indice_pct;
              PerfilEmpresa.actualizarMetaEnLista(n);
            }
          })
          .catch(() => null)
      )
    );
    if (lista.some((n) => n && n.id && !n.rater_listo)) {
      await new Promise((resolve) => setTimeout(resolve, 1200));
      return PerfilEmpresa.completarIndicesMias(lista, max - 1);
    }
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
    PerfilEmpresa._mias = lista;
    PerfilEmpresa.pintarListaMias(host, lista);
    PerfilEmpresa.completarIndicesMias(lista);
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
    // Pintar altiro en «Sus empresas» sin ★ (el índice llega en segundo plano).
    const provisional = {
      id: null,
      nombre: datos.nombre,
      categoria: datos.categoria,
      rut_empresa: datos.rut_empresa,
      telefono: datos.telefono || null,
      sitio_web: datos.sitio_web || null,
      direccion: datos.direccion,
      descripcion: datos.descripcion || null,
      rater_listo: false
    };
    const host = document.getElementById('perfilEmpresaMias');
    const prev = Array.isArray(PerfilEmpresa._mias) ? PerfilEmpresa._mias.slice() : [];
    const listaOptimistic = [provisional].concat(prev);
    PerfilEmpresa._mias = listaOptimistic;
    if (host) PerfilEmpresa.pintarListaMias(host, listaOptimistic);
    PerfilEmpresa.cerrarPanel();

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
      PerfilEmpresa._mias = prev;
      if (host) PerfilEmpresa.pintarListaMias(host, prev);
      PerfilEmpresa.setStatus(res.error || 'No se pudo crear la empresa.');
      return;
    }
    const creado = res.data || {};
    Object.assign(provisional, creado, { rater_listo: !!creado.rater_listo });
    if (host) PerfilEmpresa.pintarListaMias(host, PerfilEmpresa._mias);
    PerfilEmpresa.setStatus(
      'Empresa publicada (demo · $' +
        PerfilEmpresa.formatoClp(PerfilEmpresa.PRECIO_PUBLICAR) +
        '/mes).'
    );
    if (typeof SubirConfianza !== 'undefined') {
      SubirConfianza.empresas = null;
      SubirConfianza.reputacionMia = null;
    }
    if (typeof Market !== 'undefined') {
      Market._cache = null;
      Market._firma = '';
    }
    PerfilEmpresa.completarIndicesMias(PerfilEmpresa._mias);
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
