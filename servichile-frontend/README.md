# ServiChile PWA

Aplicación web progresiva de **catálogo B2B** e índice de transparencia de proveedores, con capa de confianza (Reportes / QR + verificación).

## Pantallas

| Ruta | Archivo | Función |
|---|---|---|
| `/` | `index.html` | Acceso y app completa |
| `/onboarding/` | `onboarding/index.html` | Alta proveedor / contratista / persona |

Vistas internas:

- **Explorar**: proveedores B2B con índice de transparencia.
- **Reportes**: informe imprimible (persona/contratista: niveles; proveedor: 30 observables) + QR y validador.
- **Verificación**: niveles 1–3 (persona/contratista) o documentación / índice (proveedor).
- **Perfil**: datos de cuenta y estado de verificación.

## Estructura

| Ruta | Contenido |
|---|---|
| `index.html` | Estructura de vistas |
| `onboarding/index.html` | Bienvenida |
| `css/styles.css` | Estilos |
| `js/app.js` | Vistas, menú y perfil |
| `js/core/auth.js` | Sesión API |
| `js/core/security.js` | RUT / PII en cliente |
| `js/compliance.js` | Cookies e incidentes locales |
| `js/modules/market.js` | Explorar proveedores |
| `js/modules/reporte-qr.js` | Emisión/validación del QR del reporte (`/v1/reporte`) |
| `js/modules/subir-confianza.js` | Verificación |
| `js/modules/reporte-persona.js` | Informe persona |
| `js/modules/reporte-empresa.js` | Informe empresa |
| `js/modules/progreso-cuenta.js` | Estrategia proveedor / contratista / persona |
| `js/onboarding.js` | Alta de cuenta |
| `sw.js` | Service Worker |
| `manifest.json` | PWA |

## Desarrollo local

```bash
# API
cd servichile-backend && source .venv/bin/activate && uvicorn app.principal:app --reload

# Frontend (incluye página 404 con diseño ServiChile)
cd servichile-frontend && python3 serve.py 5500
```

- App: http://localhost:5500/index.html  
- API: http://localhost:8000/docs  
- 404: cualquier ruta inexistente (p. ej. `/no-existe`) muestra `404.html`
