/* Parte de SubirConfianza */
(function () {
  const T = (window.SubirConfianza = window.SubirConfianza || {});
  Object.assign(T, {
    render(raiz) {
    SubirConfianza.limpiar(raiz);
    const selector = SubirConfianza.renderSelectorEmpresas();
    if (selector) raiz.appendChild(selector);
    ProgresoCuenta.actual().montarContenido(raiz);
  },

    renderSelectorEmpresas() {
    const lista = Array.isArray(SubirConfianza.empresas)
      ? SubirConfianza.empresas
      : [];
    if (lista.length < 2) return null;
    const actual = SubirConfianza.empresaActual();

    const box = document.createElement('div');
    box.className = 'reporte__selector';
    box.setAttribute('aria-label', 'Seleccionar empresa');

    const label = document.createElement('label');
    label.className = 'reporte__selector-label';
    label.htmlFor = 'confianzaEmpresaSelect';
    label.textContent = 'Empresa';

    const select = document.createElement('select');
    select.id = 'confianzaEmpresaSelect';
    select.className = 'ui-select';
    select.setAttribute('aria-label', 'Elija a qué empresa aplican estos documentos');

    lista.forEach((n) => {
      const opt = document.createElement('option');
      opt.value = String(n.id);
      opt.textContent = n.nombre || 'Empresa';
      if (actual && String(actual.id) === String(n.id)) opt.selected = true;
      select.appendChild(opt);
    });

    select.addEventListener('change', async () => {
      const id = select.value;
      SubirConfianza.guardarSeleccionId(id);
      if (typeof ReporteEmpresa !== 'undefined' && ReporteEmpresa.guardarSeleccionId) {
        ReporteEmpresa.guardarSeleccionId(id);
      }
      select.disabled = true;
      await SubirConfianza.cargarEmpresas();
      const raiz = document.getElementById('subirConfianzaRaiz');
      if (raiz) SubirConfianza.render(raiz);
    });

    box.append(label, select);
    return box;
  },

    bloqueDesgloseEmpresa() {
    if (!SubirConfianza.tieneEmpresa()) return null;
    const ficha = SubirConfianza.fichaEmpresa();
    const rep = SubirConfianza.reputacionMia;
    if (ficha.indice_transparencia == null) return null;
    if (typeof Market === 'undefined' || !Market.bloqueDesgloseIndice) {
      const fallback = document.createElement('p');
      fallback.className = 'section-lead';
      fallback.textContent = 'El desglose del índice no está disponible.';
      return fallback;
    }
    return Market.bloqueDesgloseIndice(
      ficha,
      rep,
      ficha.indice_transparencia,
      false
    );
  },

    limpiar(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }
  });
})();
