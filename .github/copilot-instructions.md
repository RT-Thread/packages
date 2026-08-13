# GitHub Copilot Review Instructions for RT-Thread Packages / RT-Thread 软件包仓库 Copilot 评审指南

## Overview / 概述

RT-Thread Packages is a repository of package indexes. Each package entry is defined by a folder containing `Kconfig` and `package.json`. Reviewers must focus on metadata correctness, Kconfig consistency, and repository policies so packages can be discovered and fetched correctly by the RT-Thread tooling.

RT-Thread Packages 仓库用于保存软件包索引信息。每个软件包目录包含 `Kconfig` 与 `package.json`。评审时需重点关注元数据正确性、Kconfig 一致性以及仓库规范，确保包能被工具正确发现与下载。

**When reviewing PRs, you MUST check all items in the PR Review Checklist section and provide feedback according to the PR Review Instructions.**

**审查 PR 时，必须检查 PR 审查清单中的所有项目，并按 PR 审查指令提供反馈。**

## Language Requirements / 语言要求

Provide review feedback in **both English and Chinese**.

评审反馈必须**中英文双语**。

## Review Focus Areas / 审查重点领域

1. **Package Index Integrity / 软件包索引完整性**
   - Folder name matches `package.json` field `name` (case-sensitive) / 目录名与 `package.json` 的 `name` 一致（区分大小写）
   - Each package folder includes `Kconfig` and `package.json` / 每个包目录包含 `Kconfig` 与 `package.json`
   - Category `Kconfig` sources the package / 分类 `Kconfig` 中引用该包

2. **package.json Schema & Style / package.json 结构与风格**
   - 4-space indent, UTF-8, no trailing commas / 4 空格缩进、UTF-8、无尾随逗号
   - Required fields: `name`, `description`, `author`, `license`, `site` / 必需字段：`name`、`description`、`author`、`license`、`site`
   - `site` entries include `version`, `URL`, `filename`, `VER_SHA` / `site` 中包含 `version`、`URL`、`filename`、`VER_SHA`
   - Keywords concise, lowercase naming preferred / 关键词简洁，名称尽量小写

3. **Versioning & Source URLs / 版本与源码链接**
   - Provide at least one fixed version plus `latest` when supported / 至少提供一个固定版本，支持时再提供 `latest`
   - Prefer immutable tags/commits for releases / 优先使用不可变标签或提交
   - `URL` must use HTTPS on GitHub or Gitee / `URL` 必须使用 GitHub 或 Gitee 的 HTTPS 地址
   - `VER_SHA` resolves to an existing branch/commit / `VER_SHA` 指向有效分支/提交
   - Upstream repo name should not start with digits / 上游仓库名避免以数字开头
   - Upstream repo must not use submodules / 上游仓库禁止使用子模块

4. **Kconfig Consistency / Kconfig 一致性**
   - Main option `PKG_USING_<PACKAGE>` / 主选项 `PKG_USING_<PACKAGE>`
   - Feature options prefix `<PACKAGE>_` / 功能选项前缀 `<PACKAGE>_`
   - Preserve existing ordering and generated comments / 保持现有顺序与生成的注释

5. **Repository Hygiene / 仓库规范**
   - No binary blobs in git / 禁止提交二进制文件
   - Shared assets only in `figures/` / 共享资源仅放在 `figures/`

6. **Validation & Tests / 校验与测试**
   - `python ci.py` should pass / `python ci.py` 需通过
   - JSON syntax check recommended: `python -m json.tool path/to/package.json` / 建议进行 JSON 语法检查
   - If applicable, verify in Env: menuconfig -> `pkgs --update` -> build with `scons` / 条件允许时在 Env 中验证

## PR Review Checklist / PR 审查清单

- PR title follows repository conventions and matches modified package(s) / PR 标题符合仓库规范并匹配修改包
- PR description includes What/Why/How and related files / PR 描述包含 What/Why/How 及相关文件
- Changes focus on a single package or a tightly related set / 变更聚焦于单一包或紧密相关的集合
- `package.json` field correctness, style, and URL policy / `package.json` 字段正确、格式规范、URL 合规
- Kconfig entries are consistent with package name and location / Kconfig 与包名/目录一致
- Version entries are valid and include fixed version(s) / 版本条目有效且包含固定版本
- Repository hygiene rules are respected / 仓库规范得到遵守
- CI/validation commands are run or explicitly acknowledged / CI/校验已运行或明确说明

## PR Review Instructions / PR 审查指令

**When reviewing a PR, you MUST systematically check the following items and provide feedback for any violations.**

**审查 PR 时，必须系统性检查以下项目，对违规项提供反馈。**

### Step 1: PR Title Check / 步骤 1：PR 标题检查

- Title should be specific and include package scope / 标题应具体并包含包范围
- Acceptable formats: / 可接受格式：
  - `update(<package>): bump to vX.Y.Z`
  - `add(<package>): initial import`
  - `[category/package] ...`
- Title scope must match modified files / 标题范围需匹配修改文件
- Avoid vague titles like "update package" / 避免“update package”等模糊标题

**Feedback template / 反馈模板**:
```
🟡 [PR Title/PR 标题]: Missing or unclear scope / 缺少或不清晰的范围

English: PR title should include package scope and describe the change.
Current title: `{current_title}`.
Suggested: `{suggested_title}`.

中文：PR 标题应包含包范围并描述变更。
当前标题：`{current_title}`。
建议：`{suggested_title}`。
```

### Step 2: PR Description Check / 步骤 2：PR 描述检查

- Must include What/Why/How and ideally modified files / 必须包含 What/Why/How，最好包含修改文件列表
- Should reference upstream release/tag/commit when updating / 更新时应引用上游 release/tag/commit

**Feedback template / 反馈模板**:
```
🟢 [PR Description/PR 描述]: Missing or insufficient description / 缺少或不充分的描述

English: Please add What/Why/How and list modified files; include upstream release/tag when applicable.

中文：请补充 What/Why/How，并列出修改文件；更新时请注明上游 release/tag。
```

### Step 3: PR File Modification Check / 步骤 3：PR 修改文件检查

- Ensure all changes are for one package or a tight set / 确保变更集中于单一包或紧密相关的集合
- If multiple unrelated packages are modified, request split / 若涉及多个无关包，建议拆分 PR

**Feedback template / 反馈模板**:
```
🟡 [PR Structure/PR 结构]: Multiple unrelated packages in one PR / 一个 PR 中包含多个无关包

English: Please split into separate PRs, one per package or tightly related group.
中文：请拆分为多个 PR，每个 PR 聚焦一个包或相关集合。
```

### Step 4: package.json Validation / 步骤 4：package.json 校验

- Verify required fields and formatting / 检查必需字段与格式
- Confirm `name` matches folder / 确认 `name` 与目录名一致
- Verify all `URL` entries use HTTPS on GitHub or Gitee / 确认所有 `URL` 条目使用 GitHub 或 Gitee HTTPS 地址
- Check `VER_SHA` points to existing tag/commit / 检查 `VER_SHA` 指向有效 tag/commit
- Ensure fixed version(s) plus `latest` where supported / 确保包含固定版本与 `latest`

**Feedback template / 反馈模板**:
```
🟡 [package.json/包信息]: Invalid field or policy violation / 字段无效或违反规范

English: `{field}` is missing/invalid or violates policy. Please update the package metadata accordingly.
中文：`{field}` 缺失/无效或违反规范，请修正包元数据。
```

### Step 5: Kconfig Consistency / 步骤 5：Kconfig 一致性检查

- `PKG_USING_<PACKAGE>` and option prefixes / `PKG_USING_<PACKAGE>` 与选项前缀
- Package is sourced in category `Kconfig` / 分类 `Kconfig` 已引用该包

**Feedback template / 反馈模板**:
```
🟡 [Kconfig/Kconfig]: Inconsistent option or missing source / 选项不一致或缺少引用

English: Please align Kconfig symbols and ensure the package is sourced in the category Kconfig.
中文：请对齐 Kconfig 符号并确保分类 Kconfig 引用该包。
```

### Step 6: Policy & Hygiene / 步骤 6：规范与整洁性检查

- No binary blobs / 无二进制文件
- No unsupported or non-HTTPS repository URLs / 不允许不支持的主机或非 HTTPS 仓库地址
- No submodules / 无子模块

**Feedback template / 反馈模板**:
```
🟡 [Policy/规范]: Repository policy violation / 违反仓库规范

English: This PR violates repository policy: {policy}. Please adjust accordingly.
中文：此 PR 违反仓库规范：{policy}。请按要求修改。
```

## Review Comment Format / 审查评论格式

Use the following format for review comments:

审查评论使用以下格式：

```
[Category/类别]: Brief description / 简要描述

English: Detailed explanation of the issue and suggested improvement.
中文：问题的详细说明和改进建议。

Example/示例:
```json
{
    "name": "pahomqtt"
}
```
```

**For PR-related issues, use severity level 🟡 Minor or 🟢 Suggestion.**

**PR 相关问题使用严重程度 🟡 Minor 或 🟢 Suggestion。**

## Severity Levels / 严重程度级别

- **🔴 Critical/严重**: Breaks tooling or makes packages unusable / 破坏工具链或导致包不可用
- **🟠 Major/主要**: Likely to cause download/build failures / 可能导致下载或构建失败
- **🟡 Minor/次要**: Style or minor metadata issues / 风格或次要元数据问题
- **🟢 Suggestion/建议**: Best practices or optional improvements / 最佳实践或可选改进
