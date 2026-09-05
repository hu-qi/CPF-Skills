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

## 当前目录

```text
CPF-Skills/
├── .atomcode.md
├── .atomcode/
│   └── skills/
│       └── thirdparty-library-discovery/
│           └── SKILL.md
├── resources/
│   └── frameworks.yaml
└── README.md
```

采用 `.atomcode/skills/` 是为了让 AtomCode 在当前项目中直接发现项目级 Skill；后续如果需要作为 Plugin/Marketplace 分发，再增加对应插件清单，不提前引入额外封装。

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
- [ ] 用真实 Flutter 选库任务跑一轮 v0.1，并根据结果修订 Skill
- [ ] 审计 CPF-RN 官方 Skills，补齐 RN 能力路由
- [ ] 审计 CPF-ApplicationTPC 官方 Skills，补齐 ArkTS/C/C++ 能力路由
- [ ] 建立 `article-rules.yaml`，结构化征文规则
- [ ] 实现总控 `harmony-contribution-orchestrator`
- [ ] 实现文章写作辅助与合规检查
- [ ] 如有分发需求，再增加 AtomCode Plugin/Marketplace 元数据

## 下一步

不要立即继续扩框架。下一步应使用 `thirdparty-library-discovery` **真实跑一轮 Flutter 选库**，目标输出 5-10 个候选，并检查：

1. 候选来源是否足够好；
2. 去重流程是否会产生误判；
3. 官方 Skill 不可用时，`NEEDS_OFFICIAL_CHECK` 是否足够清楚；
4. 评分是否真的有区分度；
5. 最终结果能否直接帮助用户确定一个适配选题。

用真实结果反推 v0.2，比继续堆规则更有价值。
