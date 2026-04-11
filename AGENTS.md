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

### 任务执行规则
每次完成以下类型的任务后，必须调用 `openspace` 的 `execute_task` 工具将过程记录为可复用技能：
- 实现一个新的功能模块
- 解决一个 bug
- 完成一次重构
- 建立项目脚手架或初始化配置
- 实现一个设计模式或架构方案

### 技能记录格式
使用 execute_task 记录技能时，任务描述应包含：
- 任务类型（如：FastAPI路由实现、React组件封装等）
- 使用的技术栈
- 关键实现要点

When making function calls using tools that accept array or object parameters ensure those are structured using JSON. For example:
<example_complex_tool>
<parameter>[{"color": "orange", "options": {"option_key_1": true, "option_key_2": "value"}}, {"color": "purple", "options": {"option_key_1": true, "option_key_2": "value"}}]</parameter>
</example_complex_tool>
