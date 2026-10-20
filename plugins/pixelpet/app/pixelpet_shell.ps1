# PixelPet shell integration for PowerShell (dot-sourced from the user's profile by shell_setup.py).
# Tells the pet when a command line starts and finishes, so long-running scripts show up
# like Claude / Codex sessions. The pet decides what is long enough to show.
# Keep this file ASCII-only: Windows PowerShell 5.1 reads BOM-less files in the ANSI code page.

if ($global:PixelPetShell -or $Host.Name -ne 'ConsoleHost' -or
    ([Environment]::GetCommandLineArgs() -match '^-noni')) { return }
try {
    Import-Module PSReadLine -ErrorAction Stop
    Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
} catch { return }

$__pp = @{ Run = 0; Busy = $false }
$__ppHandler = New-Object System.Net.Http.HttpClientHandler
$__ppHandler.UseProxy = $false
$__pp.Client = New-Object System.Net.Http.HttpClient($__ppHandler)
$__pp.Client.Timeout = [TimeSpan]::FromSeconds(3)
$__pp.Client.DefaultRequestHeaders.Add('X-PixelPet', '1')
$__pp.Url = 'http://127.0.0.1:{0}/event' -f $(if ($env:PIXELPET_PORT) { $env:PIXELPET_PORT } else { 47321 })

# Fire-and-forget: never make the prompt wait for the pet (or for a pet that is not running)
$__pp.Send = {
    param($data)
    try {
        $data.source = 'shell'
        $data.pid = $PID
        $body = New-Object System.Net.Http.StringContent(($data | ConvertTo-Json -Compress),
            [Text.Encoding]::UTF8, 'application/json')
        $null = $global:PixelPetShell.Client.PostAsync($global:PixelPetShell.Url, $body)
    } catch {}
}

# Command start: PSReadLine calls this for every line it is about to run
$__pp.PrevHistory = (Get-PSReadLineOption).AddToHistoryHandler
Set-PSReadLineOption -AddToHistoryHandler {
    param([string]$line)
    $s = $global:PixelPetShell
    # PSReadLine 2.0 also calls this for every line it loads from the history file at startup;
    # only a line that is really being run is still in the edit buffer
    $buf = $null; $cur = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$buf, [ref]$cur)
    if ($line.Trim() -and $buf -eq $line) {
        $s.Run++
        $s.Busy = $true
        & $s.Send @{ event = 'start'; run = $s.Run; cmd = $line; cwd = $PWD.ProviderPath }
    }
    if ($s.PrevHistory) { return $s.PrevHistory.Invoke($line) }
    return $true
}

# Command end: the next prompt
$__pp.PrevPrompt = $function:prompt
function global:prompt {
    $ok = $?
    $code = $global:LASTEXITCODE
    $s = $global:PixelPetShell
    if ($s.Busy) {
        $s.Busy = $false
        & $s.Send @{ event = 'end'; run = $s.Run; ok = $ok; code = $code }
    }
    $global:LASTEXITCODE = $code
    if ($s.PrevPrompt) { & $s.PrevPrompt } else { "PS $($PWD.Path)> " }
}

$global:PixelPetShell = $__pp
Remove-Variable __pp, __ppHandler
