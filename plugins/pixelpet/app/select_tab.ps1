# Windows Terminal 창(PP_HWND)에서 제목이 PP_TAB 인 탭을 선택한다. (앞의 상태 기호는 무시하고 비교)
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$A = [System.Windows.Automation.AutomationElement]
$root = $A::FromHandle([IntPtr][long]$env:PP_HWND)
$cond = New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, [System.Windows.Automation.ControlType]::TabItem)
foreach ($t in $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)) {
    $name = ($t.Current.Name -replace '^[^\w(\[]+', '').Trim()
    if ($name -eq $env:PP_TAB) {
        $t.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
        break
    }
}
