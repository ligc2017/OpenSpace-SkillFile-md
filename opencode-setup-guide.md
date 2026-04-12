# OpenCode + OpenSpace 新机器部署指南

> 适用系统：**Windows 10（版本 1903+）/ Windows 11，AMD64**
> 目标：在新电脑上复现完整的 OpenCode + OpenSpace + AGENTS.md 自动同步 + Ollama 自动技能提取的工作环境

---

## Windows 10 兼容性说明

本指南完全兼容 Windows 10，但需满足以下条件：

| 检查项 | 要求 | 验证方法 |
|-------|------|---------|
| Windows 10 版本 | **1903 或更高**（Ollama 要求） | `Win+R` → 输入 `winver` → 查看版本号 |
| 系统位数 | 64 位 | `winver` 窗口中显示 |
| PowerShell | 5.1+（Win10 自带） | `$PSVersionTable.PSVersion` |

> **如果版本低于 1903**：先执行 Windows Update 升级，或跳过 Ollama 安装（技能自动提取功能不可用，其他功能正常）。

### 关于路径中的用户名

本指南所有命令使用 `$env:USERPROFILE` 变量代替具体用户名，**在任何 Windows 账户下直接复制粘贴均可运行**，无需手动替换路径。

```powershell
# 确认你的用户目录路径
echo $env:USERPROFILE
# 输出示例：C:\Users\Administrator  或  C:\Users\张三  或  C:\Users\john
```

---

## 前置要求

在开始之前，确保新机器已安装：

- **Node.js** (v18+)：https://nodejs.org/
- **Python 3.11+**：https://www.python.org/downloads/
- **Git**：https://git-scm.com/download/win

安装完成后，打开 PowerShell 验证：

```powershell
node --version
python --version
git --version
```

### 配置 Git 全局用户信息（必做，否则无法 commit）

```powershell
git config --global user.name "ligc2017"
git config --global user.email "2317859012@qq.com"
```

验证：

```powershell
git config --global --list
# 应输出 user.name=ligc2017 和 user.email=2317859012@qq.com
```

---

## 第一步：安装 OpenCode

```powershell
npm install -g opencode-ai
```

验证安装：

```powershell
opencode --version
```

> **Windows 10 注意**：如果提示 `opencode` 不是可识别的命令，需要将 npm 全局路径加入环境变量：
> 1. 搜索"环境变量" → 编辑系统环境变量 → 环境变量
> 2. 在"用户变量"和"系统变量"的 `Path` 中均添加：`%APPDATA%\npm`
> 3. 重新打开 PowerShell

---

## 第二步：安装 oh-my-openagent 插件

```powershell
npm install -g oh-my-opencode
npm install -g oh-my-opencode-windows-x64 --force
```

---

## 第三步：安装 OpenSpace

```powershell
# 克隆 OpenSpace 到 C:\OpenSpace
git clone https://github.com/kangwork/openspace C:\OpenSpace

# 安装 Python 依赖
pip install -e C:\OpenSpace
```

> 如果 `pip install -e` 报错，尝试：`python -m pip install -e C:\OpenSpace`

---

## 第四步：安装 Ollama（自动技能提取引擎）

Ollama 是本地 AI 推理引擎，用于在退出 opencode 时自动分析对话内容并提取可复用技能。

### 4.1 下载安装

从官网下载安装包：https://ollama.com/download/windows

双击 `OllamaSetup.exe` 安装，完成后 Ollama 会在后台运行（系统托盘可见）。

> **Windows 10 兼容**：支持 Windows 10 版本 1903 及以上，安装无需管理员权限。

### 4.2 根据硬件选择合适的模型

> **关于集显笔记本（只有核显，无独立显卡）**：
> Ollama **完全支持纯 CPU 运行**，集显笔记本可以正常使用，但要选择小模型。
> 集显不会被 Ollama 利用（Intel HD/UHD/Iris 和 AMD Radeon 核显不支持 GPU 加速），
> 推理完全由 CPU + 内存承担。

| 硬件配置 | 推荐模型 | 下载大小 | 速度参考 |
|---------|---------|---------|---------|
| 集显笔记本，8GB RAM | `qwen2.5-coder:1.5b` | ~1GB | 5-8 tok/s，可用 |
| 集显笔记本，16GB RAM | `qwen2.5-coder:3b` | ~1.9GB | 5-8 tok/s，流畅 |
| 独显台式机，8GB VRAM | `qwen2.5-coder:7b` | ~4.7GB | 40+ tok/s，快速 |
| 独显台式机，16GB VRAM | `qwen2.5-coder:14b` | ~9GB | 30+ tok/s，高质量 |

**集显笔记本建议直接用 `3b`**：质量够用于技能提取，速度尚可接受（一次提取约 1-2 分钟，退出后台运行不影响使用）。

### 4.3 拉取模型

```powershell
# 集显笔记本（8GB RAM）
ollama pull qwen2.5-coder:1.5b

# 集显笔记本（16GB RAM）- 推荐
ollama pull qwen2.5-coder:3b

# 独显台式机
ollama pull qwen2.5-coder:14b
```

验证模型可用：

```powershell
ollama list
ollama run qwen2.5-coder:3b "hello"
```

### 4.4 修改 extract_skill.py 中的模型配置

如果使用的不是 `14b`，需要修改脚本中的模型名称（在第九步拉取脚本后执行）：

```powershell
notepad "$env:USERPROFILE\.config\opencode\extract_skill.py"
```

找到并修改这一行：

```python
# 改成你已经拉取的模型
OLLAMA_MODEL = "qwen2.5-coder:3b"   # 集显笔记本用这个
# OLLAMA_MODEL = "qwen2.5-coder:14b"  # 独显台式机用这个
```

---

## 第五步：配置 opencode

创建配置目录：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.config\opencode"
```

写入以下内容（新建或覆盖 `opencode.json`）：

```powershell
@'
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/qwen3.6-plus-free",
  "plugin": [
    "oh-my-openagent@latest"
  ],
  "mcp": {
    "openspace": {
      "type": "local",
      "command": [
        "python",
        "-m",
        "openspace.mcp_server"
      ],
      "environment": {
        "PYTHONPATH": "C:\\OpenSpace"
      }
    }
  }
}
'@ | Set-Content "$env:USERPROFILE\.config\opencode\opencode.json" -Encoding UTF8
```

---

## 第六步：运行 oh-my-openagent 安装器

```powershell
npx oh-my-opencode install --no-tui --claude=no --openai=no --gemini=no --copilot=no --opencode-zen=no --opencode-go=no --zai-coding-plan=no
```

然后覆盖 `oh-my-opencode.json`，为每个 agent 分配最合适的免费模型：

```powershell
@'
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/assets/oh-my-opencode.schema.json",
  "agents": {
    "hephaestus":        { "model": "opencode/big-pickle" },
    "oracle":            { "model": "opencode/minimax-m2.5-free" },
    "librarian":         { "model": "opencode/nemotron-3-super-free" },
    "explore":           { "model": "opencode/nemotron-3-super-free" },
    "multimodal-looker": { "model": "opencode/gpt-5-nano" },
    "prometheus":        { "model": "opencode/big-pickle" },
    "metis":             { "model": "opencode/big-pickle" },
    "momus":             { "model": "opencode/minimax-m2.5-free" },
    "atlas":             { "model": "opencode/minimax-m2.5-free" },
    "sisyphus-junior":   { "model": "opencode/minimax-m2.5-free" }
  },
  "categories": {
    "visual-engineering": { "model": "opencode/gpt-5-nano" },
    "ultrabrain":         { "model": "opencode/big-pickle" },
    "deep":               { "model": "opencode/big-pickle" },
    "artistry":           { "model": "opencode/gpt-5-nano" },
    "quick":              { "model": "opencode/gpt-5-nano" },
    "unspecified-low":    { "model": "opencode/gpt-5-nano" },
    "unspecified-high":   { "model": "opencode/nemotron-3-super-free" },
    "writing":            { "model": "opencode/nemotron-3-super-free" }
  }
}
'@ | Set-Content "$env:USERPROFILE\.config\opencode\oh-my-opencode.json" -Encoding UTF8
```

---

## 第七步：配置 SSH 密钥连接 GitHub

**在开始之前，先选择你的路径：**

| 场景 | 推荐方案 |
|------|---------|
| 新电脑，想直接复用主力机密钥（无需再次添加到 GitHub） | → **方案 A：恢复原私钥** |
| 新电脑，想为这台机器单独生成一对新密钥 | → **方案 B：生成新密钥并添加到 GitHub** |

---

### 方案 A：恢复原私钥（推荐迁移场景）

**原理**：主力机的私钥 + 公钥已经添加到 GitHub，直接把这对密钥复制到新机器，GitHub 就能认出来，无需任何 GitHub 操作。

**第一步**：在新机器上创建 `.ssh` 目录：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.ssh" | Out-Null
```

**第二步**：从主力机（U 盘 / 局域网共享 / 其他方式）复制以下两个文件到新机器的 `%USERPROFILE%\.ssh\`：

```
id_ed25519_github      ← 私钥（无后缀，重要！）
id_ed25519_github.pub  ← 公钥（可选，方便查看）
```

> **主力机文件位置**：`C:\Users\Administrator\.ssh\id_ed25519_github`
>
> **公钥内容**（已添加到 GitHub，供对照验证）：
> ```
> ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOOg5fYXL1iR71jIzZPWwRK+wT7f+4Ld6qs15T1ol1jV ligc2017@github-opencode-agents
> ```

**第三步**：设置私钥文件权限（Windows 必须，否则 SSH 拒绝使用）：

```powershell
$keyFile = "$env:USERPROFILE\.ssh\id_ed25519_github"
# 移除继承权限，只保留当前用户的完全控制
icacls $keyFile /inheritance:r /grant:r "${env:USERNAME}:F" | Out-Null
```

**第四步**：写入 SSH config：

```powershell
@"
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile $env:USERPROFILE/.ssh/id_ed25519_github
    IdentitiesOnly yes
"@ | Set-Content "$env:USERPROFILE\.ssh\config" -Encoding UTF8
```

**第五步**：验证：

```powershell
ssh -T git@github.com -o StrictHostKeyChecking=no
# 期望输出：Hi ligc2017! You've successfully authenticated
```

---

### 方案 B：生成新密钥并添加到 GitHub

**第一步**：生成新密钥对：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.ssh" | Out-Null
ssh-keygen -t ed25519 -C "opencode-agents" -f "$env:USERPROFILE\.ssh\id_ed25519_github" -q -N '""'
```

**第二步**：配置 SSH（443 端口，绕过防火墙）：

```powershell
@"
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile $env:USERPROFILE/.ssh/id_ed25519_github
    IdentitiesOnly yes
"@ | Set-Content "$env:USERPROFILE\.ssh\config" -Encoding UTF8
```

**第三步**：查看新公钥：

```powershell
cat "$env:USERPROFILE\.ssh\id_ed25519_github.pub"
```

复制输出，然后添加到 GitHub：

1. 打开 https://github.com/settings/ssh/new
2. Title：`opencode-windows-新机器名称`
3. Key type：`Authentication Key`
4. Key：粘贴上面复制的公钥
5. 点击 **Add SSH key**

> **为什么用 443 端口**：普通 SSH 走 22 端口，很多网络环境（公司/学校/部分代理）会屏蔽 22 端口，443 端口是 HTTPS 端口，几乎不会被屏蔽。

---

### 7.4 验证连接

```powershell
ssh -T git@github.com -o StrictHostKeyChecking=no
```

看到 `Hi ligc2017! You've successfully authenticated` 即成功。

### 7.5 如果开了代理（VPN/Clash/v2ray）仍然连不上

**问题原因**：SSH 协议默认不走系统代理，即使你的代理软件已经开启，SSH 连接仍然走直连。

**解决方案**：让 SSH 通过代理连接 GitHub。

首先确认你的代理本地端口（通常是以下之一）：
- Clash：`7890`（或 `7891`）
- v2rayN：`10808`（或 `1080`）
- 其他：查看代理软件设置里的"本地端口"

然后更新 SSH config，加入 `ProxyCommand`：

```powershell
# 先安装 ncat（netcat，用于 SSH 代理转发）
# 如果已安装 Git for Windows，ncat 通常在这里：
# C:\Program Files\Git\usr\bin\ncat.exe

# 方法一：使用 ncat（Git 自带）
@"
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile $env:USERPROFILE/.ssh/id_ed25519_github
    IdentitiesOnly yes
    ProxyCommand "C:\Program Files\Git\usr\bin\ncat.exe" --proxy 127.0.0.1:7890 --proxy-type socks5 %h %p
"@ | Set-Content "$env:USERPROFILE\.ssh\config" -Encoding UTF8
```

> 把 `7890` 换成你实际的代理端口。

验证：

```powershell
ssh -T git@github.com -o StrictHostKeyChecking=no -v 2>&1 | Select-String "connect|auth|debug"
```

**如果不想用代理连接 GitHub**（代理只用于上网，GitHub 走直连）：

在代理软件里把 `github.com` 加入**直连名单/绕过列表**，不走代理，然后用 443 端口的 SSH 直连通常也能成功。

---

## 第八步（A）：初始化 AGENTS.md git 仓库

```powershell
$repoDir = "$env:USERPROFILE\.config\opencode"

# 初始化仓库
git -C $repoDir init

# 配置用户信息
git -C $repoDir config user.name "ligc2017"
git -C $repoDir config user.email "ligc2017@users.noreply.github.com"
```

写入 `.gitignore`，只追踪必要文件：

```powershell
@'
# Ignore everything
*

# Track only these files
!AGENTS.md
!CONTINUITY.md
!extract_skill.py
!auto-push-watcher.ps1
!opencode-launch.ps1
!opencode-setup-guide.md
!pull-agents.ps1
!pull-skills.ps1
!sync-agents.ps1
!sync-skills.ps1
!.gitignore
'@ | Set-Content "$env:USERPROFILE\.config\opencode\.gitignore" -Encoding UTF8
```

```powershell
# 从 GitHub 拉取现有内容（含 AGENTS.md 和所有脚本，一步到位）
git -C $repoDir remote add origin git@github.com:ligc2017/OpenSpace-SkillFile-md.git
git -C $repoDir fetch origin
git -C $repoDir branch -M main
git -C $repoDir reset --hard origin/main
```

> 拉取完成后，`extract_skill.py`、`opencode-launch.ps1` 等所有脚本自动到位，无需手动创建。

---

## 第八步（B）：初始化 Skills 目录嵌套 git 仓库

> **背景**：OpenSpace 官方 `.gitignore` 屏蔽了 `openspace/skills/*` 目录，因此需要在 skills 目录内建立**独立的嵌套 git 仓库**，指向同一个 GitHub 远程仓库。

```powershell
$skillsDir = "C:\OpenSpace\openspace\skills"

# 初始化独立嵌套仓库
git -C $skillsDir init

# 配置用户信息
git -C $skillsDir config user.name "ligc2017"
git -C $skillsDir config user.email "ligc2017@users.noreply.github.com"

# 连接到同一个 GitHub 远程仓库
git -C $skillsDir remote add origin git@github.com:ligc2017/OpenSpace-SkillFile-md.git

# 拉取远程内容（--allow-unrelated-histories 是必须的）
git -C $skillsDir fetch origin
git -C $skillsDir branch -M main
git -C $skillsDir pull origin main --allow-unrelated-histories
```

验证：

```powershell
git -C $skillsDir remote -v
git -C $skillsDir log --oneline -5
```

---

## 第八步（C）：修复脚本中的硬编码路径（新机器必做）

从 GitHub 拉取的脚本是在 `Administrator` 账户下编写的，**如果新机器用户名不是 `Administrator`**，需要一键替换所有脚本中的残留路径。

```powershell
$configDir = "$env:USERPROFILE\.config\opencode"
$oldPath   = "C:\\Users\\Administrator"
$newPath   = $env:USERPROFILE.Replace("\", "\\")

# 替换所有 .ps1 和 .py 文件中的硬编码路径
Get-ChildItem "$configDir\*.ps1", "$configDir\*.py" | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match [regex]::Escape("C:\Users\Administrator")) {
        ($content -replace [regex]::Escape($oldPath), $newPath) |
            Set-Content $_.FullName -Encoding UTF8 -NoNewline
        Write-Host "Fixed: $($_.Name)"
    }
}
```

> **如果用户名就是 `Administrator`**：直接跳过这步，无需执行。

验证替换结果：

```powershell
# 确认 opencode-launch.ps1 里已没有 Administrator 字样
Select-String -Path "$env:USERPROFILE\.config\opencode\opencode-launch.ps1" -Pattern "Administrator"
# 应无输出（空输出 = 替换成功）
```

---

## 第九步：修改 extract_skill.py 中的模型（集显笔记本必做）

拉取完成后，`extract_skill.py` 默认使用 `qwen2.5-coder:14b`。集显笔记本需修改：

```powershell
# 用 PowerShell 直接替换（不需要手动打开文件）
$file = "$env:USERPROFILE\.config\opencode\extract_skill.py"
(Get-Content $file) -replace 'OLLAMA_MODEL\s*=\s*"qwen2.5-coder:14b"', 'OLLAMA_MODEL = "qwen2.5-coder:3b"' | Set-Content $file -Encoding UTF8
```

或者手动打开修改：

```powershell
notepad "$env:USERPROFILE\.config\opencode\extract_skill.py"
```

找到并修改：`OLLAMA_MODEL = "qwen2.5-coder:3b"`

---

## 第十步：配置 PowerShell Profile

```powershell
# 确保 profile 目录存在
New-Item -ItemType Directory -Force -Path (Split-Path $PROFILE)
```

写入 Profile（如果文件已存在会追加，不会覆盖）：

```powershell
$configDir = "$env:USERPROFILE\.config\opencode"

@"

# opencode launcher: auto-sync AGENTS.md + skill extraction on exit
function Invoke-OpenCode {
    & "$configDir\opencode-launch.ps1" @args
}
Set-Alias -Name oc -Value Invoke-OpenCode

# Override bare 'opencode' command to go through the launch wrapper
function opencode {
    & "$configDir\opencode-launch.ps1" @args
}

# oclog - view opencode background task log
# Usage: oclog | oclog -f | oclog -n 50
function oclog {
    param([switch]`$f, [int]`$n = 30)
    `$log = "$configDir\launch.log"
    if (-not (Test-Path `$log)) { Write-Host "No log file yet." -ForegroundColor Yellow; return }
    if (`$f) { Get-Content `$log -Wait -Tail `$n } else { Get-Content `$log -Tail `$n }
}
"@ | Add-Content $PROFILE -Encoding UTF8

# 立即加载
. $PROFILE
```

验证：

```powershell
Get-Command opencode   # 应显示 Function（不是 ExternalScript）
Get-Command oclog      # 应显示 Function
```

---

## 第十一步：创建 /sync-agents 命令（TUI 内手动同步）

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.config\opencode\commands"

@'
---
description: Sync AGENTS.md to GitHub (check changes and push)
---
Please run the following shell command to check if AGENTS.md has changed and push to GitHub:

!`powershell -Command "& '$env:USERPROFILE\.config\opencode\sync-agents.ps1' 2>&1"`

Report the sync result based on the output above.
'@ | Set-Content "$env:USERPROFILE\.config\opencode\commands\sync-agents.md" -Encoding UTF8
```

---

## 第十二步：验证全部配置

```powershell
# 1. 测试 OpenSpace MCP
opencode mcp list

# 2. 测试 oh-my-openagent
oh-my-opencode doctor

# 3. 测试 Ollama
ollama list
ollama run qwen2.5-coder:3b "Write a hello world in Python"

# 4. 测试 extract_skill.py（只检测，不调用 Ollama）
python "$env:USERPROFILE\.config\opencode\extract_skill.py" --check-only

# 5. 验证命令
Get-Command opencode
Get-Command oclog
```

---

## 整体工作流说明

### 启动时（后台自动）
```
输入: opencode
  → 立即进入 opencode 界面
  → 后台静默 pull 最新 AGENTS.md + Skills
  → 启动 auto-push-watcher 监听新 SKILL.md
```

### 使用中
```
正常使用 opencode...
如果 AI 写入了新 SKILL.md → watcher 自动 git push 到 GitHub
```

### 退出时（后台自动）
```
退出 opencode（Ctrl+Q）→ 立即回到终端提示符
  后台异步执行：
  → extract_skill.py 调用 Ollama 分析本次对话
  → 如有新技能 → 写入 SKILL.md → push 到 GitHub
  → sync AGENTS.md（如有变更）→ push
  → sync Skills（如有变更）→ push
```

### 查看后台状态
```powershell
oclog        # 最近 30 行日志
oclog -f     # 实时跟踪（Ctrl+C 停止）
oclog -n 100 # 最近 100 行
```

---

## 日常使用

| 操作 | 命令 |
|------|------|
| 启动 opencode（自动同步）| `opencode` 或 `oc` |
| TUI 内手动同步 AGENTS.md | `/sync-agents` |
| 查看后台日志 | `oclog` |
| 实时跟踪后台进度 | `oclog -f` |
| 手动运行技能提取 | `python "$env:USERPROFILE\.config\opencode\extract_skill.py"` |
| 强制重新提取 | `python "$env:USERPROFILE\.config\opencode\extract_skill.py" --force` |
| 查看已提取 session | `Get-Content "$env:USERPROFILE\.config\opencode\extracted_sessions.json" \| ConvertFrom-Json \| Format-Table` |

---

## 文件清单

部署完成后，以下文件应全部存在（路径中 `<用户名>` 为你的实际用户名）：

```
C:\Users\<用户名>\
├── .ssh\
│   ├── id_ed25519_github       # SSH 私钥
│   ├── id_ed25519_github.pub   # SSH 公钥（已添加到 GitHub）
│   └── config                  # SSH 配置（443 端口）
├── .config\opencode\
│   ├── opencode.json           # opencode 主配置
│   ├── oh-my-opencode.json     # agent 模型分配
│   ├── AGENTS.md               # 全局 AI 行为规则（同步到 GitHub）
│   ├── CONTINUITY.md           # 跨对话任务续作文件
│   ├── extract_skill.py        # Ollama 技能提取脚本
│   ├── auto-push-watcher.ps1   # FileSystemWatcher 自动 push
│   ├── opencode-launch.ps1     # 包装启动脚本（异步同步）
│   ├── opencode-setup-guide.md # 本部署指南
│   ├── launch.log              # 后台操作日志（运行时自动生成）
│   ├── extracted_sessions.json # 已提取的 session 记录（运行时自动生成）
│   ├── sync-agents.ps1         # 手动推送 AGENTS.md
│   ├── pull-agents.ps1         # 手动拉取 AGENTS.md
│   ├── sync-skills.ps1         # 手动推送 Skills
│   ├── pull-skills.ps1         # 手动拉取 Skills
│   ├── .gitignore              # 追踪必要文件
│   ├── .git\                   # AGENTS.md git 仓库
│   └── commands\
│       └── sync-agents.md      # /sync-agents TUI 命令
└── Documents\WindowsPowerShell\
    └── Microsoft.PowerShell_profile.ps1  # opencode/oc/oclog 命令定义

C:\OpenSpace\                   # OpenSpace 官方仓库克隆
└── openspace\
    └── skills\                 # Skills 嵌套 git 仓库
        ├── .git\               # 独立 git 仓库（remote: ligc2017/OpenSpace-SkillFile-md）
        └── <skill-name>\
            └── SKILL.md
```

---

## GitHub 仓库

同步目标：`git@github.com:ligc2017/OpenSpace-SkillFile-md.git`
分支：`main`

| 仓库路径 | 追踪内容 |
|---------|---------|
| `%USERPROFILE%\.config\opencode\` | AGENTS.md、脚本文件、部署指南 |
| `C:\OpenSpace\openspace\skills\` | 所有 `*/SKILL.md` 技能文件 |

> 两个目录使用**同一个** GitHub 远程仓库，但独立的 git 历史，通过 `--allow-unrelated-histories` 合并。

---

## 常见问题

### Q: Windows 10 和 Windows 11 安装步骤有区别吗？
没有区别，所有命令完全相同。唯一差异是 Windows 10 需要手动添加 npm 路径到环境变量（第一步有说明）。

### Q: git commit 时报错"Please tell me who you are"？
忘记配置 git 用户信息了，执行：
```powershell
git config --global user.name "ligc2017"
git config --global user.email "2317859012@qq.com"
```

### Q: 公钥已经添加到 GitHub，但 ssh -T git@github.com 还是连不上？

**第一步：确认用的是正确的密钥文件**
```powershell
# 检查 SSH config 里的密钥路径是否存在
Test-Path "$env:USERPROFILE\.ssh\id_ed25519_github"
# 应输出 True

# 检查 SSH config 内容
cat "$env:USERPROFILE\.ssh\config"
```

**第二步：开启了代理（Clash/v2ray/VPN）的情况**

SSH 默认不走系统代理，即使代理开着也不起作用。有两个解法：

- **方案 A（推荐）**：在代理软件里把 `github.com` 加入**直连/绕过列表**，让 SSH 走直连 + 443 端口
- **方案 B**：让 SSH 通过代理转发（需要 ncat）：

```powershell
# 把 7890 换成你的代理本地端口（Clash 默认 7890，v2rayN 默认 10808）
@"
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile $env:USERPROFILE/.ssh/id_ed25519_github
    IdentitiesOnly yes
    ProxyCommand "C:\Program Files\Git\usr\bin\ncat.exe" --proxy 127.0.0.1:7890 --proxy-type socks5 %h %p
"@ | Set-Content "$env:USERPROFILE\.ssh\config" -Encoding UTF8
```

**第三步：查看详细错误信息**
```powershell
ssh -T git@github.com -o StrictHostKeyChecking=no -v 2>&1 | Select-String -Pattern "connect|auth|Permission|timeout|proxy"
```

常见错误对照：

| 错误信息 | 原因 | 解决 |
|---------|------|------|
| `Permission denied (publickey)` | 公钥没加到 GitHub，或用了错误的密钥文件 | 检查 GitHub 设置里是否有该公钥；检查 SSH config 里密钥路径 |
| `Connection timed out` | 网络不通，或代理拦截了 SSH | 换方案 A/B |
| `Connection refused` | 22 端口被封，但 config 没写 443 | 检查 SSH config 是否有 `Port 443` |
| `Could not resolve hostname` | DNS 问题 | 检查代理设置，或手动 `nslookup ssh.github.com` |

### Q: 集显笔记本上 Ollama 提取速度很慢怎么办？
退出 opencode 后提取在后台异步进行，不阻塞终端。用 `oclog -f` 观察进度。
如果想更快，换 `1.5b` 模型（速度翻倍，质量略降但对技能提取够用）。

### Q: Ollama 提取出来的技能质量差怎么办？
小模型（1.5b/3b）提取的技能描述可能比较简单。可以：
1. 用 `--force` 参数重新提取：`python "$env:USERPROFILE\.config\opencode\extract_skill.py" --force`
2. 手动编辑 `C:\OpenSpace\openspace\skills\<skill-name>\SKILL.md`
3. 条件允许时换更大的模型

### Q: 如何在新电脑上快速确认整个流程正常？
```powershell
# 1. 确认 git 用户信息
git config --global --list

# 2. 确认 SSH 连接 GitHub
ssh -T git@github.com -o StrictHostKeyChecking=no

# 3. 确认 Ollama 正在运行
ollama list

# 4. 检测最近 session 是否需要提取
python "$env:USERPROFILE\.config\opencode\extract_skill.py" --check-only

# 5. 查看后台日志
oclog
```

### Q: extract_skill.py 里的路径也是硬编码 Administrator 怎么办？
第八步拉取脚本后执行以下命令自动修复所有路径：
```powershell
$file = "$env:USERPROFILE\.config\opencode\extract_skill.py"
(Get-Content $file) -replace 'C:\\\\Users\\\\Administrator', $env:USERPROFILE.Replace('\','\\') | Set-Content $file -Encoding UTF8
```
