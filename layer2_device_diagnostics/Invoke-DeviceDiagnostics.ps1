<#
.SYNOPSIS
    Layer 2 orchestrator: runs the full device-level diagnostic suite on
    this machine and emits one combined JSON result.

.DESCRIPTION
    This is the single entry point the Python integration layer
    (integration/run_diagnostics.py) calls via subprocess for each
    inventory device flagged as a local host. It composes:
      - Get-DeviceInfo.ps1        (OS / hardware / installed software)
      - Test-PrinterPeripheral.ps1 (printer test page + USB peripherals)
      - real disk free-space and memory-pressure health thresholds

    and produces a single "HealthStatus" verdict (Healthy / Warning /
    Critical) using real, checkable thresholds rather than a stub value.

.PARAMETER SkipPrinterTest
    Passed through to Test-PrinterPeripheral.ps1's -SkipTestPage switch, so
    repeated diagnostic runs don't spool a physical page every time.

.OUTPUTS
    JSON object on stdout.
#>

[CmdletBinding()]
param(
    [switch]$SkipPrinterTest
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$deviceInfoJson = & (Join-Path $scriptDir 'Get-DeviceInfo.ps1')
$deviceInfo = $deviceInfoJson | ConvertFrom-Json

$printerArgs = @{}
if ($SkipPrinterTest) { $printerArgs['SkipTestPage'] = $true }
$printerJson = & (Join-Path $scriptDir 'Test-PrinterPeripheral.ps1') @printerArgs
$printerInfo = $printerJson | ConvertFrom-Json

# --- Real health-threshold evaluation (not a placeholder verdict) ---
$warnings = New-Object System.Collections.Generic.List[string]
$critical = New-Object System.Collections.Generic.List[string]

foreach ($disk in $deviceInfo.Disks) {
    if ($null -ne $disk.PercentFree) {
        if ($disk.PercentFree -lt 5) {
            $critical.Add("Disk $($disk.DeviceID) has only $($disk.PercentFree)% free space")
        } elseif ($disk.PercentFree -lt 15) {
            $warnings.Add("Disk $($disk.DeviceID) is low on space ($($disk.PercentFree)% free)")
        }
    }
}

if ($deviceInfo.TotalMemoryGB -gt 0) {
    $freeMemoryGB = $deviceInfo.FreePhysicalMemoryMB / 1024
    $freeMemoryPercent = [math]::Round(($freeMemoryGB / $deviceInfo.TotalMemoryGB) * 100, 1)
    if ($freeMemoryPercent -lt 5) {
        $critical.Add("Free physical memory critically low ($freeMemoryPercent%)")
    } elseif ($freeMemoryPercent -lt 15) {
        $warnings.Add("Free physical memory low ($freeMemoryPercent%)")
    }
}

foreach ($printer in $printerInfo.Printers) {
    if ($printer.PrinterStatus -notin @('Normal', 'Idle', 'Printing')) {
        $warnings.Add("Printer '$($printer.Name)' reporting status: $($printer.PrinterStatus)")
    }
    if ($printer.TestPageResult -like 'Failed:*') {
        $warnings.Add("Printer '$($printer.Name)' test page failed: $($printer.TestPageResult)")
    }
}

if ($critical.Count -gt 0) {
    $healthStatus = 'Critical'
} elseif ($warnings.Count -gt 0) {
    $healthStatus = 'Warning'
} else {
    $healthStatus = 'Healthy'
}

$result = [PSCustomObject]@{
    Hostname       = $deviceInfo.Hostname
    HealthStatus   = $healthStatus
    Warnings       = @($warnings)
    CriticalIssues = @($critical)
    DeviceInfo     = $deviceInfo
    PeripheralInfo = $printerInfo
    CheckedAt      = (Get-Date).ToString("o")
}

$result | ConvertTo-Json -Depth 6
