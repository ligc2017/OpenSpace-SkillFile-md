# OpenCode + OpenSpace 新机器部署指南

> 适用系统：Windows 11 AMD64  
> 目标：在新电脑上复现完整的 OpenCode + OpenSpace + AGENTS.md 自动同步 + Ollama 自动技能提取的工作环境

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

---

## 第一步：安装 OpenCode

```powershell
npm install -g opencode-ai
```

验证安装：

```powershell
opencode --version
```

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

**集显笔记本建议直接用 `3b`**：质量够用于技能提取，速度尚可接受（一次提取约 1-2 分钟）。

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

如果使用的不是 `14b`，需要修改脚本中的模型名称（后续步骤中会创建该文件）：

```python
# 找到这一行，改成你拉取的模型名
OLLAMA_MODEL = "qwen2.5-coder:3b"   # 集显笔记本用这个
# OLLAMA_MODEL = "qwen2.5-coder:14b"  # 独显台式机用这个
```

---

## 第五步：配置 opencode

创建全局配置文件 `C:\Users\Administrator\.config\opencode\opencode.json`：

```powershell
New-Item -ItemType Directory -Force -Path "C:\Users\Administrator\.config\opencode"
```

写入以下内容（新建或覆盖 `opencode.json`）：

```json
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
```

---

## 第六步：运行 oh-my-openagent 安装器

```powershell
npx oh-my-opencode install --no-tui --claude=no --openai=no --gemini=no --copilot=no --opencode-zen=no --opencode-go=no --zai-coding-plan=no
```

安装器会自动生成 `oh-my-opencode.json` 并更新 `opencode.json`。

然后按以下内容覆盖 `C:\Users\Administrator\.config\opencode\oh-my-opencode.json`，为每个 agent 分配最合适的免费模型：

```json
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/assets/oh-my-opencode.schema.json",
  "agents": {
    "hephaestus":     { "model": "opencode/big-pickle" },
    "oracle":         { "model": "opencode/minimax-m2.5-free" },
    "librarian":      { "model": "opencode/nemotron-3-super-free" },
    "explore":        { "model": "opencode/nemotron-3-super-free" },
    "multimodal-looker": { "model": "opencode/gpt-5-nano" },
    "prometheus":     { "model": "opencode/big-pickle" },
    "metis":          { "model": "opencode/big-pickle" },
    "momus":          { "model": "opencode/minimax-m2.5-free" },
    "atlas":          { "model": "opencode/minimax-m2.5-free" },
    "sisyphus-junior":{ "model": "opencode/minimax-m2.5-free" }
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
```

---

## 第七步：配置全局 AGENTS.md（从 GitHub 拉取，无需手写）

> AGENTS.md 存储在 GitHub 仓库 `ligc2017/OpenSpace-SkillFile-md`，新机器直接拉取即可，不需要手动写内容。
> 该步骤在第九步（配置 git 仓库）完成后自动完成。

---

## 第八步：生成 SSH 密钥并添加到 GitHub

### 8.1 生成密钥

在 PowerShell 中执行：

```powershell
Start-Process -NoNewWindow -Wait -FilePath "ssh-keygen" `
  -ArgumentList "-t", "ed25519", "-C", "opencode-agents", `
  "-f", "C:\Users\Administrator\.ssh\id_ed25519_github", "-q", "-N", '""'
```

### 8.2 配置 SSH（使用 443 端口，绕过防火墙）

新建或编辑 `C:\Users\Administrator\.ssh\config`：

```
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile C:/Users/Administrator/.ssh/id_ed25519_github
    IdentitiesOnly yes
```

### 8.3 查看公钥，添加到 GitHub

```powershell
cat C:\Users\Administrator\.ssh\id_ed25519_github.pub
```

复制输出的内容，然后：

1. 打开 https://github.com/settings/ssh/new
2. Title：`opencode-windows-agents`
3. Key type：`Authentication Key`
4. Key：粘贴上面复制的公钥
5. 点击 **Add SSH key**

### 8.4 验证连接

```powershell
ssh -T git@github.com -o StrictHostKeyChecking=no
```

看到 `Hi ligc2017! You've successfully authenticated` 即成功。

---

## 第九步（A）：初始化 AGENTS.md git 仓库

```powershell
$repoDir = "C:\Users\Administrator\.config\opencode"

# 初始化仓库
git -C $repoDir init

# 配置用户信息
git -C $repoDir config user.name "ligc2017"
git -C $repoDir config user.email "ligc2017@users.noreply.github.com"
```

覆盖 `.gitignore`，只追踪必要文件：

```
# 忽略所有文件
*

# 例外：追踪以下文件
!AGENTS.md
!CONTINUITY.md
!extract_skill.py
!auto-push-watcher.ps1
!opencode-launch.ps1
!pull-agents.ps1
!pull-skills.ps1
!sync-agents.ps1
!sync-skills.ps1
!.gitignore
```

```powershell
# 从 GitHub 拉取现有内容（含 AGENTS.md 和所有脚本）
git -C $repoDir remote add origin git@github.com:ligc2017/OpenSpace-SkillFile-md.git
git -C $repoDir fetch origin
git -C $repoDir branch -M main
git -C $repoDir reset --hard origin/main
```

> **注意**：`reset --hard` 会以远程为准覆盖本地。拉取完成后，所有脚本文件（extract_skill.py、opencode-launch.ps1 等）都会自动到位，无需手动创建。

---

## 第九步（B）：初始化 Skills 目录嵌套 git 仓库

> **背景**：OpenSpace 官方 `.gitignore` 屏蔽了 `openspace/skills/*` 目录，因此需要在 skills 目录内建立**独立的嵌套 git 仓库**，指向同一个 GitHub 远程仓库，分目录管理不同内容。

```powershell
$skillsDir = "C:\OpenSpace\openspace\skills"

# 初始化独立嵌套仓库
git -C $skillsDir init

# 配置用户信息
git -C $skillsDir config user.name "ligc2017"
git -C $skillsDir config user.email "ligc2017@users.noreply.github.com"

# 连接到同一个 GitHub 远程仓库
git -C $skillsDir remote add origin git@github.com:ligc2017/OpenSpace-SkillFile-md.git

# 拉取远程内容，允许不相关历史合并
git -C $skillsDir fetch origin
git -C $skillsDir branch -M main
git -C $skillsDir pull origin main --allow-unrelated-histories
```

> **注意**：`--allow-unrelated-histories` 是必须的，因为 AGENTS.md 仓库和 skills 仓库的历史是独立的。

验证 skills 仓库状态：

```powershell
git -C $skillsDir remote -v
git -C $skillsDir log --oneline -5
```

---

## 第十步：修改 extract_skill.py 中的模型（集显笔记本必做）

拉取完成后，`extract_skill.py` 默认使用 `qwen2.5-coder:14b`。
如果是集显笔记本，打开文件修改模型名：

```powershell
notepad "C:\Users\Administrator\.config\opencode\extract_skill.py"
```

找到并修改这一行：

```python
# 改成你已经拉取的模型
OLLAMA_MODEL = "qwen2.5-coder:3b"
```

---

## 第十一步：配置 PowerShell Profile

```powershell
# 确保 profile 目录存在
New-Item -ItemType Directory -Force -Path "C:\Users\Administrator\Documents\WindowsPowerShell"
```

新建 `C:\Users\Administrator\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`：

```powershell
# opencode launcher: auto-sync AGENTS.md + skill extraction on exit
function Invoke-OpenCode {
    & "C:\Users\Administrator\.config\opencode\opencode-launch.ps1" @args
}
Set-Alias -Name oc -Value Invoke-OpenCode

# Override bare 'opencode' command to also go through the launch wrapper
function opencode {
    & "C:\Users\Administrator\.config\opencode\opencode-launch.ps1" @args
}

# oclog - view opencode background task log
# Usage:
#   oclog        show last 30 lines
#   oclog -f     live tail (follow, Ctrl+C to stop)
#   oclog -n 50  show last 50 lines
function oclog {
    param(
        [switch]$f,
        [int]$n = 30
    )
    $log = "C:\Users\Administrator\.config\opencode\launch.log"
    if (-not (Test-Path $log)) {
        Write-Host "No log file yet: $log" -ForegroundColor Yellow
        return
    }
    if ($f) {
        Write-Host "Following $log (Ctrl+C to stop)..." -ForegroundColor Cyan
        Get-Content $log -Wait -Tail $n
    } else {
        Get-Content $log -Tail $n
    }
}
```

加载 profile：

```powershell
. $PROFILE
```

---

## 第十二步：创建 /sync-agents 命令（TUI 内手动同步）

```powershell
New-Item -ItemType Directory -Force -Path "C:\Users\Administrator\.config\opencode\commands"
```

新建 `C:\Users\Administrator\.config\opencode\commands\sync-agents.md`：

```markdown
---
description: Sync AGENTS.md to GitHub (check changes and push)
---
Please run the following shell command to check if AGENTS.md has changed and push to GitHub:

!`powershell -Command "& 'C:\Users\Administrator\.config\opencode\sync-agents.ps1' 2>&1"`

Report the sync result based on the output above.
```

---

## 第十三步：验证全部配置

```powershell
# 1. 测试 OpenSpace MCP
opencode mcp list

# 2. 测试 oh-my-openagent
oh-my-opencode doctor

# 3. 测试 Ollama
ollama list
ollama run qwen2.5-coder:3b "Write a hello world in Python" --verbose

# 4. 测试 extract_skill.py（检测模式，不调用 Ollama）
python "C:\Users\Administrator\.config\opencode\extract_skill.py" --check-only

# 5. 加载 profile 并验证命令
. $PROFILE
Get-Command opencode   # 应显示 Function
Get-Command oclog      # 应显示 Function
```

---

## 整体工作流说明

### 启动时（后台自动）
```
输入: opencode
  → 后台 pull 最新 AGENTS.md + Skills（不阻塞，立即进入界面）
  → 启动 auto-push-watcher 监听新 SKILL.md
```

### 使用中
```
正常使用 opencode...
如果 AI 写入了新 SKILL.md → watcher 自动 git push 到 GitHub
```

### 退出时（后台自动）
```
退出 opencode（Ctrl+Q）→ 立即回到终端
  后台异步执行：
  → extract_skill.py 调用 Ollama 分析本次对话
  → 如有新技能 → 写入 SKILL.md → push 到 GitHub
  → sync AGENTS.md（如有变更）
  → sync Skills（如有变更）
```

### 查看后台状态
```powershell
oclog        # 最近 30 行日志
oclog -f     # 实时跟踪（退出时观察 Ollama 提取进度）
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
| 手动推送 AGENTS.md | `powershell -File "C:\Users\Administrator\.config\opencode\sync-agents.ps1"` |
| 手动拉取 AGENTS.md | `powershell -File "C:\Users\Administrator\.config\opencode\pull-agents.ps1"` |
| 手动运行技能提取 | `python "C:\Users\Administrator\.config\opencode\extract_skill.py"` |
| 强制重新提取 | `python "C:\Users\Administrator\.config\opencode\extract_skill.py" --force` |

---

## 文件清单

部署完成后，以下文件应全部存在：

```
C:\Users\Administrator\
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
│   ├── launch.log              # 后台操作日志（运行时生成）
│   ├── extracted_sessions.json # 已提取的 session 记录（运行时生成）
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
| `C:\Users\Administrator\.config\opencode\` | AGENTS.md、脚本文件 |
| `C:\OpenSpace\openspace\skills\` | 所有 `*/SKILL.md` 技能文件 |

> 两个目录使用**同一个** GitHub 远程仓库，但独立的 git 历史，通过 `--allow-unrelated-histories` 合并。

---

## 常见问题

### Q: 集显笔记本上 Ollama 提取速度很慢怎么办？
退出 opencode 后提取在后台异步进行，不影响使用。可以用 `oclog -f` 观察进度。
如果觉得等不了，换 `1.5b` 模型速度翻倍，质量略降但对技能提取够用。

### Q: Ollama 提取出来的技能质量差怎么办？
小模型（1.5b/3b）提取的技能描述可能比较简单。可以：
1. 用 `--force` 参数重新提取：`python extract_skill.py --force`
2. 手动编辑 `C:\OpenSpace\openspace\skills\<skill-name>\SKILL.md`
3. 条件允许时换更大的模型

### Q: 如何查看哪些 session 已经被提取过？
```powershell
Get-Content "C:\Users\Administrator\.config\opencode\extracted_sessions.json" | ConvertFrom-Json | Format-Table
```

### Q: 如何在新电脑上快速确认整个流程正常？
```powershell
# 1. 检查 Ollama 是否在运行
ollama list

# 2. 检测最近 session 是否需要提取
python "C:\Users\Administrator\.config\opencode\extract_skill.py" --check-only

# 3. 查看最近日志
oclog
```
