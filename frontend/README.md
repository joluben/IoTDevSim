# Frontend Project

Estructura creada según las reglas de `frontend_rules.md`.

## Estructura
- `public/`: estáticos públicos (index.html, favicon).
- `src/`: código fuente de la aplicación.
  - `assets/` fuentes, íconos, imágenes.
  - `app/` configuración central, router, providers, store.
  - `components/` UI reusable (shadcn/ui wrappers), layout, forms, common.
  - `features/` dominios (auth, dashboard, profile).
  - `hooks/` hooks personalizados.
  - `services/` comunicación con APIs.
  - `types/` tipos e interfaces TypeScript.
  - `utils/` utilidades y validadores.
  - `styles/` estilos globales (Tailwind + variables).
  - `pages/` componentes de página.
  - `tests/` pruebas con Jest + React Testing Library.

## Reglas
- TypeScript estricto, sin `any`.
- Tailwind + shadcn/ui para UI.
- Sin lógica de negocio en componentes.
- Servicios para llamadas a API.
- Accesibilidad y pruebas obligatorias.
