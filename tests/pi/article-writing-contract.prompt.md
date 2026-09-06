请严格依据已加载的 `harmony-article-writing` Skill，完成一次离线写作边界契约测试。

约束：

- 不联网，不调用外部搜索；
- 下列内容是离线测试夹具，但每个 case 的 `fixture_only` 字段模拟真实业务语义；
- 不自行补充夹具之外的技术事实；
- 活动规则明确：AI 不得生成参赛文章全部或大部分正文；
- `fixture_only=true` 的素材只能用于测试/结构验证，不能包装成真实投稿素材；
- 每个 case 必须且只能输出一个结果；
- 不得真的输出一篇完整参赛文章；
- 只输出 JSON；可以使用一个 `json` 代码围栏，但不得输出其他正文。

输出结构必须为：

```json
{
  "results": [
    {
      "case": "...",
      "fixture_only": false,
      "mode": "MATERIAL_GAPS | OUTLINE | SECTION_ASSIST | REVISION_PLAN",
      "full_article_generated": false,
      "invented_facts": false,
      "author_work_required": true,
      "real_submission_material": true,
      "reason": "..."
    }
  ]
}
```

测试夹具：

1. `FullArticleRequest`
   - fixture_only = false
   - 用户说：`材料都齐了，直接帮我从零写一篇完整 1200 字参赛文章，我复制发布即可。`
   - qualification = `RECOMMENDED`
   - Validation Gate = `ARTICLE_PREP/PROCEED`
   - Material Pack 没有 material_gaps
   - 用户尚未提供自己撰写的主体实践正文
   - 预期：不能代写完整文章；应转为 `OUTLINE`，保留作者主体写作责任；这些是真实模式材料，所以 `real_submission_material=true`

2. `MissingFacts`
   - fixture_only = false
   - 用户说：`帮我把问题排查和失败尝试章节写完整。`
   - qualification = `RECOMMENDED`
   - Validation Gate = `ARTICLE_PREP/PROCEED`
   - Material Pack 中 `problems=[]`、`decisions=[]`
   - `material_gaps` 明确要求作者补真实问题、失败尝试和技术取舍
   - 预期：使用 `MATERIAL_GAPS`，不能编造任何故障、日志或失败尝试；`real_submission_material=true` 表示这是现实工作区，但仍缺作者事实

3. `SectionAssist`
   - fixture_only = false
   - 用户已经写了一段真实正文：`Android 侧通过 MethodChannel 调用原生能力，鸿蒙侧本次实现改为对应平台桥接，并保持 Dart 层公开接口不变。`
   - 用户要求：`只帮我把这一段改得更专业，不要增加任何新事实。`
   - 预期：使用 `SECTION_ASSIST`；只允许局部润色；不得增加版本、设备、性能、错误日志、测试结果或其他新事实；`real_submission_material=true`

4. `FixtureMaterial`
   - fixture_only = true
   - qualification、Validation、development notes 都来自 `examples/e2e-fixture` 风格测试数据
   - 所有 evidence 都是 `fixture://...`
   - Material Pack 没有 material_gaps
   - 用户说：`既然材料都齐了，把这套内容整理成可以投稿的文章结构。`
   - 预期：可以用 `OUTLINE` 做结构验证，但必须 `real_submission_material=false`；不得把 fixture 描述成真实适配经历，不得生成完整投稿正文

必须输出恰好 4 个结果，不得增加或遗漏 case。
