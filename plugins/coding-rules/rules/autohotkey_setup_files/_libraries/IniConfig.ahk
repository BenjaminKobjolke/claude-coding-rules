/*
    IniConfig.ahk
    Per-script configuration helper.

    Each script reads its own "<scriptname>.ini" next to it. The ini is gitignored
    (machine-specific) and created on first launch: the first read of a missing key
    writes the supplied default, so a fresh clone generates the ini the first time
    the script runs, and the user edits it afterwards.
*/

; Read a setting; create the key (and the file) with `default` on first run.
GetIniSetting(file, section, key, default) {
    IniRead, value, %file%, %section%, %key%, %A_Space%
    if (value = "") {
        IniWrite, %default%, %file%, %section%, %key%
        value := default
    }
    return value
}
