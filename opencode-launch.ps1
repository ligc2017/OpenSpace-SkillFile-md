# opencode-launch.ps1
# Wrapper: pull AGENTS.md + Skills before opencode starts, push both after exit

Write-Host "[opencode] Pulling AGENTS.md from GitHub..." -ForegroundColor Cyan
& "C:\Users\Administrator\.config\opencode\pull-agents.ps1"

Write-Host "[opencode] Pulling Skills from GitHub..." -ForegroundColor Cyan
& "C:\Users\Administrator\.config\opencode\pull-skills.ps1"
Write-Host ""

# Start auto-push watcher in background (watches skills dir, auto git push on new SKILL.md)
$watcherJob = Start-Job -FilePath "C:\Users\Administrator\.config\opencode\auto-push-watcher.ps1"
Write-Host "[opencode] Auto-push watcher started (job $($watcherJob.Id))" -ForegroundColor DarkGray

opencode @args

# Stop watcher after opencode exits
Stop-Job -Job $watcherJob -ErrorAction SilentlyContinue
Remove-Job -Job $watcherJob -ErrorAction SilentlyContinue
Write-Host "[opencode] Auto-push watcher stopped." -ForegroundColor DarkGray

# Run skill extractor on the last session via Ollama
Write-Host "[opencode] Running skill extractor on last session..." -ForegroundColor Cyan
python "C:\Users\Administrator\.config\opencode\extract_skill.py"

Write-Host ""
Write-Host "[opencode] Pushing AGENTS.md changes to GitHub..." -ForegroundColor Cyan
& "C:\Users\Administrator\.config\opencode\sync-agents.ps1"

Write-Host "[opencode] Pushing Skills changes to GitHub..." -ForegroundColor Cyan
& "C:\Users\Administrator\.config\opencode\sync-skills.ps1"
