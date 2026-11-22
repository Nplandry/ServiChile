/* Parte de SubirConfianza */
(function () {
  const T = (window.SubirConfianza = window.SubirConfianza || {});
  Object.assign(T, {
    cedulaHecha() {
    const p = SubirConfianza.perfil();
    return !!(p.cedula_verificada || p.rut_verificado);
  },

    bloqueCedula() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-bio config-card';
    wrap.setAttribute('aria-label', 'Validación de cédula');

    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = 'Foto frontal del carnet';

    const lead = document.createElement('p');
    lead.className = 'section-lead';

    const status = document.createElement('p');
    status.className = 'status-text confianza-bio__status';
    status.setAttribute('role', 'status');

    const perfil = SubirConfianza.perfil();
    if (perfil.cedula_verificada) {
      lead.textContent =
        'Carnet validado (OCR + face-match con su selfie).';
      const partes = [];
      if (perfil.cedula_verificada_en) {
        partes.push('Validada el ' + SubirConfianza.formatoFecha(perfil.cedula_verificada_en));
      }
      if (perfil.cedula_score != null) partes.push('score ' + perfil.cedula_score + '/100');
      status.textContent = (partes.join(' ') || 'Cédula verificada') + '.';
      wrap.append(titulo, lead, status);
      return wrap;
    }

    if (!perfil.biometria_verificada) {
      lead.textContent =
        'Primero complete la verificación biométrica (selfie). Se usa para comparar el rostro del carnet.';
      status.textContent = 'Bloqueado hasta tener selfie biométrica.';
      wrap.append(titulo, lead, status);
      return wrap;
    }

    if (perfil.rut_verificado) {
      lead.textContent =
        'Ya tiene RUT verificado. Puede reforzar con la foto frontal: OCR + face-match contra su selfie.';
    } else {
      lead.textContent =
        'Encaje el frente del carnet en el marco. Se valida con OCR local, ROI del RUN y face-match contra su selfie.';
    }

    const previewWrap = document.createElement('div');
    previewWrap.className = 'confianza-cedula__preview-wrap';
    previewWrap.hidden = true;
    const preview = document.createElement('img');
    preview.className = 'confianza-cedula__preview-img';
    preview.alt = 'Vista previa del carnet';
    previewWrap.append(preview);

    const file = document.createElement('input');
    file.type = 'file';
    file.accept = 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp';
    file.className = 'confianza-docs__file';
    file.id = 'confianzaCedulaArchivo';

    const dropLabel = document.createElement('label');
    dropLabel.className = 'confianza-docs__drop-label';
    dropLabel.htmlFor = 'confianzaCedulaArchivo';
    dropLabel.innerHTML =
      '<span class="confianza-docs__drop-titulo">Elegir foto frontal</span>' +
      '<span class="confianza-docs__drop-hint">Solo el frente JPG o PNG sin reverso</span>' +
      '<span class="confianza-docs__drop-nombre" id="confianzaCedulaNombre">Ninguna foto seleccionada</span>';

    const drop = document.createElement('div');
    drop.className = 'confianza-docs__drop';
    drop.append(file, dropLabel);

    const acciones = document.createElement('div');
    acciones.className = 'confianza-bio__acciones';

    const btnCam = document.createElement('button');
    btnCam.type = 'button';
    btnCam.className = 'confianza-bio__btn confianza-bio__btn--cam';
    btnCam.textContent = 'Abrir cámara (trasera)';

    const btnCapturar = document.createElement('button');
    btnCapturar.type = 'button';
    btnCapturar.className = 'confianza-bio__btn';
    btnCapturar.textContent = 'Capturar carnet';
    btnCapturar.hidden = true;

    const btnReintentar = document.createElement('button');
    btnReintentar.type = 'button';
    btnReintentar.className = 'confianza-bio__btn confianza-bio__btn--retry';
    btnReintentar.textContent = 'Reintentar captura';
    btnReintentar.hidden = true;

    acciones.append(btnCam, btnCapturar, btnReintentar);

    const visor = document.createElement('div');
    visor.className = 'confianza-cedula__visor';
    visor.hidden = true;
    const video = document.createElement('video');
    video.className = 'confianza-cedula__video';
    video.setAttribute('playsinline', '');
    video.muted = true;
    video.autoplay = true;
    video.playsInline = true;
    const mascara = document.createElement('div');
    mascara.className = 'confianza-cedula__mascara';
    mascara.setAttribute('aria-hidden', 'true');
    const guia = document.createElement('p');
    guia.className = 'confianza-cedula__guia';
    guia.textContent = 'Encaje el frente del carnet en el marco';
    const canvas = document.createElement('canvas');
    canvas.hidden = true;
    visor.append(video, mascara, guia, canvas);

    const consentWrap = document.createElement('label');
    consentWrap.className = 'confianza-bio__consent';
    const consent = document.createElement('input');
    consent.type = 'checkbox';
    consent.id = 'confianzaCedulaConsent';
    const consentTxt = document.createElement('span');
    consentTxt.textContent =
      'Autorizo procesar la foto frontal de mi carnet.';
    consentWrap.append(consent, consentTxt);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'submit-btn confianza-bio__enviar';
    btn.textContent = 'Validar carnet';
    btn.disabled = true;

    let archivoElegido = null;
    let stream = null;
    let enviando = false;
    let previewUrl = null;
    const nombreSpan = () => document.getElementById('confianzaCedulaNombre');

    function actualizarEnviar() {
      btn.disabled = enviando || !(archivoElegido && consent.checked);
    }

    function limpiarPreviewUrl() {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        previewUrl = null;
      }
    }

    function setArchivo(archivo, etiqueta) {
      archivoElegido = archivo || null;
      limpiarPreviewUrl();
      const span = nombreSpan();
      if (span) {
        span.textContent = archivoElegido
          ? (etiqueta || archivoElegido.name) +
            ' ' +
            SubirConfianza.formatoTamano(archivoElegido.size)
          : 'Ninguna foto seleccionada';
      }
      drop.classList.toggle('confianza-docs__drop--lleno', !!archivoElegido);
      if (archivoElegido) {
        previewUrl = URL.createObjectURL(archivoElegido);
        preview.src = previewUrl;
        previewWrap.hidden = false;
        btnReintentar.hidden = false;
      } else {
        previewWrap.hidden = true;
        preview.removeAttribute('src');
        btnReintentar.hidden = true;
      }
      actualizarEnviar();
      if (archivoElegido && !consent.checked) {
        status.textContent = 'Foto lista. Marque el consentimiento para validar.';
      } else if (archivoElegido) {
        status.textContent = 'Foto lista. Pulse Validar carnet.';
      }
    }

    function detenerCamara() {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }
      video.srcObject = null;
    }

    async function abrirCamara() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        status.textContent = 'Este dispositivo no permite usar la cámara.';
        return;
      }
      btnCam.disabled = true;
      status.textContent = 'Abriendo cámara trasera…';
      try {
        detenerCamara();
        setArchivo(null);
        file.value = '';
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 1600 },
            height: { ideal: 900 }
          },
          audio: false
        });
        video.srcObject = stream;
        await video.play();
        visor.hidden = false;
        btnCapturar.hidden = false;
        btnReintentar.hidden = true;
        status.textContent = 'Encaje el carnet en el marco blanco y capture.';
      } catch {
        detenerCamara();
        status.textContent = 'No se pudo abrir la cámara. Use Elegir foto frontal.';
      } finally {
        btnCam.disabled = false;
      }
    }

    function prepararReintento(mensaje) {
      detenerCamara();
      visor.hidden = true;
      btnCapturar.hidden = true;
      setArchivo(null);
      file.value = '';
      btnReintentar.hidden = false;
      status.textContent = mensaje;
      actualizarEnviar();
    }

    file.addEventListener('change', () => {
      const f = file.files && file.files[0];
      if (!f) {
        setArchivo(null);
        return;
      }
      if (!String(f.type || '').startsWith('image/')) {
        status.textContent = 'Solo se acepta la foto frontal (JPG o PNG).';
        file.value = '';
        setArchivo(null);
        return;
      }
      detenerCamara();
      visor.hidden = true;
      btnCapturar.hidden = true;
      setArchivo(f);
    });

    consent.addEventListener('change', () => {
      actualizarEnviar();
      if (archivoElegido && !enviando) {
        status.textContent = consent.checked
          ? 'Foto lista. Pulse Validar carnet.'
          : 'Foto lista. Marque el consentimiento para validar.';
      }
    });

    btnCam.addEventListener('click', () => {
      abrirCamara();
    });

    btnReintentar.addEventListener('click', () => {
      abrirCamara();
    });

    btnCapturar.addEventListener('click', async () => {
      if (!stream || video.videoWidth < 2) {
        status.textContent = 'La cámara aún no está lista.';
        return;
      }

      const vw = video.videoWidth;
      const vh = video.videoHeight;
      const targetRatio = 1.586;
      let cw;
      let ch;
      if (vw / vh > targetRatio) {
        ch = Math.floor(vh * 0.78);
        cw = Math.floor(ch * targetRatio);
      } else {
        cw = Math.floor(vw * 0.88);
        ch = Math.floor(cw / targetRatio);
      }
      const sx = Math.floor((vw - cw) / 2);
      const sy = Math.floor((vh - ch) / 2);
      canvas.width = cw;
      canvas.height = ch;
      const ctx = canvas.getContext('2d', { alpha: false });
      ctx.drawImage(video, sx, sy, cw, ch, 0, 0, cw, ch);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.93));
      detenerCamara();
      visor.hidden = true;
      btnCapturar.hidden = true;
      if (!blob || blob.size < 1500) {
        prepararReintento('No se pudo capturar. Reintente o suba un archivo.');
        return;
      }
      setArchivo(new File([blob], 'carnet-frontal.jpg', { type: 'image/jpeg' }), 'Captura');
    });

    btn.addEventListener('click', async () => {
      if (enviando) return;
      if (!archivoElegido) {
        status.textContent = 'Seleccione o capture la foto frontal.';
        return;
      }
      if (!consent.checked) {
        status.textContent = 'Debe aceptar el procesamiento de la foto del carnet.';
        actualizarEnviar();
        return;
      }
      enviando = true;
      actualizarEnviar();
      status.textContent = 'Validando: OCR + face-match con su selfie…';
      const res = await Auth.verificarCedula(archivoElegido);
      if (!res.ok) {
        enviando = false;
        prepararReintento(
          (res.error || 'No se pudo validar el carnet.') + ' Pulse Reintentar captura.'
        );
        return;
      }
      detenerCamara();
      limpiarPreviewUrl();
      SubirConfianza.init();
    });

    wrap.append(
      titulo,
      lead,
      drop,
      previewWrap,
      visor,
      acciones,
      consentWrap,
      btn,
      status
    );
    return wrap;
  },

    bloqueBiometria() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-bio config-card';
    wrap.setAttribute('aria-label', 'Verificación biométrica');

    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = 'Verificación biométrica';

    const lead = document.createElement('p');
    lead.className = 'section-lead';

    const status = document.createElement('p');
    status.className = 'status-text confianza-bio__status';
    status.setAttribute('role', 'status');

    const hecha = SubirConfianza.biometriaHecha();

    if (hecha) {
      const perfil = SubirConfianza.perfil();
      lead.textContent =
        'Identidad verificada. Se guardó una copia comprimida de la selfie con acceso restringido y retención limitada.';
      const partes = [];
      if (perfil.biometria_verificada_en) {
        partes.push(
          'Completada el ' + SubirConfianza.formatoFecha(perfil.biometria_verificada_en)
        );
      } else {
        partes.push('Biometría completada');
      }
      if (perfil.biometria_retener_hasta) {
        partes.push(
          'retención hasta ' + SubirConfianza.formatoFecha(perfil.biometria_retener_hasta)
        );
      }
      if (perfil.biometria_bytes) {
        partes.push(SubirConfianza.formatoTamano(perfil.biometria_bytes));
      }
      status.textContent = partes.join(' ') + '.';
      wrap.append(titulo, lead, status);
      return wrap;
    }

    lead.textContent =
      'Abra la cámara frontal, encuadre su rostro y capture la selfie. Se guardará una copia comprimida solo para verificación de identidad, con retención limitada, y se borrará al eliminar la cuenta.';

    const visor = document.createElement('div');
    visor.className = 'confianza-bio__preview';
    visor.hidden = true;

    const video = document.createElement('video');
    video.className = 'confianza-bio__video-src';
    video.setAttribute('playsinline', '');
    video.setAttribute('muted', '');
    video.muted = true;
    video.autoplay = true;
    video.playsInline = true;

    const canvas = document.createElement('canvas');
    canvas.className = 'confianza-bio__canvas';
    canvas.setAttribute('aria-label', 'Vista de la selfie');

    visor.append(video, canvas);

    let stream = null;
    let archivoElegido = null;
    let rafId = 0;
    let congelado = false;
    const ctx = canvas.getContext('2d', { alpha: false });

    function detenerLoop() {
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
    }

    function detenerCamara() {
      detenerLoop();
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }
      video.srcObject = null;
    }

    function pintarFrame() {
      if (!stream || congelado || !ctx) return;
      const w = video.videoWidth;
      const h = video.videoHeight;
      if (w > 0 && h > 0) {
        if (canvas.width !== w || canvas.height !== h) {
          canvas.width = w;
          canvas.height = h;
        }

        ctx.save();
        ctx.translate(w, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(video, 0, 0, w, h);
        ctx.restore();
      }
      rafId = requestAnimationFrame(pintarFrame);
    }

    const acciones = document.createElement('div');
    acciones.className = 'confianza-bio__acciones';

    const btnAbrir = document.createElement('button');
    btnAbrir.type = 'button';
    btnAbrir.className = 'confianza-bio__btn confianza-bio__btn--cam';
    btnAbrir.textContent = 'Abrir cámara';

    const btnCapturar = document.createElement('button');
    btnCapturar.type = 'button';
    btnCapturar.className = 'confianza-bio__btn';
    btnCapturar.textContent = 'Capturar selfie';
    btnCapturar.hidden = true;

    const btnOtra = document.createElement('button');
    btnOtra.type = 'button';
    btnOtra.className = 'confianza-bio__btn';
    btnOtra.textContent = 'Volver a capturar';
    btnOtra.hidden = true;

    const btn = document.createElement('button');
    btn.className = 'submit-btn confianza-bio__enviar';
    btn.type = 'button';
    btn.textContent = 'Verificar identidad';
    btn.disabled = true;

    const consentWrap = document.createElement('label');
    consentWrap.className = 'confianza-bio__consent';
    const consent = document.createElement('input');
    consent.type = 'checkbox';
    consent.id = 'confianzaBioConsent';
    const consentTxt = document.createElement('span');
    consentTxt.textContent =
      'Autorizo guardar una copia comprimida de mi selfie para verificar identidad, con acceso restringido y retención limitada. Se borrará al eliminar mi cuenta.';
    consentWrap.append(consent, consentTxt);

    let enviando = false;

    function mensajeListo() {
      if (!archivoElegido) return;
      status.textContent = consent.checked
        ? 'Selfie lista. Pulse Verificar identidad.'
        : 'Selfie lista. Marque el consentimiento para continuar.';
    }

    function actualizarEnviar() {
      btn.disabled = enviando || !(archivoElegido && consent.checked);
      btn.setAttribute('aria-disabled', btn.disabled ? 'true' : 'false');
    }

    function uiInicial() {
      btnAbrir.hidden = false;
      btnAbrir.disabled = false;
      btnAbrir.textContent = 'Abrir cámara';
      btnCapturar.hidden = true;
      btnOtra.hidden = true;
      actualizarEnviar();
    }

    function uiCamaraLista() {
      btnAbrir.hidden = true;
      btnCapturar.hidden = false;
      btnOtra.hidden = true;
      actualizarEnviar();
    }

    function uiTrasCaptura() {
      btnAbrir.hidden = true;
      btnCapturar.hidden = true;
      btnOtra.hidden = false;
      actualizarEnviar();
      mensajeListo();
    }

    consent.addEventListener('change', () => {
      actualizarEnviar();
      if (archivoElegido && !enviando) mensajeListo();
    });
    uiInicial();

    btnAbrir.addEventListener('click', async () => {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        status.textContent = 'Este dispositivo no permite usar la cámara desde el navegador.';
        return;
      }
      btnAbrir.disabled = true;
      btnCapturar.hidden = true;
      status.textContent = 'Pidiendo acceso a la cámara…';
      try {
        detenerCamara();
        archivoElegido = null;
        congelado = false;
        actualizarEnviar();
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'user' },
            width: { ideal: 640 },
            height: { ideal: 480 }
          },
          audio: false
        });
        video.srcObject = stream;
        await video.play();
        await new Promise((resolve) => {
          if (video.videoWidth > 0) {
            resolve();
            return;
          }
          const listo = () => {
            video.removeEventListener('loadeddata', listo);
            resolve();
          };
          video.addEventListener('loadeddata', listo);
          setTimeout(resolve, 1500);
        });
        visor.hidden = false;
        detenerLoop();
        pintarFrame();
        uiCamaraLista();
        status.textContent = 'Centre su rostro y pulse Capturar selfie.';
      } catch {
        detenerCamara();
        status.textContent = 'No se pudo abrir la cámara. Permita el acceso e intente de nuevo.';
        uiInicial();
      }
    });

    btnCapturar.addEventListener('click', async () => {
      if (!stream || !ctx || canvas.width < 2 || canvas.height < 2) {
        status.textContent = 'La cámara aún no está lista.';
        return;
      }

      congelado = true;
      detenerLoop();

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92));
      if (!blob || blob.size < 500) {
        congelado = false;
        pintarFrame();
        archivoElegido = null;
        actualizarEnviar();
        status.textContent = 'No se pudo capturar la foto. Intente de nuevo.';
        return;
      }

      archivoElegido = new File([blob], 'selfie.jpg', { type: 'image/jpeg' });

      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }
      video.srcObject = null;
      uiTrasCaptura();
    });

    btnOtra.addEventListener('click', () => {
      if (enviando) return;
      archivoElegido = null;
      congelado = false;
      actualizarEnviar();
      uiInicial();
      btnAbrir.click();
    });

    btn.addEventListener('click', async () => {
      if (enviando) return;
      if (!archivoElegido) {
        status.textContent = 'Primero capture una selfie.';
        actualizarEnviar();
        return;
      }
      if (!consent.checked) {
        status.textContent =
          'Debe aceptar el almacenamiento de la selfie comprimida para continuar.';
        actualizarEnviar();
        return;
      }
      enviando = true;
      actualizarEnviar();
      status.textContent = 'Verificando y guardando copia comprimida…';
      const res = await Auth.verificarBiometria(archivoElegido);
      if (!res.ok) {
        enviando = false;
        status.textContent = res.error || 'No se pudo verificar.';
        actualizarEnviar();
        return;
      }
      detenerCamara();
      SubirConfianza.sincronizarBiometria();
      SubirConfianza.init();
    });

    acciones.append(btnAbrir, btnCapturar, btnOtra);

    const nota = document.createElement('p');
    nota.className = 'confianza-bio__nota';
    nota.textContent =
      'Dato sensible: la foto no se publica. Solo metadata aparece en su perfil (tamaño y fecha de retención).';

    wrap.append(titulo, lead, visor, acciones, consentWrap, btn, status, nota);
    return wrap;
  }
  });
})();
