请执行一次真实的 Flutter 三方库候选发现 E2E 测试。

目标：

- 找出最多 5 个当前值得继续调查的 Flutter 三方库候选；
- 优先文件处理、多媒体方向；
- 优先 `medium` 难度；
- 必须使用当前可访问的一手来源核查，不得依赖记忆断言“尚未适配”；
- 允许使用网络和命令行工具获取当前信息；
- 按 Skill 要求检查 `resources/frameworks.yaml` 中 Flutter 的发现源与必查去重源；
- 如果官方 Skill 或任何 required 去重源不可用，必须保守降级为 `NEEDS_OFFICIAL_CHECK`，不得标记为 `RECOMMENDED`。

网络访问约束：

- 不要对单个外部来源长时间重试；
- 使用命令行 HTTP 工具时，为单次请求设置合理短超时（建议不超过 15 秒）；
- 一个来源连续访问失败后，将其记录为 `unavailable` 或 `partial` 并继续，不要阻塞整个任务；
- 外部来源不可访问本身是有效测试结果，不要因此伪造检查成功。

先按照 Skill 的正常格式给出面向人的结果。

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
- 候选名称必须唯一；
- 每个候选至少提供 1 个真实的 `evidence_urls`；
- `status` 必须使用 Skill 的规范 token；
- `score` 为 0-100 的整数；
- 如果存在任何 `required: true` 且 `result != checked` 的来源，则所有候选都不得是 `RECOMMENDED`；
- `RECOMMENDED` 候选的 `pending_checks` 必须为空；
- 不要把示例占位符原样当作真实结果输出。
