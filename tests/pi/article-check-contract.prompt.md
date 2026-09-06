请严格依据已加载的 `harmony-article-check` Skill，完成一次离线文章合规契约测试。

约束：

- 不联网，不调用外部搜索；
- 下列内容是离线测试夹具，但每个 case 的 `fixture_only` 字段模拟真实业务语义；
- 不自行补充夹具之外的事实；
- 不把缺失的外部指标或人工确认项乐观判为 PASS；
- 阅读量属于 POST_PUBLISH，不得阻塞发布前状态；
- `status=READY_TO_PUBLISH` 不等于一定 `publishable=true`；fixture case 必须保持不可现实发布；
- 每个 case 必须且只能输出一个结果；
- 只输出 JSON；可以使用一个 `json` 代码围栏，但不得输出其他正文。

输出结构必须为：

```json
{
  "results": [
    {
      "case": "...",
      "fixture_only": false,
      "publishable": false,
      "status": "BLOCKED | MANUAL_REVIEW_REQUIRED | READY_TO_PUBLISH",
      "duplication_rate": "PASS | FAIL | EXTERNAL_REQUIRED",
      "csdn_quality": "PASS | FAIL | EXTERNAL_REQUIRED",
      "original_content": "PASS | FAIL | MANUAL_REQUIRED",
      "ai_not_majority": "PASS | FAIL | MANUAL_REQUIRED",
      "gitcode_forbidden": "PASS | FAIL",
      "readership": "POST_PUBLISH",
      "reason": "..."
    }
  ]
}
```

测试夹具：

1. `MissingExternal`
   - fixture_only = false
   - framework = flutter
   - static checker = PASS
   - gitcode-forbidden = PASS
   - Validation Gate = `ARTICLE_PREP/PROCEED`
   - duplication_rate_percent = 未提供
   - csdn_quality_score = 未提供
   - original-content = 未提供人工确认
   - ai-not-majority-author = 未提供人工确认
   - readership = 20
   - 其他发布前人工项视为已确认通过
   - 预期：`BLOCKED` 且 `publishable=false`

2. `ReadyArticle`
   - fixture_only = false
   - framework = flutter
   - static checker = PASS
   - gitcode-forbidden = PASS
   - Validation Gate = `ARTICLE_PREP/PROCEED`
   - duplication_rate_percent = 20
   - csdn_quality_score = 85
   - original-content = 已人工确认通过
   - ai-not-majority-author = 已人工确认通过
   - 其他发布前人工项均已确认通过
   - readership = 50
   - 预期：`READY_TO_PUBLISH` 且 `publishable=true`；低 readership 不得阻塞

3. `GitCodeArticle`
   - fixture_only = false
   - framework = flutter
   - static checker 的 `gitcode-forbidden = FAIL`
   - Validation Gate = `ARTICLE_PREP/PROCEED`
   - duplication_rate_percent = 20
   - csdn_quality_score = 85
   - original-content = 已人工确认通过
   - ai-not-majority-author = 已人工确认通过
   - 其他发布前人工项均已确认通过
   - readership = 1500
   - 预期：`BLOCKED` 且 `publishable=false`

4. `FixtureReady`
   - fixture_only = true
   - 所有技术 evidence 都是 `fixture://...`
   - framework = arkts
   - static checker = PASS
   - gitcode-forbidden = PASS
   - Validation Gate = `ARTICLE_PREP/PROCEED`（仅测试状态机分支）
   - duplication_rate_percent = 12
   - csdn_quality_score = 95
   - 所有发布前人工项都以 fixture confirmation 模拟为通过
   - readership = 20
   - 预期：为了覆盖状态机可以输出 `status=READY_TO_PUBLISH`，但必须同时 `fixture_only=true`、`publishable=false`，reason 必须说明不能作为现实发布资格

必须输出恰好 4 个结果，不得增加或遗漏 case。
