---
name: harmony-article-check
description: 检查鸿蒙三方库适配征文草稿是否满足当前活动规则。适用于“帮我检查这篇征文”“发布前审稿”“检查标题、字数、真机截图、社区引导、AtomGit/GitCode、CSDN 质量分”等任务。优先执行确定性检查，并把无法自动证明的原创性、重复率、AI 占比、CSDN 分数和真机真实性明确标记为人工或外部证据项。
---

# Harmony Article Check

## 目标

回答：**“这篇文章现在是否具备发布资格，还缺什么？”**

本 Skill 只负责文章与发布合规检查，不负责伪造技术经历，也不把发布后阅读量作为发布前内容门禁。

## 单一事实源

活动规则必须读取：

```text
resources/article-rules.yaml
```

框架、社区名称和组织链接必须读取：

```text
resources/frameworks.yaml
```

不要把易变化规则复制成另一套隐藏规则；配置与 Skill 冲突时，以当前配置为准，并报告冲突。

## 前置条件

完整的发布前检查至少需要：

1. 文章 Markdown/正文；
2. 明确框架/技术栈 variant，例如 `flutter`、`react-native`、`arkts`、`cpp`；
3. Validation Gate 结果，证明真实技术证据已经允许进入 `ARTICLE_PREP`；
4. 如活动要求外部指标，则提供对应结果，例如重复率、CSDN 质量分；
5. 原创性、AI 使用比例等无法自动证明的事项，需要作者声明或可审计证据。

如果只给文章正文，也可以先运行静态检查，但不得宣称“完整合规已通过”。

## 检查结果 token

单项规则只使用：

```text
PASS
FAIL
MANUAL_REQUIRED
EXTERNAL_REQUIRED
POST_PUBLISH
NOT_APPLICABLE
```

含义：

- `PASS`：当前证据足以证明通过；
- `FAIL`：当前事实明确违反硬规则；
- `MANUAL_REQUIRED`：机器/模型不能可靠证明，需要人工确认或作者声明；
- `EXTERNAL_REQUIRED`：需要外部平台/工具结果，例如重复率、CSDN 质量分；
- `POST_PUBLISH`：发布后指标，不阻塞发布前内容检查；
- `NOT_APPLICABLE`：规则在当前场景不适用，必须说明原因。

禁止把 `MANUAL_REQUIRED` 或 `EXTERNAL_REQUIRED` 乐观改写成 `PASS`。

## 总体状态

顶层 `status` 使用：

```text
BLOCKED
MANUAL_REVIEW_REQUIRED
READY_TO_PUBLISH
```

### `BLOCKED`

满足任一条件：

- 存在硬规则 `FAIL`；
- 必需的 `EXTERNAL_REQUIRED` 结果尚未提供；
- Validation Gate 未达到 `ARTICLE_PREP/PROCEED`。

### `MANUAL_REVIEW_REQUIRED`

确定性规则和必需外部指标均通过，但仍有原创性、AI 占比、事实真实性等人工确认项。

### `READY_TO_PUBLISH`

只有所有发布前硬规则都已有足够证据通过，且不存在未完成 `MANUAL_REQUIRED` / `EXTERNAL_REQUIRED` 项时才能使用。

阅读量等 `POST_PUBLISH` 指标不阻塞该状态。

## Workflow

### 1. 确认框架 variant

先用 `resources/frameworks.yaml` 解析 framework。

对于 ApplicationTPC，不能使用模糊的 `applicationtpc` 自动选择技术栈；必须明确 `arkts` 或 `cpp`。

### 2. 执行确定性静态检查

优先运行：

```text
scripts/article/check_article_static.py
```

当前静态检查包括：

- Markdown H1 标题是否明确包含当前框架/技术栈；
- 去除 fenced/inline code 后的中文字符数是否 `>= 800`；
- 是否出现活动禁止的 `GitCode` 品牌/链接；
- 文章开头是否包含规范社区引导语；
- 文章结尾是否再次包含规范社区引导语；
- 是否检测到图片引用（仅 INFO，不等同于真机截图真实性）。

静态 checker 的 `static_status=PASS` **只表示这些可自动检查项通过**，绝不等于完整文章合规通过。

### 3. 验证真实技术证据

完整发布前检查必须读取 Validation Gate artifact。

只有：

```text
phase = ARTICLE_PREP
decision = PROCEED
```

才可以把以下技术证据视为已通过门禁：

- 真实实现；
- 构建；
- Demo；
- 测试；
- HarmonyOS/OpenHarmony 实体设备运行；
- 成功运行截图。

仅在文章中出现一张图片，不能替代 Validation Gate 的截图/真机证据。

### 4. 检查外部指标

#### 重复率

规则：

```text
duplication_rate_percent <= 30
```

如果没有可信的重复率结果：

```text
status = EXTERNAL_REQUIRED
```

不得由模型根据文风猜测重复率。

#### CSDN 质量分

规则：

```text
csdn_quality_score >= 80
```

检查入口由 `resources/article-rules.yaml` 提供。

没有实际 CSDN 检查结果时使用 `EXTERNAL_REQUIRED`，不得预测分数。

### 5. 检查人工确认项

以下事项不能仅凭语言模型自动证明：

- 原创、无抄袭；
- AI 未生成文章全部或大部分内容；
- 故障、失败尝试、修复过程均来自真实开发记录；
- 实践性/指导性/事实性是否足够到达活动预期。

没有作者声明或可审计证据时使用：

```text
MANUAL_REQUIRED
```

不要为了给出“全绿”报告而自行通过。

### 6. 品牌与社区规则

最终文章中：

- 涉及代码托管平台时使用 `AtomGit` 品牌和 `atomgit.com` 链接；
- 禁止 `GitCode` 品牌和链接；
- 开头、结尾均使用当前 framework community 生成的规范引导语：

```text
欢迎加入{community.name}：【{community.organization}】
```

社区名和链接必须实时来自 `resources/frameworks.yaml`，不要硬编码到文章 Skill。

### 7. 发布后指标

阅读量目标：

```text
readership >= 1000
```

它属于：

```text
POST_PUBLISH
```

文章尚未发布或刚发布时不能因为阅读量不足，把发布前文章检查判为失败。

## 输出契约

输出先给简洁结论，再给机器可读结构：

```json
{
  "schema_version": 1,
  "framework": "flutter",
  "status": "BLOCKED | MANUAL_REVIEW_REQUIRED | READY_TO_PUBLISH",
  "blocking_rules": [],
  "manual_rules": [],
  "external_rules": [],
  "post_publish_rules": ["readership"],
  "checks": [
    {
      "id": "minimum-chinese-characters",
      "status": "PASS",
      "evidence": ["..."],
      "reason": "..."
    }
  ],
  "next_actions": []
}
```

要求：

- `id` 必须来自 `resources/article-rules.yaml`，或明确标记为 checker 的辅助信息项；
- `FAIL` 必须指出如何修复；
- `EXTERNAL_REQUIRED` 必须说明需要哪个实际外部结果；
- `MANUAL_REQUIRED` 必须说明由谁/依据什么确认；
- 不把 `POST_PUBLISH` 放入 `blocking_rules`。

## 与写作 Skill 的边界

如果发现可直接修复的文章文本问题，而仓库存在 `harmony-article-writing`：

- 可以把问题清单交给 writing Skill；
- 修改后必须重新执行本 Skill；
- writing Skill 不能直接声明自己的修改已经合规。

如果 writing Skill 尚不存在，就输出修订建议，不伪造路由。

## 红线

- 不预测 CSDN 质量分。
- 不预测重复率。
- 不自动宣称文章原创。
- 不自动宣称 AI 占比合规。
- 不把图片存在当成真机运行成功。
- 不把模拟器结果当成真机证据。
- 不把 `static_status=PASS` 当成完整发布合规。
- 不因发布后阅读量尚未达到 1000 而阻塞发布前检查。
- 不允许最终文章出现 `GitCode` 品牌或链接。
