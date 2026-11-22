/* Parte de SubirConfianza */
(function () {
  const T = (window.SubirConfianza = window.SubirConfianza || {});
  Object.assign(T, {
    docVigente(meta) {
    if (!meta || !meta.verificado) return false;
    if (!meta.vence_en) return true;
    const hasta = Date.parse(meta.vence_en);
    if (!Number.isFinite(hasta)) return true;
    return hasta >= Date.now();
  },

    tieneDoc(tipo) {
    const local = SubirConfianza.state.docs.find(
      (d) => d.tipo === tipo && d.verificado !== false && d.caducado !== true
    );
    if (local) {
      if (local.vence_en && Date.parse(local.vence_en) < Date.now()) return false;
      return true;
    }
    const empresa = SubirConfianza.empresaActual();
    const docs = empresa && empresa.docs_empresa;
    return !!(docs && docs[tipo] && SubirConfianza.docVigente(docs[tipo]));
  },

    tiposDocEmpresa() {
    return [
      'carpeta_tributaria',
      'inicio_actividades',
      'vigencia_sociedad',
      'vigencia_poderes',
      'poder_representante',
      'constitucion',
      'f30',
      'no_quiebra',
      'antecedentes_rl',
      'patente',
      'titularidad_cuenta'
    ];
  },

    tiposDocEmpresaPades() {
    return [
      'carpeta_tributaria',
      'inicio_actividades',
      'vigencia_sociedad',
      'vigencia_poderes',
      'poder_representante',
      'constitucion',
      'f30',
      'no_quiebra',
      'antecedentes_rl'
    ];
  },

    sincronizarDocsEmpresaDesdeApi(empresa) {
    if (!empresa || !empresa.docs_empresa || typeof empresa.docs_empresa !== 'object') {
      return;
    }
    const tipos = SubirConfianza.tiposDocEmpresa();
    tipos.forEach((tipo) => {
      const meta = empresa.docs_empresa[tipo];
      if (!meta || !meta.verificado) {
        SubirConfianza.state.docs = SubirConfianza.state.docs.filter((d) => d.tipo !== tipo);
        return;
      }
      const caducado = !SubirConfianza.docVigente(meta);
      SubirConfianza.state.docs = SubirConfianza.state.docs.filter((d) => d.tipo !== tipo);
      SubirConfianza.state.docs.unshift({
        id: 'api-' + tipo,
        tipo,
        nombre: tipo + '.pdf',
        fecha: meta.verificado_en || new Date().toISOString(),
        vence_en: meta.vence_en || null,
        score: meta.score,
        verificado: true,
        caducado
      });
    });
    SubirConfianza.guardar();
  },

    bloqueDocumentos() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-docs config-card';
    wrap.setAttribute('aria-label', 'Subir documentos');

    const head = document.createElement('div');
    head.className = 'confianza-docs__head';

    const prog = typeof ProgresoCuenta !== 'undefined' ? ProgresoCuenta.actual() : null;
    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = prog ? prog.tituloDocumentos() : 'Subir documentos';

    const notaTxt = prog ? prog.notaDocumentos() : '';
    head.appendChild(titulo);
    if (notaTxt) {
      const nota = document.createElement('p');
      nota.className = 'confianza-docs__nota';
      nota.textContent = notaTxt;
      head.appendChild(nota);
    }

    const form = document.createElement('form');
    form.className = 'confianza-docs__form';
    form.noValidate = true;

    const fieldTipo = document.createElement('div');
    fieldTipo.className = 'field';
    const labelTipo = document.createElement('label');
    labelTipo.className = 'field__label';
    labelTipo.htmlFor = 'confianzaDocTipo';
    labelTipo.textContent = 'Tipo de documento';
    const select = document.createElement('select');
    select.id = 'confianzaDocTipo';
    select.className = 'ui-select';
    SubirConfianza.tiposDocumento().forEach(([value, text]) => {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = text;
      select.appendChild(opt);
    });
    fieldTipo.append(labelTipo, select);

    const drop = document.createElement('div');
    drop.className = 'confianza-docs__drop';

    const input = document.createElement('input');
    input.id = 'confianzaDocArchivo';
    input.className = 'confianza-docs__file';
    input.type = 'file';
    input.accept = '.pdf,image/jpeg,image/png,application/pdf';

    const dropLabel = document.createElement('label');
    dropLabel.className = 'confianza-docs__drop-label';
    dropLabel.htmlFor = 'confianzaDocArchivo';

    const dropTitulo = document.createElement('span');
    dropTitulo.className = 'confianza-docs__drop-titulo';
    dropTitulo.textContent = 'Elegir archivo';

    const dropNombre = document.createElement('span');
    dropNombre.className = 'confianza-docs__drop-nombre';
    dropNombre.textContent = 'Ningún archivo seleccionado';

    dropLabel.append(dropTitulo, dropNombre);
    drop.append(input, dropLabel);

    const actualizarArchivo = () => {
      const archivo = input.files && input.files[0];
      drop.classList.toggle('confianza-docs__drop--lleno', !!archivo);
      dropNombre.textContent = archivo
        ? archivo.name + ' ' + SubirConfianza.formatoTamano(archivo.size)
        : select.value === 'cedula'
          ? 'Ninguna foto seleccionada'
          : 'Ningún archivo seleccionado';
    };

    const sincronizarTipoArchivo = () => {
      const esCarnet = select.value === 'cedula';
      const esAval = select.value === 'aval';
      const esDocEmpresa = SubirConfianza.tiposDocEmpresa().includes(select.value);
      const soloPdf =
        esAval || esDocEmpresa || select.value === 'antecedentes';
      drop.hidden = false;
      input.accept = esCarnet
        ? 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp'
        : soloPdf
          ? 'application/pdf,.pdf'
          : '.pdf,image/jpeg,image/png,application/pdf';
      dropTitulo.textContent = esCarnet
        ? 'Foto frontal del carnet'
        : esAval
          ? 'PDF de aval o garantía'
          : esDocEmpresa
            ? 'PDF del documento legal'
            : 'Elegir archivo';
      if (esCarnet && input.files && input.files[0]) {
        const tipo = (input.files[0].type || '').toLowerCase();
        if (tipo && !tipo.startsWith('image/')) {
          input.value = '';
        }
      }
      if (soloPdf && input.files && input.files[0]) {
        const f = input.files[0];
        const ok =
          String(f.type || '') === 'application/pdf' || /\.pdf$/i.test(f.name || '');
        if (!ok) input.value = '';
      }
      actualizarArchivo();
    };

    input.addEventListener('change', actualizarArchivo);
    select.addEventListener('change', sincronizarTipoArchivo);
    sincronizarTipoArchivo();

    ['dragenter', 'dragover'].forEach(ev => {
      drop.addEventListener(ev, e => {
        e.preventDefault();
        drop.classList.add('confianza-docs__drop--activo');
      });
    });
    ['dragleave', 'drop'].forEach(ev => {
      drop.addEventListener(ev, e => {
        e.preventDefault();
        drop.classList.remove('confianza-docs__drop--activo');
      });
    });
    drop.addEventListener('drop', e => {
      const files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) return;
      try {
        const dt = new DataTransfer();
        dt.items.add(files[0]);
        input.files = dt.files;
      } catch {
        return;
      }
      actualizarArchivo();
    });

    const acciones = document.createElement('div');
    acciones.className = 'confianza-docs__acciones';

    const btn = document.createElement('button');
    btn.className = 'submit-btn confianza-docs__submit';
    btn.type = 'submit';
    btn.textContent = 'Registrar documento';

    const status = document.createElement('p');
    status.className = 'status-text confianza-docs__status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');

    acciones.append(btn, status);
    form.append(fieldTipo, drop, acciones);

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const tipo = select.value;
      const archivo = input.files && input.files[0];
      if (!archivo) {
        status.textContent =
          select.value === 'cedula'
            ? 'Seleccione la foto frontal del carnet.'
            : 'Seleccione un archivo.';
        return;
      }
      if (tipo === 'cedula') {
        const mime = (archivo.type || '').toLowerCase();
        const esImagen =
          mime.startsWith('image/') ||
          /\.(jpe?g|png|webp)$/i.test(archivo.name || '');
        if (!esImagen) {
          status.textContent =
            'Del carnet solo se acepta la foto frontal (JPG o PNG). No se pide el reverso.';
          return;
        }
      }
      if (tipo === 'antecedentes') {
        if (SubirConfianza.perfil().antecedentes_verificados) {
          status.textContent = 'El certificado de antecedentes ya está verificado.';
          return;
        }
        btn.disabled = true;
        status.textContent = 'Validando certificado…';
        const res =
          typeof Auth !== 'undefined' && Auth.verificarAntecedentes
            ? await Auth.verificarAntecedentes(archivo)
            : { ok: false, error: 'Sesión no disponible.' };
        btn.disabled = false;
        if (!res.ok) {
          status.textContent = res.error || 'No se pudo validar el certificado.';
          return;
        }
        const data = res.antecedentes || {};
        SubirConfianza.state.docs = SubirConfianza.state.docs.filter(
          (d) => d.tipo !== 'antecedentes'
        );
        SubirConfianza.state.docs.unshift({
          id: String(Date.now()),
          tipo: 'antecedentes',
          nombre: archivo.name,
          tamano: archivo.size,
          fecha: new Date().toISOString(),
          anotaciones: data.antecedentes_anotaciones,
          score: data.antecedentes_score,
          verificado: true
        });
        SubirConfianza.guardar();
        SubirConfianza.init();
        return;
      }
      if (tipo === 'aval') {
        const mime = (archivo.type || '').toLowerCase();
        const esPdf = mime === 'application/pdf' || /\.pdf$/i.test(archivo.name || '');
        if (!esPdf) {
          status.textContent = 'Del aval/garantía solo se acepta PDF.';
          return;
        }
        if (SubirConfianza.perfil().aval_verificado) {
          status.textContent = 'El aval o garantía ya está verificado.';
          return;
        }
        btn.disabled = true;
        status.textContent = 'Validando aval/garantía…';
        const res =
          typeof Auth !== 'undefined' && Auth.verificarAval
            ? await Auth.verificarAval(archivo)
            : { ok: false, error: 'Sesión no disponible.' };
        btn.disabled = false;
        if (!res.ok) {
          status.textContent = res.error || 'No se pudo validar el aval/garantía.';
          return;
        }
        const data = res.aval || {};
        SubirConfianza.state.docs = SubirConfianza.state.docs.filter((d) => d.tipo !== 'aval');
        SubirConfianza.state.docs.unshift({
          id: String(Date.now()),
          tipo: 'aval',
          nombre: archivo.name,
          tamano: archivo.size,
          fecha: new Date().toISOString(),
          score: data.aval_score,
          avalTipo: data.aval_tipo,
          verificado: true
        });
        SubirConfianza.guardar();
        SubirConfianza.init();
        return;
      }
      if (SubirConfianza.tiposDocEmpresa().includes(tipo)) {
        const mime = (archivo.type || '').toLowerCase();
        const esPdf = mime === 'application/pdf' || /\.pdf$/i.test(archivo.name || '');
        if (!esPdf) {
          status.textContent = 'Solo se acepta PDF.';
          return;
        }
        const empresa = SubirConfianza.empresaActual();
        if (!empresa || !empresa.id) {
          status.textContent = 'Cree primero su empresa en Perfil.';
          return;
        }
        if (SubirConfianza.tieneDoc(tipo)) {
          status.textContent = 'Ese documento legal ya está verificado.';
          return;
        }
        btn.disabled = true;
        status.textContent = 'Validando documento legal…';
        const res =
          typeof Auth !== 'undefined' && Auth.verificarDocEmpresa
            ? await Auth.verificarDocEmpresa(empresa.id, tipo, archivo)
            : { ok: false, error: 'Sesión no disponible.' };
        btn.disabled = false;
        if (!res.ok) {
          status.textContent = res.error || 'No se pudo validar el documento.';
          return;
        }
        const data = res.documento || {};
        if (data.docs_empresa) {
          empresa.docs_empresa = data.docs_empresa;
        }
        if (data.indice_transparencia != null) {
          empresa.indice_transparencia = data.indice_transparencia;
        }
        if (data.indice_pct != null) {
          empresa.indice_pct = data.indice_pct;
        }
        SubirConfianza.reputacionMia = Object.assign({}, SubirConfianza.reputacionMia || {}, {
          indice_transparencia: data.indice_transparencia,
          indice_pct: data.indice_pct,
          docs_verificados: data.docs_verificados,
          docs_total: data.docs_total
        });
        const metaTipo =
          (data.docs_empresa && data.docs_empresa[tipo]) || {};
        SubirConfianza.state.docs = SubirConfianza.state.docs.filter((d) => d.tipo !== tipo);
        SubirConfianza.state.docs.unshift({
          id: String(Date.now()),
          tipo,
          nombre: archivo.name,
          tamano: archivo.size,
          fecha: metaTipo.verificado_en || new Date().toISOString(),
          vence_en: metaTipo.vence_en || null,
          score: data.score,
          verificado: true,
          caducado: false
        });
        SubirConfianza.guardar();
        SubirConfianza.init();
        return;
      }
      if (SubirConfianza.tieneDoc(tipo)) {
        status.textContent = 'Ese tipo de documento ya está registrado.';
        return;
      }
      SubirConfianza.state.docs.unshift({
        id: String(Date.now()),
        tipo,
        nombre: archivo.name,
        tamano: archivo.size,
        fecha: new Date().toISOString()
      });
      SubirConfianza.guardar();
      SubirConfianza.init();
    });

    const listaWrap = document.createElement('div');
    listaWrap.className = 'confianza-docs__registrados';

    const listaTitulo = document.createElement('h4');
    listaTitulo.className = 'confianza-docs__lista-titulo';
    listaTitulo.textContent = 'Documentos registrados';

    const lista = document.createElement('ul');
    lista.className = 'confianza-docs__lista';
    if (!SubirConfianza.state.docs.length) {
      const vacio = document.createElement('li');
      vacio.className = 'confianza-docs__vacio';
      vacio.textContent = 'Aún no hay documentos. Sube uno para desbloquear su requisito.';
      lista.appendChild(vacio);
    } else {
      SubirConfianza.state.docs.forEach(doc => {
        const li = document.createElement('li');
        li.className = 'confianza-docs__item';
        if (doc.caducado) li.classList.add('confianza-docs__item--caducado');

        const icono = document.createElement('span');
        icono.className = 'confianza-docs__item-icono';
        icono.setAttribute('aria-hidden', 'true');
        icono.textContent = 'PDF';

        const cuerpo = document.createElement('div');
        cuerpo.className = 'confianza-docs__item-cuerpo';

        const nombre = document.createElement('strong');
        nombre.textContent = doc.nombre;

        const meta = document.createElement('span');
        let metaTxt =
          SubirConfianza.etiquetaTipo(doc.tipo) +
          ' ' +
          SubirConfianza.formatoFecha(doc.fecha) +
          (doc.tamano != null ? ' ' + SubirConfianza.formatoTamano(doc.tamano) : '');
        if (doc.tipo === 'antecedentes' && doc.verificado) {
          metaTxt +=
            ' Anotaciones: ' +
            (doc.anotaciones === true ? 'Sí' : doc.anotaciones === false ? 'No' : '-');
          if (doc.score != null) metaTxt += ' Score ' + doc.score;
        }
        if (doc.tipo === 'aval' && doc.verificado) {
          if (doc.avalTipo) metaTxt += ' ' + doc.avalTipo;
          if (doc.score != null) metaTxt += ' Score ' + doc.score;
        }
        if (doc.vence_en) {
          metaTxt +=
            ' ' +
            (doc.caducado ? 'Caducó' : 'Vence') +
            ' ' +
            SubirConfianza.formatoFecha(doc.vence_en);
        }
        if (doc.caducado) {
          metaTxt += ' Revalide subiendo un PDF nuevo';
        }
        meta.textContent = metaTxt;

        cuerpo.append(nombre, meta);
        li.append(icono, cuerpo);

        if (
          SubirConfianza.tiposDocEmpresa().includes(doc.tipo) &&
          doc.verificado &&
          !doc.caducado
        ) {
          const btnRev = document.createElement('button');
          btnRev.type = 'button';
          btnRev.className = 'history__clear confianza-docs__revocar';
          btnRev.textContent = 'Revocar';
          btnRev.addEventListener('click', async () => {
            const empresa = SubirConfianza.empresaActual();
            if (!empresa || !empresa.id) {
              status.textContent = 'No hay empresa asociada.';
              return;
            }
            if (
              !window.confirm(
                '¿Revocar «' +
                  SubirConfianza.etiquetaTipo(doc.tipo) +
                  '»? Dejará de contar en el índice hasta que revalide.'
              )
            ) {
              return;
            }
            btnRev.disabled = true;
            status.textContent = 'Revocando documento…';
            const res =
              typeof Auth !== 'undefined' && Auth.revocarDocEmpresa
                ? await Auth.revocarDocEmpresa(empresa.id, doc.tipo)
                : { ok: false, error: 'Sesión no disponible.' };
            btnRev.disabled = false;
            if (!res.ok) {
              status.textContent = res.error || 'No se pudo revocar.';
              return;
            }
            const data = res.documento || {};
            if (data.docs_empresa) empresa.docs_empresa = data.docs_empresa;
            if (data.indice_transparencia != null) {
              empresa.indice_transparencia = data.indice_transparencia;
            }
            if (data.indice_pct != null) empresa.indice_pct = data.indice_pct;
            SubirConfianza.reputacionMia = Object.assign(
              {},
              SubirConfianza.reputacionMia || {},
              {
                indice_transparencia: data.indice_transparencia,
                indice_pct: data.indice_pct,
                docs_verificados: data.docs_verificados,
                docs_total: data.docs_total,
                docs_empresa: data.docs_empresa
              }
            );
            SubirConfianza.state.docs = SubirConfianza.state.docs.filter(
              (d) => d.tipo !== doc.tipo
            );
            SubirConfianza.guardar();
            status.textContent =
              data.motivo || 'Documento revocado. Puede revalidar subiendo un PDF nuevo.';
            SubirConfianza.init();
          });
          li.appendChild(btnRev);
        }

        lista.appendChild(li);
      });
    }

    listaWrap.append(listaTitulo, lista);
    wrap.append(head, form, listaWrap);
    return wrap;
  },

    etiquetaTipo(tipo) {
    const mapa = {
      cedula: 'Carnet (frontal)',
      antecedentes: 'Antecedentes',
      aval: 'Aval / garantía',
      carpeta_tributaria: 'Carpeta tributaria (SII)',
      inicio_actividades: 'Inicio de actividades (SII)',
      vigencia_sociedad: 'Vigencia de la sociedad',
      vigencia_poderes: 'Vigencia de poderes',
      poder_representante: 'Poder representante',
      constitucion: 'Constitución',
      f30: 'F30 Dirección del Trabajo',
      no_quiebra: 'No quiebra / concursal',
      antecedentes_rl: 'Antecedentes representante',
      patente: 'Patente municipal',
      titularidad_cuenta: 'Titularidad cuenta bancaria'
    };
    return mapa[tipo] || tipo;
  },

    formatoFecha(iso) {
    try {
      return new Date(iso).toLocaleString('es-CL', { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return iso;
    }
  },

    formatoTamano(bytes) {
    const n = Number(bytes);
    if (!Number.isFinite(n) || n < 0) return '';
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / (1024 * 1024)).toFixed(1) + ' MB';
  }
  });
})();
