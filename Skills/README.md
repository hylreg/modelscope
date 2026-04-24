## Skills 目录说明

本目录用于存放可复用的 **Cursor Agent Skills**（技能）。每个 skill 是一个文件夹，文件夹内必须包含 `SKILL.md`（带 YAML frontmatter），结构如下：

```text
Skills/
  skill-name/
    SKILL.md
```

## 当前可用 Skills
- **`skill-template`**：Skill 语法/结构模板（可复制改名快速新建）。见 `skill-template/SKILL.md`。
- **`self-intro`**：中文求职/面试自我介绍（默认约 60 秒），支持岗位对齐、项目量化、30 秒/2 分钟/偏技术版变体。见 `self-intro/SKILL.md`。
- **`resume-generator`**：中文简历生成/润色（ATS 友好、默认一页 Markdown），支持根据 JD 对齐关键词、把经历改写为量化要点，并可选投递版/面试版。见 `resume-generator/SKILL.md`。

## 使用方式（约定）

1. **挑一个目标**：例如“写自我介绍”“根据 JD 生成简历”。
2. **提供最关键输入**：
   - `self-intro`：姓名/称呼、目标岗位、年限、技术栈、1-2 个项目亮点（尽量量化）、优势/价值观/诉求。
   - `resume-generator`：目标岗位 JD（或关键词）、基本信息、技能栈、工作/项目经历（含指标）。
3. **触发提示词**：直接说“用 `self-intro` ……”或“用 `resume-generator` ……”即可。

如果你后续新增 skill，建议：

- **命名**：小写 + 连字符（例如 `paper-summary`）
- **描述**：写清楚“做什么 + 什么时候用”（便于被自动发现）
- **长度**：`SKILL.md` 尽量保持精简，详细内容可拆到同目录的 `reference.md` / `examples.md`
