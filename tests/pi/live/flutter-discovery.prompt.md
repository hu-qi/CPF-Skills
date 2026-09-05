请严格依据已加载的 `thirdparty-library-discovery` Skill，对 CI 采集器提供的**当前 live evidence snapshot** 做 Flutter 候选筛选和状态判定。

本阶段的职责边界：

- evidence 已由确定性采集器从 `resources/frameworks.yaml` 配置的来源实时获取；
- 不要再次联网，不要调用工具，不要补充 evidence 中没有的事实；
- `official_skill_checks` 若为 `not_run`，表示对应 CPF-Flutter 官方 Skill 本次没有执行，必须按 Skill 的保守规则处理；
- `dedup_matches` 是已采集来源中的正向命中，可以作为“已存在相关实现”的证据；
- `partial` / `unavailable` 来源的“未命中”不能证明不存在适配；
- 如果任何 required 去重源不是 `checked`，不得给出 `RECOMMENDED`；
- 如果技术适配必要性尚未经过官方 Skill 或等价证据确认，应使用 `NEEDS_OFFICIAL_CHECK`，而不是自行推断为 `RECOMMENDED`。

目标：

- 从 evidence 的候选池中选出 3-5 个最值得继续调查的 Flutter 包；
- 优先文件处理、多媒体方向；
- 优先 `medium` 难度；
- 对 evidence 中已明确命中现有适配的候选，可列为代表性排除项；
- 所有评分、状态、理由都必须有 evidence 支撑，不得凭记忆补数据。

先按照 Skill 的正常格式给出简洁的面向人结果。

然后在回答末尾追加下面这个机器可读区块，字段名和枚举值必须保持一致：

<!-- CI_RESULT -->
```json
{
  "framework": "flutter",
  "candidates": [
    {
      "name": "package_name",
      "status": "RECOMMENDED | NEEDS_OFFICIAL_CHECK | EXCLUDED_ALREADY_ADAPTED | EXCLUDED_NO_ADAPTATION_NEEDED | EXCLUDED_LOW_VALUE | EXCLUDED_UNVERIFIABLE",
      "difficulty": "easy | medium | hard",
      "score": 0,
      "evidence_urls": ["https://..."],
      "pending_checks": ["..."]
    }
  ],
  "checked_sources": [
    {
      "name": "source name",
      "url": "https://...",
      "required": true,
      "result": "checked | partial | unavailable"
    }
  ],
  "notes": "简短说明"
}
```

机器可读区块要求：

- `candidates` 至少 3 个，最多 5 个；
- 候选必须来自 evidence，名称唯一；
- 每个候选至少提供其 `pub_dev_url` 作为真实 `evidence_urls`；
- `status` 必须使用 Skill 的规范 token；
- `score` 为 0-100 的整数；
- `checked_sources` 必须忠实复制 evidence 中已检查来源的 `name/url/required/result`，不得把 `partial` 或 `unavailable` 改成 `checked`；
- 如果存在任何 `required: true` 且 `result != checked` 的来源，则所有候选都不得是 `RECOMMENDED`；
- `RECOMMENDED` 候选的 `pending_checks` 必须为空；
- 不要把示例占位符原样当作真实结果输出。

下面紧接着会提供 JSON evidence snapshot；只根据它作答。
