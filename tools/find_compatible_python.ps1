$ErrorActionPreference = "SilentlyContinue"

$candidates = [System.Collections.Generic.List[string]]::new()
$seen = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)

function Add-Candidate([string] $Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    $expanded = [Environment]::ExpandEnvironmentVariables($Path.Trim('"'))
    if ((Test-Path -LiteralPath $expanded -PathType Leaf) -and $seen.Add($expanded)) {
        $candidates.Add($expanded)
    }
}

foreach ($commandName in @("python.exe", "python3.exe")) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command -and $command.Source) { Add-Candidate $command.Source }
}

$registryLocations = @(
    @([Microsoft.Win32.RegistryHive]::CurrentUser, [Microsoft.Win32.RegistryView]::Registry64),
    @([Microsoft.Win32.RegistryHive]::CurrentUser, [Microsoft.Win32.RegistryView]::Registry32),
    @([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64),
    @([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry32)
)

foreach ($location in $registryLocations) {
    try {
        $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($location[0], $location[1])
        $pythonCore = $base.OpenSubKey("Software\Python\PythonCore")
        if (-not $pythonCore) { continue }
        foreach ($versionName in ($pythonCore.GetSubKeyNames() | Sort-Object -Descending)) {
            $versionKey = $pythonCore.OpenSubKey($versionName)
            $installKey = $versionKey.OpenSubKey("InstallPath")
            if (-not $installKey) { continue }
            $executable = [string] $installKey.GetValue("ExecutablePath", "")
            if (-not $executable) {
                $folder = [string] $installKey.GetValue("", "")
                if ($folder) { $executable = Join-Path $folder "python.exe" }
            }
            Add-Candidate $executable
            $installKey.Dispose()
            $versionKey.Dispose()
        }
        $pythonCore.Dispose()
        $base.Dispose()
    } catch {
        continue
    }
}

foreach ($candidate in $candidates) {
    & $candidate -c "import struct,sys; raise SystemExit(0 if sys.version_info[:2] in ((3,10),(3,11),(3,12)) and struct.calcsize('P') == 8 else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Output $candidate
        exit 0
    }
}

exit 1
