/* Parte de SubirConfianza */
(function () {
  const T = (window.SubirConfianza = window.SubirConfianza || {});
  Object.assign(T, {
    STORAGE_KEY: 'servichile.subirConfianza.cache',

    STORAGE_KEY_LEGACY: 'servichile.subirConfianza.mock',

    carruselIdx: 0,

    tablaAbierta: false,

    NIVELES: [
    {
      id: 1,
      titulo: 'Nivel 1 Identidad',
      evalua: 'Que la persona sea real, accesible y localizable',
      requisito: 'Cuenta activa, identidad verificada y datos de contacto con mayoría de edad.',
      usos: 'Primeros contactos, QR de reporte y primeros trabajos con baja fricción.',
      discriminatorio: false,
      discriminatorioNota: 'NO - base para cualquier trato',
      tareas: [
        {
          id: 'n1-registro',
          label: 'Crear cuenta e iniciar sesión',
          como: 'Se completa al registrarse y mantener una sesión activa en la plataforma.'
        },
        {
          id: 'n1-cedula',
          label: 'Verificar su identidad',
          como: 'Se completa al verificar el RUT en el perfil o al validar la foto frontal del carnet (OCR local, sin reverso).'
        },
        {
          id: 'n1-perfil',
          label: 'Completar teléfono y edad',
          como: 'Se completa al guardar un teléfono móvil y declarar edad de 18 años o más.'
        }
      ]
    },
    {
      id: 2,
      titulo: 'Nivel 2 Cumplimiento',
      evalua: 'Que concreté trabajos y mantenga buen historial',
      requisito: 'Al menos un trabajo concretado, reputación alta y pocos no concretados.',
      usos: 'Trabajos concretados, entregas y tratos recurrentes con respaldo de comportamiento.',
      discriminatorio: false,
      discriminatorioNota: 'NO - se gana concretando trabajos',
      tareas: [
        {
          id: 'n2-concretados',
          label: 'Concretar al menos un trabajo',
          como: 'Se completa cuando el titular marca al menos un trabajo como concretado.'
        },
        {
          id: 'n2-puntualidad',
          label: 'Mantener buena reputación',
          como: 'Se completa cuando el puntaje de confiabilidad alcanza 85% o más.'
        },
        {
          id: 'n2-no-concretados',
          label: 'Mantener pocos no concretados',
          como: 'Se completa cuando la tasa de trabajos no concretados se mantiene bajo 15%.'
        }
      ]
    },
    {
      id: 3,
      titulo: 'Nivel 3 Identidad reforzada',
      evalua: 'Mayor certeza para tratos de alto valor',
      requisito: 'Antecedentes, verificación facial y un aval o garantía.',
      usos: 'Contratos sensibles, entregas de alto valor y menor riesgo para ambas partes.',
      discriminatorio: false,
      discriminatorioNota: 'NO - refuerza identidad, no mide plata',
      tareas: [
        {
          id: 'n3-antecedentes',
          label: 'Presentar certificado de antecedentes',
          como: 'Se completa al cargar el certificado de antecedentes o un certificado comercial equivalente.'
        },
        {
          id: 'n3-biometria',
          label: 'Confirmar identidad con foto',
          como: 'Se completa al aprobar la verificación facial; se guarda una copia comprimida con retención limitada.'
        },
        {
          id: 'n3-aval',
          label: 'Registrar un aval o garantía',
          como: 'Se completa al cargar un aval, garantía o documento de respaldo.'
        }
      ]
    }
  ],

    state: {
    docs: [],
    biometriaOk: false
  },

    empresas: null,

    reputacionMia: null,

    STORAGE_EMPRESA: 'servichile.empresa.seleccionada',

    async init() {
    SubirConfianza.cargar();
    const raiz = document.getElementById('subirConfianzaRaiz');
    if (!raiz) return;
    await SubirConfianza.cargarEmpresas();
    SubirConfianza.render(raiz);
  },

    storageQuien() {
    const user = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    return user && user.email ? String(user.email).toLowerCase() : 'anon';
  },

    claveSeleccion() {
    return SubirConfianza.STORAGE_EMPRESA + ':' + SubirConfianza.storageQuien();
  },

    leerSeleccionId() {
    try {
      return localStorage.getItem(SubirConfianza.claveSeleccion()) || '';
    } catch (_) {
      return '';
    }
  },

    guardarSeleccionId(id) {
    try {
      if (id) localStorage.setItem(SubirConfianza.claveSeleccion(), String(id));
      else localStorage.removeItem(SubirConfianza.claveSeleccion());
    } catch (_) {

    }
  },

    elegirNegocio(lista) {
    if (!Array.isArray(lista) || !lista.length) return null;
    const want = SubirConfianza.leerSeleccionId();
    if (want) {
      const hit = lista.find((n) => String(n.id) === want);
      if (hit) return hit;
    }
    return lista[0];
  },

    async cargarEmpresas() {
    SubirConfianza.empresas = [];
    SubirConfianza.reputacionMia = null;
    if (typeof Auth === 'undefined' || !Auth.isAuthenticated() || !Auth.request) {
      return [];
    }
    try {
      const mias = await Auth.request('/v1/businesses/mias', {
        token: Auth.sesion.token
      });
      const lista = mias && Array.isArray(mias.data) ? mias.data : [];
      SubirConfianza.empresas = lista;
      if (!lista.length) return [];
      const actual = SubirConfianza.elegirNegocio(lista);
      if (actual && actual.id) SubirConfianza.guardarSeleccionId(actual.id);
      SubirConfianza.sincronizarDocsEmpresaDesdeApi(actual);
      const res = await Auth.request(
        '/v1/businesses/' + encodeURIComponent(actual.id) + '/reputation',
        { token: Auth.sesion.token }
      );
      if (res && res.ok && res.data) {
        SubirConfianza.reputacionMia = res.data;

        if (actual.indice_transparencia == null && res.data.indice_transparencia != null) {
          actual.indice_transparencia = res.data.indice_transparencia;
        }
        if (actual.indice_pct == null && res.data.indice_pct != null) {
          actual.indice_pct = res.data.indice_pct;
        }
      }
      return lista;
    } catch (_e) {
      SubirConfianza.empresas = [];
      return [];
    }
  },

    tieneEmpresa() {
    return Array.isArray(SubirConfianza.empresas) && SubirConfianza.empresas.length > 0;
  },

    empresaActual() {
    return SubirConfianza.elegirNegocio(SubirConfianza.empresas);
  },

    storageKey() {
    return SubirConfianza.STORAGE_KEY + ':' + SubirConfianza.storageQuien();
  },

    cargar() {
    try {
      const quien = SubirConfianza.storageQuien();
      const clave = SubirConfianza.STORAGE_KEY + ':' + quien;
      const legacy = SubirConfianza.STORAGE_KEY_LEGACY + ':' + quien;
      let raw = localStorage.getItem(clave);
      if (!raw) {
        raw = localStorage.getItem(legacy);
        if (raw) {
          localStorage.setItem(clave, raw);
          localStorage.removeItem(legacy);
        }
      }
      try {
        localStorage.removeItem(SubirConfianza.STORAGE_KEY_LEGACY);
      } catch {}
      if (!raw) {
        SubirConfianza.state = { docs: [], biometriaOk: false };
      } else {
        const parsed = JSON.parse(raw);
        SubirConfianza.state.docs = Array.isArray(parsed.docs) ? parsed.docs : [];
        SubirConfianza.state.biometriaOk = false;
      }
    } catch {
      SubirConfianza.state = { docs: [], biometriaOk: false };
    }
    SubirConfianza.sincronizarBiometria();
  },

    sincronizarBiometria() {
    const serverOk = !!SubirConfianza.perfil().biometria_verificada;
    SubirConfianza.state.biometriaOk = serverOk;
    SubirConfianza.guardar();
  },

    guardar() {
    try {
      localStorage.setItem(
        SubirConfianza.storageKey(),
        JSON.stringify({
          docs: SubirConfianza.state.docs

        })
      );
    } catch {}
  },

    perfil() {
    const user = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    return (user && user.perfil) || {};
  },

    esProveedor() {
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.esProveedor()
      : SubirConfianza.perfil().tipo_cuenta === 'proveedor';
  },

    esEmpresa() {
    return SubirConfianza.esProveedor();
  },

    biometriaHecha() {
    return !!SubirConfianza.perfil().biometria_verificada;
  },

    tiposDocumento() {
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.actual().tiposDocumento()
      : [];
  },

    fichaEmpresa() {
    const empresa = SubirConfianza.empresaActual();
    const rep = SubirConfianza.reputacionMia;
    if (!empresa) {
      return {
        id: null,
        nombre: 'Sin empresa',
        indice_transparencia: null,
        indice_pct: null,
        _docsCargados: 0,
        _docsTotal: 0,
        _sinFicha: true
      };
    }
    const ids =
      typeof ProgresoCuenta !== 'undefined'
        ? ProgresoCuenta.de('proveedor').idsDocumento()
        : [];
    let docs = 0;
    for (let i = 0; i < ids.length; i++) {
      if (SubirConfianza.tieneDoc(ids[i])) docs += 1;
    }

    const repOk =
      !!rep &&
      (rep.business_id == null || String(rep.business_id) === String(empresa.id));
    if (repOk && rep.docs_verificados != null) docs = Number(rep.docs_verificados);
    const totalDocs =
      repOk && rep.docs_total != null ? Number(rep.docs_total) : ids.length || 11;

    const enMarket =
      typeof Market !== 'undefined' && Array.isArray(Market.negocios)
        ? Market.negocios.find((n) => n && String(n.id) === String(empresa.id))
        : null;
    const indice =
      enMarket && enMarket.indice_transparencia != null
        ? Number(enMarket.indice_transparencia)
        : empresa.indice_transparencia != null
          ? Number(empresa.indice_transparencia)
          : repOk && rep.indice_transparencia != null
            ? Number(rep.indice_transparencia)
            : null;
    const pct =
      enMarket && enMarket.indice_pct != null
        ? Number(enMarket.indice_pct)
        : empresa.indice_pct != null
          ? Number(empresa.indice_pct)
          : repOk && rep.indice_pct != null
            ? Number(rep.indice_pct)
            : indice != null
              ? Math.round((indice / 10) * 100)
              : null;
    return {
      id: empresa.id,
      nombre: empresa.nombre || 'Mi empresa',
      rut_empresa: (empresa.rut_empresa || '').trim() || null,
      telefono: (empresa.telefono || '').trim() || null,
      sitio_web: (empresa.sitio_web || '').trim() || null,
      direccion: (empresa.direccion || '').trim() || null,
      indice_transparencia: indice,
      indice_pct: pct,
      _docsCargados: docs,
      _docsTotal: totalDocs,
      _sinFicha: false
    };
  },

    bloqueSinEmpresa() {
    if (typeof ReporteEmpresa !== 'undefined' && ReporteEmpresa.renderAvisoSinFicha) {
      return ReporteEmpresa.renderAvisoSinFicha();
    }
    const box = document.createElement('section');
    box.className = 'reporte-sin-ficha';
    const titulo = document.createElement('h2');
    titulo.className = 'section-heading';
    titulo.textContent = 'Aún no tiene una ficha de empresa';
    const lead = document.createElement('p');
    lead.className = 'section-lead';
    lead.textContent =
      'Cree su empresa en Perfil para ver el índice de transparencia y cargar documentos legales.';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'submit-btn';
    btn.textContent = 'Ir a Perfil a crear la empresa';
    btn.addEventListener('click', () => {
      if (typeof App !== 'undefined' && App.openSection) App.openSection('perfil');
    });
    box.append(titulo, lead, btn);
    return box;
  }
  });
})();
