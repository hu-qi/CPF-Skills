# CPF-Skills

面向鸿蒙三方库适配与征文流程的上层 Skills 集合。

本仓库不重复实现 CPF-Flutter、CPF-RN、CPF-ApplicationTPC 等社区已经提供的框架级能力，而是重点解决：

1. **发现值得适配的三方库**：从各生态中筛选有价值、需要鸿蒙适配、且尚未完成适配的候选库。
2. **确定资格与路由**：把 discovery、官方 Skill 结论、活动去重收敛为稳定 qualification，并确定性决定下一步。
3. **编排官方 Skills**：根据框架、技术栈与阶段，优先复用当前已经审计确认的官方 Skill。
4. **管理验证与征文流程**：严格区分“可以开始适配”“适配已完成”“具备文章素材”“文章合规”。

## 设计原则

- **官方 Skill 优先**：已有官方能力时，不在本仓库维护平行实现。
- **单一职责**：Discovery、Qualification、Routing、Validation、Article 是不同阶段。
- **配置驱动**：框架资源、官方仓、去重源和能力映射维护在 `resources/`，不散落硬编码。
- **事实与流程分离**：实时事实来自可审计数据源/源码快照；Skill 负责流程和判断规则。
- **活动规则高于通用输出**：官方 Skill 负责技术判断；活动资格与文章合规由本项目规则约束。
- **不把“未发现”当作“不存在”**：来源 `partial` / `unavailable` 时必须保守降级。
- **确定性门禁优先**：资格、框架路由、Validation 等关键状态由 Python contract 计算，模型不能绕过。
- **真实证据优先**：不把方案、推测、模拟器结果或模型描述当成真机运行/适配完成证据。

## 当前流程

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
文章写作 / 合规检查（下一阶段）
```

## 当前可用 Skills

### `thirdparty-library-discovery`

回答：**“我应该适配哪个三方库？”**

项目级 Skill：

```text
.atomcode/skills/thirdparty-library-discovery/SKILL.md
```

当前 Flutter discovery 已跑通真实 evidence 流程，核心约束包括：

- pub.dev 候选发现；
- direct `flutter.plugin` 信号预筛；
- 不把“支持 Android/iOS”直接等同于“需要原生适配”；
- 去重使用规范化等价名称，不使用任意 substring；
- 官方 `flutter-library-search` / necessity check 只负责技术判断；
- required 去重源未完整检查时不能升级为 `RECOMMENDED`；
- 输出使用规范状态 token，不允许自造同义状态。

官方 Skill handoff 规范：

```text
.atomcode/skills/thirdparty-library-discovery/references/official-skill-handoff.md
```

### `harmony-contribution-orchestrator`

回答：**“这个候选现在允许做什么，下一步路由到哪里？”**

项目级 Skill：

```text
.atomcode/skills/harmony-contribution-orchestrator/SKILL.md
```

当前已经具备四个确定性层：

```text
candidate qualification
    ↓
resolve_qualification_gate.py
    ↓
resolve_framework_route.py
    ↓
resolve_next_action.py
    ↓
adaptation / blocked / stopped
```

适配完成后再进入：

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

## Qualification 门禁

最终候选资格使用以下状态：

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

才允许进入：

```text
phase = ADAPTATION
decision = PROCEED
```

其余状态只能 `BLOCKED` 或 `STOP`。

## Framework Route Resolver

框架路由事实维护在：

```text
resources/frameworks.yaml
```

当前关键边界：

### Flutter

已审计资格相关官方 Skills：

- `flutter-library-search`
- `ohos-flutter-plugin-adaptation-necessity-check`

当前未确认独立的实际 porting implementation Skill，因此进入实现阶段后不能凭空创造官方路由。

### React Native

当前 CPF-RN 官方 HEAD 已由 CI 审计。已确认的三方库业务能力包括：

- `rnoh-lib-interface-analyzer`
- `rnoh-lib-code-check`
- `rnoh-lib-demo-doc`
- `rnoh-lib-demo-gen`
- `rnoh-lib-xts-gen`

当前未审计到独立实际移植 implementation Skill，因此：

```text
adaptation_implementation = null
```

### ApplicationTPC / ArkTS

当前官方仓审计确认：

```text
oh​​os-library-migration-analyzer
    ↓
oh​​os-library-porting
```

实际配置使用无零宽字符的 Skill 名：

```text
ohos-library-migration-analyzer
ohos-library-porting
```

ArkTS 可确定性路由到官方 `ohos-library-porting`。

### ApplicationTPC / C/C++

当前审计确认 `ohos-library-migration-analyzer` 可以用于迁移分析，但现有 `ohos-library-porting` 主流程面向 ArkTS/ETS + HAR，没有足够证据把它视为完整 C/C++ NDK 实现 Skill。因此：

```text
analysis_skill = ohos-library-migration-analyzer
adaptation_implementation = null
route_type = MANUAL_REQUIRED
```

通用名称 `applicationtpc` 不允许静默选择 ArkTS；必须显式指定 `arkts` 或 `cpp`。

## Validation Gate

适配已经开始，不等于适配已经验证完成。

进入 `ARTICLE_PREP` 前必须同时验证：

1. `implementation`：真实代码/实现产物；
2. `build`：构建成功；
3. `demo`：Demo 或最小使用场景；
4. `tests`：关键功能测试通过；
5. `device_run`：HarmonyOS/OpenHarmony **实体设备**运行成功；
6. `screenshots`：真实成功运行截图。

每项状态只能使用：

```text
VERIFIED
FAILED
NOT_RUN
MISSING
```

所有检查均为 `VERIFIED` 且有证据时：

```text
phase = ARTICLE_PREP
decision = PROCEED
```

否则：

```text
phase = VALIDATION
decision = BLOCKED
```

其中 `device_run=VERIFIED` 还强制要求：

```text
device_kind = physical
platform = HarmonyOS | OpenHarmony
```

模拟器/预览器不能满足征文真机门禁。

## CI / 测试分层

### 1. Deterministic Tests

```text
.github/workflows/deterministic-tests.yml
```

自动运行，不需要模型 API Key。当前覆盖：

- discovery helper regression；
- qualification gate；
- framework route resolver；
- composed orchestrator next-action；
- validation gate；
- GitHub Actions Node 24 runtime guard。

GitHub Actions 第一方依赖最低版本守卫：

```text
actions/checkout        >= v7
actions/upload-artifact >= v7
actions/setup-python    >= v7
actions/setup-node      >= v6
```

### 2. Pi Skill Contract Tests

```text
.github/workflows/pi-skill-test.yml
```

自动使用 `agnes-2.5-flash`，Secret：

```text
AGNES_API_KEY
```

endpoint：

```text
https://api.agnes-ai.cn/v1
```

API Key 不进入仓库。

Pi contract 负责检查模型是否遵守 Skill 状态机；关键流程门禁仍由 deterministic resolver 最终决定。

### 3. Live Flutter Discovery E2E

```text
.github/workflows/pi-live-discovery.yml
```

手动运行。流程为：

```text
实时确定性采集 evidence
    ↓
Pi --no-tools + project Skill
    ↓
机器断言
```

模型不控制实时网络采集。

### 4. Official Flutter Candidate Smoke

```text
.github/workflows/pi-official-flutter-candidate.yml
```

手动运行单候选核查：

```text
确定性采集官方规则所需 evidence
    ↓
Pi --no-tools + CPF-Flutter official Skill
    ↓
official handoff
    ↓
activity evidence
    ↓
qualification
    ↓
gate / route
```

真实样本已经验证：

- `cached_network_image` → `EXCLUDED_NO_ADAPTATION_NEEDED`
- `audioplayers` → 活动去重明确命中 → `EXCLUDED_ALREADY_ADAPTED`

### 5. Official Skills Audits

当前有：

```text
.github/workflows/cpf-flutter-official-skills-smoke.yml
.github/workflows/cpf-rn-official-skills-audit.yml
.github/workflows/cpf-applicationtpc-official-skills-audit.yml
```

它们浅克隆官方当前 HEAD、枚举实际 `SKILL.md`、保存 commit 和 artifact，以避免凭记忆维护 Skill 名称。

## 关键实现文件

```text
scripts/
├── qualification/
│   └── ...
└── orchestrator/
    ├── resolve_qualification_gate.py
    ├── resolve_framework_route.py
    ├── resolve_next_action.py
    └── resolve_validation_gate.py

tests/unit/
├── test_discovery_helpers.py
├── test_orchestrator_gate.py
├── test_framework_route.py
├── test_orchestrator_next_action.py
└── test_validation_gate.py
```

## 规划中的 Skills

### `harmony-article-writing`

基于真实 qualification、代码 diff、提交、构建/测试日志、问题记录和真机截图组织技术文章，不虚构适配过程。

### `harmony-article-check`

对标题、字数、真机截图、社区引导、品牌/链接、CSDN 质量要求等活动规则做结构化检查，并把发布前内容合规与发布后阅读指标分开。

## Roadmap

- [x] 仓库定位与职责边界
- [x] `thirdparty-library-discovery` v0.1
- [x] Flutter live evidence + official Skill handoff
- [x] candidate qualification artifact
- [x] qualification deterministic gate
- [x] `harmony-contribution-orchestrator` MVP
- [x] CPF-Flutter / CPF-RN / CPF-ApplicationTPC 官方能力审计
- [x] ArkTS / C/C++ 显式 framework routing
- [x] composed `qualification → gate → route → next_action`
- [x] Validation Artifact + deterministic Validation Gate
- [x] Node 24 GitHub Actions 迁移与静态版本守卫
- [ ] 建立 `article-rules.yaml`，结构化活动规则
- [ ] 实现 `harmony-article-writing`
- [ ] 实现 `harmony-article-check`
- [ ] 增加真实适配完成后的 validation artifact 样例
- [ ] 如有分发需求，再增加 AtomCode Plugin/Marketplace 元数据

## 下一步

当前技术侧主链已经具备确定性资格、框架路由和 Validation Gate。下一步进入文章侧之前，优先建立：

```text
resources/article-rules.yaml
```

把征文规则拆成：

- 发布前硬性门禁；
- 文章内容/结构规则；
- 品牌与链接规则；
- AI 使用约束；
- CSDN 发布前质量检查；
- 发布后阅读量指标。

完成后，`harmony-article-writing` 与 `harmony-article-check` 才有稳定的共享事实源，而不是各自在 Skill 文案里复制活动规则。
