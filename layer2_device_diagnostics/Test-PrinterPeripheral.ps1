<#
.SYNOPSIS
    Layer 2 device-level diagnostics: real printer functional testing and
    peripheral (USB) enumeration.

.DESCRIPTION
    For every installed printer, this submits a real test-page print job to
    the Windows print spooler via the Win32_Printer.PrintTestPage WMI method
    (the same mechanism the "Print a test page" button in Windows printer
    properties uses) and reports the printer's live status and queue depth.
    It also enumerates connected USB peripherals via Get-PnpDevice.

.PARAMETER PrinterName
    Optional. If provided, only this printer is tested. Otherwise every
    installed printer is tested.

.PARAMETER SkipTestPage
    Optional switch. If set, printers are enumerated and their status
    reported, but no physical test page is queued. Useful for running this
    diagnostic repeatedly without spooling paper each time.

.OUTPUTS
    JSON object on stdout.
#>

[CmdletBinding()]
param(
    [string]$PrinterName,
    [switch]$SkipTestPage
)

$ErrorActionPreference = 'Stop'

$printers = Get-Printer -ErrorAction SilentlyContinue
if ($PrinterName) {
    $printers = $printers | Where-Object { $_.Name -eq $PrinterName }
}

$printerResults = @()

foreach ($printer in $printers) {
    $jobCount = (Get-PrintJob -PrinterName $printer.Name -ErrorAction SilentlyContinue | Measure-Object).Count

    $testResult = "Skipped (SkipTestPage set)"
    if (-not $SkipTestPage) {
        try {
            $escapedName = $printer.Name -replace "'", "''"
            $wmiPrinter = Get-CimInstance -ClassName Win32_Printer -Filter "Name='$escapedName'"
            if ($wmiPrinter) {
                Invoke-CimMethod -InputObject $wmiPrinter -MethodName PrintTestPage | Out-Null
                $testResult = "Test page job submitted to spooler"
            } else {
                $testResult = "Printer not found via WMI - test page not sent"
            }
        } catch {
            $testResult = "Failed: $($_.Exception.Message)"
        }
    }

    $printerResults += [PSCustomObject]@{
        Name           = $printer.Name
        DriverName     = $printer.DriverName
        PortName       = $printer.PortName
        PrinterStatus  = $printer.PrinterStatus.ToString()
        Shared         = $printer.Shared
        JobsInQueue    = $jobCount
        TestPageResult = $testResult
    }
}

$usbPeripherals = Get-PnpDevice -Class USB -Status OK -ErrorAction SilentlyContinue |
    Select-Object FriendlyName, InstanceId, Status

$result = [PSCustomObject]@{
    PrinterCount          = @($printers).Count
    Printers              = @($printerResults)
    USBPeripheralCount    = @($usbPeripherals).Count
    USBPeripheralsSample  = @($usbPeripherals | Select-Object -First 15)
    CheckedAt             = (Get-Date).ToString("o")
}

$result | ConvertTo-Json -Depth 5
