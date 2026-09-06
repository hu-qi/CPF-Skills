请严格依据已加载的 `harmony-article-check` Skill，完成一次离线文章合规契约测试。

约束：

- 不联网，不调用外部搜索；
- 下列检查结果和指标都是测试夹具，视为已验证输入；
- 不自行补充夹具之外的事实；
- 不把缺失的外部指标或人工确认项乐观判为 PASS；
- 阅读量属于 POST_PUBLISH，不得阻塞发布前状态；
- 每个 case 必须且只能输出一个结果；
- 只输出 JSON；可以使用一个 `json` 代码围栏，但不得输出其他正文。

输出结构必须为：

```json
{
  "results": [
    {
      "case": "...",
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

2. `ReadyArticle`
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

3. `GitCodeArticle`
   - framework = flutter
   - static checker 的 `gitcode-forbidden = FAIL`
   - Validation Gate = `ARTICLE_PREP/PROCEED`
   - duplication_rate_percent = 20
   - csdn_quality_score = 85
   - original-content = 已人工确认通过
   - ai-not-majority-author = 已人工确认通过
   - 其他发布前人工项均已确认通过
   - readership = 1500

必须输出恰好 3 个结果，不得增加或遗漏 case。
