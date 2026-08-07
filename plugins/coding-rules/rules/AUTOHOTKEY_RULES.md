# Version
1

Increase this version number whenever this rule file changes.

# AutoHotkey Rules (v1)

See `COMMON_RULES.md` for rules that apply to all languages. The rules below add the
AutoHotkey-specific guidance. They target **AutoHotkey v1.x** (the version these tools are
written in); where v2 behaves differently it is flagged inline with a **v2 note**.

---

## Single-Instance Toggle — Run Once Starts, Run Again Exits

This is the headline rule for any script that keeps running (persistent hotkey scripts, tray
tools, watchers): **launching it the first time starts it; launching it again exits the running
instance.** No second copy ever runs in parallel, and the same shortcut both starts and stops it.

Implement it with the shared `SingleInstance.ahk` library (COM active-object based), not with
AHK's built-in `#SingleInstance`:

```autohotkey
#NoEnv
SendMode Input
#SingleInstance off          ; toggle is handled by the library, NOT by AHK
#Persistent
SetWorkingDir %A_ScriptDir%

#Include %A_ScriptDir%\_libraries\SingleInstance.ahk

class MaximizeObject {
    __New() {
        ; startup work — runs only on the first launch
    }
    IsActive() {
        return true
    }
    Quit() {
        ; shutdown work — runs when a second launch finds this instance
        ExitApp
    }
}

CheckSingleInstance("{B8E2A3F7-9D4C-4A1E-8F5B-6C7D8E9F0A1B}", "MaximizeObject")
```

How it works:

- Each script defines a class with `__New()` (startup), `IsActive()` (returns `true`), and
  `Quit()` (shutdown + `ExitApp`).
- `CheckSingleInstance(GUID, "ClassName")` looks for an already-registered COM object under the
  GUID. If found, it calls that instance's `Quit()` and exits — so the **second** launch tells
  the **first** to shut down, and both processes end. If none is found, it constructs and
  registers the object, and the script keeps running.
- Every script MUST use its **own unique GUID**. Reusing another script's GUID makes the two
  scripts kill each other. Generate a fresh one per script.

Why: a single shortcut becomes an on/off toggle, duplicate instances can't fight over the same
hotkeys or resources, and shutdown is centralized in `Quit()`.

**v2 note:** `new %Class%()`, `ComObjActive`, and `VarSetCapacity` in the library are v1-only.
A v2 port needs a rewrite. For simple cases that only need "no duplicates" (without the
relaunch-to-exit behavior), v2's `#SingleInstance Force` plus a named mutex is enough.

---

## Standard Script Header

Start every script with the same directives so behavior is predictable:

```autohotkey
#NoEnv                       ; recommended for performance and compatibility
SendMode Input               ; faster, more reliable Send
#SingleInstance off          ; the library owns instance handling (see above)
#Persistent                  ; keep running after the auto-execute section
SetWorkingDir %A_ScriptDir%  ; relative paths resolve against the script, not the caller
```

`#Persistent` is required for hotkey/tray scripts so they don't exit after the auto-execute
section. One-shot scripts (do a job and quit) omit `#Persistent` and the single-instance block.

**v2 note:** `#NoEnv` and `SendMode Input` are defaults in v2 and can be dropped; `SetWorkingDir
A_ScriptDir` loses the `%...%`.

---

## Project Structure

```
my-ahk-tools/
├── _libraries/             # shared code, #Include'd by scripts (underscore sorts to top)
│   ├── SingleInstance.ahk
│   ├── TrayMenu.ahk        # shared tray menu + clean-exit revoke
│   ├── IniConfig.ahk       # per-script ini read/auto-create helper
│   └── Log.ahk
├── maximize.ahk            # one script = one responsibility
├── downloads_launcher.ahk
├── downloads_launcher.ini  # machine-specific, gitignored, auto-created on first run
├── docs/
│   └── MAXIMIZE.md
└── README.md
```

Scripts live at the root; shared helpers live in `_libraries\`. The underscore prefix keeps the
library folder at the top of the listing.

---

## Reuse via `#Include`

Shared logic belongs in `_libraries\` and is pulled in with an `%A_ScriptDir%`-anchored include:

```autohotkey
#Include %A_ScriptDir%\_libraries\SingleInstance.ahk
```

Never copy-paste a helper function between scripts — extract it into `_libraries\` and include it
in both. This is the AutoHotkey form of the common **DRY** rule.

**Shared libraries must be function-only.** `#Include` injects the file's text in place, so a
library that has **bare top-level labels or executable statements** and is included *above* the
auto-execute terminator (`return`/`ExitApp`) gets **fallen into at startup** — the auto-execute
flow skips function definitions but runs straight into the first label. Real failure seen here: a
`TrayMenu_Reload:` label ran `Reload` before `CheckSingleInstance` registered, so the
single-instance toggle never armed and instances piled up. Rules:

- A lib that needs callbacks (menu targets, `OnExit`, timers, hotkeys-by-binding) exposes them as
  **functions**, not bare labels. `Menu, ..., FuncName` (v1.1.20+) and `OnExit("FuncName")` both
  accept functions.
- If a lib genuinely must contain subroutine labels, `#Include` it **at the bottom** of the script
  (after the auto-execute `return`), never at the top.
- Function-only libs (`SingleInstance.ahk`, `IniConfig.ahk`, `TrayMenu.ahk`) are safe to include
  anywhere.

---

## Tray Menu Convention

Persistent scripts get a consistent tray menu — strip the standard items, then offer Reload and
Exit — plus an `OnExit` handler that **revokes the single-instance registration** before the
process dies, so a later relaunch starts cleanly instead of finding a stale slot.

This whole block is identical across scripts, so it lives once in `_libraries\TrayMenu.ahk` and
every script calls `SetupTrayMenu()`:

The library is **function-only** (no bare top-level labels). This matters: a label-bearing file
`#Include`d above the auto-execute `return` would be **fallen into at startup** — e.g. a
`TrayMenu_Reload:` label runs `Reload` before `CheckSingleInstance` registers, breaking the
single-instance toggle. Menu targets and `OnExit` therefore use functions, which the auto-execute
flow skips:

```autohotkey
; _libraries\TrayMenu.ahk  (requires SingleInstance.ahk for ObjRegisterActive + ActiveObject)
SetupTrayMenu() {
    Menu, tray, NoStandard
    Menu, tray, add                       ; separator
    Menu, tray, add, Reload, TrayMenu_Reload
    Menu, tray, add, Exit,   TrayMenu_Exit
    OnExit("TrayMenu_OnExit")
}
TrayMenu_Reload(ItemName:="", ItemPos:="", MenuName:="") {
    Reload
}
TrayMenu_Exit(ItemName:="", ItemPos:="", MenuName:="") {
    ExitApp
}
TrayMenu_OnExit(ExitReason:="", ExitCode:="") {
    global ActiveObject
    if (ActiveObject)
        ObjRegisterActive(ActiveObject, "")   ; unregister the COM active object
}
```

In each script, after `CheckSingleInstance(...)`:

```autohotkey
#Include %A_ScriptDir%\_libraries\TrayMenu.ahk
SetupTrayMenu()
return
```

---

## Configuration over Hardcoded Paths — Per-Script Auto-Created Ini

Do not bake machine-specific paths or values into scripts (e.g. `E:\downloads`, a 7-Zip install
path). Each script reads its **own** ini named after the script — `downloads_launcher.ahk` →
`downloads_launcher.ini` — sitting next to it. Three rules make this portable:

1. **Per-script, not shared.** One `<scriptname>.ini` per script, beside the `.ahk`. No central
   `settings.ini` that every script fights over.
2. **Gitignored.** The ini holds machine-specific values, so it is never committed. The project
   `.gitignore` MUST include `*.ini`.
3. **Auto-created on first launch.** The script creates the ini with default values the first
   time it runs, then reads from it. A fresh clone runs once, generates the ini, and the user
   edits it afterwards — no manual setup step, no missing-file errors.

Use the shared `_libraries\IniConfig.ahk` helper — the first read of a missing key writes the
default, which both creates the file and seeds it:

```autohotkey
; _libraries\IniConfig.ahk
GetIniSetting(file, section, key, default) {
    IniRead, value, %file%, %section%, %key%, %A_Space%
    if (value = "") {
        IniWrite, %default%, %file%, %section%, %key%
        value := default
    }
    return value
}
```

```autohotkey
#Include %A_ScriptDir%\_libraries\IniConfig.ahk
cfg := A_ScriptDir . "\downloads_launcher.ini"
DownloadsDir := GetIniSetting(cfg, "Paths", "DownloadsDir", "E:\downloads")
SevenZipPath := GetIniSetting(cfg, "Paths", "SevenZipPath", "C:\Program Files\7-Zip\7z.exe")
```

Keep the per-script GUID as a clearly labelled constant near the top of the file. This is the
AutoHotkey form of the common **String Constants** / centralized-configuration rule: one place to
change a value, and the script is portable to another machine by editing the `.ini` only.

---

## Logging Strategy

**Small scripts** (a handful of hotkeys, a one-shot job): `MsgBox` is acceptable for output and
debugging. No centralized logger module is required — don't add `Log.ahk` for a script that
doesn't need it.

**Persistent / larger scripts** (tray tools, watchers, anything that grows past a few hotkeys):
don't scatter `MsgBox` calls for tracing. Use a single logger module in `_libraries\` (e.g.
`Log.ahk`) that writes to a file and is gated by one `debug` flag, so logging has a single
off switch — the AutoHotkey form of the common **centralized-logger** rule:

```autohotkey
; _libraries\Log.ahk
Log(msg) {
    global DebugEnabled
    if (!DebugEnabled)
        return
    FileAppend, % A_Now . "  " . msg . "`n", %A_ScriptDir%\log.txt
}
```

In those larger scripts, reserve `MsgBox` for genuine user-facing prompts (confirmations, errors
the user must see), not for tracing what the script is doing.

---

## Testing

The common **Test-Driven Development** and **Integration Tests** rules in `COMMON_RULES.md` do
**not** apply to AutoHotkey scripts. No test suite, no `tools/run_tests.bat`, no
`run_integration_tests.bat` is required. Verify manually: run the script and confirm the
hotkeys/behavior work as expected.

---

## Naming & File Length

The common rules apply directly:

- **Max 300 lines per file** — split a growing script into modules under `_libraries\` and
  `#Include` them.
- **Descriptive names** for functions, labels, and hotkey handlers (`MoveWindowTo`, not `mw`).
- **One script = one responsibility.** A script that maximizes windows does not also launch
  downloads; that's a second script with its own GUID.

---

## Project Setup Scripts

Copy the setup files from the `autohotkey_setup_files/` folder bundled with the
coding-rules plugin (next to this rules file).

### _libraries/SingleInstance.ahk

The COM-based single-instance library (`ObjRegisterActive` + `CheckSingleInstance`). Drop it into
the project's `_libraries\` folder and `#Include` it — this is what powers the run-once-starts,
run-again-exits toggle.

### _libraries/TrayMenu.ahk

The shared tray menu + clean-exit handler (`SetupTrayMenu` + `TrayMenu_OnExit` revoke). `#Include`
it and call `SetupTrayMenu()` after `CheckSingleInstance(...)` — removes the duplicated tray block
from every script.

### _libraries/IniConfig.ahk

The per-script ini helper (`GetIniSetting`) that reads `<scriptname>.ini` and auto-creates missing
keys with defaults on first run. Pair with `*.ini` in `.gitignore`.

### template.ahk

A skeleton script with the standard header, the `#Include`s, a sample single-instance class, a
placeholder GUID, and `SetupTrayMenu()`. Copy it, rename it, replace the GUID and class name, and
add hotkeys — the fastest correct starting point for a new script.
