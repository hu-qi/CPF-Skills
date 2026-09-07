# Changelog

本项目采用语义化版本风格记录公开版本。

## [0.1.0] - 2026-09-07

首个可用 MVP 版本，完成从候选发现到文章合规检查的上层 workflow 基础闭环。

### Added

- `thirdparty-library-discovery`：候选发现、活动去重、官方 Skill handoff 与资格状态输出。
- `harmony-contribution-orchestrator`：qualification gate、framework route、next-action、Validation Gate。
- `harmony-article-writing`：基于真实适配材料的素材包、提纲和局部写作辅助，禁止整篇/大部分参赛正文自动代写。
- `harmony-article-check`：静态检查、完整 compliance aggregation、发布前/发布后状态分离。
- `resources/frameworks.yaml`：框架、社区、官方 Skills 路由事实源。
- `resources/article-rules.yaml`：活动文章规则结构化事实源。
- Flutter live discovery / official candidate smoke。
- CPF-Flutter、CPF-RN、CPF-ApplicationTPC 官方 Skills 审计工作流。
- 5 个隔离 Pi Skill contract matrix。
- deterministic regression suite。
- `examples/e2e-fixture/` fixture-only 端到端回归样例。
- `scripts/evidence/init_real_case.py` 真实案例 evidence intake initializer。
- `TODO.md`：v0.2.0 首个真实适配闭环验收清单。

### Safety / Evidence Boundaries

- `fixture://` 证据只允许在显式 `fixture_only=true` 的测试夹具中使用。
- fixture 不得触发真实资格检查、官方 Skill、framework porting route 或人工适配动作。
- fixture compliance 即使覆盖 `READY_TO_PUBLISH` 分支，也必须 `publishable=false`。
- 真实文章发布资格要求 `fixture_only=false` 且 `READY_TO_PUBLISH + publishable=true`。
- Validation Gate 要求 implementation / build / demo / tests / physical device run / screenshots 六项真实证据。
- HarmonyOS/OpenHarmony 真机要求不能由模拟器、预览器或文字描述替代。

### Known Scope

- 当前尚未包含“真实适配完成”的公开 reference case；该项列入 v0.2.0 P0。
- Flutter / RN 部分实际 porting 阶段仍可能需要人工/交互式适配，因为当前审计未确认独立完整实现 Skill。
- ApplicationTPC ArkTS 已确认可路由 `ohos-library-porting`；C/C++ 当前保持分析 + manual implementation 边界。
- Plugin / Marketplace 分发元数据暂不属于 v0.1.0 范围。
