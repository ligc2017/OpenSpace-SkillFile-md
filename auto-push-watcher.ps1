# auto-push-watcher.ps1
# Watches the skills directory for new SKILL.md files and auto-pushes to GitHub.
# Run once at startup (added to opencode-launch.ps1).
# Runs silently in the background - check C:\OpenSpace\openspace\skills\auto-push.log

$SkillsDir = "C:\OpenSpace\openspace\skills"
$LogFile   = "$SkillsDir\auto-push.log"

function Write-Log {
    param([string]$Msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $Msg" | Out-File -FilePath $LogFile -Append -Encoding UTF8
}

Write-Log "auto-push-watcher started, watching $SkillsDir"

$watcher                     = New-Object System.IO.FileSystemWatcher
$watcher.Path                = $SkillsDir
$watcher.Filter              = "SKILL.md"
$watcher.IncludeSubdirectories = $true
$watcher.NotifyFilter        = [System.IO.NotifyFilters]::FileName -bor `
                               [System.IO.NotifyFilters]::LastWrite
$watcher.EnableRaisingEvents = $true

$action = {
    param($src, $e)
    Start-Sleep -Seconds 3   # wait for file to be fully written
    $path = $e.FullPath
    Write-Log "Detected new/changed: $path"

    $env:GIT_TERMINAL_PROMPT = "0"
    $env:GCM_INTERACTIVE     = "never"

    # Stage all changes
    & git -C $SkillsDir add -A 2>&1 | Out-File -FilePath $LogFile -Append -Encoding UTF8

    # Check if there is anything to commit
    $status = & git -C $SkillsDir status --porcelain 2>&1
    if (-not $status) {
        Write-Log "Nothing new to commit."
        return
    }

    # Commit
    $msg = "auto: new skill from session $(Get-Date -Format 'yyyyMMdd-HHmmss')"
    & git -C $SkillsDir commit -m $msg 2>&1 | Out-File -FilePath $LogFile -Append -Encoding UTF8

    # Push
    $pushOut = & git -C $SkillsDir push origin main 2>&1
    $pushOut | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Log "Push complete: $msg"
}

# Register for both Created and Changed events
Register-ObjectEvent -InputObject $watcher -EventName "Created" -Action $action | Out-Null
Register-ObjectEvent -InputObject $watcher -EventName "Changed" -Action $action | Out-Null

Write-Log "Watcher registered. Waiting for SKILL.md changes..."

# Keep alive
while ($true) {
    Start-Sleep -Seconds 30
}
