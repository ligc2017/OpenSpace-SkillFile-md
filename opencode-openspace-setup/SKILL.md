---
name: opencode-openspace-setup
description: 在 Windows 11 上完整安装和配置 OpenCode + OpenSpace + oh-my-openagent，包括 MCP 连接、免费模型分配、全局 AGENTS.md 规则配置
tags: [opencode, openspace, setup, windows, mcp, oh-my-openagent]
---

# OpenCode + OpenSpace 集成配置技能

## 适用场景
在 Windows 11 AMD64 上从零开始搭建 OpenCode + OpenSpace AI 编程工作流。

## 技术栈
- opencode-ai (v1.4+)
- oh-my-openagent (v3.16+)
- OpenSpace MCP Server (Python)
- Node.js / npm

## 关键步骤

### 1. 安装依赖
```powershell
npm install -g opencode-ai
npm install -g oh-my-opencode
npm install -g oh-my-opencode-windows-x64 --force
git clone https://github.com/HKUDS/OpenSpace.git C:\OpenSpace
pip install -e C:\OpenSpace
```

### 2. opencode.json 配置
路径：`C:\Users\Administrator\.config\opencode\opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/qwen3.6-plus-free",
  "plugin": ["oh-my-openagent@latest"],
  "mcp": {
    "openspace": {
      "type": "local",
      "command": ["python", "-m", "openspace.mcp_server"],
      "environment": {
        "PYTHONPATH": "C:\\OpenSpace"
      }
    }
  }
}
```

### 3. 运行 oh-my-openagent 安装器（无付费订阅）
```powershell
npx oh-my-opencode install --no-tui --claude=no --openai=no --gemini=no --copilot=no --opencode-zen=no --opencode-go=no --zai-coding-plan=no
```

### 4. oh-my-opencode.json 模型分配（免费模型）
路径：`C:\Users\Administrator\.config\opencode\oh-my-opencode.json`

模型分配策略（按 agent 职责）：
- `opencode/big-pickle`：hephaestus, prometheus, metis + ultrabrain/deep 类别
- `opencode/minimax-m2.5-free`：oracle, momus, atlas, sisyphus-junior
- `opencode/nemotron-3-super-free`：librarian, explore + writing/unspecified-high
- `opencode/gpt-5-nano`：multimodal-looker + quick/visual/artistry

### 5. 验证
```powershell
opencode mcp list          # 应显示 openspace connected
oh-my-opencode doctor      # 应只有可选工具警告
```

## 注意事项
- 所有 `github-copilot/` 前缀模型需要 GitHub Copilot 订阅，无订阅时必须替换为 `opencode/` 前缀
- `oh-my-opencode-windows-x64` 平台包版本可能落后于主包，用 `--force` 安装后功能正常
- OpenSpace MCP 通过 `python -m openspace.mcp_server` 启动，需要设置 `PYTHONPATH`
