---
name: claude-code-setup
description: 在 Windows 11 上安装 Anthropic 官方终端版 AI 编程助手 Claude Code，包括安装、验证和首次配置
tags: [claude-code, anthropic, cli, windows, install]
---

# Claude Code 安装配置技能

## 适用场景
在 Windows 11 上安装 Anthropic 官方 CLI 工具 Claude Code（`claude` 命令），用于终端内直接与 Claude 交互和编程。

## 技术栈
- Node.js (v18+) / npm
- @anthropic-ai/claude-code (npm 包)

## 安装步骤

### 1. 前置要求
```powershell
node --version   # 需要 v18+
npm --version
```

### 2. 安装 Claude Code
```powershell
npm install -g @anthropic-ai/claude-code
```

### 3. 验证安装
```powershell
claude --version
```
成功输出类似：`2.1.101`

### 4. 首次使用
```powershell
claude   # 启动交互模式，按提示登录 Anthropic 账号
```

或者配置 API Key 方式（无账号时）：
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-xxxx"
claude "你好"
```

## 常用命令
```powershell
claude              # 启动交互模式
claude "问题"       # 直接提问
claude --help       # 查看帮助
```

## 注意事项
- Claude Code 需要 Anthropic 账号或 API Key，与 opencode（使用 GitHub Copilot 免费额度）不同
- 如果已有 opencode，两者可以并存，命令分别是 `claude` 和 `opencode`
- 安装后第一次运行会进行身份验证流程
