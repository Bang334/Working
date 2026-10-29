param([switch]$Launch)
$ErrorActionPreference='Stop'
$installRoot=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs\Antigravity IDE')).TrimEnd('\')
$stageRoot=[IO.Path]::GetFullPath((Join-Path $installRoot '_')).TrimEnd('\')
if($stageRoot -ne ($installRoot+'\_')){throw 'Unexpected staging path.'}
if(-not (Test-Path -LiteralPath (Join-Path $stageRoot 'Antigravity IDE.exe'))){throw 'Staged application executable not found.'}
if(-not (Test-Path -LiteralPath (Join-Path $stageRoot 'resources\app\product.json'))){throw 'Staged application resources not found.'}
$entries=@(Get-ChildItem -LiteralPath $stageRoot -Force | Where-Object { $_.Name -notlike 'is-*.tmp' })
foreach($entry in $entries){
    $resolvedSource=[IO.Path]::GetFullPath($entry.FullName)
    $resolvedTarget=[IO.Path]::GetFullPath((Join-Path $installRoot $entry.Name))
    if(-not $resolvedSource.StartsWith($stageRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Source is outside staging.'}
    if([IO.Path]::GetDirectoryName($resolvedTarget) -ne $installRoot){throw 'Destination is outside the installation root.'}
    if(Test-Path -LiteralPath $resolvedTarget){throw "Destination already exists; refusing overwrite: $($entry.Name)"}
}
$completed=[System.Collections.Generic.List[string]]::new()
try{
    foreach($entry in $entries){
        Move-Item -LiteralPath $entry.FullName -Destination (Join-Path $installRoot $entry.Name)
        $completed.Add($entry.Name)
    }
}catch{
    $originalError=$_
    for($index=$completed.Count-1;$index -ge 0;$index--){
        Move-Item -LiteralPath (Join-Path $installRoot $completed[$index]) -Destination (Join-Path $stageRoot $completed[$index])
    }
    throw $originalError
}
$appExe=Join-Path $installRoot 'Antigravity IDE.exe'
[pscustomobject]@{ExecutableExists=(Test-Path -LiteralPath $appExe);RestoredEntries=$completed.Count;InstallRoot=$installRoot} | ConvertTo-Json
if($Launch){
    $appProcess=Start-Process -FilePath $appExe -WorkingDirectory $installRoot -PassThru
    Write-Output "Launch requested, PID: $($appProcess.Id)"
}
