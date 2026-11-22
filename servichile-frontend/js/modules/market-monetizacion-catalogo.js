/* Parte de MarketMonetizacion */
(function () {
  const T = (window.MarketMonetizacion = window.MarketMonetizacion || {});
  Object.assign(T, {
  STORAGE_REBOTE: 'servichile.rebote.vistas',

  STORAGE_PAGO: 'servichile.pago.informe',

  STORAGE_PAGO_RETORNO: 'servichile.pago.informe.retorno',

  STORAGE_PRINT: 'servichile.pago.informe.print',

  _confirmandoPago: false,

  PRECIO_INFORME: 9990,

  PRECIO_PLAN: 89990,

  _catalogoCargado: false,

  indiceDe(n) {
    if (n == null || n.indice_transparencia == null || n.indice_transparencia === '') {
      return {
        ok: false,
        nota: null,
        caso: 'Sin índice de transparencia (la ficha aún no tiene score).'
      };
    }
    const v = Number(n.indice_transparencia);
    if (!Number.isFinite(v)) {
      return {
        ok: false,
        nota: null,
        caso: 'Índice de transparencia inválido.'
      };
    }
    if (v === 0) {
      return {
        ok: false,
        nota: '0.0',
        caso: 'Índice 0 - sin señales o sin puntaje acumulado.'
      };
    }
    return { ok: true, nota: v.toFixed(1), caso: null };
  },

  datosCatalogo(n) {
    const indice = MarketMonetizacion.indiceDe(n);
    return {
      nota: indice.nota,
      casoIndice: indice.caso,
      indiceOk: indice.ok,
      precio: MarketMonetizacion.PRECIO_INFORME,
      precioTxt:
        '$' + MarketMonetizacion.formatoClp(MarketMonetizacion.PRECIO_INFORME) + ' CLP'
    };
  },

  datosDemo(n) {
    return MarketMonetizacion.datosCatalogo(n);
  },

  async cargarCatalogo() {
    if (MarketMonetizacion._catalogoCargado) return MarketMonetizacion.PRECIO_INFORME;
    try {
      const res = await Auth.request('/v1/pagos/informe/catalogo');
      if (res.ok && res.data && res.data.monto) {
        MarketMonetizacion.PRECIO_INFORME = Number(res.data.monto) || MarketMonetizacion.PRECIO_INFORME;
        MarketMonetizacion._catalogoCargado = true;
      }
    } catch (_) {

    }
    return MarketMonetizacion.PRECIO_INFORME;
  },

  async cargarResumenCompras() {
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token) return null;
    const res = await Auth.request('/v1/pagos/informe/resumen', {
      token: sesion.token
    });
    if (!res.ok) return null;
    return res.data || null;
  },

  registrarVistaRebote(n) {
    let mapa = {};
    try {
      mapa = JSON.parse(localStorage.getItem(MarketMonetizacion.STORAGE_REBOTE) || '{}') || {};
    } catch {
      mapa = {};
    }
    const id = String(n.id);
    const prev = mapa[id] || { vistas: 0, nombre: n.nombre };
    const indice = MarketMonetizacion.indiceDe(n);
    prev.vistas += 1;
    prev.nombre = n.nombre;
    prev.nota = indice.nota;
    prev.casoIndice = indice.caso;
    mapa[id] = prev;
    localStorage.setItem(MarketMonetizacion.STORAGE_REBOTE, JSON.stringify(mapa));
    return prev;
  },

  panel(n) {
    const cat = MarketMonetizacion.datosCatalogo(n);
    const wrap = document.createElement('aside');
    wrap.className = 'paywall';
    wrap.setAttribute('aria-label', 'Informe de proveedor');

    const titulo = document.createElement('h3');
    titulo.className = 'paywall__titulo';
    titulo.textContent = 'Informe de proveedor';

    const lead = document.createElement('p');
    lead.className = 'paywall__lead';
    lead.textContent =
      'Reporte de transparencia de ' +
      (n.nombre || 'esta empresa') +
      ', con QR de verificación y PDF. Entrega al confirmar el pago.';

    const precio = document.createElement('p');
    precio.className = 'paywall__precio';
    precio.innerHTML =
      '<strong>' +
      cat.precioTxt +
      '</strong> <span>pago único</span>';

    if (cat.casoIndice) {
      const aviso = document.createElement('p');
      aviso.className = 'paywall__lead paywall__lead--aviso';
      aviso.textContent = cat.casoIndice;
      wrap._avisoIndice = aviso;
    }

    const unlock = document.createElement('button');
    unlock.type = 'button';
    unlock.className = 'paywall__unlock';
    unlock.textContent = 'Comprar informe ' + cat.precioTxt;
    unlock.addEventListener('click', async () => {
      const reabierto = await MarketMonetizacion.reabrirInformeSiComprado(n);
      if (!reabierto) MarketMonetizacion.abrirCheckout(n, { fase: 'resumen' });
    });

    wrap.append(titulo, lead, precio);
    if (wrap._avisoIndice) wrap.appendChild(wrap._avisoIndice);
    wrap.append(unlock);
    wrap._demo = cat;
    wrap._negocio = n;
    MarketMonetizacion.cargarCatalogo().then(() => {
      const actual = MarketMonetizacion.datosCatalogo(n);
      precio.innerHTML =
        '<strong>' + actual.precioTxt + '</strong> <span>pago único</span>';
      if (!unlock.disabled && unlock.textContent.indexOf('Ver informe') < 0) {
        unlock.textContent = 'Comprar informe ' + actual.precioTxt;
      }
    });
    MarketMonetizacion.consultarAcceso(n).then((data) => {
      if (!data || !data.autorizado || !unlock.isConnected) return;
      unlock.disabled = false;
      unlock.textContent = 'Ver informe comprado';
    });
    return wrap;
  },

  formatoClp(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }
  });
})();
