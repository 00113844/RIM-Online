$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$excel.AutomationSecurity = 3 # msoAutomationSecurityForceDisable

$file = (Resolve-Path "Ryegrass-RIM-*-DOWNLOAD-NOW.xlsm").Path
$wb = $excel.Workbooks.Open($file, 0, $true)

$excel.Calculate()

function Print-Range-TSV($sheetName, $rangeStr) {
    Write-Output "`n--- Range: $sheetName!$rangeStr ---"
    $ws = $wb.Sheets.Item($sheetName)
    $range = $ws.Range($rangeStr)
    $rows = $range.Rows.Count
    $cols = $range.Columns.Count
    
    for ($r = 1; $r -le $rows; $r++) {
        $rowVals = [System.Collections.Generic.List[string]]::new()
        for ($c = 1; $c -le $cols; $c++) {
            $cell = $range.Cells.Item($r, $c)
            # Use Value2 or Text
            $val = $cell.Text
            if ($val -eq $null) { $val = "" }
            $rowVals.Add($val)
        }
        Write-Output ($rowVals -join "`t")
    }
}

Print-Range-TSV "2.Strategy" "B1:U20"
Print-Range-TSV "1.Profile" "A1:Q30"
Print-Range-TSV "+Prices" "A1:Q40"
Print-Range-TSV "+Options" "A1:Q40"

Write-Output "`n--- Named Ranges ---"
foreach ($n in $wb.Names) {
    try {
        $rng = $n.RefersToRange
        if ($rng -and $rng.Count -eq 1) {
            $sheet = $rng.Worksheet.Name
            if ($sheet -eq "1.Profile" -or $sheet -eq "+Prices" -or $sheet -eq "+Options" -or $sheet -eq "2.Strategy") {
                $addr = $rng.Address($false, $false)
                $val = $rng.Text
                Write-Output "$($n.Name), $sheet!$addr, $val"
            }
        }
    } catch {}
}

$wb.Close($false)
$excel.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
[GC]::Collect()
[GC]::WaitForPendingFinalizers()
