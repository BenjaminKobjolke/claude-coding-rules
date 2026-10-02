# Version
1

Increase this version number whenever this rule file changes.

# Python Web Templates (Jinja2)

Applies on top of `PYTHON_RULES.md` when the project renders web templates.

## Template Engine

Keep Python, HTML, CSS, and JS separated.
This means using a template engine.

Use Jinja2:

```bash
uv add jinja2
```

Do not put JS code into templates. Use separate `.js` files.

Example structure:

```
project/
├── app/
├── templates/
└── static/
    ├── css/
    └── js/
```

Example template:

```html
<!-- templates/page.html -->
<!doctype html>
<html>
  <head>
    <link rel="stylesheet" href="/static/css/app.css">
  </head>
  <body>
    <h1>{{ title }}</h1>
    <script src="/static/js/app.js"></script>
  </body>
</html>
```

---
