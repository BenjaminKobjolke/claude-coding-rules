# App Icons (Flutter / Android)

House standard for launcher and notification icons, plus the setup steps for a
new project. Read this before generating, replacing, or debugging any icon.

## House style

**Solid black background, simple white line art.** Every app follows it, so the
icons read as one family and every one of them survives being masked, tinted,
and shrunk to 24 px.

- **Background: `#000000`.** Not brand colour, not a gradient, not transparent
  (see "Why not transparent" below).
- **Art: pure white `#FFFFFF`, line-drawn, one subject.** No fills, no gradients,
  no shadows, no text. One recognisable object — a monitor, a clock, a box.
- **Strokes: thick and even.** The same art gets rendered at 24 px in the status
  bar. A stroke thinner than ~1/16 of the canvas width vanishes at that size.
- **Keep the source art as a separate white-on-transparent PNG.** Everything else
  — the black-backed launcher icon, the adaptive foreground, the notification
  silhouette — is derived from it. Never hand-edit a derived file.

---

## The two icon systems

Android treats these completely differently. They look similar and are routinely
confused; wiring one does not wire the other.

| | Launcher icon | Notification icon |
|---|---|---|
| Shows in | Home screen, app drawer, task switcher | Status bar, notification shade |
| Colour | Full colour | **None** — Android discards RGB and tints the alpha silhouette white |
| Source art | `assets/icon/app_icon*.png` | `assets/icon/notification_icon.png` |
| Generated into | `mipmap-*/ic_launcher.png`, `drawable-*/ic_launcher_foreground.png` | `drawable-*/ic_stat_<app>.png` |
| Generator | `flutter_launcher_icons` | Pillow snippet (below) |

---

## Setting up icons in a new project

### 1. Source art

Put three files in `assets/icon/`:

| File | What it is |
|---|---|
| `logo_source.png` | The master: white line art on transparent, square, at least 512 px |
| `app_icon.png` | 512x512 legacy icon — the art composited on solid black |
| `app_icon_foreground.png` | 512x512 adaptive **foreground** — white art on transparent, with adaptive-icon safe-zone padding (art inside the middle ~66%) |

Adaptive icons crop hard to a launcher-chosen mask, so the foreground needs that
extra padding while the legacy icon does not. That is why they are two files,
not one.

### 2. Add the generator

```yaml
dev_dependencies:
  flutter_launcher_icons: ^0.14.4
```

### 3. Configure it in `pubspec.yaml`

```yaml
# App icon generation: `fvm dart run flutter_launcher_icons`
flutter_launcher_icons:
  android: true
  ios: false                    # set true and add ios paths for an iOS target
  image_path: "assets/icon/app_icon.png"
  adaptive_icon_background: "#000000"
  adaptive_icon_foreground: "assets/icon/app_icon_foreground.png"
  min_sdk_android: 21
```

### 4. Generate

```
fvm dart run flutter_launcher_icons
```

This rewrites `android/app/src/main/res/values/colors.xml`
(`ic_launcher_background`) and every `mipmap-*` / `drawable-*` PNG. **Never edit
those generated files by hand** — the next run overwrites them.

### 5. Add the notification icon

See "Notification icon" below. A project with any notification — a foreground
service, a local notification, a push — needs one. Skipping it leaves a white
blob in the status bar.

---

## Why not transparent

**An adaptive icon's background layer must be opaque.** The launcher masks
background and foreground into its own shape (circle, squircle, teardrop — it
varies by device) and parallax-animates the two layers against each other. A
transparent background layer is undefined behaviour: some launchers render it
black, some white, some show artifacts mid-animation.

Black is the deliberate house choice, not a fallback that happens to work.

## Both background definitions must change together

`adaptive_icon_background` covers API 26+. The legacy `app_icon.png` carries its
background **baked into the pixels** and serves anything below that — which
matters whenever `minSdk < 26`. Changing the pubspec value alone silently leaves
old devices on the old colour.

### Recolouring a legacy icon's baked-in background

The legacy icon is white art alpha-blended over a flat colour. To move it to a
new background without a coloured fringe, solve the blend alpha back out per
pixel. **Never swap the background colour pixel-by-pixel** — that leaves every
anti-aliased edge tinted with the old colour.

```python
from PIL import Image
import numpy as np

OLD_BG = np.array([63., 81., 181.])   # the colour currently baked in
FG = np.array([255., 255., 255.])     # the art colour

img = np.asarray(Image.open('assets/icon/app_icon.png').convert('RGB')).astype(float)
alpha = np.clip(((img - OLD_BG) / (FG - OLD_BG))[..., 0], 0, 1)  # red: widest gap
out = np.repeat((alpha * 255)[..., None], 3, axis=2).astype('uint8')  # over black
Image.fromarray(out, 'RGB').convert('RGBA').save('assets/icon/app_icon.png')
```

Sanity-check the model first: the per-channel alpha estimates should agree to
within ~0.01. If they do not, the art is not a flat blend and this shortcut does
not apply — recomposite from `logo_source.png` instead.

---

## Notification icon

### Why it must be its own asset

Android renders notification **small icons** as a pure alpha silhouette — it
throws the RGB channels away and tints the remaining shape white. Point one at
the full-colour `@mipmap/ic_launcher` and the status bar shows a featureless
white square, because the launcher icon is an opaque block of pixels.

### Master asset spec

`assets/icon/notification_icon.png`:

| | |
|---|---|
| Format | PNG, RGBA |
| Colour | White `#FFFFFF` on a fully transparent background |
| Size | 512x512 or larger, square |
| Content | Silhouette only — no background fill, gradient, colour, or shadow. Only alpha survives |
| Strokes | Thick. At mdpi the whole icon is 24 px; strokes thinner than ~1/16 of the canvas width disappear entirely |

Draw it **separately and bolder** than the launcher art. Launcher line art that
looks crisp at 192 px turns to mush at 24 px.

### Generating the density set

Run from the repo root after adding or replacing the master. It crops to the
alpha bounding box first, so the art fills the 24dp box regardless of how the
master is padded:

```python
from pathlib import Path
from PIL import Image

SRC = 'assets/icon/notification_icon.png'
DST = 'android/app/src/main/res/drawable-%s/ic_stat_myapp.png'   # name it per app
DENSITIES = [('mdpi', 24), ('hdpi', 36), ('xhdpi', 48),
             ('xxhdpi', 72), ('xxxhdpi', 96)]

art = Image.open(SRC).convert('RGBA')
art = art.crop(art.split()[3].getbbox())
for bucket, size in DENSITIES:
    path = Path(DST % bucket)
    path.parent.mkdir(parents=True, exist_ok=True)
    scaled = art.copy()
    scaled.thumbnail((size - 2, size - 2), Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(
        scaled, ((size - scaled.width) // 2, (size - scaled.height) // 2))
    canvas.save(path)
```

Preview the mdpi output before committing. If the 24 px version is unreadable,
the source strokes are too thin — redraw, do not post-process.

### Wiring — every place that posts a notification

Centralize the resource identifiers in the project's `Constants` class (see
`COMMON_RULES.md` → "String Constants"), never as inline literals:

```dart
/// Status-bar icon for every notification this app posts. Separate from the
/// launcher icon: Android renders small icons as a white alpha silhouette, so
/// an opaque `@mipmap/ic_launcher` shows up as a featureless blob.
static const String notificationIconResource = '@drawable/ic_stat_myapp';

/// Manifest meta-data key flutter_foreground_task resolves its icon through
/// (`ForegroundService.kt` reads `appInfo.metaData.getInt(metaDataName)`).
static const String notificationIconMetaData =
    'com.example.myapp.NOTIFICATION_ICON';
```

**`flutter_local_notifications`** — pass it to `AndroidInitializationSettings`.
That becomes the plugin's default for everything it posts, so individual
`AndroidNotificationDetails` need no per-notification `icon:` override:

```dart
const androidInit =
    AndroidInitializationSettings(Constants.notificationIconResource);
```

**`flutter_foreground_task`** resolves its icon *indirectly*, through
application-level manifest meta-data. Two halves, and they must agree:

```dart
await FlutterForegroundTask.startService(
  // ...
  notificationIcon: const NotificationIcon(
    metaDataName: Constants.notificationIconMetaData,
  ),
);
```

```xml
<!-- android/app/src/main/AndroidManifest.xml, inside <application> -->
<meta-data
    android:name="com.example.myapp.NOTIFICATION_ICON"
    android:resource="@drawable/ic_stat_myapp" />
```

The meta-data must sit at **application** level, not on the `<service>`. A
mismatch between the Dart constant and the manifest fails **silently**: the
service falls back to the app icon and the status bar shows a white blob again.

---

## Verifying an icon change

1. `grep ic_launcher_background android/app/src/main/res/values/colors.xml`
2. Corner pixels of `assets/icon/app_icon.png` are the intended background colour
3. `tools/build_debug.bat`, install on a device
4. Launcher: check the app drawer **and** the task switcher
5. Post a notification — the status bar must show the silhouette, not a solid
   square. Check both the collapsed status bar and the expanded shade
6. If `minSdk < 26`: an API 24/25 emulator exercises the legacy non-adaptive path

## Documenting it per project

Every project that customises its icons gets a `docs/ICONS.md` recording its own
source-art paths, drawable names, meta-data key, and wiring locations. Reference
implementation: `block-screen-app/docs/ICONS.md`.
