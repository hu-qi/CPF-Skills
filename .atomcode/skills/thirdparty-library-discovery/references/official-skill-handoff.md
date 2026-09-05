# Official Skill Handoff Contract

本文件定义 `thirdparty-library-discovery` 与框架官方 Skills 之间的结果交接契约。

目标不是重新解释官方 Skill 的内部实现，而是把官方结果映射为本项目稳定、可测试的状态输入。

## 原则

1. 官方 Skill 的原始结论必须保留，不得改写成更强的事实。
2. “未发现适配”不等于“确定不存在适配”。
3. `RECOMMENDED` 只能在技术必要性与活动去重都满足时产生。
4. 任一 required 去重源未完成，最终不得为 `RECOMMENDED`。
5. 官方 Skill 不可用、超时、输出不可解析时，应记录为 `not_run` / `unavailable` / `inconclusive`，不得伪造成功。

## 规范输入

对单个候选，推荐把官方结果归一化为以下结构：

```json
{
  "candidate": "package_name",
  "official_checks": {
    "library_search": {
      "skill": "flutter-library-search",
      "result": "adapted | not_found | no_adaptation_needed | inconclusive | not_run",
      "evidence": ["..."],
      "reason": "..."
    },
    "adaptation_necessity": {
      "skill": "ohos-flutter-plugin-adaptation-necessity-check",
      "result": "needed | not_needed | inconclusive | not_run",
      "evidence": ["..."],
      "reason": "..."
    }
  },
  "dedup_checks": [
    {
      "name": "CPF-Flutter",
      "required": true,
      "result": "checked | partial | unavailable",
      "matches": []
    }
  ]
}
```

`evidence` 可以为空，但 `reason` 必须说明结论来源或为什么无法得出结论。

## 状态映射

按以下优先级应用，先命中的规则优先：

1. `library_search.result == adapted` → `EXCLUDED_ALREADY_ADAPTED`。
2. `library_search.result == no_adaptation_needed` → `EXCLUDED_NO_ADAPTATION_NEEDED`。
3. `adaptation_necessity.result == not_needed` → `EXCLUDED_NO_ADAPTATION_NEEDED`。
4. 任一 required `dedup_checks.result != checked` → 不得 `RECOMMENDED`；若候选仍有价值，则 `NEEDS_OFFICIAL_CHECK`。
5. 任一 required 去重源存在明确同库匹配 → `EXCLUDED_ALREADY_ADAPTED`。
6. `adaptation_necessity.result == needed`，且所有 required 去重源均 `checked` 且无匹配，且 `library_search.result` 不表示已适配/无需适配 → 可进入 `RECOMMENDED` 资格判断。
7. 官方必要性结论为 `inconclusive` / `not_run`，或仍缺关键证据 → `NEEDS_OFFICIAL_CHECK`。
8. 候选身份、原始包或关键证据本身不可验证 → `EXCLUDED_UNVERIFIABLE`。

## 冲突处理

如果两个官方 Skill 结论冲突：

- 不自行选择更乐观结论；
- 最终状态降级为 `NEEDS_OFFICIAL_CHECK`；
- 在 `reason` 中同时记录两个原始结论；
- 要求人工或更新后的官方 Skill 复核。

例如：

- `library_search = adapted`
- `adaptation_necessity = needed`

技术上“仍有适配必要性”不能推翻“已有适配”的活动去重事实，因此活动状态仍应优先排除；若“adapted”证据本身不确定，则降级人工复核。

## 推荐升级条件

一个候选从 `NEEDS_OFFICIAL_CHECK` 升级为 `RECOMMENDED`，至少应同时满足：

- 官方必要性检查明确为 `needed`；
- 官方库搜索未确认已有可用鸿蒙适配；
- 所有活动 required 去重源都已 `checked`；
- required 去重源中没有同库或等价实现的明确命中；
- 候选仍满足维护性、生态价值和征文实践价值要求。

评分只影响排序，不得绕过以上硬门槛。
