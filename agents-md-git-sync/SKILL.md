---
name: agents-md-git-sync
description: 在 Windows 上配置 opencode 启动/退出时自动通过 SSH + Git 同步 AGENTS.md 到 GitHub，包含防火墙 443 端口绕过方案和 PowerShell 包装脚本
tags: [git, github, ssh, powershell, windows, automation, agents-md, sync]
---

# AGENTS.md Git 自动同步技能

## 适用场景
需要在多台 Windows 机器间同步 opencode 全局规则文件（AGENTS.md），做到：
- 启动 opencode 前自动从 GitHub 拉取最新版本
- 退出 opencode 后自动检测变更并推送到 GitHub

## 技术栈
- Git + SSH (ed25519)
- PowerShell 脚本
- GitHub（SSH over 443 端口）

## 关键实现

### SSH 配置（解决 22 端口被封问题）
路径：`C:\Users\Administrator\.ssh\config`

```
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile C:/Users/Administrator/.ssh/id_ed25519_github
    IdentitiesOnly yes
```

### 生成 SSH 密钥
```powershell
Start-Process -NoNewWindow -Wait -FilePath "ssh-keygen" `
  -ArgumentList "-t","ed25519","-C","opencode-agents",`
    "-f","C:\Users\Administrator\.ssh\id_ed25519_github","-q","-N",'""'
```
然后将 `id_ed25519_github.pub` 内容添加到 GitHub Settings > SSH Keys。

### Git 仓库初始化（只追踪 AGENTS.md）
```powershell
$dir = "C:\Users\Administrator\.config\opencode"
git -C $dir init
git -C $dir remote add origin git@github.com:<user>/<repo>.git
git -C $dir config user.name "<user>"
git -C $dir config user.email "<user>@users.noreply.github.com"
```

`.gitignore` 内容：
```
*
!AGENTS.md
!.gitignore
```

### sync-agents.ps1（退出时推送）
```powershell
$repoDir = "C:\Users\Administrator\.config\opencode"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Set-Location $repoDir
$status = git status --porcelain AGENTS.md 2>&1
if ([string]::IsNullOrWhiteSpace($status)) { Write-Output "No changes"; exit 0 }
git stash 2>&1 | Out-Null
git pull origin main 2>&1 | Out-Null
git stash pop 2>&1 | Out-Null
git add AGENTS.md 2>&1 | Out-Null
git commit -m "auto: update AGENTS.md [$timestamp]" 2>&1 | Out-Null
git push origin main 2>&1
Write-Output "Synced [$timestamp]"
```

### pull-agents.ps1（启动时拉取）
```powershell
Set-Location "C:\Users\Administrator\.config\opencode"
$pull = git pull origin main 2>&1
if ($pull -match "Already up to date") { Write-Output "Up to date" }
else { Write-Output "Updated: $pull" }
```

### opencode-launch.ps1（包装脚本）
```powershell
Write-Host "[opencode] Pulling AGENTS.md..." -ForegroundColor Cyan
& "C:\Users\Administrator\.config\opencode\pull-agents.ps1"
opencode @args
Write-Host "[opencode] Pushing AGENTS.md..." -ForegroundColor Cyan
& "C:\Users\Administrator\.config\opencode\sync-agents.ps1"
```

### PowerShell Profile（oc 别名）
路径：`C:\Users\Administrator\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`
```powershell
function Invoke-OpenCode {
    & "C:\Users\Administrator\.config\opencode\opencode-launch.ps1" @args
}
Set-Alias -Name oc -Value Invoke-OpenCode
```

## 注意事项
- 所有 PowerShell 脚本必须使用纯 ASCII/英文，中文字符在某些编码环境下会导致解析失败
- `git pull --rebase` 在有未暂存文件时会失败，需先 `git stash` 再 `git pull` 再 `git stash pop`
- opencode 没有内置 lifecycle hook，必须用包装脚本实现启动/退出触发
