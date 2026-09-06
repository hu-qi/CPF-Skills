---
name: harmony-contribution-orchestrator
description: 编排鸿蒙三方库适配征文全流程的阶段与门禁。适用于“这个候选下一步做什么”“开始适配前帮我确认资格”“根据 qualification 继续推进”“把选库、适配、验证、写作串起来”等任务。总控只消费标准化资格与阶段证据并路由官方 Skills，不重复实现框架社区已有的适配逻辑。
---

# Harmony Contribution Orchestrator

## 目标

回答一个问题：**“基于当前已验证状态，下一步允许做什么？”**

本 Skill 是流程编排层。它负责：

- 读取候选的标准化 qualification；
- 执行活动资格和阶段门禁；
- 决定继续、阻塞或停止；
- 路由到框架官方 Skill、验证阶段、文章阶段；
- 保留事实、证据、待确认项和阶段产物。

本 Skill **不负责**：

- 自己重新实现三方库搜索；
- 自己重复做官方源码适配分析；
- 绕过 qualification 直接开始移植；
- 在缺少真实开发证据时编造适配过程或文章素材。

## 单一事实入口

开始“是否允许适配”的判断时，以标准化 qualification artifact 为唯一资格输入。

Flutter 当前 qualification 结构由仓库内确定性构建器生成，核心字段至少包括：

```json
{
  "framework": "flutter",
  "candidate": "package_name",
  "qualification": {
    "status": "RECOMMENDED | NEEDS_OFFICIAL_CHECK | EXCLUDED_ALREADY_ADAPTED | EXCLUDED_NO_ADAPTATION_NEEDED | EXCLUDED_LOW_VALUE | EXCLUDED_UNVERIFIABLE",
    "eligible_to_start_adaptation": true,
    "reason": "...",
    "pending_checks": []
  }
}
```

如果用户只给出库名而没有 qualification：

1. 不自行假装资格已经通过；
2. 优先调用 `thirdparty-library-discovery` 或对应框架的候选级官方检查/活动去重流程；
3. 生成或取得标准化 qualification 后再继续。

如果已有 qualification，不要重新执行完整 discovery，除非用户明确要求重新核查，或证据已明显过期。

## 规范阶段

总控使用以下阶段 token：

- `DISCOVERY`：尚未形成候选资格产物。
- `QUALIFICATION`：候选存在，但仍需资格/官方/活动去重确认。
- `ADAPTATION`：资格已通过，可进入实际适配。
- `VALIDATION`：已有适配实现，等待构建、Demo、测试、真机运行等验证。
- `ARTICLE_PREP`：技术验证已完成，整理真实开发证据和文章素材。
- `ARTICLE_CHECK`：文章草稿存在，执行活动合规检查。
- `DONE`：技术与文章要求均已完成到当前可验证范围。
- `STOPPED`：候选被确定排除，不应继续适配。

`phase` 必须使用上面的英文 token，禁止自造同义状态。

## 规范决策

每次输出一个顶层 `decision`：

- `PROCEED`：当前门禁已通过，可以执行 `next_action`。
- `BLOCKED`：缺少必需证据或检查，必须先完成 `pending_checks`。
- `STOP`：候选已被确定排除，停止适配流程。

## Qualification 门禁

按以下优先级处理，不得乐观升级：

### 1. `EXCLUDED_ALREADY_ADAPTED`

输出：

- `phase = STOPPED`
- `decision = STOP`
- `next_action = 不开始重复适配；如有价值可改为补测试、文档或选择其他候选`

活动去重事实优先。即使技术上仍存在改进空间，也不能把它改写成“本次征文可重新适配”。

### 2. `EXCLUDED_NO_ADAPTATION_NEEDED`

输出：

- `phase = STOPPED`
- `decision = STOP`
- `next_action = 选择其他确实存在平台适配工作的候选`

不得为了推进流程而人为制造平台改造任务。

### 3. `EXCLUDED_LOW_VALUE` / `EXCLUDED_UNVERIFIABLE`

输出：

- `phase = STOPPED`
- `decision = STOP`
- 明确保留原始排除原因。

### 4. `NEEDS_OFFICIAL_CHECK`

输出：

- `phase = QUALIFICATION`
- `decision = BLOCKED`
- `next_action = 完成 qualification.pending_checks 中的官方检查或 required 去重`

如果 `pending_checks` 指向具体官方 Skill，优先调用对应官方 Skill；完成后必须重新生成 qualification，不能仅凭自然语言回答直接进入适配。

### 5. `RECOMMENDED`

只有同时满足以下条件才允许进入适配：

- `qualification.status == RECOMMENDED`；
- `qualification.eligible_to_start_adaptation == true`；
- qualification 没有仍会阻塞资格的 `pending_checks`。

输出：

- `phase = ADAPTATION`
- `decision = PROCEED`
- `next_action = 按 resources/frameworks.yaml 路由框架官方 Skills，开始实际适配`

如果 `status == RECOMMENDED` 但 `eligible_to_start_adaptation != true`，视为契约冲突：

- 不继续；
- `phase = QUALIFICATION`；
- `decision = BLOCKED`；
- 要求重新生成 qualification。

## 官方 Skill 路由

框架资源与官方 Skill 名称读取 `resources/frameworks.yaml`，不要在本 Skill 中复制易变化版本或仓库事实。

### Flutter

当前已验证的候选资格相关官方 Skills：

- `flutter-library-search`
- `ohos-flutter-plugin-adaptation-necessity-check`

它们用于资格确认，不等同于“实际适配实现 Skill”。进入 `ADAPTATION` 后：

1. 读取当前 CPF-Flutter 官方 Skills 仓库；
2. 选择与实际任务阶段匹配、当前确实存在的官方 Skill；
3. 不凭记忆硬编码未审计的 Skill 名称；
4. 如果当前环境没有合适的官方适配 Skill，明确输出需要人工/交互式适配，而不是伪造官方路由。

### 其他框架

读取 `resources/frameworks.yaml` 的 `official_skills`。配置或官方仓库尚未审计完整时，保持 `BLOCKED` 或说明能力边界，不自行创造 Skill 名称。

## 适配后的阶段门禁

qualification 只解决“是否值得开始”，不证明“适配已经完成”。

进入 `VALIDATION` 至少需要存在真实适配产物，例如：

- 实际代码 diff / commit；
- 新增或修改的平台实现；
- 可构建的工程或库产物；
- 与原接口行为对齐的实现证据。

仅有方案、伪代码或文字说明不能把阶段推进到 `VALIDATION`。

## Validation 门禁

进入 `ARTICLE_PREP` 前，至少检查：

- 编译/构建成功证据；
- Demo 或最小使用场景；
- 关键功能测试结果；
- HarmonyOS / OpenHarmony 真机成功运行证据；
- 可用于文章的真实运行截图；
- 关键问题与解决过程来自实际记录，而不是事后编造。

缺任一活动硬性证据时：

- `phase = VALIDATION`
- `decision = BLOCKED`
- 把缺项列入 `pending_checks`。

## Article Prep

技术验证通过后才进入 `ARTICLE_PREP`。

文章素材优先从以下事实中整理：

- qualification 与选库证据；
- 真实代码 diff / commit；
- 构建与运行日志；
- Demo；
- 遇到的问题、失败尝试和最终方案；
- 真机截图；
- README / API 对齐记录。

如果仓库中存在 `harmony-article-writing`，路由给它；不存在时只输出结构化素材包和待实现路由，不假装已完成文章 Skill。

## Article Check

文章草稿形成后，如果存在 `harmony-article-check`，执行活动合规检查。

合规检查与发布后指标分开：发布前不能因为“阅读量尚未达到目标”判文章内容生成失败；但必须保留为发布后待跟踪项。

## 输出契约

默认输出简洁的人类可读结论，并提供一个机器可读结构：

```json
{
  "framework": "flutter",
  "candidate": "package_name",
  "phase": "ADAPTATION",
  "decision": "PROCEED",
  "qualification_status": "RECOMMENDED",
  "next_action": "...",
  "route": {
    "skill": "...",
    "source": "official | project | manual"
  },
  "pending_checks": [],
  "evidence": []
}
```

其中：

- `qualification_status` 原样保留 qualification 的规范 token；
- `route.skill` 只有在 Skill 名称已从当前配置或当前官方仓库确认时才能填写；
- 不存在可确认的 Skill 时使用 `null`，并把 `route.source` 设为 `manual`；
- `evidence` 只放实际存在的路径、URL、commit、日志、截图等引用。

## 红线

- 不绕过 `RECOMMENDED` 门禁开始实际适配。
- 不把 `NEEDS_OFFICIAL_CHECK` 解释成“基本可以开工”。
- 不因为模型认为候选有价值就推翻活动去重排除。
- 不把官方 Skill 的 `inconclusive` 擅自升级成确定技术结论。
- 不把 qualification 当成适配完成证据。
- 不把编译成功当成真机运行成功。
- 不在没有真实开发记录时生成虚构的故障、修复、测试或截图描述。
- 不重复实现官方社区已经维护的框架级适配流程。
