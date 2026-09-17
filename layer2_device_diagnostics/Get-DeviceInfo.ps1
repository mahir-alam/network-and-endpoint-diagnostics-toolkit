<#
.SYNOPSIS
    Layer 2 device-level diagnostics: pulls OS, hardware, and installed
    software info from the local machine using real, built-in Windows
    cmdlets (Get-ComputerInfo, CIM/WMI classes).

.OUTPUTS
    JSON object on stdout so it can be consumed by the Python integration
    layer (integration/run_diagnostics.py) via subprocess.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

try {
    $computerInfo = Get-ComputerInfo -Property CsName, WindowsProductName, WindowsVersion, OsArchitecture, CsProcessors
} catch {
    $computerInfo = $null
}

$os    = Get-CimInstance -ClassName Win32_OperatingSystem
$cs    = Get-CimInstance -ClassName Win32_ComputerSystem
$cpu   = Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1
$disks = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DriveType=3" |
    Select-Object DeviceID,
        @{Name = 'SizeGB'; Expression = { [math]::Round($_.Size / 1GB, 2) } },
        @{Name = 'FreeGB'; Expression = { [math]::Round($_.FreeSpace / 1GB, 2) } },
        @{Name = 'PercentFree'; Expression = { if ($_.Size) { [math]::Round(($_.FreeSpace / $_.Size) * 100, 1) } else { $null } } }

$memoryModules = Get-CimInstance -ClassName Win32_PhysicalMemory
$totalMemoryGB = [math]::Round(($memoryModules | Measure-Object -Property Capacity -Sum).Sum / 1GB, 2)

$uninstallPaths = @(
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$installedSoftware = Get-ItemProperty -Path $uninstallPaths -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName } |
    Select-Object -ExpandProperty DisplayName -Unique |
    Sort-Object

$result = [PSCustomObject]@{
    Hostname                = $env:COMPUTERNAME
    OS                      = $os.Caption
    OSVersion               = $os.Version
    OSArchitecture          = $os.OSArchitecture
    Manufacturer            = $cs.Manufacturer
    Model                   = $cs.Model
    CPU                     = $cpu.Name
    LogicalProcessors       = $cs.NumberOfLogicalProcessors
    TotalMemoryGB           = $totalMemoryGB
    FreePhysicalMemoryMB    = [math]::Round($os.FreePhysicalMemory / 1024, 0)
    Disks                   = @($disks)
    InstalledSoftwareCount  = $installedSoftware.Count
    InstalledSoftwareSample = @($installedSoftware | Select-Object -First 15)
    LastBootUpTime          = $os.LastBootUpTime.ToString("o")
    CheckedAt               = (Get-Date).ToString("o")
}

$result | ConvertTo-Json -Depth 4
