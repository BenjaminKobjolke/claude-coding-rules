# Version
1

Increase this version number whenever this rule file changes.

# Arduino C/C++ Rules (arduino-cli)

See `COMMON_RULES.md` for rules that apply to all languages. The rules below add the
embedded-specific guidance for Arduino projects built with `arduino-cli`.

---

## Keep Sketches Thin — No Logic in `.ino`

The `.ino` sketch is a build entry point, not a place for code. Put **all** real logic, state,
and types in `.h` / `.cpp` translation units. The `.ino` only includes the project header and
delegates:

```cpp
// MyProject.ino  — entry point only, no logic
#include "src/app.h"

void setup() { app_setup(); }
void loop()  { app_loop(); }
```

```cpp
// src/app.h  — declarations
#pragma once
void app_setup();
void app_loop();
```

```cpp
// src/app.cpp  — the actual logic lives here
#include "app.h"
#include <Arduino.h>

void app_setup() { /* ... */ }
void app_loop()  { /* ... */ }
```

Why:

- `.ino` files are preprocessed by the Arduino build (prototypes auto-generated, files
  concatenated) and **cannot be unit-tested on the host or reused** by another project.
- Logic in `.cpp` compiles with a normal host compiler, so it can be tested without a board
  (see "Host-Side Unit Tests").
- A class/module in `.h`/`.cpp` is reusable across sketches; a blob in `.ino` is not.

Rule: if a function does anything beyond delegating into a module, it does not belong in `.ino`.

---

## Project Structure

```
MyProject/
├── MyProject.ino          # thin entry point — setup()/loop() delegate only
├── sketch.yaml            # pinned FQBN + libraries (committed)
├── src/                   # all logic as .h/.cpp modules
│   ├── app.h
│   ├── app.cpp
│   ├── sensor.h
│   └── sensor.cpp
├── include/
│   └── config.h           # pins, timings, constants
├── test/                  # host-side unit tests (no board needed)
│   ├── mocks/Arduino.h     # mocked hardware API
│   └── test_sensor.cpp
├── tools/
│   └── run_tests.bat
├── build.bat
├── upload.bat
└── README.md
```

---

## arduino-cli Workflow

Use `arduino-cli`; do not depend on the Arduino IDE. Pin the board and libraries so builds are
reproducible, and commit `sketch.yaml`:

```yaml
# sketch.yaml
default_fqbn: arduino:avr:uno
default_port: COM3
```

```bash
# Compile
arduino-cli compile --fqbn arduino:avr:uno .

# Upload
arduino-cli upload -p COM3 --fqbn arduino:avr:uno .
```

Install libraries via `arduino-cli lib install "Name"` and record them in `sketch.yaml` so a
fresh checkout builds identically. The `build.bat` / `upload.bat` wrappers (see "Project Setup
Scripts") encapsulate these commands.

---

## Host-Side Unit Tests

Because logic lives in `.cpp`, compile those units with the host compiler (`g++`) and run them
on the dev machine — no board required. This is how the common "tests are mandatory" rule is
satisfied for embedded.

- Keep hardware access (`digitalWrite`, `analogRead`, `Serial`, `millis`) behind a thin
  interface so logic modules depend on the interface, not on `Arduino.h` directly.
- Provide a mocked `Arduino.h` under `test/mocks/` and a fake/recording implementation of the
  hardware interface; assert on logic behavior.
- Use a small framework — Unity (ThrowTheSwitch) or GoogleTest.

```cpp
// A logic module takes its hardware dependency as a seam, so tests inject a fake:
class Hardware {
public:
    virtual int readAnalog(uint8_t pin) = 0;
    virtual void writeDigital(uint8_t pin, bool high) = 0;
};

void update_pump(Hardware& hw);  // pure logic, testable on host
```

`tools/run_tests.bat` compiles `test/` + the modules under test with `g++` and runs the binary.
Hardware-dependent code stays minimal so most behavior is covered without flashing a device.

---

## Memory Discipline

Microcontrollers have tiny RAM and no real heap management.

- **Never use the `String` class** — it fragments the heap. Use fixed `char[]` buffers and the
  `<cstring>` functions, or a bounded string helper.
- Wrap string literals in `F()` so they stay in flash, not RAM: `Serial.println(F("ready"))`.
- Store large constant tables in `PROGMEM`.
- Avoid dynamic allocation (`new` / `malloc`) — especially inside `loop()`. Pre-allocate fixed
  buffers at startup.

---

## Non-Blocking Timing

Never call `delay()` in real logic — it stalls the whole loop. Use `millis()` state machines so
the device stays responsive:

```cpp
static uint32_t last = 0;
const uint32_t INTERVAL_MS = 1000;

void app_loop() {
    uint32_t now = millis();
    if (now - last >= INTERVAL_MS) {
        last = now;
        tick();
    }
    // other work continues every loop iteration
}
```

`delay()` is acceptable only in one-off setup or test sketches, never in the main control flow.

---

## Interrupt Service Routines (ISRs)

- Keep ISRs as short as possible — set a flag, store a reading, return.
- Share state with the main loop only through `volatile` variables, and guard multi-byte reads
  against tearing (briefly disable interrupts or use `noInterrupts()`/`interrupts()`).
- Never call `Serial`, `delay()`, or allocate inside an ISR.

```cpp
volatile bool g_pulse = false;
void onPulse() { g_pulse = true; }   // ISR: minimal
```

---

## Fixed-Width Types

Use explicit-width integer types from `<stdint.h>` instead of bare `int` (whose width varies by
board — 16-bit on AVR, 32-bit on ESP32):

- `uint8_t`, `int16_t`, `uint32_t`, etc. sized to the value's real range.
- `bool` for flags.
- `size_t` for sizes/indices.

This is the embedded form of the common "prefer type-safe values" rule and prevents portability
bugs across boards.

---

## Centralize Pins & Configuration

Put every pin number, timing constant, and tuning value in `include/config.h` using `constexpr`
(typed, scoped) rather than scattering `#define`s through the code:

```cpp
// include/config.h
#pragma once
#include <stdint.h>

namespace config {
    constexpr uint8_t  PIN_PUMP        = 5;
    constexpr uint8_t  PIN_MOISTURE    = A0;
    constexpr uint32_t SAMPLE_INTERVAL = 1000;  // ms
    constexpr uint16_t MOISTURE_MIN    = 300;
}
```

Prefer `constexpr` over `#define`: it carries a type, respects scope, and is visible to the
debugger. This is the embedded form of the common "String Constants" rule.

---

## Serial Logging Strategy

Do not scatter raw `Serial.print` calls. Use a single compile-time-gated debug macro so logging
strips out of release builds (saving flash/RAM and keeping timing tight):

```cpp
// include/debug.h
#pragma once

#ifdef DEBUG
  #define DEBUG_BEGIN(baud) Serial.begin(baud)
  #define DEBUG_PRINT(...)  Serial.print(__VA_ARGS__)
  #define DEBUG_PRINTLN(...) Serial.println(__VA_ARGS__)
#else
  #define DEBUG_BEGIN(baud)
  #define DEBUG_PRINT(...)
  #define DEBUG_PRINTLN(...)
#endif
```

Enable with `arduino-cli compile --build-property "build.extra_flags=-DDEBUG" ...`. This is the
embedded form of the common centralized-logging rule.

Wrap these macros in one logger named **`Log`** (`Log.h` / `Log.cpp`) — e.g. `Log::info(...)`,
`Log::error(...)`. Feature code calls `Log`, never `Serial.print` directly, so logging has a
single compile-time gate and one place to change the sink (Serial, none, etc.).

---

## Input Validation at Boundaries

The common "Input Validation at Boundaries" rule applies to physical and serial inputs:

- Range-check `analogRead` / sensor values before acting on them; reject impossible readings.
- Validate the length and format of serial commands before parsing; never index past a buffer.
- Treat anything arriving over Serial, I2C, or radio as untrusted, exactly like a network input.

---

## Project Setup Scripts

Copy the setup batch files from the `arduino_setup_files/` folder bundled with the
coding-rules plugin (next to this rules file).

### build.bat

Compiles the sketch with `arduino-cli` using the project's FQBN.

### upload.bat

Uploads the compiled sketch to the connected board on the configured port.

### tools/run_tests.bat

Builds and runs the host-side unit tests with `g++` (no board required) — satisfies the common
`tools/run_tests.bat` requirement.

### Usage

```bash
# Compile firmware
build.bat

# Flash to board
upload.bat

# Run host-side tests
tools\run_tests.bat
```
