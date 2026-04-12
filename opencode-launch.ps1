# opencode-launch.ps1
# All git sync and skill extraction run in background - user enters opencode immediately.
# Logs: $env:USERPROFILE\.config\opencode\launch.log

$ConfigDir = "$env:USERPROFILE\.config\opencode"
$LogFile   = "$ConfigDir\launch.log"

function Write-Log {
    param([string]$Msg, [string]$Color = "DarkGray")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $Msg" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Host "[opencode] $Msg" -ForegroundColor $Color
}

# ── Background: pull AGENTS.md + Skills on startup ─────────────────────────
$pullJob = Start-Job -ScriptBlock {
    param($ConfigDir, $LogFile)

    function Log([string]$m) {
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "$ts [pull] $m" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    }

    $env:GIT_TERMINAL_PROMPT = "0"
    $env:GCM_INTERACTIVE     = "never"
    $env:GIT_PAGER           = "cat"

    # Pull AGENTS.md
    $r = git -C $ConfigDir pull origin main 2>&1
    if ($r -match "Already up to date") { Log "AGENTS.md up to date" }
    else { Log "AGENTS.md pulled: $r" }

    # Pull Skills
    $skillsDir = "C:\OpenSpace\openspace\skills"
    $r2 = git -C $skillsDir pull origin main 2>&1
    if ($r2 -match "Already up to date") { Log "Skills up to date" }
    else { Log "Skills pulled: $r2" }

    Log "Pull complete"
} -ArgumentList $ConfigDir, $LogFile

Write-Log "Background sync started (pull job $($pullJob.Id))" "DarkGray"

# ── Background: auto-push watcher ──────────────────────────────────────────
$watcherJob = Start-Job -FilePath "$ConfigDir\auto-push-watcher.ps1"

# ── Launch opencode immediately ─────────────────────────────────────────────
& (Get-Command opencode -CommandType ExternalScript).Source @args
$ocExitCode = $LASTEXITCODE

# ── After opencode exits: fire background cleanup ───────────────────────────

# Stop watcher
Stop-Job  -Job $watcherJob -ErrorAction SilentlyContinue
Remove-Job -Job $watcherJob -ErrorAction SilentlyContinue

# Stop pull job (may already be done)
Stop-Job  -Job $pullJob -ErrorAction SilentlyContinue
Remove-Job -Job $pullJob -ErrorAction SilentlyContinue

Write-Log "opencode exited (code $ocExitCode). Running background cleanup..." "DarkGray"

# Fire extract + sync as a single detached background job so the terminal
# returns to the prompt immediately.
Start-Job -ScriptBlock {
    param($ConfigDir, $LogFile)

    function Log([string]$m) {
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "$ts [exit] $m" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    }

    $env:GIT_TERMINAL_PROMPT = "0"
    $env:GCM_INTERACTIVE     = "never"
    $env:GIT_PAGER           = "cat"

    Log "Starting skill extraction..."

    # 1. Extract skills via Ollama
    $extractOut = python "$ConfigDir\extract_skill.py" 2>&1
    Log "extract_skill: $extractOut"

    # 2. Sync AGENTS.md
    $agentsStatus = git -C $ConfigDir status --porcelain AGENTS.md 2>&1
    if (-not [string]::IsNullOrWhiteSpace($agentsStatus)) {
        $ts2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        git -C $ConfigDir add AGENTS.md 2>&1 | Out-Null
        git -C $ConfigDir commit -m "auto: update AGENTS.md [$ts2]" 2>&1 | Out-Null
        $r = git -C $ConfigDir push origin main 2>&1
        Log "AGENTS.md pushed: $r"
    } else {
        Log "AGENTS.md: no changes"
    }

    # 3. Sync Skills
    $skillsDir = "C:\OpenSpace\openspace\skills"
    $skillsStatus = git -C $skillsDir status --porcelain 2>&1
    if (-not [string]::IsNullOrWhiteSpace($skillsStatus)) {
        $ts2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        git -C $skillsDir add -A 2>&1 | Out-Null
        git -C $skillsDir commit -m "auto: update skills [$ts2]" 2>&1 | Out-Null
        $r = git -C $skillsDir push origin main 2>&1
        Log "Skills pushed: $r"
    } else {
        Log "Skills: no changes"
    }

    Log "Background cleanup complete."

} -ArgumentList $ConfigDir, $LogFile | Out-Null

Write-Host "[opencode] Background sync running. Check launch.log for details." -ForegroundColor DarkGray

exit $ocExitCode
