请严格依据已加载的 `thirdparty-library-discovery` Skill 完成一次离线契约测试。

约束：

- 不要联网，不要调用外部搜索，不要补充任何未提供的事实；
- 只根据下面提供的模拟证据判断状态；
- 不要因为“没看到适配”就推断“没有适配”；
- 每个候选只能给出一个最终状态；
- `status` 必须使用 Skill 中定义的英文规范状态 token，不得翻译、缩写或改写；
- 必须输出且只输出一个 JSON 对象，不要 Markdown，不要代码围栏，不要额外说明；
- `results` 必须严格包含下面 3 个候选，顺序不限，不得遗漏或增加候选。

关键机器语义（不得重新解释）：

- `library_search.result = adapted` 表示“已经存在鸿蒙适配”，必须映射到 `EXCLUDED_ALREADY_ADAPTED`；
- `library_search.result = adapted` **绝不**等于 `no_adaptation_needed`；
- `adaptation_necessity.result = not_needed` 表示技术上无需平台适配，映射到 `EXCLUDED_NO_ADAPTATION_NEEDED`；
- required 去重尚未全部完成时，不得升级为 `RECOMMENDED`。

JSON 结构固定为：

{
  "results": [
    {
      "candidate": "候选名",
      "status": "规范状态 token",
      "reason": "简短中文原因"
    }
  ]
}

候选与证据：

1. `AlphaPlugin`
   - Flutter 插件，当前仍维护；
   - 明确包含平台原生实现，因此技术上可能需要鸿蒙适配；
   - `library_search.result = not_run`；
   - `adaptation_necessity.result = not_run`；
   - 活动 required 去重源尚未全部完成验证。

2. `BetaPlugin`
   - Flutter 插件；
   - `library_search.result = adapted`；
   - 这是官方明确的“已有鸿蒙适配实现”结论。

3. `GammaPackage`
   - Flutter 包；
   - `adaptation_necessity.result = not_needed`；
   - 官方源码级检查确认该包为纯 Dart 实现，不依赖平台原生能力。
