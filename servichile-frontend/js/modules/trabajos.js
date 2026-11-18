
const Trabajos = {
  async crear(businessId) {
    if (!Auth.isAuthenticated()) {
      return { ok: false, error: 'Inicie sesión para abrir un trabajo con este proveedor.' };
    }
    return Auth.request('/v1/trabajos', {
      method: 'POST',
      token: Auth.sesion.token,
      body: { business_id: businessId }
    });
  },

  async mias() {
    if (!Auth.isAuthenticated()) {
      return { ok: false, error: 'Sin sesión.', data: [] };
    }
    return Auth.request('/v1/trabajos', { token: Auth.sesion.token });
  },

  async cancelar(trabajoId) {
    return Auth.request('/v1/trabajos/' + encodeURIComponent(trabajoId), {
      method: 'DELETE',
      token: Auth.sesion.token
    });
  },

  async delNegocio(businessId) {
    return Auth.request(
      '/v1/businesses/' + encodeURIComponent(businessId) + '/trabajos',
      { token: Auth.sesion.token }
    );
  },

  async concretar(businessId, qrToken) {
    return Auth.request(
      '/v1/businesses/' + encodeURIComponent(businessId) + '/trabajos/concretar',
      {
        method: 'POST',
        token: Auth.sesion.token,
        body: { qr_token: qrToken }
      }
    );
  },

  async noConcretado(businessId, trabajoId) {
    return Auth.request(
      '/v1/businesses/' +
        encodeURIComponent(businessId) +
        '/trabajos/' +
        encodeURIComponent(trabajoId) +
        '/no-concretado',
      { method: 'POST', token: Auth.sesion.token }
    );
  },

  etiquetaEstado(estado) {
    const map = {
      abierto: 'Abierto',
      concretado: 'Concretado',
      no_concretado: 'No concretado',
      cancelado: 'Cancelado'
    };
    return map[estado] || estado || '—';
  },

  panelTrabajoContratista(n, estadoEl) {
    const wrap = document.createElement('div');
    wrap.className = 'trabajos-panel';

    const titulo = document.createElement('p');
    titulo.className = 'trabajos-panel__titulo';
    titulo.textContent = 'Trabajo con este proveedor';

    const hint = document.createElement('p');
    hint.className = 'field__hint';
    hint.textContent =
      'Abra un trabajo y muestre el código QR al titular para marcar concretado.';

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'submit-btn trabajos-panel__btn';
    btn.textContent = 'Abrir trabajo';

    const detalle = document.createElement('div');
    detalle.className = 'trabajos-panel__detalle';
    detalle.hidden = true;

    btn.addEventListener('click', async () => {
      btn.disabled = true;
      if (estadoEl) estadoEl.textContent = 'Abriendo trabajo…';
      const res = await Trabajos.crear(n.id);
      btn.disabled = false;
      if (!res.ok) {
        if (estadoEl) estadoEl.textContent = res.error || 'No se pudo abrir el trabajo.';
        return;
      }
      const r = res.data || {};
      detalle.hidden = false;
      while (detalle.firstChild) detalle.removeChild(detalle.firstChild);
      const code = document.createElement('code');
      code.className = 'trabajos-panel__qr';
      code.textContent = r.qr_token || '';
      const meta = document.createElement('p');
      meta.className = 'field__hint';
      meta.textContent =
        'Estado: ' +
        Trabajos.etiquetaEstado(r.estado) +
        '. Muestre este código al proveedor.';
      const cancelar = document.createElement('button');
      cancelar.type = 'button';
      cancelar.className = 'history__clear';
      cancelar.textContent = 'Cancelar trabajo';
      cancelar.addEventListener('click', async () => {
        const c = await Trabajos.cancelar(r.id);
        if (!c.ok) {
          if (estadoEl) estadoEl.textContent = c.error || 'No se pudo cancelar.';
          return;
        }
        detalle.hidden = true;
        if (estadoEl) estadoEl.textContent = 'Trabajo cancelado.';
      });
      detalle.append(code, meta, cancelar);
      if (estadoEl) estadoEl.textContent = 'Trabajo abierto. Guarde el código QR.';
    });

    wrap.append(titulo, hint, btn, detalle);
    return wrap;
  },

  panelConcretarTitular(negocio) {
    const wrap = document.createElement('div');
    wrap.className = 'trabajos-titular';
    wrap.dataset.businessId = String(negocio.id);

    const titulo = document.createElement('p');
    titulo.className = 'trabajos-titular__titulo';
    titulo.textContent = 'Concretar trabajos';

    const form = document.createElement('form');
    form.className = 'trabajos-titular__form';
    form.noValidate = true;

    const field = document.createElement('div');
    field.className = 'field';
    const label = document.createElement('label');
    label.className = 'field__label';
    label.htmlFor = 'trabajoQr-' + negocio.id;
    label.textContent = 'Código QR del contratista';
    const input = document.createElement('input');
    input.id = 'trabajoQr-' + negocio.id;
    input.className = 'field__input';
    input.type = 'text';
    input.autocomplete = 'off';
    input.maxLength = 64;
    input.placeholder = 'Pegue el código del trabajo';
    field.append(label, input);

    const acciones = document.createElement('div');
    acciones.className = 'trabajos-titular__acciones';
    const btnOk = document.createElement('button');
    btnOk.type = 'submit';
    btnOk.className = 'perfil-empresa__btn perfil-empresa__btn--editar';
    btnOk.textContent = 'Marcar concretado';
    acciones.appendChild(btnOk);

    const status = document.createElement('p');
    status.className = 'status-text';
    status.setAttribute('role', 'status');

    const lista = document.createElement('div');
    lista.className = 'trabajos-titular__lista';

    form.append(field, acciones);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const token = (input.value || '').trim();
      if (token.length < 10) {
        status.textContent = 'Ingrese el código QR completo.';
        return;
      }
      status.textContent = 'Registrando…';
      const res = await Trabajos.concretar(negocio.id, token);
      if (!res.ok) {
        status.textContent = res.error || 'No se pudo marcar como concretado.';
        return;
      }
      input.value = '';
      status.textContent = 'Trabajo concretado.';
      Trabajos.pintarListaTitular(lista, negocio.id, status);
    });

    wrap.append(titulo, form, status, lista);
    Trabajos.pintarListaTitular(lista, negocio.id, status);
    return wrap;
  },

  async pintarListaTitular(host, businessId, statusEl) {
    if (!host) return;
    host.textContent = 'Cargando trabajos…';
    const res = await Trabajos.delNegocio(businessId);
    if (!res.ok) {
      host.textContent = res.error || 'No se pudieron cargar los trabajos.';
      return;
    }
    const items = Array.isArray(res.data) ? res.data : [];
    while (host.firstChild) host.removeChild(host.firstChild);
    if (!items.length) {
      const vacio = document.createElement('p');
      vacio.className = 'field__hint';
      vacio.textContent = 'Sin trabajos en esta ficha.';
      host.appendChild(vacio);
      return;
    }
    const ul = document.createElement('ul');
    ul.className = 'trabajos-titular__ul';
    items.forEach((r) => {
      const li = document.createElement('li');
      li.className = 'trabajos-titular__li';
      const txt = document.createElement('span');
      txt.textContent =
        Trabajos.etiquetaEstado(r.estado) +
        ' · ' +
        String(r.qr_token || '').slice(0, 10) +
        '…';
      li.appendChild(txt);
      if (r.estado === 'abierto') {
        const noConc = document.createElement('button');
        noConc.type = 'button';
        noConc.className = 'perfil-empresa__btn perfil-empresa__btn--eliminar';
        noConc.textContent = 'No concretado';
        noConc.addEventListener('click', async () => {
          const c = await Trabajos.noConcretado(businessId, r.id);
          if (!c.ok) {
            if (statusEl) statusEl.textContent = c.error || 'No se pudo marcar.';
            return;
          }
          if (statusEl) statusEl.textContent = 'Marcado como no concretado.';
          Trabajos.pintarListaTitular(host, businessId, statusEl);
        });
        li.appendChild(noConc);
      }
      ul.appendChild(li);
    });
    host.appendChild(ul);
  }
};
