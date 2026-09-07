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

## Fixture 隔离

测试夹具和真实流程必须严格分离。

- 普通 qualification 中出现 `fixture://...` 证据时，确定性 gate 必须直接拒绝；
- 只有显式 `fixture_only = true` 的回归夹具允许使用 `fixture://...`；
- fixture 可以覆盖 qualification / routing 状态机分支，但**不能触发真实操作**；
- fixture 即使得到 `ADAPTATION/PROCEED` 状态，也不得解析真实框架 porting Skill、不得调用官方或人工适配动作；
- fixture 的 `NEEDS_OFFICIAL_CHECK` 也不得自动调用真实官方资格检查 Skill；
- 下游 artifact 必须继续传播 `fixture_only`，不得在中间阶段丢失该语义。

因此 `fixture_only = true` 只表示“允许测试状态机”，不表示“允许执行 next_action”。

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

- `PROCEED`：当前门禁已通过，可以执行 `next_action`；仅适用于真实流程。
- `BLOCKED`：缺少必需证据或检查，必须先完成 `pending_checks`。
- `STOP`：候选已被确定排除，停止适配流程。

fixture 即使为了回归覆盖得到 `PROCEED`，也只能测试状态机，不得执行真实 `next_action`。

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

对于**真实输入**，如果 `pending_checks` 指向具体官方 Skill：

1. 先确认该 Skill 已在当前 `resources/frameworks.yaml` 或当前官方仓库中存在；
2. 已确认存在时，**必须**把该 Skill 写入输出的 `route.skill`，即使当前 `decision = BLOCKED`；
3. `route.source = official`；
4. 只有名称未确认、不是 Skill、或只是人工检查事项时，`route.skill` 才使用 `null`；
5. 完成检查后必须重新生成 qualification，不能仅凭自然语言回答直接进入适配。

例如 `pending_checks = ["执行 flutter-library-search 并重新生成 qualification"]`，而当前配置已确认 `flutter-library-search` 存在，则必须输出：

```json
{
  "phase": "QUALIFICATION",
  "decision": "BLOCKED",
  "route": {
    "skill": "flutter-library-search",
    "source": "official"
  }
}
```

如果同一 artifact 为 `fixture_only = true`，则不得把该 `route.skill` 当成真实可执行动作。

### 5. `RECOMMENDED`

只有同时满足以下条件才允许真实流程进入适配：

- `fixture_only != true`；
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

fixture 为了测试状态机可以覆盖到 `ADAPTATION/PROCEED`，但仍属于非执行态：不得解析或调用真实适配路由。

## 官方 Skill 路由

框架资源与官方 Skill 名称读取 `resources/frameworks.yaml`，不要在本 Skill 中复制易变化版本或仓库事实。

真实输入进入 `ADAPTATION` 时，优先使用仓库内确定性路由：

```text
scripts/orchestrator/resolve_framework_route.py
scripts/orchestrator/resolve_next_action.py
```

确定性 resolver 的结果高于模型临场猜测；如果 resolver 返回 `MANUAL_REQUIRED`，不得自行创造一个不存在的官方实现 Skill。

当 `fixture_only = true` 时，确定性路由必须保持非执行态，例如返回 `BLOCKED_BY_GATE` / 空 route；模型不得绕过这一结果自行补出官方或人工 porting 动作。

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

对于存在多个技术栈的 framework family（例如 ApplicationTPC），必须使用明确 variant；不得把模糊 family 名称静默映射到某个实现技术栈。

## 适配后的阶段门禁

qualification 只解决“是否值得开始”，不证明“适配已经完成”。

进入 `VALIDATION` 至少需要存在真实适配产物，例如：

- 实际代码 diff / commit；
- 新增或修改的平台实现；
- 可构建的工程或库产物；
- 与原接口行为对齐的实现证据。

仅有方案、伪代码或文字说明不能把阶段推进到 `VALIDATION`。

## Validation 门禁

进入 Validation 阶段后，**不得仅凭自然语言描述判断是否可以写文章**。

优先读取：

```text
references/validation-artifact.md
```

并使用仓库内确定性门禁：

```text
scripts/orchestrator/resolve_validation_gate.py
```

Validation Artifact 必须包含以下 6 个 required checks：

- `implementation`
- `build`
- `demo`
- `tests`
- `device_run`
- `screenshots`

每项只允许以下状态 token：

```text
VERIFIED
FAILED
NOT_RUN
MISSING
```

其中：

- `VERIFIED` 必须附带至少一个真实 evidence 引用；
- `device_run=VERIFIED` 必须明确 `device_kind=physical`；
- `device_run=VERIFIED` 的 `platform` 必须是 `HarmonyOS` 或 `OpenHarmony`；
- 模拟器、预览器或 Android/iOS 设备不能满足真机运行门禁；
- 任一检查 `FAILED` / `NOT_RUN` / `MISSING` 时，保持 `VALIDATION/BLOCKED`；
- 只有六项全部满足确定性契约时，才能得到 `ARTICLE_PREP/PROCEED`。

因此，进入 `ARTICLE_PREP` 前至少要有：

- 真实实现证据；
- 编译/构建成功证据；
- Demo 或最小使用场景；
- 关键功能测试结果；
- HarmonyOS / OpenHarmony 实体设备成功运行证据；
- 可用于文章的真实运行截图；
- 关键问题与解决过程来自实际记录，而不是事后编造。

Validation Gate 的机器输出是阶段推进的事实依据。模型不能因为“证据看起来差不多齐了”而覆盖 `BLOCKED`。

fixture Validation 可以覆盖同一状态机，但必须保持 `fixture_only = true`，不得被解释为真实技术证据。

## Article Prep

只有真实 `resolve_validation_gate.py` 输出：

```text
phase = ARTICLE_PREP
decision = PROCEED
fixture_only = false
```

才进入真实文章准备阶段。

文章素材优先从以下事实中整理：

- qualification 与选库证据；
- 真实代码 diff / commit；
- 构建与运行日志；
- Demo；
- 遇到的问题、失败尝试和最终方案；
- 真机截图；
- README / API 对齐记录。

如果仓库中存在 `harmony-article-writing`，路由给它；不存在时只输出结构化素材包和待实现路由，不假装已完成文章 Skill。

fixture 的 Article Material Pack 只能用于结构和回归测试，不能包装成真实征文素材。

## Article Check

文章草稿形成后，如果存在 `harmony-article-check`，执行活动合规检查。

合规检查与发布后指标分开：发布前不能因为“阅读量尚未达到目标”判文章内容生成失败；但必须保留为发布后待跟踪项。

fixture 即使覆盖 `READY_TO_PUBLISH` 状态分支，也必须保持 `publishable = false`。

## 输出契约

默认输出简洁的人类可读结论，并提供一个机器可读结构：

```json
{
  "fixture_only": false,
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

- `fixture_only` 必须从输入继续传播，不能在中间阶段丢失；
- `qualification_status` 原样保留 qualification 的规范 token；
- `route.skill` 只有在 Skill 名称已从当前配置或当前官方仓库确认、且当前是真实可执行流程时才能填写；
- **当真实 `NEEDS_OFFICIAL_CHECK` 的 `pending_checks` 明确引用已确认存在的 Skill 时，`route.skill` 必须填写该 Skill，不能因为 `decision = BLOCKED` 而置空**；
- fixture 不得产生可执行的真实 Skill route；
- 不存在可确认的 Skill 时使用 `null`，并把 `route.source` 设为 `manual`；
- `evidence` 只放实际存在的路径、URL、commit、日志、截图等引用；真实流程不得使用 `fixture://`。

## 红线

- 不绕过 `RECOMMENDED` 门禁开始实际适配。
- 不把 `NEEDS_OFFICIAL_CHECK` 解释成“基本可以开工”。
- 不因为模型认为候选有价值就推翻活动去重排除。
- 不把官方 Skill 的 `inconclusive` 擅自升级成确定技术结论。
- 不把 qualification 当成适配完成证据。
- 不把编译成功当成真机运行成功。
- 不把模拟器/预览器结果当作真机运行成功。
- 不绕过 deterministic Validation Gate 进入 `ARTICLE_PREP`。
- 不在没有真实开发记录时生成虚构的故障、修复、测试或截图描述。
- 不重复实现官方社区已经维护的框架级适配流程。
- 不允许 fixture 触发真实资格检查、适配路由、官方 Skill 或人工 porting 动作。
- 不允许把 `fixture://` 证据混入真实 qualification、validation、material pack 或 compliance。