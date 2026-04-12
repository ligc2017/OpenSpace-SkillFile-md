# OpenCode 全局行为规则

## OpenSpace 技能学习规则

### 新项目初始化
每当在一个新项目目录中开始工作时（即当前目录没有 AGENTS.md 文件），必须：
1. 使用 `openspace` 的 `search_skills` 工具，搜索是否有与当前项目类型相关的已有技能
2. 将搜索到的相关技能告知用户
3. 创建项目的 AGENTS.md 文件，写入项目基本信息和技能使用规则

### 任务开始前
接到任何编码任务时，先用 `openspace` 的 `search_skills` 工具搜索是否有现成技能可用，
如果找到相关技能，优先复用，并告知用户"已找到相关技能：XXX"。

### 任务执行规则（强制）

**每次完成以下类型的任务后，必须立即调用 `openspace_execute_task` 工具将过程记录为可复用技能，不得跳过：**
- 实现一个新的功能模块
- 解决一个 bug
- 完成一次重构
- 建立项目脚手架或初始化配置
- 实现一个设计模式或架构方案
- 完成任何工具/环境的安装与配置

**技能必须保存到：`C:\OpenSpace\openspace\skills\`**

调用方式：
```
openspace_execute_task(
  task="[任务类型]：[具体描述]，技术栈：[xxx]，关键要点：[xxx]",
  workspace_dir="C:\\OpenSpace\\openspace\\skills"
)
```

### 技能记录格式
使用 execute_task 记录技能时，任务描述应包含：
- 任务类型（如：FastAPI路由实现、React组件封装等）
- 使用的技术栈
- 关键实现要点
- 遇到的坑和解决方案

### 技能文件说明
- 技能以 SKILL.md 形式存储在 `C:\OpenSpace\openspace\skills\<skill-name>\SKILL.md`
- 每次退出 opencode 时，技能文件会自动通过 git 同步到 GitHub
- GitHub 仓库：`git@github.com:ligc2017/OpenSpace-SkillFile-md.git`
- **自动提取**：opencode 退出后，`extract_skill.py` 会自动用本地 Ollama 分析最近 session 并提取技能

## 对话续作规则

### 每次对话结束前（强制）
在完成用户请求后，如果工作**未全部完成**，必须将剩余任务写入 `CONTINUITY.md`：

```
C:\Users\Administrator\.config\opencode\CONTINUITY.md
```

写入格式：
```markdown
## 待续任务
- [ ] 任务描述1
- [ ] 任务描述2

## 上下文摘要
- 项目路径：...
- 关键文件：...
- 当前状态：...
```

### 每次对话开始时（强制）
1. 读取 `C:\Users\Administrator\.config\opencode\CONTINUITY.md`
2. 如果有未完成任务（`- [ ]`），**立即开始执行**，无需等用户再次说明
3. 完成后将对应任务标记为 `- [x]`，并更新文件

### 自动技能提取说明
- `opencode-launch.ps1` 启动时会开启 FileSystemWatcher 后台进程监听 skills 目录
- opencode 退出后自动调用 `extract_skill.py` 分析最近对话，用 Ollama 提取可复用技能
- 新写入的 SKILL.md 会被 watcher 自动 `git push` 到 GitHub
- 提取脚本路径：`C:\Users\Administrator\.config\opencode\extract_skill.py`
- 使用模型：`qwen2.5-coder:14b`（本地 Ollama）

When making function calls using tools that accept array or object parameters ensure those are structured using JSON. For example:
<example_complex_tool>
<parameter>[{"color": "orange", "options": {"option_key_1": true, "option_key_2": "value"}}, {"color": "purple", "options": {"option_key_1": true, "option_key_2": "value"}}]</parameter>
</example_complex_tool>
