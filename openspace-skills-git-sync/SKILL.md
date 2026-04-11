---
name: openspace-skills-git-sync
description: 在 OpenSpace skills 目录内建立独立 git 仓库，将 SKILL.md 技能文件自动同步到 GitHub，解决 OpenSpace 官方仓库 .gitignore 屏蔽 skills 目录的问题
tags: [git, github, openspace, skills, sync, automation, windows]
---

# OpenSpace Skills Git 自动同步技能

## 适用场景
OpenSpace 官方仓库的 `.gitignore` 明确忽略了 `openspace/skills/*`，导致用户积累的技能文件无法通过官方仓库同步。
本技能通过在 `skills/` 目录内建立**嵌套独立 git 仓库**解决此问题。

## 技术栈
- Git（嵌套仓库）
- PowerShell 脚本
- GitHub SSH

## 关键实现

### 为什么需要嵌套仓库
```
C:\OpenSpace\           ← 官方仓库（remote: HKUDS/OpenSpace）
  .gitignore            ← 包含 openspace/skills/*（刻意忽略）
  openspace\
    skills\             ← 在这里建立独立仓库
      .git\             ← 嵌套仓库（remote: 你的 GitHub）
      skill-a\
        SKILL.md
      skill-b\
        SKILL.md
```

### 初始化嵌套仓库
```powershell
$skillsDir = "C:\OpenSpace\openspace\skills"
git -C $skillsDir init
git -C $skillsDir config user.name "<user>"
git -C $skillsDir config user.email "<user>@users.noreply.github.com"
git -C $skillsDir remote add origin git@github.com:<user>/<repo>.git
git -C $skillsDir branch -M main
```

### sync-skills.ps1（退出时推送）
```powershell
$skillsDir = "C:\OpenSpace\openspace\skills"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Set-Location $skillsDir
$status = git status --porcelain 2>&1
if ([string]::IsNullOrWhiteSpace($status)) { Write-Output "No skill changes"; exit 0 }
git stash 2>&1 | Out-Null
git pull origin main 2>&1 | Out-Null
git stash pop 2>&1 | Out-Null
git add -A 2>&1 | Out-Null
git commit -m "auto: update skills [$timestamp]" 2>&1 | Out-Null
git push origin main 2>&1
Write-Output "Skills synced [$timestamp]"
```

### pull-skills.ps1（启动时拉取）
```powershell
Set-Location "C:\OpenSpace\openspace\skills"
$pull = git pull origin main 2>&1
if ($pull -match "Already up to date") { Write-Output "Skills up to date" }
else { Write-Output "Skills updated: $pull" }
```

## SKILL.md 文件格式
每个技能是一个子目录，包含 `SKILL.md`，必须以 YAML frontmatter 开头：
```markdown
---
name: skill-name
description: 技能描述（用于搜索匹配）
tags: [tag1, tag2]
---
# 技能正文
具体的操作步骤和代码示例...
```

## 注意事项
- OpenSpace 官方 `.gitignore` 屏蔽了 skills 目录，必须用嵌套仓库，不能直接提交到官方仓库
- `openspace.db` 记录技能的元数据和索引，但 SKILL.md 文件才是实际内容，两者都需要存在
- 嵌套仓库与外层仓库完全独立，不会互相干扰
