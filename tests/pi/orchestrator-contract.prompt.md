请严格依据已加载的 `harmony-contribution-orchestrator` Skill，完成一次离线 qualification 路由契约测试。

约束：

- 不联网，不调用外部搜索；
- 下列 qualification 都是测试夹具，视为已验证标准化输入；
- 不重新执行 discovery，不补充夹具之外的事实；
- 每个候选必须且只能输出一个结果；
- `phase`、`decision`、`qualification_status` 必须使用 Skill 定义的规范英文 token；
- 只输出 JSON；可以使用一个 `json` 代码围栏，但不得输出其他正文。

输出结构必须为：

```json
{
  "results": [
    {
      "candidate": "...",
      "phase": "...",
      "decision": "...",
      "qualification_status": "...",
      "route_skill": "具体 Skill 名称或 null",
      "reason": "..."
    }
  ]
}
```

测试夹具：

1. `ReadyPlugin`
   - framework = flutter
   - qualification.status = `RECOMMENDED`
   - qualification.eligible_to_start_adaptation = true
   - qualification.pending_checks = []
   - 当前夹具没有提供“实际适配 Skill 已确认存在”的信息

2. `NeedsCheckPlugin`
   - framework = flutter
   - qualification.status = `NEEDS_OFFICIAL_CHECK`
   - qualification.eligible_to_start_adaptation = false
   - qualification.pending_checks = [`执行 flutter-library-search 并重新生成 qualification`]

3. `ExistingPlugin`
   - framework = flutter
   - qualification.status = `EXCLUDED_ALREADY_ADAPTED`
   - qualification.eligible_to_start_adaptation = false
   - reason = `CPF-Flutter 活动去重源已存在同库实现`

4. `PureDartPackage`
   - framework = flutter
   - qualification.status = `EXCLUDED_NO_ADAPTATION_NEEDED`
   - qualification.eligible_to_start_adaptation = false
   - reason = `官方检查确认纯 Dart，无需平台适配`

必须输出恰好 4 个结果，不得增加或遗漏候选。
