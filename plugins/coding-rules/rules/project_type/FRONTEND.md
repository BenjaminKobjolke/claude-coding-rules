# Version
1

Increase this version number whenever this rule file changes.

# Frontend SPA Rules

These rules apply to all frontend single-page application projects, regardless of framework.
See `COMMON_RULES.md` for rules that apply to all languages.

---

## Build Tooling

Use Vite as the build tool with ES modules (`"type": "module"` in package.json).

### Base Path

Always set `base: './'` for relative asset paths. This allows deployment in any subdirectory without reconfiguration:

```javascript
// vite.config.js
export default defineConfig({
  base: './',
});
```

### Dev Server Proxy

Proxy API requests to the backend during development to avoid CORS issues:

```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost/your-backend-api',
        changeOrigin: true,
      },
    },
  },
});
```

---

## Styling

Use Tailwind CSS with PostCSS and Autoprefixer.

### Dark Mode

Use OS-aware dark mode via the `media` strategy — no manual toggle needed:

```javascript
// tailwind.config.js
export default {
  darkMode: 'media',
  content: ['./index.html', './src/**/*.{svelte,js,ts,jsx,tsx}'],
};
```

### Global Styles

Import Tailwind layers in a single global CSS file:

```css
/* src/app.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### PostCSS

```javascript
// postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

### SCSS/Sass (Optional)

SCSS can be used alongside Tailwind for complex component styles, or as the sole styling approach.
See `SCSS_RULES.md` for detailed rules on file organization, naming, mixins, and dark mode.

Install as a dev dependency — Vite compiles SCSS automatically:

```bash
npm install -D sass
```

---

## API Client

Create a centralized API client module (`src/lib/api.js`) instead of scattering `fetch()` calls across components.

### Pattern

Two core helpers — `request()` for raw responses, `json()` for parsed JSON:

```javascript
import { API_BASE_URL } from '../config.js';

async function request(path, options = {}) {
  const url = API_BASE_URL + path;
  const headers = { ...getAuthHeader(), ...options.headers };
  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    authStore.logout();
    window.location.hash = '#/login';
    throw new Error('Unauthorized');
  }

  return res;
}

async function json(path, options = {}) {
  const res = await request(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error || res.statusText);
  }
  return res.json();
}
```

### Exported Functions

Export named functions for each API operation. Keep function signatures simple:

```javascript
export function getEntries(page = 1, perPage = 20, filters = {}) {
  const params = new URLSearchParams({ page, per_page: perPage });
  for (const [key, value] of Object.entries(filters)) {
    if (value != null && value !== '') params.set(key, value);
  }
  return json(`/entries?${params}`);
}

export function deleteEntry(id) {
  return json(`/entries/${id}`, { method: 'DELETE' });
}
```

---

## Configuration

### Build-Time Environment Variables

Use the build tool's environment variable system (e.g., `import.meta.env` with Vite). Prefix variables with the required prefix (`VITE_` for Vite).

### Runtime Config Module

Create a single `config.js` that reads environment variables and provides defaults:

```javascript
// src/config.js
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
```

### Environment Files

- `.env` — local overrides (gitignored)
- `.env.example` — template with placeholder values (committed)

---

## Authentication Pattern

### Flow

1. On app mount, check backend auth method (`GET /auth`)
2. If `method: 'none'` → auto-login as anonymous
3. Otherwise → redirect to login page
4. On login → store credentials in `sessionStorage`
5. All API requests inject `Authorization` header from store
6. On 401 response → clear auth, redirect to login
7. On logout → clear `sessionStorage`

### Why sessionStorage

Use `sessionStorage` (not `localStorage`) for auth credentials:
- Cleared when the browser tab closes
- Not shared across tabs (prevents accidental credential leakage)
- Auto-cleared on 401 from the API client

---

## Release System

### Version Management

Store the version in `package.json`. Use batch scripts in `tools/` for version management:

- `tools/version.bat` — display current version
- `tools/version-increment.bat` — increment patch version
- `tools/version-decrement.bat` — decrement patch version

### Release Notes

Store release notes as JSON files in `public/release_notes/`:

```
public/release_notes/
├── manifest.json              # Auto-generated, lists all versions newest-first
├── 1.0.0/
│   └── en.json
└── 1.0.1/
    └── en.json
```

#### Release Note Schema (`en.json`)

```json
{
  "version": "1.0.1",
  "date": "2026-03-01",
  "title": "Bug Fixes",
  "sections": [
    {
      "heading": "Bug Fixes",
      "items": [
        "Fixed issue with file upload validation"
      ]
    }
  ]
}
```

#### Manifest (`manifest.json`)

Auto-generated by a Node.js script that scans version directories:

```json
{
  "versions": ["1.0.1", "1.0.0"]
}
```

Regenerate with: `node tools/update-manifest.js`

### Automated Release

`tools/release.bat` runs the full workflow:
1. Increment patch version
2. Check/create release notes for new version
3. Regenerate manifest.json
4. Run production build

### In-App About Page

The app fetches `manifest.json` at runtime and displays release notes with prev/next navigation. No hardcoded versions — fully dynamic.

---

## Required Batch Files

Every frontend SPA project must include these in `tools/`:

| File | Purpose |
|------|---------|
| `tools/install.bat` | Install dependencies (`npm install`) |
| `tools/run.bat` | Start development server (`npm run dev`) |
| `tools/build.bat` | Production build (`npm run build`) |
| `tools/release.bat` | Full release workflow (version + notes + build) |

---

## API Testing Collection

Include a Hoppscotch (or similar) API collection for testing backend endpoints:

```
hoppscotch/
├── CLAUDE.md        # Instructions for using the collection
└── example.json     # Exported collection file
```

This helps onboarding and debugging API integration.
