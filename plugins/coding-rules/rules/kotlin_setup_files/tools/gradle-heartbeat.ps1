# Runs gradlew.bat and prints a heartbeat every 30 s, so a long silent task
# (e.g. lintAnalyzeDebug) shows it is still alive. The last "> Task" line above
# the heartbeats names the task that is running.
$root = Split-Path $PSScriptRoot -Parent
$start = Get-Date
$gradleArgs = if ($args.Count) { $args } else { @('help') }

# Start-Process joins ArgumentList into a command line. Quote each argument using
# the Windows command-line escaping rules before passing the joined string.
$quotedGradleArgs = foreach ($argument in $gradleArgs) {
    $quoted = [System.Text.StringBuilder]::new()
    $null = $quoted.Append('"')
    $backslashes = 0

    foreach ($character in $argument.ToCharArray()) {
        if ($character -eq '\') {
            $backslashes++
            continue
        }

        if ($character -eq '"') {
            $null = $quoted.Append(('\' * (2 * $backslashes + 1)))
            $null = $quoted.Append('"')
            $backslashes = 0
            continue
        }

        if ($backslashes -gt 0) {
            $null = $quoted.Append(('\' * $backslashes))
            $backslashes = 0
        }
        $null = $quoted.Append($character)
    }

    if ($backslashes -gt 0) {
        $null = $quoted.Append(('\' * (2 * $backslashes)))
    }
    $null = $quoted.Append('"')
    $quoted.ToString()
}
$p = Start-Process -FilePath (Join-Path $root 'gradlew.bat') -ArgumentList ($quotedGradleArgs -join ' ') -NoNewWindow -PassThru
$null = $p.Handle  # keeps ExitCode readable after the process ends
while (-not $p.WaitForExit(30000)) {
    [Console]::Out.WriteLine('[run-gradle] still running, {0:N0} s' -f ((Get-Date) - $start).TotalSeconds)
    [Console]::Out.Flush()
}
exit $p.ExitCode
