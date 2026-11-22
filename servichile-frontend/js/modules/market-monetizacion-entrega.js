/* Parte de MarketMonetizacion */
(function () {
  const T = (window.MarketMonetizacion = window.MarketMonetizacion || {});
  Object.assign(T, {
  async precargarReputacion(businessId) {
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token || !businessId) return null;
    const res = await Auth.request(
      '/v1/businesses/' + encodeURIComponent(businessId) + '/reputation',
      { token: sesion.token }
    );
    if (!res.ok || !res.data) return null;
    if (typeof Market !== 'undefined') {
      if (!Market._reps) Market._reps = {};
      Market._reps[String(businessId)] = res.data;
    }
    return res.data;
  },

  async entregarInformePagado(n, pago) {
    if (!(await MarketMonetizacion.asegurarReporteEmpresa())) {
      MarketMonetizacion.pintarCheckout('error', {
        mensaje:
          'El pago está ok, pero no se pudo abrir el PDF. Guarde la orden y contacte soporte.',
        orden: pago && pago.buy_order,
        reclamo: pago && pago.reclamo
      });
      return false;
    }
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token || !n || !n.id) {
      MarketMonetizacion.toast('Inicie sesión para abrir el informe comprado.');
      return false;
    }
    let pagoOk = pago || null;
    const guardado = MarketMonetizacion.leerPrintToken(n.id);
    let printToken =
      (pagoOk && pagoOk.print_token) ||
      (guardado && guardado.print_token) ||
      null;
    if (!printToken) {
      const acceso = await MarketMonetizacion.consultarAcceso(n);
      if (acceso && acceso.print_token) {
        pagoOk = acceso;
        printToken = acceso.print_token;
        MarketMonetizacion.guardarPrintToken(
          n.id,
          acceso.print_token,
          acceso.buy_order
        );
      }
    }
    if (!printToken) {
      MarketMonetizacion.toast(
        'Falta el sello de impresión. Reabra el informe desde «Ver informe comprado».'
      );
      return false;
    }
    const ver = await Auth.request('/v1/pagos/informe/verificar-print', {
      method: 'POST',
      token: sesion.token,
      body: { business_id: n.id, print_token: printToken }
    });
    if (!ver.ok || !ver.data || !ver.data.autorizado || !ver.data.print_token) {
      MarketMonetizacion.pintarCheckout('error', {
        mensaje:
          (ver.data && ver.data.detail && ver.data.detail.mensaje) ||
          ver.error ||
          'No se pudo validar el sello de impresión. Reabra el informe comprado.',
        orden: (pagoOk && pagoOk.buy_order) || (guardado && guardado.buy_order),
        reclamo: pagoOk && pagoOk.reclamo
      });
      return false;
    }
    pagoOk = ver.data;
    MarketMonetizacion.guardarPrintToken(
      n.id,
      pagoOk.print_token,
      pagoOk.buy_order
    );
    let rep =
      (typeof Market !== 'undefined' && Market._reps && Market._reps[String(n.id)]) ||
      null;
    if (!rep) rep = await MarketMonetizacion.precargarReputacion(n.id);
    const ok = await ReporteEmpresa.imprimirFicha(n, rep, {
      autorizado: true,
      buy_order: pagoOk.buy_order,
      payload: pagoOk.qr_payload || null,
      expires_at: pagoOk.expires_at || null,
      print_token: pagoOk.print_token
    });
    if (!ok) return false;
    MarketMonetizacion.toast(
      pagoOk.enviado
        ? 'Informe abierto. Comprobante enviado a ' +
            (pagoOk.destino || 'su correo') +
            '.'
        : 'Informe abierto. Si no llega el comprobante al correo, revise spam o contacte soporte.'
    );
    return true;
  },

  async consultarAcceso(n) {
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token || !n || !n.id) return null;
    const res = await Auth.request(
      '/v1/pagos/informe/acceso/' + encodeURIComponent(n.id),
      { token: sesion.token }
    );
    if (!res.ok || !res.data || !res.data.autorizado) return null;
    return res.data;
  },

  async reabrirInformeSiComprado(n) {
    const data = await MarketMonetizacion.consultarAcceso(n);
    if (!data) return false;
    if (data.print_token) {
      MarketMonetizacion.guardarPrintToken(
        data.business_id || n.id,
        data.print_token,
        data.buy_order
      );
    }
    await MarketMonetizacion.abrirCheckout(n, {
      fase: 'exito',
      orden: data.buy_order,
      pago: data
    });
    return true;
  },

  revelarPaywallSiVisible() {
    const panel = document.querySelector('.paywall');
    if (!panel) return;
    const unlock = panel.querySelector('.paywall__unlock');
    if (unlock) {
      unlock.disabled = true;
      unlock.textContent = 'Informe comprado';
    }
  },

  mostrarRebote(n, demo) {
    const vista = MarketMonetizacion.registrarVistaRebote(n);
    const total = Math.max(3, vista.vistas);
    const notaTxt =
      vista.nota != null
        ? 'Nota actual: ' + vista.nota + ' ⭐'
        : vista.casoIndice || demo.casoIndice || 'Sin índice de transparencia';
    MarketMonetizacion.toast(
      'Aviso al titular de ' +
        n.nombre +
        ': «' +
        total +
        ' empresas revisaron el perfil esta semana (' +
        notaTxt +
        ').»'
    );
  },

  mostrarPlanRecurrente(resumen) {
    const gastado =
      (resumen && resumen.gastado_mes) ||
      MarketMonetizacion.PRECIO_INFORME * 2;
    MarketMonetizacion.abrirBanner(
      'Este mes lleva $' +
        MarketMonetizacion.formatoClp(gastado) +
        ' en informes. El Plan Empresas (próximamente, $' +
        MarketMonetizacion.formatoClp(MarketMonetizacion.PRECIO_PLAN) +
        '/mes) incluirá informes ilimitados y alertas.',
      'Avisarme cuando esté listo'
    );
  },

  abrirBanner(texto, ctaLabel) {
    let banner = document.getElementById('paywallBanner');
    if (banner) banner.remove();
    banner = document.createElement('div');
    banner.id = 'paywallBanner';
    banner.className = 'paywall-banner';
    banner.setAttribute('role', 'status');
    const p = document.createElement('p');
    p.textContent = texto;
    const acciones = document.createElement('div');
    acciones.className = 'paywall-banner__acciones';
    const cta = document.createElement('button');
    cta.type = 'button';
    cta.className = 'paywall-banner__cta';
    cta.textContent = ctaLabel;
    cta.addEventListener('click', () => {
      MarketMonetizacion.toast(
        'Plan Empresas: próximamente. Escríbanos a pagos@servichile.cl si quiere prioridad.'
      );
      banner.remove();
    });
    const cerrar = document.createElement('button');
    cerrar.type = 'button';
    cerrar.className = 'paywall-banner__cerrar';
    cerrar.textContent = 'Ahora no';
    cerrar.addEventListener('click', () => banner.remove());
    acciones.append(cta, cerrar);
    banner.append(p, acciones);
    document.body.appendChild(banner);
  },

  toast(msg) {
    let el = document.getElementById('paywallToast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'paywallToast';
      el.className = 'paywall-toast';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(MarketMonetizacion._toastTimer);
    MarketMonetizacion._toastTimer = setTimeout(() => {
      el.hidden = true;
    }, 7000);
  },

  async asegurarReporteEmpresa() {
    if (typeof ReporteEmpresa !== 'undefined' && ReporteEmpresa.imprimirFicha) return true;
    if (typeof Carga === 'undefined' || !Carga.script) return false;
    const v =
      (typeof Auth !== 'undefined' && Auth.APP_VERSION) ||
      (typeof window !== 'undefined' && window.SERVICHILE_APP_VERSION) ||
      '219';
    await Carga.script('js/modules/reporte-empresa.js?v=' + v);
    await Carga.script('js/modules/reporte-qr.js?v=' + v);
    return typeof ReporteEmpresa !== 'undefined' && !!ReporteEmpresa.imprimirFicha;
  },

  async entregarInforme(n, statusEl) {

    MarketMonetizacion.abrirCheckout(n, { fase: 'resumen' });
    if (statusEl) statusEl.textContent = 'Complete el pago para obtener el informe.';
    return false;
  },

  async descargarInforme(n, statusEl) {
    return MarketMonetizacion.entregarInforme(n, statusEl);
  },

  limpiar(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }
  });
})();
