---
name: harmony-article-check
description: 检查鸿蒙三方库适配征文草稿是否满足当前活动规则。适用于“帮我检查这篇征文”“发布前审稿”“检查标题、字数、真机截图、社区引导、AtomGit/GitCode、CSDN 质量分”等任务。优先执行确定性检查，并把无法自动证明的原创性、重复率、AI 占比、CSDN 分数和真机真实性明确标记为人工或外部证据项。
---

# Harmony Article Check

## 目标

回答：**“这篇文章现在是否具备发布资格，还缺什么？”**

本 Skill 只负责文章与发布合规检查，不伪造技术经历，不把发布后阅读量作为发布前门禁。

## 单一事实源

活动规则：

```text
resources/article-rules.yaml
```

框架、社区名、组织链接：

```text
resources/frameworks.yaml
```

确定性实现：

```text
scripts/article/check_article_static.py
scripts/article/build_compliance_report.py
```

配置与 Skill 冲突时，以当前配置和确定性 report 为准，并报告冲突。

## Closed-world 规则

发布资格是 **closed-world** 判定：

- 只能使用 `resources/article-rules.yaml` 中存在的活动规则、Validation Gate，以及明确声明的 checker 辅助项；
- **不得自行增加“最终人工审阅”“编辑复核”“再确认一次”等额外发布门禁**；
- 如果所有配置中的发布前 hard/manual/external 项都已经有足够证据通过，则必须使用 `READY_TO_PUBLISH`；
- 不能因为“谨慎起见”把已经全部确认的 case 降成 `MANUAL_REVIEW_REQUIRED`；
- `MANUAL_REVIEW_REQUIRED` 只用于配置中真实存在、且当前仍未完成的人工确认项。

这条规则是机器契约的一部分，不是建议。

## Fixture 与真实发布资格隔离

测试夹具使用：

```text
fixture_only = true
fixture://...
```

它只能用于回归测试，不是现实活动证据。

确定性 compliance report 会同时输出：

```text
fixture_only = true | false
publishable = true | false
```

规则：

- 真实输入 `fixture_only=false` 且全部发布前规则通过时，才允许 `publishable=true`；
- fixture 即使覆盖到 `status=READY_TO_PUBLISH` 分支，也必须 `publishable=false`；
- 真实 Validation 或人工确认中出现 `fixture://` 引用属于无效输入，应拒绝而不是继续判定；
- 不得通过删除 fixture 标签，把测试数据描述成真实可发布文章。

因此 **`status=READY_TO_PUBLISH` 不能单独等价为“现实文章可以发布”**；需要同时确认：

```text
publishable = true
```

## 前置条件

完整检查需要：

1. 文章 Markdown/正文；
2. 明确 framework variant，例如 `flutter`、`react-native`、`arkts`、`cpp`；
3. Validation Gate artifact；
4. 活动要求的实际外部指标；
5. 配置中规定的人工确认/证据。

只给正文时可以运行静态检查，但不能声称完整合规已经通过。

## 单项状态 token

只能使用：

```text
PASS
FAIL
MANUAL_REQUIRED
EXTERNAL_REQUIRED
POST_PUBLISH
NOT_APPLICABLE
```

- `PASS`：已有足够证据。
- `FAIL`：明确违反规则。
- `MANUAL_REQUIRED`：配置要求人工确认，但当前没有确认/证据。
- `EXTERNAL_REQUIRED`：配置要求外部平台/工具结果，但当前未提供。
- `POST_PUBLISH`：发布后指标，不阻塞发布前状态。
- `NOT_APPLICABLE`：当前场景不适用，必须说明原因。

不得把缺失项乐观改成 `PASS`，也不得给已完成项追加新的人工门禁。

## 顶层状态

只能使用：

```text
BLOCKED
MANUAL_REVIEW_REQUIRED
READY_TO_PUBLISH
```

### `BLOCKED`

任一成立：

- 存在发布前 hard rule `FAIL`；
- 存在未完成的必需 `EXTERNAL_REQUIRED`；
- Validation Gate 不是 `ARTICLE_PREP/PROCEED`。

### `MANUAL_REVIEW_REQUIRED`

同时满足：

- 没有 `FAIL`；
- 没有 `EXTERNAL_REQUIRED`；
- Validation Gate 已通过；
- **至少一个配置中真实存在的人工规则仍为 `MANUAL_REQUIRED`**。

### `READY_TO_PUBLISH`

同时满足：

- Validation Gate = `ARTICLE_PREP/PROCEED`；
- 所有发布前 hard/static rule 通过；
- 所有必需 external rule 已提供实际结果且通过；
- 所有配置中的 manual rule 已确认通过或明确 `NOT_APPLICABLE`；
- 不存在 `FAIL`、`EXTERNAL_REQUIRED`、`MANUAL_REQUIRED`。

此时即使：

```text
readership < 1000
```

仍然必须是 `READY_TO_PUBLISH`，因为 readership 是 `POST_PUBLISH`。

对于真实文章，最终可发布结论还必须满足：

```text
fixture_only = false
publishable = true
```

## Workflow

### 1. 确认 framework variant

从 `resources/frameworks.yaml` 解析。

ApplicationTPC 必须明确 `arkts` 或 `cpp`，不能用模糊 `applicationtpc` 自动选技术栈。

### 2. 静态检查

优先执行：

```text
scripts/article/check_article_static.py
```

当前确定性检查：

- H1 标题包含当前框架/技术栈；
- 去除 fenced/inline code 后中文字符 `>= 800`；
- 不出现 `GitCode` 品牌/链接；
- 开头包含规范社区引导；
- 结尾再次包含规范社区引导；
- 图片引用存在性仅作为 INFO。

`static_status=PASS` 只代表这些自动规则通过，不代表完整合规。

### 3. Validation Gate

只有：

```text
phase = ARTICLE_PREP
decision = PROCEED
```

才把以下技术证据视为通过：

- implementation
- build
- demo
- tests
- HarmonyOS/OpenHarmony physical device run
- screenshots

文章里出现图片不能替代 Validation Gate 的真机/截图真实性。

### 4. 外部指标

#### 重复率

```text
duplication_rate_percent <= 30
```

无可信结果 → `EXTERNAL_REQUIRED`。

#### CSDN 质量分

```text
csdn_quality_score >= 80
```

无实际检查结果 → `EXTERNAL_REQUIRED`。

不得预测这两个值。

### 5. 人工确认

人工项只来自 `resources/article-rules.yaml`，例如：

- 原创/无抄袭；
- AI 未生成全部或大部分内容；
- 开发历史、问题、修复来自真实记录；
- 实践性/指导性/事实性；
- 版本策略或品牌使用等当前配置要求人工确认的事项。

无确认 → `MANUAL_REQUIRED`。
已有明确确认/可审计证据 → `PASS`。
**不得在这些规则之外再增加一个笼统“最终人工复核”。**

### 6. 品牌与社区

最终文章：

- 托管平台品牌使用 `AtomGit` 和 `atomgit.com`；
- 禁止 `GitCode` 品牌和链接；
- 开头/结尾社区引导模板：

```text
欢迎加入{community.name}：【{community.organization}】
```

社区事实从 `resources/frameworks.yaml` 读取，不硬编码。

### 7. 发布后指标

```text
readership >= 1000
```

永远标记为：

```text
POST_PUBLISH
```

未达到目标不能进入 `blocking_rules`，也不能把 `READY_TO_PUBLISH` 降级。

## 完整 Compliance Report

当已有 static report、Validation Gate、external metrics 和 manual confirmations 时，优先运行：

```text
scripts/article/build_compliance_report.py
```

确定性 report 的顶层 `status`、`fixture_only`、`publishable` 是最终机器判定依据。模型负责解释结果、给修复建议，不得覆盖这些字段。

## 输出契约

默认输出简洁结论 + 机器结构：

```json
{
  "schema_version": 1,
  "fixture_only": false,
  "publishable": false,
  "framework": "flutter",
  "status": "BLOCKED | MANUAL_REVIEW_REQUIRED | READY_TO_PUBLISH",
  "blocking_rules": [],
  "manual_rules": [],
  "external_rules": [],
  "post_publish_rules": ["readership"],
  "checks": [],
  "next_actions": []
}
```

要求：

- rule id 来自 `resources/article-rules.yaml`，或明确为 checker 辅助项；
- `FAIL` 指出修复方式；
- `EXTERNAL_REQUIRED` 说明需要哪个真实外部结果；
- `MANUAL_REQUIRED` 说明需要哪个配置中的人工确认；
- `POST_PUBLISH` 不进入 `blocking_rules`；
- 不创建配置外的新 mandatory rule；
- fixture report 不得解释为现实发布资格；
- 对真实文章说“可以发布”时必须有 `publishable=true`。

## 与 Writing Skill 的边界

文本可修复问题可以交给：

```text
harmony-article-writing
```

修改后必须重新运行 article check。Writing Skill 不能自行宣布合规。

## 红线

- 不预测 CSDN 分数。
- 不预测重复率。
- 不自动宣称原创或 AI 占比合规。
- 不把图片存在当成真机运行成功。
- 不把模拟器结果当成真机证据。
- 不把 `static_status=PASS` 当成完整发布合规。
- 不因 readership 未到 1000 阻塞发布前状态。
- 不允许最终文章出现 `GitCode` 品牌或链接。
- **不发明 `article-rules.yaml` 之外的额外发布门禁。**
- **不把 fixture 的 `READY_TO_PUBLISH` 描述成现实 `publishable=true`。**
