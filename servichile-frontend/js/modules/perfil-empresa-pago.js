/* Parte de PerfilEmpresa */
(function () {
  const T = (window.PerfilEmpresa = window.PerfilEmpresa || {});
  Object.assign(T, {
    modo: null,

    editandoId: null,

    PREFIJO_TEL: '+56 9 ',

    PRECIO_PUBLICACION: 8990,

    STORAGE_BORRADOR: 'servichile.publicacion.borrador',

    STORAGE_PAGO: 'servichile.publicacion.pago',

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

    precioPublicacionTxt() {
    return (
      '$' + PerfilEmpresa.formatoClp(PerfilEmpresa.PRECIO_PUBLICACION) + ' CLP'
    );
  },

    guardarBorrador(datos) {
    try {
      sessionStorage.setItem(
        PerfilEmpresa.STORAGE_BORRADOR,
        JSON.stringify(datos || {})
      );
    } catch (_) {

    }
  },

    leerBorrador() {
    try {
      const raw = sessionStorage.getItem(PerfilEmpresa.STORAGE_BORRADOR);
      return raw ? JSON.parse(raw) : null;
    } catch (_) {
      return null;
    }
  },

    limpiarBorrador() {
    try {
      sessionStorage.removeItem(PerfilEmpresa.STORAGE_BORRADOR);
    } catch (_) {

    }
  },

    guardarPagoPendiente(data) {
    try {
      sessionStorage.setItem(
        PerfilEmpresa.STORAGE_PAGO,
        JSON.stringify(
          Object.assign({}, data || {}, { producto: 'publicacion' })
        )
      );
      if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.guardarPagoPendiente) {
        MarketMonetizacion.guardarPagoPendiente({
          buy_order: data && data.buy_order,
          token: data && data.token,
          producto: 'publicacion'
        });
      }
    } catch (_) {

    }
  },

    leerPagoPendiente() {
    try {
      const raw = sessionStorage.getItem(PerfilEmpresa.STORAGE_PAGO);
      if (raw) return JSON.parse(raw);
    } catch (_) {

    }
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.leerPagoPendiente) {
      const p = MarketMonetizacion.leerPagoPendiente() || {};
      if (p.producto === 'publicacion') return p;
    }
    return null;
  },

    limpiarPagoPendiente() {
    try {
      sessionStorage.removeItem(PerfilEmpresa.STORAGE_PAGO);
    } catch (_) {

    }
  },

    esRetornoPublicacion() {
    const p = PerfilEmpresa.leerPagoPendiente() || {};
    if (p.producto === 'publicacion') return true;
    try {
      return (
        new URLSearchParams(window.location.search || '').get('producto') ===
        'publicacion'
      );
    } catch (_) {
      return false;
    }
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
    PerfilEmpresa.cargarCatalogoPublicacion();
  },

    async cargarCatalogoPublicacion() {
    try {
      const res = await Auth.request('/v1/pagos/publicacion/catalogo');
      if (res.ok && res.data && res.data.monto) {
        PerfilEmpresa.PRECIO_PUBLICACION = Number(res.data.monto) || 8990;
        PerfilEmpresa._aplicarTextosPrecio();
      }
    } catch (_) {

    }
  },

    _aplicarTextosPrecio() {
    const txt = PerfilEmpresa.precioPublicacionTxt();
    const btn = document.getElementById('peBtnPublicarPagar');
    if (btn) btn.textContent = 'Pagar y publicar ' + txt;
    const enviar = document.getElementById('peBtnEnviarPublicar');
    if (enviar && PerfilEmpresa.modo === 'crear') {
      enviar.textContent = 'Pagar ' + txt + ' y publicar';
    }
  },

    urlRetornoPublicacion() {
    let base = window.location.origin + window.location.pathname;
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.urlRetornoPago) {
      base = MarketMonetizacion.urlRetornoPago();
    } else {
      base = base + (base.indexOf('?') >= 0 ? '&' : '?') + 'pago=retorno';
    }
    if (base.indexOf('producto=publicacion') < 0) {
      base += (base.indexOf('?') >= 0 ? '&' : '?') + 'producto=publicacion';
    }
    return base;
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
    PerfilEmpresa.guardarBorrador(datos);
    PerfilEmpresa.setStatus(
      'Iniciando pago de publicación (' +
        PerfilEmpresa.precioPublicacionTxt() +
        ')…'
    );

    const acceso = await Auth.request('/v1/pagos/publicacion/acceso', {
      method: 'GET',
      token: Auth.sesion.token
    });
    if (acceso.ok && acceso.data && acceso.data.autorizado && !acceso.data.consumido) {
      await PerfilEmpresa.crearConBuyOrder(datos, acceso.data.buy_order);
      return;
    }

    const ini = await Auth.request('/v1/pagos/publicacion', {
      method: 'POST',
      token: Auth.sesion.token,
      body: { return_url: PerfilEmpresa.urlRetornoPublicacion() }
    });
    if (!ini.ok) {
      const detail = ini.data && ini.data.detail;
      const codigo = detail && detail.codigo;
      if (codigo === 'cupon_disponible' && detail.buy_order) {
        await PerfilEmpresa.crearConBuyOrder(datos, detail.buy_order);
        return;
      }
      PerfilEmpresa.setStatus(
        (detail && detail.mensaje) || ini.error || 'No se pudo iniciar el pago.'
      );
      return;
    }
    PerfilEmpresa.guardarPagoPendiente({
      buy_order: ini.data.buy_order,
      token: ini.data.token,
      reclamo: ini.data.reclamo
    });
    PerfilEmpresa.setStatus('Redirigiendo a Webpay…');
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = ini.data.url;
    form.style.display = 'none';
    const tokenField = document.createElement('input');
    tokenField.type = 'hidden';
    tokenField.name = 'token_ws';
    tokenField.value = ini.data.token;
    form.appendChild(tokenField);
    document.body.appendChild(form);
    form.submit();
  },

    async crearConBuyOrder(datos, buyOrder) {
    const host = document.getElementById('perfilEmpresaMias');
    const prev = Array.isArray(PerfilEmpresa._mias) ? PerfilEmpresa._mias.slice() : [];
    const provisional = {
      id: null,
      nombre: datos.nombre,
      categoria: datos.categoria,
      rut_empresa: datos.rut_empresa,
      telefono: datos.telefono || null,
      sitio_web: datos.sitio_web || null,
      direccion: datos.direccion,
      descripcion: datos.descripcion || null,
      servicios: datos.servicios,
      industrias: datos.industrias,
      contrataciones: datos.contrataciones,
      monto: datos.monto || null,
      plazo: datos.plazo || null,
      referencias: datos.referencias,
      rater_listo: false
    };
    const listaOptimistic = [provisional].concat(prev);
    PerfilEmpresa._mias = listaOptimistic;
    if (host) PerfilEmpresa.pintarListaMias(host, listaOptimistic);
    PerfilEmpresa.cerrarPanel();
    PerfilEmpresa.setStatus('Publicando ficha…');

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
        rut_empresa: datos.rut_empresa,
        servicios: datos.servicios,
        industrias: datos.industrias,
        contrataciones: datos.contrataciones,
        monto: datos.monto || null,
        plazo: datos.plazo || null,
        referencias: datos.referencias,
        buy_order: buyOrder
      },
      token: Auth.sesion.token
    });
    if (!res.ok) {
      PerfilEmpresa._mias = prev;
      if (host) PerfilEmpresa.pintarListaMias(host, prev);
      const detail = res.data && res.data.detail;
      PerfilEmpresa.setStatus(
        (detail && detail.mensaje) || res.error || 'No se pudo crear la empresa.'
      );
      return false;
    }
    const creado = res.data || {};
    Object.assign(provisional, creado, { rater_listo: !!creado.rater_listo });
    if (host) PerfilEmpresa.pintarListaMias(host, PerfilEmpresa._mias);
    PerfilEmpresa.limpiarBorrador();
    PerfilEmpresa.limpiarPagoPendiente();
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.limpiarPagoPendiente) {
      MarketMonetizacion.limpiarPagoPendiente();
    }
    PerfilEmpresa.setStatus('Empresa publicada. Ya aparece en Explorar.');
    if (typeof SubirConfianza !== 'undefined') {
      SubirConfianza.empresas = null;
      SubirConfianza.reputacionMia = null;
    }
    if (typeof Market !== 'undefined') {
      Market._cache = null;
      Market._firma = '';
    }
    PerfilEmpresa.completarIndicesMias(PerfilEmpresa._mias);
    return true;
  },

    async procesarRetornoPublicacion() {
    if (PerfilEmpresa._confirmandoPublicacion) return true;
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.capturarRetornoDesdeUrl) {
      MarketMonetizacion.capturarRetornoDesdeUrl();
    }
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token) {
      const status = document.getElementById('loginStatus');
      if (status) {
        status.textContent =
          'Pago de publicación recibido. Inicie sesión para crear la ficha.';
      }
      return true;
    }
    PerfilEmpresa._confirmandoPublicacion = true;
    try {
      return await PerfilEmpresa._procesarRetornoPublicacionAutenticado(sesion);
    } finally {
      PerfilEmpresa._confirmandoPublicacion = false;
    }
  },

    async _procesarRetornoPublicacionAutenticado(sesion) {
    const params = new URLSearchParams(window.location.search || '');
    const guardado =
      (typeof MarketMonetizacion !== 'undefined' &&
        MarketMonetizacion.leerRetornoPago &&
        MarketMonetizacion.leerRetornoPago()) ||
      {};
    const tokenWs = params.get('token_ws') || guardado.token_ws || null;
    const tbkToken = params.get('TBK_TOKEN') || guardado.tbk_token || null;
    const pendiente = PerfilEmpresa.leerPagoPendiente() || {};
    const orden =
      pendiente.buy_order ||
      params.get('TBK_ORDEN_COMPRA') ||
      guardado.tbk_orden ||
      null;

    async function irAPerfil() {
      if (typeof App !== 'undefined' && App.openSection) {
        await App.openSection('perfil');
      } else if (typeof App !== 'undefined' && App.showView) {
        App.showView('perfilView');
        if (typeof PerfilEmpresa.init === 'function') PerfilEmpresa.init();
      }
    }

    if (tbkToken && !tokenWs) {
      if (orden) {
        await Auth.request('/v1/pagos/publicacion/anular', {
          method: 'POST',
          token: sesion.token,
          body: { buy_order: orden, motivo: 'Cancelado o abortado en Webpay' }
        });
      }
      PerfilEmpresa.limpiarPagoPendiente();
      await irAPerfil();
      PerfilEmpresa.setStatus('Pago de publicación cancelado en Webpay.');
      return true;
    }

    await irAPerfil();
    PerfilEmpresa.setStatus('Confirmando pago de publicación…');
    let conf;
    if (tokenWs) {
      conf = await Auth.request('/v1/pagos/publicacion/confirmar', {
        method: 'POST',
        token: sesion.token,
        body: { token: tokenWs }
      });
    } else if (orden) {
      conf = await Auth.request('/v1/pagos/publicacion/recuperar', {
        method: 'POST',
        token: sesion.token,
        body: { buy_order: orden }
      });
    } else {
      PerfilEmpresa.setStatus('No se pudo recuperar el pago de publicación.');
      return true;
    }

    if (!conf.ok || !conf.data || !conf.data.autorizado) {
      const detail = conf.data && conf.data.detail;
      PerfilEmpresa.setStatus(
        (detail && detail.mensaje) ||
          (conf.data && conf.data.error_detalle) ||
          conf.error ||
          'El pago de publicación no fue autorizado.'
      );
      return true;
    }

    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.limpiarPagoPendiente) {
      try {
        sessionStorage.removeItem(MarketMonetizacion.STORAGE_PAGO_RETORNO);
      } catch (_) {
      }
    }

    const datos = PerfilEmpresa.leerBorrador();
    if (!datos) {
      PerfilEmpresa.setStatus(
        'Pago OK (orden ' +
          conf.data.buy_order +
          '). Complete el formulario y publique para usar el cupón.'
      );
      PerfilEmpresa.mostrarModo('crear');
      return true;
    }
    await PerfilEmpresa.crearConBuyOrder(datos, conf.data.buy_order);
    return true;
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
        rut_empresa: datos.rut_empresa,
        servicios: datos.servicios,
        industrias: datos.industrias,
        contrataciones: datos.contrataciones,
        monto: datos.monto || null,
        plazo: datos.plazo || null,
        referencias: datos.referencias
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
  });
})();
