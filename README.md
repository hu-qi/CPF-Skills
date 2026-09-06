# CPF-Skills

面向鸿蒙三方库适配与征文流程的上层 Skills 集合。

本仓库不重复实现 CPF-Flutter、CPF-RN、CPF-ApplicationTPC 等社区已经提供的框架级能力，而是重点解决：

1. **发现值得适配的三方库**；
2. **确定资格与下一步路由**；
3. **优先编排当前已审计的官方 Skills**；
4. **用确定性门禁约束适配、验证、文章准备与发布检查**。

## 设计原则

- **官方 Skill 优先**：已有官方能力时不维护平行实现。
- **单一职责**：Discovery、Qualification、Routing、Validation、Article 分阶段处理。
- **配置驱动**：框架能力事实放 `resources/frameworks.yaml`，活动规则放 `resources/article-rules.yaml`。
- **证据优先于模型记忆**：实时事实来自可审计来源、源码快照、日志和真实运行证据。
- **确定性门禁优先**：资格、框架路由、Validation、文章静态规则由脚本计算，模型不能覆盖。
- **不把“未发现”当成“不存在”**：来源 `partial` / `unavailable` 时保守降级。
- **发布前与发布后分离**：阅读量等发布后指标不阻塞发布前内容检查。

## 当前主流程

```text
第三方生态
    ↓
thirdparty-library-discovery
    ↓
discovery evidence
    ↓
官方 Skill judgment + 活动去重
    ↓
candidate qualification artifact
    ↓
qualification gate
    ↓
framework route resolver
    ↓
官方 Skill / manual adaptation
    ↓
validation artifact
    ↓
validation gate
    ↓
ARTICLE_PREP
    ↓
harmony-article-check
    ↓
发布 / 人工补项 / 外部指标检查
```

## 当前可用 Skills

### `thirdparty-library-discovery`

回答：**“我应该适配哪个三方库？”**

```text
.atomcode/skills/thirdparty-library-discovery/SKILL.md
```

当前 Flutter discovery 已跑通真实 evidence 流程，并明确区分：

- `flutter-library-search` 第一层官方业务结论；
- `ohos-flutter-plugin-adaptation-necessity-check` 按需源码级复核；
- 活动 required 去重；
- 最终 `RECOMMENDED / NEEDS_OFFICIAL_CHECK / EXCLUDED_*` 状态。

关键规则：

```text
library_search = needs_adaptation
+ required dedup 全部 checked
+ required dedup 无命中
```

即可进入 `RECOMMENDED` 资格判断；`adaptation_necessity = not_run` 本身不是阻塞条件。

官方 handoff 规范：

```text
.atomcode/skills/thirdparty-library-discovery/references/official-skill-handoff.md
```

### `harmony-contribution-orchestrator`

回答：**“这个候选现在允许做什么，下一步路由到哪里？”**

```text
.atomcode/skills/harmony-contribution-orchestrator/SKILL.md
```

当前确定性链路：

```text
candidate qualification
    ↓
resolve_qualification_gate.py
    ↓
resolve_framework_route.py
    ↓
resolve_next_action.py
```

适配完成后：

```text
validation artifact
    ↓
resolve_validation_gate.py
    ↓
VALIDATION/BLOCKED
或
ARTICLE_PREP/PROCEED
```

Validation Artifact 契约：

```text
.atomcode/skills/harmony-contribution-orchestrator/references/validation-artifact.md
```

### `harmony-article-check` v0.1

回答：**“这篇征文现在是否具备发布资格，还缺什么？”**

```text
.atomcode/skills/harmony-article-check/SKILL.md
```

检查结果严格区分：

```text
PASS
FAIL
MANUAL_REQUIRED
EXTERNAL_REQUIRED
POST_PUBLISH
NOT_APPLICABLE
```

完整发布状态：

```text
BLOCKED
MANUAL_REVIEW_REQUIRED
READY_TO_PUBLISH
```

当前确定性文章静态检查器：

```text
scripts/article/check_article_static.py
```

已自动检查：

- H1 标题是否明确包含框架/技术栈；
- 去除 fenced/inline code 后非代码中文字符是否 `>= 800`；
- 最终文章是否出现禁止的 `GitCode` 品牌/链接；
- 开头和结尾是否各包含一次规范社区引导语；
- 图片引用是否存在（仅 INFO，不能代替真机截图真实性）。

以下不能由模型自动宣称通过：

- 原创性；
- 重复率；
- AI 是否生成全部或大部分正文；
- CSDN 实际质量分；
- 真机截图真实性。

## Shared Activity Rules

活动级 SSOT：

```text
resources/article-rules.yaml
```

目前结构化维护：

- 开工资格；
- 技术验证证据；
- 标题/正文/原创/字数规则；
- 重复率 `<= 30%`；
- 非代码中文正文 `>= 800`；
- AtomGit / GitCode 品牌与链接规则；
- 开头/结尾社区引导语；
- AI 不得生成文章全部或大部分内容；
- CSDN 质量分 `>= 80`；
- 发布后阅读量 `>= 1000`，但不作为发布前阻塞项。

CSDN 质量检查入口：

```text
https://www.csdn.net/qc
```

框架社区名称和组织链接不复制进 `article-rules.yaml`，统一从 `resources/frameworks.yaml` 获取。

## Qualification 门禁

状态：

```text
RECOMMENDED
NEEDS_OFFICIAL_CHECK
EXCLUDED_ALREADY_ADAPTED
EXCLUDED_NO_ADAPTATION_NEEDED
EXCLUDED_LOW_VALUE
EXCLUDED_UNVERIFIABLE
```

只有：

```text
qualification.status == RECOMMENDED
qualification.eligible_to_start_adaptation == true
pending_checks == []
```

才允许：

```text
phase = ADAPTATION
decision = PROCEED
```

## Framework Routing

路由事实：

```text
resources/frameworks.yaml
```

### Flutter

已审计资格相关 Skills：

```text
flutter-library-search
ohos-flutter-plugin-adaptation-necessity-check
```

当前未确认独立实际 porting implementation Skill。

### React Native

当前官方 HEAD 已审计确认：

```text
rnoh-lib-interface-analyzer
rnoh-lib-code-check
rnoh-lib-demo-doc
rnoh-lib-demo-gen
rnoh-lib-xts-gen
```

未发现独立实际移植 implementation Skill：

```text
adaptation_implementation = null
```

### ApplicationTPC / ArkTS

当前审计确认：

```text
ohos-library-migration-analyzer
    ↓
ohos-library-porting
```

ArkTS 可确定性路由到官方 porting Skill。

### ApplicationTPC / C/C++

当前确认分析能力：

```text
analysis_skill = ohos-library-migration-analyzer
```

但尚无足够证据把 `ohos-library-porting` 当作完整 C/C++ NDK 实现 Skill：

```text
adaptation_implementation = null
route_type = MANUAL_REQUIRED
```

`applicationtpc` 不能静默选 ArkTS；必须明确 `arkts` 或 `cpp`。

## Validation Gate

进入 `ARTICLE_PREP` 前必须验证：

```text
implementation
build
demo
tests
device_run
screenshots
```

状态只能使用：

```text
VERIFIED
FAILED
NOT_RUN
MISSING
```

`VERIFIED` 必须附真实 evidence。

`device_run=VERIFIED` 还要求：

```text
device_kind = physical
platform = HarmonyOS | OpenHarmony
```

模拟器/预览器不能满足活动真机门禁。

## CI / 测试分层

### Deterministic Tests

```text
.github/workflows/deterministic-tests.yml
```

自动运行，无需模型 API Key。当前覆盖：

- discovery helper；
- qualification gate；
- framework route；
- orchestrator next-action；
- validation gate；
- article-rules schema；
- article static checker；
- GitHub Actions Node 24 runtime guard。

第一方 GitHub Actions 最低版本：

```text
actions/checkout        >= v7
actions/upload-artifact >= v7
actions/setup-python    >= v7
actions/setup-node      >= v6
```

### Pi Skill Contract Tests

```text
.github/workflows/pi-skill-test.yml
```

自动使用：

```text
agnes-2.5-flash
https://api.agnes-ai.cn/v1
```

Secret：

```text
AGNES_API_KEY
```

API Key 不进入仓库。

### Live Flutter Discovery E2E

```text
.github/workflows/pi-live-discovery.yml
```

手动执行；实时网络采集由确定性脚本控制，Pi 使用 `--no-tools` 消费 evidence snapshot。

### Official Flutter Candidate Smoke

```text
.github/workflows/pi-official-flutter-candidate.yml
```

真实样本已验证：

- `cached_network_image` → `EXCLUDED_NO_ADAPTATION_NEEDED`
- `audioplayers` → required 活动去重明确命中 → `EXCLUDED_ALREADY_ADAPTED`

### Official Skills Audits

```text
.github/workflows/cpf-flutter-official-skills-smoke.yml
.github/workflows/cpf-rn-official-skills-audit.yml
.github/workflows/cpf-applicationtpc-official-skills-audit.yml
```

浅克隆当前官方 HEAD、枚举实际 `SKILL.md`、保存 commit 和 artifact，避免凭记忆维护 Skill 名称。

## 关键实现

```text
.atomcode/skills/
├── thirdparty-library-discovery/
├── harmony-contribution-orchestrator/
└── harmony-article-check/

resources/
├── frameworks.yaml
└── article-rules.yaml

scripts/
├── orchestrator/
│   ├── resolve_qualification_gate.py
│   ├── resolve_framework_route.py
│   ├── resolve_next_action.py
│   └── resolve_validation_gate.py
└── article/
    └── check_article_static.py

tests/unit/
├── test_discovery_helpers.py
├── test_orchestrator_gate.py
├── test_framework_route.py
├── test_orchestrator_next_action.py
├── test_validation_gate.py
├── test_article_rules.py
└── test_article_static_check.py
```

## Roadmap

- [x] 仓库定位与职责边界
- [x] `thirdparty-library-discovery`
- [x] Flutter live evidence + official Skill handoff
- [x] candidate qualification artifact
- [x] qualification deterministic gate
- [x] `harmony-contribution-orchestrator` MVP
- [x] CPF-Flutter / CPF-RN / CPF-ApplicationTPC 官方能力审计
- [x] ArkTS / C/C++ 显式 framework routing
- [x] `qualification → gate → route → next_action`
- [x] Validation Artifact + deterministic Validation Gate
- [x] `resources/article-rules.yaml`
- [x] `harmony-article-check` v0.1 + deterministic static checker
- [x] Node 24 GitHub Actions 迁移与静态版本守卫
- [ ] 为 `harmony-article-check` 增加 Pi contract
- [ ] 实现完整 article compliance report aggregator（static + validation + external/manual evidence）
- [ ] 实现 `harmony-article-writing`
- [ ] 增加真实适配完成后的 validation/article-check 样例
- [ ] 如有分发需求，再增加 AtomCode Plugin/Marketplace 元数据

## 下一步

优先完成 `harmony-article-check` 的模型契约与完整 compliance report 聚合层；稳定后再实现 `harmony-article-writing`。这样写作 Skill 生成或修改文章后，可以立即交给确定性/结构化检查，而不是“先写再猜是否合规”。
