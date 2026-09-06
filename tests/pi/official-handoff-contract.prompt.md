请严格依据已加载的 `thirdparty-library-discovery` Skill，并按仓库中的官方 Skill handoff 规则，完成一次离线状态映射契约测试。

约束：

- 不联网，不调用外部搜索；
- 下列“官方 Skill 结果”和“去重结果”都是测试夹具，视为已验证输入；
- 不补充夹具之外的事实；
- 每个候选必须且只能输出一个最终 `status`；
- `status` 必须使用 discovery Skill 的规范英文 token；
- 输出 JSON；可以使用一个 `json` 代码围栏，但不得输出其他正文；
- **必须保留下面输出骨架中已经给出的 4 个 candidate 字段，不得删除、改名、重排或新增候选**；
- 你的任务只是在每个对象中填写规范 `status` 和非空 `reason`。

输出必须严格使用下面骨架：

```json
{
  "results": [
    {
      "candidate": "ReadyPlugin",
      "status": "<填写规范 token>",
      "reason": "<填写原因>"
    },
    {
      "candidate": "ExistingPlugin",
      "status": "<填写规范 token>",
      "reason": "<填写原因>"
    },
    {
      "candidate": "PureDartPackage",
      "status": "<填写规范 token>",
      "reason": "<填写原因>"
    },
    {
      "candidate": "PartialCheckPlugin",
      "status": "<填写规范 token>",
      "reason": "<填写原因>"
    }
  ]
}
```

测试候选：

1. `ReadyPlugin`
   - `library_search.result = needs_adaptation`
   - `adaptation_necessity.result = not_run`
   - 所有 required 去重源均 `checked`
   - 所有 required 去重源 `matches = []`
   - 候选维护性、生态价值与征文价值均已通过前置筛选

2. `ExistingPlugin`
   - `library_search.result = adapted`
   - `adaptation_necessity.result = needed`
   - 所有 required 去重源均 `checked`
   - CPF-Flutter 去重源有明确同库命中

3. `PureDartPackage`
   - `library_search.result = no_adaptation_needed`
   - `adaptation_necessity.result = not_needed`
   - 所有 required 去重源均 `checked`
   - 无去重命中

4. `PartialCheckPlugin`
   - `library_search.result = needs_adaptation`
   - `adaptation_necessity.result = not_run`
   - CPF-Flutter 与 hxa-flutter 为 `checked` 且无匹配
   - `CPF-Flutter ThirdpartyLibrarites` 为 required，但 `result = partial`
   - 候选本身仍有较高价值

必须输出恰好 4 个结果，不得增加或遗漏候选。
