/* Parte de PerfilEmpresa */
(function () {
  const T = (window.PerfilEmpresa = window.PerfilEmpresa || {});
  Object.assign(T, {
    render() {
    const wrap = document.createElement('div');
    wrap.className = 'perfil-empresa';

    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = '¿Quiere crear una empresa?';

    const lead = document.createElement('p');
    lead.className = 'section-lead';
    lead.textContent =
      'Cree su ficha para aparecer ante compradores B2B que buscan proveedores verificables.';

    const valor = document.createElement('div');
    valor.className = 'perfil-empresa__valor';
    const valorTitulo = document.createElement('p');
    valorTitulo.className = 'perfil-empresa__valor-titulo';
    valorTitulo.textContent = 'Publicar tiene valor: sin ficha activa no lo encuentran en Explorar.';
    const valorLista = document.createElement('ul');
    valorLista.className = 'perfil-empresa__valor-lista';
    [
      'Publicar ficha cuesta ' +
        PerfilEmpresa.precioPublicacionTxt() +
        ' (Webpay). El informe de proveedor se vende aparte.',
      'La ficha queda a su nombre. No hay directorio previo para reclamar.',
      'Si la quita del perfil, se elimina del marketplace.'
    ].forEach((t) => {
      const li = document.createElement('li');
      li.textContent = t;
      valorLista.appendChild(li);
    });
    const acciones = document.createElement('div');
    acciones.className = 'perfil-empresa__acciones';

    const btnCrear = document.createElement('button');
    btnCrear.type = 'button';
    btnCrear.className = 'submit-btn';
    btnCrear.id = 'peBtnPublicarPagar';
    btnCrear.textContent =
      'Pagar y publicar ' + PerfilEmpresa.precioPublicacionTxt();
    btnCrear.addEventListener('click', () => PerfilEmpresa.mostrarModo('crear'));

    acciones.appendChild(btnCrear);
    valor.append(valorTitulo, valorLista, acciones);

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

    wrap.append(titulo, lead, valor, panel, miasTitulo, mias, status);
    return wrap;
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
    return partes.filter(Boolean).join(' ');
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
      actualizar.textContent = 'Editar ficha';
      actualizar.addEventListener('click', () => PerfilEmpresa.mostrarModo('editar', n));
      const quitar = document.createElement('button');
      quitar.type = 'button';
      quitar.className = 'perfil-empresa__btn perfil-empresa__btn--eliminar';
      quitar.textContent = 'Eliminar';
      quitar.addEventListener('click', () => PerfilEmpresa.quitarEmpresa(n.id, n.nombre));
      accionesItem.append(actualizar, quitar);
      const superior = document.createElement('div');
      superior.className = 'perfil-empresa__item-superior';
      superior.append(texto, accionesItem);
      li.appendChild(superior);
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
  }
  });
})();
