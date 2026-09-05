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

## 规划中的 Skills

### 1. `thirdparty-library-discovery`

回答：**“我应该适配哪个三方库？”**

职责：

- 根据指定框架发现候选三方库；
- 过滤低价值、长期不维护、明显不适合作为适配选题的库；
- 检查候选库是否存在平台相关实现、是否具有鸿蒙适配必要性；
- 检查官方/社区已有鸿蒙适配，完成去重；
- 根据生态价值、适配必要性、适配难度、征文价值进行排序；
- 输出推荐候选及排除理由。

这是本仓库优先实现的第一个 Skill。

### 2. `harmony-contribution-orchestrator`

回答：**“完成一次三方库适配征文，接下来应该做什么？”**

负责识别框架、读取当前活动配置、调用官方 Skills，并串联：

`选库 → 去重 → 必要性判断 → 适配 → Demo/测试验证 → 写作 → 合规检查`

### 3. `harmony-article-writing`

回答：**“如何把真实适配过程整理成符合要求的技术文章？”**

重点基于真实开发材料（代码 diff、提交记录、README、Demo、错误与解决过程、运行截图）组织文章，而不是脱离事实直接生成完整适配经历。

### 4. `harmony-article-check`

回答：**“这篇文章是否符合征文要求？”**

输出可执行的合规检查结果，包括硬性要求、缺失项、风险项和发布后指标。

## 官方 Skills

本项目计划优先复用以下社区提供的 Skills：

- CPF-Flutter: https://atomgit.com/CPF-Flutter/skills
- CPF-RN: https://atomgit.com/CPF-RN/skills
- CPF-ApplicationTPC: https://atomgit.com/CPF-ApplicationTPC/skills

具体调用关系和能力映射将在后续资源配置中维护。

## 初始目录规划

```text
CPF-Skills/
├── README.md
├── skills/
│   ├── thirdparty-library-discovery/
│   ├── harmony-contribution-orchestrator/
│   ├── harmony-article-writing/
│   └── harmony-article-check/
└── resources/
    ├── frameworks.yaml
    └── article-rules.yaml
```

目录会随着首个 Skill 的实现逐步落地，不提前创建空目录或无实际用途的占位文件。

## Roadmap

- [x] 明确仓库定位与职责边界
- [ ] 设计 `thirdparty-library-discovery` 输入、输出和判定流程
- [ ] 建立 `frameworks.yaml`，维护框架与官方资源路由
- [ ] 建立 `article-rules.yaml`，结构化征文规则
- [ ] 实现 Flutter 的候选库发现流程作为第一个可运行样例
- [ ] 接入 CPF-Flutter 官方 Skills 做去重与适配必要性判定
- [ ] 扩展 React Native / ApplicationTPC
- [ ] 实现总控 orchestrator
- [ ] 实现文章写作辅助与合规检查

## 当前阶段

当前只完成项目骨架设计。下一步聚焦 `thirdparty-library-discovery`，先把“候选库从哪里来、如何筛选、如何判定、输出什么”定义清楚，再开始实现。
