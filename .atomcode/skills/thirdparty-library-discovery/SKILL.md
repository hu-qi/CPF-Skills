---
name: thirdparty-library-discovery
description: 为鸿蒙三方库适配征文发现、筛选和排序候选三方库。适用于“我不知道适配哪个库”“帮我找尚未适配鸿蒙的库”“给我推荐若干 Flutter/RN/ArkTS 等适配选题”等任务；候选发现与官方适配必要性判断分离，优先复用对应社区官方 Skills。
---

# Third-party Library Discovery

## 目标

回答：**“我应该适配哪个三方库？”**

本 Skill 负责：

- 从指定技术生态发现候选库；
- 做价值/维护性初筛；
- 消费官方 Skill 技术结论；
- 执行活动 required 去重门禁；
- 对通过硬门槛的候选评分和排序。

本 Skill **不负责实际移植**，也不重复实现 CPF-Flutter、CPF-RN、CPF-ApplicationTPC 等社区已有的源码级能力。

## 输入

- `framework`：如 `flutter`、`react-native`、`arkts`、`cpp`、`kmp-cmp`、`cordova`、`ionic`、`cjmp`、`electron`。
- `topic`：可选能力方向，如图片、视频、数据库、蓝牙、文件、网络、安全。
- `count`：默认 `10`。
- `difficulty`：`easy | medium | hard | any`，默认 `any`。
- `freshness`：默认优先仍维护、近期仍有发布或提交活动的库。

框架入口、去重源和官方 Skill 路由读取：

```text
resources/frameworks.yaml
```

## 规范状态 token

每个候选只能使用以下状态之一：

```text
RECOMMENDED
NEEDS_OFFICIAL_CHECK
EXCLUDED_ALREADY_ADAPTED
EXCLUDED_NO_ADAPTATION_NEEDED
EXCLUDED_LOW_VALUE
EXCLUDED_UNVERIFIABLE
```

`status` 是机器接口，必须逐字输出，禁止翻译、缩写、别名或自造状态。

例如禁止：

```text
ADAPTED
UNVERIFIED
ADAPTATION_NOT_NEEDED
已适配
无需适配
```

解释放在 `reason`，不能改写 `status` token。

## Critical Constraints

1. 官方 Skill 负责技术结论，本项目 Skill 负责活动资格与排序。
2. 技术上“需要适配”不等于活动上“可重复适配”。
3. required 去重源未全部 `checked` 时，禁止 `RECOMMENDED`。
4. “未搜索到”不等于“不存在”。
5. 官方结论 `inconclusive` / `not_run` 不得擅自升级为确定事实。
6. **Flutter 的 `ohos-flutter-plugin-adaptation-necessity-check` 是按需源码级复核，不是每个候选推荐前的强制第二关。**
7. **当 `flutter-library-search=needs_adaptation` 已是明确官方业务结论，且 required 去重全部完成无命中时，`adaptation_necessity=not_run` 本身绝不能阻塞候选进入 `RECOMMENDED` 资格判断。**
8. 评分只用于排序，不能绕过硬门禁。

## Workflow

### 1. 解析框架

读取 `resources/frameworks.yaml`，确认：

- discovery source；
- required dedup sources；
- 官方 Skills 仓库；
- 当前是否已审计相关官方能力。

对于存在多个技术栈的 framework family，必须明确 variant；不要静默选择。

### 2. 发现候选

候选池目标至少：

```text
max(count * 3, 20)
```

优先：

- 常见业务能力；
- 有采用/热度证据；
- 当前仍维护；
- 容易构造 Demo；
- 有平台能力差异或原生实现迹象。

Flutter discovery 阶段优先识别直接 `flutter.plugin` 信号，不把“支持 Android/iOS”的标签直接等同于“存在原生插件实现”。

### 3. 初筛

至少检查：

- 原始包/仓库身份可验证；
- 维护状态；
- 采用/使用证据；
- 是否归档/失维/已被主流替代；
- 是否属于纯配置、模板、环境搭建类主题。

证据不足时不要编造下载量、Star、发布日期等事实。

### 4. 消费官方技术结论

Flutter 优先使用：

```text
flutter-library-search
oh​​os-flutter-plugin-adaptation-necessity-check
```

实际 Skill 名无隐藏字符：

```text
flutter-library-search
ohos-flutter-plugin-adaptation-necessity-check
```

其中：

- `flutter-library-search` 是第一层官方业务结论；
- necessity check 只在搜索结论不明确、需要源码级复核、或正式开工前需要更深入技术报告时执行。

官方 handoff 的完整说明位于：

```text
references/official-skill-handoff.md
```

但以下决策优先级是本 Skill 的**强制规则**，即使 reference 未被运行环境自动加载也必须遵守。

## Flutter Official Handoff Decision Matrix

输入中的 `library_search.result` 使用：

```text
adapted
needs_adaptation
no_adaptation_needed
inconclusive
not_run
```

`adaptation_necessity.result` 使用：

```text
needed
not_needed
inconclusive
not_run
```

`dedup_checks[].result` 使用：

```text
checked
partial
unavailable
```

按以下顺序判断，先命中的规则优先：

### Rule 1 — 已适配

```text
library_search.result == adapted
```

→ `EXCLUDED_ALREADY_ADAPTED`

### Rule 2 — 官方搜索明确无需适配

```text
library_search.result == no_adaptation_needed
```

→ `EXCLUDED_NO_ADAPTATION_NEEDED`

### Rule 3 — 源码级检查明确无需适配

```text
adaptation_necessity.result == not_needed
```

→ `EXCLUDED_NO_ADAPTATION_NEEDED`

### Rule 4 — required 去重未完成

任一：

```text
required == true
and result != checked
```

→ 不得 `RECOMMENDED`；候选仍有价值时为 `NEEDS_OFFICIAL_CHECK`

### Rule 5 — required 去重命中已有实现

任一 required 来源存在明确同库/等价实现 `matches`：

→ `EXCLUDED_ALREADY_ADAPTED`

### Rule 6 — 官方搜索已明确需要适配

同时满足：

```text
library_search.result == needs_adaptation
all required dedup result == checked
all required dedup matches == []
```

→ 候选**可以进入 `RECOMMENDED` 资格判断**。

此时：

```text
adaptation_necessity.result == not_run
```

**不阻塞、不降级，不得因此改成 `NEEDS_OFFICIAL_CHECK`。**

只有存在其他真实硬门槛（例如低价值、不可验证）才可排除或降级。

### Rule 7 — 源码级必要性检查明确需要适配

同时满足：

```text
adaptation_necessity.result == needed
all required dedup result == checked
all required dedup matches == []
library_search.result not in [adapted, no_adaptation_needed]
```

→ 候选可以进入 `RECOMMENDED` 资格判断。

### Rule 8 — 仍无明确技术结论

例如：

```text
library_search.result in [inconclusive, not_run]
adaptation_necessity.result in [inconclusive, not_run]
```

且没有更高优先级排除事实：

→ `NEEDS_OFFICIAL_CHECK`

### Rule 9 — 身份不可验证

原始包、仓库或关键候选身份本身无法验证：

→ `EXCLUDED_UNVERIFIABLE`

## 冲突处理

如果两个官方结论冲突：

- 不选更乐观结论；
- 活动已有适配事实优先排除；
- 其他冲突降级 `NEEDS_OFFICIAL_CHECK`；
- `reason` 保留冲突的原始结论。

例如：

```text
library_search = adapted
adaptation_necessity = needed
```

活动状态仍优先：`EXCLUDED_ALREADY_ADAPTED`。

## 其他框架

读取 `resources/frameworks.yaml` 的 `official_skills`。

- 已存在官方技术检查 Skill：优先调用/消费其结论；
- 没有确认能力：只执行当前可验证检查并说明边界；
- 不凭记忆创造 Skill 名称。

## 活动去重

必须逐项处理当前框架的 `dedup_sources`。

required source 的结果只有真正完整核查后才能标记为 `checked`。

名称匹配必须采用规范化后的包身份等价匹配，不做任意 substring 匹配，避免：

```text
file -> file_picker
image -> cached_network_image
```

这类误排除。

## 价值、难度与排序

只对通过硬性筛选的候选评分。

四个维度各 `0-5`：

- `ecosystem_value`
- `adaptation_necessity`
- `feasibility`
- `article_value`

综合分：

```text
score = ecosystem_value * 7
      + adaptation_necessity * 6
      + feasibility * 4
      + article_value * 3
```

满分 100。

难度：

```text
easy
medium
hard
```

必须附简短依据。

默认排序：

1. `RECOMMENDED`；
2. 综合分；
3. 用户指定 difficulty 匹配度；
4. 证据完整度；
5. 真机验证和文章实践路径清晰度。

## 输出

主表至少包含：

| 排名 | 库 | 方向 | 状态 | 难度 | 评分 | 推荐理由 | 关键证据 |
|---:|---|---|---|---|---:|---|---|

另列：

- 有代表性的排除项；
- `NEEDS_OFFICIAL_CHECK` 的待确认项；
- 最值得立即推进的 `1-3` 个候选。

待确认项必须说明：

- 需要执行哪个已确认官方 Skill；
- 哪个 required 去重源尚未完成；
- 什么事实补齐后才能升级。

## 证据规则

- 最新版本、维护状态、热度、是否已适配等时效性事实以当前 evidence 为准。
- 优先原始包页、原仓、官方社区仓等一手来源。
- “未搜索到”只能写“在已检查来源中未发现”。
- 官方 Skill 技术结论优先于启发式判断。
- 活动去重事实优先于通用技术判断。

## 红线

- 不把热门直接等同于值得适配。
- 不把 Android/iOS 目录直接等同于必须适配鸿蒙。
- 不把 `adaptation_necessity=not_run` 作为 `library_search=needs_adaptation` 的默认阻塞项。
- 不因搜索不到结果就断言不存在适配。
- 不绕过 required 去重来源。
- 不重复实现官方 Skill 的完整源码分析。
- 不开始实际移植；选定候选后转交官方适配能力或 `harmony-contribution-orchestrator`。
