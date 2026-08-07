# Version
1

Increase this version number whenever this rule file changes.

# Svelte Rules

See `COMMON_RULES.md` for rules that apply to all languages.
See `project_type/FRONTEND.md` for rules that apply to all frontend SPA projects.

## Svelte Version

Use Svelte 5 with the modern runes API. Do not use the legacy `$:` reactive syntax.

Available runes:
- `$state` — reactive state
- `$derived` — computed values
- `$props` — component props
- `$bindable` — two-way bindable props
- `$effect` — side effects

```svelte
<script>
  let count = $state(0);
  let doubled = $derived(count * 2);
  let { value = $bindable(0) } = $props();
</script>
```

---

## Project Structure

```
project/
├── src/
│   ├── App.svelte              # Root component (router + layout shell)
│   ├── main.js                 # Entry point (mounts App)
│   ├── config.js               # Runtime configuration constants
│   ├── app.css                 # Global styles (Tailwind and/or SCSS imports)
│   ├── components/             # Reusable UI components
│   │   ├── layout/             # Navbar, Footer, Sidebar
│   │   ├── shared/             # ConfirmDialog, LoadingSpinner, Toast
│   │   └── <domain>/           # Domain-grouped components
│   ├── lib/                    # Utility modules (api, auth, utils)
│   ├── routes/                 # Page-level components (one per route)
│   ├── stores/                 # Svelte stores (state management)
│   └── tests/
│       └── setup.js            # Test setup & polyfills
├── public/                     # Static assets served as-is
├── tools/                      # Build & release batch scripts
├── docs/                       # Project documentation
├── index.html                  # HTML entry point
├── vite.config.js
├── svelte.config.js
├── tailwind.config.js
├── postcss.config.js
├── package.json
└── .env.example
```

---

## Routing

Use `svelte-spa-router` for client-side hash-based routing (`#/path`).

### Route Definition

Define all routes in `App.svelte`. Use `wrap()` with conditions for protected routes:

```svelte
<script>
  import Router from 'svelte-spa-router';
  import { wrap } from 'svelte-spa-router/wrap';

  const routes = {
    '/login': Login,
    '/': wrap({ component: EntryList, conditions: [isAuthenticated] }),
    '/entries/:id': wrap({ component: EntryDetail, conditions: [isAuthenticated] }),
  };

  function conditionsFailed() {
    window.location.hash = '#/login';
  }
</script>

<Router {routes} on:conditionsFailed={conditionsFailed} />
```

### Navigation

Use hash-based links: `<a href="#/path">`. For programmatic navigation:
```javascript
window.location.hash = '#/entries/123';
```

---

## State Management

Use Svelte's built-in `writable` stores. Create factory functions that return a store with domain-specific methods.

### Auth Store (sessionStorage)

```javascript
import { writable } from 'svelte/store';

function createAuthStore() {
  const stored = getStoredAuth(); // from sessionStorage
  const { subscribe, set } = writable(stored);

  return {
    subscribe,
    login(username, password) {
      storeAuth(username, password);
      set({ username, password });
    },
    logout() {
      clearAuth();
      set(null);
    },
  };
}

export const authStore = createAuthStore();
```

### Settings Store (localStorage)

```javascript
import { writable } from 'svelte/store';

const STORAGE_KEY = 'app_settings';

function createSettingsStore() {
  const { subscribe, set, update } = writable(load());
  return {
    subscribe,
    set(values) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(values));
      set(values);
    },
    update(fn) {
      update((current) => {
        const next = fn(current);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        return next;
      });
    },
  };
}

export const settingsStore = createSettingsStore();
```

### Notification Store (auto-dismiss)

```javascript
import { writable } from 'svelte/store';

function createNotificationStore() {
  const { subscribe, update } = writable([]);
  let nextId = 0;

  function add(message, type = 'info', duration = 4000) {
    const id = nextId++;
    update((n) => [...n, { id, message, type }]);
    if (duration > 0) setTimeout(() => remove(id), duration);
    return id;
  }

  function remove(id) {
    update((n) => n.filter((item) => item.id !== id));
  }

  return {
    subscribe,
    success: (msg) => add(msg, 'success'),
    error: (msg) => add(msg, 'error', 6000),
    info: (msg) => add(msg, 'info'),
    remove,
  };
}

export const notifications = createNotificationStore();
```

---

## Component Organization

Group components by domain, not by type. Shared/reusable components go in `shared/`.

```
src/components/
├── layout/                # App shell: Navbar, Footer
│   └── Navbar.svelte
├── shared/                # Reusable across domains
│   ├── ConfirmDialog.svelte
│   ├── LoadingSpinner.svelte
│   └── Toast.svelte
├── entries/               # Entry list domain
│   ├── EntryTable.svelte
│   ├── Pagination.svelte
│   └── SearchFilter.svelte
├── detail/                # Entry detail domain
│   ├── EntryHeader.svelte
│   ├── EntryBody.svelte
│   └── EditEntryModal.svelte
└── upload/                # Upload domain
    ├── FileUploadForm.svelte
    └── TextUploadForm.svelte
```

### Page Components

Page-level components live in `src/routes/` — one file per route. These compose domain components and handle data fetching.

---

## Shared UI Components

Every project should include these reusable components in `src/components/shared/`:

- **Toast.svelte** — Renders notifications from the notification store. Positioned fixed, auto-dismisses.
- **LoadingSpinner.svelte** — Consistent loading indicator.
- **ConfirmDialog.svelte** — Modal confirmation for destructive actions (delete, etc.).

---

## Testing

Use Vitest with jsdom and `@testing-library/svelte`.

### package.json Scripts

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

### Vite Test Configuration

```javascript
// vite.config.js
export default defineConfig({
  resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.js'],
    include: ['src/**/*.test.js'],
    css: false,
  },
});
```

### Setup File

```javascript
// src/tests/setup.js
import '@testing-library/jest-dom/vitest';

// Polyfill localStorage for Node environments that lack standard methods
function createStorage() {
  let store = {};
  return {
    getItem(key) { return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null; },
    setItem(key, value) { store[key] = String(value); },
    removeItem(key) { delete store[key]; },
    clear() { store = {}; },
    get length() { return Object.keys(store).length; },
    key(i) { return Object.keys(store)[i] ?? null; },
  };
}

globalThis.localStorage = createStorage();
```

### Test File Placement

Co-locate test files next to the module they test:

```
src/lib/api.js
src/lib/api.test.js
src/stores/auth.js
src/stores/auth.test.js
src/components/entries/EntryTable.svelte
src/components/entries/EntryTable.test.js
```

---

## API Client

Create a centralized fetch wrapper in `src/lib/api.js` with error handling and auth headers.
All API calls go through this module — never use raw `fetch()` directly in components.

---

## Logging

Route all logging through one module that exports **`logger`** (`src/lib/logger.ts`). Feature
code and components import `logger`, never call `console.log`/`console.error` directly — this
gives a single enable/level toggle (e.g. off in production) without touching call sites.

```ts
import { logger } from '$lib/logger';

logger.info('User loaded', { userId });
logger.error('Failed to load user', { userId, error });
```

---

## Form Validation

Validate form inputs before submission. Show inline error messages next to the relevant fields.
Disable the submit button while validation errors exist or while a request is in-flight.

---

## Environment Config

Use `.env` files with Vite's `import.meta.env` for environment-specific configuration. Prefix
variables with `VITE_`. Always provide a `.env.example` with placeholder values committed to
version control.

---

## Self-Describing Classes

Implement the common "Self-Describing Classes" rule using a TypeScript interface with an explicit
method, or a static field descriptor.

### Option A: Interface with method (for class-based code)

```typescript
interface Searchable {
  getSearchableFields(): Record<string, string>;
}

class Customer implements Searchable {
  constructor(
    public name: string,
    public email: string,
    public phone: string,
  ) {}

  getSearchableFields(): Record<string, string> {
    return { name: this.name, email: this.email, phone: this.phone };
  }
}
```

### Option B: Field descriptor (for plain objects / Svelte stores)

```typescript
const CUSTOMER_SEARCHABLE_FIELDS = ['name', 'email', 'phone'] as const;

function getSearchableValues(customer: Customer): string[] {
  return CUSTOMER_SEARCHABLE_FIELDS.map((key) => customer[key]);
}
```

Prefer the interface approach when using classes. For store-based data, keep the field
descriptor co-located with the type definition so new fields are not forgotten.
