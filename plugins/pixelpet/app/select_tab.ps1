# Select the tab in the Windows Terminal window PP_HWND whose title matches one of PP_TABS
# (newline separated, first wins), ignoring leading status glyphs. Retries briefly so a title
# change has time to reach the tab. WT may ignore UIA Select(), so fall back to one click on
# the tab and put the mouse back.
# NOTE: keep this file ASCII-only. Windows PowerShell 5.1 reads BOM-less UTF-8 as the ANSI
# code page, and a multibyte comment can swallow the following line.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class PPMouse {
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X; public int Y; }
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    public static void Click(int x, int y) {
        POINT old; GetCursorPos(out old);
        SetCursorPos(x, y);
        mouse_event(0x0002, 0, 0, 0, IntPtr.Zero);
        mouse_event(0x0004, 0, 0, 0, IntPtr.Zero);
        SetCursorPos(old.X, old.Y);
    }
}
'@
[void][PPMouse]::SetProcessDPIAware()
$A = [System.Windows.Automation.AutomationElement]
$root = $A::FromHandle([IntPtr][long]$env:PP_HWND)
$cond = New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, [System.Windows.Automation.ControlType]::TabItem)
$mark = $env:PP_MARK
$want = $env:PP_TABS
for ($try = 0; $try -lt 15; $try++) {
    $tabs = New-Object System.Collections.ArrayList
    foreach ($e in $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)) { [void]$tabs.Add($e) }
    foreach ($pass in @('mark', 'title')) {
        $hits = New-Object System.Collections.ArrayList
        foreach ($e in $tabs) {
            $name = $e.Current.Name
            if ($pass -eq 'mark') {
                if ($mark -and $name.Contains($mark)) { [void]$hits.Add($e) }
            } elseif ($want) {
                $plain = ($name -replace '[\u200b-\u200d\u2060]', '' -replace '^[^\w(\[]+', '').Trim()
                if ($plain -eq $want) { [void]$hits.Add($e) }
            }
        }
        if ($hits.Count -eq 1) {   # skip if several tabs share the title
            $t = $hits[0]
            $sel = $t.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
            if ($sel.Current.IsSelected) { exit 0 }
            $sel.Select()
            Start-Sleep -Milliseconds 80
            if (-not $sel.Current.IsSelected) {
                $r = $t.Current.BoundingRectangle
                if (-not $r.IsEmpty) { [PPMouse]::Click([int]($r.X + [Math]::Min(30, $r.Width / 2)), [int]($r.Y + $r.Height / 2)) }
            }
            exit 0
        }
    }
    Start-Sleep -Milliseconds 100
}
exit 1
