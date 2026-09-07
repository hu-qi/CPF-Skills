# TODO / Roadmap

本文件记录 `v0.1.0` 之后的优先事项。当前原则：**不再优先增加抽象层，先用真实适配项目验证整条 workflow。**

## P0 — v0.2.0：首个真实适配闭环

- [ ] 选择一个通过活动去重、确实需要鸿蒙适配的真实三方库。
- [ ] 使用 `scripts/evidence/init_real_case.py` 创建真实案例工作区。
- [ ] 完成 qualification，达到：
  - [ ] `qualification.status = RECOMMENDED`
  - [ ] `eligible_to_start_adaptation = true`
  - [ ] `pending_checks = []`
- [ ] 按对应框架官方 Skills / 已审计路由完成真实适配实现。
- [ ] 保存真实实现证据：commit / diff / source refs。
- [ ] 完成构建并保存真实 build log。
- [ ] 完成 Demo / 最小使用场景。
- [ ] 执行关键功能测试并保存报告或日志。
- [ ] 在 HarmonyOS / OpenHarmony **实体设备**上成功运行。
- [ ] 保存可用于文章的真实成功运行截图。
- [ ] 使 Validation Gate 六项全部达到 `VERIFIED`：
  - [ ] implementation
  - [ ] build
  - [ ] demo
  - [ ] tests
  - [ ] device_run
  - [ ] screenshots
- [ ] 生成真实 Article Material Pack，并补齐真实问题、失败尝试和技术取舍记录。
- [ ] 用作者真实主体内容形成文章草稿；AI 不生成全部或大部分正文。
- [ ] 运行 article static check 与 full compliance report。
- [ ] 提供真实重复率结果与 CSDN 质量分。
- [ ] 完成活动要求的人工确认项。
- [ ] 得到真实：`status = READY_TO_PUBLISH` 且 `publishable = true`。
- [ ] 将该案例作为仓库首个 real-case regression / reference case，但不提交敏感或不可公开证据。

### P0 验收标准

只有同时具备以下事实，才允许把 P0 标记完成：

```text
真实 qualification
+ 真实适配 commit/diff
+ 真实 build/test
+ HarmonyOS/OpenHarmony physical device run
+ 真实截图
+ Validation Gate ARTICLE_PREP/PROCEED
+ 非 fixture Article Material Pack
+ Article Check READY_TO_PUBLISH + publishable=true
```

`examples/e2e-fixture/`、`fixture://...`、模型生成的模拟结果均不能用于满足上述验收条件。

## P1 — 流程增强

- [ ] 基于首个真实案例复盘 gate / schema 是否存在过严、过松或重复字段。
- [ ] 增加 real-case preflight/checklist 工具，快速输出当前仍缺失的真实证据。
- [ ] 为真实案例增加可脱敏的 regression fixtures，保持真实证据与测试夹具分离。
- [ ] 继续审计其他框架官方 Skills 的版本与能力变化。
- [ ] 根据真实使用结果再决定是否补充更多 framework-specific routing。

## P2 — 分发与维护

- [ ] 如有实际分发需求，再增加 AtomCode Plugin / Marketplace 元数据。
- [ ] 明确版本发布策略与兼容性约定。
- [ ] 维护 CHANGELOG / release notes。
- [ ] 定期复核 `resources/frameworks.yaml` 和 `resources/article-rules.yaml` 的时效性。

## 非目标

以下事项暂不因为“看起来完整”而优先实现：

- 重复实现 CPF-Flutter / CPF-RN / CPF-ApplicationTPC 已有技术适配 Skills；
- 用合成数据伪造真实适配案例；
- 为尚未真实使用的框架提前堆叠复杂抽象；
- 将阅读量等发布后指标错误地变成发布前阻塞条件。
