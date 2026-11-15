

const Auth = {

  API_BASE: (typeof window !== 'undefined' && window.SERVICHILE_API_BASE) || 'http://localhost:8000',
  STORAGE_KEY: 'servichile.session',
  sesion: null,

  init() {
    Auth.restoreSession();
    return Auth;
  },

  isAuthenticated() {
    return Auth.sesion !== null;
  },

  getCurrentUser() {
    return Auth.sesion;
  },

  async request(path, { method = 'GET', body, token } = {}) {
    const headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (token) headers['Authorization'] = 'Bearer ' + token;
    let res;
    try {
      res = await fetch(Auth.API_BASE + path, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined
      });
    } catch {
      return { ok: false, status: 0, error: 'No se pudo conectar con el servidor. Intente de nuevo.' };
    }
    let data = null;
    try {
      data = await res.json();
    } catch {}
    if (res.ok) return { ok: true, status: res.status, data };
    return { ok: false, status: res.status, error: Auth.mensajeError(res.status, data) };
  },

  mensajeError(status, data) {
    if (status === 429) return 'Demasiados intentos. Espere un minuto e intente de nuevo.';
    if (data && typeof data.detail === 'string') return data.detail;
    if (status === 422) {
      const msg = Auth.mensajeValidacion(data);
      if (msg) return msg;
      return 'Revise los datos ingresados.';
    }
    return 'Ocurrió un error. Intente de nuevo.';
  },

  mensajeValidacion(data) {
    const detalle = data && data.detail;
    if (!Array.isArray(detalle) || !detalle.length) return '';
    const primero = detalle[0] || {};
    const loc = Array.isArray(primero.loc) ? primero.loc : [];
    const campo = String(loc[loc.length - 1] || '');
    const raw = String(primero.msg || '').toLowerCase();
    if (campo === 'email' || raw.includes('email')) {
      return 'Ingrese un correo electrónico válido (por ejemplo nombre@dominio.cl).';
    }
    if (campo === 'password' || raw.includes('password') || raw.includes('at least 8')) {
      return 'La contraseña debe tener al menos 8 caracteres.';
    }
    if (campo === 'nombre') {
      return 'Ingrese un nombre válido (mínimo 2 caracteres).';
    }
    if (campo === 'edad') {
      return 'Ingrese una edad entre 14 y 120 años.';
    }
    if (campo === 'tipo_cuenta') {
      return 'Elija si es proveedor, contratista o persona.';
    }
    if (campo === 'telefono') {
      return 'Ingrese un teléfono válido.';
    }
    if (campo === 'rut') {
      return 'Ingrese un RUT válido.';
    }
    return 'Revise los datos ingresados.';
  },

  async login(email, password) {
    const res = await Auth.request('/v1/auth/login', {
      method: 'POST',
      body: { email: String(email || '').trim(), password: String(password || '') }
    });
    if (!res.ok) return { ok: false, error: res.error };
    return Auth.cargarSesion(res.data.access_token);
  },

  async register(data) {
    const perfil = Auth.limpiarPerfil(data.perfil);
    if (!perfil || !perfil.tipo_cuenta) {
      return {
        ok: false,
        error: 'Elija si es proveedor, contratista o persona.'
      };
    }
    const payload = {
      email: String(data.email || '').trim(),
      nombre: String(data.nombre || '').trim(),
      password: String(data.password || ''),
      perfil
    };
    const res = await Auth.request('/v1/auth/registro', { method: 'POST', body: payload });
    if (!res.ok) return { ok: false, error: res.error };
    return Auth.login(payload.email, payload.password);
  },

  async onboardApi(data) {
    return Auth.register({
      nombre: data.nombre,
      email: data.email,
      password: data.password,
      perfil: {
        edad: data.edad,
        tipo_cuenta: data.tipo_cuenta
      }
    });
  },

  limpiarPerfil(perfil) {
    if (!perfil) return null;
    const limpio = {};
    if (
      perfil.tipo_cuenta === 'persona' ||
      perfil.tipo_cuenta === 'contratista' ||
      perfil.tipo_cuenta === 'proveedor'
    ) {
      limpio.tipo_cuenta = perfil.tipo_cuenta;
    }
    if (perfil.edad !== undefined && perfil.edad !== null && perfil.edad !== '') {
      limpio.edad = Number(perfil.edad);
    }
    return limpio.tipo_cuenta ? limpio : null;
  },

  async eliminarCuenta(password) {
    if (!Auth.sesion) return { ok: false, error: 'Inicie sesión para continuar.' };
    const res = await Auth.request('/v1/auth/yo', { method: 'DELETE', body: { password: String(password || '') }, token: Auth.sesion.token });
    if (res.status === 404 || res.status === 405) {
      return { ok: false, error: 'El servidor no tiene esta función. Reinicie el backend con la versión nueva.' };
    }
    if (!res.ok) return { ok: false, error: res.error };
    Auth.logout();
    return { ok: true };
  },

  async verificarAntecedentes(archivo) {
    if (!Auth.sesion) return { ok: false, error: 'Inicie sesión para continuar.' };
    if (!archivo) return { ok: false, error: 'Seleccione el PDF del certificado.' };
    const nombre = String(archivo.name || '');
    const esPdf =
      String(archivo.type || '') === 'application/pdf' ||
      /\.pdf$/i.test(nombre);
    if (!esPdf) {
      return { ok: false, error: 'Suba el PDF oficial del Registro Civil.' };
    }
    if (archivo.size > 8 * 1024 * 1024) {
      return { ok: false, error: 'El PDF supera 8 MB.' };
    }
    const formulario = new FormData();
    formulario.append('archivo', archivo, nombre || 'antecedentes.pdf');
    formulario.append('nombre_archivo', nombre || 'antecedentes.pdf');
    let res;
    try {
      res = await fetch(Auth.API_BASE + '/v1/perfil/antecedentes', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + Auth.sesion.token },
        body: formulario
      });
    } catch {
      return { ok: false, error: 'No se pudo conectar con el servidor. Intente de nuevo.' };
    }
    let data = null;
    try {
      data = await res.json();
    } catch {}
    if (!res.ok) return { ok: false, error: Auth.mensajeError(res.status, data) };
    await Auth.verificarSesion();
    return { ok: true, antecedentes: data };
  },

  async verificarBiometria(archivo) {
    if (!Auth.sesion) return { ok: false, error: 'Inicie sesión para continuar.' };
    if (!archivo) return { ok: false, error: 'Seleccione o capture una foto.' };
    if (!String(archivo.type || '').startsWith('image/')) {
      return { ok: false, error: 'Suba una foto (JPEG, PNG, WebP o GIF).' };
    }
    if (archivo.size > 5 * 1024 * 1024) {
      return { ok: false, error: 'La foto supera 5 MB. Use una imagen más liviana.' };
    }
    const formulario = new FormData();
    formulario.append('foto', archivo);
    let res;
    try {
      res = await fetch(Auth.API_BASE + '/v1/perfil/biometria', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + Auth.sesion.token },
        body: formulario
      });
    } catch {
      return { ok: false, error: 'No se pudo conectar con el servidor. Intente de nuevo.' };
    }
    let data = null;
    try {
      data = await res.json();
    } catch {}
    if (!res.ok) return { ok: false, error: Auth.mensajeError(res.status, data) };
    await Auth.verificarSesion();
    return { ok: true, biometria: data };
  },

  async actualizarPerfil(cambios) {
    if (!Auth.sesion) return { ok: false, error: 'Inicie sesión para continuar.' };
    const res = await Auth.request('/v1/perfil', { method: 'PATCH', body: cambios, token: Auth.sesion.token });
    if (!res.ok) return { ok: false, error: res.error };
    Auth.sesion.perfil = res.data;
    Auth.persistSession();
    return { ok: true, perfil: res.data };
  },

  async cargarSesion(token) {
    const me = await Auth.request('/v1/auth/yo', { token });
    if (!me.ok) return { ok: false, error: 'No se pudo iniciar sesión. Intente de nuevo.' };
    Auth.sesion = { email: me.data.email, nombre: me.data.nombre, perfil: me.data.perfil || {}, token: token };
    Auth.persistSession();
    return { ok: true, user: Auth.sesion };
  },

  async verificarSesion() {
    if (!Auth.sesion) return false;
    const token = Auth.sesion.token;
    const me = await Auth.request('/v1/auth/yo', { token });

    if (Auth.tokenGuardado() !== token) {
      Auth.sesion = null;
      Auth.restoreSession();
      return Auth.isAuthenticated();
    }
    if (me.ok) {
      Auth.sesion.nombre = me.data.nombre;
      Auth.sesion.perfil = me.data.perfil || {};
      Auth.persistSession();
      return true;
    }
    if (me.status === 0) return true;
    Auth.logout();
    return false;
  },

  tokenGuardado() {
    try {
      const raw = localStorage.getItem(Auth.STORAGE_KEY);
      return raw ? (JSON.parse(raw) || {}).token || null : null;
    } catch (e) {
      return null;
    }
  },

  logout() {
    Auth.sesion = null;
    try {
      localStorage.removeItem(Auth.STORAGE_KEY);
    } catch {}
  },

  persistSession() {
    try {
      localStorage.setItem(Auth.STORAGE_KEY, JSON.stringify(Auth.sesion));
    } catch {}
  },

  restoreSession() {
    try {
      const raw = localStorage.getItem(Auth.STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && parsed.token) {
        Auth.sesion = { email: parsed.email, nombre: parsed.nombre, perfil: parsed.perfil || {}, token: parsed.token };
      }
    } catch (e) {
      Auth.sesion = null;
    }
  }
};
