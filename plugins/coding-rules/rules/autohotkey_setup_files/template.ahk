; ============================================================================
;  TEMPLATE — copy this file, rename it, and replace the GUID + class name.
;  A persistent toggle script: first run starts it, second run exits it.
; ============================================================================

#NoEnv                       ; recommended for performance and compatibility
SendMode Input               ; faster, more reliable Send
#SingleInstance off          ; toggle is handled by SingleInstance.ahk, not AHK
#Persistent                  ; keep running after the auto-execute section
SetWorkingDir %A_ScriptDir%

#Include %A_ScriptDir%\_libraries\SingleInstance.ahk
#Include %A_ScriptDir%\_libraries\TrayMenu.ahk

; --- Single-instance toggle -------------------------------------------------
; The class is the script's lifecycle. __New() runs on first launch, Quit() runs
; when a SECOND launch finds this instance already active (both then exit).
class MyScriptObject {
    __New() {
        ; one-time startup work goes here
        ; MsgBox Starting MyScript
    }
    IsActive() {
        return true
    }
    Quit() {
        ; shutdown / cleanup work goes here
        ; MsgBox Shutting down MyScript
        ExitApp
    }
}

; Generate a fresh, unique GUID per script (do NOT reuse another script's GUID).
CheckSingleInstance("{REPLACE-WITH-A-UNIQUE-GUID}", "MyScriptObject")

; --- Tray menu + clean exit (revokes the single-instance COM slot) -----------
SetupTrayMenu()
return

; ============================================================================
;  Hotkeys / logic below
; ============================================================================

; #+a::                         ; example: Win+Shift+A
;     ; do work
; return
