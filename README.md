# CPF-Skills

面向鸿蒙三方库适配与征文流程的上层 Skills 集合。

本仓库不重复实现 CPF-Flutter、CPF-RN、CPF-ApplicationTPC 等社区已经提供的三方库适配能力，而是重点解决：

1. **发现值得适配的三方库**：从各生态中筛选有价值、需要鸿蒙适配、且尚未完成适配的候选库。
2. **编排官方 Skills**：根据框架和任务阶段，优先复用对应社区维护的官方 Skill。
3. **征文流程管理**：把选库、去重、适配、验证、写作、质检串成完整流程。
4. **文章合规检查**：按照活动规则检查标题、字数、运行截图、社区引导、品牌与链接等要求。

## 设计原则

- **官方 Skill 优先**：已有官方能力时，不在本仓库维护平行实现。
- **单一职责**：一个 Skill 解决一个明确问题，避免“大而全”的 Skill。
- **配置驱动**：框架版本、SDK、中心仓、去重仓、社区链接等易变化信息不硬编码进 Skill 主逻辑。
- **事实与流程分离**：Skill 描述“怎么做”，资源文件维护“当前是什么”。
- **先发现，再判定，再适配**：候选库发现、适配必要性判断、实际适配是三个不同阶段。
- **活动规则高于通用输出**：官方 Skill 负责技术判断；征文资格与最终文章合规以当前活动规则为准。
- **证据优先于模型记忆**：实时事实由可审计的数据源或源码快照提供，模型只在证据之上做规则判定。
- **不把“未发现”当作“不存在”**：来源 `partial` / `unavailable` 时必须保守降级。

## 当前可用 Skill

### `thirdparty-library-discovery` v0.1

回答：**“我应该适配哪个三方库？”**

当前正式支持 Flutter 作为首个样例，其他框架已经建立资源路由，但仍标记为 `experimental`。

主要能力：

- 从框架对应的包中心/目录发现候选库；
- Flutter 候选优先要求 pubspec 存在直接 `flutter.plugin` 平台声明，避免把“支持 Android/iOS”误当成“包含原生插件实现”；
- 过滤失维、低价值或无法验证的候选；
- 将“候选发现”和“适配必要性判断”分开；
- Flutter 优先衔接 CPF-Flutter 官方 `flutter-library-search` 与 `ohos-flutter-plugin-adaptation-necessity-check`；
- 按活动要求检查中心仓和社区仓去重；
- 去重仓库名称使用规范化后的**等价名称匹配**，禁止任意 substring 匹配，避免 `file` 误撞 `file_picker` 等情况；
- 以生态价值、适配必要性、可行性、征文价值四个维度评分；
- 输出推荐、待官方确认、已适配、无需适配等明确状态；
- 强制区分“未搜索到”和“确定不存在”，避免把推测当事实。

项目级 Skill 位于：

```text
.atomcode/skills/thirdparty-library-discovery/SKILL.md
```

官方 Skill 与本项目状态机之间的稳定交接协议位于：

```text
.atomcode/skills/thirdparty-library-discovery/references/official-skill-handoff.md
```

在 AtomCode 中进入本仓库后，可通过 Skill 菜单或自然语言触发，例如：

```text
帮我找 10 个 Flutter 适合做鸿蒙三方库适配征文的候选库，优先中等难度、文件和多媒体方向。
```

也可以显式选择：

```text
$thirdparty-library-discovery 帮我找 10 个 Flutter 候选库
```

> Skill 能否直接调用 CPF 官方 Skills，取决于当前运行环境是否已经安装/加载对应官方 Skill。关键官方检查不可执行时，本 Skill 必须输出 `NEEDS_OFFICIAL_CHECK`，不得伪造官方结论。

## Flutter 官方 Skill Handoff

目前对 CPF-Flutter 两个官方 Skill 建立了明确路由：

- `flutter-library-search`：库搜索、已有鸿蒙支持检查、是否需要适配的第一层结论；
- `ohos-flutter-plugin-adaptation-necessity-check`：需要完整源码的进一步技术必要性检查，按需执行，不强制每个候选都跑。

`flutter-library-search` 的结果归一化为：

```text
adapted
needs_adaptation
no_adaptation_needed
inconclusive
not_run
```

其中：

- `adapted` → `EXCLUDED_ALREADY_ADAPTED`
- `no_adaptation_needed` → `EXCLUDED_NO_ADAPTATION_NEEDED`
- `needs_adaptation` + 活动 required 去重全部完成且无命中 → 才有资格进入 `RECOMMENDED`
- `inconclusive` / `not_run` → `NEEDS_OFFICIAL_CHECK`

官方结果、活动去重和最终候选状态是三层不同语义，不互相偷换。

## 官方 Skills 依赖

本项目优先复用以下社区提供的 Skills：

- CPF-Flutter: https://atomgit.com/CPF-Flutter/skills
- CPF-RN: https://atomgit.com/CPF-RN/skills
- CPF-ApplicationTPC: https://atomgit.com/CPF-ApplicationTPC/skills

具体调用关系和能力映射维护在 `resources/frameworks.yaml`。尚未完成官方仓库审计的 Skill 名称不会凭记忆写入配置。

CPF-Flutter 当前还有一个无模型 smoke workflow：

```text
.github/workflows/cpf-flutter-official-skills-smoke.yml
```

它会浅克隆最新官方 Skills 仓库，校验本项目依赖的 Skill 路径存在，并把 `SKILL.md`、`references/` 和官方仓库 commit 作为 Actions artifact 保存，避免复制官方 Skill 到本仓库造成版本漂移。

## CI / 测试分层

### 1. Deterministic Discovery Tests

```text
.github/workflows/deterministic-tests.yml
```

自动运行，不需要 API Key，不调用模型，不访问实时业务数据。用于锁定确定性代码行为，例如：

- `file_picker` 可以匹配 `fluttertpc_file_picker`；
- `file` 不能因为 substring 匹配而误撞 `file_picker`；
- `no_adaptation_needed` 与 `needs_adaptation` 对缺失搜索源采用不同的证据完整性规则；
- 官方源码快照的 pubspec 包名解析稳定。

这是成本最低、最应该作为基础门禁的一层。

### 2. Pi Skill Contract Tests

```text
.github/workflows/pi-skill-test.yml
```

自动运行 `agnes-2.5-flash`，使用 Repository Secret：

```text
AGNES_API_KEY
```

通过 OpenAI-compatible endpoint `https://api.agnes-ai.cn/v1` 调用。API Key **不得提交到仓库**。

当前包含两类固定 fixture：

1. discovery 核心状态机：验证 `NEEDS_OFFICIAL_CHECK`、`EXCLUDED_ALREADY_ADAPTED`、`EXCLUDED_NO_ADAPTATION_NEEDED`；
2. official handoff：验证 `RECOMMENDED`、已适配排除、无需适配排除、required 去重不完整时降级。

Pi 通过 `--skill .atomcode/skills/thirdparty-library-discovery/SKILL.md` 注册 Skill，并通过 `/skill:thirdparty-library-discovery` 强制加载完整内容。测试接受纯 JSON 或单个 fenced JSON，但对候选数量、字段和规范状态 token 做严格断言。

> Fork PR 默认拿不到 Repository Secrets，因此模型 contract 只在能够读取仓库 Secret 的运行上下文中执行。

### 3. Live Flutter Discovery E2E

```text
.github/workflows/pi-live-discovery.yml
```

**手动运行。** 只使用 `agnes-2.5-flash`。

流程拆成：

```text
实时确定性采集
  ↓
flutter-evidence.json
  ↓
Pi --no-tools + thirdparty-library-discovery
  ↓
机器断言
```

确定性采集器会读取 `resources/frameworks.yaml`，从当前 pub.dev 与活动去重源获取候选/去重证据。Pi 不控制网络请求，只负责在 evidence snapshot 上执行 Skill 状态机。

当前候选发现已经增加两个重要约束：

- 平台支持标签不能替代直接 Flutter plugin 信号；
- 社区仓去重必须按包身份等价匹配，不做模糊 substring 排除。

### 4. Pi Official Flutter Candidate Smoke

```text
.github/workflows/pi-official-flutter-candidate.yml
```

**手动运行。** 输入一个真实 Flutter package name，用于进一步核查某个候选。

它不是把网络控制权交给官方 Skill，而是：

```text
浅克隆最新 CPF-Flutter Skills
  ↓
按官方规则确定性采集 pub.dev / 原仓源码 / 跨平台搜索证据
  ↓
原仓优先 shallow git clone，避免匿名 GitHub API rate limit
  ↓
Pi --no-tools + 官方 flutter-library-search
  ↓
OFFICIAL_RESULT
  ↓
<candidate>.handoff.json
```

原仓扫描会定位与候选 package name 匹配的 `pubspec.yaml`，检查 `android/`、`ios/`、`ohos/`/`harmony/`、Dart channel 标记和平台判断，并记录实际源码 commit。

2026-09-06 的首次完整验证中，`cached_network_image` 被官方 `flutter-library-search` 基于源码证据判断为 `no_adaptation_needed`，归一化 handoff 成功。这个例子也促使 discovery 阶段增加 direct-plugin 预筛，避免再把纯 Dart 高热度包放到候选榜首。

实时/跨站来源不可用时，smoke 可以产出 `inconclusive`；它的目的首先是保存可审计证据，而不是为了“跑绿”强行给出确定结论。

## 规划中的 Skills

### `harmony-contribution-orchestrator`

回答：**“完成一次三方库适配征文，接下来应该做什么？”**

负责识别框架、读取当前活动配置、调用官方 Skills，并串联：

`选库 → 去重 → 必要性判断 → 适配 → Demo/测试验证 → 写作 → 合规检查`

### `harmony-article-writing`

回答：**“如何把真实适配过程整理成符合要求的技术文章？”**

重点基于真实开发材料（代码 diff、提交记录、README、Demo、错误与解决过程、运行截图）组织文章，而不是脱离事实直接生成完整适配经历。

### `harmony-article-check`

回答：**“这篇文章是否符合征文要求？”**

输出可执行的合规检查结果，包括硬性要求、缺失项、风险项和发布后指标。

## 当前目录

```text
CPF-Skills/
├── .atomcode.md
├── .atomcode/
│   └── skills/
│       └── thirdparty-library-discovery/
│           ├── SKILL.md
│           └── references/
│               └── official-skill-handoff.md
├── .github/
│   └── workflows/
│       ├── deterministic-tests.yml
│       ├── pi-skill-test.yml
│       ├── pi-live-discovery.yml
│       ├── pi-official-flutter-candidate.yml
│       └── cpf-flutter-official-skills-smoke.yml
├── resources/
│   └── frameworks.yaml
├── scripts/
│   └── ci/
│       ├── fetch-cpf-flutter-skills.sh
│       ├── test-pi-skill.sh
│       ├── test-pi-live-discovery.sh
│       └── test-pi-official-flutter-candidate.sh
├── tests/
│   ├── unit/
│   │   └── test_discovery_helpers.py
│   └── pi/
│       ├── discovery-contract.prompt.md
│       ├── assert_discovery_contract.py
│       ├── official-handoff-contract.prompt.md
│       ├── assert_official_handoff_contract.py
│       └── live/
│           ├── collect_flutter_evidence.py
│           ├── collect_official_flutter_search_evidence.py
│           ├── normalize_official_flutter_result.py
│           ├── flutter-discovery.prompt.md
│           └── assert_flutter_discovery.py
└── README.md
```

采用 `.atomcode/skills/` 是为了让 AtomCode 在当前项目中直接发现项目级 Skill；Pi 测试通过 `--skill` 加载同一份 `SKILL.md`。后续如果需要作为 Plugin/Marketplace 分发，再增加对应插件清单，不提前引入额外封装。

## 框架支持状态

| 框架 | 发现流程状态 | 官方 Skills 路由 |
|---|---|---|
| Flutter | `supported` | 已配置并验证库搜索、必要性检查路由 |
| React Native | `experimental` | 已登记官方 Skills 仓库，待能力审计 |
| ApplicationTPC (ArkTS) | `experimental` | 已登记官方 Skills 仓库，待能力审计 |
| ApplicationTPC (C/C++) | `experimental` | 已登记官方 Skills 仓库，待能力审计 |
| KMP / CMP | `experimental` | 待补 |
| Cordova | `experimental` | 待补 |
| Ionic | `experimental` | 待补 |
| CJMP | `experimental` | 待补 |
| Electron | `experimental` | 待补 |

## Roadmap

- [x] 明确仓库定位与职责边界
- [x] 设计 `thirdparty-library-discovery` 输入、输出和判定流程
- [x] 建立 `frameworks.yaml`，维护框架与官方资源路由
- [x] 实现 Flutter 候选发现流程 v0.1
- [x] 建立 Pi + Agnes Flash 离线契约测试
- [x] 跑通 live evidence 采集 + Skill 判定链路
- [x] 拉取并审计 CPF-Flutter `flutter-library-search` / `ohos-flutter-plugin-adaptation-necessity-check` 及 references
- [x] 建立官方 Skill handoff 规范和回归测试
- [x] 跑通单候选官方 Skill evidence → judgment → handoff 链路
- [x] 用 `cached_network_image` 真实复核发现纯 Dart 误选问题，并修订候选预筛
- [x] 修复模糊 substring 去重导致的短包名误伤
- [x] 增加零模型 deterministic regression CI
- [ ] 再验证 1～2 个“确实需要原生能力”的 Flutter 候选，确认 `needs_adaptation` / `adapted` 分支的真实表现
- [ ] 把 discovery evidence、official handoff、活动去重合并为统一 candidate qualification artifact
- [ ] 审计 CPF-RN 官方 Skills，补齐 RN 能力路由
- [ ] 审计 CPF-ApplicationTPC 官方 Skills，补齐 ArkTS/C/C++ 能力路由
- [ ] 建立 `article-rules.yaml`，结构化征文规则
- [ ] 实现总控 `harmony-contribution-orchestrator`
- [ ] 实现文章写作辅助与合规检查
- [ ] 如有分发需求，再增加 AtomCode Plugin/Marketplace 元数据

## 下一步

Flutter 发现链路的基础设施已经基本可用。下一步优先做 **candidate qualification artifact**：把一个候选的 discovery 证据、活动去重状态、`flutter-library-search` handoff、可选 necessity-check 结果收敛成一份稳定 JSON，并由确定性规则输出最终资格状态。

这一步完成后，`harmony-contribution-orchestrator` 就可以直接消费 qualification artifact，而不需要理解每个官方 Skill 的原始输出格式。
