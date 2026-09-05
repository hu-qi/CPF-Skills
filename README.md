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

## 当前可用 Skill

### `thirdparty-library-discovery` v0.1

回答：**“我应该适配哪个三方库？”**

当前正式支持 Flutter 作为首个样例，其他框架已经建立资源路由，但仍标记为 `experimental`。

主要能力：

- 从框架对应的包中心/目录发现候选库；
- 过滤失维、低价值或无法验证的候选；
- 将“候选发现”和“适配必要性判断”分开；
- Flutter 优先衔接 CPF-Flutter 官方 `flutter-library-search` 与 `ohos-flutter-plugin-adaptation-necessity-check`；
- 按活动要求检查中心仓和社区仓去重；
- 以生态价值、适配必要性、可行性、征文价值四个维度评分；
- 输出推荐、待官方确认、已适配、无需适配等明确状态；
- 强制区分“未搜索到”和“确定不存在”，避免把推测当事实。

项目级 Skill 位于：

```text
.atomcode/skills/thirdparty-library-discovery/SKILL.md
```

在 AtomCode 中进入本仓库后，可通过 Skill 菜单或自然语言触发，例如：

```text
帮我找 10 个 Flutter 适合做鸿蒙三方库适配征文的候选库，优先中等难度、文件和多媒体方向。
```

也可以显式选择：

```text
$thirdparty-library-discovery 帮我找 10 个 Flutter 候选库
```

> 说明：Skill 能否自动调用 CPF 官方 Skills，取决于当前 AtomCode 环境是否已经安装/加载对应官方 Skill。若不可调用，本 Skill 会将关键候选标记为 `NEEDS_OFFICIAL_CHECK`，而不是伪造官方检查结论。

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

## 官方 Skills

本项目优先复用以下社区提供的 Skills：

- CPF-Flutter: https://atomgit.com/CPF-Flutter/skills
- CPF-RN: https://atomgit.com/CPF-RN/skills
- CPF-ApplicationTPC: https://atomgit.com/CPF-ApplicationTPC/skills

具体调用关系和能力映射维护在 `resources/frameworks.yaml`。尚未完成官方仓库审计的 Skill 名称不会凭记忆写入配置。

## Pi CI 契约测试

仓库使用 Pi 对 Skill 的核心行为做模型回归测试。当前工作流：

```text
.github/workflows/pi-skill-test.yml
```

当前只运行：

- `agnes-2.5-flash`

通过中国区 OpenAI-compatible 网关 `https://api.agnes-ai.cn/v1` 调用。API Key **不得提交到仓库**，请在 GitHub 仓库中配置 Repository Secret：

```text
AGNES_API_KEY
```

当前离线契约测试使用固定 fixture 验证 `NEEDS_OFFICIAL_CHECK`、`EXCLUDED_ALREADY_ADAPTED`、`EXCLUDED_NO_ADAPTATION_NEEDED` 三条核心状态迁移，不依赖实时包中心或社区仓搜索，因此适合作为 PR 回归检查。

Pi 在 CI 中通过 `--skill .atomcode/skills/thirdparty-library-discovery/SKILL.md` 注册 Skill，并通过 `/skill:thirdparty-library-discovery` 强制加载完整 Skill 内容。模型输出保存在 Actions artifact 中，便于排查状态机回归。

> Fork PR 默认拿不到 Repository Secrets，因此工作流只在手动触发或仓库内 PR 上运行模型测试。

## Live Flutter Discovery E2E

独立工作流：

```text
.github/workflows/pi-live-discovery.yml
```

Live E2E 同样只运行 `agnes-2.5-flash`，并拆成两个阶段：

1. 确定性 Python 采集器按短超时从 `resources/frameworks.yaml` 配置的当前来源获取 Flutter 候选和去重证据，保存为 `flutter-evidence.json`；
2. Pi 以 `--no-tools` 模式读取这份 evidence snapshot，只负责按照 Skill 做状态判定和排序。

这样可以把“外部来源访问失败”和“Skill 判断失败”区分开，并保留可审计的原始证据快照与模型输出。

## 当前目录

```text
CPF-Skills/
├── .atomcode.md
├── .atomcode/
│   └── skills/
│       └── thirdparty-library-discovery/
│           └── SKILL.md
├── .github/
│   └── workflows/
│       ├── pi-skill-test.yml
│       └── pi-live-discovery.yml
├── resources/
│   └── frameworks.yaml
├── scripts/
│   └── ci/
│       ├── test-pi-skill.sh
│       └── test-pi-live-discovery.sh
├── tests/
│   └── pi/
│       ├── discovery-contract.prompt.md
│       ├── assert_discovery_contract.py
│       └── live/
│           ├── collect_flutter_evidence.py
│           ├── flutter-discovery.prompt.md
│           └── assert_flutter_discovery.py
└── README.md
```

采用 `.atomcode/skills/` 是为了让 AtomCode 在当前项目中直接发现项目级 Skill；Pi 测试通过 `--skill` 加载同一个 `SKILL.md`。后续如果需要作为 Plugin/Marketplace 分发，再增加对应插件清单，不提前引入额外封装。

## 框架支持状态

| 框架 | 发现流程状态 | 官方 Skills 路由 |
|---|---|---|
| Flutter | `supported` | 已配置库搜索和适配必要性检查 |
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
- [x] 配置仓库 `AGNES_API_KEY` Secret 并跑通首次 contract CI
- [x] 增加真实 Flutter 候选发现的 live/e2e 测试框架
- [ ] 跑通稳定的 live evidence 采集 + Skill 判定链路
- [ ] 用真实 Flutter 选库任务跑一轮 v0.1，并根据结果修订 Skill
- [ ] 审计 CPF-RN 官方 Skills，补齐 RN 能力路由
- [ ] 审计 CPF-ApplicationTPC 官方 Skills，补齐 ArkTS/C/C++ 能力路由
- [ ] 建立 `article-rules.yaml`，结构化征文规则
- [ ] 实现总控 `harmony-contribution-orchestrator`
- [ ] 实现文章写作辅助与合规检查
- [ ] 如有分发需求，再增加 AtomCode Plugin/Marketplace 元数据

## 下一步

先让 `Pi Live Flutter Discovery E2E` 在 `agnes-2.5-flash` 上稳定跑通，确认实时证据采集、必查去重源状态、规范状态 token 和最终候选结构都可审计。

通过后，再用真实 Flutter 选库任务跑一轮 v0.1，并根据 live evidence 结果修订 Skill；随后推进 RN 与 ApplicationTPC 的官方 Skills 审计。
