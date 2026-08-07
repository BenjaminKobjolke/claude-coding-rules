/*
    TrayMenu.ahk
    Shared tray menu + clean-exit boilerplate for persistent toggle scripts.
    Requires _libraries\SingleInstance.ahk (provides ObjRegisterActive + ActiveObject).
*/

; Strip the standard tray items and offer Reload / Exit, then register a clean-exit
; handler that frees the single-instance COM slot so a relaunch starts fresh.
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
        ObjRegisterActive(ActiveObject, "")   ; free single-instance slot for clean relaunch
}
