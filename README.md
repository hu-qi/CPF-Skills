# CPF-Skills

面向鸿蒙三方库适配与征文流程的上层 Skills 集合。

本仓库不重复实现 CPF-Flutter、CPF-RN、CPF-ApplicationTPC 等社区已经提供的框架级能力，而是重点解决：

1. **发现值得适配的三方库**；
2. **确定活动资格与下一步路由**；
3. **优先编排当前已审计的官方 Skills**；
4. **用确定性门禁约束适配、验证、文章准备与发布检查**；
5. **把真实技术证据与测试夹具严格隔离**。

## 设计原则

- **官方 Skill 优先**：已有官方能力时不维护平行实现。
- **单一职责**：Discovery、Qualification、Routing、Validation、Article 分阶段处理。
- **配置驱动**：框架能力事实放 `resources/frameworks.yaml`，活动规则放 `resources/article-rules.yaml`。
- **证据优先于模型记忆**：实时事实来自可审计来源、源码快照、日志和真实运行证据。
- **确定性门禁优先**：资格、框架路由、Validation、文章静态规则和完整 compliance 由脚本计算，模型不能覆盖。
- **不把“未发现”当成“不存在”**：来源 `partial` / `unavailable` 时保守降级。
- **发布前与发布后分离**：阅读量等发布后指标不阻塞发布前内容检查。
- **Fixture 不得污染真实流程**：`fixture://` 证据只允许在显式 `fixture_only=true` 的回归夹具中使用，fixture compliance 永远 `publishable=false`。

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
article material pack
    ↓
harmony-article-writing
    ↓
article static check
    ↓
full compliance report
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

### `harmony-article-writing` v0.1

回答：**“如何基于真实适配证据整理文章素材、提纲和局部文本？”**

```text
.atomcode/skills/harmony-article-writing/SKILL.md
```

本 Skill 不提供“一键生成整篇参赛文章”。当前边界：

- 可以整理 qualification / validation / development notes；
- 可以生成文章结构和章节要点；
- 可以做局部改写、润色和规则对齐；
- 缺失真实问题、失败尝试或技术取舍时，只生成 `material_gaps`；
- 禁止凭空补写不存在的开发经历；
- `full_article_generation_allowed = false`。

确定性素材包：

```text
scripts/article/build_article_material_pack.py
```

### `harmony-article-check` v0.1

回答：**“这篇征文现在是否具备发布资格，还缺什么？”**

```text
.atomcode/skills/harmony-article-check/SKILL.md
```

单项检查状态：

```text
PASS
FAIL
MANUAL_REQUIRED
EXTERNAL_REQUIRED
POST_PUBLISH
NOT_APPLICABLE
```

完整发布前状态：

```text
BLOCKED
MANUAL_REVIEW_REQUIRED
READY_TO_PUBLISH
```

同时输出：

```text
publishable = true | false
```

真实输入只有在全部发布前规则通过时才能：

```text
status = READY_TO_PUBLISH
publishable = true
```

fixture 即使为了回归测试覆盖 `READY_TO_PUBLISH` 分支，也必须：

```text
fixture_only = true
publishable = false
```

当前确定性文章工具：

```text
scripts/article/check_article_static.py
scripts/article/build_compliance_report.py
```

静态检查自动覆盖：

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

`VERIFIED` 必须附 evidence。

`device_run=VERIFIED` 还要求：

```text
device_kind = physical
platform = HarmonyOS | OpenHarmony
```

模拟器/预览器不能满足活动真机门禁。

普通 validation artifact 中出现：

```text
fixture://...
```

会被直接拒绝。只有显式测试夹具允许：

```text
fixture_only = true
```

## Fixture-only E2E

目录：

```text
examples/e2e-fixture/
```

它端到端覆盖：

```text
qualification
→ validation gate
→ article material pack
→ article static check
→ compliance report
```

所有输入都带：

```text
fixture_only = true
```

所有测试证据使用：

```text
fixture://...
```

该样例**不是实际适配案例**，不能作为征文、真机运行或活动资格证据。完整说明见：

```text
examples/e2e-fixture/README.md
```

## Real-case evidence intake

初始化真实案例工作区：

```bash
python3 scripts/evidence/init_real_case.py <framework> <candidate> <output-dir>
```

例如：

```bash
python3 scripts/evidence/init_real_case.py arkts some-real-library work/some-real-library
```

初始化结果故意保持阻塞：

```text
qualification.status = NEEDS_OFFICIAL_CHECK
eligible_to_start_adaptation = false
validation.* = MISSING
external metrics = null
manual confirmations = NOT_PROVIDED
fixture_only = false
```

脚本还会：

- 解析并规范 framework alias；
- 拒绝 `applicationtpc` 这种未选择 `arkts` / `cpp` 的模糊 framework family；
- 拒绝覆盖非空输出目录；
- 生成 case 内 `README.md`，说明资格、Validation、开发记录和合规证据如何补齐。

初始化本身不代表通过任何门禁。只有真实 evidence 补齐后，才能运行同一套 qualification / validation / article pipeline。

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
- full article compliance report；
- article material pack；
- fixture-only article pipeline E2E；
- real-case evidence intake；
- fixture evidence 防污染；
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

使用隔离 matrix job，当前 5 个 contract 首轮全部通过：

```text
contract-discovery
contract-official-handoff
contract-orchestrator
contract-article-check
contract-article-writing
```

关键 CI 策略：

```text
fail-fast = false
max-parallel = 2
Pi 单次调用 timeout = 180s
```

这样单个 LLM contract 漂移不会吞掉其他 Skill 的测试结果。

模型配置：

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

这些样本用于验证候选资格判断，不代表本仓库完成了它们的实际适配。

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
├── harmony-article-writing/
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
├── article/
│   ├── build_article_material_pack.py
│   ├── check_article_static.py
│   └── build_compliance_report.py
└── evidence/
    └── init_real_case.py

examples/
└── e2e-fixture/

tests/unit/
├── test_discovery_helpers.py
├── test_orchestrator_gate.py
├── test_framework_route.py
├── test_orchestrator_next_action.py
├── test_validation_gate.py
├── test_article_rules.py
├── test_article_static_check.py
├── test_article_compliance_report.py
├── test_article_material_pack.py
├── test_e2e_article_fixture.py
└── test_real_case_intake.py
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
- [x] `harmony-article-check` v0.1
- [x] full article compliance report aggregator
- [x] `harmony-article-writing` v0.1
- [x] article material pack
- [x] 5 个独立 Pi Skill contract matrix
- [x] fixture-only article pipeline E2E
- [x] fixture evidence 防污染保护
- [x] real-case evidence intake initializer
- [x] Node 24 GitHub Actions 迁移与静态版本守卫
- [ ] 增加**真实适配完成**后的 validation/article-check 案例
- [ ] 如有分发需求，再增加 AtomCode Plugin/Marketplace 元数据

## 下一步

当前架构、合成 E2E、模型 contract、证据防污染和真实案例接入入口都已闭环。下一优先级是接入**一个真实适配案例**，而不是继续增加抽象层。

在没有真实 commit、构建日志、测试结果、HarmonyOS/OpenHarmony 实体设备运行和截图前，本仓库不会伪造“真实案例已完成”。有真实项目后，先用 `scripts/evidence/init_real_case.py` 建立工作区，再用同一套 deterministic gate、material pack 和 article compliance 流程完成首个真实验收。
